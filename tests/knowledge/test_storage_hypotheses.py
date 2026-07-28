"""Phase E storage — schema idempotency + hypotheses writes (spec §4.1)."""
import pytest

from data.db import connect
from research.knowledge import storage
from research.knowledge.models import Hypothesis, Status


def test_ensure_knowledge_tables_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.ensure_knowledge_tables(conn)          # must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"hypotheses", "hypothesis_links", "failure_registry"} <= tables
    conn.close()


def test_record_and_get_hypothesis(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(
        hypothesis_id="NR7_BULL_v1", title="NR7 BULL edge", rationale="liq-conditional"))
    row = storage.get_hypothesis(conn, "NR7_BULL_v1")
    assert row["hypothesis_id"] == "NR7_BULL_v1"
    assert row["status"] == "PROPOSED"
    assert row["rationale"] == "liq-conditional"
    assert row["proposed_at"]                       # auto-stamped
    conn.close()


def test_record_duplicate_hypothesis_id_raises(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    with pytest.raises(Exception):
        storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="b"))
    conn.close()


def test_set_status_updates_valid_value(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    storage.set_status(conn, "H1", Status.REJECTED)
    assert storage.get_hypothesis(conn, "H1")["status"] == "REJECTED"
    conn.close()


def test_set_status_rejects_out_of_vocabulary(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    storage.record_hypothesis(conn, Hypothesis(hypothesis_id="H1", title="a"))
    with pytest.raises(ValueError):
        storage.set_status(conn, "H1", "BOGUS")
    conn.close()
