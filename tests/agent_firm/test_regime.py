import json
import pytest
from unittest.mock import AsyncMock
from engine.agent_firm.agents import regime
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        regime="TRENDING",
    )


def _make_context():
    return {
        "wf_scores": [
            {"strategy": "vol_weighted", "consistency_pct": 68.0,
             "avg_return_pct": 3.2, "avg_sharpe": 1.1, "weighted_score": 72.0},
        ],
        "sector_data": [
            {"date": "2026-05-19", "signal": "BUY", "vpin_label": "NORMAL", "vol_ratio": 1.8},
        ],
    }


@pytest.mark.asyncio
async def test_regime_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "regime_call": "TRENDING",
            "sector_tailwind": True,
            "macro_risk": "LOW",
            "reasoning": "Consistent walk-forward with elevated VPIN",
        }),
        "tokens_in": 700, "tokens_out": 55, "cost_usd": 0.0003, "duration_s": 2.0,
    }
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "regime"
    assert result.status == "ok"
    assert result.output["regime_call"] == "TRENDING"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "bad json", "tokens_in": 50, "tokens_out": 3,
        "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("network down")
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "network down" in result.error
