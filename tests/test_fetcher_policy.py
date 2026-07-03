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
