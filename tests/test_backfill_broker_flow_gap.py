"""Regression tests for tools/backfill_broker_flow_gap.py.

Covers: idempotent gap-only backfill (never touches COMPLETE dates, never
re-fetches a ticker already present for a date), and correct writes to both
broker_flow and bandar_detector for historical dates.
"""
import sqlite3

import pytest

import tools.backfill_broker_flow_gap as bf


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    c.execute("""CREATE TABLE broker_flow (
        ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
        lot INTEGER, lot_value INTEGER, value INTEGER, value_total INTEGER,
        avg_price REAL, freq INTEGER, investor_type TEXT,
        PRIMARY KEY (ticker, trade_date, broker_code, side)
    )""")
    c.execute("""CREATE TABLE bandar_detector (
        ticker TEXT, trade_date TEXT, avg_price REAL, total_buyer INTEGER,
        total_seller INTEGER, net_broker_count INTEGER, broker_accdist TEXT,
        value INTEGER, volume INTEGER, top1_accdist TEXT, top3_accdist TEXT,
        top5_accdist TEXT, top10_accdist TEXT, avg_accdist TEXT, updated_at TEXT,
        PRIMARY KEY (ticker, trade_date)
    )""")
    yield c
    c.close()


def _seed_ohlcv(conn, date, tickers):
    conn.executemany("INSERT INTO ohlcv (ticker, date) VALUES (?, ?)", [(t, date) for t in tickers])


def _seed_broker_flow(conn, date, tickers):
    conn.executemany(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side) VALUES (?, ?, 'DX', 'BUY')",
        [(t, date) for t in tickers],
    )


def _broker_result(ticker, trade_date, lot=1000):
    return {
        "broker_rows": [{
            "ticker": ticker, "trade_date": trade_date, "broker_code": "ZP",
            "side": "BUY", "lot": lot, "lot_value": 0, "value": 0,
            "value_total": 0, "avg_price": 0.0, "freq": 1, "investor_type": "",
        }],
        "bandar": {
            "ticker": ticker, "trade_date": trade_date, "avg_price": None,
            "total_buyer": None, "total_seller": None, "net_broker_count": None,
            "broker_accdist": None, "value": None, "volume": None,
            "top1_accdist": None, "top3_accdist": None, "top5_accdist": None,
            "top10_accdist": None, "avg_accdist": None, "updated_at": "2026-08-04T00:00:00",
        },
        "trade_date": trade_date,
    }


def test_missing_tickers_for_date_excludes_already_present(conn):
    _seed_ohlcv(conn, "2026-07-31", ["AALI", "BBCA", "TLKM"])
    _seed_broker_flow(conn, "2026-07-31", ["AALI"])

    missing = bf.missing_tickers_for_date(conn, "2026-07-31")

    assert sorted(missing) == ["BBCA", "TLKM"]


def test_missing_tickers_for_date_empty_when_complete(conn):
    _seed_ohlcv(conn, "2026-07-31", ["AALI", "BBCA"])
    _seed_broker_flow(conn, "2026-07-31", ["AALI", "BBCA"])

    assert bf.missing_tickers_for_date(conn, "2026-07-31") == []


def test_gap_dates_excludes_complete_dates(conn):
    """Core requirement: the gap detector must skip COMPLETE dates entirely —
    a complete date must never appear in the work list the backfill loop
    consumes, guaranteeing it is never touched/overwritten."""
    _seed_ohlcv(conn, "2026-07-29", ["AALI"])
    _seed_broker_flow(conn, "2026-07-29", ["AALI"])  # COMPLETE

    _seed_ohlcv(conn, "2026-07-30", ["AALI", "BBCA"])
    _seed_broker_flow(conn, "2026-07-30", ["AALI"])  # PARTIAL

    _seed_ohlcv(conn, "2026-07-31", ["AALI"])
    # no broker_flow rows at all -> MISSING

    dates = bf.gap_dates(conn)

    assert "2026-07-29" not in dates
    assert dates == ["2026-07-30", "2026-07-31"]


