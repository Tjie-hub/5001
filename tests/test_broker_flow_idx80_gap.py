"""Tests for tools/broker_flow_idx80_gap.py — IDX80 universe, canonical
IHSG-confirmed trading dates, and the broker_flow completion predicate.
"""
import sqlite3

import pytest

import tools.broker_flow_idx80_gap as g


SCHEMA = """
CREATE TABLE idx_tickers (
    ticker TEXT PRIMARY KEY, status TEXT DEFAULT "active",
    in_idx30 INTEGER DEFAULT 0, in_lq45 INTEGER DEFAULT 0,
    in_idx80 INTEGER DEFAULT 0);
CREATE TABLE ohlcv (
    ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER);
CREATE TABLE trading_calendar (
    date TEXT PRIMARY KEY, source TEXT, updated_at TEXT);
CREATE TABLE broker_flow (
    ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
    lot INTEGER, lot_value INTEGER, value INTEGER, value_total INTEGER,
    avg_price REAL, freq INTEGER, investor_type TEXT,
    PRIMARY KEY (ticker, trade_date, broker_code, side));
CREATE TABLE bandar_detector (
    ticker TEXT, trade_date TEXT, avg_price REAL, total_buyer INTEGER,
    total_seller INTEGER, net_broker_count INTEGER, broker_accdist TEXT,
    value INTEGER, volume INTEGER, top1_accdist TEXT, top3_accdist TEXT,
    top5_accdist TEXT, top10_accdist TEXT, avg_accdist TEXT, updated_at TEXT,
    PRIMARY KEY (ticker, trade_date));
"""


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    yield c
    c.close()


def _ticker(conn, ticker, status="active", in_idx80=1):
    conn.execute(
        "INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES (?, ?, ?)",
        (ticker, status, in_idx80),
    )


def _ihsg_bar(conn, date):
    conn.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (date,))
    conn.execute(
        "INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (date,)
    )


def _scraper_only_row(conn, date):
    """A trading_calendar row with NO IHSG ohlcv bar (scraper_eod-only)."""
    conn.execute(
        "INSERT INTO trading_calendar (date, source) VALUES (?, 'scraper_eod')",
        (date,),
    )


# --- universe -----------------------------------------------------------


def test_idx80_universe_selects_active_in_idx80_only(conn):
    _ticker(conn, "BBCA", status="active", in_idx80=1)
    _ticker(conn, "BBRI", status="active", in_idx80=1)
    _ticker(conn, "DEAD", status="delisted", in_idx80=1)  # inactive -> excluded
    _ticker(conn, "SMALL", status="active", in_idx80=0)  # not IDX80 -> excluded
    assert g.idx80_universe(conn) == ["BBCA", "BBRI"]


def test_idx80_universe_never_hardcoded_reflects_db_changes(conn):
    _ticker(conn, "AAAA", status="active", in_idx80=1)
    assert g.idx80_universe(conn) == ["AAAA"]
    conn.execute("UPDATE idx_tickers SET in_idx80=0 WHERE ticker='AAAA'")
    assert g.idx80_universe(conn) == []


# --- canonical calendar --------------------------------------------------


def test_canonical_dates_requires_ihsg_bar_not_just_calendar_row(conn):
    _ihsg_bar(conn, "2025-01-02")
    _scraper_only_row(conn, "2025-01-03")  # calendar row, no IHSG bar
    dates, non_ihsg = g.canonical_trading_dates(conn, "2025-01-01", "2025-01-05")
    assert dates == ["2025-01-02"]
    assert [r["date"] for r in non_ihsg] == ["2025-01-03"]


def test_canonical_dates_date_to_exclusive(conn):
    _ihsg_bar(conn, "2025-01-02")
    _ihsg_bar(conn, "2025-01-03")
    dates, _ = g.canonical_trading_dates(conn, "2025-01-02", "2025-01-03")
    assert dates == ["2025-01-02"]  # 01-03 excluded, matches --date-to semantics


def test_canonical_dates_excludes_weekends_and_holidays_implicitly(conn):
    # No IHSG bar was ever inserted for weekends/holidays -- they simply never
    # appear in the result, without any hardcoded holiday list.
    _ihsg_bar(conn, "2025-01-02")  # Thursday
    dates, _ = g.canonical_trading_dates(conn, "2025-01-01", "2025-01-06")
    assert "2025-01-04" not in dates  # Saturday
    assert "2025-01-05" not in dates  # Sunday
    assert dates == ["2025-01-02"]


# --- completion predicate ------------------------------------------------


def test_cell_incomplete_when_nothing_present(conn):
    assert not g.broker_cell_complete(conn, "BBCA", "2025-01-02")


def test_cell_complete_when_broker_flow_rows_exist(conn):
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side) "
        "VALUES ('BBCA', '2025-01-02', 'ZP', 'BUY')"
    )
    assert g.broker_cell_complete(conn, "BBCA", "2025-01-02")


def test_cell_incomplete_when_bandar_detector_has_real_nonzero_data_but_no_broker_rows(conn):
    """Anomalous state (nonzero bandar_detector rollup, no broker_flow rows)
    must stay incomplete so a rerun retries it, rather than being silently
    accepted as done."""
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
        "VALUES ('BBCA', '2025-01-02', 12345, 678)"
    )
    assert not g.broker_cell_complete(conn, "BBCA", "2025-01-02")


def test_cell_complete_when_confirmed_empty_marker_present(conn):
    """A bandar_detector row with value=0 AND volume=0 is the confirmed-empty
    marker written by the runner after retry exhaustion still returned an
    empty payload -- mirrors stockbit_flow's zero-activity-row precedent for
    stockbit_flow_bars."""
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
        "VALUES ('BBCA', '2025-01-02', 0, 0)"
    )
    assert g.broker_cell_complete(conn, "BBCA", "2025-01-02")


def test_cell_complete_when_confirmed_empty_marker_has_null_columns(conn):
    """COALESCE guard: NULL value/volume must not be misread as 'has activity'."""
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date) VALUES ('BBCA', '2025-01-02')"
    )
    assert g.broker_cell_complete(conn, "BBCA", "2025-01-02")


def test_missing_cells_preserves_order_and_excludes_complete(conn):
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side) "
        "VALUES ('BBCA', '2025-01-02', 'ZP', 'BUY')"
    )
    missing = g.missing_cells(conn, "2025-01-02", ["BBCA", "BBRI", "TLKM"])
    assert missing == ["BBRI", "TLKM"]
