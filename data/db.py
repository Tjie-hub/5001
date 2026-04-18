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
    """)
    conn.commit()
    conn.close()
    print("DB initialized.")
