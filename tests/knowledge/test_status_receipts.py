"""Phase E Task 11 (v3 amendment V3-4): receipt-bound status transitions.
Promotion-track labels are structurally gated on gate_decisions receipts."""
import pytest

from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import storage
from research.knowledge.models import Hypothesis, Status


def _decision(conn, final_state, run_id="run1"):
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=final_state, failing_stage=None,
                     stage_results=[StageResult("min_sample", Verdict.PASS, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id=run_id,
                     strategy_fn="NR7 Breakout")
    return gk.persist_decision(conn, d)


def _seed(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    return conn


def test_forward_testing_requires_receipt(tmp_path):
    conn = _seed(tmp_path)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.FORWARD_TESTING)
    conn.close()


def test_forward_testing_accepts_promote_receipt_and_links_it(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.PROMOTE)
    storage.set_status(conn, "H1", Status.FORWARD_TESTING,
                       evidence_decision_id=dec_id)
    assert storage.get_hypothesis(conn, "H1")["status"] == "FORWARD_TESTING"
    row = conn.execute(
        "SELECT 1 FROM hypothesis_links WHERE hypothesis_id='H1' AND "
        "source_table='gate_decisions' AND source_id=?", (dec_id,)).fetchone()
    assert row is not None
    conn.close()


def test_forward_testing_rejects_non_promote_receipt(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.WATCHLIST)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.FORWARD_TESTING,
                           evidence_decision_id=dec_id)
    conn.close()


def test_validated_requires_promote_receipt_plus_forward_receipt(tmp_path):
    conn = _seed(tmp_path)
    dec_id = _decision(conn, FinalState.PROMOTE)
    with pytest.raises(ValueError):                     # no forward receipt
        storage.set_status(conn, "H1", Status.VALIDATED,
                           evidence_decision_id=dec_id)
    storage.set_status(conn, "H1", Status.VALIDATED, evidence_decision_id=dec_id,
                       forward_receipt="ft_go_2026-07-14")
    assert storage.get_hypothesis(conn, "H1")["status"] == "VALIDATED"
    conn.close()


def test_gated_status_rejects_unknown_decision_id(tmp_path):
    conn = _seed(tmp_path)
    gk.ensure_gate_tables(conn)
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", Status.VALIDATED,
                           evidence_decision_id="nope", forward_receipt="ft")
    conn.close()


def test_record_hypothesis_rejects_gated_initial_status(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    with pytest.raises(ValueError):
        storage.record_hypothesis(conn, Hypothesis(
            hypothesis_id="X", title="x", status=Status.VALIDATED))
    with pytest.raises(ValueError):
        storage.record_hypothesis(conn, Hypothesis(
            hypothesis_id="Y", title="y", status=Status.FORWARD_TESTING))
    conn.close()


def test_status_debt_grandfather_allows_seeded_forward_testing(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(
        hypothesis_id="NR7_BULL_LOWLIQ_v1", title="grandfathered",
        status=Status.FORWARD_TESTING))                 # in _STATUS_DEBT
    assert (storage.get_hypothesis(conn, "NR7_BULL_LOWLIQ_v1")["status"]
            == "FORWARD_TESTING")
    conn.close()
