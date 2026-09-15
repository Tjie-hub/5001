"""Tests for D1 — /api/dashboard/risk aggregation.

Tests the pure engine.dashboard.get_risk_dashboard() function.
Foreign-owned-brokerage net flow (investor_type='Asing' — brokerage ownership, not
end-investor identity; D1), IHSG technicals, breadth, VPIN, and accdist are all aggregated
into a single dict. Fixture rows carry `value`, broker_flow's real signed IDR column (BUY
positive, SELL negative) — the engine sums it directly (SUM(value)), never
(BUY lot_value) - (SELL lot_value), the D2 anti-pattern. See
docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md.
"""
import sqlite3
import tempfile
import os
import datetime
from unittest.mock import patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_db(rows_ohlcv=None, rows_broker_flow=None, rows_daily_screen=None,
             rows_bandar=None):
    """Create a temp SQLite DB with all tables needed by the dashboard."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE ohlcv (
            date TEXT, ticker TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER,
            PRIMARY KEY (date, ticker)
        );
        CREATE TABLE broker_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT,
            ticker TEXT,
            investor_type TEXT,
            side TEXT,
            lot_volume INTEGER,
            value REAL
        );
        CREATE TABLE daily_screen (
            ticker TEXT, trade_date TEXT,
            close REAL, vpin REAL,
            PRIMARY KEY (ticker, trade_date)
        );
        CREATE TABLE bandar_detector (
            ticker TEXT, trade_date TEXT,
            broker_accdist TEXT,
            PRIMARY KEY (ticker, trade_date)
        );
    """)
    if rows_ohlcv:
        conn.executemany(
            "INSERT OR IGNORE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows_ohlcv
        )
    if rows_broker_flow:
        conn.executemany(
            "INSERT INTO broker_flow (trade_date,ticker,investor_type,side,value) "
            "VALUES (?,?,?,?,?)", rows_broker_flow
        )
    if rows_daily_screen:
        conn.executemany(
            "INSERT OR IGNORE INTO daily_screen (ticker,trade_date,close,vpin) VALUES (?,?,?,?)",
            rows_daily_screen
        )
    if rows_bandar:
        conn.executemany(
            "INSERT OR IGNORE INTO bandar_detector (ticker,trade_date,broker_accdist) VALUES (?,?,?)",
            rows_bandar
        )
    conn.commit()
    conn.close()
    return tmp.name


def _ihsg_rows(date_close_pairs):
    return [
        (d, 'IHSG', c * 0.995, c * 1.005, c * 0.99, c, 10_000_000_000)
        for d, c in date_close_pairs
    ]


def _trading_dates(anchor: str, n: int) -> list[str]:
    """n consecutive date strings ending on anchor."""
    end = datetime.date.fromisoformat(anchor)
    return [str(end - datetime.timedelta(days=n - 1 - i)) for i in range(n)]


DATE = '2026-06-05'
DATES = _trading_dates(DATE, 25)


# ── Shape ─────────────────────────────────────────────────────────────────────

def test_risk_dashboard_returns_all_required_keys(tmp_path):
    db = _make_db(rows_ohlcv=_ihsg_rows([(d, 6000) for d in DATES]))
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    required = {'date', 'risk_score', 'tier', 'components',
                'ihsg', 'breadth', 'foreign_flow', 'vpin', 'accdist'}
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"

    assert 'close' in result['ihsg']
    assert 'ma5' in result['ihsg']
    assert 'ma20' in result['ihsg']
    assert 'death_cross' in result['ihsg']
    assert 'ytd_pct' in result['ihsg']

    assert 'today' in result['foreign_flow']
    assert 'net_5d' in result['foreign_flow']
    assert 'net_20d' in result['foreign_flow']
    assert 'trend' in result['foreign_flow']


# ── Empty DB ─────────────────────────────────────────────────────────────────

def test_risk_dashboard_empty_db_does_not_crash(tmp_path):
    db = _make_db()
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    assert isinstance(result['risk_score'], float)
    assert isinstance(result['tier'], str)
    assert result['tier'] in ('GREEN', 'YELLOW', 'ORANGE', 'RED', 'CRITICAL')


# ── Foreign flow ─────────────────────────────────────────────────────────────

def test_risk_dashboard_foreign_flow_outflow(tmp_path):
    broker_rows = [
        # Today: Asing SELL 10B, BUY 2B → today net = -8B. `value` is signed
        # (BUY positive, SELL negative), matching the real broker_flow column.
        (DATE, 'BBRI', 'Asing', 'SELL', -10_000_000_000),
        (DATE, 'BBRI', 'Asing', 'BUY',   2_000_000_000),
        # 3 days ago: SELL 5B
        ('2026-06-02', 'TLKM', 'Asing', 'SELL', -5_000_000_000),
    ]
    db = _make_db(rows_broker_flow=broker_rows)
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    ff = result['foreign_flow']
    assert ff['today'] == -8_000_000_000
    assert ff['net_5d'] < 0          # -13B total in last 5 days
    assert ff['trend'] == 'OUTFLOW'


def test_risk_dashboard_foreign_flow_inflow(tmp_path):
    broker_rows = [
        (DATE, 'BBRI', 'Asing', 'BUY', 6_000_000_000),
        (DATE, 'BBRI', 'Asing', 'SELL', -1_000_000_000),
    ]
    db = _make_db(rows_broker_flow=broker_rows)
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    ff = result['foreign_flow']
    assert ff['today'] == 5_000_000_000
    assert ff['trend'] == 'INFLOW'


# ── YTD ──────────────────────────────────────────────────────────────────────

def test_risk_dashboard_ytd_computed(tmp_path):
    # IHSG: Jan 2 = 7000, today = 6000 → YTD = -14.29%
    rows = _ihsg_rows([('2026-01-02', 7000)]) + _ihsg_rows([(d, 6000) for d in DATES])
    db = _make_db(rows_ohlcv=rows)
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    ytd = result['ihsg']['ytd_pct']
    assert ytd is not None
    assert abs(ytd - (-14.29)) < 0.5


# ── D2 regression ─────────────────────────────────────────────────────────────

def test_risk_dashboard_foreign_flow_is_sum_of_signed_value_not_buy_minus_sell_lot_value(tmp_path):
    """D2: SUM(value) directly, never (BUY lot_value) - (SELL lot_value) — lot_value is
    unsigned on both sides, a different (wrong) quantity from the true signed net. This
    fixture includes a side/sign disagreement (a BUY row carrying a negative value) to prove
    the implementation is a plain sum, not a side-filtered subtraction."""
    broker_rows = [
        (DATE, 'BBRI', 'Asing', 'BUY', -2_000_000_000),   # side/sign disagreement, as seen live
        (DATE, 'BBRI', 'Asing', 'SELL', 500_000_000),      # side/sign disagreement, as seen live
        (DATE, 'BBRI', 'Asing', 'BUY', 9_000_000_000),
    ]
    db = _make_db(rows_broker_flow=broker_rows)
    with patch('flow_filter._DB_PATH', db):
        from engine.dashboard import get_risk_dashboard
        result = get_risk_dashboard(db, DATE)

    correct_sum_value = -2_000_000_000 + 500_000_000 + 9_000_000_000  # == 7.5B
    assert result['foreign_flow']['today'] == correct_sum_value == 7_500_000_000
