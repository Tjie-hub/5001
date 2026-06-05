"""Tests for C5 — IHSG technical death cross / lower high detector.

The March death cross and progressive lower high sequence (9,174→8,291)
were never automatically detected. This module tests detect_ihsg_technicals().
"""
import sqlite3
import tempfile
import os

from engine.technicals import detect_ihsg_technicals


def _make_ihsg_db(rows):
    """Create temp SQLite DB with IHSG ohlcv rows. Returns (path, conn)."""
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
        "INSERT OR IGNORE INTO ohlcv VALUES (?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    return tmp.name, conn


def _ihsg_rows(date_close_pairs):
    """Build IHSG ohlcv rows from (date, close) list."""
    return [
        (d, 'IHSG', c * 0.995, c * 1.005, c * 0.990, c, 10_000_000_000)
        for d, c in date_close_pairs
    ]


import datetime

def _dates_from(start_str, n):
    """Generate n consecutive date strings starting from start_str."""
    start = datetime.date.fromisoformat(start_str)
    return [str(start + datetime.timedelta(days=i)) for i in range(n)]


# ── Output shape ──────────────────────────────────────────────────────────────

def test_returns_required_keys():
    dates = _dates_from('2026-01-02', 25)
    rows = _ihsg_rows([(d, 7000) for d in dates])
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    required = {'date', 'close', 'ma5', 'ma20', 'death_cross',
                'lower_high', 'support_breaks', 'label'}
    assert required.issubset(result.keys()), f"Missing: {required - result.keys()}"


def test_no_ihsg_data_returns_empty():
    _, conn = _make_ihsg_db([])
    result = detect_ihsg_technicals(conn, '2026-05-08')
    conn.close()
    assert result['close'] is None
    assert result['death_cross'] is False


# ── Death cross ───────────────────────────────────────────────────────────────

def test_death_cross_detected_when_ma5_crosses_below_ma20():
    """MA5 goes below MA20 → death_cross = True on the crossing day."""
    # Build 25 days: first 20 rising (MA5 > MA20), then 5 dropping fast
    dates = _dates_from('2026-01-02', 25)
    closes = [9000 - i * 10 for i in range(20)] + [7500 - i * 200 for i in range(5)]
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['death_cross'] is True, (
        f"expected death_cross=True, ma5={result['ma5']:.1f} ma20={result['ma20']:.1f}"
    )


def test_no_death_cross_when_ma5_above_ma20():
    """Steadily rising market: MA5 > MA20, no death cross."""
    dates = _dates_from('2026-01-02', 25)
    closes = [7000 + i * 50 for i in range(25)]  # rising
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['death_cross'] is False


# ── Lower high sequence ───────────────────────────────────────────────────────

def test_lower_high_detected_when_three_consecutive_highs_decline():
    """Three consecutive swing highs each lower than the prior → lower_high = True."""
    # Peaks at 9174, 8500, 8291 with dips between
    dates = _dates_from('2026-01-02', 30)
    closes = (
        [9000, 9174, 8900, 8800] +   # peak 1 at 9174
        [8600, 8500, 8300, 8200] +   # peak 2 at 8500
        [8100, 8291, 8000, 7900] +   # peak 3 at 8291
        [7800, 7700, 7650, 7600] +
        [7550, 7500, 7450, 7400] +
        [7350, 7300, 7250, 7200] +
        [7150, 7100, 7050, 7000, 6950, 6900]
    )
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['lower_high'] is True


def test_no_lower_high_in_rising_market():
    """Rising highs → lower_high = False."""
    dates = _dates_from('2026-01-02', 25)
    closes = [7000 + i * 100 for i in range(25)]
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['lower_high'] is False


# ── Support breaks ────────────────────────────────────────────────────────────

def test_support_break_detected_at_6200():
    """Close below 6200 → '6200' in support_breaks."""
    dates = _dates_from('2026-01-02', 25)
    closes = [6500] * 20 + [6100] * 5   # breaks 6200 in last 5 bars
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert '6200' in result['support_breaks'], f"support_breaks={result['support_breaks']}"


def test_support_break_detected_at_6000():
    dates = _dates_from('2026-01-02', 25)
    closes = [6200] * 20 + [5950] * 5
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert '6000' in result['support_breaks']


def test_support_break_detected_at_5500():
    dates = _dates_from('2026-01-02', 25)
    closes = [5700] * 20 + [5450] * 5
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert '5500' in result['support_breaks']


def test_no_support_break_above_all_levels():
    dates = _dates_from('2026-01-02', 25)
    closes = [8000] * 25
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['support_breaks'] == []


# ── Label ─────────────────────────────────────────────────────────────────────

def test_label_bearish_trend_when_death_cross_and_lower_high():
    """death_cross=True AND lower_high=True → BEARISH_TREND."""
    dates = _dates_from('2026-01-02', 30)
    # Big drop with lower highs and MA5 < MA20
    closes = [9000 - i * 120 for i in range(30)]
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['label'] in ('BEARISH_TREND', 'DOWNTREND', 'BEAR'), \
        f"got {result['label']}"


def test_label_bullish_when_rising_no_death_cross():
    """Rising market, no death cross → BULLISH label."""
    dates = _dates_from('2026-01-02', 25)
    closes = [7000 + i * 80 for i in range(25)]
    rows = _ihsg_rows(list(zip(dates, closes)))
    _, conn = _make_ihsg_db(rows)
    result = detect_ihsg_technicals(conn, dates[-1])
    conn.close()
    assert result['label'] in ('BULLISH', 'UPTREND', 'BULL'), f"got {result['label']}"
