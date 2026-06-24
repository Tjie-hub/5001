"""
engine/catalyst.py — Dated catalyst flags for the edge-score veto stage.

A directional veto (engine/veto.py Tier A) is overridable only when a dated
catalyst is on record for the ticker near the scan date. Strict-by-default:
an empty/absent table means has_catalyst() returns False, so the vetoes bite
*harder* without catalyst data — "better no pick than bad pick."

Population is intentionally out of scope here: seed manually (dividend ex-dates,
earnings, index events) and later auto-feed from calendar_filter / news. This
module only stores and queries flags.
"""
import sqlite3
from datetime import datetime

# kind ∈ DIVIDEND_EX | EARNINGS | INDEX_EVENT | CORP_ACTION | NEWS_HARD
CATALYST_DDL = """
CREATE TABLE IF NOT EXISTS catalyst_flags (
    ticker        TEXT NOT NULL,
    catalyst_date TEXT NOT NULL,
    kind          TEXT NOT NULL,
    note          TEXT,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (ticker, catalyst_date, kind)
)
"""


def ensure_catalyst_table(conn: sqlite3.Connection) -> None:
    conn.execute(CATALYST_DDL)


def add_catalyst(conn: sqlite3.Connection, ticker: str, catalyst_date: str,
                 kind: str, note: str = '') -> None:
    """Insert (or replace) a catalyst flag. Idempotent on (ticker,date,kind)."""
    ensure_catalyst_table(conn)
    conn.execute(
        "INSERT OR REPLACE INTO catalyst_flags "
        "(ticker, catalyst_date, kind, note, created_at) VALUES (?,?,?,?,?)",
        (ticker, catalyst_date, kind, note, datetime.now().isoformat()),
    )
    conn.commit()


def has_catalyst(conn: sqlite3.Connection, ticker: str, date: str,
                 window_days: int = 2) -> bool:
    """True if any catalyst_flag for `ticker` falls within ±window_days of
    `date`. Ensures the table first → strict False when there is no data."""
    ensure_catalyst_table(conn)
    row = conn.execute(
        "SELECT 1 FROM catalyst_flags WHERE ticker=? "
        "AND catalyst_date BETWEEN date(?, ?) AND date(?, ?) LIMIT 1",
        (ticker, date, f'-{window_days} days', date, f'+{window_days} days'),
    ).fetchone()
    return row is not None
