import httpx
import pytest
import respx

from engine.agent_firm.client import DeepSeekClient


@pytest.mark.asyncio
async def test_chat_returns_content_tokens_cost():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1", model="deepseek-v4-pro")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-v4-pro",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            },
        ))
        result = await client.chat([{"role": "user", "content": "ping"}])
    assert result["content"] == "hi"
    assert result["tokens_in"] == 100
    assert result["tokens_out"] == 50
    assert result["cost_usd"] == pytest.approx((100 / 1_000_000 * 0.435) + (50 / 1_000_000 * 0.870), rel=1e-9)


@pytest.mark.asyncio
async def test_chat_retries_on_500_then_succeeds():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        route = router.post("/chat/completions")
        route.side_effect = [
            httpx.Response(500, json={"error": "server"}),
            httpx.Response(200, json={
                "id": "x", "object": "chat.completion", "created": 0,
                "model": "deepseek-v4-pro",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }),
        ]
        result = await client.chat([{"role": "user", "content": "ping"}])
    assert result["content"] == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_chat_raises_after_retries_exhausted():
    client = DeepSeekClient(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500, json={"error": "server"}))
        with pytest.raises(Exception):
            await client.chat([{"role": "user", "content": "ping"}], max_retries=1)


def test_cost_calc_zero_when_no_tokens():
    assert DeepSeekClient._calc_cost(0, 0) == 0.0
