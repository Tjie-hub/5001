"""
engine/indicators.py — Pure indicator functions for the IDX walk-forward system.

Each function accepts a DataFrame with OHLCV columns and returns a pd.Series
aligned to the input index. A `warmup_bars` lambda attribute declares how many
leading bars are required before the indicator produces valid values.
"""

import numpy as np
import pandas as pd
import sqlite3
from config import DB_PATH

# ── R16: Session-level indicator cache ───────────────────────────────────────
# Keyed by (func_name, id(df), *params). Safe within a scan session because
# ohlcv_map holds strong references to each df — id() stability guaranteed.
# Call clear_indicator_cache() at the start of each scan to prevent stale hits.
_INDICATOR_CACHE: dict = {}


def clear_indicator_cache() -> int:
    """Flush the session cache. Returns number of entries cleared."""
    n = len(_INDICATOR_CACHE)
    _INDICATOR_CACHE.clear()
    return n


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # SMA-ATR intentional: less lag than Wilder's EWM, appropriate for position sizing.
    # Wilder's EWM is reserved for calc_adx where the formula requires it.
    _key = ('atr', id(df), period)
    if _key in _INDICATOR_CACHE:
        return _INDICATOR_CACHE[_key]
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    result = tr.rolling(period, min_periods=period).mean()
    _INDICATOR_CACHE[_key] = result
    return result

calc_atr.warmup_bars = lambda period=14: period


def calc_vwap(df: pd.DataFrame, window: int = 60) -> pd.Series:
    _key = ('vwap', id(df), window)
    if _key in _INDICATOR_CACHE:
        return _INDICATOR_CACHE[_key]
    tp = (df['high'] + df['low'] + df['close']) / 3
    cum_tp_vol = (tp * df['volume']).rolling(window, min_periods=window).sum()
    cum_vol    = df['volume'].rolling(window, min_periods=window).sum()
    # Zero-volume windows (trading halts) yield NaN — callers should handle.
    result = cum_tp_vol / cum_vol
    _INDICATOR_CACHE[_key] = result
    return result

calc_vwap.warmup_bars = lambda window=60: window


def calc_vol_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    # Rolling mean includes current bar, dampening VR spikes ~10%. Intentional conservatism.
    _key = ('vol_ratio', id(df), period)
    if _key in _INDICATOR_CACHE:
        return _INDICATOR_CACHE[_key]
    avg = df['volume'].rolling(period, min_periods=1).mean()
    result = df['volume'] / avg
    _INDICATOR_CACHE[_key] = result
    return result

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
    _key = ('weekly_trend', id(df))
    if _key in _INDICATOR_CACHE:
        return _INDICATOR_CACHE[_key]
    if len(df) < 100:
        result = (True, 'W:insufficient_data')
        _INDICATOR_CACHE[_key] = result
        return result
    try:
        dfc = df.copy()
        if not isinstance(dfc.index, pd.DatetimeIndex):
            dfc['date'] = pd.to_datetime(dfc['date'])
            dfc = dfc.set_index('date')
        weekly = dfc['close'].resample('W').last().dropna()
        if len(weekly) < 22:
            result = (True, 'W:insufficient_weeks')
            _INDICATOR_CACHE[_key] = result
            return result
        wma20    = weekly.rolling(20).mean()
        cur_c    = weekly.iloc[-1]
        cur_ma20 = wma20.iloc[-1]
        if pd.isna(cur_ma20) or cur_ma20 <= 0:
            result = (True, 'W:ma20_nan')
            _INDICATOR_CACHE[_key] = result
            return result
        ma20_5w  = wma20.iloc[-6] if len(wma20) >= 6 else wma20.iloc[0]
        slope    = float((cur_ma20 - ma20_5w) / ma20_5w * 100) if ma20_5w > 0 else 0.0
        if cur_c >= cur_ma20 and slope >= -1.0:
            result = (True,  f'W:OK c={cur_c:.0f}≥ma20={cur_ma20:.0f} slope={slope:+.1f}%')
        else:
            result = (False, f'W:FAIL c={cur_c:.0f}<ma20={cur_ma20:.0f} slope={slope:+.1f}%')
        _INDICATOR_CACHE[_key] = result
        return result
    except Exception as e:
        return True, f'W:error({e})'

