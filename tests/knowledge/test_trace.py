"""Phase E trace bundle + orphan report + status-consistency flag (spec §6, §7)."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import ingest, storage, trace
from research.knowledge.models import Hypothesis, Status


def _reject_decision(conn, run_id="run1"):
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=[StageResult("walk_forward", Verdict.FAIL, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id=run_id,
                     strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def test_trace_assembles_full_bundle(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="NR7_BULL_v1",
                                               title="NR7 BULL", status=Status.REJECTED))
    dec_id = _reject_decision(conn)
    ingest.ingest_gate_rejects(conn, resolve=lambda row: "NR7_BULL_v1")
    bundle = trace.trace(conn, "NR7_BULL_v1")
    assert bundle["hypothesis"]["hypothesis_id"] == "NR7_BULL_v1"
    assert [d["decision_id"] for d in bundle["decisions"]] == [dec_id]
    assert bundle["decisions"][0]["evidence"]                # gate_evidence attached
    assert len(bundle["failures"]) == 1
    conn.close()


def test_orphan_report_flags_unlinked_then_clears(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    dec_id = _reject_decision(conn)
    orphans = trace.orphan_report(conn)
    assert dec_id in orphans["gate_decisions"]
    storage.add_link(conn, "NR7_BULL_v1", "gate_decisions", dec_id)
    assert trace.orphan_report(conn)["gate_decisions"] == []
    conn.close()


def test_check_status_consistency_flags_validated_over_reject(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a",
                                               status=Status.VALIDATED))
    dec_id = _reject_decision(conn)
    storage.add_link(conn, "H1", "gate_decisions", dec_id)
    warnings = trace.check_status_consistency(conn, "H1")
    assert any("VALIDATED" in w and "REJECT" in w for w in warnings)
    conn.close()
