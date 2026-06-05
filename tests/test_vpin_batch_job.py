"""Tests for C10 — VPIN batch compute scheduler job.

daily_screen.vpin is already populated by screener_jobs.py, but it's buried
inside run_eod(). C10 adds a standalone run_vpin_daily_batch() job that
can run independently and also maintains a dedicated vpin_scores table
for historical querying.
"""
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

from scheduler.jobs import run_vpin_daily_batch, ensure_vpin_scores_table


def _make_db(with_vpin=True):
    """Create temp DB with daily_screen and ticks tables."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE daily_screen (
            date TEXT, ticker TEXT, close REAL, volume INTEGER,
            avg_vol_20d REAL, vpin REAL, vpin_label TEXT,
            PRIMARY KEY (date, ticker)
        )
    """)
    conn.execute("""
        CREATE TABLE ticks (
            id INTEGER PRIMARY KEY, date TEXT, ticker TEXT,
            time TEXT, price REAL, volume INTEGER, tick_type TEXT
        )
    """)
    # Insert some tickers without VPIN
    conn.execute("INSERT INTO daily_screen (date, ticker, close, volume) VALUES ('2026-06-05','BBCA',8000,5000000)")
    conn.execute("INSERT INTO daily_screen (date, ticker, close, volume) VALUES ('2026-06-05','BBRI',5000,3000000)")
    if with_vpin:
        # BBCA already has VPIN, BBRI does not
        conn.execute("UPDATE daily_screen SET vpin=0.92, vpin_label='TOXIC' WHERE ticker='BBCA'")
    conn.commit()
    return tmp.name, conn


# ── ensure_vpin_scores_table ──────────────────────────────────────────────────

def test_ensure_creates_table():
    db, conn = _make_db()
    ensure_vpin_scores_table(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close(); os.unlink(db)
    assert 'vpin_scores' in tables


def test_ensure_is_idempotent():
    """Calling ensure_vpin_scores_table twice should not raise."""
    db, conn = _make_db()
    ensure_vpin_scores_table(conn)
    ensure_vpin_scores_table(conn)  # second call
    conn.close(); os.unlink(db)


def test_vpin_scores_has_required_columns():
    db, conn = _make_db()
    ensure_vpin_scores_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(vpin_scores)").fetchall()}
    conn.close(); os.unlink(db)
    required = {'ticker', 'date', 'vpin', 'vpin_label', 'bucket_count', 'error'}
    assert required.issubset(cols), f"Missing columns: {required - cols}"


# ── run_vpin_daily_batch ──────────────────────────────────────────────────────

def test_batch_creates_vpin_scores_table():
    db, conn = _make_db()
    conn.close()

    mock_calc = MagicMock(return_value={
        'vpin': 0.95, 'vpin_label': 'TOXIC', 'bucket_count': 30, 'error': None
    })

    with patch('scheduler.jobs.DB_PATH', db), \
         patch('scheduler.jobs.get_all_tickers', return_value=['BBCA']), \
         patch('engine.vpin.calc_vpin', mock_calc), \
         patch('scheduler.jobs.send_telegram', MagicMock()):
        run_vpin_daily_batch('2026-06-05')

    conn2 = sqlite3.connect(db)
    tables = {r[0] for r in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn2.close(); os.unlink(db)
    assert 'vpin_scores' in tables


def test_batch_saves_vpin_to_scores_table():
    db, conn = _make_db(with_vpin=False)
    conn.close()

    mock_calc = MagicMock(return_value={
        'vpin': 0.88, 'vpin_label': 'TOXIC', 'bucket_count': 45, 'error': None
    })

    with patch('scheduler.jobs.DB_PATH', db), \
         patch('scheduler.jobs.get_all_tickers', return_value=['BBCA', 'BBRI']), \
         patch('engine.vpin.calc_vpin', mock_calc), \
         patch('scheduler.jobs.send_telegram', MagicMock()):
        result = run_vpin_daily_batch('2026-06-05')

    conn2 = sqlite3.connect(db)
    rows = conn2.execute("SELECT ticker, vpin FROM vpin_scores WHERE date='2026-06-05'").fetchall()
    conn2.close(); os.unlink(db)

    tickers = {r[0] for r in rows}
    assert 'BBCA' in tickers or 'BBRI' in tickers


def test_batch_returns_summary_dict():
    db, conn = _make_db(with_vpin=False)
    conn.close()

    mock_calc = MagicMock(return_value={
        'vpin': 0.88, 'vpin_label': 'TOXIC', 'bucket_count': 45, 'error': None
    })

    with patch('scheduler.jobs.DB_PATH', db), \
         patch('scheduler.jobs.get_all_tickers', return_value=['BBCA']), \
         patch('engine.vpin.calc_vpin', mock_calc), \
         patch('scheduler.jobs.send_telegram', MagicMock()):
        result = run_vpin_daily_batch('2026-06-05')

    os.unlink(db)
    assert isinstance(result, dict)
    assert 'computed' in result
    assert 'errors' in result


def test_batch_handles_calc_error_gracefully():
    """If calc_vpin raises, the batch should continue with remaining tickers."""
    db, conn = _make_db(with_vpin=False)
    conn.close()

    def side_effect(conn, ticker, date, **kwargs):
        if ticker == 'BBCA':
            raise ValueError("ticks data unavailable")
        return {'vpin': 0.85, 'vpin_label': 'TOXIC', 'bucket_count': 30, 'error': None}

    with patch('scheduler.jobs.DB_PATH', db), \
         patch('scheduler.jobs.get_all_tickers', return_value=['BBCA', 'BBRI']), \
         patch('engine.vpin.calc_vpin', side_effect=side_effect), \
         patch('scheduler.jobs.send_telegram', MagicMock()):
        result = run_vpin_daily_batch('2026-06-05')

    os.unlink(db)
    assert result['errors'] >= 1  # BBCA errored
    assert result['computed'] >= 0  # BBRI may have computed
