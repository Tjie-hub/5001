"""engine/watchlist_ledger.py — the append-only, auditable record of what the
engine put in front of a human, and why.

WHY THIS EXISTS (audit 2026-09-02, findings A-1, A-2, F-1)
-----------------------------------------------------------
`watchlist_snapshot` is written with INSERT OR REPLACE keyed on
(date, strategy, ticker): a same-day re-run silently rewrote history. It also
stores no price, no timestamp, no exit rule and no strategy attribution, so
"what did we predict, and what happened?" was not answerable from the record --
the audit had to reconstruct outcomes from a separate price table.

This module adds the ledger that makes the EOD -> Premarket architecture
measurable:

  watchlist_snapshot_log  every row the engine ever published, append-only,
                          revision-numbered, with the decision price, the entry
                          rule, the attributing walk-forward strategy (when
                          there is one) and its OOS evidence AS OF THAT MOMENT.

  watchlist_revision      every Premarket change to the frozen EOD base plan --
                          RETAIN / REMOVE / ADD / UPGRADE / DOWNGRADE -- with a
                          reason code and the new information that justified it.

Both are protected by BEFORE UPDATE / BEFORE DELETE triggers that ABORT. History
cannot be rewritten, only appended to. `watchlist_snapshot` is kept as the
"current state" projection so existing readers and the Telegram diff keep
working unchanged; the log is the evidence.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

BASE_PLAN = "PLAN"                 # a published plan with >=1 candidate
BASE_EMPTY = "EMPTY_PLAN"          # the job ran and deliberately approved nobody
BASE_MISSING = "NO_EOD_SNAPSHOT"   # no publication exists at all

STRATEGY_EOD = "eod"
STRATEGY_PREMARKET = "premarket"

ACTION_RETAIN = "RETAIN"
ACTION_REMOVE = "REMOVE"
ACTION_ADD = "ADD"
ACTION_UPGRADE = "UPGRADE"
ACTION_DOWNGRADE = "DOWNGRADE"
ACTIONS = (ACTION_RETAIN, ACTION_REMOVE, ACTION_ADD, ACTION_UPGRADE,
           ACTION_DOWNGRADE)

SNAPSHOT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS watchlist_snapshot_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at   TEXT    NOT NULL,
    date          TEXT    NOT NULL,
    strategy      TEXT    NOT NULL,
    revision      INTEGER NOT NULL,
    ticker        TEXT    NOT NULL,
    rank          INTEGER NOT NULL,
    confidence    REAL,
    conviction    REAL,
    confluence    INTEGER,
    sources       TEXT,
    strategy_fn   TEXT,
    rule_id       TEXT,
    admission_path TEXT,
    wf_expectancy_pct REAL,
    wf_n_trades   INTEGER,
    wf_last_computed  TEXT,
    decision_price     REAL,
    decision_price_basis TEXT,
    entry_rule    TEXT,
    provenance    TEXT
)
"""

# A published plan with ZERO approved names writes no rows to
# watchlist_snapshot_log -- there is nothing to write, and fabricating a
# placeholder ticker row would corrupt every downstream count. But "we published
# nothing today" is a REAL prediction and must be as auditable as any other
# (audit P-3 2026-09-02 for wf_rule_study, then P-2 2026-09-03 here: on
# 2026-09-02 the EOD job approved 0 of 8 and the ledger came out empty, so the
# next Premarket could not tell an empty plan from a job that never ran).
#
# This manifest records every publication regardless of size, so absence of rows
# stops being ambiguous.
PUBLICATION_DDL = """
CREATE TABLE IF NOT EXISTS watchlist_publication (
    date         TEXT    NOT NULL,
    strategy     TEXT    NOT NULL,
    revision     INTEGER NOT NULL,
    recorded_at  TEXT    NOT NULL,
    n_rows       INTEGER NOT NULL,
    PRIMARY KEY (date, strategy, revision)
)
"""

REVISION_DDL = """
CREATE TABLE IF NOT EXISTS watchlist_revision (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at  TEXT NOT NULL,
    date         TEXT NOT NULL,
    base_date    TEXT,
    ticker       TEXT NOT NULL,
    action       TEXT NOT NULL,
    reason_code  TEXT NOT NULL,
    reason       TEXT NOT NULL,
    evidence     TEXT
)
"""

