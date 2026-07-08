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
