"""Read-only SQLite query tool exposed to agents.

Agents call this with a SELECT statement and parameters. Anything that is not
a SELECT raises ValueError — this is a defense-in-depth against prompt-injection
attempts that try to mutate state via the tool.
"""

import sqlite3
from pathlib import Path
from typing import Any
from data.db import connect as db_connect


def query(db_path: Path | str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cleaned = sql.strip().upper()
    if not cleaned.startswith("SELECT"):
        raise ValueError(f"sqlite_query only allows SELECT statements, got: {sql[:80]!r}")
    conn = db_connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
