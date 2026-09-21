"""Tests for tools/backfill_foreign_flow_idx80.py -- the IDX80 foreign-flow
production RUNNER. It delegates every fetch/write to
tools.backfill_broker_flow_idx80.fetch_and_store_cell, so these tests focus
on: (a) that delegation actually happens and produces identical outcomes,
(b) the foreign-specific gap-only cell selection, and (c) the diagnostic
foreign breakdown. No network access: stockbit_fetcher.fetch_broker_flow is
always monkeypatched.
"""
import sqlite3

import pytest

import stockbit_fetcher as sf
import tools.backfill_broker_flow_idx80 as B
import tools.backfill_foreign_flow_idx80 as R


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
def conn(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES ('BBCA','active',1)")
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES ('BBRI','active',1)")
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES ('NOTIDX','active',0)")
    for d in ("2025-01-02", "2025-01-03"):
        c.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        c.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,))
    c.commit()
    monkeypatch.setattr(R, "DB_PATH", path)
    # fetch_and_store_cell's empty-retry backoff lives in B (the delegate
    # module), not in R -- both time.sleep call sites must be silenced.
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(B.time, "sleep", lambda *a, **k: None)
    yield c
    c.close()


def _populated_result(ticker, trade_date, lot=1000, investor_type="Asing"):
    return {
        "broker_rows": [{
            "ticker": ticker, "trade_date": trade_date, "broker_code": "ZP",
            "side": "BUY", "lot": lot, "lot_value": 1, "value": 2,
            "value_total": 3, "avg_price": 9000.0, "freq": 4,
            "investor_type": investor_type,
        }],
        "bandar": {
            "ticker": ticker, "trade_date": trade_date, "avg_price": 9000.0,
            "total_buyer": 1, "total_seller": 1, "net_broker_count": 1,
            "broker_accdist": "ACC", "value": 100, "volume": 50,
            "top1_accdist": "ACC", "top3_accdist": "ACC", "top5_accdist": "ACC",
            "top10_accdist": "ACC", "avg_accdist": "ACC",
            "updated_at": "2025-01-02T00:00:00",
        },
        "trade_date": trade_date,
    }


def _empty_result(ticker, trade_date):
    return {"broker_rows": [], "bandar": {}, "trade_date": trade_date}


# --- delegation is real, not a reimplementation ----------------------------


def test_outcome_constants_are_reexported_not_redefined():
    assert R.POPULATED is B.POPULATED
    assert R.EMPTY_CONFIRMED is B.EMPTY_CONFIRMED
    assert R.FAILED_HTTP is B.FAILED_HTTP
    assert R.FAILED_TIMEOUT is B.FAILED_TIMEOUT
    assert R.RATE_LIMITED is B.RATE_LIMITED


def test_fetch_and_store_cell_is_the_broker_runner_implementation():
    assert R.fetch_and_store_cell is B.fetch_and_store_cell


# --- universe / gap dates ---------------------------------------------------


def test_universe_is_active_idx80_only(conn):
    assert R.universe(conn) == ["BBCA", "BBRI"]


def test_gap_dates_date_to_exclusive(conn):
    assert R.gap_dates(conn, "2025-01-02", "2025-01-03") == ["2025-01-02"]
    assert R.gap_dates(conn, "2025-01-02", "2025-01-04") == ["2025-01-02", "2025-01-03"]


# --- fetch_and_store_cell outcomes (via delegation) -------------------------


def test_populated_cell_writes_broker_flow_and_bandar(conn, monkeypatch):
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None: _populated_result(ticker, date))
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.POPULATED
    row = conn.execute(
        "SELECT broker_code, side, lot, investor_type FROM broker_flow "
        "WHERE ticker='BBCA' AND trade_date='2025-01-02'"
    ).fetchone()
    assert row == ("ZP", "BUY", 1000, "Asing")


def test_empty_response_is_retried_before_confirming(conn, monkeypatch):
    calls = []

    def fake(token, ticker, date=None):
        calls.append(1)
        return _empty_result(ticker, date)

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.EMPTY_CONFIRMED
    assert len(calls) == R.EMPTY_RETRIES + 1
    marker = conn.execute(
        "SELECT value, volume FROM bandar_detector WHERE ticker='BBCA' AND trade_date='2025-01-02'"
    ).fetchone()
    assert marker == (0, 0)


