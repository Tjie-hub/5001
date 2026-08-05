"""Tests for the deterministic Risk-decision guardrails."""
import pytest

from engine.agent_firm.guardrails import (
    apply_guardrails, build_consensus_summary, normalize_quant,
)
from engine.agent_firm.schemas import AgentResult, PortfolioContext, RiskContext


def _r(role, output, status="ok"):
    return AgentResult(role=role, status=status, output=output)


def _analysts(flow=None, tech=None, regime=None, news=None):
    out = []
    if flow is not None:
        out.append(_r("flow", flow))
    if tech is not None:
        out.append(_r("technical", tech))
    if regime is not None:
        out.append(_r("regime", regime))
    if news is not None:
        out.append(_r("news", news))
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


# ── WP4a: build_consensus_summary() ──────────────────────────────────────────
def test_consensus_counts_negative_and_positive_verdicts():
    a = _analysts(tech={"verdict": "BEARISH"}, flow={"flow_verdict": "NEUTRAL"},
                  regime={"regime_call": "BEAR"}, news={"sentiment": "BEARISH"})
    c = build_consensus_summary(a, "TEST")
    assert c.negative_count == 3
    assert c.positive_count == 0
    assert c.aligned_bullish == 0
    assert c.already_open_position is False
    assert c.entries_blocked is False


def test_consensus_counts_positive_verdicts_and_mirrors_aligned_bullish():
    a = _analysts(tech={"verdict": "BULLISH"}, flow={"flow_verdict": "ACCUMULATING"},
                  regime={"regime_call": "BULL"}, news={"sentiment": "BULLISH"})
    c = build_consensus_summary(a, "TEST")
    assert c.negative_count == 0
    assert c.positive_count == 4
    assert c.aligned_bullish == 4


def test_consensus_neutral_and_missing_analysts_count_toward_neither():
    a = _analysts(tech={"verdict": "NEUTRAL"})  # flow/regime/news missing entirely
    c = build_consensus_summary(a, "TEST")
    assert c.negative_count == 0
    assert c.positive_count == 0


def test_consensus_already_open_position_true():
    portfolio = PortfolioContext(open_trades=[{"ticker": "BBCA"}], open_position_count=1)
    c = build_consensus_summary([], "BBCA", portfolio_ctx=portfolio)
    assert c.already_open_position is True


def test_consensus_already_open_position_false_for_different_ticker():
    portfolio = PortfolioContext(open_trades=[{"ticker": "BBCA"}], open_position_count=1)
    c = build_consensus_summary([], "TLKM", portfolio_ctx=portfolio)
    assert c.already_open_position is False


def test_consensus_entries_blocked_reflects_risk_context():
    c = build_consensus_summary([], "TEST", risk_ctx=RiskContext(entries_blocked=True))
    assert c.entries_blocked is True


def test_consensus_defaults_when_contexts_omitted():
    c = build_consensus_summary([], "TEST")
    assert c.already_open_position is False
    assert c.entries_blocked is False


# ── WP4b: K1 — three or more negative analyst verdicts ───────────────────────
def test_k1_vetoes_on_three_negative_verdicts():
    # flow NEUTRAL keeps guardrail #1 (bearish-flow-not-offset) from preempting K1.
    a = _analysts(tech={"verdict": "BEARISH"}, flow={"flow_verdict": "NEUTRAL"},
                  regime={"regime_call": "BEAR"}, news={"sentiment": "BEARISH"})
    consensus = build_consensus_summary(a, "TEST")
    decision, reason = apply_guardrails("approve", 0.6, a, consensus=consensus)
    assert decision == "veto"
    assert "K1" in reason


def test_k1_survives_with_only_two_negative_verdicts():
    a = _analysts(tech={"verdict": "BEARISH"}, flow={"flow_verdict": "NEUTRAL"},
                  regime={"regime_call": "BEAR"}, news={"sentiment": "NEUTRAL"})
    consensus = build_consensus_summary(a, "TEST")
    assert apply_guardrails("approve", 0.6, a, consensus=consensus) == ("approve", None)


# ── WP4b: K2 — candidate already has an open position ────────────────────────
def test_k2_vetoes_when_candidate_already_open():
    a = _analysts(tech={"verdict": "BULLISH"}, flow={"flow_verdict": "ACCUMULATING"},
                  regime={"regime_call": "BULL"}, news={"sentiment": "BULLISH"})
    portfolio = PortfolioContext(open_trades=[{"ticker": "BBCA"}], open_position_count=1)
    consensus = build_consensus_summary(a, "BBCA", portfolio_ctx=portfolio)
    decision, reason = apply_guardrails("approve", 0.9, a, consensus=consensus)
    assert decision == "veto"
    assert "K2" in reason


def test_k2_survives_when_candidate_not_open():
    a = _analysts(tech={"verdict": "BULLISH"}, flow={"flow_verdict": "ACCUMULATING"},
                  regime={"regime_call": "BULL"}, news={"sentiment": "BULLISH"})
    portfolio = PortfolioContext(open_trades=[{"ticker": "BBCA"}], open_position_count=1)
    consensus = build_consensus_summary(a, "TLKM", portfolio_ctx=portfolio)
    assert apply_guardrails("approve", 0.9, a, consensus=consensus) == ("approve", None)


# ── WP4b: backward compatibility ──────────────────────────────────────────────
def test_k1_k2_do_not_fire_when_consensus_omitted():
    """Pre-WP4 callers that never pass `consensus` must see unchanged behavior,
    even when the analyst verdicts would trigger K1 if a consensus were built."""
    a = _analysts(tech={"verdict": "BEARISH"}, flow={"flow_verdict": "NEUTRAL"},
                  regime={"regime_call": "BEAR"}, news={"sentiment": "BEARISH"})
    assert apply_guardrails("approve", 0.6, a) == ("approve", None)
