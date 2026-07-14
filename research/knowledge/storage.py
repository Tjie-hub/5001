"""Phase E persistence (spec §4). Three tables in walkforward.db, created
idempotently. Evidence tables (hypothesis_links, failure_registry) are strictly
append-only: no UPDATE, no DELETE. `hypotheses` is append-only EXCEPT its
status/notes_json label columns (spec §4.1, §7). Production may READ; only
research/ WRITES (CI-fenced by tests/test_research_data_fence.py)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from research.knowledge.models import Status

HYPOTHESES_DDL = """
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id       TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    rationale           TEXT,
    origin              TEXT,
    status              TEXT NOT NULL,
    dataset_fingerprint TEXT,
    config_hash         TEXT,
    git_commit          TEXT,
    prereg_ref          TEXT,
    proposed_at         TEXT NOT NULL,
    notes_json          TEXT
)
"""

HYPOTHESIS_LINKS_DDL = """
CREATE TABLE IF NOT EXISTS hypothesis_links (
    link_id            TEXT PRIMARY KEY,
    hypothesis_id      TEXT NOT NULL,
    source_table       TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    source_fingerprint TEXT,
    linked_at          TEXT NOT NULL
)
"""

FAILURE_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS failure_registry (
    failure_id     TEXT PRIMARY KEY,
    hypothesis_id  TEXT,
    reject_reason  TEXT NOT NULL,
    failing_stage  TEXT,
    source         TEXT NOT NULL,
    evidence_ref   TEXT,
    fingerprint    TEXT,
    recorded_at    TEXT NOT NULL
)
"""

_VALID_STATUSES = {s.value for s in Status}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_knowledge_tables(conn) -> None:
    conn.execute(HYPOTHESES_DDL)
    conn.execute(HYPOTHESIS_LINKS_DDL)
    conn.execute(FAILURE_REGISTRY_DDL)
    conn.commit()


def record_hypothesis(conn, hyp) -> str:
    """Insert one hypotheses row. Raises if the hypothesis_id already exists
    (append-only identity — no silent overwrite). Returns the hypothesis_id."""
    status = hyp.status.value if isinstance(hyp.status, Status) else str(hyp.status)
    if status not in _VALID_STATUSES:
        raise ValueError(f"invalid status {status!r}; allowed {_VALID_STATUSES}")
    conn.execute(
        "INSERT INTO hypotheses (hypothesis_id, title, rationale, origin, status, "
        "dataset_fingerprint, config_hash, git_commit, prereg_ref, proposed_at, "
        "notes_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (hyp.hypothesis_id, hyp.title, hyp.rationale, hyp.origin, status,
         hyp.dataset_fingerprint, hyp.config_hash, hyp.git_commit, hyp.prereg_ref,
         hyp.proposed_at or _now(),
         json.dumps(hyp.notes) if hyp.notes else None))
    conn.commit()
    return hyp.hypothesis_id


def get_hypothesis(conn, hypothesis_id):
    """Return the hypotheses row as a dict, or None."""
    cur = conn.execute("SELECT * FROM hypotheses WHERE hypothesis_id=?",
                       (hypothesis_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def set_status(conn, hypothesis_id, status) -> None:
    """The one sanctioned mutation (spec §4.1/§7): update a hypothesis's label."""
    value = status.value if isinstance(status, Status) else str(status)
    if value not in _VALID_STATUSES:
        raise ValueError(f"invalid status {value!r}; allowed {_VALID_STATUSES}")
    conn.execute("UPDATE hypotheses SET status=? WHERE hypothesis_id=?",
                 (value, hypothesis_id))
    conn.commit()


def _link_exists(conn, hypothesis_id, source_table, source_id) -> bool:
    return conn.execute(
        "SELECT 1 FROM hypothesis_links WHERE hypothesis_id=? AND source_table=? "
        "AND source_id=? LIMIT 1",
        (hypothesis_id, source_table, source_id)).fetchone() is not None


def add_link(conn, hypothesis_id, source_table, source_id, source_fingerprint=None):
    """Append one hypothesis_links row unless (hypothesis_id, source_table,
    source_id) already exists. Returns the new link_id, or None if it was a dedup
    no-op — keeps the table append-only while making re-linking safe to re-run."""
    if _link_exists(conn, hypothesis_id, source_table, source_id):
        return None
    link_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO hypothesis_links (link_id, hypothesis_id, source_table, "
        "source_id, source_fingerprint, linked_at) VALUES (?,?,?,?,?,?)",
        (link_id, hypothesis_id, source_table, source_id, source_fingerprint, _now()))
    conn.commit()
    return link_id


def _failure_exists(conn, f) -> bool:
    if f.source == "gate":
        return conn.execute(
            "SELECT 1 FROM failure_registry WHERE source='gate' AND fingerprint=? "
            "AND IFNULL(failing_stage,'')=IFNULL(?,'') LIMIT 1",
            (f.fingerprint, f.failing_stage)).fetchone() is not None
    # manual: dedupe on (hypothesis_id, reject_reason) unless a fingerprint is given
    if f.fingerprint:
        return conn.execute(
            "SELECT 1 FROM failure_registry WHERE fingerprint=? LIMIT 1",
            (f.fingerprint,)).fetchone() is not None
    return conn.execute(
        "SELECT 1 FROM failure_registry WHERE IFNULL(hypothesis_id,'')=IFNULL(?,'') "
        "AND reject_reason=? LIMIT 1",
        (f.hypothesis_id, f.reject_reason)).fetchone() is not None


def insert_failure(conn, f):
    """Append one failure_registry row unless a matching one exists (dedup rule in
    _failure_exists). Returns the new failure_id, or None on a dedup no-op."""
    if _failure_exists(conn, f):
        return None
    failure_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO failure_registry (failure_id, hypothesis_id, reject_reason, "
        "failing_stage, source, evidence_ref, fingerprint, recorded_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (failure_id, f.hypothesis_id, f.reject_reason, f.failing_stage, f.source,
         f.evidence_ref, f.fingerprint, _now()))
    conn.commit()
    return failure_id
