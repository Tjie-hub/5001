import httpx
import pytest
import respx

from engine.agent_firm.providers.zai import ZAIProvider


@pytest.mark.asyncio
async def test_generate_returns_provider_response():
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1", model="glm-5.2")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "id": "resp-1", "object": "chat.completion", "created": 0,
                "model": "glm-5.2",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            },
        ))
        resp = await client.generate([{"role": "user", "content": "ping"}])
    assert resp.content == "hi"
    assert resp.provider == "zai"
    assert resp.tokens_in == 100
    assert resp.tokens_out == 50
    assert resp.request_id == "resp-1"
    assert resp.cost_usd == pytest.approx((100 / 1_000_000 * 0.435) + (50 / 1_000_000 * 0.870), rel=1e-9)


@pytest.mark.asyncio
async def test_generate_retries_on_500_then_succeeds():
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        route = router.post("/chat/completions")
        route.side_effect = [
            httpx.Response(500, json={"error": "server"}),
            httpx.Response(200, json={
                "id": "x", "object": "chat.completion", "created": 0,
                "model": "glm-5.2",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }),
        ]
        resp = await client.generate([{"role": "user", "content": "ping"}])
    assert resp.content == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_provider_exception_after_retries_exhausted():
    from engine.agent_firm.providers.errors import ProviderException
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500, json={"error": "server"}))
        with pytest.raises(ProviderException):
            await client.generate([{"role": "user", "content": "ping"}], max_retries=1)


def test_cost_calc_zero_when_no_tokens():
    assert ZAIProvider._calc_cost(0, 0) == 0.0


def test_zai_capabilities():
    client = ZAIProvider(api_key="sk-test")
    assert client.capabilities.supports_json_mode is True
    assert client.capabilities.supports_json_schema is False
    assert client.name == "zai"


# --- RCA 2026-07-10: ZAI 429 code 1308 is a 5-hour usage window, not a burst ---

@pytest.mark.asyncio
async def test_429_usage_limit_message_classified_as_session_limit():
    from engine.agent_firm.providers.errors import ProviderSessionLimit
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            429,
            json={"error": {"code": "1308",
                            "message": "Usage limit reached for 5 hour. Your limit will reset later."}},
        ))
        with pytest.raises(ProviderSessionLimit) as exc_info:
            await client.generate([{"role": "user", "content": "ping"}], max_retries=0)
    assert exc_info.value.category == "session_limit_exceeded"
    assert exc_info.value.reset_time is None  # ZAI gives no reset timestamp


@pytest.mark.asyncio
async def test_plain_429_still_rate_limited():
    from engine.agent_firm.providers.errors import ProviderRateLimited
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            429, json={"error": {"code": "1302", "message": "Rate limit reached for requests"}},
        ))
        with pytest.raises(ProviderRateLimited):
            await client.generate([{"role": "user", "content": "ping"}], max_retries=0)


# --- RCA 2026-07-13: ZAI concurrency cap (prevent 429 bursts) ----------------

@pytest.mark.asyncio
async def test_semaphore_caps_concurrent_requests():
    """At most `max_concurrent` HTTP calls may be in flight at once. The firm
    fans out with unbounded asyncio.gather(); without a cap the ZAI endpoint
    returns 429 code 1302 under burst, opening the circuit and feeding the
    "all providers down" alert."""
    import asyncio

    client = ZAIProvider(
        api_key="sk-test", base_url="https://api.test.com/v1", max_concurrent=2,
    )
    in_flight = 0
    peak = 0
    gate = asyncio.Event()
    gate.set()

    async def _track(request):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.02)  # hold the slot briefly
        in_flight -= 1
        return httpx.Response(200, json={
            "id": "x", "object": "chat.completion", "created": 0, "model": "glm-5.2",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(side_effect=_track)
        await asyncio.gather(*[
            client.generate([{"role": "user", "content": "ping"}]) for _ in range(10)
        ])
    assert peak <= 2, f"semaphore allowed {peak} concurrent calls (cap was 2)"


def test_semaphore_defaults_to_config(monkeypatch):
    """Without an explicit arg, the cap comes from ZAI_MAX_CONCURRENT config."""
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "ZAI_MAX_CONCURRENT", 7)
    client = ZAIProvider(api_key="sk-test")
    # asyncio.Semaphore exposes its value via repr ("value:7" on this Python).
    assert client._semaphore._value == 7
