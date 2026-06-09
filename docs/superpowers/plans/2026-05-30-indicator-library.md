# Indicator Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract all indicator math from `engine/strategies.py` and `engine/regime_filter.py` into a new `engine/indicators.py` with warmup metadata, consistent NaN handling, SQLite-backed caching, and a full single-pass migration of all import sites.

**Architecture:** `engine/indicators.py` is a flat module of pure functions plus an `IndicatorCache` class backed by `walkforward.db`. Each function has a `warmup_bars` callable attribute; `get_warmup()` returns the max across a list. All callers are hard-cut to import from `engine.indicators` in one pass — no shims remain in `strategies.py` or `regime_filter.py`.

**Tech Stack:** Python, pandas, numpy, sqlite3, pytest

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| **Create** | `engine/indicators.py` | All `calc_*` functions, `IndicatorCache`, `get_warmup` |
| **Create** | `tests/test_indicators.py` | Unit tests for all indicators + cache |
| **Modify** | `engine/strategies.py` | Remove 7 `calc_*` defs; add import from `engine.indicators` |
| **Modify** | `engine/regime_filter.py` | Remove 5 `calc_*` defs; add import from `engine.indicators` |
| **Modify** | `engine/optimizer.py` | Move `calc_atr/vol_ratio/vwap` import to `engine.indicators` |
| **Modify** | `engine/swing_screener.py` | Move `calc_atr/vol_ratio` import to `engine.indicators` |
| **Modify** | `routes/backtest.py` | Update inline `calc_vol_ratio` import |
| **Modify** | `scheduler/scanner.py` | Update inline `calc_vol_ratio/calc_relative_strength` import |
| **Modify** | `monitor.py` | Update inline `calc_atr` import |
| **Modify** | `engine/walkforward_multi.py` | Replace `WARMUP_BARS = 75` with `get_warmup(...)` |
| **Modify** | `scheduler/utils.py` | Add `IndicatorCache.clear(ticker)` in `fetch_latest` |

---

## Task 1: Create `engine/indicators.py` with `strategies.py` functions

**Files:**
- Create: `engine/indicators.py`
- Create: `tests/test_indicators.py`

- [x] **Step 1: Write failing tests**

```python
# tests/test_indicators.py
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def ohlcv():
    n = 40
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(n) * 10)
    high = close + np.abs(np.random.randn(n) * 5)
    low  = close - np.abs(np.random.randn(n) * 5)
    return pd.DataFrame({
        'date':   pd.date_range('2025-01-01', periods=n),
        'open':   close - np.random.randn(n) * 3,
        'high':   high,
        'low':    low,
        'close':  close,
        'volume': np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })


class TestCalcAtr:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_atr
        assert isinstance(calc_atr(ohlcv, period=14), pd.Series)

    def test_length_matches(self, ohlcv):
        from engine.indicators import calc_atr
        assert len(calc_atr(ohlcv, period=14)) == len(ohlcv)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_atr
        result = calc_atr(ohlcv, period=14)
        assert result.iloc[:13].isna().all()

    def test_no_nan_after_warmup(self, ohlcv):
        from engine.indicators import calc_atr
        result = calc_atr(ohlcv, period=14)
        assert not result.iloc[14:].isna().any()

    def test_positive_values(self, ohlcv):
        from engine.indicators import calc_atr
        assert (calc_atr(ohlcv, period=14).dropna() > 0).all()


class TestCalcVwap:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vwap
        assert isinstance(calc_vwap(ohlcv, window=20), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_vwap
        result = calc_vwap(ohlcv, window=20)
        assert result.iloc[:19].isna().all()

    def test_no_nan_after_warmup(self, ohlcv):
        from engine.indicators import calc_vwap
        assert not calc_vwap(ohlcv, window=20).iloc[20:].isna().any()


class TestCalcVolRatio:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert isinstance(calc_vol_ratio(ohlcv, period=20), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert not calc_vol_ratio(ohlcv, period=20).isna().any()

    def test_mean_near_one(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert abs(calc_vol_ratio(ohlcv, period=20).mean() - 1.0) < 0.5


class TestCalcDelta:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_delta
        assert isinstance(calc_delta(ohlcv), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_delta
        assert not calc_delta(ohlcv).isna().any()


class TestCalcVwma:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vwma
        assert isinstance(calc_vwma(ohlcv, period=20), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_vwma
        assert calc_vwma(ohlcv, period=20).iloc[:19].isna().all()


class TestCalcSma:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_sma
        assert isinstance(calc_sma(ohlcv, period=20), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_sma
        assert not calc_sma(ohlcv, period=20).isna().any()

    def test_converges_to_rolling_mean(self, ohlcv):
        from engine.indicators import calc_sma
        result   = calc_sma(ohlcv, period=20)
        expected = ohlcv['close'].rolling(20).mean().iloc[20]
        assert abs(result.iloc[20] - expected) < 0.01


class TestCalcRelativeStrength:
    def test_returns_float(self, ohlcv):
        from engine.indicators import calc_relative_strength
        assert isinstance(calc_relative_strength(ohlcv, ohlcv, period=20), float)

    def test_same_ticker_is_one(self, ohlcv):
        from engine.indicators import calc_relative_strength
        assert abs(calc_relative_strength(ohlcv, ohlcv, period=20) - 1.0) < 0.001

    def test_none_fallback(self):
        from engine.indicators import calc_relative_strength
        assert calc_relative_strength(None, None) == 1.0
```

