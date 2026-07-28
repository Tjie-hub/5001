"""Phase E ingest — auto-derive failures from gate REJECTs (idempotent) + manual
channel (spec §5). Uses the real gatekeeper storage to build a gate_decisions row."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import ingest, storage


def _reject_decision(conn):
    gk.ensure_gate_tables(conn)
    results = [StageResult("walk_forward", Verdict.FAIL, {"consistency_pct": 46.8},
                           {"min_consistency_pct": 50})]
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=results, candidate_hash="c", config_hash="cfg",
                     dataset_fingerprint="fp", git_commit="g", seed=1,
                     forward_test_rule=None, run_id="run1", strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def test_ingest_gate_rejects_creates_failure_and_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _reject_decision(conn)
    n1 = ingest.ingest_gate_rejects(conn)
    assert n1 == 1
    n2 = ingest.ingest_gate_rejects(conn)               # re-run: nothing new
    assert n2 == 0
    row = conn.execute("SELECT source, failing_stage FROM failure_registry").fetchone()
    assert row == ("gate", "walk_forward")
    conn.close()


def test_ingest_links_failure_when_resolver_maps_hypothesis(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    dec_id = _reject_decision(conn)
    ingest.ingest_gate_rejects(conn, resolve=lambda row: "NR7_BULL_v1")
    # both the failure row and the gate decision are linked to the hypothesis
    tables = {r[0] for r in conn.execute(
        "SELECT source_table FROM hypothesis_links WHERE hypothesis_id='NR7_BULL_v1'")}
    assert tables == {"failure_registry", "gate_decisions"}
    fr = conn.execute("SELECT hypothesis_id, evidence_ref FROM failure_registry"
                      ).fetchone()
    assert fr == ("NR7_BULL_v1", dec_id)
    conn.close()


def test_record_failure_manual(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    fid = ingest.record_failure(conn, "FLOW", "no edge (mega+mid caps)")
    assert fid is not None
    row = conn.execute("SELECT source FROM failure_registry WHERE failure_id=?",
                       (fid,)).fetchone()
    assert row[0] == "manual"
    conn.close()
