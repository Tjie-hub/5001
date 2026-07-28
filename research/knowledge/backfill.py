"""Phase E backfill (spec §8). Seed the two live hypotheses and back-link their
existing evidence by strategy_fn. Idempotent: safe to re-run (record_hypothesis is
guarded, links + failures dedupe). Broader historical backfill is deferred."""
from __future__ import annotations

from research.knowledge import ingest, storage
from research.knowledge.models import Hypothesis, Status

# strategy_fn (as written in gate_decisions/regime_profiles) -> hypothesis_id
_STRATEGY_TO_HYPOTHESIS = {"NR7 Breakout": "NR7_BULL_v1"}

_SEED_HYPOTHESES = [
    Hypothesis(hypothesis_id="NR7_BULL_v1", title="NR7 BULL breakout edge",
               rationale="BULL-regime NR7 breakout; liquidity-conditional (Phase D).",
               origin="manual", status=Status.REJECTED),
    Hypothesis(hypothesis_id="NR7_BULL_LOWLIQ_v1",
               title="NR7 BULL edge conditioned on LOW liquidity",
               rationale="BULL AND LOW_LIQ sub-cell (+2.29% vs -0.47% HIGH_LIQ).",
               origin="regime_scan", status=Status.FORWARD_TESTING,
               prereg_ref="docs/superpowers/specs/2026-07-12-prereg-nr7-bull-lowliq-v1.md"),
]


def _record_if_absent(conn, hyp):
    if storage.get_hypothesis(conn, hyp.hypothesis_id) is None:
        storage.record_hypothesis(conn, hyp)


def _link_by_strategy(conn, table, source_pk):
    """Link every row of `table` to the hypothesis its strategy_fn maps to."""
    for source_id, strategy_fn in conn.execute(
            f"SELECT {source_pk}, strategy_fn FROM {table}").fetchall():
        hyp = _STRATEGY_TO_HYPOTHESIS.get(strategy_fn)
        if hyp:
            storage.add_link(conn, hyp, table, source_id)


def seed_known_hypotheses(conn) -> dict:
    """Seed the live hypotheses, link their gate_decisions/regime_profiles, ingest
    their gate REJECTs as failures, and add one manual failure seed. Returns a
    small summary. Idempotent."""
    for hyp in _SEED_HYPOTHESES:
        _record_if_absent(conn, hyp)
    _link_by_strategy(conn, "gate_decisions", "decision_id")
    _link_by_strategy(conn, "regime_profiles", "profile_id")
    ingest.ingest_gate_rejects(
        conn, resolve=lambda row: _STRATEGY_TO_HYPOTHESIS.get(row["strategy_fn"]))
    # one manual failure seed (flow-edge study — predates the gate)
    ingest.record_failure(conn, None, "flow edge: no edge (mega+mid caps)",
                          fingerprint="flow_edge_study_2026-07-07")
    return {"hypotheses": conn.execute(
        "SELECT COUNT(*) FROM hypotheses").fetchone()[0]}