- [x] **Step 2: Run to confirm import failure**

```
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
pytest tests/test_indicators.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'engine.indicators'`

- [x] **Step 3: Create `engine/indicators.py`**

```python
# engine/indicators.py
"""
Indicator library — pure OHLCV math functions.
Each function has a warmup_bars attribute (callable with matching default params)
indicating the minimum bars required before the output is fully valid.
"""
import numpy as np
import pandas as pd


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # SMA-ATR intentional: less lag than Wilder's EWM, appropriate for position sizing.
    # Wilder's EWM is reserved for calc_adx where the formula requires it.
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l,
                    (h - c.shift()).abs(),
                    (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()
calc_atr.warmup_bars = lambda period=14: period


def calc_vwap(df: pd.DataFrame, window: int = 60) -> pd.Series:
    tp = (df['high'] + df['low'] + df['close']) / 3
    cum_tp_vol = (tp * df['volume']).rolling(window, min_periods=window).sum()
    cum_vol    = df['volume'].rolling(window, min_periods=window).sum()
    return cum_tp_vol / cum_vol
calc_vwap.warmup_bars = lambda window=60: window


def calc_vol_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    # Rolling mean includes current bar, dampening VR spikes ~10%. Intentional conservatism.
    avg = df['volume'].rolling(period, min_periods=1).mean()
    return df['volume'] / avg
calc_vol_ratio.warmup_bars = lambda period=20: period


def calc_delta(df: pd.DataFrame) -> pd.Series:
    rng = (df['high'] - df['low']).replace(0, np.nan)
    return ((df['close'] - df['open']) / rng * df['volume']).fillna(0)
calc_delta.warmup_bars = lambda: 0


def calc_vwma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return (df['close'] * df['volume']).rolling(period, min_periods=period).sum() / \
            df['volume'].rolling(period, min_periods=period).sum()
calc_vwma.warmup_bars = lambda period=20: period


def calc_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df['close'].rolling(period, min_periods=1).mean()
calc_sma.warmup_bars = lambda period=20: period


def calc_relative_strength(ticker_df: pd.DataFrame, ihsg_df: pd.DataFrame,
                            period: int = 20) -> float:
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
```

- [x] **Step 4: Run tests**

```
pytest tests/test_indicators.py -v
```

Expected: All 16 tests pass.

- [x] **Step 5: Commit**

```bash
git add engine/indicators.py tests/test_indicators.py
git commit -m "feat(r9): create engine/indicators.py with strategies.py indicator functions"
```

---

## Task 2: Add regime_filter indicators, `calc_weekly_trend`, warmup metadata, `get_warmup`

**Files:**
- Modify: `engine/indicators.py`
- Modify: `tests/test_indicators.py`

- [x] **Step 1: Append failing tests to `tests/test_indicators.py`**

