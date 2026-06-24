"""Tests for C3 — market-wide VPIN toxicity sensor.

daily_screen already stores per-ticker vpin values, but no code aggregates
them into a market-wide summary. This module verifies get_market_vpin_summary().
"""
import sqlite3
import tempfile
import os

from engine.vpin import get_market_vpin_summary


def _make_vpin_db(rows):
    """Create temp SQLite DB with daily_screen vpin data. Returns (path, conn)."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE daily_screen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, ticker TEXT, vpin REAL
        )
    """)
    conn.executemany(
        "INSERT INTO daily_screen (date, ticker, vpin) VALUES (?,?,?)",
        rows
    )
    conn.commit()
    return tmp.name, conn


# ── Basic output shape ────────────────────────────────────────────────────────

def test_returns_dict_with_required_keys():
    _, conn = _make_vpin_db([('2026-05-08', 'BBCA', 0.98)])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    required = {'date', 'tickers_with_vpin', 'avg_vpin',
                'pct_above_08', 'pct_above_095',
                'count_above_08', 'count_above_095', 'label'}
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"


def test_empty_returns_insufficient_data():
    _, conn = _make_vpin_db([])
    result = get_market_vpin_summary(conn, '2099-01-01')
    conn.close()
    assert result['tickers_with_vpin'] == 0
    assert result['avg_vpin'] is None
    assert result['label'] == 'INSUFFICIENT_DATA'


def test_null_vpin_rows_excluded():
    """NULL vpin rows in daily_screen must not count toward the summary."""
    _, conn = _make_vpin_db([
        ('2026-05-08', 'BBCA', 0.98),
        ('2026-05-08', 'BBRI', None),   # NULL — excluded
    ])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['tickers_with_vpin'] == 1


# ── Threshold counts ──────────────────────────────────────────────────────────

def test_count_above_08_correct():
    _, conn = _make_vpin_db([
        ('2026-05-08', 'A', 0.85),
        ('2026-05-08', 'B', 0.75),   # below 0.8
        ('2026-05-08', 'C', 0.92),
        ('2026-05-08', 'D', 0.65),   # below 0.8
    ])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['count_above_08'] == 2
    assert result['pct_above_08'] == 50.0


def test_count_above_095_correct():
    _, conn = _make_vpin_db([
        ('2026-05-08', 'A', 0.97),
        ('2026-05-08', 'B', 0.96),
        ('2026-05-08', 'C', 0.94),   # below 0.95
        ('2026-05-08', 'D', 0.98),
    ])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['count_above_095'] == 3
    assert result['pct_above_095'] == 75.0


def test_avg_vpin_computed_correctly():
    _, conn = _make_vpin_db([
        ('2026-05-08', 'A', 0.90),
        ('2026-05-08', 'B', 0.80),
        ('2026-05-08', 'C', 0.70),
    ])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert abs(result['avg_vpin'] - 0.8) < 0.001


# ── Label thresholds (BVC scale) ──────────────────────────────────────────────
# BVC VPIN centers ~0.30 on a normal day; labels key on avg + pct_above_05.

def test_label_green_normal_day():
    """Normal BVC day (avg ~0.30, few names >0.5) → GREEN."""
    rows = [('2026-01-05', f'T{i}', 0.30) for i in range(50)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['label'] == 'GREEN'


def test_label_yellow_by_avg():
    rows = [('2026-01-05', f'T{i}', 0.36) for i in range(50)]   # avg 0.36 ≥ 0.35
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['label'] == 'YELLOW'


def test_label_yellow_by_pct_above_05():
    # avg stays < 0.35 but ≥15% of names are above 0.5 → YELLOW via the tail
    rows = [('2026-01-05', f'T{i}', 0.55 if i < 8 else 0.25) for i in range(50)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['avg_vpin'] < 0.35 and result['pct_above_05'] >= 15
    assert result['label'] == 'YELLOW'


def test_label_orange_and_red_by_avg():
    for avg_v, expected in [(0.41, 'ORANGE'), (0.46, 'RED')]:
        rows = [('2026-01-05', f'T{i}', avg_v) for i in range(50)]
        _, conn = _make_vpin_db(rows)
        result = get_market_vpin_summary(conn, '2026-01-05')
        conn.close()
        assert result['label'] == expected, f"avg {avg_v} → {result['label']}, want {expected}"


def test_label_critical_by_avg():
    rows = [('2026-01-05', f'T{i}', 0.52) for i in range(50)]   # avg ≥ 0.50
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['label'] == 'CRITICAL'


def test_label_critical_by_pct_above_05():
    # avg < 0.50 (would be ORANGE) but ≥60% of names above 0.5 → CRITICAL via tail
    rows = [('2026-01-05', f'T{i}', 0.55 if i < 32 else 0.20) for i in range(50)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['avg_vpin'] < 0.50 and result['pct_above_05'] >= 60
    assert result['label'] == 'CRITICAL'


def test_only_uses_specified_date():
    """Must not include rows from other dates."""
    _, conn = _make_vpin_db([
        ('2026-05-07', 'BBCA', 0.99),  # different date
        ('2026-05-08', 'BBRI', 0.40),
    ])
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['tickers_with_vpin'] == 1
    assert result['avg_vpin'] == 0.40
