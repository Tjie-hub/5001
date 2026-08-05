import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import news
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import NewsContext, SignalCandidate


def _make_candidate(news_ctx=None):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        news=news_ctx,
    )


def _make_news_context(**overrides):
    base = dict(
        mentions_7d=[{"ticker": "BBRI", "date": "2026-05-19", "count": 3,
                      "headlines": ["BBRI earnings beat", "BI rate hold", "Foreign buy BBRI"]}],
        mentions_count_7d=3,
        has_catalyst=True,
    )
    base.update(overrides)
    return NewsContext(**base)


def _response(content: str, tokens_in=900, tokens_out=70) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0005, duration_s=3.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_news_returns_ok_on_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "sentiment": "BULLISH",
        "catalyst": "bullish",
        "key_headline": "BBRI earnings beat",
        "summary": "Strong earnings and foreign inflow support bullish thesis",
    }))
    result = await news.run(_make_candidate(_make_news_context()), fake_client)
    assert result.role == "news"
    assert result.status == "ok"
    assert result.output["sentiment"] == "BULLISH"
    assert result.tokens_in == 900


@pytest.mark.asyncio
async def test_news_prompt_payload_carries_news_context_not_raw_dict(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "sentiment": "BULLISH", "catalyst": "bullish",
            "key_headline": "BBRI earnings beat", "summary": "ok",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await news.run(_make_candidate(_make_news_context()), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    assert payload["news_context"]["mentions_count_7d"] == 3
    assert payload["news_context"]["has_catalyst"] is True
    assert "news_mentions_7d" not in payload


@pytest.mark.asyncio
async def test_news_missing_context_degrades_to_default_not_raise(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "sentiment": "NEUTRAL", "catalyst": "neutral",
            "key_headline": None, "summary": "no recent news found",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await news.run(_make_candidate(news_ctx=None), fake_client)
    assert result.status == "ok"
    payload = json.loads(captured["body"][1]["content"])
    assert payload["news_context"]["mentions_count_7d"] == 0
    assert payload["news_context"]["has_catalyst"] is False


@pytest.mark.asyncio
async def test_news_returns_failed_on_invalid_json(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not json", tokens_in=50, tokens_out=3)
    result = await news.run(_make_candidate(_make_news_context()), fake_client)
    assert result.status == "failed"
    # generate() succeeded (real call happened) before the JSON parse failed —
    # the failed result must still carry resp's real cost/token/provider data.
    assert result.tokens_in == 50
    assert result.tokens_out == 3
    assert result.cost_usd == 0.0005
    assert result.provider == "zai"
    assert result.model == "glm-5.2"


@pytest.mark.asyncio
async def test_news_returns_failed_on_client_exception(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("api down")
    result = await news.run(_make_candidate(_make_news_context()), fake_client)
    assert result.status == "failed"
    assert "api down" in result.error
