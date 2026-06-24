"""Tests for engine/catalyst.py — dated catalyst flags (strict-by-default)."""
import sqlite3

from engine.catalyst import ensure_catalyst_table, has_catalyst, add_catalyst


def _db():
    conn = sqlite3.connect(':memory:')
    ensure_catalyst_table(conn)
    return conn


class TestHasCatalyst:
    def test_empty_table_is_false(self):
        assert has_catalyst(_db(), 'BBCA', '2026-06-22') is False

    def test_missing_table_is_false(self):
        # has_catalyst must ensure the table itself → strict False, no raise
        conn = sqlite3.connect(':memory:')
        assert has_catalyst(conn, 'BBCA', '2026-06-22') is False

    def test_exact_date_true(self):
        conn = _db()
        add_catalyst(conn, 'BBCA', '2026-06-22', 'DIVIDEND_EX')
        assert has_catalyst(conn, 'BBCA', '2026-06-22') is True

    def test_within_window_true(self):
        conn = _db()
        add_catalyst(conn, 'BBCA', '2026-06-23', 'EARNINGS')
        assert has_catalyst(conn, 'BBCA', '2026-06-22', window_days=2) is True

    def test_outside_window_false(self):
        conn = _db()
        add_catalyst(conn, 'BBCA', '2026-06-26', 'EARNINGS')
        assert has_catalyst(conn, 'BBCA', '2026-06-22', window_days=2) is False

    def test_other_ticker_false(self):
        conn = _db()
        add_catalyst(conn, 'INCO', '2026-06-22', 'INDEX_EVENT')
        assert has_catalyst(conn, 'BBCA', '2026-06-22') is False

    def test_add_is_idempotent(self):
        conn = _db()
        add_catalyst(conn, 'BBCA', '2026-06-22', 'DIVIDEND_EX', 'Rp5')
        add_catalyst(conn, 'BBCA', '2026-06-22', 'DIVIDEND_EX', 'Rp5')
        n = conn.execute("SELECT COUNT(*) FROM catalyst_flags").fetchone()[0]
        assert n == 1