```python
class TestCalcAdx:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_adx
        assert isinstance(calc_adx(ohlcv, period=14), pd.Series)

    def test_range_0_to_100(self, ohlcv):
        from engine.indicators import calc_adx
        valid = calc_adx(ohlcv, period=14).dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


class TestCalcMaSlope:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_ma_slope
        assert isinstance(calc_ma_slope(ohlcv), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_ma_slope
        # ma_period=20 + shift of slope_window=5 → first 24 rows NaN
        assert calc_ma_slope(ohlcv, ma_period=20, slope_window=5).iloc[:24].isna().all()


class TestCalcVrMean:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vr_mean
        assert isinstance(calc_vr_mean(ohlcv), pd.Series)


class TestCalcPriceRangePct:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_price_range_pct
        assert isinstance(calc_price_range_pct(ohlcv, window=20), pd.Series)

    def test_non_negative(self, ohlcv):
        from engine.indicators import calc_price_range_pct
        assert (calc_price_range_pct(ohlcv, window=20).dropna() >= 0).all()


class TestCalcCloseVsMa:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_close_vs_ma
        assert isinstance(calc_close_vs_ma(ohlcv, period=20), pd.Series)


class TestCalcWeeklyTrend:
    def test_insufficient_data_soft_pass(self, ohlcv):
        from engine.indicators import calc_weekly_trend
        passes, reason = calc_weekly_trend(ohlcv)   # 40 bars < 100
        assert passes is True and 'insufficient' in reason

    def test_uptrend_returns_bool_and_str(self):
        from engine.indicators import calc_weekly_trend
        n = 150
        close = pd.Series(range(1000, 1000 + n), dtype=float)
        df = pd.DataFrame({
            'date':  pd.date_range('2024-01-01', periods=n),
            'close': close,
        })
        passes, reason = calc_weekly_trend(df)
        assert isinstance(passes, bool) and isinstance(reason, str)


class TestWarmupMetadata:
    def test_calc_atr_default(self):
        from engine.indicators import calc_atr
        assert calc_atr.warmup_bars() == 14

    def test_calc_atr_custom(self):
        from engine.indicators import calc_atr
        assert calc_atr.warmup_bars(period=7) == 7

    def test_calc_adx_default(self):
        from engine.indicators import calc_adx
        assert calc_adx.warmup_bars() == 28

    def test_calc_vwap_default(self):
        from engine.indicators import calc_vwap
        assert calc_vwap.warmup_bars() == 60

    def test_get_warmup_returns_max(self):
        from engine.indicators import get_warmup, calc_atr, calc_adx, calc_vwap
        assert get_warmup([calc_atr, calc_adx, calc_vwap]) == 60

    def test_get_warmup_empty(self):
        from engine.indicators import get_warmup
        assert get_warmup([]) == 0
```

- [x] **Step 2: Run to confirm failures**

```
pytest tests/test_indicators.py::TestCalcAdx tests/test_indicators.py::TestWarmupMetadata -v 2>&1 | head -20
```

Expected: `ImportError` for `calc_adx`, `get_warmup`.

- [x] **Step 3: Append to `engine/indicators.py`**

```python
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
```

- [x] **Step 4: Run all tests**

```
pytest tests/test_indicators.py -v
```

Expected: All tests pass.

- [x] **Step 5: Commit**

```bash
git add engine/indicators.py tests/test_indicators.py
git commit -m "feat(r9): add regime_filter indicators, calc_weekly_trend, warmup metadata, get_warmup"
```

---

## Task 3: Add `IndicatorCache`

**Files:**
- Modify: `engine/indicators.py`
- Modify: `tests/test_indicators.py`

- [x] **Step 1: Append failing tests to `tests/test_indicators.py`**

