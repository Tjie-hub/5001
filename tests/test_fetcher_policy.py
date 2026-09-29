"""Phase 2A fetcher policy (audit C-4):
- yfinance is RAW (auto_adjust=False) — one price basis with the scraper.
- yfinance NEVER overwrites an existing bar (scraper is the EOD authority);
  it inserts missing (ticker,date) rows as is_final=1 and repairs NULL-close rows.
- C1 finality guard (bootstrap audit 2026-09-16): rows dated the CURRENT WIB
  day are provisional (is_final=0) from this path — only the 16:15 EOD
  scraper may write a settled same-day bar.
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


def test_save_df_prior_day_backfill_is_final(db, monkeypatch):
    """Historical/new prior-day insertion keeps existing semantics: is_final=1."""
    import data.fetcher as f
    from data.fetcher import _save_df
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-07-03")
    _save_df("TST", _yf_frame(["2026-07-01", "2026-07-02"], [100.0, 200.0]))
    conn = sqlite3.connect(db)
    rows = dict(conn.execute("SELECT date, is_final FROM ohlcv WHERE ticker='TST'").fetchall())
    conn.close()
    assert rows == {"2026-07-01": 1, "2026-07-02": 1}


def test_save_df_same_wib_day_cannot_be_final(db, monkeypatch):
    """C1 regression: the 2026-09-15 pre-open defect (585 same-day is_final=1
    rows from the morning fetch) must be impossible — same-WIB-day bars from
    the yfinance path are provisional (is_final=0)."""
    import data.fetcher as f
    from data.fetcher import _save_df
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-07-02")
    _save_df("TST", _yf_frame(["2026-07-01", "2026-07-02"], [100.0, 200.0]))
    conn = sqlite3.connect(db)
    prior = conn.execute("SELECT is_final FROM ohlcv WHERE date='2026-07-01'").fetchone()[0]
    same_day = conn.execute("SELECT is_final FROM ohlcv WHERE date='2026-07-02'").fetchone()[0]
    conn.close()
    assert prior == 1           # settled history unchanged
    assert same_day == 0        # today: provisional only


def test_save_df_same_day_null_close_repair_stays_provisional(db, monkeypatch):
    """The NULL-close repair branch honours the guard too: a same-day
    placeholder repaired by the morning fetch must not become final."""
    import data.fetcher as f
    from data.fetcher import _save_df
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-07-02")
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)"
                 " VALUES ('TST','2026-07-02',NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    conn.close()
    _save_df("TST", _yf_frame(["2026-07-02"], [150.0]))
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT close, is_final FROM ohlcv WHERE date='2026-07-02'").fetchone()
    conn.close()
    assert row == (150.0, 0)


def test_eod_scraper_still_writes_final_same_day(tmp_path, monkeypatch):
    """The 16:15 EOD authority (screener/idx_scraper.save_ohlcv_to_db) is the
    writer that MAY stamp is_final=1 on the current WIB day — the guard must
    not have taken that away."""
    import sqlite3 as sq3
    import screener.idx_scraper as ix
    db = str(tmp_path / "scraper_eod.db")
    monkeypatch.setattr(ix, "_DB_PATH", db)
    conn = sq3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL,"
                 " low REAL, close REAL, volume REAL, is_final INTEGER,"
                 " UNIQUE(ticker, date))")
    conn.commit()
    conn.close()

    n = ix.save_ohlcv_to_db(
        {"TST": {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 5000}},
        "2026-07-02", is_final=True)

    conn = sq3.connect(db)
    row = conn.execute("SELECT close, is_final FROM ohlcv WHERE ticker='TST'").fetchone()
    conn.close()
    assert n == 1
    assert row == (105.0, 1)


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


# ── IHSG finalisation (2026-09-29) ───────────────────────────────────────────
# The index is never covered by the 16:15 EOD scraper (it is not a tradebook
# ticker), and the incremental refresh starts from MAX(date)+1, so every IHSG
# bar written provisional on its own day stayed is_final=0 forever
# (09-22..09-28 stranded). finalise_index_bars settles past sessions.

def _seed_ihsg(db, rows):
    conn = sqlite3.connect(db)
    conn.executemany("INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final)"
                     " VALUES ('IHSG',?,?,?,?,?,0,?)", rows)
    conn.commit()
    conn.close()


def test_finalise_index_bars_settles_past_provisional_sessions(db, monkeypatch):
    import data.fetcher as f
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-09-29")
    _seed_ihsg(db, [("2026-09-25", 6300, 6320, 6240, 6247.0, 0),
                    ("2026-09-28", 6200, 6210, 6150, 6154.0, 0),
                    ("2026-09-29", 6150, 6160, 6140, 6155.0, 0)])   # today: stays provisional
    seen = {}

    def fake_download(sym, start=None, end=None, **kw):
        seen.update(sym=sym, start=start, end=end)
        return _yf_frame(["2026-09-25", "2026-09-28"], [6250.0, 6160.0])
    monkeypatch.setattr(f.yf, "download", fake_download)

    n = f.finalise_index_bars()

    conn = sqlite3.connect(db)
    got = dict(conn.execute("SELECT date, is_final FROM ohlcv WHERE ticker='IHSG'").fetchall())
    close = conn.execute("SELECT close FROM ohlcv WHERE ticker='IHSG' AND date='2026-09-28'").fetchone()[0]
    conn.close()
    assert n == 2
    assert seen["sym"] == "^JKSE" and seen["start"] == "2026-09-25" and seen["end"] == "2026-09-29"
    assert got == {"2026-09-25": 1, "2026-09-28": 1, "2026-09-29": 0}
    assert close == 6160.0      # settled value replaces the intraday snapshot


def test_finalise_index_bars_leaves_a_session_the_source_lacks(db, monkeypatch):
    import data.fetcher as f
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-09-29")
    _seed_ihsg(db, [("2026-09-24", 6360, 6370, 6290, 6300.0, 0)])
    monkeypatch.setattr(f.yf, "download", lambda *a, **k: _yf_frame([], []))
    assert f.finalise_index_bars() == 0
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT is_final FROM ohlcv WHERE ticker='IHSG'").fetchone()[0] == 0
    conn.close()


def test_finalise_index_bars_is_a_noop_with_nothing_stranded(db, monkeypatch):
    import data.fetcher as f
    monkeypatch.setattr(f, "_wib_today", lambda: "2026-09-29")

    def boom(*a, **k):
        raise AssertionError("no fetch expected")
    monkeypatch.setattr(f.yf, "download", boom)
    assert f.finalise_index_bars() == 0


def test_incremental_fetch_finalises_the_index():
    import inspect
    import data.fetcher as f
    assert "finalise_index_bars(" in inspect.getsource(f.fetch_all_incremental)
