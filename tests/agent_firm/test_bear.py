import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import bear
from engine.agent_firm.providers.base import ProviderResponse
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
                    output={"regime_call": "BULL"}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH"}),
    ]


def _make_bull():
    return AgentResult(
        role="bull", status="ok",
        output={"bull_case": "Strong flow + trend.", "key_strength": "Foreign accumulation"},
    )


def _response(content: str, tokens_in=1200, tokens_out=85) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0006, duration_s=3.2,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_bear_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "bear_case": "Foreign flows can reverse rapidly if BI surprises.",
        "key_risk": "BI rate surprise causing sector rotation out of banks",
    }))
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.role == "bear"
    assert result.status == "ok"
    assert "bear_case" in result.output
    assert result.tokens_in == 1200
    assert result.provider == "zai"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("nope", tokens_in=50, tokens_out=3)
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"
    # generate() succeeded (real call happened) before the JSON parse failed —
    # the failed result must still carry resp's real cost/token/provider data.
    assert result.tokens_in == 50
    assert result.tokens_out == 3
    assert result.cost_usd == 0.0006
    assert result.provider == "zai"
    assert result.model == "glm-5.2"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("conn reset")
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"
    assert "conn reset" in result.error
