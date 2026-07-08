import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import bull
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
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "BULL", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
    ]


def _response(content: str, tokens_in=1100, tokens_out=80) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0005, duration_s=3.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_bull_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "bull_case": "Foreign accumulation + earnings beat creates strong entry.",
        "key_strength": "Smart money accumulation with bullish technicals",
    }))
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.role == "bull"
    assert result.status == "ok"
    assert "bull_case" in result.output
    assert result.tokens_in == 1100
    assert result.provider == "zai"


@pytest.mark.asyncio
async def test_bull_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("bad", tokens_in=50, tokens_out=3)
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bull_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("llm down")
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"
    assert "llm down" in result.error
