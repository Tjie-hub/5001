"""Phase 2A corpus rebuild: build side table -> verify vs old -> swap.
The fetcher is injectable; tests never touch the network."""
import sqlite3

import pandas as pd
import pytest


def _mk_db(tmp_path):
    from data.market_schema import ensure_market_data_schema
    path = str(tmp_path / "reb.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                 " close REAL, volume REAL, UNIQUE(ticker,date))")
    # old corpus: AAAA has 2 bars; one real session (2026-07-01) was purged
    for d, c in (("2026-06-30", 100.0), ("2026-07-02", 105.0)):
        conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                     " VALUES ('AAAA',?,?,?,?,?,1000)", (d, c - 1, c + 1, c - 2, c))
    conn.commit()
    conn.close()
    ensure_market_data_schema(path)
    return path


def _fake_fetch(ticker, period):
    """Returns a raw-history frame incl. the restored 2026-07-01 session."""
    dates = ["2026-06-30", "2026-07-01", "2026-07-02"]
    closes = [100.0, 100.0, 106.0]   # 106 vs old 105 = 0.94% > 0.5% threshold
    return pd.DataFrame({
        "date": dates,
        "open": [c - 1 for c in closes], "high": [c + 1 for c in closes],
        "low": [c - 2 for c in closes], "close": closes,
        "volume": [1000.0, 0.0, 1200.0],
    })


def test_build_populates_side_table(tmp_path):
    from scripts.rebuild_ohlcv_raw import build
    db = _mk_db(tmp_path)
    stats = build(db, tickers=["AAAA"], fetch_fn=_fake_fetch, period="5y")
    assert stats["tickers_ok"] == 1
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM ohlcv_raw").fetchone()[0] == 3
    assert conn.execute("SELECT MIN(is_final) FROM ohlcv_raw").fetchone()[0] == 1
    conn.close()


def test_verify_reports_restored_sessions_and_deltas(tmp_path):
    from scripts.rebuild_ohlcv_raw import build, verify
    db = _mk_db(tmp_path)
    build(db, tickers=["AAAA"], fetch_fn=_fake_fetch, period="5y")
    rep = verify(db)
    assert rep["tickers_old"] == 1 and rep["tickers_new"] == 1
    assert rep["restored_rows"] == 1            # 2026-07-01 came back
    assert rep["lost_rows"] == 0
    assert rep["close_mismatches"] and rep["close_mismatches"][0]["date"] == "2026-07-02"
    assert rep["ok"] is True


def test_swap_archives_and_renames(tmp_path):
    from scripts.rebuild_ohlcv_raw import build, verify, swap
    db = _mk_db(tmp_path)
    build(db, tickers=["AAAA"], fetch_fn=_fake_fetch, period="5y")
    rep = verify(db)
    swap(db, rep)
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "ohlcv_pre_raw_rebuild" in names and "ohlcv_raw" not in names
    assert conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0] == 3
    # UNIQUE(ticker,date) survives on the new table
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final)"
                     " VALUES ('AAAA','2026-07-02',1,1,1,1,1,1)")
    conn.close()


def test_swap_refuses_failing_verification(tmp_path):
    from scripts.rebuild_ohlcv_raw import build, swap
    db = _mk_db(tmp_path)
    build(db, tickers=["AAAA"], fetch_fn=_fake_fetch, period="5y")
    with pytest.raises(RuntimeError):
        swap(db, {"ok": False})
