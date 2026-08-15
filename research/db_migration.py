"""R-5 Tier-1 migration (scoping note §4 step 3): copy the 8 Tier-1 tables'
rows from an existing single-file DB into research.db, verify row counts
match exactly, and only then DROP them from the source. Two-phase by design:
every table is copied AND verified before any table is dropped, so a failure
partway through leaves the source completely untouched -- safe to fix and
re-run. Idempotent: a table already absent from the source (already migrated)
is a no-op, not an error.
"""
from __future__ import annotations

import sqlite3

from research.db import TIER1_TABLES


def _table_exists(conn: sqlite3.Connection, schema: str, table: str) -> bool:
    return conn.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone() is not None


def _row_count(conn: sqlite3.Connection, schema: str, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]


def migrate_tier1(prod_path: str, research_path: str) -> dict:
    """Returns {table: {"copied": int, "dropped": bool}} for every TIER1_TABLES
    entry. Raises RuntimeError (touching nothing in prod_path) if any table's
    post-copy row count doesn't match, or if a table exists in both DBs with
    rows already present in research.db (ambiguous partial-migration state)."""
    conn = sqlite3.connect(f"file:{research_path}", uri=True)
    conn.execute(f"ATTACH DATABASE 'file:{prod_path}' AS src")

    report: dict[str, dict] = {}
    to_drop: list[str] = []
    try:
        for table in TIER1_TABLES:
            in_src = _table_exists(conn, "src", table)
            in_main = _table_exists(conn, "main", table)

            if not in_src:
                report[table] = {"copied": 0, "dropped": False}
                continue  # already migrated (or never existed) -- no-op

            if in_main and _row_count(conn, "main", table) > 0:
                raise RuntimeError(
                    f"table {table!r} exists in both {prod_path} and {research_path} "
                    f"with rows already present in the destination -- ambiguous "
                    f"partial-migration state, resolve manually before re-running")

            src_count = _row_count(conn, "src", table)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM src.{table} WHERE 0")
            conn.execute(f"INSERT INTO {table} SELECT * FROM src.{table}")
            dst_count = _row_count(conn, "main", table)
            if dst_count != src_count:
                raise RuntimeError(
                    f"row count mismatch migrating {table!r}: source={src_count} "
                    f"destination={dst_count} -- refusing to drop the source table")
            conn.commit()
            report[table] = {"copied": src_count, "dropped": True}
            to_drop.append(table)
    finally:
        conn.execute("DETACH DATABASE src")
        conn.close()

    # Phase 2: every table above either had nothing to copy or was verified --
    # only now do we touch the source with a destructive DROP.
    if to_drop:
        prod_conn = sqlite3.connect(prod_path)
        try:
            for table in to_drop:
                prod_conn.execute(f"DROP TABLE {table}")
            prod_conn.commit()
        finally:
            prod_conn.close()

    return report
