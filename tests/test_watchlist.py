# tests/test_watchlist.py
import sqlite3
import pandas as pd
import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite DB with regime_watchlist + paper_trades + backtest_cache."""
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
            bt_win_rate REAL,
            bt_return_pct REAL,
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

        CREATE TABLE backtest_cache (
            ticker TEXT, computed_date TEXT,
            best_strategy TEXT, best_return REAL, win_rate REAL,
            PRIMARY KEY (ticker, computed_date)
        );
    """)
    conn.commit()
    return conn


def test_add_new_entry(tmp_db):
    from engine.watchlist import add_to_watchlist
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=28.0,
                              close_vs_ma50_pct=-5.2, win_rate=60.0,
                              best_return=8.0, scan_date='2026-05-26')
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
                     win_rate=60.0, best_return=8.0, scan_date='2026-05-26')
    added = add_to_watchlist(tmp_db, 'BBRI', rsi=27.0, close_vs_ma50_pct=-6.0,
                              win_rate=60.0, best_return=8.0, scan_date='2026-05-26')
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
                              win_rate=60.0, best_return=8.0, scan_date='2026-05-26')
    assert added is False


def test_promote_on_bull_flip(tmp_db):
    from engine.watchlist import add_to_watchlist, promote_watchlist
    add_to_watchlist(tmp_db, 'BBCA', rsi=29.0, close_vs_ma50_pct=-6.0,
                     win_rate=55.0, best_return=7.0, scan_date='2026-05-20')
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
        INSERT INTO regime_watchlist (ticker, added_date, status)
        VALUES ('ASII', '2026-04-15', 'active')
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
                     win_rate=58.0, best_return=9.0, scan_date='2026-05-20')
    promote_watchlist(tmp_db, ['BBNI'], scan_date='2026-05-26')
    tickers = priority_tickers(tmp_db)
    assert 'BBNI' in tickers


def test_quality_gate_passes_and_fails(tmp_db):
    from engine.watchlist import passes_quality_gate
    tmp_db.executemany(
        "INSERT INTO backtest_cache (ticker, computed_date, best_strategy, best_return, win_rate) "
        "VALUES (?,?,?,?,?)",
        [
            ('GOOD', '2026-05-26', 'Vol-Weighted Entry', 12.0, 65.0),  # passes
            ('LOWWR', '2026-05-26', 'ORB', 12.0, 40.0),                # win_rate too low
            ('LOWRET', '2026-05-26', 'Momentum Following', 2.0, 65.0), # return too low
        ],
    )
    tmp_db.commit()
    ok, wr, ret = passes_quality_gate(tmp_db, 'GOOD')
    assert ok is True and wr == 65.0 and ret == 12.0
    assert passes_quality_gate(tmp_db, 'LOWWR')[0] is False
    assert passes_quality_gate(tmp_db, 'LOWRET')[0] is False
    assert passes_quality_gate(tmp_db, 'MISSING')[0] is False


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
