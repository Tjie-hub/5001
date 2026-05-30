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


def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # Wilder's EWM required — ADX/DMI defined this way per Welles Wilder's spec.
    high, low, close = df['high'], df['low'], df['close']
    plus_dm  = high.diff()
    minus_dm = -low.diff()
    plus_dm  = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr  = pd.concat([high - low,
                     (high - close.shift(1)).abs(),
                     (low  - close.shift(1)).abs()], axis=1).max(axis=1)
    atr      = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di  = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/period, min_periods=period).mean()

calc_adx.warmup_bars = lambda period=14: period * 2


def calc_ma_slope(df: pd.DataFrame, ma_period: int = 20, slope_window: int = 5) -> pd.Series:
    ma = df['close'].rolling(ma_period, min_periods=ma_period).mean()
    return (ma - ma.shift(slope_window)) / ma.shift(slope_window) * 100

calc_ma_slope.warmup_bars = lambda ma_period=20, slope_window=5: ma_period + slope_window


def calc_vr_mean(df: pd.DataFrame, vr_period: int = 20, mean_window: int = 10) -> pd.Series:
    avg_vol = df['volume'].rolling(vr_period, min_periods=1).mean()
    vr = df['volume'] / avg_vol.replace(0, np.nan)
    return vr.rolling(mean_window, min_periods=1).mean()

calc_vr_mean.warmup_bars = lambda vr_period=20, mean_window=10: vr_period + mean_window


def calc_price_range_pct(df: pd.DataFrame, window: int = 20) -> pd.Series:
    highest = df['high'].rolling(window, min_periods=1).max()
    lowest  = df['low'].rolling(window, min_periods=1).min()
    return (highest - lowest) / lowest.replace(0, np.nan) * 100

calc_price_range_pct.warmup_bars = lambda window=20: window


def calc_close_vs_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    ma = df['close'].rolling(period, min_periods=period).mean()
    return (df['close'] - ma) / ma * 100

calc_close_vs_ma.warmup_bars = lambda period=20: period


def calc_weekly_trend(df: pd.DataFrame) -> tuple:
    """Returns (passes: bool, reason: str). Soft-pass if < 100 bars."""
    if len(df) < 100:
        return True, 'W:insufficient_data'
    try:
        dfc = df.copy()
        if not isinstance(dfc.index, pd.DatetimeIndex):
            dfc['date'] = pd.to_datetime(dfc['date'])
            dfc = dfc.set_index('date')
        weekly = dfc['close'].resample('W').last().dropna()
        if len(weekly) < 22:
            return True, 'W:insufficient_weeks'
        wma20    = weekly.rolling(20).mean()
        cur_c    = weekly.iloc[-1]
        cur_ma20 = wma20.iloc[-1]
        if pd.isna(cur_ma20) or cur_ma20 <= 0:
            return True, 'W:ma20_nan'
        ma20_5w  = wma20.iloc[-6] if len(wma20) >= 6 else wma20.iloc[0]
        slope    = float((cur_ma20 - ma20_5w) / ma20_5w * 100) if ma20_5w > 0 else 0.0
        if cur_c >= cur_ma20 and slope >= -1.0:
            return True,  f'W:OK c={cur_c:.0f}≥ma20={cur_ma20:.0f} slope={slope:+.1f}%'
        return False, f'W:FAIL c={cur_c:.0f}<ma20={cur_ma20:.0f} slope={slope:+.1f}%'
    except Exception as e:
        return True, f'W:error({e})'

calc_weekly_trend.warmup_bars = lambda: 100


def get_warmup(funcs: list) -> int:
    """Return max warmup_bars (with default params) across a list of indicator functions."""
    if not funcs:
        return 0
    return max(fn.warmup_bars() for fn in funcs)
