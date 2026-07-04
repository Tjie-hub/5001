"""Phase 3A: the EOD screener path self-cleans holiday-fill rows (audit C-5
follow-up — the purge was never wired here, so fills accumulated to 4,138 rows
by 2026-07-04). Tests the extracted _eod_calendar_cleanup helper directly."""
import sqlite3

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    from data.market_schema import ensure_market_data_schema
    path = str(tmp_path / "eod.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    # IHSG trading days (calendar source) — 2026-07-06 (holiday) is ABSENT
    for d in ("2026-07-03", "2026-07-07"):
        conn.execute("INSERT INTO ohlcv (ticker,date,close) VALUES ('IHSG',?,7000)", (d,))
    # a real ticker with a spurious holiday-fill on 2026-07-06 (not a trading day)
    for d in ("2026-07-03", "2026-07-06", "2026-07-07"):
        conn.execute("INSERT INTO ohlcv (ticker,date,close) VALUES ('AAAA',?,100)", (d,))
    conn.commit()
    conn.close()
    ensure_market_data_schema(path)
    import data.db as ddb
    monkeypatch.setattr(ddb, "DB_PATH", path)
    return path


def test_eod_cleanup_purges_holiday_fills(db):
    from screener.screener_jobs import _eod_calendar_cleanup
    removed = _eod_calendar_cleanup(min_days=1)
    assert removed == 1                      # only the 2026-07-06 holiday-fill
    conn = sqlite3.connect(db)
    dates = {r[0] for r in conn.execute("SELECT DISTINCT date FROM ohlcv WHERE ticker='AAAA'")}
    conn.close()
    assert "2026-07-06" not in dates, "holiday-fill not purged"
    assert {"2026-07-03", "2026-07-07"} <= dates, "real sessions wrongly removed"


def test_eod_cleanup_failsoft_on_missing_tables(tmp_path, monkeypatch):
    """No trading_calendar / sparse calendar -> returns 0, never raises."""
    import data.db as ddb
    path = str(tmp_path / "bare.db")
    sqlite3.connect(path).close()            # empty db, no ohlcv/calendar
    monkeypatch.setattr(ddb, "DB_PATH", path)
    from screener.screener_jobs import _eod_calendar_cleanup
    assert _eod_calendar_cleanup(min_days=1) == 0
