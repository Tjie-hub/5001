import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import technical
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate, TechnicalContext


def _make_candidate(technical_ctx=None):
    return SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        technical=technical_ctx,
    )


def _response(content: str, tokens_in=1200, tokens_out=80) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0006, duration_s=3.2,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_technical_returns_ok_result_on_success():
    candidate = _make_candidate(TechnicalContext(
        sma20=5010.0, sma50=4990.0, mechanical_direction="BULLISH",
        support_levels=[5000.0], resistance_levels=[5200.0],
    ))
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "verdict": "BULLISH",
        "conviction": 0.75,
        "key_levels": {"support": 5000, "resistance": 5200},
        "reasoning": "Higher highs and rising volume",
    }))
    result = await technical.run(candidate, fake_client)
    assert result.role == "technical"
    assert result.status == "ok"
    assert result.output["verdict"] == "BULLISH"
    assert result.tokens_in == 1200


@pytest.mark.asyncio
async def test_technical_does_not_query_sqlite_directly():
    """WP3: the agent must consume TechnicalContext, not derive facts from raw OHLCV —
    confirmed by the absence of any sqlite_query tool call (WP1/WP2 removed the db_path
    parameter that used to make this call)."""
    candidate = _make_candidate(TechnicalContext(sma20=5010.0, mechanical_direction="BULLISH"))
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "verdict": "BULLISH", "conviction": 0.7,
        "key_levels": {"support": 5000, "resistance": 5200},
        "reasoning": "trend intact",
    }))
    result = await technical.run(candidate, fake_client)
    assert result.tools_called == []


@pytest.mark.asyncio
async def test_technical_prompt_payload_carries_technical_context_not_raw_ohlcv():
    candidate = _make_candidate(TechnicalContext(
        sma20=100.0, mechanical_direction="BULLISH", support_levels=[95.0],
    ))
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "verdict": "BULLISH", "conviction": 0.7,
            "key_levels": {"support": 95, "resistance": 110},
            "reasoning": "ok",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await technical.run(candidate, fake_client)
    payload = json.loads(captured["body"][1]["content"])
    assert "technical_context" in payload
    assert payload["technical_context"]["sma20"] == 100.0
    assert payload["technical_context"]["mechanical_direction"] == "BULLISH"
    assert "ohlcv" not in payload
    assert "ohlcv_recent_60d" not in payload


@pytest.mark.asyncio
async def test_technical_missing_context_degrades_to_default_not_raise():
    """candidate.technical is None (e.g. a caller that predates WP2's producer wiring) —
    the agent must fail soft to TechnicalContext()'s defaults, not raise."""
    candidate = _make_candidate(technical_ctx=None)
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "verdict": "NEUTRAL", "conviction": 0.0,
            "key_levels": {"support": 0, "resistance": 0},
            "reasoning": "insufficient data",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await technical.run(candidate, fake_client)
    assert result.status == "ok"
    payload = json.loads(captured["body"][1]["content"])
    assert payload["technical_context"]["sma20"] is None
    assert payload["technical_context"]["mechanical_direction"] == "NEUTRAL"


@pytest.mark.asyncio
async def test_technical_returns_failed_on_invalid_json():
    candidate = _make_candidate(TechnicalContext(sma20=100.0))
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not valid json", tokens_in=100, tokens_out=5)
    result = await technical.run(candidate, fake_client)
    assert result.status == "failed"
    assert "json" in result.error.lower() or "decode" in result.error.lower()
    # client.generate() succeeded (real, billable call happened) before the
    # JSON parse failed — the failed result must still carry resp's real
    # cost/token/provider data, not schema defaults.
    assert result.tokens_in == 100
    assert result.tokens_out == 5
    assert result.cost_usd == 0.0006
    assert result.provider == "zai"
    assert result.model == "glm-5.2"
    assert result.runtime_version == "1.0.0"


@pytest.mark.asyncio
async def test_technical_returns_failed_on_client_exception():
    candidate = _make_candidate(TechnicalContext(sma20=100.0))
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("network down")
    result = await technical.run(candidate, fake_client)
    assert result.status == "failed"
    assert "network down" in result.error
    # generate() itself raised — no response was ever received, so defaults hold.
    assert result.tokens_in == 0
    assert result.cost_usd == 0.0
    assert result.provider == ""
