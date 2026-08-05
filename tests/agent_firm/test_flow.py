import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import flow
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import FlowContext, SignalCandidate


def _make_candidate(flow_ctx=None):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        flow=flow_ctx,
    )


def _make_flow_context(**overrides):
    base = dict(
        verdict="ACCUMULATING", smart_money="YES", composite_score=8,
        foreign_score=2.5, net_foreign_14d=3000, trend_7d="accumulating",
    )
    base.update(overrides)
    return FlowContext(**base)


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
    result = await flow.run(_make_candidate(_make_flow_context()), fake_client)
    assert result.role == "flow"
    assert result.status == "ok"
    assert result.output["flow_verdict"] == "ACCUMULATING"
    assert result.tokens_in == 800


@pytest.mark.asyncio
async def test_flow_prompt_payload_carries_flow_context_not_raw_rows():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY",
            "net_foreign_14d": 3000, "reasoning": "ok",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await flow.run(_make_candidate(_make_flow_context()), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    assert payload["flow_context"]["verdict"] == "ACCUMULATING"
    assert payload["flow_context"]["net_foreign_14d"] == 3000
    assert "stockbit_flow_14d" not in payload
    assert "broker_flow_14d" not in payload


@pytest.mark.asyncio
async def test_flow_missing_context_degrades_to_default_not_raise():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "flow_verdict": "NEUTRAL", "smart_money_signal": "NEUTRAL",
            "net_foreign_14d": 0, "reasoning": "insufficient flow data",
        }))

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await flow.run(_make_candidate(flow_ctx=None), fake_client)
    assert result.status == "ok"
    payload = json.loads(captured["body"][1]["content"])
    assert payload["flow_context"]["verdict"] is None
    assert payload["flow_context"]["trend_7d"] == "flat"


@pytest.mark.asyncio
async def test_flow_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not json", tokens_in=100, tokens_out=5)
    result = await flow.run(_make_candidate(_make_flow_context()), fake_client)
    assert result.status == "failed"
    # generate() succeeded (real call happened) before the JSON parse failed —
    # the failed result must still carry resp's real cost/token/provider data.
    assert result.tokens_in == 100
    assert result.tokens_out == 5
    assert result.cost_usd == 0.0004
    assert result.provider == "zai"
    assert result.model == "glm-5.2"


@pytest.mark.asyncio
async def test_flow_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("timeout")
    result = await flow.run(_make_candidate(_make_flow_context()), fake_client)
    assert result.status == "failed"
    assert "timeout" in result.error