_TRIGGERS = (
    ("watchlist_snapshot_log_no_update", "watchlist_snapshot_log", "UPDATE",
     "watchlist_snapshot_log is append-only"),
    ("watchlist_snapshot_log_no_delete", "watchlist_snapshot_log", "DELETE",
     "watchlist_snapshot_log is append-only"),
    ("watchlist_publication_no_update", "watchlist_publication", "UPDATE",
     "watchlist_publication is append-only"),
    ("watchlist_publication_no_delete", "watchlist_publication", "DELETE",
     "watchlist_publication is append-only"),
    ("watchlist_revision_no_update", "watchlist_revision", "UPDATE",
     "watchlist_revision is append-only"),
    ("watchlist_revision_no_delete", "watchlist_revision", "DELETE",
     "watchlist_revision is append-only"),
)


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Idempotent DDL + the append-only triggers. Safe on every startup."""
    conn.execute(SNAPSHOT_LOG_DDL)
    conn.execute(PUBLICATION_DDL)
    conn.execute(REVISION_DDL)
    for name, table, event, msg in _TRIGGERS:
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {event} ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{msg}'); END"
        )
    conn.commit()


def next_revision(conn: sqlite3.Connection, date_str: str, strategy: str) -> int:
    ensure_tables(conn)
    a = conn.execute(
        "SELECT MAX(revision) FROM watchlist_snapshot_log "
        "WHERE date=? AND strategy=?", (date_str, strategy)).fetchone()[0]
    # An empty publication leaves no snapshot row but still consumed a revision
    # number; ignoring it would make the next publication reuse it.
    b = conn.execute(
        "SELECT MAX(revision) FROM watchlist_publication "
        "WHERE date=? AND strategy=?", (date_str, strategy)).fetchone()[0]
    return max(int(a or 0), int(b or 0)) + 1


def append_snapshot(conn: sqlite3.Connection, date_str: str, strategy: str,
                    ranked: list[dict[str, Any]],
                    *, recorded_at: Optional[str] = None) -> int:
    """Append one immutable revision of a published watchlist. Returns the
    revision number. An empty `ranked` still records a revision -- "we published
    nothing today" is itself a prediction and must be measurable."""
    ensure_tables(conn)
    rev = next_revision(conn, date_str, strategy)
    ts = recorded_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i, c in enumerate(ranked, 1):
        conn.execute(
            "INSERT INTO watchlist_snapshot_log "
            "(recorded_at, date, strategy, revision, ticker, rank, confidence, "
            " conviction, confluence, sources, strategy_fn, rule_id, "
            " admission_path, wf_expectancy_pct, wf_n_trades, wf_last_computed, "
            " decision_price, decision_price_basis, entry_rule, provenance) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, date_str, strategy, rev, c["ticker"], i,
             c.get("confidence"), c.get("conviction"), c.get("confluence"),
             json.dumps(c.get("sources") or []),
             c.get("strategy_fn"), c.get("rule_id"), c.get("admission_path"),
             c.get("wf_expectancy_pct"), c.get("wf_n_trades"),
             c.get("wf_last_computed"),
             c.get("decision_price"), c.get("decision_price_basis"),
             c.get("entry_rule"),
             json.dumps(c.get("provenance") or {}, default=str)),
        )
    conn.execute(
        "INSERT INTO watchlist_publication (date, strategy, revision, "
        " recorded_at, n_rows) VALUES (?,?,?,?,?)",
        (date_str, strategy, rev, ts, len(ranked)))
    conn.commit()
    return rev


def read_snapshot(conn: sqlite3.Connection, date_str: str, strategy: str,
                  revision: Optional[int] = None) -> list[dict[str, Any]]:
    """The published rows for one (date, strategy). Latest revision by default."""
    ensure_tables(conn)
    if revision is None:
        row = conn.execute(
            "SELECT MAX(revision) FROM watchlist_snapshot_log "
            "WHERE date=? AND strategy=?", (date_str, strategy)).fetchone()
        revision = row[0]
        if revision is None:
            return []
    cur = conn.execute(
        "SELECT ticker, rank, confidence, conviction, confluence, sources, "
        "       strategy_fn, rule_id, admission_path, wf_expectancy_pct, "
        "       wf_n_trades, wf_last_computed, decision_price, "
        "       decision_price_basis, entry_rule, provenance, recorded_at "
        "FROM watchlist_snapshot_log WHERE date=? AND strategy=? AND revision=? "
        "ORDER BY rank", (date_str, strategy, revision))
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        d["sources"] = json.loads(d["sources"] or "[]")
        d["provenance"] = json.loads(d["provenance"] or "{}")
        d["revision"] = revision
        out.append(d)
    return out


