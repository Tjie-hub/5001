"""Shared fixtures for forward_testing tests."""
import sqlite3
import pytest

from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo


@pytest.fixture
def ft_db(tmp_path):
    """Temp DB with Phase-1 ft_* tables + empty source tables (scheduled_signals, daily_screen)."""
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT, ticker TEXT, strategies TEXT,
            flow_score INTEGER, flow_verdict TEXT, smart_money TEXT,
            signal_reasons TEXT, signal_direction TEXT DEFAULT 'BUY'
        );
        CREATE TABLE daily_screen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, ticker TEXT, close INTEGER, volume INTEGER,
            signal TEXT
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def repo(ft_db):
    return FTRepo(ft_db)
