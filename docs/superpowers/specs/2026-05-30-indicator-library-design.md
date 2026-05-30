# Indicator Library — Design Spec
_R9 · Sprint 14 · 2026-05-30_

## Goal

Extract all manual indicator calculations scattered across `engine/strategies.py` and `engine/regime_filter.py` into a single `engine/indicators.py` module with:
- Consistent `warmup_bars` metadata on every function
- Uniform `min_periods` NaN handling
- SQLite-backed `IndicatorCache` for persistent caching across scan runs
- Single migration pass: all import sites updated, no shims left behind

---

## Module Structure

**`engine/indicators.py`** — flat module, all functions at module level.

No registry, no class hierarchy. Callers import functions directly:
```python
from engine.indicators import calc_atr, calc_vwap, IndicatorCache, get_warmup
```

---

## Indicator Inventory

### Migrated from `engine/strategies.py`

| Function | Signature | `warmup_bars` |
|---|---|---|
| `calc_atr` | `(df, period=14) -> Series` | `period` |
| `calc_vwap` | `(df, window=60) -> Series` | `window` |
| `calc_vol_ratio` | `(df, period=20) -> Series` | `period` |
| `calc_delta` | `(df) -> Series` | `0` |
| `calc_vwma` | `(df, period=20) -> Series` | `period` |
| `calc_relative_strength` | `(ticker_df, ihsg_df, period=20) -> float` | `period + 1` |
| `calc_weekly_trend` | `(df) -> tuple` | `100` (≈20 weekly bars) |

### Migrated from `engine/regime_filter.py`

| Function | Signature | `warmup_bars` |
|---|---|---|
| `calc_adx` | `(df, period=14) -> Series` | `period * 2` |
| `calc_ma_slope` | `(df, ma_period=20, slope_window=5) -> Series` | `ma_period + slope_window` |
| `calc_vr_mean` | `(df, vr_period=20, mean_window=10) -> Series` | `vr_period + mean_window` |
| `calc_price_range_pct` | `(df, window=20) -> Series` | `window` |
| `calc_close_vs_ma` | `(df, period=20) -> Series` | `period` |

### New (replaces inline rolling calcs)

| Function | Signature | `warmup_bars` | Replaces |
|---|---|---|---|
| `calc_sma` | `(df, period) -> Series` | `period` | `df['close'].rolling(N).mean()` inline calls |

### Stays in `strategies.py` (not pure OHLCV math)

- `calc_volume_profile` — stub only, logic lives in `_get_poc_hvn`
- `calc_opening_range_from_ticks` — DB-dependent, not a pure indicator

---

## Warmup Metadata

Each function gets a `warmup_bars` callable attribute set immediately after definition:

```python
def calc_atr(df, period=14):
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()

calc_atr.warmup_bars = lambda period=14: period
```

**`get_warmup(funcs, **params) -> int`** helper returns the maximum warmup across a list of indicator functions:

```python
bars_needed = get_warmup([calc_atr, calc_adx, calc_vwap])  # → 60
```

This replaces the hardcoded `75` bar prepend in `engine/walkforward_multi.py` (added in Sprint 9) with a value computed from the actual indicators each strategy uses.

---

## NaN Handling

All `rolling()` calls that currently omit `min_periods` will be updated:

- Indicators where partial windows are **misleading** (ATR, ADX, VWAP, VWMA): `min_periods=period`. Returns `NaN` until enough bars exist.
- Indicators where partial windows are **acceptable** (SMA, VR): `min_periods=1`. Returns a value from bar 1, converging to the full-window result.

No behavior change once the warmup window is satisfied. Only the leading NaN rows change.

---

## IndicatorCache

### Schema

New table in `walkforward.db`:

```sql
CREATE TABLE IF NOT EXISTS indicator_cache (
    ticker      TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    indicator   TEXT    NOT NULL,
    period      INTEGER NOT NULL,
    value       REAL,
    PRIMARY KEY (ticker, date, indicator, period)
)
```

### Interface

```python
cache = IndicatorCache(db_path=DB_PATH)

# Persist a computed Series (index = date strings)
cache.put(ticker, indicator_name, period, series)

# Retrieve: returns Series if all requested dates are cached, else None
series = cache.get(ticker, indicator_name, period, dates)

# Invalidate after new OHLCV arrives for a ticker
cache.clear(ticker)
```

### Invalidation

`cache.clear(ticker)` is called in `scheduler/jobs.py` inside `fetch_latest()` after new OHLCV is saved to the DB. This keeps the cache fresh without a TTL.

### Usage layer

Strategies do **not** call the cache directly. The cache is used by:
- `engine/walkforward_multi.py` — before running a strategy on a window, checks `cache.get(ticker, 'atr', 14, dates)`; on miss, computes and calls `cache.put`
- `engine/optimizer.py` — same pattern during grid search per-ticker per-param-set

Strategy function bodies remain unchanged. Callers that use indicators ad-hoc (routes, scanner, monitor) do not use the cache — they call `calc_*` directly as before.

---

## Migration Plan

All import sites updated in one pass. No shims left in `strategies.py` or `regime_filter.py`.

| File | Change |
|---|---|
| `engine/strategies.py` | Remove all `calc_*` definitions; add `from engine.indicators import calc_atr, calc_vwap, calc_vol_ratio, calc_delta, calc_vwma, calc_relative_strength, calc_weekly_trend, calc_sma` |
| `engine/regime_filter.py` | Remove `calc_adx`, `calc_ma_slope`, `calc_vr_mean`, `calc_price_range_pct`, `calc_close_vs_ma`; add `from engine.indicators import ...` |
| `engine/optimizer.py` | `from engine.strategies import calc_atr, calc_vol_ratio, calc_vwap` → `from engine.indicators import ...` |
| `engine/swing_screener.py` | `from engine.strategies import calc_atr, calc_vol_ratio` → `from engine.indicators import ...` |
| `routes/backtest.py` | Inline `from engine.strategies import calc_vol_ratio` → `from engine.indicators import calc_vol_ratio` |
| `scheduler/scanner.py` | Inline `from engine.strategies import calc_vol_ratio, calc_relative_strength` → `from engine.indicators import ...` |
| `monitor.py` | Inline `from engine.strategies import calc_atr` → `from engine.indicators import calc_atr` |
| `scheduler/jobs.py` | Add `IndicatorCache(DB_PATH).clear(ticker)` after `fetch_latest` saves OHLCV |
| `engine/walkforward_multi.py` | Replace hardcoded `75` prepend with `get_warmup([...])` |

---

## Testing

- Existing 166+ tests run after migration to confirm no regressions.
- Dedicated unit tests for `engine/indicators.py` added as part of R12 (CI/CD sprint):
  - Each `calc_*` function: correct output on known input, correct leading NaN count
  - `IndicatorCache`: put/get round-trip, clear invalidates correctly
  - `get_warmup`: returns max across mixed indicator list

---

## Out of Scope

- `calc_volume_profile` / `_get_poc_hvn` — pattern-specific, stays in `strategies.py`
- `calc_opening_range_from_ticks` — DB-dependent tick aggregation, stays in `strategies.py`
- ATR smoothing method unification — documented decision from Sprint 16: SMA in strategies, Wilder's EWM in regime_filter. Both stay as-is.
