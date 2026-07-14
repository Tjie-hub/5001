"""Phase E trace + orphan detection (spec §6, §7). All joins go through
hypothesis_links so the source tables are never altered."""
from __future__ import annotations

from research.knowledge.config import load_config
from research.knowledge.storage import get_hypothesis

# PK column for each linkable source table.
_PK = {"research_runs": "run_id", "gate_decisions": "decision_id",
       "regime_profiles": "profile_id", "failure_registry": "failure_id"}


def _rows(conn, table, ids):
    """Fetch rows of `table` whose PK is in `ids`, as dicts."""
    if not ids:
        return []
    pk = _PK[table]
    marks = ",".join("?" * len(ids))
    cur = conn.execute(f"SELECT * FROM {table} WHERE {pk} IN ({marks})", tuple(ids))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _linked_ids(conn, hypothesis_id, source_table):
    return [r[0] for r in conn.execute(
        "SELECT source_id FROM hypothesis_links WHERE hypothesis_id=? AND "
        "source_table=?", (hypothesis_id, source_table)).fetchall()]


def trace(conn, hypothesis_id) -> dict:
    """Assemble the full evidence bundle for one hypothesis."""
    decisions = _rows(conn, "gate_decisions",
                      _linked_ids(conn, hypothesis_id, "gate_decisions"))
    for d in decisions:
        ev = conn.execute("SELECT stage, verdict, statistic_json, threshold_json "
                          "FROM gate_evidence WHERE decision_id=?",
                          (d["decision_id"],)).fetchall()
        d["evidence"] = [{"stage": s, "verdict": v, "statistic_json": sj,
                          "threshold_json": tj} for s, v, sj, tj in ev]
    return {
        "hypothesis": get_hypothesis(conn, hypothesis_id),
        "experiments": _rows(conn, "research_runs",
                             _linked_ids(conn, hypothesis_id, "research_runs")),
        "decisions": decisions,
        "regime_profiles": _rows(conn, "regime_profiles",
                                 _linked_ids(conn, hypothesis_id, "regime_profiles")),
        "failures": _rows(conn, "failure_registry",
                          _linked_ids(conn, hypothesis_id, "failure_registry")),
    }


def _table_exists(conn, table) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone() is not None


def orphan_report(conn, scope=None) -> dict:
    """Every row in the orphan-scope tables with no hypothesis_links entry. Advisory
    — this operationalizes 'no orphan experiments' (spec §6). Missing tables yield []."""
    scope = scope or load_config().orphan_scope
    out = {}
    for table in scope:
        if not _table_exists(conn, table):
            out[table] = []
            continue
        pk = _PK[table]
        ids = [r[0] for r in conn.execute(
            f"SELECT {pk} FROM {table} WHERE {pk} NOT IN "
            f"(SELECT source_id FROM hypothesis_links WHERE source_table=?)",
            (table,)).fetchall()]
        out[table] = ids
    return out


def check_status_consistency(conn, hypothesis_id) -> list:
    """Advisory contradictions between declared status and linked evidence (spec §7)."""
    hyp = get_hypothesis(conn, hypothesis_id)
    if hyp is None:
        return [f"unknown hypothesis {hypothesis_id!r}"]
    warnings = []
    linked_dec_ids = _linked_ids(conn, hypothesis_id, "gate_decisions")
    states = [r[0] for r in _rows_states(conn, linked_dec_ids)]
    if hyp["status"] == "VALIDATED" and "REJECT" in states:
        warnings.append("status=VALIDATED but a linked gate_decision=REJECT")
    if hyp["status"] == "REJECTED" and not _linked_ids(
            conn, hypothesis_id, "failure_registry"):
        warnings.append("status=REJECTED but no linked failure row")
    return warnings


def _rows_states(conn, decision_ids):
    if not decision_ids:
        return []
    marks = ",".join("?" * len(decision_ids))
    return conn.execute(
        f"SELECT final_state FROM gate_decisions WHERE decision_id IN ({marks})",
        tuple(decision_ids)).fetchall()