```python
class TestIndicatorCache:
    def test_put_and_get_full_hit(self, tmp_path):
        from engine.indicators import IndicatorCache
        cache  = IndicatorCache(db_path=str(tmp_path / 'test.db'))
        series = pd.Series({'2025-01-01': 10.0, '2025-01-02': 11.0, '2025-01-03': 12.0})
        cache.put('BBCA', 'atr', 14, series)
        result = cache.get('BBCA', 'atr', 14, ['2025-01-01', '2025-01-02', '2025-01-03'])
        assert result is not None and len(result) == 3
        assert abs(result['2025-01-01'] - 10.0) < 0.001

    def test_get_miss_returns_none(self, tmp_path):
        from engine.indicators import IndicatorCache
        cache = IndicatorCache(db_path=str(tmp_path / 'test.db'))
        assert cache.get('BBCA', 'atr', 14, ['2025-01-01']) is None

    def test_partial_miss_returns_none(self, tmp_path):
        from engine.indicators import IndicatorCache
        cache = IndicatorCache(db_path=str(tmp_path / 'test.db'))
        cache.put('BBCA', 'atr', 14, pd.Series({'2025-01-01': 10.0}))
        assert cache.get('BBCA', 'atr', 14, ['2025-01-01', '2025-01-02']) is None

    def test_clear_removes_ticker(self, tmp_path):
        from engine.indicators import IndicatorCache
        cache = IndicatorCache(db_path=str(tmp_path / 'test.db'))
        cache.put('BBCA', 'atr', 14, pd.Series({'2025-01-01': 10.0}))
        cache.clear('BBCA')
        assert cache.get('BBCA', 'atr', 14, ['2025-01-01']) is None

    def test_clear_leaves_other_tickers(self, tmp_path):
        from engine.indicators import IndicatorCache
        cache = IndicatorCache(db_path=str(tmp_path / 'test.db'))
        cache.put('BBCA', 'atr', 14, pd.Series({'2025-01-01': 10.0}))
        cache.put('TLKM', 'atr', 14, pd.Series({'2025-01-01': 20.0}))
        cache.clear('BBCA')
        result = cache.get('TLKM', 'atr', 14, ['2025-01-01'])
        assert result is not None and abs(result['2025-01-01'] - 20.0) < 0.001
```

- [x] **Step 2: Run to confirm failures**

```
pytest tests/test_indicators.py::TestIndicatorCache -v 2>&1 | head -15
```

Expected: `ImportError: cannot import name 'IndicatorCache'`

- [x] **Step 3: Append `IndicatorCache` to `engine/indicators.py`**

```python
import sqlite3
from config import DB_PATH


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
```

- [x] **Step 4: Run all tests**

```
pytest tests/test_indicators.py -v
```

Expected: All tests pass.

- [x] **Step 5: Commit**

```bash
git add engine/indicators.py tests/test_indicators.py
git commit -m "feat(r9): add IndicatorCache to engine/indicators.py"
```

---

## Task 4: Migrate `engine/strategies.py`

**Files:**
- Modify: `engine/strategies.py`

Remove 7 `calc_*` definitions; replace with a single import block. Also replace two inline `rolling().mean()` calls with `calc_sma`.

- [x] **Step 1: Add import block at top of `engine/strategies.py`**

After the existing `import numpy as np` / `import pandas as pd` lines, add:

```python
from engine.indicators import (
    calc_atr,
    calc_delta,
    calc_relative_strength,
    calc_sma,
    calc_vwap,
    calc_vol_ratio,
    calc_vwma,
    calc_weekly_trend,
)
```

- [x] **Step 2: Delete `calc_vwap` definition**

Remove these lines (currently around line 36):
```python
def calc_vwap(df: pd.DataFrame, window: int = 60) -> pd.Series:
    """Rolling VWAP 60 hari — lebih relevan untuk sinyal entry."""
    tp = (df['high'] + df['low'] + df['close']) / 3
    cum_tp_vol = (tp * df['volume']).rolling(window).sum()
    cum_vol    = df['volume'].rolling(window).sum()
    return cum_tp_vol / cum_vol
```

- [x] **Step 3: Delete `calc_atr` definition**

Remove these lines (currently around line 43):
```python
def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    # SMA-ATR intentional: simpler, less lag than Wilder's EWM, appropriate for position sizing.
    # Wilder's EWM is reserved for ADX/DMI in regime_filter.py where the formula requires it.
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l,
                    (h - c.shift()).abs(),
                    (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()
```

- [x] **Step 4: Delete `calc_vol_ratio`, `calc_relative_strength`, `calc_delta` definitions**

Remove these three functions (currently around lines 52–74):
```python
def calc_vol_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    ...
def calc_relative_strength(ticker_df: pd.DataFrame, ihsg_df: pd.DataFrame, period: int = 20) -> float:
    ...
def calc_delta(df: pd.DataFrame) -> pd.Series:
    ...
```

- [x] **Step 5: Delete `calc_vwma` definition**

Remove these lines (currently around line 365):
```python
def calc_vwma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volume Weighted Moving Average."""
    return (df['close'] * df['volume']).rolling(period).sum() / \
            df['volume'].rolling(period).sum()
```

