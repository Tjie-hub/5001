"""Tests for engine/agent_firm/smoke.py — the Tier 4 daily smoke probe.

Covers `_check_cost` (provider-aware cost sanity check) directly, plus
`main()`'s exit codes via mocking `evaluate_async` so no real provider
(zai HTTP call or claude CLI subprocess) is ever invoked.
"""
from unittest.mock import AsyncMock, patch

import pytest

from engine.agent_firm import smoke
from engine.agent_firm.schemas import AgentDecision


def _decision(
    decision="approve",
    cost_usd=0.01,
    tokens_in=500,
    providers_used=None,
    duration_s=5.0,
):
    return AgentDecision(
        ticker="BBRI",
        strategy="momentum_following",
        scan_time="2026-07-09T00:00:00+00:00",
        quant_score=4.2,
        decision=decision,
        confidence=0.8,
        size_hint=1.0,
        rationale="test",
        tokens_in=tokens_in,
        tokens_out=200,
        cost_usd=cost_usd,
        duration_s=duration_s,
        providers_used=providers_used or [],
    )


# ── _check_cost unit tests ──────────────────────────────────────────────────

def test_check_cost_zai_only_healthy():
    d = _decision(cost_usd=0.01, providers_used=["zai"])
    ok, err = smoke._check_cost(d)
    assert ok is True
    assert err is None


def test_check_cost_zai_only_too_cheap_fails():
    d = _decision(cost_usd=0.00001, providers_used=["zai"])
    ok, err = smoke._check_cost(d)
    assert ok is False
    assert "cost" in err


def test_check_cost_zai_only_too_expensive_fails():
    d = _decision(cost_usd=1.0, providers_used=["zai"])
    ok, err = smoke._check_cost(d)
    assert ok is False
    assert "cost" in err


def test_check_cost_claude_only_healthy_zero_cost_passes():
    """Claude is subscription-billed: cost_usd=0.0 is expected and healthy."""
    d = _decision(cost_usd=0.0, tokens_in=500, providers_used=["claude"])
    ok, err = smoke._check_cost(d)
    assert ok is True
    assert err is None


def test_check_cost_claude_only_zero_tokens_fails():
    """cost_usd=0 AND tokens_in=0 looks like the pipeline never really ran."""
    d = _decision(cost_usd=0.0, tokens_in=0, providers_used=["claude"])
    ok, err = smoke._check_cost(d)
    assert ok is False
    assert "tokens_in" in err


def test_check_cost_mixed_healthy_low_cost_passes():
    """Mixed claude+zai: cost below the zai-only floor is legitimate."""
    d = _decision(cost_usd=0.00002, tokens_in=500, providers_used=["claude", "zai"])
    ok, err = smoke._check_cost(d)
    assert ok is True
    assert err is None


def test_check_cost_mixed_over_ceiling_fails():
    d = _decision(cost_usd=1.0, tokens_in=500, providers_used=["claude", "zai"])
    ok, err = smoke._check_cost(d)
    assert ok is False
    assert "cost" in err


def test_check_cost_mixed_zero_tokens_fails():
    d = _decision(cost_usd=0.0, tokens_in=0, providers_used=["claude", "zai"])
    ok, err = smoke._check_cost(d)
    assert ok is False
    assert "tokens_in" in err


# ── main() integration tests (evaluate_async mocked) ────────────────────────

def _run_main_with(decision):
    with patch.object(smoke, "evaluate_async", new=AsyncMock(return_value=[decision])), \
         patch.object(smoke.config, "is_active", return_value=True):
        return smoke.main()


def test_main_zai_only_healthy_exits_ok():
    d = _decision(decision="approve", cost_usd=0.01, providers_used=["zai"])
    assert _run_main_with(d) == 0


def test_main_zai_only_out_of_bounds_exits_4():
    d = _decision(decision="approve", cost_usd=0.0, providers_used=["zai"])
    assert _run_main_with(d) == 4


def test_main_claude_only_healthy_exits_ok():
    """The bug this test guards: claude-only used to false-alarm exit 4."""
    d = _decision(decision="approve", cost_usd=0.0, tokens_in=500, providers_used=["claude"])
    assert _run_main_with(d) == 0


def test_main_degraded_skips_cost_check_entirely():
    """degraded decisions bypass the cost check regardless of provider/cost."""
    d = _decision(decision="degraded", cost_usd=0.0, tokens_in=0, providers_used=[])
    assert _run_main_with(d) == 0


def test_main_skip_when_firm_not_active():
    with patch.object(smoke.config, "is_active", return_value=False):
        assert smoke.main() == 0
