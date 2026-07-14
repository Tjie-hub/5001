"""Phase E storage — idempotent link writer + failure insert (spec §4.2, §4.3)."""
from data.db import connect
from research.knowledge import storage
from research.knowledge.models import FailureRecord


def _conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    return conn


def test_add_link_inserts_once_and_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    lid = storage.add_link(conn, "H1", "gate_decisions", "dec1", "fp1")
    assert lid is not None
    again = storage.add_link(conn, "H1", "gate_decisions", "dec1", "fp1")
    assert again is None                                # dedup: no second row
    n = conn.execute("SELECT COUNT(*) FROM hypothesis_links").fetchone()[0]
    assert n == 1
    conn.close()


def test_add_link_distinguishes_source_rows(tmp_path):
    conn = _conn(tmp_path)
    storage.add_link(conn, "H1", "gate_decisions", "dec1")
    storage.add_link(conn, "H1", "research_runs", "run1")
    n = conn.execute("SELECT COUNT(*) FROM hypothesis_links").fetchone()[0]
    assert n == 2
    conn.close()


def test_insert_failure_and_dedupe_by_fingerprint_stage(tmp_path):
    conn = _conn(tmp_path)
    f = FailureRecord(hypothesis_id="H1", reject_reason="gate REJECT at walk_forward",
                      source="gate", failing_stage="walk_forward",
                      evidence_ref="dec1", fingerprint="dec1")
    fid = storage.insert_failure(conn, f)
    assert fid is not None
    dup = storage.insert_failure(conn, f)               # same fingerprint+stage
    assert dup is None
    n = conn.execute("SELECT COUNT(*) FROM failure_registry").fetchone()[0]
    assert n == 1
    conn.close()


def test_insert_manual_failure_dedupe_by_reason(tmp_path):
    conn = _conn(tmp_path)
    f = FailureRecord(hypothesis_id="FLOW", reject_reason="no edge (mega+mid caps)",
                      source="manual")
    assert storage.insert_failure(conn, f) is not None
    assert storage.insert_failure(conn, f) is None      # same (hypothesis, reason)
    conn.close()
