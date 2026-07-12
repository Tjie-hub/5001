"""The gate orchestrator (spec §3/§5).

`run_gate` builds the stage context from a candidate, folds the eight stages,
reduces them to one FinalState, and — with full provenance — persists the decision
(append-only) inside a research_runs envelope and optionally writes a report.

Pure w.r.t. production: writes only research tables + an optional results doc.
Deterministic: the statistical evidence depends only on (candidate, config, seed);
only the run_id (a fresh provenance handle) varies between runs.
"""
from __future__ import annotations

from data.db import connect
from research import tracking
from research.gatekeeper import report as _report
from research.gatekeeper import stages
from research.gatekeeper.candidate import build_ctx, candidate_hash
from research.gatekeeper.config import config_hash
from research.gatekeeper.decision import decide
from research.gatekeeper.models import FinalState, GateDecision
from research.gatekeeper.storage import ensure_gate_tables, persist_decision

DB_PATH = tracking.DB_PATH


def run_gate(candidate, config, db_path: str = None, report_path: str = None,
             persist: bool = True) -> GateDecision:
    db_path = db_path or DB_PATH

    ctx = build_ctx(candidate, config)
    results = [stage(ctx, config) for stage in stages.PIPELINE]
    final_state, failing = decide(results, config)
    ftr = dict(config.forward_test_rule) if final_state == FinalState.PROMOTE else None

    conn = connect(db_path)
    try:
        fingerprint = tracking.dataset_fingerprint(conn)["sha256"]
    except Exception:
        fingerprint = None

    decision = GateDecision(
        final_state=final_state, failing_stage=failing, stage_results=results,
        candidate_hash=candidate_hash(candidate), config_hash=config_hash(config),
        dataset_fingerprint=fingerprint, git_commit=tracking.git_commit(),
        seed=config.seed, forward_test_rule=ftr, run_id=None,
        strategy_fn=candidate.strategy_fn)

    if persist:
        with tracking.track_run(
                "gate-eval",
                params={"strategy": candidate.strategy_fn,
                        "config_hash": decision.config_hash},
                db_path=db_path) as run:
            run.metrics = {"final_state": final_state, "failing_stage": failing}
            decision.run_id = run.run_id
        ensure_gate_tables(conn)
        persist_decision(conn, decision)
    conn.close()

    if report_path:
        _report.write_report(decision, report_path)
    return decision
