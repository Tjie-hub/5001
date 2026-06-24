"""Tests for the deterministic Risk-decision guardrails."""
import pytest

from engine.agent_firm.guardrails import apply_guardrails, normalize_quant
from engine.agent_firm.schemas import AgentResult


def _r(role, output, status="ok"):
    return AgentResult(role=role, status=status, output=output)


def _analysts(flow=None, tech=None, regime=None):
    out = []
    if flow is not None:
        out.append(_r("flow", flow))
    if tech is not None:
        out.append(_r("technical", tech))
    if regime is not None:
        out.append(_r("regime", regime))
    return out


# ── hard flow contradiction ──────────────────────────────────────────────────
def test_bearish_flow_not_offset_is_vetoed():
    a = _analysts(flow={"flow_verdict": "BEARISH"}, tech={"verdict": "NEUTRAL"})
    decision, reason = apply_guardrails("approve", 0.6, a)
    assert decision == "veto" and "flow BEARISH" in reason


def test_bearish_flow_offset_by_bullish_technical_survives():
    a = _analysts(flow={"flow_verdict": "DISTRIBUTING"}, tech={"verdict": "BULLISH"})
    assert apply_guardrails("approve", 0.6, a) == ("approve", None)


def test_neutral_flow_survives():
    # OASA premarket case: flow NEUTRAL/BUY, technical NEUTRAL → stays approve
    a = _analysts(flow={"flow_verdict": "NEUTRAL"}, tech={"verdict": "NEUTRAL"},
                  regime={"regime_call": "BULL"})
    assert apply_guardrails("approve", 0.6, a) == ("approve", None)


# ── regime confidence floor ──────────────────────────────────────────────────
def test_low_confidence_vetoed_in_weak_regime():
    a = _analysts(flow={"flow_verdict": "NEUTRAL"}, regime={"regime_call": "SIDEWAYS"})
    decision, reason = apply_guardrails("approve", 0.50, a)
    assert decision == "veto" and "confidence 0.50" in reason


def test_confidence_at_floor_survives_weak_regime():
    a = _analysts(flow={"flow_verdict": "NEUTRAL"}, regime={"regime_call": "BEAR"})
    assert apply_guardrails("approve", 0.55, a) == ("approve", None)


def test_low_confidence_ok_in_bull_regime():
    a = _analysts(flow={"flow_verdict": "NEUTRAL"}, regime={"regime_call": "BULL"})
    assert apply_guardrails("approve", 0.50, a) == ("approve", None)


# ── never upgrades / no-op on veto ───────────────────────────────────────────
def test_veto_is_never_changed():
    a = _analysts(flow={"flow_verdict": "BULLISH"}, regime={"regime_call": "BULL"})
    assert apply_guardrails("veto", 0.9, a) == ("veto", None)


def test_degraded_passthrough_untouched():
    assert apply_guardrails("degraded", None, []) == ("degraded", None)


# ── quant normalization ──────────────────────────────────────────────────────
@pytest.mark.parametrize("score,strategy,expected", [
    (100.0, "premarket", 1.0),
    (78.0, "eod", 0.78),
    (0.0, "eod", 0.0),
    (4.0, "vol_weighted", 0.9),     # flow scale: (4+5)/10
    (-3.0, "momentum", 0.2),        # bearish flow score → low normalized
    (-50.0, "momentum", 0.0),       # clamp low
    (500.0, "premarket", 1.0),      # clamp high
])
def test_normalize_quant(score, strategy, expected):
    assert normalize_quant(score, strategy) == pytest.approx(expected)
