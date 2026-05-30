"""
engine/indicators.py — Pure indicator functions for the IDX walk-forward system.

Each function accepts a DataFrame with OHLCV columns and returns a pd.Series
aligned to the input index. A `warmup_bars` lambda attribute declares how many
leading bars are required before the indicator produces valid values.
"""

import numpy as np
import pandas as pd


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # SMA-ATR intentional: less lag than Wilder's EWM, appropriate for position sizing.
    # Wilder's EWM is reserved for calc_adx where the formula requires it.
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

calc_atr.warmup_bars = lambda period=14: period


def calc_vwap(df: pd.DataFrame, window: int = 60) -> pd.Series:
    tp = (df['high'] + df['low'] + df['close']) / 3
    cum_tp_vol = (tp * df['volume']).rolling(window, min_periods=window).sum()
    cum_vol    = df['volume'].rolling(window, min_periods=window).sum()
    # Zero-volume windows (trading halts) yield NaN — callers should handle.
    return cum_tp_vol / cum_vol

calc_vwap.warmup_bars = lambda window=60: window


def calc_vol_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    # Rolling mean includes current bar, dampening VR spikes ~10%. Intentional conservatism.
    avg = df['volume'].rolling(period, min_periods=1).mean()
    return df['volume'] / avg

calc_vol_ratio.warmup_bars = lambda period=20: period
# warmup_bars reflects full-window accuracy, not first-value availability.
# With min_periods=1, a ratio exists from bar 1 but stabilises at bar period.


def calc_delta(df: pd.DataFrame) -> pd.Series:
    rng = (df['high'] - df['low']).replace(0, np.nan)
    return ((df['close'] - df['open']) / rng * df['volume']).fillna(0)

calc_delta.warmup_bars = lambda: 0


def calc_vwma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    # Zero-volume windows (trading halts) yield NaN — callers should handle.
    return (df['close'] * df['volume']).rolling(period, min_periods=period).sum() / \
            df['volume'].rolling(period, min_periods=period).sum()

calc_vwma.warmup_bars = lambda period=20: period


def calc_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df['close'].rolling(period, min_periods=1).mean()

calc_sma.warmup_bars = lambda period=20: period
# warmup_bars reflects full-window accuracy, not first-value availability.
# With min_periods=1, a value exists from bar 1 but converges at bar period.


def calc_relative_strength(ticker_df: pd.DataFrame, ihsg_df: pd.DataFrame, period: int = 20) -> float:
    if ticker_df is None or ihsg_df is None:
        return 1.0
    if len(ticker_df) < period + 1 or len(ihsg_df) < period + 1:
        return 1.0
    ticker_return = ticker_df['close'].iloc[-1] / ticker_df['close'].iloc[-period - 1] - 1
    ihsg_return   = ihsg_df['close'].iloc[-1]  / ihsg_df['close'].iloc[-period - 1]  - 1
    denominator   = 1 + ihsg_return
    if denominator == 0:
        return 1.0
    return (1 + ticker_return) / denominator

calc_relative_strength.warmup_bars = lambda period=20: period + 1
