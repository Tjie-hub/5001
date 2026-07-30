import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from config import default_db_path, resolve_db_path

DB_PATH = resolve_db_path(os.getenv('DB_PATH', default_db_path()))


def log_db_identity(db_path: str = None) -> None:
    """Log the resolved absolute DB_PATH and its file identity (H-7
    continuation, P0.E2.S2.T2). Positively identifies which physical
    database file is in use -- not merely the configured path string --
    by including stat-derived identity (device/inode, size, mtime), so a
    silently-wrong path (e.g. an empty file freshly created at the wrong
    location) is distinguishable from the real, populated DB in the logs.

    Callers are responsible for invoking this exactly once at startup;
    this function has no import-time side effects and is safe to call
    from any process that wants a startup DB-identity record (currently
    just app.py's `if __name__ == "__main__"` block).

    Pre-figures the Phase 1 Certifier DB-identity check (PLAN-001
    P1.E4.S1, EXEC-001 section 7.3) -- this is intentionally just a log
    line, not that check.
    """
    path = db_path or DB_PATH
    logger = logging.getLogger(__name__)
    try:
        st = os.stat(path)
        logger.info(
            'DB identity resolved at startup',
            extra={
                'db_path': path,
                'db_exists': True,
                'db_size_bytes': st.st_size,
                'db_mtime': datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
                                     .isoformat(timespec='seconds'),
                'db_dev': st.st_dev,
                'db_ino': st.st_ino,
            },
        )
    except FileNotFoundError:
        logger.info(
            'DB identity resolved at startup',
            extra={'db_path': path, 'db_exists': False},
        )

def connect(path=None, timeout=30):
    """The one SQLite entry point: timeout + busy_timeout + WAL.

    Drop-in replacement for ``sqlite3.connect(path)`` — no row_factory, same
    return type, same ``with conn:`` transaction semantics. Every production
    connection to any of our DBs should come through here so lock-hardening
    lives in exactly one place (audit item 3.3; the 2026-06 lock bugs were all
    missing-pragma variants of the same defect).
    """
    conn = sqlite3.connect(path or DB_PATH, timeout=timeout)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # :memory:/read-only paths may reject WAL — timeout still applies
    return conn


def get_db():
    conn = connect()
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
    # Forward-testing foundation tables (Phase 1). Lazy import avoids any
    # import cycle; idempotent so safe on every startup.
    from forward_testing.storage.db import init_ft_tables
    init_ft_tables(DB_PATH)

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
            cost_usd REAL,
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

        CREATE TABLE IF NOT EXISTS provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            reason TEXT,
            duration_s REAL,
            request_id TEXT,
            failover INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_provider_events_provider_date
            ON provider_events(provider, created_at);
    """)

    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    if "agent_decision_id" not in cols:
        conn.execute(
            "ALTER TABLE scheduled_signals ADD COLUMN agent_decision_id INTEGER "
            "REFERENCES agent_decisions(id)"
        )

    trace_cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_traces)")}
    for col, ddl in [
        ("provider", "ALTER TABLE agent_traces ADD COLUMN provider TEXT"),
        ("model", "ALTER TABLE agent_traces ADD COLUMN model TEXT"),
        ("runtime_version", "ALTER TABLE agent_traces ADD COLUMN runtime_version TEXT"),
        ("failover", "ALTER TABLE agent_traces ADD COLUMN failover INTEGER DEFAULT 0"),
        ("error", "ALTER TABLE agent_traces ADD COLUMN error TEXT"),
        ("cost_usd", "ALTER TABLE agent_traces ADD COLUMN cost_usd REAL"),
    ]:
        if col not in trace_cols:
            conn.execute(ddl)

    decision_cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_decisions)")}
    if "providers_used" not in decision_cols:
        conn.execute("ALTER TABLE agent_decisions ADD COLUMN providers_used TEXT")

    conn.commit()
    conn.close()
