"""Phase 2A schema: is_final flag on ohlcv, trading_calendar, corporate_actions.

ensure_market_data_schema is idempotent and safe on any DB that already has
an ohlcv table (legacy rows become is_final=1 — they are settled history).
"""
import sqlite3

import pytest


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "m.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('AAAA','2026-01-02',1,2,0.5,1.5,100)")
    conn.commit()
    conn.close()
    return path


def test_schema_adds_is_final_default_1(db):
    from data.market_schema import ensure_market_data_schema
    ensure_market_data_schema(db)
    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ohlcv)")}
    assert "is_final" in cols
    assert conn.execute("SELECT is_final FROM ohlcv WHERE ticker='AAAA'").fetchone()[0] == 1
    conn.close()


def test_schema_creates_calendar_and_actions_tables(db):
    from data.market_schema import ensure_market_data_schema
    ensure_market_data_schema(db)
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"trading_calendar", "corporate_actions"} <= names
    conn.close()


def test_schema_is_idempotent(db):
    from data.market_schema import ensure_market_data_schema
    ensure_market_data_schema(db)
    ensure_market_data_schema(db)   # second run must not raise
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0] == 1
    conn.close()


def test_build_calendar_from_ihsg(db):
    from data.market_schema import ensure_market_data_schema, build_trading_calendar
    ensure_market_data_schema(db)
    conn = sqlite3.connect(db)
    for d in ("2026-01-02", "2026-01-05", "2026-01-06"):
        conn.execute("INSERT OR IGNORE INTO ohlcv (ticker,date,open,high,low,close,volume)"
                     " VALUES ('IHSG',?,7000,7100,6900,7050,1)", (d,))
    conn.commit()
    n = build_trading_calendar(conn)
    assert n == 3
    dates = {r[0] for r in conn.execute("SELECT date FROM trading_calendar")}
    assert dates == {"2026-01-02", "2026-01-05", "2026-01-06"}
    assert build_trading_calendar(conn) == 0    # idempotent: nothing new
    conn.close()


def _mk_prod_like_db(tmp_path):
    from data.market_schema import ensure_market_data_schema
    path = str(tmp_path / "scr.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    conn.commit()
    conn.close()
    ensure_market_data_schema(path)
    return path


def test_scraper_intraday_is_provisional_eod_is_final(tmp_path, monkeypatch):
    import screener.idx_scraper as scraper
    db = _mk_prod_like_db(tmp_path)
    monkeypatch.setattr(scraper, "_DB_PATH", db)
    bar = {"TST": {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 5000}}

    scraper.save_ohlcv_to_db(bar, "2026-07-03")                  # intraday default
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT is_final FROM ohlcv WHERE ticker='TST'").fetchone()[0] == 0
    conn.close()

    bar["TST"]["close"] = 106
    scraper.save_ohlcv_to_db(bar, "2026-07-03", is_final=True)   # 16:15 EOD
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT close, is_final FROM ohlcv WHERE ticker='TST'").fetchone()
    assert row == (106, 1)
    conn.close()


def test_scraper_eod_save_upserts_calendar(tmp_path, monkeypatch):
    import screener.idx_scraper as scraper
    db = _mk_prod_like_db(tmp_path)
    monkeypatch.setattr(scraper, "_DB_PATH", db)
    bar = {"TST": {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 5000}}
    scraper.save_ohlcv_to_db(bar, "2026-07-03", is_final=True)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM trading_calendar WHERE date='2026-07-03'").fetchone()[0] == 1
    conn.close()


def test_load_ohlcv_bulk_final_only(tmp_path, monkeypatch):
    """Research jobs (WF refresh, backtest cache) must not see provisional
    intraday bars (Phase 2A item 2.1)."""
    import scheduler.utils as su
    import data.loaders as dl
    db = _mk_prod_like_db(tmp_path)
    # impl moved to data.loaders in M2 — patch the new home (su re-exports it)
    monkeypatch.setattr(dl, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final)"
                 " VALUES ('TST','2026-07-02',1,2,0.5,1.5,10,1)")
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final)"
                 " VALUES ('TST','2026-07-03',1,2,0.5,1.5,10,0)")   # partial today
    conn.commit()
    conn.close()

    full = su._load_ohlcv_bulk()
    finals = su._load_ohlcv_bulk(final_only=True)
    assert len(full["TST"]) == 2
    assert len(finals["TST"]) == 1
    assert str(finals["TST"]["date"].iloc[0])[:10] == "2026-07-02"
