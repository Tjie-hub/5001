import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), 'walkforward.db'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_context():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT NOT NULL,
            date    TEXT NOT NULL,
            open    REAL,
            high    REAL,
            low     REAL,
            close   REAL,
            volume  REAL,
            UNIQUE(ticker, date)
        );
        CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON ohlcv(ticker);

        CREATE TABLE IF NOT EXISTS idx_tickers (
            ticker              TEXT PRIMARY KEY,
            status              TEXT DEFAULT 'active',
            first_seen          TEXT,
            last_checked        TEXT,
            last_fetch_date     TEXT,
            last_fetch_status   TEXT,
            fail_count          INTEGER DEFAULT 0,
            in_idx30            INTEGER DEFAULT 0,
            in_lq45             INTEGER DEFAULT 0,
            in_idx80            INTEGER DEFAULT 0,
            updated_at          TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("DB initialized.")
    init_agent_firm_tables()

def init_agent_firm_tables():
    """Idempotent migration for Phase 1 agent firm tables. Safe to call repeatedly."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            overridden INTEGER DEFAULT 0,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scan_time, ticker, strategy)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_decisions_ticker_date
            ON agent_decisions(ticker, scan_time);

        CREATE TABLE IF NOT EXISTS agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER REFERENCES agent_decisions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            prompt_version TEXT,
            output TEXT,
            tools_called TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_agent_traces_decision
            ON agent_traces(decision_id);

        CREATE TABLE IF NOT EXISTS scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL
        );
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    if "agent_decision_id" not in cols:
        conn.execute(
            "ALTER TABLE scheduled_signals ADD COLUMN agent_decision_id INTEGER "
            "REFERENCES agent_decisions(id)"
        )
    conn.commit()
    conn.close()