def test_fetch_and_store_one_writes_broker_flow_and_bandar_detector(conn, monkeypatch):
    monkeypatch.setattr(bf.sf, "fetch_broker_flow",
                         lambda token, ticker, date: _broker_result(ticker, date, lot=999))

    ok = bf.fetch_and_store_one(conn, "tok", "AALI", "2026-07-31")

    assert ok is True
    row = conn.execute(
        "SELECT ticker, trade_date, broker_code, lot FROM broker_flow"
    ).fetchone()
    assert row == ("AALI", "2026-07-31", "ZP", 999)
    bandar_row = conn.execute(
        "SELECT ticker, trade_date FROM bandar_detector"
    ).fetchone()
    assert bandar_row == ("AALI", "2026-07-31")


def test_fetch_and_store_one_returns_false_on_no_data(conn, monkeypatch):
    monkeypatch.setattr(bf.sf, "fetch_broker_flow", lambda token, ticker, date: None)

    ok = bf.fetch_and_store_one(conn, "tok", "AALI", "2026-07-31")

    assert ok is False
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0


def test_backfill_is_idempotent_never_duplicates_same_key_row(conn, monkeypatch):
    """Re-running fetch_and_store_one for the same (ticker, date, broker,
    side) key must replace, not duplicate (INSERT OR REPLACE semantics)."""
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side, lot) "
        "VALUES ('AALI', '2026-07-31', 'ZP', 'BUY', 1)"
    )
    conn.commit()

    monkeypatch.setattr(bf.sf, "fetch_broker_flow",
                         lambda token, ticker, date: _broker_result(ticker, date, lot=42))
    bf.fetch_and_store_one(conn, "tok", "AALI", "2026-07-31")

    rows = conn.execute("SELECT ticker, trade_date, broker_code, side, lot FROM broker_flow").fetchall()
    assert rows == [("AALI", "2026-07-31", "ZP", "BUY", 42)]  # replaced, not duplicated


def test_summarize_gaps_counts_and_estimates(conn):
    """Pre-flight summary required before any backfill: missing/partial
    counts, expected ticker count, estimated requests, estimated runtime."""
    _seed_ohlcv(conn, "2026-04-23", ["AALI", "BBCA", "TLKM", "UNVR"])
    # MISSING: 0 present, 4 needed
    _seed_ohlcv(conn, "2026-04-24", ["AALI", "BBCA", "TLKM", "UNVR"])
    _seed_broker_flow(conn, "2026-04-24", ["AALI"])  # PARTIAL: 3 needed

    summary = bf.summarize_gaps(conn)

    assert summary["n_missing"] == 1
    assert summary["n_partial"] == 1
    assert summary["total_requests"] == 4 + 3  # 7 missing (ticker,date) pairs
    assert summary["avg_expected_tickers"] == 4
    assert summary["estimated_hours"] == pytest.approx(7 * bf.RATE_LIMIT_DELAY / 3600)


def test_summarize_gaps_empty_when_all_complete(conn):
    _seed_ohlcv(conn, "2026-04-23", ["AALI"])
    _seed_broker_flow(conn, "2026-04-23", ["AALI"])

    summary = bf.summarize_gaps(conn)

    assert summary["n_missing"] == 0
    assert summary["n_partial"] == 0
    assert summary["total_requests"] == 0


def test_select_dates_to_process_targets_specific_dates():
    all_gaps = ["2026-04-23", "2026-04-24", "2026-08-03", "2026-08-04"]

    result = bf.select_dates_to_process(all_gaps, only_dates=["2026-08-03"])

    assert result == ["2026-08-03"]


def test_select_dates_to_process_errors_on_date_not_in_gap_list():
    """The validation phase must fail loudly, not silently no-op, if the
    requested date isn't actually a real gap (e.g. already COMPLETE)."""
    all_gaps = ["2026-04-23", "2026-04-24"]

    with pytest.raises(ValueError, match="2026-08-03"):
        bf.select_dates_to_process(all_gaps, only_dates=["2026-08-03"])


def test_select_dates_to_process_limit_takes_oldest_first():
    all_gaps = ["2026-04-23", "2026-04-24", "2026-08-03"]

    result = bf.select_dates_to_process(all_gaps, limit=2)

    assert result == ["2026-04-23", "2026-04-24"]


def test_select_dates_to_process_defaults_to_all_gaps():
    all_gaps = ["2026-04-23", "2026-04-24"]

    assert bf.select_dates_to_process(all_gaps) == all_gaps
