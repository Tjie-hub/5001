import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import regime
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import RegimeContext, SignalCandidate


def _make_candidate(regime_ctx=None):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        regime="BULL",
        regime_context=regime_ctx,
    )


def _make_regime_context(**overrides):
    base = dict(
        regime_call="BULL", sector_tailwind=True, macro_risk="LOW",
        best_strategy="vol_weighted", ticker_consistency_pct=68.0,
    )
    base.update(overrides)
    return RegimeContext(**base)


def _response(content: str, tokens_in=700, tokens_out=55) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0003, duration_s=2.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_regime_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "regime_call": "BULL",
        "sector_tailwind": True,
        "macro_risk": "LOW",
        "reasoning": "Consistent walk-forward with elevated VPIN",
    }))
    result = await regime.run(_make_candidate(_make_regime_context()), fake_client)
    assert result.role == "regime"
    assert result.status == "ok"
    assert result.output["regime_call"] == "BULL"


@pytest.mark.asyncio
async def test_regime_prompt_payload_carries_regime_context_not_raw_rows():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "regime_call": "BULL", "sector_tailwind": True, "macro_risk": "LOW",
            "reasoning": "ok",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await regime.run(_make_candidate(_make_regime_context()), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    assert payload["regime_context"]["regime_call"] == "BULL"
    assert payload["regime_context"]["ticker_consistency_pct"] == 68.0
    assert "wf_scores" not in payload
    assert "sector_data_10d" not in payload


@pytest.mark.asyncio
async def test_regime_missing_context_degrades_to_default_not_raise():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "regime_call": "UNKNOWN", "sector_tailwind": False, "macro_risk": "LOW",
            "reasoning": "insufficient regime data",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await regime.run(_make_candidate(regime_ctx=None), fake_client)
    assert result.status == "ok"
    payload = json.loads(captured["body"][1]["content"])
    assert payload["regime_context"]["regime_call"] == "UNKNOWN"
    assert payload["regime_context"]["recent_screen_signals"] == []


@pytest.mark.asyncio
async def test_regime_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("bad json", tokens_in=50, tokens_out=3)
    result = await regime.run(_make_candidate(_make_regime_context()), fake_client)
    assert result.status == "failed"
    # generate() succeeded (real call happened) before the JSON parse failed —
    # the failed result must still carry resp's real cost/token/provider data.
    assert result.tokens_in == 50
    assert result.tokens_out == 3
    assert result.cost_usd == 0.0003
    assert result.provider == "zai"
    assert result.model == "glm-5.2"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("network down")
    result = await regime.run(_make_candidate(_make_regime_context()), fake_client)
    assert result.status == "failed"
    assert "network down" in result.error
