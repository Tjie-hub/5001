"""Corporate-action adjustment layer (research audit R-1, Phase A).

Storage keeps RAW exchange prices (C-4). The research loading path back-adjusts
through splits from the corporate_actions table so backtests never see the
artificial gap a split prints in a raw series. Dividends are deliberately NOT
price-adjusted (price-return basis). Live scans (final_only=False) stay raw.
"""
import os
import sqlite3
import tempfile

import pandas as pd
import pytest

from data.adjustments import load_split_factors, adjust_ohlcv
from data.loaders import _load_ohlcv_bulk


def _df(rows):
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


# ─── adjust_ohlcv (pure) ─────────────────────────────────────────────────────

def test_single_split_back_adjusts_prior_bars_only():
    df = _df([
        ("2025-01-01", 1000, 1100, 900, 1000, 10_000),
        ("2025-01-02", 1000, 1100, 900, 1000, 10_000),
        ("2025-01-03", 500, 550, 450, 500, 20_000),   # 2:1 split takes effect here
    ])
    out = adjust_ohlcv(df, [("2025-01-03", 2.0)])
    # bars strictly BEFORE the ex-date: price /= 2, volume *= 2
    assert out.loc[0, "close"] == pytest.approx(500)
    assert out.loc[0, "open"] == pytest.approx(500)
    assert out.loc[0, "high"] == pytest.approx(550)
    assert out.loc[0, "low"] == pytest.approx(450)
    assert out.loc[0, "volume"] == pytest.approx(20_000)
    assert out.loc[1, "close"] == pytest.approx(500)
    # the ex-date bar itself is already new-basis: untouched
    assert out.loc[2, "close"] == pytest.approx(500)
    assert out.loc[2, "volume"] == pytest.approx(20_000)


def test_sequential_splits_compound():
    # CUAN case: two 10:1 splits days apart -> earliest bars divided by 100
    df = _df([
        ("2025-07-01", 10_000, 10_000, 10_000, 10_000, 1_000),
        ("2025-07-10", 1_000, 1_000, 1_000, 1_000, 10_000),
        ("2025-07-15", 100, 100, 100, 100, 100_000),
    ])
    out = adjust_ohlcv(df, [("2025-07-10", 10.0), ("2025-07-15", 10.0)])
    assert out.loc[0, "close"] == pytest.approx(100)      # /10 /10
    assert out.loc[0, "volume"] == pytest.approx(100_000)
    assert out.loc[1, "close"] == pytest.approx(100)      # /10 (second split only)
    assert out.loc[2, "close"] == pytest.approx(100)      # untouched


def test_no_splits_returns_frame_unchanged():
    df = _df([("2025-01-01", 100, 110, 90, 100, 1_000)])
    out = adjust_ohlcv(df, [])
    pd.testing.assert_frame_equal(out, df)


def test_invalid_ratios_are_skipped():
    df = _df([
        ("2025-01-01", 100, 100, 100, 100, 1_000),
        ("2025-01-02", 100, 100, 100, 100, 1_000),
    ])
    out = adjust_ohlcv(df, [("2025-01-02", 0.0), ("2025-01-02", -3.0),
                            ("2025-01-02", float("nan")), ("2025-01-02", 1.0)])
    assert out.loc[0, "close"] == pytest.approx(100)
    assert out.loc[0, "volume"] == pytest.approx(1_000)


# ─── load_split_factors ──────────────────────────────────────────────────────

