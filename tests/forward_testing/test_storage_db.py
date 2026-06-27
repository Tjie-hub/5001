"""Connection helper tests: row factory + busy_timeout.

(WAL-mode coverage is added in Task 2, once init_ft_tables/_ensure_wal exists.)
"""
import sqlite3
from forward_testing.storage.db import ft_get_db


def test_ft_get_db_sets_row_factory_and_busy_timeout(tmp_path):
    db_path = str(tmp_path / "ft.db")
    conn = ft_get_db(db_path)
    try:
        assert conn.row_factory is sqlite3.Row
        bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert bt == 30000
    finally:
        conn.close()
