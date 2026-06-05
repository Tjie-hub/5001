"""Tests for C4 — market breadth sensor.

Breadth collapsed to 22.5% (% stocks above MA20) 7 days before the Jan 28
crash (-7.35%). No breadth tracking existed. This module tests get_market_breadth().
"""
import sqlite3
import tempfile
import os

from engine.breadth import get_market_breadth


def _make_ohlcv_db(rows):
    """Create temp SQLite DB with ohlcv data. Returns (path, conn)."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE ohlcv (
            date TEXT, ticker TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER,
            PRIMARY KEY (date, ticker)
        )
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO ohlcv (date, ticker, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    return tmp.name, conn


def _build_series(ticker, dates_closes):
    """Build OHLCV rows from (date, close) list."""
    return [
        (d, ticker, c * 0.99, c * 1.01, c * 0.98, c, 1_000_000)
        for d, c in dates_closes
    ]


# ── Output shape ──────────────────────────────────────────────────────────────

def test_returns_required_keys():
    _, conn = _make_ohlcv_db(
        _build_series('BBCA', [('2026-01-02', 1000), ('2026-01-03', 1010)])
    )
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    required = {'date', 'total', 'advancers', 'decliners', 'unchanged',
                'adv_dec_ratio', 'pct_advancing', 'pct_above_ma20', 'label'}
    assert required.issubset(result.keys()), f"Missing: {required - result.keys()}"


def test_no_data_returns_empty():
    _, conn = _make_ohlcv_db([])
    result = get_market_breadth(conn, '2099-01-01')
    conn.close()
    assert result['total'] == 0
    assert result['label'] == 'INSUFFICIENT_DATA'


# ── Advancers / Decliners ─────────────────────────────────────────────────────

def test_advancer_detected_when_close_above_prev():
    rows = (
        _build_series('BBCA', [('2026-01-02', 1000), ('2026-01-03', 1050)]) +  # up
        _build_series('BBRI', [('2026-01-02', 500),  ('2026-01-03', 480)])     # down
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['advancers'] == 1
    assert result['decliners'] == 1
    assert result['total'] == 2


def test_unchanged_when_close_equals_prev():
    rows = _build_series('TLKM', [('2026-01-02', 3000), ('2026-01-03', 3000)])
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['unchanged'] == 1
    assert result['advancers'] == 0
    assert result['decliners'] == 0


def test_pct_advancing_computed_correctly():
    """3 advancers out of 4 tickers = 75%."""
    rows = (
        _build_series('A', [('2026-01-02', 100), ('2026-01-03', 110)]) +
        _build_series('B', [('2026-01-02', 100), ('2026-01-03', 110)]) +
        _build_series('C', [('2026-01-02', 100), ('2026-01-03', 110)]) +
        _build_series('D', [('2026-01-02', 100), ('2026-01-03', 90)])
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['pct_advancing'] == 75.0


def test_adv_dec_ratio_computed():
    rows = (
        _build_series('A', [('2026-01-02', 100), ('2026-01-03', 110)]) +
        _build_series('B', [('2026-01-02', 100), ('2026-01-03', 90)])
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['adv_dec_ratio'] == 1.0  # 1 / 1


def test_tickers_without_prev_day_excluded():
    """Ticker with no previous day data must not count in breadth."""
    rows = (
        _build_series('BBCA', [('2026-01-02', 1000), ('2026-01-03', 1050)]) +
        [('2026-01-03', 'NEWCO', 500, 510, 490, 505, 100_000)]  # no prev
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['total'] == 1  # only BBCA has prev day


# ── % above MA20 ──────────────────────────────────────────────────────────────

def test_pct_above_ma20_positive_when_closing_above_average():
    """Stock trading above its 20-day average contributes to pct_above_ma20."""
    import datetime
    base = datetime.date(2026, 1, 2)
    # Build 21 bars: first 20 at 100, then day 21 at 120 (above 20d avg of 100)
    dates = [(str(base + datetime.timedelta(days=i)), 100 if i < 20 else 120)
             for i in range(21)]
    rows = _build_series('BBCA', dates)
    _, conn = _make_ohlcv_db(rows)
    last_date = dates[-1][0]
    result = get_market_breadth(conn, last_date)
    conn.close()
    assert result['pct_above_ma20'] == 100.0


def test_pct_above_ma20_zero_when_below_average():
    """Stock below its 20-day average → pct_above_ma20 = 0."""
    import datetime
    base = datetime.date(2026, 1, 2)
    dates = [(str(base + datetime.timedelta(days=i)), 100 if i < 20 else 80)
             for i in range(21)]
    rows = _build_series('BBRI', dates)
    _, conn = _make_ohlcv_db(rows)
    last_date = dates[-1][0]
    result = get_market_breadth(conn, last_date)
    conn.close()
    assert result['pct_above_ma20'] == 0.0


# ── Labels ────────────────────────────────────────────────────────────────────

def test_label_bear_market_when_breadth_very_low():
    """< 30% advancing → BEAR_MARKET breadth."""
    rows = (
        [r for i in range(2) for r in _build_series(f'T{i}', [('2026-01-02', 100), ('2026-01-03', 110)])] +
        [r for i in range(8) for r in _build_series(f'D{i}', [('2026-01-02', 100), ('2026-01-03', 90)])]
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['label'] in ('BEAR_MARKET', 'WEAK'), f"got {result['label']}"


def test_label_bull_market_when_breadth_high():
    """> 70% advancing → BULL_MARKET breadth."""
    rows = (
        [r for i in range(8) for r in _build_series(f'T{i}', [('2026-01-02', 100), ('2026-01-03', 110)])] +
        [r for i in range(2) for r in _build_series(f'D{i}', [('2026-01-02', 100), ('2026-01-03', 90)])]
    )
    _, conn = _make_ohlcv_db(rows)
    result = get_market_breadth(conn, '2026-01-03')
    conn.close()
    assert result['label'] in ('BULL_MARKET', 'STRONG'), f"got {result['label']}"
