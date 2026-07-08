import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import flow
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context(verdict="ACCUMULATING"):
    return {
        "stockbit_flow": [
            {"trade_date": "2026-05-19", "buy_lot": 5000, "sell_lot": 2000,
             "net_lot": 3000, "net_value": 1500000000, "verdict": "BUY",
             "smart_money": "YES", "foreign_score": 2.5, "composite_score": 8},
        ],
        "broker_flow": [
            {"trade_date": "2026-05-19", "broker_code": "BK", "side": "BUY",
             "lot_value": 1000000000, "investor_type": "Asing"},
        ],
        "stockbit_flow_bars": [],
    }


def _response(content: str, tokens_in=800, tokens_out=60) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0004, duration_s=2.5,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_flow_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "flow_verdict": "ACCUMULATING",
        "smart_money_signal": "BUY",
        "net_foreign_14d": 3000,
        "reasoning": "Consistent net buying with smart money",
    }))
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "flow"
    assert result.status == "ok"
    assert result.output["flow_verdict"] == "ACCUMULATING"
    assert result.tokens_in == 800


@pytest.mark.asyncio
async def test_flow_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not json", tokens_in=100, tokens_out=5)
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_flow_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("timeout")
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "timeout" in result.error
