"""
Strategy Filter Library

Provides common filter functions for strategy entry conditions.
Filters can be combined via apply_filters().

Usage:
    from engine.strategies.filters import filter_vwma_above, apply_filters

    signals = my_entry_signal(df)
    filtered_signals = apply_filters(df, [filter_vwma_above, filter_above_ma50])
"""

import pandas as pd

from engine.indicators import (
    calc_atr,
    calc_sma,
    calc_vol_ratio,
    calc_vwma,
)


# ─────────────────────────────────────────────
# INDIVIDUAL FILTERS
# ─────────────────────────────────────────────

def filter_vwma_above(df: pd.DataFrame) -> pd.Series:
    """Price above VWMA 20 — bullish trend filter."""
    vwma = calc_vwma(df, 20)
    return df['close'] > vwma


def filter_above_ma50(df: pd.DataFrame) -> pd.Series:
    """Price above MA 50 — medium-term trend filter."""
    return df['close'] > calc_sma(df, 50)


def filter_low_atr(df: pd.DataFrame) -> pd.Series:
    """ATR below 1.2x ATR MA — avoid excessively volatile days."""
    atr = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    return atr < atr_ma * 1.2


def filter_vr_min(df: pd.DataFrame, threshold: float = 1.3) -> pd.Series:
    """Volume ratio above threshold — volume confirmation."""
    return calc_vol_ratio(df, 20) >= threshold


def filter_uptrend(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Close higher than N days ago — momentum trend."""
    return df['close'] > df['close'].shift(lookback)


# ─────────────────────────────────────────────
# FILTER COMBINER
# ─────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, filters: list) -> pd.Series:
    """
    Apply all filters with AND logic.

    Args:
        df: OHLCV DataFrame
        filters: List of filter functions (each takes df, returns Series)

    Returns:
        Boolean Series (True where all filters pass)
    """
    mask = pd.Series(True, index=df.index)
    for f in filters:
        mask = mask & f(df)
    return mask


__all__ = [
    'filter_vwma_above',
    'filter_above_ma50',
    'filter_low_atr',
    'filter_vr_min',
    'filter_uptrend',
    'apply_filters',
]