- [x] **Step 6: Delete `calc_weekly_trend` definition**

Remove the entire `calc_weekly_trend` function (currently around lines 1202–1238).

- [x] **Step 7: Replace inline rolling in `filter_above_ma50`**

Find (around line 139):
```python
    return df['close'] > df['close'].rolling(50).mean()
```
Replace with:
```python
    return df['close'] > calc_sma(df, 50)
```

- [x] **Step 8: Replace inline rolling in `strategy_conservative`**

Find (around line 348):
```python
    ma20  = df['close'].rolling(20).mean()
```
Replace with:
```python
    ma20  = calc_sma(df, 20)
```

- [x] **Step 9: Run full test suite**

```
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass.

- [x] **Step 10: Commit**

```bash
git add engine/strategies.py
git commit -m "refactor(r9): remove calc_* from strategies.py, import from engine.indicators"
```

---

## Task 5: Migrate `engine/regime_filter.py`

**Files:**
- Modify: `engine/regime_filter.py`

- [x] **Step 1: Add import after existing imports in `engine/regime_filter.py`**

After the `try/except yfinance` block (around line 24), add:

```python
from engine.indicators import (
    calc_adx,
    calc_close_vs_ma,
    calc_ma_slope,
    calc_price_range_pct,
    calc_vr_mean,
)
```

- [x] **Step 2: Delete `calc_adx` definition**

Remove the entire function (lines 33–55):
```python
def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    ...
```

- [x] **Step 3: Delete `calc_ma_slope`, `calc_vr_mean`, `calc_price_range_pct`, `calc_close_vs_ma` definitions**

Remove all four functions (lines 58–82).

- [x] **Step 4: Run full test suite**

```
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass.

- [x] **Step 5: Commit**

```bash
git add engine/regime_filter.py
git commit -m "refactor(r9): remove calc_* from regime_filter.py, import from engine.indicators"
```

---

## Task 6: Migrate `engine/optimizer.py` and `engine/swing_screener.py`

**Files:**
- Modify: `engine/optimizer.py`
- Modify: `engine/swing_screener.py`

- [x] **Step 1: Update `engine/optimizer.py` imports**

Find the `from engine.strategies import (...)` block (lines 13–23). Remove `calc_atr`, `calc_delta`, `calc_vol_ratio`, `calc_vwap` from it. Add a new import line directly above it:

```python
from engine.indicators import calc_atr, calc_delta, calc_vol_ratio, calc_vwap
from engine.strategies import (
    Trade,
    apply_costs,
    lot_size,
    run_strategy,
    _watch_signal_block,
)
```

- [x] **Step 2: Update `engine/swing_screener.py`**

Find (line 21):
```python
from engine.strategies import calc_atr, calc_vol_ratio
```
Replace with:
```python
from engine.indicators import calc_atr, calc_vol_ratio
```

- [x] **Step 3: Run tests**

```
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass.

- [x] **Step 4: Commit**

```bash
git add engine/optimizer.py engine/swing_screener.py
git commit -m "refactor(r9): update optimizer.py + swing_screener.py imports to engine.indicators"
```

---

## Task 7: Migrate inline imports in routes, scheduler, monitor

**Files:**
- Modify: `routes/backtest.py`
- Modify: `scheduler/scanner.py`
- Modify: `monitor.py`

- [x] **Step 1: Update `routes/backtest.py`**

Find the inline import (around line 918, inside a function body):
```python
from engine.strategies import calc_vol_ratio
```
Replace with:
```python
from engine.indicators import calc_vol_ratio
```

- [x] **Step 2: Update `scheduler/scanner.py`**

Find the inline import (around line 218, inside a function body):
```python
from engine.strategies import calc_vol_ratio, calc_relative_strength
```
Replace with:
```python
from engine.indicators import calc_vol_ratio, calc_relative_strength
```

- [x] **Step 3: Update `monitor.py`**

Find the inline import (around line 252, inside a function body):
```python
from engine.strategies import calc_atr
```
Replace with:
```python
from engine.indicators import calc_atr
```

- [x] **Step 4: Run full test suite**

```
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass.

- [x] **Step 5: Confirm no stale imports remain**

```
grep -rn "from engine.strategies import calc_" . --include="*.py" | grep -v __pycache__ | grep -v ".claude/worktrees"
```

