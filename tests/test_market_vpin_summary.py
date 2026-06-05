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


# ── Label thresholds ──────────────────────────────────────────────────────────

def test_label_critical_when_pct_above_095_ge_75():
    """75%+ of tickers above 0.95 → CRITICAL (matches macro_idx.md crash threshold)."""
    rows = [('2026-05-08', f'T{i}', 0.97 if i < 75 else 0.60) for i in range(100)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['label'] == 'CRITICAL', f"expected CRITICAL, got {result['label']}"


def test_label_critical_when_avg_vpin_ge_095():
    """avg_vpin >= 0.95 → CRITICAL."""
    rows = [('2026-05-08', f'T{i}', 0.97) for i in range(10)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-05-08')
    conn.close()
    assert result['label'] == 'CRITICAL'


def test_label_red_when_pct_above_08_ge_70():
    """70-84% of tickers above 0.8 (but <75% above 0.95) → RED."""
    rows = [(
        '2026-06-01', f'T{i}',
        0.85 if i < 70 else 0.70  # 70% above 0.8, none above 0.95
    ) for i in range(100)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-06-01')
    conn.close()
    assert result['label'] in ('RED', 'CRITICAL'), f"got {result['label']}"


def test_label_green_when_vpin_low():
    """Low VPIN → GREEN."""
    rows = [('2026-01-05', f'T{i}', 0.40) for i in range(50)]
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-01-05')
    conn.close()
    assert result['label'] == 'GREEN'


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


def test_real_crash_data_is_critical():
    """Replicate Apr 28 crash data: avg=0.973, 39/46 above 0.95 = 84.8%."""
    rows = (
        [('2026-04-28', f'TOXIC{i}', 0.97) for i in range(39)] +
        [('2026-04-28', f'NORM{i}', 0.70) for i in range(7)]
    )
    _, conn = _make_vpin_db(rows)
    result = get_market_vpin_summary(conn, '2026-04-28')
    conn.close()
    assert result['label'] == 'CRITICAL'
    assert result['pct_above_095'] > 75
