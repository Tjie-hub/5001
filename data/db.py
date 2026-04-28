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
