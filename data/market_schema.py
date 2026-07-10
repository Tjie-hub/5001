"""Phase 2A (audit C-4/C-5) — market-data schema authority.

- ohlcv.is_final: 1 = settled bar (scraper 16:15 EOD final, or yfinance
  historical backfill); 0 = provisional intraday scraper bar. Research jobs
  must exclude is_final=0; live scans deliberately consume them.
- trading_calendar: IDX trading dates derived from IHSG bars. Replaces the
  purge that deleted real sessions of illiquid names (C-5).
- corporate_actions: dividends/splits from yfinance. The ohlcv basis is RAW
  exchange prices (single basis, C-4); research adjusts via this table.
"""
import sqlite3

from config import DB_PATH
from data.db import connect as db_connect

_DDL = """
CREATE TABLE IF NOT EXISTS trading_calendar (
    date       TEXT PRIMARY KEY,
    source     TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS corporate_actions (
    ticker     TEXT NOT NULL,
    date       TEXT NOT NULL,
    action     TEXT NOT NULL,          -- 'dividend' | 'split'
    value      REAL,                   -- dividend amount / split ratio
    source     TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date, action)
);
"""


def ensure_market_data_schema(db_path: str = DB_PATH) -> None:
    """Idempotent. Adds ohlcv.is_final (legacy rows -> 1) + the two tables."""
    conn = db_connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ohlcv)")}
        if cols and "is_final" not in cols:
            conn.execute("ALTER TABLE ohlcv ADD COLUMN is_final INTEGER DEFAULT 1")
        conn.executescript(_DDL)
        conn.commit()
    finally:
        conn.close()


def build_trading_calendar(conn: sqlite3.Connection) -> int:
    """Upsert IDX trading dates from IHSG bars. Returns rows newly added."""
    before = conn.execute("SELECT COUNT(*) FROM trading_calendar").fetchone()[0]
    conn.execute(
        "INSERT OR IGNORE INTO trading_calendar (date, source) "
        "SELECT DISTINCT date, 'IHSG' FROM ohlcv WHERE ticker='IHSG'"
    )
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM trading_calendar").fetchone()[0]
    return after - before
