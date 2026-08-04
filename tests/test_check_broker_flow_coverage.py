"""Regression tests for tools/check_broker_flow_coverage.py — the gap-audit
tool (see docs/audit/BROKER_FLOW_BACKFILL_REPORT.md, 2026-08-04).
"""
import sqlite3

import pytest

from tools.check_broker_flow_coverage import build_report


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("""CREATE TABLE broker_flow (
        ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT
    )""")
    yield c
    c.close()


def _seed_ohlcv(conn, date, tickers):
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date) VALUES (?, ?)",
        [(t, date) for t in tickers],
    )


def _seed_broker_flow(conn, date, tickers):
    conn.executemany(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side) VALUES (?, ?, 'DX', 'BUY')",
        [(t, date) for t in tickers],
    )


def test_complete_date_when_actual_meets_expected(conn):
    _seed_ohlcv(conn, "2026-07-31", ["AALI", "BBCA", "BBRI", "TLKM", "UNVR"])
    _seed_broker_flow(conn, "2026-07-31", ["AALI", "BBCA", "BBRI", "TLKM", "UNVR"])

    report = build_report(conn)

    row = next(r for r in report if r["trade_date"] == "2026-07-31")
    assert row["expected"] == 5
    assert row["actual"] == 5
    assert row["status"] == "COMPLETE"


def test_missing_date_when_no_broker_flow_rows(conn):
    _seed_ohlcv(conn, "2026-07-30", ["AALI", "BBCA", "BBRI"])
    # no broker_flow rows for this date at all

    report = build_report(conn)

    row = next(r for r in report if r["trade_date"] == "2026-07-30")
    assert row["expected"] == 3
    assert row["actual"] == 0
    assert row["status"] == "MISSING"


def test_partial_date_when_actual_below_expected(conn):
    _seed_ohlcv(conn, "2026-07-29", ["AALI", "BBCA", "BBRI", "TLKM"])
    _seed_broker_flow(conn, "2026-07-29", ["AALI", "BBCA"])

    report = build_report(conn)

    row = next(r for r in report if r["trade_date"] == "2026-07-29")
    assert row["expected"] == 4
    assert row["actual"] == 2
    assert row["status"] == "PARTIAL"


def test_complete_when_actual_exceeds_expected():
    """Extra tickers (e.g. open paper-trade positions not in the ohlcv
    universe that day) must not be misreported as a gap."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    _seed_ohlcv(c, "2026-07-28", ["AALI", "BBCA"])
    _seed_broker_flow(c, "2026-07-28", ["AALI", "BBCA", "GOTO"])

    report = build_report(c)

    row = next(r for r in report if r["trade_date"] == "2026-07-28")
    assert row["expected"] == 2
    assert row["actual"] == 3
    assert row["status"] == "COMPLETE"
    c.close()


def test_non_trading_dates_are_excluded_from_report(conn):
    """A date with no ohlcv rows at all (weekend/holiday) must never appear —
    the report is scoped strictly to real trading days."""
    _seed_ohlcv(conn, "2026-07-31", ["AALI"])
    _seed_broker_flow(conn, "2026-08-01", ["AALI"])  # a Saturday, hypothetically

    report = build_report(conn)

    dates = [r["trade_date"] for r in report]
    assert "2026-08-01" not in dates
    assert "2026-07-31" in dates


def test_report_sorted_by_trade_date(conn):
    _seed_ohlcv(conn, "2026-07-31", ["AALI"])
    _seed_ohlcv(conn, "2026-07-29", ["AALI"])
    _seed_ohlcv(conn, "2026-07-30", ["AALI"])

    report = build_report(conn)

    assert [r["trade_date"] for r in report] == ["2026-07-29", "2026-07-30", "2026-07-31"]


def test_dates_before_feature_introduction_are_excluded(conn):
    """broker_flow was introduced 2026-04-23 (commit 6ac9aa1) — dates before
    that were never expected to have coverage and must never be reported as
    gaps, regardless of what ohlcv contains."""
    _seed_ohlcv(conn, "2021-07-05", ["AALI"])  # long before the feature existed
    _seed_ohlcv(conn, "2026-04-22", ["AALI"])  # one day before introduction
    _seed_ohlcv(conn, "2026-04-23", ["AALI"])  # introduction day itself

    report = build_report(conn)

    dates = [r["trade_date"] for r in report]
    assert "2021-07-05" not in dates
    assert "2026-04-22" not in dates
    assert "2026-04-23" in dates


def test_unsupported_tickers_flags_ticker_with_zero_broker_rows_across_many_dates():
    """A ticker present in ohlcv on many dates, with zero broker_flow rows on
    ANY of them, is a confirmed permanent API limitation (e.g. suspended
    stock, index symbol) — not a real backfill gap."""
    from tools.check_broker_flow_coverage import unsupported_tickers

    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    dates = [f"2026-05-{d:02d}" for d in range(1, 26)]  # 25 dates
    for d in dates:
        _seed_ohlcv(c, d, ["IHSG", "BBCA"])
        _seed_broker_flow(c, d, ["BBCA"])  # IHSG never gets broker data

    result = unsupported_tickers(c, min_samples=20)

    assert "IHSG" in result
    assert "BBCA" not in result
    c.close()


def test_unsupported_tickers_excludes_ticker_with_any_broker_data():
    """A ticker that returned data even once is NOT permanently unsupported —
    just occasionally illiquid. Must not be classified as unsupported."""
    from tools.check_broker_flow_coverage import unsupported_tickers

    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    dates = [f"2026-05-{d:02d}" for d in range(1, 26)]
    for d in dates:
        _seed_ohlcv(c, d, ["THIN"])
    _seed_broker_flow(c, dates[0], ["THIN"])  # traded on just 1 of 25 days

    result = unsupported_tickers(c, min_samples=20)

    assert "THIN" not in result
    c.close()


def test_unsupported_tickers_excludes_insufficient_sample_size():
    """A ticker only seen a handful of times with no broker data is
    insufficient evidence of a permanent limitation — could be a new listing
    or coincidence, not yet proven."""
    from tools.check_broker_flow_coverage import unsupported_tickers

    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    for d in ["2026-05-01", "2026-05-02", "2026-05-03"]:  # only 3 samples
        _seed_ohlcv(c, d, ["NEWIPO"])

    result = unsupported_tickers(c, min_samples=20)

    assert "NEWIPO" not in result
    c.close()


def test_build_report_subtracts_unsupported_tickers_from_expected():
    """Core fix: a date whose only 'gap' is a confirmed-unsupported ticker
    must not be reported as PARTIAL — that ticker was never really
    achievable, so the effective expected count excludes it."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    # Build up 25 days of history establishing IHSG as permanently unsupported.
    dates = [f"2026-05-{d:02d}" for d in range(1, 26)]
    for d in dates:
        _seed_ohlcv(c, d, ["IHSG", "BBCA"])
        _seed_broker_flow(c, d, ["BBCA"])  # BBCA complete, IHSG never

    report = build_report(c)

    row = next(r for r in report if r["trade_date"] == "2026-05-25")
    assert row["expected"] == 1  # IHSG excluded from the expected count
    assert row["actual"] == 1
    assert row["status"] == "COMPLETE"
    c.close()
