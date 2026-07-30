"""Data-platform loaders — shared floor (spec §2).

Moved verbatim from scheduler/utils.py in M2 so research/ can load the corpus
without importing execution modules. scheduler/utils re-exports both for
back-compat; both sides of the boundary import from here.
"""
import os

import pandas as pd

from data.db import connect as db_connect
from config import DB_PATH


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


def _load_ohlcv_bulk(final_only: bool = False) -> dict:
    """Load all OHLCV in one query. Returns {ticker: DataFrame}.

    final_only=True excludes provisional intraday bars (is_final=0) — required
    for research jobs (WF refresh, backtest cache) so a partial 14:35 bar never
    contaminates scores (Phase 2A item 2.1). Live scans keep the default:
    partial bars ARE their signal input. COALESCE keeps pre-migration DBs and
    test fixtures without the column working.
    """
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
    conn.close()
    for c in ["open", "high", "low", "close", "volume"]:
        all_df[c] = all_df[c].astype(float)
    return {t: grp.reset_index(drop=True) for t, grp in all_df.groupby("ticker")}
