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
    """No reset timestamp in the message -> falls back to reset_time=None (the
    Router applies its QUOTA_FALLBACK_HOLD_S window in that case)."""
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
    assert exc_info.value.reset_time is None


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


# --- audit 2026-07-22: ZAI DOES advertise a real reset timestamp on genuine
# quota exhaustion ("Your limit will reset at YYYY-MM-DD HH:MM:SS", WIB per
# live production events cross-checked against 3 independent incidents on
# 2026-07-13/21) -- discarding it (reset_time=None) forced the Router's 900s
# fallback hold instead of the true ~5h/weekly window, causing continuous
# re-probing of a provider already known to be exhausted for hours/days. ---

@pytest.mark.asyncio
async def test_429_usage_limit_with_real_reset_timestamp_extracts_reset_time():
    from datetime import datetime, timezone
    from engine.agent_firm.providers.errors import ProviderSessionLimit
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            429,
            json={"error": {"code": "1308",
                            "message": "Usage limit reached for 5 hour. "
                                       "Your limit will reset at 2026-07-22 00:56:18"}},
        ))
        with pytest.raises(ProviderSessionLimit) as exc_info:
            await client.generate([{"role": "user", "content": "ping"}], max_retries=0)
    # "2026-07-22 00:56:18" is WIB (Asia/Jakarta, UTC+7) -> 2026-07-21 17:56:18 UTC.
    assert exc_info.value.reset_time == datetime(2026, 7, 21, 17, 56, 18, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_weekly_monthly_limit_exhausted_classified_as_session_limit():
    """Code 1310 ('Weekly/Monthly Limit Exhausted') does not contain the
    literal 'usage limit reached' phrase, but it IS a sustained quota
    exhaustion carrying its own reset timestamp -- production evidence
    (provider_events, 2026-07-14..16) shows 80 unheld re-probes over 2 days
    because this message fell through to plain ProviderRateLimited, which the
    Router does not hold/persist (only ProviderSessionLimit is)."""
    from datetime import datetime, timezone
    from engine.agent_firm.providers.errors import ProviderSessionLimit
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            429,
            json={"error": {"code": "1310",
                            "message": "Weekly/Monthly Limit Exhausted. "
                                       "Your limit will reset at 2026-07-17 09:18:06"}},
        ))
        with pytest.raises(ProviderSessionLimit) as exc_info:
            await client.generate([{"role": "user", "content": "ping"}], max_retries=0)
    assert exc_info.value.category == "session_limit_exceeded"
    assert exc_info.value.reset_time == datetime(2026, 7, 17, 2, 18, 6, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_plain_429_without_reset_timestamp_stays_rate_limited():
    """A transient burst limit (code 1302/1305) has no reset timestamp and no
    'usage limit reached' phrase -> must stay ProviderRateLimited (unchanged
    behavior; these self-heal via the circuit breaker within one tick)."""
    from engine.agent_firm.providers.errors import ProviderRateLimited
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            429, json={"error": {"code": "1305",
                                  "message": "The service may be temporarily "
                                             "overloaded, please try again later"}},
        ))
        with pytest.raises(ProviderRateLimited):
            await client.generate([{"role": "user", "content": "ping"}], max_retries=0)


def test_parse_zai_reset_rejects_garbage():
    from engine.agent_firm.providers.zai import _parse_zai_reset
    assert _parse_zai_reset("") is None
    assert _parse_zai_reset("no reset info here") is None
    assert _parse_zai_reset("Your limit will reset at not-a-date") is None


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
