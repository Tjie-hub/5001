import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), 'walkforward.db'))

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

    # RCA 2026-07-10: session-limit events carry the advertised reset time
    # (engine/agent_firm/providers/metrics.py::provider_stats() has queried
    # this column since 2abeb4b/48b5d17; the migration adding it was never
    # committed, so it only ever existed in an uncommitted local edit -- this
    # is the first real CI run against committed HEAD (RC1), which is why it
    # surfaced only now).
    pe_cols = {r[1] for r in conn.execute("PRAGMA table_info(provider_events)")}
    if "reset_time" not in pe_cols:
        conn.execute("ALTER TABLE provider_events ADD COLUMN reset_time TEXT")

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
