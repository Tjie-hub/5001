import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, PortfolioContext, RiskContext, SignalCandidate


def _response(content: str, tokens_in=1500, tokens_out=90) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0007, duration_s=4.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_risk_approve_on_bullish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BULLISH", "conviction": 0.75,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "Higher highs",
        },
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "approve",
        "confidence": 0.7,
        "size_tier": "normal",
        "rationale": "Risk: trend intact.\nBull/Bear: bull case dominates",
    }))
    result = await risk.run(candidate, [technical], fake_client)
    assert result.role == "risk"
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_tier"] == "normal"


@pytest.mark.asyncio
async def test_risk_veto_on_bearish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=2.5, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BEARISH", "conviction": 0.8,
            "key_levels": {"support": 4800, "resistance": 5050},
            "reasoning": "Lower lows",
        },
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "veto",
        "confidence": 0.85,
        "size_tier": None,
        "rationale": "Risk: clear downtrend.\nBull/Bear: bear case dominant",
    }), tokens_in=1400, tokens_out=80)
    result = await risk.run(candidate, [technical], fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "veto"


@pytest.mark.asyncio
async def test_risk_returns_failed_on_invalid_json():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("garbage", tokens_in=100, tokens_out=5)
    result = await risk.run(candidate, [], fake_client)
    assert result.status == "failed"
    # generate() succeeded (real call happened) before the JSON parse failed —
    # the failed result must still carry resp's real cost/token/provider data.
    assert result.tokens_in == 100
    assert result.tokens_out == 5
    assert result.cost_usd == 0.0007
    assert result.provider == "zai"
    assert result.model == "glm-5.2"


@pytest.mark.asyncio
async def test_risk_propagates_analyst_failures_in_payload():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    failed_technical = AgentResult(role="technical", status="failed", error="network")
    captured_messages = {}

    async def capture_generate(messages, **kwargs):
        captured_messages["body"] = messages
        return _response(json.dumps({
            "decision": "approve", "confidence": 0.3, "size_tier": "reduce",
            "rationale": "Risk: analyst down, low conviction.\nBull/Bear: n/a",
        }), tokens_in=50, tokens_out=30)

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await risk.run(candidate, [failed_technical], fake_client)
    assert result.status == "ok"
    payload = captured_messages["body"][1]["content"]
    assert "failed" in payload
    assert result.output["confidence"] == 0.3


# ── WP3: RiskContext/PortfolioContext consumption ────────────────────────────

@pytest.mark.asyncio
async def test_risk_prompt_payload_carries_portfolio_and_risk_context():
    """WP3: Risk Manager must consume PortfolioContext/RiskContext directly off the
    candidate, closing the pre-existing gap where risk_v2.md claimed to check open
    positions but was never actually given the data."""
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        portfolio=PortfolioContext(open_trades=[{"ticker": "BBRI"}], open_position_count=1),
        risk_limits=RiskContext(entries_blocked=False, drawdown_pct=3.5),
    )
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "decision": "veto", "confidence": 0.6, "size_tier": None,
            "rationale": "Risk: already open.\nBull/Bear: n/a",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await risk.run(candidate, [], fake_client)
    payload = json.loads(captured["body"][1]["content"])
    assert payload["portfolio_context"]["already_open_position"] is True
    assert payload["portfolio_context"]["open_position_count"] == 1
    assert payload["risk_context"]["drawdown_pct"] == 3.5
    assert payload["risk_context"]["entries_blocked"] is False
    # Risk Manager must never see the full open_trades list or perform its own lookup —
    # only the already-computed boolean/count facts.
    assert "open_trades" not in payload["portfolio_context"]


@pytest.mark.asyncio
async def test_risk_missing_portfolio_and_risk_context_degrades_to_default():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "decision": "approve", "confidence": 0.6, "size_tier": "normal",
            "rationale": "ok.\nok.",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await risk.run(candidate, [], fake_client)
    assert result.status == "ok"
    payload = json.loads(captured["body"][1]["content"])
    assert payload["portfolio_context"]["already_open_position"] is False
    assert payload["risk_context"]["entries_blocked"] is False
    assert payload["risk_context"]["drawdown_pct"] is None