Expected: No output.

- [x] **Step 6: Commit**

```bash
git add routes/backtest.py scheduler/scanner.py monitor.py
git commit -m "refactor(r9): update inline imports in backtest/scanner/monitor to engine.indicators"
```

---

## Task 8: Replace `WARMUP_BARS = 75` in `engine/walkforward_multi.py`

**Files:**
- Modify: `engine/walkforward_multi.py`

- [x] **Step 1: Add import at top of `engine/walkforward_multi.py`**

After the existing `.strategies` import block (around line 21), add:

```python
from engine.indicators import get_warmup, calc_atr, calc_adx, calc_ma_slope, calc_vwap
```

- [x] **Step 2: Replace the constant (around line 217)**

Find:
```python
    WARMUP_BARS = 75
```
Replace with:
```python
    # Derived from the heaviest-warmup indicators across all strategies:
    # calc_vwap(window=60) dominates; calc_adx(28), calc_ma_slope(25), calc_atr(14) follow.
    WARMUP_BARS = get_warmup([calc_vwap, calc_adx, calc_ma_slope, calc_atr])  # → 60
```

- [x] **Step 3: Run tests**

```
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass. `WARMUP_BARS` evaluates to 60 (still covers all indicator warmup windows).

- [x] **Step 4: Commit**

```bash
git add engine/walkforward_multi.py
git commit -m "refactor(r9): replace hardcoded WARMUP_BARS=75 with get_warmup() in walkforward_multi.py"
```

---

## Task 9: Wire `IndicatorCache.clear()` into `scheduler/utils.py`

**Files:**
- Modify: `scheduler/utils.py`

- [x] **Step 1: Add import at top of `scheduler/utils.py`**

After existing imports, add:
```python
from engine.indicators import IndicatorCache
```

- [x] **Step 2: Add cache invalidation inside `fetch_latest` after successful save**

Find in `fetch_latest()` (around line 85):
```python
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
        try:
            from engine.suspension_detector import scan_all as _scan_suspensions
```

Insert between the print and the suspension scan:
```python
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
        try:
            _cache = IndicatorCache()
            for t in tickers:
                _cache.clear(t)
        except Exception as _ce:
            logging.warning("indicator cache clear failed (non-fatal): %s", _ce)
        try:
            from engine.suspension_detector import scan_all as _scan_suspensions
```

- [x] **Step 3: Run tests**

```
pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All tests pass.

- [x] **Step 4: Commit**

```bash
git add scheduler/utils.py
git commit -m "feat(r9): invalidate IndicatorCache per-ticker in fetch_latest"
```

---

## Task 10: Final verification and TODO update

- [x] **Step 1: Run full test suite**

```
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
pytest tests/ -v 2>&1 | tail -40
```

Expected: All tests pass with no `ImportError` or `AttributeError`.

- [x] **Step 2: Verify all imports resolved**

```bash
python3 -c "
from engine.indicators import (
    calc_atr, calc_vwap, calc_vol_ratio, calc_delta, calc_vwma,
    calc_relative_strength, calc_weekly_trend, calc_sma,
    calc_adx, calc_ma_slope, calc_vr_mean, calc_price_range_pct, calc_close_vs_ma,
    get_warmup, IndicatorCache
)
print('All imports OK')
"
```

Expected: `All imports OK`

- [x] **Step 3: Verify no stale `calc_*` imports from strategies**

```bash
grep -rn "from engine.strategies import calc_" . --include="*.py" | grep -v __pycache__ | grep -v ".claude/worktrees"
```

Expected: No output.

- [x] **Step 4: Mark R9 complete in `TODO.md`**

Find:
```
- [x] **R9. Build indicator library** — Extract manual calculations from `strategies.py` into `engine/indicators.py` with auto-warmup, NaN handling, caching. ~6 hr.
```
Replace with:
```
- [x] **R9. Build indicator library** — `engine/indicators.py`: 13 `calc_*` functions, `warmup_bars` metadata, `get_warmup()`, `IndicatorCache` (SQLite). Full migration: 9 files updated, no shims. `WARMUP_BARS` in WF harness replaced with `get_warmup()`. SHIPPED 2026-05-30.
```

- [x] **Step 5: Commit**

```bash
git add TODO.md
git commit -m "chore: mark R9 complete in TODO.md"
```
