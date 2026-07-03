"""Phase 2A nightly reconciliation: scraper-final bars vs yfinance raw closes.
Alert-only — NOTHING is written to ohlcv. price_fetcher is injectable."""
import sqlite3

import pytest


@pytest.fixture()
def db(tmp_path):
    from data.market_schema import ensure_market_data_schema
    path = str(tmp_path / "r.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    for t, c in (("AAAA", 1000.0), ("BBBB", 500.0), ("CCCC", 2000.0)):
        conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                     " VALUES (?, '2026-07-03', ?, ?, ?, ?, 1000)",
                     (t, c - 5, c + 5, c - 10, c))
    conn.commit()
    conn.close()
    ensure_market_data_schema(path)
    return path


def test_reconcile_flags_only_material_mismatches(db):
    from data.reconcile import reconcile_ohlcv
    yf_closes = {"AAAA": 1000.5, "BBBB": 520.0, "CCCC": 2000.0}   # BBBB off by 4%
    report = reconcile_ohlcv("2026-07-03", db_path=db,
                             price_fetcher=lambda tickers, date: yf_closes,
                             tolerance=0.001)
    assert report["compared"] == 3
    assert [m["ticker"] for m in report["mismatches"]] == ["BBBB"]
    assert report["mismatches"][0]["scraper"] == 500.0
    assert report["mismatches"][0]["yfinance"] == 520.0


def test_reconcile_never_writes(db):
    from data.reconcile import reconcile_ohlcv
    before = sqlite3.connect(db).execute(
        "SELECT ticker, close FROM ohlcv ORDER BY ticker").fetchall()
    reconcile_ohlcv("2026-07-03", db_path=db,
                    price_fetcher=lambda t, d: {"AAAA": 1.0, "BBBB": 1.0, "CCCC": 1.0})
    after = sqlite3.connect(db).execute(
        "SELECT ticker, close FROM ohlcv ORDER BY ticker").fetchall()
    assert before == after


def test_reconcile_handles_missing_yf_data(db):
    from data.reconcile import reconcile_ohlcv
    report = reconcile_ohlcv("2026-07-03", db_path=db,
                             price_fetcher=lambda t, d: {})
    assert report["compared"] == 0
    assert report["missing_yf"] == 3
