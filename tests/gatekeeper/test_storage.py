"""Phase C storage (spec §7): append-only gate_decisions + gate_evidence.
Idempotent DDL; re-persisting appends a new decision (never mutates)."""
from data.db import connect
from research.gatekeeper import storage
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)


def _decision():
    results = [StageResult("min_sample", Verdict.PASS, {"n_overall": 500}, {}),
               StageResult("confidence_interval", Verdict.WATCH,
                           {"lo": 0.32, "hi": 2.06}, {"promotion_bar_pct": 0.5})]
    return GateDecision(
        final_state=FinalState.WATCHLIST, failing_stage=None, stage_results=results,
        candidate_hash="cand123", config_hash="cfg456",
        dataset_fingerprint="fp789", git_commit="abc", seed=20260711,
        forward_test_rule=None, run_id="run1", strategy_fn="NR7 Breakout")


def test_ensure_gate_tables_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_gate_tables(conn)
    storage.ensure_gate_tables(conn)          # must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"gate_decisions", "gate_evidence"} <= tables
    conn.close()


def test_persist_writes_one_decision_and_one_evidence_row_per_stage(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_gate_tables(conn)
    d = _decision()
    decision_id = storage.persist_decision(conn, d)
    assert conn.execute("SELECT COUNT(*) FROM gate_decisions").fetchone()[0] == 1
    ev = conn.execute("SELECT COUNT(*) FROM gate_evidence WHERE decision_id=?",
                      (decision_id,)).fetchone()[0]
    assert ev == len(d.stage_results)
    row = conn.execute("SELECT final_state, strategy_fn, config_hash, "
                       "dataset_fingerprint FROM gate_decisions").fetchone()
    assert row == (FinalState.WATCHLIST, "NR7 Breakout", "cfg456", "fp789")
    conn.close()


def test_persist_is_append_only(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_gate_tables(conn)
    d = _decision()
    id1 = storage.persist_decision(conn, d)
    id2 = storage.persist_decision(conn, d)     # same decision, persisted again
    assert id1 != id2                            # new row, not an update
    assert conn.execute("SELECT COUNT(*) FROM gate_decisions").fetchone()[0] == 2
    conn.close()
