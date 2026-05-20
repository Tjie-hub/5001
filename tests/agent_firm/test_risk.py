import json

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.schemas import AgentResult, SignalCandidate


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
    fake_client.chat.return_value = {
        "content": json.dumps({
            "decision": "approve",
            "confidence": 0.7,
            "size_hint": 1.0,
            "rationale": "Risk: trend intact.\nBull/Bear: bull case dominates",
        }),
        "tokens_in": 1500, "tokens_out": 90, "cost_usd": 0.0007, "duration_s": 4.0,
    }
    result = await risk.run(candidate, [technical], fake_client)
    assert result.role == "risk"
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.0


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
    fake_client.chat.return_value = {
        "content": json.dumps({
            "decision": "veto",
            "confidence": 0.85,
            "size_hint": 0.0,
            "rationale": "Risk: clear downtrend.\nBull/Bear: bear case dominant",
        }),
        "tokens_in": 1400, "tokens_out": 80, "cost_usd": 0.0006, "duration_s": 3.8,
    }
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
    fake_client.chat.return_value = {
        "content": "garbage",
        "tokens_in": 100, "tokens_out": 5, "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await risk.run(candidate, [], fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_risk_propagates_analyst_failures_in_payload():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    failed_technical = AgentResult(role="technical", status="failed", error="network")
    captured_messages = {}
    async def capture_chat(messages, **kwargs):
        captured_messages["body"] = messages
        return {
            "content": json.dumps({
                "decision": "approve", "confidence": 0.3, "size_hint": 0.5,
                "rationale": "Risk: analyst down, low conviction.\nBull/Bear: n/a",
            }),
            "tokens_in": 50, "tokens_out": 30, "cost_usd": 0.0, "duration_s": 1.0,
        }
    fake_client = AsyncMock()
    fake_client.chat.side_effect = capture_chat
    result = await risk.run(candidate, [failed_technical], fake_client)
    assert result.status == "ok"
    payload = captured_messages["body"][1]["content"]
    assert "failed" in payload
    assert result.output["confidence"] == 0.3
