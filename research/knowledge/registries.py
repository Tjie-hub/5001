"""Phase E registries (spec §9): the Experiment Registry, Validation Archive and
Evidence Archive are query VIEWS over existing research tables — no duplicated
storage. Stable read API for Phase F/G."""
from __future__ import annotations


def _dicts(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def experiment_registry(conn, kind=None) -> list:
    """Every research run (optionally filtered by kind)."""
    if kind:
        return _dicts(conn.execute(
            "SELECT * FROM research_runs WHERE kind=? ORDER BY started_at", (kind,)))
    return _dicts(conn.execute("SELECT * FROM research_runs ORDER BY started_at"))


def validation_archive(conn, final_state=None) -> list:
    """Every gate decision (optionally filtered by final_state)."""
    if final_state:
        return _dicts(conn.execute(
            "SELECT * FROM gate_decisions WHERE final_state=? ORDER BY decided_at",
            (final_state,)))
    return _dicts(conn.execute("SELECT * FROM gate_decisions ORDER BY decided_at"))


def evidence_archive(conn, decision_id=None) -> list:
    """Gate evidence rows, optionally scoped to one decision."""
    if decision_id:
        return _dicts(conn.execute(
            "SELECT * FROM gate_evidence WHERE decision_id=?", (decision_id,)))
    return _dicts(conn.execute("SELECT * FROM gate_evidence"))
