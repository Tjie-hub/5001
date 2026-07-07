"""Tests for data.db.connect() — the one hardened SQLite entry point."""
import sqlite3

import pytest

import data.db as ddb


def test_connect_sets_busy_timeout_and_wal(tmp_path):
    db = str(tmp_path / "t.db")
    conn = ddb.connect(db)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        conn.close()


def test_connect_is_dropin_no_row_factory(tmp_path):
    """Drop-in for sqlite3.connect: plain tuples, usable as txn context manager."""
    db = str(tmp_path / "t.db")
    with ddb.connect(db) as conn:
        conn.execute("CREATE TABLE x (a, b)")
        conn.execute("INSERT INTO x VALUES (1, 2)")
    conn.close()
    conn2 = ddb.connect(db)
    try:
        row = conn2.execute("SELECT a, b FROM x").fetchone()
        assert row == (1, 2)          # tuple equality — Row would fail this
        assert type(row) is tuple
    finally:
        conn2.close()


def test_connect_defaults_to_main_db_path(monkeypatch, tmp_path):
    db = str(tmp_path / "main.db")
    monkeypatch.setattr(ddb, "DB_PATH", db)
    conn = ddb.connect()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS y (a)")
    finally:
        conn.close()
    assert (tmp_path / "main.db").exists()


def test_connect_survives_pragma_failure_on_memory_db():
    """Pragmas are best-effort — :memory: / exotic paths must not raise."""
    conn = ddb.connect(":memory:")
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()


def test_get_db_now_hardened(monkeypatch, tmp_path):
    """get_db() keeps its Row contract AND gains the pragmas."""
    db = str(tmp_path / "main.db")
    monkeypatch.setattr(ddb, "DB_PATH", db)
    conn = ddb.get_db()
    try:
        assert conn.row_factory is sqlite3.Row
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
    finally:
        conn.close()
