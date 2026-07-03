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
