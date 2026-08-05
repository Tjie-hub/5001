"""AF-2 ADR-AF-003 — B2 regression test.

Reproduces the exact scenario `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md` documents as a
confirmed, currently-shipped defect before this change: `EDGE_SCORE_MODE=enforce` AND the Agent
Firm both active for the same candidate. Before the fix, `run_agent_firm_gate()`'s unconditional
write silently discarded `run_edge_veto_stage()`'s deterministic `size_mult`/`edge_score` —
replacing a computed, validated value with either the LLM's own hint or a blind default of 1.0.

This test proves that no longer happens: the final `agent_size_hint` is a function of BOTH
`edge_score` and the Agent Firm's `size_tier`, computed by exactly one call to
`engine.position_sizing.resolve_size_hint()` (via `resolve_agent_size_hints()`), never a second
write clobbering a first.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

import scheduler.scanner as scanner_mod


class _FakeConn:
    """Minimal stand-in for db_connect(DB_PATH) — only what run_edge_veto_stage() touches."""

    def execute(self, sql, *a, **k):
        return self

    def fetchone(self):
        return (0,)  # open_positions_count

    def close(self):
        pass


def _make_signal(ticker):
    return {"ticker": ticker, "strategies": ["vol_weighted"],
            "flow": {"score": 3.0, "verdict": "BULLISH", "confirmed": True}}


def _run_full_pipeline(ticker, edge_score, agent_decision):
    """Mirrors scheduled_multi_strategy_scan()'s real call order: edge-veto stage ->
    agent-firm gate -> resolve_agent_size_hints() — the exact sequence the ADR's evidence
    table names as the collision site."""
    sig = _make_signal(ticker)
    intersection_results = [sig]
    flow_confirmed = [sig]

    survivor = {"ticker": ticker, "edge_score": edge_score, "size_mult": round(edge_score, 2)}

    with patch.object(scanner_mod, "db_connect", lambda *a, **k: _FakeConn()), \
         patch("config.edge_mode", lambda: "enforce"), \
         patch("engine.edge_enrich.market_regime", lambda conn: "BULL"), \
         patch("engine.edge_enrich.enrich_candidate",
               lambda conn, tkr, date_str, **kw: {"ticker": tkr}), \
         patch("engine.veto.apply_vetoes", lambda candidates, mreg, open_n: [survivor]):
        intersection_results, flow_confirmed = scanner_mod.run_edge_veto_stage(
            intersection_results, flow_confirmed, {}, "2026-07-29", "10:00",
        )

    assert intersection_results and intersection_results[0]["ticker"] == ticker
    assert intersection_results[0]["edge_score"] == edge_score
    assert "agent_size_hint" not in intersection_results[0], (
        "run_edge_veto_stage() must not write agent_size_hint itself (ADR-AF-003)"
    )

    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(side_effect=lambda c, **k: [agent_decision])
    mock_cfg = MagicMock()
    mock_cfg.is_active = MagicMock(return_value=True)
    mock_cfg.get_enforce = MagicMock(return_value=False)  # shadow: doesn't filter

    import engine.agent_firm as _pkg
    import paper_trade as _pt
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", mock_cfg), \
         patch.object(scanner_mod, "DB_PATH", ":memory:"), \
         patch.object(_pt, "DB_PATH", ":memory:"), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm": mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }):
        flow_confirmed = scanner_mod.run_agent_firm_gate(
            intersection_results, flow_confirmed, "2026-07-29", "10:00",
        )

    assert "agent_size_hint" not in flow_confirmed[0], (
        "run_agent_firm_gate() must not write agent_size_hint itself (ADR-AF-003)"
    )

    scanner_mod.resolve_agent_size_hints(flow_confirmed)
    return flow_confirmed[0]


@pytest.mark.parametrize("edge_score,tier,expected", [
    (0.8, "normal", 0.8),     # both present, normal tier -> edge_score unchanged
    (0.8, "reduce", 0.56),    # both present, reduce tier -> edge_score * 0.7
    (0.8, "increase", 0.92),  # both present, increase tier -> edge_score * 1.15
])
def test_b2_both_modes_active_neither_signal_discarded(edge_score, tier, expected):
    """The exact ADR-AF-003 collision scenario: EDGE_SCORE_MODE=enforce AND Agent Firm both
    active for the same ticker. The final agent_size_hint must reflect BOTH signals, not
    silently discard the computed edge_score in favor of the LLM's own hint alone."""
    decision = MagicMock(ticker="COLLIDE", decision="approve", size_tier=tier)
    row = _run_full_pipeline("COLLIDE", edge_score, decision)
    assert row["agent_size_hint"] == pytest.approx(expected, abs=0.01)


def test_b2_agent_firm_does_not_approve_edge_score_alone_survives():
    """Old bug's second failure mode: when Agent Firm does NOT approve (veto/degraded/not
    evaluated), the old code wrote a blind default of 1.0, discarding a validated edge score
    that says otherwise. Must now return the edge_score directly (only-edge_score branch)."""
    decision = MagicMock(ticker="COLLIDE", decision="veto", size_tier=None)
    row = _run_full_pipeline("COLLIDE", 0.73, decision)
    assert row["agent_size_hint"] == 0.73, (
        "a vetoed/no-tier candidate must fall through to the only-edge_score branch, "
        "not the old blind default of 1.0 that discarded the computed edge score"
    )


def test_b2_regression_guard_no_blind_default_when_edge_score_present():
    """Directly encodes the ADR's own words: 'discarding a computed, validated edge score in
    favor of a value that encodes no information at all' must no longer be possible when
    edge_score is present, regardless of what Agent Firm decided."""
    for tier in (None, "reduce", "normal", "increase"):
        decision = MagicMock(ticker="COLLIDE", decision="approve" if tier else "veto", size_tier=tier)
        row = _run_full_pipeline("COLLIDE", 0.65, decision)
        assert row["agent_size_hint"] != 1.0 or tier == "normal", (
            f"tier={tier}: result must be derived from edge_score=0.65, not the old blind "
            f"default, unless the derived value coincidentally equals 1.0"
        )