def test_http_failure_retries_then_transient_recovery_is_populated(conn, monkeypatch):
    responses = [Exception("boom"), _populated_result("BBCA", "2025-01-02")]

    def fake(token, ticker, date=None):
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.POPULATED


def test_sustained_http_failure_reports_failed_http(conn, monkeypatch):
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None: (_ for _ in ()).throw(Exception("boom")))
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.FAILED_HTTP
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0


def test_rate_limit_exceeded_reports_rate_limited(conn, monkeypatch):
    def fake(token, ticker, date=None):
        raise sf.RateLimitExceeded("stayed 429")

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.RATE_LIMITED


def test_timeout_reports_failed_timeout(conn, monkeypatch):
    import requests

    def fake(token, ticker, date=None):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    outcome = R.fetch_and_store_cell(conn, "tok", "BBCA", "2025-01-02")
    assert outcome == R.FAILED_TIMEOUT


# --- foreign-specific gap-only orchestration in run() ----------------------


def test_run_skips_vendor_call_for_cell_with_confirmed_empty_foreign_only(conn, monkeypatch):
    """A ticker-day with broker_flow rows for a NON-Asing investor type is
    foreign-complete (genuinely zero foreign activity, already checked) --
    run() must never re-fetch it, even though it has no Asing row."""
    conn.execute(
        "INSERT INTO broker_flow (ticker, trade_date, broker_code, side, investor_type) "
        "VALUES ('BBCA', '2025-01-02', 'ZP', 'BUY', 'Lokal')"
    )
    conn.commit()
    calls = []

    def fake(token, ticker, date=None):
        calls.append((ticker, date))
        return _populated_result(ticker, date)

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", "2025-01-03", conn=conn)
    tickers_called = {t for t, d in calls}
    assert "BBCA" not in tickers_called  # confirmed-empty-foreign-only -- never re-fetched
    assert "BBRI" in tickers_called
    assert stats["skipped"] == 1
    assert stats["populated"] == 1


def test_run_dry_run_makes_no_vendor_calls_and_writes_nothing(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", "2025-01-04", conn=conn, dry_run=True)
    assert calls == []
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0
    assert stats["dry_run"] is True
    assert stats["planned_cells"] == 4  # 2 dates x 2 IDX80 tickers
    assert stats["foreign_breakdown"][R.STATE_MISSING] == 4


def test_rerun_after_full_population_makes_no_further_vendor_calls(conn, monkeypatch):
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None: _populated_result(ticker, date))
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    R.run("2025-01-02", "2025-01-03", conn=conn)

    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None: calls.append(1))
    stats2 = R.run("2025-01-02", "2025-01-03", conn=conn)
    assert calls == []
    assert stats2["skipped"] == 2
    assert stats2["populated"] == 0


def test_run_reports_foreign_breakdown_distinguishing_present_from_confirmed_empty(conn, monkeypatch):
    responses = {
        ("BBCA", "2025-01-02"): _populated_result("BBCA", "2025-01-02", investor_type="Asing"),
        ("BBRI", "2025-01-02"): _populated_result("BBRI", "2025-01-02", investor_type="Lokal"),
    }

    def fake(token, ticker, date=None):
        return responses[(ticker, date)]

    monkeypatch.setattr(sf, "fetch_broker_flow", fake)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda *a, **k: "tok")
    stats = R.run("2025-01-02", "2025-01-03", conn=conn)
    bd = stats["foreign_breakdown"]
    assert bd[R.STATE_PRESENT] == 1
    assert bd[R.STATE_CONFIRMED_EMPTY_FOREIGN_ONLY] == 1


# --- non-destructive SQL (static scan of this runner's own source) ---------


def test_runner_source_contains_no_destructive_sql():
    import re
    from pathlib import Path

    text = Path(R.__file__).read_text()
    destructive = re.compile(
        r"\b(DELETE\s+FROM|DROP\s+TABLE|DROP\s+INDEX|TRUNCATE|"
        r"UPDATE\s+broker_flow|UPDATE\s+bandar_detector)\b", re.IGNORECASE)
    assert destructive.findall(text) == []
