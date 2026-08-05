"""AF-2 ADR-AF-003 — engine.position_sizing.resolve_size_hint(): the sole authority for
agent_size_hint. Exhaustive precedence-path + boundary-case coverage (no `hypothesis`
dependency, per AF2_TEST_STRATEGY.md's own documented constraint — a small, enumerable matrix
achieves the same coverage without adding a new test dependency).
"""
import pytest

from engine.position_sizing import (
    DEFAULT_SIZE_HINT,
    MAX_SIZE_HINT,
    MIN_SIZE_HINT,
    resolve_size_hint,
)


# ── Precedence path 1: neither edge_score nor size_tier present ──────────────────────

def test_neither_present_returns_default():
    assert resolve_size_hint(edge_score=None, size_tier=None) == DEFAULT_SIZE_HINT == 1.0


def test_neither_present_ignores_consensus_and_execution():
    """consensus/execution are accepted per the ADR's declared signature but are not combined
    into the precedence rule — passing them must not change the neither-present outcome."""
    assert resolve_size_hint(
        edge_score=None, size_tier=None, consensus=object(), execution=object(),
    ) == DEFAULT_SIZE_HINT


# ── Precedence path 2: only edge_score present (Agent Firm inactive/degraded/vetoed) ─

@pytest.mark.parametrize("edge_score,expected", [
    (0.0, 0.0),
    (0.42, 0.42),
    (0.777, 0.78),   # rounding to 2 dp
    (1.0, 1.0),
])
def test_only_edge_score_returned_directly(edge_score, expected):
    assert resolve_size_hint(edge_score=edge_score, size_tier=None) == expected


def test_only_edge_score_clamped_above_max():
    """edge_score should never exceed MAX_SIZE_HINT in practice (compute_edge() is a weighted
    [0,1] sum) — but the resolver clamps defensively regardless, per the ADR's 'bounded [0.0,
    1.5] by construction' contract."""
    assert resolve_size_hint(edge_score=2.5, size_tier=None) == MAX_SIZE_HINT


def test_only_edge_score_clamped_below_min():
    assert resolve_size_hint(edge_score=-0.5, size_tier=None) == MIN_SIZE_HINT


# ── Precedence path 3: only size_tier present (EDGE_SCORE_MODE=off) ──────────────────

@pytest.mark.parametrize("tier,expected", [
    ("reduce", 0.5),
    ("normal", 1.0),
    ("increase", 1.2),
])
def test_only_size_tier_maps_to_fixed_base_value(tier, expected):
    assert resolve_size_hint(edge_score=None, size_tier=tier) == expected


def test_only_size_tier_unrecognized_value_falls_back_to_default():
    """Fail-soft: an unrecognized tier string is treated as the neutral case, matching this
    repo's existing convention (unrecognized enum value -> neutral), not a raise."""
    assert resolve_size_hint(edge_score=None, size_tier="aggressive") == DEFAULT_SIZE_HINT


# ── Precedence path 4: both present — edge_score is the base, size_tier modulates ────

@pytest.mark.parametrize("edge_score,tier,expected", [
    (1.0, "reduce", 0.7),      # 1.0 * 0.7
    (1.0, "normal", 1.0),      # 1.0 * 1.0
    (1.0, "increase", 1.15),   # 1.0 * 1.15
    (0.5, "reduce", 0.35),     # 0.5 * 0.7
    (0.5, "increase", 0.57),   # 0.5 * 1.15 = 0.575 -> round(0.575, 2) == 0.57 in Python
                               # (0.575 has no exact binary representation, so it rounds down)
])
def test_both_present_edge_score_modulated_by_tier(edge_score, tier, expected):
    result = resolve_size_hint(edge_score=edge_score, size_tier=tier)
    # Use approx for the one case with a rounding ambiguity (Python's round-half-to-even).
    assert result == pytest.approx(expected, abs=0.01)


def test_both_present_clamped_at_max_when_modulation_would_exceed_1_5():
    """A high edge_score with 'increase' modulation must not exceed MAX_SIZE_HINT."""
    assert resolve_size_hint(edge_score=1.4, size_tier="increase") == MAX_SIZE_HINT


def test_both_present_neither_signal_silently_discarded():
    """The core ADR-AF-003 guarantee: with both inputs present, the output is a function of
    BOTH — changing either input changes the output. Neither is a blind default that ignores
    the other."""
    base = resolve_size_hint(edge_score=0.8, size_tier="normal")
    reduced = resolve_size_hint(edge_score=0.8, size_tier="reduce")
    increased = resolve_size_hint(edge_score=0.8, size_tier="increase")
    assert reduced < base < increased
    # Same tier, different edge_score also changes the output.
    higher_edge = resolve_size_hint(edge_score=0.95, size_tier="normal")
    assert higher_edge > base


def test_both_present_unrecognized_tier_falls_back_to_normal_modulation():
    result = resolve_size_hint(edge_score=0.6, size_tier="aggressive")
    assert result == resolve_size_hint(edge_score=0.6, size_tier="normal")


# ── Output bounds — every path, exhaustively ─────────────────────────────────────────

@pytest.mark.parametrize("edge_score,size_tier", [
    (None, None), (0.5, None), (None, "reduce"), (None, "normal"), (None, "increase"),
    (0.5, "reduce"), (0.5, "normal"), (0.5, "increase"),
    (0.0, "reduce"), (1.0, "increase"), (1.5, "increase"), (-1.0, "reduce"),
])
def test_output_always_within_bounds(edge_score, size_tier):
    result = resolve_size_hint(edge_score=edge_score, size_tier=size_tier)
    assert MIN_SIZE_HINT <= result <= MAX_SIZE_HINT


def test_default_size_hint_constant_matches_pre_adr_default():
    """The pre-existing default (1.0), preserved, not silently changed — ADR-AF-003 explicitly
    requires this."""
    assert DEFAULT_SIZE_HINT == 1.0
