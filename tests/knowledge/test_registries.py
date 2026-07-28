"""Phase E registries as query views (spec §9): no new storage, stable read API."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import registries
from research.tracking import ensure_research_runs_table


def test_experiment_registry_reads_research_runs(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    ensure_research_runs_table(conn)
    conn.execute("INSERT INTO research_runs (run_id, kind, started_at, status) "
                 "VALUES ('run1','nr7','2026-07-14','ok')")
    conn.commit()
    rows = registries.experiment_registry(conn)
    assert [r["run_id"] for r in rows] == ["run1"]
    conn.close()


def test_validation_archive_and_evidence_archive(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.WATCHLIST, failing_stage=None,
                     stage_results=[StageResult("min_sample", Verdict.PASS, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id="run1",
                     strategy_fn="NR7 Breakout")
    dec_id = gk.persist_decision(conn, d)
    assert [r["decision_id"] for r in registries.validation_archive(conn)] == [dec_id]
    ev = registries.evidence_archive(conn, decision_id=dec_id)
    assert ev and ev[0]["stage"] == "min_sample"
    conn.close()
