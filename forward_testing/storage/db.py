"""Forward-testing storage: connection helper + idempotent schema bootstrap.

DB-lock discipline (incident 2026-06-25): every caller opens a SHORT-LIVED
connection, writes in one transaction, and closes. Never hold a connection
open across long computation. WAL is persistent on the db file (set by
init_ft_tables via _ensure_wal); busy_timeout is set per-connection.
"""
import sqlite3


def _default_db_path():
    """Resolve the canonical DB path lazily so tests can inject a temp path
    without importing config."""
    from config import DB_PATH
    return DB_PATH


def ft_get_db(db_path=None):
    """Open a short-lived FT connection: Row factory + busy_timeout.

    Caller is responsible for closing promptly (use `with ft_get_db(...) as c:`).
    """
    conn = sqlite3.connect(db_path or _default_db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_wal(db_path):
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    finally:
        conn.close()


def init_ft_tables(db_path=None):
    """Create the Phase-1 forward-testing tables. Idempotent.

    Later phases extend this with positions/trades/performance/scoreboard tables.
    """
    from forward_testing.storage.schema import FT_PHASE1_SCHEMA, FT_PHASE2_SCHEMA
    db_path = db_path or _default_db_path()
    _ensure_wal(db_path)
    conn = ft_get_db(db_path)
    try:
        conn.executescript(FT_PHASE1_SCHEMA + "\n" + FT_PHASE2_SCHEMA)
        conn.commit()
    finally:
        conn.close()
