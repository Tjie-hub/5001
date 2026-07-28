"""Conditioners (spec §6): tag a trade with a vol-tier and a liq-tier.

Pure and no-look-ahead — everything is computed from data available at the entry
bar. Cut-points are self-relative (vol vs the ticker's own median; liquidity vs a
multiple of the production eligibility floor).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from engine.liquidity import VALUE_LIQ_MIN_IDR


def _realized_vol(close: pd.Series, window: int) -> pd.Series:
    """Rolling std of daily returns (in %), the realized-vol proxy."""
    ret = close.pct_change() * 100.0
    return ret.rolling(window).std()


def vol_tier(df: pd.DataFrame, entry_date: str, window: int, median_lookback: int) -> str:
    """HIGH_VOL if realized vol at entry >= the ticker's own trailing median, else LOW_VOL.

    df must have 'date' (YYYY-MM-DD str) and 'close'. Only bars with date <= entry_date
    are used (no look-ahead)."""
    hist = df[df["date"] <= entry_date].tail(median_lookback + window + 5)
    if len(hist) < window + 2:
        return "LOW_VOL"
    rv = _realized_vol(hist["close"].reset_index(drop=True), window).dropna()
    if rv.empty:
        return "LOW_VOL"
    current = rv.iloc[-1]
    median = rv.median()
    return "HIGH_VOL" if current >= median else "LOW_VOL"


def liq_tier(adv_value: Optional[float], high_multiple: float) -> str:
    """HIGH_LIQ if 30-day ADV value >= high_multiple * the production liquidity floor."""
    if adv_value is None:
        return "LOW_LIQ"
    return "HIGH_LIQ" if adv_value >= high_multiple * VALUE_LIQ_MIN_IDR else "LOW_LIQ"
