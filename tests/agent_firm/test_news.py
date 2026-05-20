import json
import pytest
import respx
import httpx
from unittest.mock import AsyncMock
from engine.agent_firm.agents import news
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context():
    return {
        "news_mentions": [
            {"ticker": "BBRI", "date": "2026-05-19", "count": 3,
             "headlines": ["BBRI earnings beat", "BI rate hold", "Foreign buy BBRI"]},
        ],
    }


@pytest.mark.asyncio
async def test_news_returns_ok_on_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "sentiment": "BULLISH",
            "catalyst": "bullish",
            "key_headline": "BBRI earnings beat",
            "summary": "Strong earnings and foreign inflow support bullish thesis",
        }),
        "tokens_in": 900, "tokens_out": 70, "cost_usd": 0.0005, "duration_s": 3.0,
    }
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "news"
    assert result.status == "ok"
    assert result.output["sentiment"] == "BULLISH"
    assert result.tokens_in == 900


@pytest.mark.asyncio
async def test_news_returns_failed_on_invalid_json(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "not json", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_news_returns_failed_on_client_exception(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("api down")
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "api down" in result.error