def _mkdb(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,
        date TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL,
        volume REAL, is_final INTEGER DEFAULT 1, UNIQUE(ticker, date))""")
    conn.execute("""CREATE TABLE corporate_actions (
        ticker TEXT NOT NULL, date TEXT NOT NULL, action TEXT NOT NULL,
        value REAL, source TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (ticker, date, action))""")
    return conn


def test_load_split_factors_reads_splits_not_dividends():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        conn = _mkdb(db)
        conn.executemany(
            "INSERT INTO corporate_actions (ticker,date,action,value,source) VALUES (?,?,?,?,'t')",
            [("AAAA", "2025-06-01", "split", 2.0),
             ("AAAA", "2025-01-01", "split", 10.0),
             ("AAAA", "2025-03-01", "dividend", 25.0),
             ("BBBB", "2025-02-01", "split", 0.0)])   # invalid, dropped
        conn.commit()
        factors = load_split_factors(conn)
        conn.close()
    assert factors == {"AAAA": [("2025-01-01", 10.0), ("2025-06-01", 2.0)]}


def test_load_split_factors_fail_soft_without_table():
    conn = sqlite3.connect(":memory:")
    assert load_split_factors(conn) == {}
    conn.close()


# ─── loader integration ──────────────────────────────────────────────────────

def _seed_corpus(db):
    conn = _mkdb(db)
    rows = [("SPLT", "2025-01-01", 1000, 1000, 1000, 1000, 1_000, 1),
            ("SPLT", "2025-01-02", 500, 500, 500, 500, 2_000, 1),
            ("RAWW", "2025-01-01", 700, 700, 700, 700, 3_000, 1),
            ("RAWW", "2025-01-02", 710, 710, 710, 710, 3_000, 0)]  # provisional
    conn.executemany(
        "INSERT INTO ohlcv (ticker,date,open,high,low,close,volume,is_final) "
        "VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.execute(
        "INSERT INTO corporate_actions (ticker,date,action,value,source) "
        "VALUES ('SPLT','2025-01-02','split',2.0,'t')")
    conn.commit()
    conn.close()


def test_bulk_loader_adjusts_research_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_corpus(db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        out = _load_ohlcv_bulk(final_only=True)
    assert out["SPLT"].iloc[0]["close"] == pytest.approx(500)   # back-adjusted
    assert out["SPLT"].iloc[0]["volume"] == pytest.approx(2_000)
    assert out["SPLT"].iloc[1]["close"] == pytest.approx(500)
    assert out["RAWW"].iloc[0]["close"] == pytest.approx(700)   # no split, no change
    assert len(out["RAWW"]) == 1                                # is_final fence intact


def test_bulk_loader_live_path_stays_raw(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_corpus(db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        out = _load_ohlcv_bulk(final_only=False)
    assert out["SPLT"].iloc[0]["close"] == pytest.approx(1000)  # raw
    assert len(out["RAWW"]) == 2                                # partial bar included


def test_bulk_loader_adjusted_override(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_corpus(db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        adj = _load_ohlcv_bulk(final_only=False, adjusted=True)
        raw = _load_ohlcv_bulk(final_only=True, adjusted=False)
    assert adj["SPLT"].iloc[0]["close"] == pytest.approx(500)
    assert raw["SPLT"].iloc[0]["close"] == pytest.approx(1000)


def test_per_ticker_research_loader_is_adjusted_and_settled():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_corpus(db)
        conn = sqlite3.connect(db)
        from data.loaders import load_ohlcv_df
        splt = load_ohlcv_df(conn, "SPLT")
        raww = load_ohlcv_df(conn, "RAWW")
        raw_splt = load_ohlcv_df(conn, "SPLT", adjusted=False)
        conn.close()
    assert splt.iloc[0]["close"] == pytest.approx(500)      # split-adjusted
    assert splt.iloc[0]["volume"] == pytest.approx(2_000)
    assert len(raww) == 1                                   # is_final fence
    assert raww.iloc[0]["close"] == pytest.approx(700)
    assert raw_splt.iloc[0]["close"] == pytest.approx(1000)  # override works


def test_research_modules_do_not_hand_roll_price_reads():
    """Guard: every research price load must route through data.loaders (the
    adjusted path). A raw `SELECT ...open/high/low/close... FROM ohlcv` in
    research/ bypasses split adjustment — the exact hole audit R-1 found."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    price_read = re.compile(
        r"SELECT\s[^\"']*\b(open|high|low|close)\b[^\"']*\bFROM\s+ohlcv\b", re.I | re.S)
    offenders = []
    for p in (root / "research").rglob("*.py"):
        if price_read.search(p.read_text(encoding="utf-8")):
            offenders.append(str(p.relative_to(root)))
    assert not offenders, (
        "research/ reads raw ohlcv prices directly (must use data.loaders "
        f"adjusted path): {offenders}")


def test_storage_stays_raw(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_corpus(db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        _load_ohlcv_bulk(final_only=True)
        conn = sqlite3.connect(db)
        close0 = conn.execute(
            "SELECT close FROM ohlcv WHERE ticker='SPLT' AND date='2025-01-01'"
        ).fetchone()[0]
        conn.close()
    assert close0 == 1000   # loader never writes back
