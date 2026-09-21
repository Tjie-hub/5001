"""Tests for tools/foreign_flow_idx80_gap.py -- IDX80 universe (re-exported),
canonical IHSG-confirmed trading dates (re-exported), and the foreign-flow
(`investor_type='Asing'`) completion/state predicates.
"""
import sqlite3

import pytest

import tools.foreign_flow_idx80_gap as g
import tools.broker_flow_idx80_gap as bg


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


def _broker_row(conn, ticker, date, investor_type, broker_code="ZP", side="BUY"):
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side, investor_type) "
        "VALUES (?, ?, ?, ?, ?)",
        (ticker, date, broker_code, side, investor_type),
    )


def _empty_marker(conn, ticker, date):
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
        "VALUES (?, ?, 0, 0)",
        (ticker, date),
    )


# --- re-exports are the same objects/behavior as broker_flow_idx80_gap ----


def test_idx80_universe_is_reexported_from_broker_gap(conn):
    _ticker(conn, "BBCA")
    assert g.idx80_universe is bg.idx80_universe
    assert g.idx80_universe(conn) == ["BBCA"]


def test_canonical_trading_dates_is_reexported_from_broker_gap(conn):
    _ihsg_bar(conn, "2025-01-02")
    assert g.canonical_trading_dates is bg.canonical_trading_dates
    dates, _ = g.canonical_trading_dates(conn, "2025-01-01", "2025-01-05")
    assert dates == ["2025-01-02"]


# --- foreign_cell_state ----------------------------------------------------


def test_state_missing_when_nothing_present(conn):
    assert g.foreign_cell_state(conn, "BBCA", "2025-01-02") == g.STATE_MISSING


def test_state_present_when_asing_row_exists(conn):
    _broker_row(conn, "BBCA", "2025-01-02", "Asing")
    assert g.foreign_cell_state(conn, "BBCA", "2025-01-02") == g.STATE_PRESENT


def test_state_confirmed_empty_foreign_only_when_other_investor_type_present(conn):
    """broker_flow has rows (Lokal), but genuinely zero Asing rows -- a
    real, checked, zero-foreign-activity session."""
    _broker_row(conn, "BBCA", "2025-01-02", "Lokal")
    assert (
        g.foreign_cell_state(conn, "BBCA", "2025-01-02")
        == g.STATE_CONFIRMED_EMPTY_FOREIGN_ONLY
    )


def test_state_confirmed_empty_session_when_zero_marker_present(conn):
    _empty_marker(conn, "BBCA", "2025-01-02")
    assert (
        g.foreign_cell_state(conn, "BBCA", "2025-01-02")
        == g.STATE_CONFIRMED_EMPTY_SESSION
    )


def test_state_missing_when_bandar_detector_has_nonzero_data_but_no_broker_rows(conn):
    """Anomalous partial state -- must stay MISSING so a rerun retries it."""
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
        "VALUES ('BBCA', '2025-01-02', 12345, 678)"
    )
    assert g.foreign_cell_state(conn, "BBCA", "2025-01-02") == g.STATE_MISSING


def test_state_present_takes_priority_over_other_rows(conn):
    _broker_row(conn, "BBCA", "2025-01-02", "Lokal", broker_code="A")
    _broker_row(conn, "BBCA", "2025-01-02", "Asing", broker_code="B")
    assert g.foreign_cell_state(conn, "BBCA", "2025-01-02") == g.STATE_PRESENT


# --- foreign_cell_complete matches broker_cell_complete exactly -----------


@pytest.mark.parametrize(
    "setup",
    [
        lambda c: None,  # nothing -- both incomplete
        lambda c: _broker_row(c, "BBCA", "2025-01-02", "Asing"),
        lambda c: _broker_row(c, "BBCA", "2025-01-02", "Lokal"),
        lambda c: _empty_marker(c, "BBCA", "2025-01-02"),
    ],
)
def test_foreign_complete_matches_broker_complete_in_every_state(conn, setup):
    setup(conn)
    assert g.foreign_cell_complete(conn, "BBCA", "2025-01-02") == bg.broker_cell_complete(
        conn, "BBCA", "2025-01-02"
    )


# --- missing_cells -----------------------------------------------------


def test_missing_cells_preserves_order_and_excludes_complete(conn):
    _broker_row(conn, "BBCA", "2025-01-02", "Asing")
    _broker_row(conn, "BBRI", "2025-01-02", "Lokal")  # confirmed-empty-foreign-only
    missing = g.missing_cells(conn, "2025-01-02", ["BBCA", "BBRI", "TLKM"])
    assert missing == ["TLKM"]
