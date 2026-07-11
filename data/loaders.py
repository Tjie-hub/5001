"""Data-platform loaders — shared floor (spec §2).

Moved verbatim from scheduler/utils.py in M2 so research/ can load the corpus
without importing execution modules. scheduler/utils re-exports both for
back-compat; both sides of the boundary import from here.
"""
import os

import pandas as pd

from data.db import connect as db_connect

DB_PATH = os.getenv("DB_PATH", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "walkforward.db"))


def get_all_tickers():
    """Return all active tickers: idx_tickers table first, fallback to ohlcv."""
    conn = db_connect(DB_PATH)
    # Prefer the master list (populated after discovery)
    try:
        rows = conn.execute(
            "SELECT ticker FROM idx_tickers WHERE status='active' ORDER BY ticker"
        ).fetchall()
        if rows:
            conn.close()
            return [r[0] for r in rows]
    except Exception:
        pass
    # Fallback: tickers already in ohlcv
    tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker").fetchall()]
    conn.close()
    return tickers


def load_ohlcv_df(conn, ticker: str, final_only: bool = True,
                  adjusted: bool = None) -> pd.DataFrame:
    """Per-ticker research loader: settled bars, split-adjusted (audit R-1).

    Studies must use this instead of hand-rolled `SELECT ... FROM ohlcv`
    (guard: tests/test_corporate_adjustments.py). Same flag semantics as
    _load_ohlcv_bulk; the caller owns `conn`.
    """
    from data.adjustments import load_split_factors, adjust_ohlcv

    if adjusted is None:
        adjusted = final_only
    where = "WHERE ticker=?"
    if final_only:
        where += " AND COALESCE(is_final, 1) = 1"
    try:
        df = pd.read_sql(
            f"SELECT date, open, high, low, close, volume FROM ohlcv "
            f"{where} ORDER BY date ASC", conn, params=(ticker,))
    except Exception:
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date ASC", conn, params=(ticker,))
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    if adjusted:
        splits = load_split_factors(conn).get(ticker, [])
        df = adjust_ohlcv(df, splits)
    return df


def _load_ohlcv_bulk(final_only: bool = False, adjusted: bool = None) -> dict:
    """Load all OHLCV in one query. Returns {ticker: DataFrame}.

    final_only=True excludes provisional intraday bars (is_final=0) — required
    for research jobs (WF refresh, backtest cache) so a partial 14:35 bar never
    contaminates scores (Phase 2A item 2.1). Live scans keep the default:
    partial bars ARE their signal input. COALESCE keeps pre-migration DBs and
    test fixtures without the column working.

    adjusted=None follows final_only: the research path (final_only=True) is
    back-adjusted through splits from corporate_actions (audit R-1) while live
    scans stay on the raw basis. Storage is never modified — adjustment applies
    to the loaded frames only (data/adjustments.py).
    """
    from data.adjustments import load_split_factors, adjust_ohlcv

    if adjusted is None:
        adjusted = final_only
    conn = db_connect(DB_PATH)
    if final_only:
        try:
            all_df = pd.read_sql(
                'SELECT * FROM ohlcv WHERE COALESCE(is_final, 1) = 1 '
                'ORDER BY ticker, date ASC', conn)
        except Exception:
            all_df = pd.read_sql('SELECT * FROM ohlcv ORDER BY ticker, date ASC', conn)
    else:
        all_df = pd.read_sql('SELECT * FROM ohlcv ORDER BY ticker, date ASC', conn)
    split_factors = load_split_factors(conn) if adjusted else {}
    conn.close()
    for c in ["open", "high", "low", "close", "volume"]:
        all_df[c] = all_df[c].astype(float)
    out = {t: grp.reset_index(drop=True) for t, grp in all_df.groupby("ticker")}
    for ticker, splits in split_factors.items():
        if ticker in out:
            out[ticker] = adjust_ohlcv(out[ticker], splits)
    return out
