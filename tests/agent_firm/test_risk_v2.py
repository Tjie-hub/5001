import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate(score=4.0):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=score, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_all_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.75}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "BULL", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
        AgentResult(role="bull", status="ok",
                    output={"bull_case": "Strong case.", "key_strength": "Accumulation"}),
        AgentResult(role="bear", status="ok",
                    output={"bear_case": "Rate risk.", "key_risk": "BI surprise"}),
    ]


def _response(content: str, tokens_in=2000, tokens_out=100) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0009, duration_s=5.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_risk_v2_approve_on_full_bullish_committee():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "approve", "confidence": 0.82,
        "size_hint": 1.2,
        "rationale": "Risk: all analysts aligned.\nBull/Bear: bull case dominates.",
    }))
    result = await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.2
    assert result.tokens_in == 2000


@pytest.mark.asyncio
async def test_risk_v2_all_6_reports_in_payload():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "decision": "approve", "confidence": 0.6,
            "size_hint": 1.0, "rationale": "ok.\nok.",
        }), tokens_in=50, tokens_out=30)

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    roles = [r["role"] for r in payload["analyst_reports"]]
    assert "bull" in roles
    assert "bear" in roles
    assert len(roles) == 6
