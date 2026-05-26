# tests/test_watchlist.py
import sqlite3
import pandas as pd
import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite DB with regime_watchlist + paper_trades tables."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE regime_watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            added_date  TEXT NOT NULL,
            regime_at_add TEXT NOT NULL DEFAULT 'BEAR',
            rsi_at_add  REAL,
            close_vs_ma50_pct REAL,
            wf_score    REAL,
            status      TEXT NOT NULL DEFAULT 'active',
            promoted_date TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_rwl_ticker_status
            ON regime_watchlist(ticker, status);

        CREATE TABLE paper_trades (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT,
            status  TEXT DEFAULT 'OPEN'
        );
    """)
    conn.commit()
    return conn


def test_add_new_entry(tmp_db):
    from engine.watchlist import add_to_watchlist
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=28.0,
                              close_vs_ma50_pct=-5.2, wf_score=72.0,
                              scan_date='2026-05-26')
    assert added is True
    row = tmp_db.execute(
        "SELECT ticker, status, rsi_at_add FROM regime_watchlist WHERE ticker='BBRI'"
    ).fetchone()
    assert row[0] == 'BBRI'
    assert row[1] == 'active'
    assert row[2] == 28.0


def test_duplicate_not_added(tmp_db):
    from engine.watchlist import add_to_watchlist
    add_to_watchlist(tmp_db, 'BBRI', rsi=28.0, close_vs_ma50_pct=-5.2,
                     wf_score=72.0, scan_date='2026-05-26')
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=27.0, close_vs_ma50_pct=-6.0,
                              wf_score=72.0, scan_date='2026-05-26')
    assert added is False
    count = tmp_db.execute(
        "SELECT COUNT(*) FROM regime_watchlist WHERE ticker='BBRI'"
    ).fetchone()[0]
    assert count == 1


def test_open_trade_not_added(tmp_db):
    from engine.watchlist import add_to_watchlist
    tmp_db.execute("INSERT INTO paper_trades (ticker, status) VALUES ('BMRI', 'OPEN')")
    tmp_db.commit()
    added = add_to_watchlist(tmp_db, 'BMRI', rsi=28.0, close_vs_ma50_pct=-5.0,
                              wf_score=72.0, scan_date='2026-05-26')
    assert added is False


def test_promote_on_bull_flip(tmp_db):
    from engine.watchlist import add_to_watchlist, promote_watchlist
    add_to_watchlist(tmp_db, 'BBCA', rsi=29.0, close_vs_ma50_pct=-6.0,
                     wf_score=65.0, scan_date='2026-05-20')
    promoted = promote_watchlist(tmp_db, ['BBCA', 'TLKM'], scan_date='2026-05-26')
    assert 'BBCA' in promoted
    row = tmp_db.execute(
        "SELECT status, promoted_date FROM regime_watchlist WHERE ticker='BBCA'"
    ).fetchone()
    assert row[0] == 'promoted'
    assert row[1] == '2026-05-26'


def test_promote_ignores_unknown_tickers(tmp_db):
    from engine.watchlist import promote_watchlist
    promoted = promote_watchlist(tmp_db, ['NONEXISTENT'], scan_date='2026-05-26')
    assert promoted == []


def test_expire_stale(tmp_db):
    from engine.watchlist import expire_stale
    # entry added 35 calendar days ago (stale beyond 30-day default)
    tmp_db.execute("""
        INSERT INTO regime_watchlist (ticker, added_date, wf_score, status)
        VALUES ('ASII', '2026-04-15', 70.0, 'active')
    """)
    tmp_db.commit()
    expired = expire_stale(tmp_db, scan_date='2026-05-26', max_calendar_days=30)
    assert 'ASII' in expired
    row = tmp_db.execute(
        "SELECT status FROM regime_watchlist WHERE ticker='ASII'"
    ).fetchone()
    assert row[0] == 'expired'


def test_priority_tickers_returns_promoted(tmp_db):
    from engine.watchlist import add_to_watchlist, promote_watchlist, priority_tickers
    add_to_watchlist(tmp_db, 'BBNI', rsi=30.0, close_vs_ma50_pct=-4.0,
                     wf_score=68.0, scan_date='2026-05-20')
    promote_watchlist(tmp_db, ['BBNI'], scan_date='2026-05-26')
    tickers = priority_tickers(tmp_db)
    assert 'BBNI' in tickers


def test_compute_rsi_uptrend_high():
    from engine.watchlist import compute_rsi
    # steady uptrend → RSI should be high (>60)
    closes = pd.Series([100 + i for i in range(30)])
    rsi = compute_rsi(closes)
    assert rsi > 60


def test_compute_rsi_downtrend_low():
    from engine.watchlist import compute_rsi
    # steady downtrend → RSI should be low (<40)
    closes = pd.Series([130 - i for i in range(30)])
    rsi = compute_rsi(closes)
    assert rsi < 40