calc_weekly_trend.warmup_bars = lambda: 100


def get_warmup(funcs: list) -> int:
    """Return max warmup_bars (with default params) across a list of indicator functions."""
    if not funcs:
        return 0
    return max(fn.warmup_bars() for fn in funcs)


class IndicatorCache:
    """SQLite-backed cache for indicator Series, keyed by (ticker, indicator, period)."""

    def __init__(self, db_path: str = DB_PATH):
        self._db = db_path
        self._init_table()

    def _init_table(self):
        conn = sqlite3.connect(self._db)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_cache (
                    ticker    TEXT    NOT NULL,
                    date      TEXT    NOT NULL,
                    indicator TEXT    NOT NULL,
                    period    INTEGER NOT NULL,
                    value     REAL,
                    PRIMARY KEY (ticker, date, indicator, period)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def put(self, ticker: str, indicator: str, period: int, series: pd.Series):
        conn = sqlite3.connect(self._db)
        try:
            rows = [
                (ticker, str(date), indicator, period,
                 float(val) if not pd.isna(val) else None)
                for date, val in series.items()
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO indicator_cache "
                "(ticker, date, indicator, period, value) VALUES (?,?,?,?,?)",
                rows
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, ticker: str, indicator: str, period: int,
            dates: list) -> 'pd.Series | None':
        conn = sqlite3.connect(self._db)
        try:
            placeholders = ','.join('?' * len(dates))
            rows = conn.execute(
                f"SELECT date, value FROM indicator_cache "
                f"WHERE ticker=? AND indicator=? AND period=? AND date IN ({placeholders})",
                [ticker, indicator, period] + [str(d) for d in dates]
            ).fetchall()
        finally:
            conn.close()
        if len(rows) < len(dates):
            return None
        return pd.Series({r[0]: r[1] for r in rows})

    def clear(self, ticker: str):
        conn = sqlite3.connect(self._db)
        try:
            conn.execute("DELETE FROM indicator_cache WHERE ticker=?", (ticker,))
            conn.commit()
        finally:
            conn.close()


def classify_volume_context(df: pd.DataFrame) -> str:
    """
    Classify the volume spike context of the last bar.
    Returns one of: 'crash_absorption', 'exhaustion_distribution',
                    'breakout_accumulation', 'normal'.

    Priority order:
      crash_absorption:        VR >= 2.0x AND close >= 20% below 20d high
      exhaustion_distribution: VR >= 2.0x AND bearish close AND within 5% of 20d high
      breakout_accumulation:   VR >= 1.5x AND within 5% of 20d high AND above MA20
      normal:                  everything else
    """
    if len(df) < 20:
        return "normal"

    close_s  = df["close"].astype(float)
    high_20d = df["high"].astype(float).rolling(20).max().iloc[-1]
    ma20     = close_s.rolling(20).mean().iloc[-1]
    last     = df.iloc[-1]
    cl       = float(last["close"])
    op       = float(last["open"])
    vr       = calc_vol_ratio(df, 20).iloc[-1]

    if pd.isna(vr) or pd.isna(high_20d) or high_20d <= 0:
        return "normal"

    pct_from_high = (cl - high_20d) / high_20d  # negative = below high

    if vr >= 2.0 and pct_from_high <= -0.20:
        return "crash_absorption"
    if vr >= 2.0 and cl < op and pct_from_high >= -0.05:
        return "exhaustion_distribution"
    if vr >= 1.5 and pct_from_high >= -0.05 and not pd.isna(ma20) and cl > ma20:
        return "breakout_accumulation"
    return "normal"
