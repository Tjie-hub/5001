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


def test_already_adjusted_series_is_not_double_adjusted():
    """REGRESSION (Phase A validation incident 2026-07-11): the corpus is
    split-adjusted at the source (yfinance adjusts OHLC for splits even with
    auto_adjust=False; the 2026-07-03 rebuild inherited that basis). A split
    factor may only be applied when the series actually shows the gap —
    blindly dividing an already-continuous series fabricates a rally
    (CUAN momentum printed +39%/trade before this guard)."""
    df = _df([
        ("2025-01-01", 1000, 1010, 990, 1000, 10_000),
        ("2025-01-02", 1010, 1020, 1000, 1010, 10_000),   # continuous: no gap
    ])
    out = adjust_ohlcv(df, [("2025-01-02", 2.0)])
    assert out.loc[0, "close"] == pytest.approx(1000)   # untouched
    assert out.loc[0, "volume"] == pytest.approx(10_000)


def test_small_ratios_below_verifiability_floor_are_skipped():
    """A 1.05 bonus-issue ratio is indistinguishable from a normal daily move —
    it can't be gap-verified, and its impact is immaterial. Skip."""
    df = _df([
        ("2025-01-01", 1000, 1010, 990, 1000, 10_000),
        ("2025-01-02", 952, 962, 942, 952, 10_500),   # ~5% drop, matches 1.05
    ])
    out = adjust_ohlcv(df, [("2025-01-02", 1.05)])
    assert out.loc[0, "close"] == pytest.approx(1000)


def test_reverse_split_on_continuous_series_is_skipped():
    """BBRM case: declared 2:3 reverse split, series dead flat — observed
    ratio 1.0 sits inside a naive [0.6r, 1.6r] band for r=0.667. The gap test
    must prefer 'already adjusted' (~1.0) over the declared ratio."""
    df = _df([
        ("2021-08-12", 67.77, 67.77, 67.77, 67.77, 1_000),
        ("2021-08-13", 67.77, 67.77, 67.77, 67.77, 1_000),
        ("2021-08-16", 67.77, 67.77, 67.77, 67.77, 1_000),
    ])
    out = adjust_ohlcv(df, [("2021-08-13", 2.0 / 3.0)])
    assert out.loc[0, "close"] == pytest.approx(67.77)


def test_single_bar_anomaly_is_not_a_split_gap():
    """TMAS case: one bad tick at the ex-date (298 -> 43 -> 286) mimics a 10:1
    gap but the price bounces straight back — a real basis change persists.
    Verification must look past the first post bar."""
    df = _df([
        ("2023-05-22", 298, 300, 296, 298, 1_000),
        ("2023-05-23", 43.3, 44, 43, 43.3, 1_000),    # bad tick
        ("2023-05-24", 286, 290, 284, 286, 1_000),
        ("2023-05-25", 296, 298, 294, 296, 1_000),
    ])
    out = adjust_ohlcv(df, [("2023-05-23", 10.0)])
    assert out.loc[0, "close"] == pytest.approx(298)   # untouched


def test_real_persistent_gap_still_adjusts():
    """A genuine split gap persists across post bars — must still apply."""
    df = _df([
        ("2025-01-02", 1000, 1010, 990, 1000, 1_000),
        ("2025-01-03", 102, 103, 101, 102, 10_000),
        ("2025-01-06", 99, 100, 98, 99, 10_000),
        ("2025-01-07", 101, 102, 100, 101, 10_000),
    ])
    out = adjust_ohlcv(df, [("2025-01-03", 10.0)])
    assert out.loc[0, "close"] == pytest.approx(100)
    assert out.loc[1, "close"] == pytest.approx(102)


def test_unverifiable_split_outside_history_is_skipped():
    df = _df([("2025-06-01", 100, 110, 90, 100, 1_000)])
    # ex-date before all bars: nothing to adjust; after all bars: no post bar
    out1 = adjust_ohlcv(df, [("2025-01-01", 2.0)])
    out2 = adjust_ohlcv(df, [("2025-12-01", 2.0)])
    assert out1.loc[0, "close"] == pytest.approx(100)
    assert out2.loc[0, "close"] == pytest.approx(100)


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
