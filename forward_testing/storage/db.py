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
    conn.execute("PRAGMA foreign_keys=ON")  # enforce REFERENCES (off by default in sqlite)
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
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn):
    """Idempotent column adds for tables created by an earlier schema version.

    CREATE TABLE IF NOT EXISTS never alters an existing table, so a new column
    needs an explicit ALTER guarded against re-running on an already-migrated db.
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(ft_shadow_position)")}
    if "last_eval_date" not in cols:
        conn.execute("ALTER TABLE ft_shadow_position ADD COLUMN last_eval_date TEXT")
    if "signal_date" not in cols:
        conn.execute("ALTER TABLE ft_shadow_position ADD COLUMN signal_date TEXT")
    if "raw_entry_price" not in cols:
        conn.execute("ALTER TABLE ft_shadow_position ADD COLUMN raw_entry_price REAL")
