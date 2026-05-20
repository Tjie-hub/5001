import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import bear
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.7}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "TRENDING"}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH"}),
    ]


def _make_bull():
    return AgentResult(
        role="bull", status="ok",
        output={"bull_case": "Strong flow + trend.", "key_strength": "Foreign accumulation"},
    )


@pytest.mark.asyncio
async def test_bear_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "bear_case": "Foreign flows can reverse rapidly if BI surprises.",
            "key_risk": "BI rate surprise causing sector rotation out of banks",
        }),
        "tokens_in": 1200, "tokens_out": 85, "cost_usd": 0.0006, "duration_s": 3.2,
    }
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.role == "bear"
    assert result.status == "ok"
    assert "bear_case" in result.output
    assert result.tokens_in == 1200


@pytest.mark.asyncio
async def test_bear_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "nope", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("conn reset")
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"
    assert "conn reset" in result.error
