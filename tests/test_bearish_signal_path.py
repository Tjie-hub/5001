"""Tests for C1 — scheduled_signals BEARISH/SELL path.

The scanner had no SELL signal path at all: every signal stored in
scheduled_signals was BUY-side. This module verifies the new
scan_distribution_signals() function and signal_direction DB column.
"""
import sqlite3
import tempfile
import os
import pandas as pd
import numpy as np
from unittest.mock import patch

from scheduler.scanner import scan_distribution_signals


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_ohlcv(n=20, trend='declining'):
    """Build minimal OHLCV DataFrame."""
    dates = pd.date_range('2026-01-01', periods=n, freq='D')
    if trend == 'declining':
        close = np.linspace(1000, 800, n)  # drops from 1000 → 800
    elif trend == 'rising':
        close = np.linspace(800, 1000, n)  # rises
    else:
        close = np.full(n, 900.0)
    df = pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'open': close * 0.99,
        'high': close * 1.01,
        'low': close * 0.98,
        'close': close,
        'volume': np.full(n, 1_000_000),
    })
    return df


def _make_db(trade_date='2026-06-05', rows=None):
    """Create a temp SQLite DB with stockbit_flow data. Returns (path, conn)."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE stockbit_flow (
            ticker TEXT, trade_date TEXT, composite_score INTEGER,
            verdict TEXT, smart_money TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    if rows:
        conn.executemany(
            "INSERT INTO stockbit_flow VALUES (?,?,?,?,?)",
            rows
        )
    conn.commit()
    return tmp.name, conn


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_sell_signal_generated_for_bearish_flow_declining_price_bear_regime():
    """BEARISH flow (score -4) + declining price + BEAR regime → SELL signal returned."""
    db_path, conn = _make_db(rows=[
        ('BRPT', '2026-06-05', -4, '🔴 BEARISH', 'STRONG_SELL'),
    ])
    conn.close()

    ohlcv_map = {'BRPT': _make_ohlcv(trend='declining')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='BEAR'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)

    assert len(results) == 1, f"expected 1 SELL signal, got {len(results)}"
    r = results[0]
    assert r['ticker'] == 'BRPT'
    assert r['signal_direction'] == 'SELL'
    assert r['flow_verdict'] == 'BEARISH'
    assert r['flow_score'] == -4
    assert r['smart_money'] == 'STRONG_SELL'


def test_sell_signal_skips_bull_regime():
    """BEARISH flow + declining price + BULL regime → no signal (don't short uptrends)."""
    db_path, conn = _make_db(rows=[
        ('TLKM', '2026-06-05', -4, '🔴 BEARISH', 'STRONG_SELL'),
    ])
    conn.close()

    ohlcv_map = {'TLKM': _make_ohlcv(trend='declining')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='BULL'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert results == [], "BULL regime must not generate SELL signals"


def test_sell_signal_skips_rising_price():
    """BEARISH flow + rising price + BEAR regime → no signal (no distribution confirmation)."""
    db_path, conn = _make_db(rows=[
        ('DEWA', '2026-06-05', -4, '🔴 BEARISH', 'STRONG_SELL'),
    ])
    conn.close()

    ohlcv_map = {'DEWA': _make_ohlcv(trend='rising')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='BEAR'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert results == [], "rising price contradicts distribution — no SELL signal"


def test_sell_signal_skips_weak_bearish_score():
    """Flow score -2 (not ≤ -3) → no signal — threshold requires strong distribution."""
    db_path, conn = _make_db(rows=[
        ('BULL', '2026-06-05', -2, '🔴 BEARISH', 'NO'),
    ])
    conn.close()

    ohlcv_map = {'BULL': _make_ohlcv(trend='declining')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='BEAR'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert results == [], "score -2 is not BEARISH enough (threshold is ≤ -3)"


def test_sell_signal_skips_sideways_regime_with_declining_price():
    """SIDEWAYS regime is allowed (not just BEAR) — verify SIDEWAYS produces signals."""
    db_path, conn = _make_db(rows=[
        ('AMMN', '2026-06-05', -5, '🔴 BEARISH', 'STRONG_SELL'),
    ])
    conn.close()

    ohlcv_map = {'AMMN': _make_ohlcv(trend='declining')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='SIDEWAYS'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert len(results) == 1, "SIDEWAYS regime should allow SELL signals"
    assert results[0]['signal_direction'] == 'SELL'


def test_sell_signal_skips_ticker_missing_from_ohlcv():
    """Ticker in flow DB but not in ohlcv_map → skipped gracefully."""
    db_path, conn = _make_db(rows=[
        ('ZZZZZ', '2026-06-05', -5, '🔴 BEARISH', 'STRONG_SELL'),
    ])
    conn.close()

    with patch('scheduler.scanner.DB_PATH', db_path):
        results = scan_distribution_signals({}, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert results == []


def test_sell_signal_skips_wrong_date():
    """Flow data from yesterday is not used for today's signals."""
    db_path, conn = _make_db(rows=[
        ('BBRI', '2026-06-04', -5, '🔴 BEARISH', 'STRONG_SELL'),  # yesterday
    ])
    conn.close()

    ohlcv_map = {'BBRI': _make_ohlcv(trend='declining')}

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', return_value='BEAR'):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    assert results == [], "yesterday's flow data must not generate today's signals"


def test_multiple_tickers_some_pass_some_fail():
    """Mix of tickers — only those meeting all criteria produce SELL signals."""
    db_path, conn = _make_db(rows=[
        ('BRPT', '2026-06-05', -5, '🔴 BEARISH', 'STRONG_SELL'),  # passes
        ('TLKM', '2026-06-05', -4, '🔴 BEARISH', 'STRONG_SELL'),  # BULL regime → skip
        ('BBCA', '2026-06-05', -1, '🟡 NEUTRAL', 'NO'),           # score not bearish enough
    ])
    conn.close()

    ohlcv_map = {
        'BRPT': _make_ohlcv(trend='declining'),
        'TLKM': _make_ohlcv(trend='declining'),
        'BBCA': _make_ohlcv(trend='declining'),
    }

    # Use a call counter: BRPT=BEAR (1st), TLKM=BULL (2nd). BBCA filtered by score before regime.
    call_count = [0]
    def _regime(df):
        call_count[0] += 1
        return 'BEAR' if call_count[0] == 1 else 'BULL'

    with patch('scheduler.scanner.DB_PATH', db_path), \
         patch('scheduler.scanner._safe_regime', side_effect=_regime):
        results = scan_distribution_signals(ohlcv_map, '2026-06-05', '09:00')

    os.unlink(db_path)
    tickers = [r['ticker'] for r in results]
    assert 'BRPT' in tickers
    assert 'TLKM' not in tickers
    assert 'BBCA' not in tickers


# ── DB column test ────────────────────────────────────────────────────────────

def test_scheduled_signals_table_has_signal_direction_column():
    """scheduled_signals table must have signal_direction column."""
    from scheduler.scanner import _ensure_scheduled_signals_table
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    _ensure_scheduled_signals_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)").fetchall()}
    conn.close()
    os.unlink(tmp.name)
    assert 'signal_direction' in cols, "scheduled_signals must have signal_direction column"


def test_sell_signal_saved_with_sell_direction():
    """scan_distribution_signals results saved to DB have signal_direction='SELL'."""
    from scheduler.scanner import _ensure_scheduled_signals_table, _save_signals_to_db
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    _ensure_scheduled_signals_table(conn)

    sell_signals = [{
        'ticker': 'BRPT',
        'strategies': ['distribution'],
        'signal_direction': 'SELL',
        'flow_score': -4,
        'flow_verdict': 'BEARISH',
        'smart_money': 'STRONG_SELL',
        'signal_reasons': ['BEARISH flow (score=-4)'],
        'flow': {'score': -4, 'verdict': 'BEARISH', 'smart_money': 'STRONG_SELL'},
    }]

    _save_signals_to_db(conn, sell_signals, '2026-06-05', '09:00')
    conn.commit()

    row = conn.execute(
        "SELECT signal_direction, flow_verdict FROM scheduled_signals WHERE ticker='BRPT'"
    ).fetchone()
    conn.close()
    os.unlink(tmp.name)

    assert row is not None
    assert row[0] == 'SELL'
    assert row[1] == 'BEARISH'


def test_buy_signal_saved_with_buy_direction():
    """Existing BUY signals must be saved with signal_direction='BUY'."""
    from scheduler.scanner import _ensure_scheduled_signals_table, _save_signals_to_db
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    _ensure_scheduled_signals_table(conn)

    buy_signals = [{
        'ticker': 'BBCA',
        'strategies': ['vol_weighted'],
        'signal_direction': 'BUY',
        'flow_score': 4,
        'flow_verdict': 'BULLISH',
        'smart_money': 'STRONG_BUY',
        'signal_reasons': ['vol_weighted: signal'],
        'flow': {'score': 4, 'verdict': 'BULLISH', 'smart_money': 'STRONG_BUY'},
    }]

    _save_signals_to_db(conn, buy_signals, '2026-06-05', '09:00')
    conn.commit()

    row = conn.execute(
        "SELECT signal_direction, flow_verdict FROM scheduled_signals WHERE ticker='BBCA'"
    ).fetchone()
    conn.close()
    os.unlink(tmp.name)

    assert row is not None
    assert row[0] == 'BUY'
    assert row[1] == 'BULLISH'