def latest_date_before(conn: sqlite3.Connection, strategy: str,
                       before: str) -> Optional[str]:
    """Most recent published date for `strategy` strictly before `before`.

    This is how Premarket finds the EOD base plan to revise: the previous
    session's plan, never today's (which does not exist yet at 08:35).
    """
    ensure_tables(conn)
    row = conn.execute(
        "SELECT MAX(date) FROM watchlist_publication "
        "WHERE strategy=? AND date < ?", (strategy, before)).fetchone()
    if row and row[0]:
        return row[0]
    # Publications recorded before this table existed left only snapshot rows.
    row = conn.execute(
        "SELECT MAX(date) FROM watchlist_snapshot_log "
        "WHERE strategy=? AND date < ?", (strategy, before)).fetchone()
    return row[0] if row and row[0] else None


def publication(conn: sqlite3.Connection, date_str: str, strategy: str):
    """The latest publication manifest for one (date, strategy), or None."""
    ensure_tables(conn)
    row = conn.execute(
        "SELECT date, strategy, revision, recorded_at, n_rows "
        "FROM watchlist_publication WHERE date=? AND strategy=? "
        "ORDER BY revision DESC LIMIT 1", (date_str, strategy)).fetchone()
    if not row:
        return None
    return dict(zip(["date", "strategy", "revision", "recorded_at", "n_rows"], row))


def base_plan(conn: sqlite3.Connection, before: str,
              strategy: str = STRATEGY_EOD) -> dict:
    """Resolve the base plan Premarket should revise.

    Returns {'status', 'date', 'rows', 'revision'} where status is one of
    BASE_PLAN / BASE_EMPTY / BASE_MISSING.

    The distinction matters operationally: BASE_EMPTY means the engine ran and
    deliberately approved nobody -- a real prediction, and revising it correctly
    yields an empty premarket plan. BASE_MISSING means no publication exists,
    which is an operational fault (job never ran, DB restored, first day) and
    must be reported as such rather than silently treated as "nothing to trade".
    """
    ensure_tables(conn)
    date_str = latest_date_before(conn, strategy, before)
    if not date_str:
        return {"status": BASE_MISSING, "date": None, "rows": [], "revision": None}
    rows = read_snapshot(conn, date_str, strategy)
    pub = publication(conn, date_str, strategy)
    revision = pub["revision"] if pub else (rows[0]["revision"] if rows else None)
    if rows:
        return {"status": BASE_PLAN, "date": date_str, "rows": rows,
                "revision": revision}
    return {"status": BASE_EMPTY, "date": date_str, "rows": [],
            "revision": revision}


def record_revisions(conn: sqlite3.Connection, date_str: str,
                     base_date: Optional[str], decisions) -> int:
    """Append the Premarket revision decisions. Returns rows written."""
    ensure_tables(conn)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = 0
    for d in decisions:
        action = d["action"] if isinstance(d, dict) else d.action
        if action not in ACTIONS:
            raise ValueError(f"unknown revision action {action!r}")
        get = (lambda k: d[k]) if isinstance(d, dict) else (lambda k: getattr(d, k))
        conn.execute(
            "INSERT INTO watchlist_revision "
            "(recorded_at, date, base_date, ticker, action, reason_code, reason, evidence) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, date_str, base_date, get("ticker"), action,
             get("reason_code"), get("reason"),
             json.dumps(get("evidence") or {}, default=str)),
        )
        n += 1
    conn.commit()
    return n


def read_revisions(conn: sqlite3.Connection, date_str: str) -> list[dict[str, Any]]:
    ensure_tables(conn)
    cur = conn.execute(
        "SELECT ticker, action, reason_code, reason, evidence, base_date, recorded_at "
        "FROM watchlist_revision WHERE date=? ORDER BY id", (date_str,))
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        d["evidence"] = json.loads(d["evidence"] or "{}")
        out.append(d)
    return out
