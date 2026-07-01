"""Shared fixtures for forward_testing tests."""
import sqlite3
import pytest

from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo


@pytest.fixture
def ft_db(tmp_path):
    """Temp DB with Phase-1+2 ft_* tables + source tables (scheduled_signals, daily_screen,
    ohlcv, suspension_events)."""
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
            date TEXT, ticker TEXT, close INTEGER, volume INTEGER, signal TEXT
        );
        CREATE TABLE ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL
        );
        CREATE TABLE suspension_events (
            ticker TEXT, last_normal_date TEXT, resume_date TEXT,
            missing_td INTEGER, gap_pct REAL, classification TEXT, detected_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def repo(ft_db):
    return FTRepo(ft_db)


def seed_ohlcv(conn, ticker, bars):
    """bars: list of (date, open, high, low, close[, volume]) in ascending date order."""
    rows = [b if len(b) == 6 else b + (0.0,) for b in bars]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        [(ticker,) + r for r in rows],
    )


def seed_signal(conn, scan_time, ticker, strategies, flow_score=0, direction="BUY"):
    """Insert a scheduled_signals row; returns its id."""
    cur = conn.execute(
        "INSERT INTO scheduled_signals (scan_time, ticker, strategies, flow_score, signal_direction) "
        "VALUES (?,?,?,?,?)",
        (scan_time, ticker, strategies, flow_score, direction),
    )
    return cur.lastrowid
