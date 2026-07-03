"""Phase 2A fetcher policy (audit C-4):
- yfinance is RAW (auto_adjust=False) — one price basis with the scraper.
- yfinance NEVER overwrites an existing bar (scraper is the EOD authority);
  it inserts missing (ticker,date) rows as is_final=1 and repairs NULL-close rows.
- dividends/splits land in corporate_actions.
"""
import sqlite3

import pandas as pd
import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    import data.db as ddb
    from data.market_schema import ensure_market_data_schema
    path = str(tmp_path / "f.db")
    monkeypatch.setattr(ddb, "DB_PATH", path)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    conn.commit()
    conn.close()
    ensure_market_data_schema(path)
    return path


def _yf_frame(dates, closes, dividends=None, splits=None):
    idx = pd.to_datetime(dates)
    data = {
        "Open": [c - 1 for c in closes], "High": [c + 2 for c in closes],
        "Low": [c - 2 for c in closes], "Close": closes,
        "Volume": [1000] * len(closes),
    }
    if dividends is not None:
        data["Dividends"] = dividends
    if splits is not None:
        data["Stock Splits"] = splits
    return pd.DataFrame(data, index=idx).rename_axis("Date")


def test_save_df_never_overwrites_existing_bar(db):
    from data.fetcher import _save_df
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final)"
                 " VALUES ('TST','2026-07-01',100,110,95,105,5000,1)")   # scraper bar
    conn.commit()
    conn.close()

    _save_df("TST", _yf_frame(["2026-07-01", "2026-07-02"], [999.0, 200.0]))

    conn = sqlite3.connect(db)
    kept = conn.execute("SELECT close FROM ohlcv WHERE ticker='TST' AND date='2026-07-01'").fetchone()[0]
    new = conn.execute("SELECT close, is_final FROM ohlcv WHERE ticker='TST' AND date='2026-07-02'").fetchone()
    conn.close()
    assert kept == 105          # scraper bar untouched
    assert new == (200.0, 1)    # gap backfilled as final


def test_save_df_repairs_null_close_rows(db):
    from data.fetcher import _save_df
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('TST','2026-07-01',NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    conn.close()
    _save_df("TST", _yf_frame(["2026-07-01"], [123.0]))
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT close FROM ohlcv WHERE date='2026-07-01'").fetchone()[0] == 123.0
    conn.close()


def test_save_actions_records_dividends_and_splits(db):
    from data.fetcher import _save_df
    _save_df("TST", _yf_frame(["2026-07-01", "2026-07-02"], [100.0, 101.0],
                              dividends=[0.0, 5.0], splits=[0.0, 2.0]))
    conn = sqlite3.connect(db)
    rows = set(conn.execute("SELECT date, action, value FROM corporate_actions").fetchall())
    conn.close()
    assert ("2026-07-02", "dividend", 5.0) in rows
    assert ("2026-07-02", "split", 2.0) in rows
    assert not any(r[1] == "dividend" and r[2] == 0.0 for r in rows)


def test_all_yf_download_calls_are_raw():
    """auto_adjust must be False everywhere (raw basis, C-4)."""
    import inspect
    import data.fetcher as f
    src = inspect.getsource(f)
    assert "auto_adjust=True" not in src
    assert "auto_adjust=False" in src


def _seed_calendar(db, dates):
    conn = sqlite3.connect(db)
    conn.executemany("INSERT OR IGNORE INTO trading_calendar (date, source) VALUES (?, 'test')",
                     [(d,) for d in dates])
    conn.commit()
    conn.close()


def test_calendar_purge_keeps_identical_price_sessions(db):
    """Audit C-5 regression: an illiquid name printing the same close+volume
    on consecutive REAL sessions must survive the purge."""
    from data.fetcher import purge_non_calendar_days
    _seed_calendar(db, ["2026-07-01", "2026-07-02"])
    conn = sqlite3.connect(db)
    for d in ("2026-07-01", "2026-07-02"):
        conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                     " VALUES ('ILLQ',?,50,50,50,50,0)", (d,))
    conn.commit()
    conn.close()
    removed = purge_non_calendar_days(min_days=1)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM ohlcv WHERE ticker='ILLQ'").fetchone()[0] == 2
    conn.close()
    assert removed == 0


def test_calendar_purge_removes_non_trading_dates(db):
    from data.fetcher import purge_non_calendar_days
    _seed_calendar(db, ["2026-07-01"])
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('TST','2026-07-01',1,2,0.5,1.5,10)")     # real session
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('TST','2026-07-05',1,2,0.5,1.5,10)")     # Sunday fill
    conn.commit()
    conn.close()
    assert purge_non_calendar_days(min_days=1) == 1
    conn = sqlite3.connect(db)
    dates = [r[0] for r in conn.execute("SELECT date FROM ohlcv WHERE ticker='TST'")]
    conn.close()
    assert dates == ["2026-07-01"]


def test_calendar_purge_noop_when_calendar_sparse(db):
    """Safety: with a near-empty calendar (< MIN_CALENDAR_DAYS) the purge must
    refuse to run rather than delete the whole table."""
    from data.fetcher import purge_non_calendar_days, MIN_CALENDAR_DAYS
    _seed_calendar(db, ["2026-07-01"])          # 1 << MIN_CALENDAR_DAYS
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('TST','2026-07-05',1,2,0.5,1.5,10)")
    conn.commit()
    conn.close()
    assert MIN_CALENDAR_DAYS >= 100
    assert purge_non_calendar_days() == 0       # refused: calendar too sparse
