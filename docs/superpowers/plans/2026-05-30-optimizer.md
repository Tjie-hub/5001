# Strategy Parameter Optimizer (R7) Implementation Plan

> ✅ SHIPPED 2026-05-30 — all 32 tests pass. See `engine/optimizer.py` + `tests/test_optimizer.py`.

**Goal:** Build `engine/optimizer.py` with grid search + walk-forward validation to tune VR thresholds, ATR multipliers, and donchian/MA periods per-ticker for 5 core strategies; persist results in SQLite; expose via 2 REST endpoints.

**Architecture:** Thin parameterized wrappers for each strategy (no touching existing strategy functions); `grid_search()` evaluates all param combos on a df slice by Sharpe; `optimize_strategy()` runs WF-validated optimization using the existing `walk_forward_split()`; DB persistence via a new `optimizer_results` table created inline on first save; REST endpoints added to the existing `backtest_bp` blueprint.

**Tech Stack:** Python, pandas, NumPy, itertools.product; reuses `walk_forward_split`, `compute_metrics`, `run_strategy`, `calc_vol_ratio`, `calc_atr`, `calc_delta`, `calc_vwap`, `apply_costs`, `lot_size` from existing engine modules.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `engine/optimizer.py` | PARAM_GRIDS, parameterized runners, grid_search, optimize_strategy, save/get DB functions |
| Create | `tests/test_optimizer.py` | Unit tests (TDD-first) for all optimizer functions |
| Modify | `routes/backtest.py` | Add `POST /api/optimizer/run` and `GET /api/optimizer/result/<ticker>/<strategy>` |

---

## Strategies + Parameters Being Tuned

| Strategy key | Parameters | Grid size |
|---|---|---|
| `vol_weighted` | `vr_threshold`, `atr_sl_mult`, `atr_tp_mult` | 4×3×3 = 36 |
| `momentum` | `vr_threshold`, `atr_sl_mult`, `atr_tp_mult` | 4×3×3 = 36 |
| `vwap_reversion` | `dist_threshold`, `vr_threshold`, `atr_sl_mult`, `atr_tp_mult` | 4×3×3×3 = 108 |
| `conservative` | `vr_threshold`, `atr_sl_mult`, `atr_tp_mult` | 3×3×3 = 27 |
| `trend_following_breakout` | `donchian_period`, `vol_mult`, `atr_trail_mult`, `atr_expand_mult` | 3×3×3×3 = 81 |

---

## Task 1: Parameterized runners + PARAM_GRIDS (TDD)

**Files:**
- Create: `tests/test_optimizer.py` (write tests first)
- Create: `engine/optimizer.py` (implement to pass tests)

- [x] **Step 1: Write the failing tests**

Create `tests/test_optimizer.py`:

```python
"""Tests for engine/optimizer.py"""
import numpy as np
import pandas as pd
import pytest


def _make_df(n=250, seed=42):
    np.random.seed(seed)
    close = np.cumprod(1 + np.random.normal(0.0003, 0.015, n)) * 1000
    return pd.DataFrame({
        'date':   pd.date_range('2022-01-03', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open':   (close * 0.998).round(0),
        'high':   (close * 1.015).round(0),
        'low':    (close * 0.985).round(0),
        'close':  close.round(0),
        'volume': np.random.randint(500_000, 3_000_000, n).astype(float),
    })


# ─── Parameterized runners ────────────────────────────────────────────────────

def test_run_vol_weighted_returns_expected_keys():
    from engine.optimizer import _run_vol_weighted
    df = _make_df(250)
    result = _run_vol_weighted(df, 10_000_000, {'vr_threshold': 1.8, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0})
    assert 'trades' in result
    assert 'equity' in result
    assert 'initial_capital' in result
    assert result['initial_capital'] == 10_000_000


def test_run_vol_weighted_high_threshold_fewer_or_equal_trades():
    from engine.optimizer import _run_vol_weighted
    df = _make_df(250)
    r_low  = _run_vol_weighted(df, 10_000_000, {'vr_threshold': 1.0, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0})
    r_high = _run_vol_weighted(df, 10_000_000, {'vr_threshold': 5.0, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0})
    assert len(r_low['trades']) >= len(r_high['trades'])


def test_run_momentum_returns_expected_keys():
    from engine.optimizer import _run_momentum
    df = _make_df(250)
    result = _run_momentum(df, 10_000_000, {'vr_threshold': 1.3, 'atr_sl_mult': 1.2, 'atr_tp_mult': 2.4})
    assert 'trades' in result and 'equity' in result


def test_run_vwap_reversion_returns_expected_keys():
    from engine.optimizer import _run_vwap_reversion
    df = _make_df(250)
    result = _run_vwap_reversion(df, 10_000_000,
                                  {'dist_threshold': -0.01, 'vr_threshold': 1.3,
                                   'atr_sl_mult': 0.8, 'atr_tp_mult': 1.6})
    assert 'trades' in result and 'equity' in result


def test_run_vwap_reversion_tighter_dist_threshold_fewer_trades():
    from engine.optimizer import _run_vwap_reversion
    df = _make_df(250)
    r_wide  = _run_vwap_reversion(df, 10_000_000,
                                   {'dist_threshold': -0.001, 'vr_threshold': 1.0,
                                    'atr_sl_mult': 0.8, 'atr_tp_mult': 1.6})
    r_tight = _run_vwap_reversion(df, 10_000_000,
                                   {'dist_threshold': -0.050, 'vr_threshold': 5.0,
                                    'atr_sl_mult': 0.8, 'atr_tp_mult': 1.6})
    assert len(r_wide['trades']) >= len(r_tight['trades'])


def test_run_conservative_returns_expected_keys():
    from engine.optimizer import _run_conservative
    df = _make_df(250)
    result = _run_conservative(df, 10_000_000, {'vr_threshold': 1.3, 'atr_sl_mult': 0.7, 'atr_tp_mult': 1.4})
    assert 'trades' in result and 'equity' in result


def test_run_tfb_returns_expected_keys():
    from engine.optimizer import _run_tfb
    df = _make_df(250)
    result = _run_tfb(df, 10_000_000,
                      {'donchian_period': 20, 'vol_mult': 1.8,
                       'atr_trail_mult': 2.5, 'atr_expand_mult': 0.5})
    assert 'trades' in result and 'equity' in result
    assert result['initial_capital'] == 10_000_000


def test_run_tfb_returns_empty_if_insufficient_data():
    from engine.optimizer import _run_tfb
    df = _make_df(50)
    result = _run_tfb(df, 10_000_000,
                      {'donchian_period': 20, 'vol_mult': 1.8,
                       'atr_trail_mult': 2.5, 'atr_expand_mult': 0.5})
    assert result['trades'] == []


# ─── PARAM_GRIDS ─────────────────────────────────────────────────────────────

def test_param_grids_contains_all_five_strategies():
    from engine.optimizer import PARAM_GRIDS
    for key in ('vol_weighted', 'momentum', 'vwap_reversion', 'conservative', 'trend_following_breakout'):
        assert key in PARAM_GRIDS


def test_strategy_runners_contains_all_five():
    from engine.optimizer import STRATEGY_RUNNERS
    for key in ('vol_weighted', 'momentum', 'vwap_reversion', 'conservative', 'trend_following_breakout'):
        assert key in STRATEGY_RUNNERS
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'engine.optimizer'`

- [x] **Step 3: Create `engine/optimizer.py` with runners**

```python
"""
optimizer.py — Strategy Parameter Optimizer

Grid search + walk-forward validation for tuning VR thresholds,
ATR multipliers, and MA/period params per-ticker.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from engine.strategies import (
    Trade,
    apply_costs,
    calc_atr,
    calc_delta,
    calc_vol_ratio,
    calc_vwap,
    lot_size,
    run_strategy,
)
from engine.walkforward_multi import compute_metrics, walk_forward_split

# ─── Param grids ────────────────────────────────────────────────────────────

PARAM_GRIDS: dict[str, dict[str, list]] = {
    'vol_weighted': {
        'vr_threshold': [1.5, 1.8, 2.0, 2.5],
        'atr_sl_mult':  [0.8, 1.0, 1.2],
        'atr_tp_mult':  [1.6, 2.0, 2.4],
    },
    'momentum': {
        'vr_threshold': [1.2, 1.3, 1.5, 2.0],
        'atr_sl_mult':  [0.8, 1.0, 1.2],
        'atr_tp_mult':  [2.0, 2.4, 3.0],
    },
    'vwap_reversion': {
        'dist_threshold': [-0.005, -0.010, -0.015, -0.020],
        'vr_threshold':   [1.2, 1.3, 1.5],
        'atr_sl_mult':    [0.6, 0.8, 1.0],
        'atr_tp_mult':    [1.2, 1.6, 2.0],
    },
    'conservative': {
        'vr_threshold': [1.2, 1.3, 1.5],
        'atr_sl_mult':  [0.5, 0.7, 0.9],
        'atr_tp_mult':  [1.2, 1.4, 1.8],
    },
    'trend_following_breakout': {
        'donchian_period': [15, 20, 25],
        'vol_mult':        [1.5, 1.8, 2.2],
        'atr_trail_mult':  [2.0, 2.5, 3.0],
        'atr_expand_mult': [0.3, 0.5, 0.7],
    },
}


# ─── Parameterized runners ────────────────────────────────────────────────────

def _run_vol_weighted(df: pd.DataFrame, capital: float, params: dict) -> dict:
    vr_threshold = params.get('vr_threshold', 1.8)
    atr_sl_mult  = params.get('atr_sl_mult', 1.0)
    atr_tp_mult  = params.get('atr_tp_mult', 2.0)
    vr    = calc_vol_ratio(df, 20)
    delta = calc_delta(df)
    sig   = (vr > vr_threshold) & (delta > 0) & (df['close'] > df['open'])
    return run_strategy(df, sig, atr_sl_mult=atr_sl_mult, atr_tp_mult=atr_tp_mult,
                        min_rr=2.0, strategy_name='vol_weighted',
                        initial_capital=capital)


def _run_momentum(df: pd.DataFrame, capital: float, params: dict) -> dict:
    vr_threshold = params.get('vr_threshold', 1.3)
    atr_sl_mult  = params.get('atr_sl_mult', 1.2)
    atr_tp_mult  = params.get('atr_tp_mult', 2.4)
    vr      = calc_vol_ratio(df, 20)
    streak2 = (
        (df['close'] > df['close'].shift(1)) &
        (df['close'].shift(1) > df['close'].shift(2))
    )
    sig = streak2 & (vr > vr_threshold) & (vr <= 5.0)
    return run_strategy(df, sig, atr_sl_mult=atr_sl_mult, atr_tp_mult=atr_tp_mult,
                        min_rr=2.0, strategy_name='momentum',
                        initial_capital=capital, trail_sl=True)


def _run_vwap_reversion(df: pd.DataFrame, capital: float, params: dict) -> dict:
    dist_threshold = params.get('dist_threshold', -0.010)
    vr_threshold   = params.get('vr_threshold', 1.3)
    atr_sl_mult    = params.get('atr_sl_mult', 0.8)
    atr_tp_mult    = params.get('atr_tp_mult', 1.6)
    vwap = calc_vwap(df)
    vr   = calc_vol_ratio(df, 20)
    dist = (df['close'] - vwap) / vwap
    sig  = (dist < dist_threshold) & (vr > vr_threshold)
    return run_strategy(df, sig, atr_sl_mult=atr_sl_mult, atr_tp_mult=atr_tp_mult,
                        min_rr=2.0, strategy_name='vwap_reversion',
                        initial_capital=capital)


def _run_conservative(df: pd.DataFrame, capital: float, params: dict) -> dict:
    vr_threshold = params.get('vr_threshold', 1.3)
    atr_sl_mult  = params.get('atr_sl_mult', 0.7)
    atr_tp_mult  = params.get('atr_tp_mult', 1.4)
    vr       = calc_vol_ratio(df, 20)
    ma20     = df['close'].rolling(20).mean()
    atr      = calc_atr(df, 14)
    atr_ma   = atr.rolling(10).mean()
    bullish  = df['close'] > df['open']
    above_ma = df['close'] > ma20
    atr_ok   = atr < atr_ma * 1.5
    sig = (vr > vr_threshold) & bullish & above_ma & atr_ok
    return run_strategy(df, sig, atr_sl_mult=atr_sl_mult, atr_tp_mult=atr_tp_mult,
                        min_rr=2.0, strategy_name='conservative',
                        initial_capital=capital)


def _run_tfb(df: pd.DataFrame, capital: float, params: dict) -> dict:
    donchian_period = int(params.get('donchian_period', 20))
    vol_mult        = params.get('vol_mult', 1.8)
    atr_trail_mult  = params.get('atr_trail_mult', 2.5)
    atr_expand_mult = params.get('atr_expand_mult', 0.5)
    strategy_name   = 'trend_following_breakout'
    initial_capital = capital

    min_bars = donchian_period + 65
    if len(df) < min_bars:
        return {
            'strategy': strategy_name, 'trades': [],
            'equity': [capital] * len(df),
            'final_capital': capital, 'initial_capital': initial_capital,
        }

    ma20      = df['close'].rolling(20).mean()
    ma50      = df['close'].rolling(50).mean()
    atr       = calc_atr(df, 14)
    avg_vol   = df['volume'].rolling(20).mean()
    donchian  = df['high'].rolling(donchian_period).max().shift(1)
    atr60_med = atr.rolling(60).median()

    signal = (
        (df['close']  > donchian) &
        (df['volume'] > vol_mult * avg_vol) &
        (atr          > atr_expand_mult * atr60_med) &
        (df['close']  > ma50)
    )

    equity      = [capital]
    trades      = []
    in_trade    = False
    entry_price = 0.0
    trail_stop  = 0.0
    lots        = 0
    entry_date  = ''

    start_bar = donchian_period + 65
    for i in range(start_bar, len(df)):
        row      = df.iloc[i]
        date     = str(row['date'])[:10]
        cur_atr  = atr.iloc[i]
        cur_ma20 = ma20.iloc[i]

        if in_trade:
            new_stop   = row['close'] - atr_trail_mult * cur_atr
            trail_stop = max(trail_stop, new_stop)
            exit_reason = None
            exit_price  = None
            if row['low'] <= trail_stop:
                exit_price  = apply_costs(trail_stop, 'SELL')
                exit_reason = 'TRAIL_SL'
            elif row['close'] < cur_ma20:
                exit_price  = apply_costs(row['close'], 'SELL')
                exit_reason = 'MA20_BREAK'
            elif i == len(df) - 1:
                exit_price  = apply_costs(row['close'], 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross   = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name,
                ))
                in_trade = False
        elif signal.iloc[i - 1]:
            sig_atr = atr.iloc[i - 1]
            if pd.isna(sig_atr) or sig_atr <= 0:
                equity.append(capital)
                continue
            entry_price = apply_costs(row['open'], 'BUY')
            sl_dist     = atr_trail_mult * sig_atr
            sl_pct      = sl_dist / entry_price
            if sl_pct <= 0.001:
                equity.append(capital)
                continue
            lots = lot_size(capital, entry_price, 0.005, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital and lots > 0:
                trail_stop = entry_price - sl_dist
                in_trade   = True
                entry_date = date

        equity.append(capital)

    return {
        'strategy': strategy_name, 'trades': trades, 'equity': equity,
        'final_capital': capital, 'initial_capital': initial_capital,
    }


STRATEGY_RUNNERS: dict[str, Any] = {
    'vol_weighted':             _run_vol_weighted,
    'momentum':                 _run_momentum,
    'vwap_reversion':           _run_vwap_reversion,
    'conservative':             _run_conservative,
    'trend_following_breakout': _run_tfb,
}
```

- [x] **Step 4: Run tests — verify Task 1 tests pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "runner or param_grid or strategy_runners" 2>&1
```

Expected: all 10 tests PASS

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/optimizer.py tests/test_optimizer.py && git commit -m "feat(r7): add parameterized runners + PARAM_GRIDS to engine/optimizer.py"
```

---

## Task 2: `_iter_param_grid()` + `grid_search()` (TDD)

**Files:**
- Modify: `tests/test_optimizer.py` (add tests)
- Modify: `engine/optimizer.py` (add functions)

- [x] **Step 1: Add tests for grid_search**

Append to `tests/test_optimizer.py`:

```python
# ─── _iter_param_grid ─────────────────────────────────────────────────────────

def test_iter_param_grid_full_product():
    from engine.optimizer import _iter_param_grid
    grid = {'a': [1, 2], 'b': [10, 20]}
    combos = _iter_param_grid(grid)
    assert len(combos) == 4
    assert {'a': 1, 'b': 10} in combos
    assert {'a': 2, 'b': 20} in combos


def test_iter_param_grid_single_param():
    from engine.optimizer import _iter_param_grid
    combos = _iter_param_grid({'x': [5, 6, 7]})
    assert len(combos) == 3
    assert all(len(c) == 1 for c in combos)


# ─── grid_search ──────────────────────────────────────────────────────────────

def test_grid_search_returns_sorted_by_sharpe():
    from engine.optimizer import grid_search
    df = _make_df(250)
    results = grid_search(df, 'vol_weighted', capital=10_000_000)
    assert len(results) > 0
    sharpes = [r['metrics']['sharpe'] for r in results]
    assert sharpes == sorted(sharpes, reverse=True)


def test_grid_search_each_result_has_params_and_metrics():
    from engine.optimizer import grid_search
    df = _make_df(250)
    results = grid_search(df, 'conservative', capital=10_000_000)
    for r in results:
        assert 'params' in r
        assert 'metrics' in r
        assert 'sharpe' in r['metrics']
        assert 'vr_threshold' in r['params']


def test_grid_search_result_count_matches_grid_size():
    from engine.optimizer import grid_search, PARAM_GRIDS
    from itertools import product as iproduct
    df = _make_df(250)
    results = grid_search(df, 'conservative', capital=10_000_000)
    grid = PARAM_GRIDS['conservative']
    expected_count = 1
    for v in grid.values():
        expected_count *= len(v)
    assert len(results) == expected_count


def test_grid_search_custom_param_grid():
    from engine.optimizer import grid_search
    df = _make_df(250)
    small_grid = {'vr_threshold': [1.5, 2.0], 'atr_sl_mult': [1.0], 'atr_tp_mult': [2.0]}
    results = grid_search(df, 'vol_weighted', capital=10_000_000, param_grid=small_grid)
    assert len(results) == 2


def test_grid_search_raises_on_unknown_strategy():
    from engine.optimizer import grid_search
    df = _make_df(250)
    with pytest.raises(ValueError, match='Unknown strategy'):
        grid_search(df, 'nonexistent', capital=10_000_000)
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "grid_search or iter_param" 2>&1 | head -20
```

Expected: `AttributeError: module 'engine.optimizer' has no attribute '_iter_param_grid'`

- [x] **Step 3: Add `_iter_param_grid` and `grid_search` to `engine/optimizer.py`**

Append after `STRATEGY_RUNNERS` definition:

```python
# ─── Helpers ──────────────────────────────────────────────────────────────────

def _iter_param_grid(grid: dict[str, list]) -> list[dict]:
    """Expand a param dict into a list of all combinations."""
    keys   = list(grid.keys())
    values = list(grid.values())
    return [dict(zip(keys, combo)) for combo in product(*values)]


# ─── Grid search ──────────────────────────────────────────────────────────────

def grid_search(
    df: pd.DataFrame,
    strategy_key: str,
    capital: float = 50_000_000,
    param_grid: dict | None = None,
) -> list[dict]:
    """
    Evaluate all param combos for strategy_key on df.
    Returns list sorted by Sharpe (descending).
    Each item: {'params': {...}, 'metrics': {...}}.
    """
    if strategy_key not in STRATEGY_RUNNERS:
        raise ValueError(f"Unknown strategy: {strategy_key!r}. Valid: {list(STRATEGY_RUNNERS)}")
    runner = STRATEGY_RUNNERS[strategy_key]
    grid   = param_grid if param_grid is not None else PARAM_GRIDS[strategy_key]
    combos = _iter_param_grid(grid)
    results = []
    for params in combos:
        raw     = runner(df, capital, params)
        metrics = compute_metrics(raw)
        results.append({'params': params, 'metrics': metrics})
    results.sort(key=lambda x: x['metrics']['sharpe'], reverse=True)
    return results
```

- [x] **Step 4: Run tests — verify Task 2 tests pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "grid_search or iter_param" 2>&1
```

Expected: 6 tests PASS

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/optimizer.py tests/test_optimizer.py && git commit -m "feat(r7): add _iter_param_grid + grid_search to optimizer"
```

---

## Task 3: `optimize_strategy()` (TDD)

**Files:**
- Modify: `tests/test_optimizer.py` (add tests)
- Modify: `engine/optimizer.py` (add function)

- [x] **Step 1: Add tests for optimize_strategy**

Append to `tests/test_optimizer.py`:

```python
# ─── optimize_strategy ────────────────────────────────────────────────────────

def _make_df_long(n=400, seed=7):
    """Long enough for at least one WF window (15 months = ~325 bars)."""
    np.random.seed(seed)
    close = np.cumprod(1 + np.random.normal(0.0004, 0.012, n)) * 1000
    return pd.DataFrame({
        'date':   pd.date_range('2021-01-04', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open':   (close * 0.998).round(0),
        'high':   (close * 1.015).round(0),
        'low':    (close * 0.985).round(0),
        'close':  close.round(0),
        'volume': np.random.randint(500_000, 3_000_000, n).astype(float),
    })


def test_optimize_strategy_returns_expected_keys():
    from engine.optimizer import optimize_strategy
    df = _make_df_long(400)
    small_grid = {'vr_threshold': [1.5, 2.0], 'atr_sl_mult': [1.0], 'atr_tp_mult': [2.0]}
    result = optimize_strategy(df, 'vol_weighted', capital=10_000_000, param_grid=small_grid)
    assert 'strategy' in result
    assert 'best_params' in result
    assert 'oos_metrics' in result
    assert 'windows' in result
    assert result['strategy'] == 'vol_weighted'


def test_optimize_strategy_best_params_is_dict_with_correct_keys():
    from engine.optimizer import optimize_strategy
    df = _make_df_long(400)
    small_grid = {'vr_threshold': [1.5, 2.0], 'atr_sl_mult': [1.0], 'atr_tp_mult': [2.0]}
    result = optimize_strategy(df, 'vol_weighted', capital=10_000_000, param_grid=small_grid)
    bp = result['best_params']
    assert 'vr_threshold' in bp
    assert 'atr_sl_mult' in bp
    assert 'atr_tp_mult' in bp
    assert bp['vr_threshold'] in [1.5, 2.0]


def test_optimize_strategy_oos_metrics_contains_expected_keys():
    from engine.optimizer import optimize_strategy
    df = _make_df_long(400)
    small_grid = {'vr_threshold': [1.8], 'atr_sl_mult': [1.0], 'atr_tp_mult': [2.0]}
    result = optimize_strategy(df, 'vol_weighted', capital=10_000_000, param_grid=small_grid)
    oos = result['oos_metrics']
    assert 'avg_sharpe' in oos
    assert 'avg_return_pct' in oos
    assert 'avg_win_rate' in oos
    assert 'windows_tested' in oos
    assert oos['windows_tested'] >= 1


def test_optimize_strategy_windows_list_has_per_window_detail():
    from engine.optimizer import optimize_strategy
    df = _make_df_long(400)
    small_grid = {'vr_threshold': [1.8], 'atr_sl_mult': [1.0], 'atr_tp_mult': [2.0]}
    result = optimize_strategy(df, 'vol_weighted', capital=10_000_000, param_grid=small_grid)
    assert len(result['windows']) >= 1
    w = result['windows'][0]
    assert 'best_params' in w
    assert 'train_sharpe' in w
    assert 'oos_metrics' in w
    assert 'test_start' in w
    assert 'test_end' in w


def test_optimize_strategy_raises_on_unknown_strategy():
    from engine.optimizer import optimize_strategy
    df = _make_df_long(400)
    with pytest.raises(ValueError, match='Unknown strategy'):
        optimize_strategy(df, 'nonexistent')


def test_optimize_strategy_raises_on_insufficient_data():
    from engine.optimizer import optimize_strategy
    df = _make_df(50)  # too short for WF
    with pytest.raises(ValueError, match='Data tidak cukup'):
        optimize_strategy(df, 'vol_weighted')
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "optimize_strategy" 2>&1 | head -20
```

Expected: `AttributeError: module 'engine.optimizer' has no attribute 'optimize_strategy'`

- [x] **Step 3: Add `optimize_strategy` to `engine/optimizer.py`**

Append after `grid_search`:

```python
# ─── Walk-forward optimization ────────────────────────────────────────────────

def optimize_strategy(
    df: pd.DataFrame,
    strategy_key: str,
    capital: float = 50_000_000,
    param_grid: dict | None = None,
) -> dict:
    """
    Walk-forward validated parameter optimization.

    For each WF window (12-month train, 3-month test):
      1. Grid-search all param combos on train → pick best Sharpe
      2. Evaluate best params on test (with warmup tail)
    Returns best_params (most frequent train-winner), averaged OOS metrics,
    and per-window detail.
    """
    if strategy_key not in STRATEGY_RUNNERS:
        raise ValueError(f"Unknown strategy: {strategy_key!r}. Valid: {list(STRATEGY_RUNNERS)}")

    windows = walk_forward_split(df)
    if not windows:
        raise ValueError("Data tidak cukup untuk walk-forward (butuh minimal 15 bulan)")

    grid   = param_grid if param_grid is not None else PARAM_GRIDS[strategy_key]
    runner = STRATEGY_RUNNERS[strategy_key]
    combos = _iter_param_grid(grid)
    WARMUP_BARS = 75

    window_results = []

    for w in windows:
        train_df       = w['train']
        test_df        = w['test']
        test_start_str = w['test_start']

        # Best params on train by Sharpe
        train_scores = []
        for params in combos:
            raw     = runner(train_df, capital, params)
            metrics = compute_metrics(raw)
            train_scores.append((params, metrics['sharpe']))
        train_scores.sort(key=lambda x: x[1], reverse=True)
        best_params_window, train_sharpe = train_scores[0]

        # Evaluate on test with warmup
        warmup_tail = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended    = pd.concat([warmup_tail, test_df], ignore_index=True)
        raw_test    = runner(extended, capital, best_params_window)

        kept   = [t for t in raw_test['trades'] if t.entry_date >= test_start_str]
        cur_cap = capital
        eq      = [capital]
        for t in kept:
            cur_cap += t.pnl_rp
            eq.append(cur_cap)
        raw_test['trades']          = kept
        raw_test['equity']          = eq
        raw_test['final_capital']   = cur_cap
        raw_test['initial_capital'] = capital
        oos = compute_metrics(raw_test)

        window_results.append({
            'window':       w['window'],
            'train_start':  w['train_start'],
            'train_end':    w['train_end'],
            'test_start':   w['test_start'],
            'test_end':     w['test_end'],
            'best_params':  best_params_window,
            'train_sharpe': round(train_sharpe, 3),
            'oos_metrics':  oos,
        })

    # Global best_params = most-frequent train winner across windows
    param_wins     = Counter(str(w['best_params']) for w in window_results)
    winner_str     = param_wins.most_common(1)[0][0]
    best_params_global = next(c for c in combos if str(c) == winner_str)

    oos_sharpes = [w['oos_metrics']['sharpe']           for w in window_results]
    oos_returns = [w['oos_metrics']['total_return_pct'] for w in window_results]
    oos_wr      = [w['oos_metrics']['win_rate']         for w in window_results]

    return {
        'strategy':    strategy_key,
        'best_params': best_params_global,
        'oos_metrics': {
            'avg_sharpe':     round(float(np.mean(oos_sharpes)), 3),
            'avg_return_pct': round(float(np.mean(oos_returns)), 2),
            'avg_win_rate':   round(float(np.mean(oos_wr)), 1),
            'windows_tested': len(window_results),
        },
        'windows': window_results,
    }
```

- [x] **Step 4: Run tests — verify Task 3 tests pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "optimize_strategy" 2>&1
```

Expected: 7 tests PASS

- [x] **Step 5: Run full test suite to catch regressions**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all existing tests pass + new optimizer tests pass

- [x] **Step 6: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/optimizer.py tests/test_optimizer.py && git commit -m "feat(r7): add optimize_strategy() with WF-validated grid search"
```

---

## Task 4: DB persistence — `save_optimizer_result` + `get_optimizer_result` (TDD)

**Files:**
- Modify: `tests/test_optimizer.py` (add tests)
- Modify: `engine/optimizer.py` (add 2 functions)

- [x] **Step 1: Add DB tests**

Append to `tests/test_optimizer.py`:

```python
# ─── DB persistence ───────────────────────────────────────────────────────────

def test_save_and_get_round_trip(tmp_path):
    from engine.optimizer import save_optimizer_result, get_optimizer_result
    db = str(tmp_path / 'test.db')
    result = {
        'strategy':    'vol_weighted',
        'best_params': {'vr_threshold': 2.0, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0},
        'oos_metrics': {
            'avg_sharpe': 0.85, 'avg_return_pct': 12.3,
            'avg_win_rate': 55.0, 'windows_tested': 3,
        },
    }
    save_optimizer_result('BRPT', 'vol_weighted', result, db)
    loaded = get_optimizer_result('BRPT', 'vol_weighted', db)
    assert loaded is not None
    assert loaded['ticker'] == 'BRPT'
    assert loaded['strategy'] == 'vol_weighted'
    assert loaded['best_params']['vr_threshold'] == 2.0
    assert loaded['oos_metrics']['avg_sharpe'] == 0.85
    assert 'updated_at' in loaded


def test_get_optimizer_result_returns_none_if_missing(tmp_path):
    from engine.optimizer import get_optimizer_result
    db = str(tmp_path / 'empty.db')
    assert get_optimizer_result('XXXX', 'vol_weighted', db) is None


def test_save_upserts_on_duplicate(tmp_path):
    from engine.optimizer import save_optimizer_result, get_optimizer_result
    db = str(tmp_path / 'upsert.db')
    r1 = {
        'strategy': 'momentum', 'best_params': {'vr_threshold': 1.3, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0},
        'oos_metrics': {'avg_sharpe': 0.5, 'avg_return_pct': 5.0, 'avg_win_rate': 50.0, 'windows_tested': 2},
    }
    r2 = {
        'strategy': 'momentum', 'best_params': {'vr_threshold': 2.0, 'atr_sl_mult': 1.2, 'atr_tp_mult': 2.4},
        'oos_metrics': {'avg_sharpe': 1.2, 'avg_return_pct': 18.0, 'avg_win_rate': 62.0, 'windows_tested': 3},
    }
    save_optimizer_result('BBCA', 'momentum', r1, db)
    save_optimizer_result('BBCA', 'momentum', r2, db)
    loaded = get_optimizer_result('BBCA', 'momentum', db)
    assert loaded['best_params']['vr_threshold'] == 2.0  # r2 overwrote r1


def test_ticker_upcased_on_save(tmp_path):
    from engine.optimizer import save_optimizer_result, get_optimizer_result
    db = str(tmp_path / 'case.db')
    result = {
        'strategy': 'conservative', 'best_params': {'vr_threshold': 1.5, 'atr_sl_mult': 0.7, 'atr_tp_mult': 1.4},
        'oos_metrics': {'avg_sharpe': 0.6, 'avg_return_pct': 7.0, 'avg_win_rate': 52.0, 'windows_tested': 2},
    }
    save_optimizer_result('bbca', 'conservative', result, db)
    loaded = get_optimizer_result('BBCA', 'conservative', db)
    assert loaded is not None
    assert loaded['ticker'] == 'BBCA'
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "save_and_get or get_optimizer or save_upserts or ticker_upcased" 2>&1 | head -20
```

Expected: `AttributeError: module 'engine.optimizer' has no attribute 'save_optimizer_result'`

- [x] **Step 3: Add DB functions to `engine/optimizer.py`**

Append after `optimize_strategy`:

```python
# ─── DB persistence ───────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS optimizer_results (
        ticker              TEXT NOT NULL,
        strategy            TEXT NOT NULL,
        best_params_json    TEXT NOT NULL,
        oos_avg_sharpe      REAL,
        oos_avg_return_pct  REAL,
        oos_avg_win_rate    REAL,
        windows_tested      INTEGER,
        updated_at          TEXT NOT NULL,
        PRIMARY KEY (ticker, strategy)
    )
"""


def save_optimizer_result(
    ticker: str,
    strategy_key: str,
    result: dict,
    db_path: str,
) -> None:
    """Upsert optimizer result for (ticker, strategy) into optimizer_results table."""
    oos  = result['oos_metrics']
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE_SQL)
    conn.execute(
        """
        INSERT OR REPLACE INTO optimizer_results
            (ticker, strategy, best_params_json, oos_avg_sharpe,
             oos_avg_return_pct, oos_avg_win_rate, windows_tested, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            ticker.upper(), strategy_key,
            json.dumps(result['best_params']),
            oos['avg_sharpe'],
            oos['avg_return_pct'],
            oos['avg_win_rate'],
            oos['windows_tested'],
            datetime.now().strftime('%Y-%m-%d %H:%M'),
        ),
    )
    conn.commit()
    conn.close()


def get_optimizer_result(
    ticker: str,
    strategy_key: str,
    db_path: str,
) -> dict | None:
    """Fetch cached optimizer result for (ticker, strategy). Returns None if missing."""
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE_SQL)
    row = conn.execute(
        """
        SELECT best_params_json, oos_avg_sharpe, oos_avg_return_pct,
               oos_avg_win_rate, windows_tested, updated_at
        FROM optimizer_results WHERE ticker=? AND strategy=?
        """,
        (ticker.upper(), strategy_key),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'ticker':      ticker.upper(),
        'strategy':    strategy_key,
        'best_params': json.loads(row[0]),
        'oos_metrics': {
            'avg_sharpe':     row[1],
            'avg_return_pct': row[2],
            'avg_win_rate':   row[3],
            'windows_tested': row[4],
        },
        'updated_at': row[5],
    }
```

- [x] **Step 4: Run tests — verify Task 4 tests pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "save_and_get or get_optimizer or save_upserts or ticker_upcased" 2>&1
```

Expected: 4 tests PASS

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/optimizer.py tests/test_optimizer.py && git commit -m "feat(r7): add save/get DB persistence for optimizer results"
```

---

## Task 5: REST endpoints in `routes/backtest.py` (TDD)

**Files:**
- Modify: `tests/test_optimizer.py` (add endpoint tests)
- Modify: `routes/backtest.py` (add 2 endpoints)

- [x] **Step 1: Add endpoint tests**

Append to `tests/test_optimizer.py`:

```python
# ─── REST endpoints ───────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path):
    """Flask test client with mocked optimizer."""
    import os
    os.environ['DB_PATH'] = str(tmp_path / 'test.db')
    from app import app
    app.config['TESTING'] = True
    return app.test_client()


def test_optimizer_run_returns_200_with_best_params(client, tmp_path):
    from unittest.mock import patch
    fake_result = {
        'strategy': 'vol_weighted',
        'best_params': {'vr_threshold': 2.0, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0},
        'oos_metrics': {'avg_sharpe': 0.9, 'avg_return_pct': 14.0, 'avg_win_rate': 58.0, 'windows_tested': 3},
        'windows': [],
    }
    import pandas as pd
    import numpy as np
    np.random.seed(1)
    n = 400
    close = np.cumprod(1 + np.random.normal(0.0003, 0.012, n)) * 1000
    fake_df = pd.DataFrame({
        'date':   pd.date_range('2021-01-04', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open':   (close * 0.998).round(0),
        'high':   (close * 1.015).round(0),
        'low':    (close * 0.985).round(0),
        'close':  close.round(0),
        'volume': np.random.randint(500_000, 3_000_000, n).astype(float),
    })
    with patch('routes.backtest.pd.read_sql', return_value=fake_df), \
         patch('routes.backtest.sqlite3.connect'), \
         patch('engine.optimizer.optimize_strategy', return_value=fake_result), \
         patch('engine.optimizer.save_optimizer_result'):
        resp = client.post('/api/optimizer/run',
                           json={'ticker': 'BBCA', 'strategy': 'vol_weighted'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['best_params']['vr_threshold'] == 2.0
    assert data['ticker'] == 'BBCA'


def test_optimizer_run_returns_400_if_ticker_missing(client):
    resp = client.post('/api/optimizer/run', json={'strategy': 'vol_weighted'})
    assert resp.status_code == 400


def test_optimizer_run_returns_422_for_unknown_strategy(client, tmp_path):
    import pandas as pd
    import numpy as np
    from unittest.mock import patch
    np.random.seed(1)
    n = 400
    close = np.cumprod(1 + np.random.normal(0, 0.01, n)) * 1000
    fake_df = pd.DataFrame({
        'date': pd.date_range('2021-01-04', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open': close.round(0), 'high': close.round(0),
        'low': close.round(0), 'close': close.round(0),
        'volume': np.ones(n) * 1_000_000,
    })
    with patch('routes.backtest.pd.read_sql', return_value=fake_df), \
         patch('routes.backtest.sqlite3.connect'):
        resp = client.post('/api/optimizer/run',
                           json={'ticker': 'BBCA', 'strategy': 'not_a_strategy'})
    assert resp.status_code == 422


def test_optimizer_result_get_returns_404_if_missing(client):
    resp = client.get('/api/optimizer/result/ZZZZ/vol_weighted')
    assert resp.status_code == 404


def test_optimizer_result_get_returns_200_with_cached(client, tmp_path):
    from unittest.mock import patch
    cached = {
        'ticker': 'BBCA', 'strategy': 'vol_weighted',
        'best_params': {'vr_threshold': 1.8, 'atr_sl_mult': 1.0, 'atr_tp_mult': 2.0},
        'oos_metrics': {'avg_sharpe': 0.7, 'avg_return_pct': 9.0, 'avg_win_rate': 54.0, 'windows_tested': 3},
        'updated_at': '2026-05-30 12:00',
    }
    with patch('engine.optimizer.get_optimizer_result', return_value=cached):
        resp = client.get('/api/optimizer/result/BBCA/vol_weighted')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['best_params']['vr_threshold'] == 1.8
```

- [x] **Step 2: Run tests to verify they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "optimizer_run or optimizer_result" 2>&1 | head -20
```

Expected: 404 for `/api/optimizer/run` (route not yet registered)

- [x] **Step 3: Add endpoints to `routes/backtest.py`**

Append to `routes/backtest.py` (after existing imports, add to top):

```python
import sqlite3
import pandas as pd
```

Then append 2 routes at the end of the file:

```python
@backtest_bp.route('/api/optimizer/run', methods=['POST'])
def api_optimizer_run():
    """
    POST /api/optimizer/run
    Body: {"ticker": "BRPT", "strategy": "vol_weighted", "capital": 50000000}
    Returns: best_params, oos_metrics, per-window detail.
    """
    body     = request.get_json(force=True)
    ticker   = (body.get('ticker') or '').strip().upper()
    strategy = (body.get('strategy') or '').strip()
    capital  = float(body.get('capital', 50_000_000))

    if not ticker or not strategy:
        return jsonify({'error': 'ticker and strategy required'}), 400

    from engine.optimizer import STRATEGY_RUNNERS, optimize_strategy, save_optimizer_result
    if strategy not in STRATEGY_RUNNERS:
        return jsonify({
            'error': f"Unknown strategy: {strategy!r}. Valid: {list(STRATEGY_RUNNERS)}"
        }), 422

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? ORDER BY date",
            conn, params=(ticker,),
        )
        conn.close()
        if len(df) < 60:
            return jsonify({'error': f'Insufficient data for {ticker}: {len(df)} bars'}), 400
        for col in ('open', 'high', 'low', 'close', 'volume'):
            df[col] = df[col].astype(float)

        result = optimize_strategy(df, strategy, capital)
        save_optimizer_result(ticker, strategy, result, DB_PATH)
        result['ticker'] = ticker
        # Strip verbose exit_reasons from window oos_metrics to keep response lean
        for w in result.get('windows', []):
            w['oos_metrics'].pop('exit_reasons', None)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/api/optimizer/result/<ticker>/<strategy>', methods=['GET'])
def api_optimizer_result(ticker, strategy):
    """GET cached optimizer result for (ticker, strategy)."""
    from engine.optimizer import get_optimizer_result
    result = get_optimizer_result(ticker.upper(), strategy, DB_PATH)
    if not result:
        return jsonify({'error': f'No optimizer result for {ticker}/{strategy}'}), 404
    return jsonify(result)
```

- [x] **Step 4: Check imports — ensure `sqlite3` and `pandas` are imported in `routes/backtest.py`**

Run:
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && head -20 routes/backtest.py
```

If `sqlite3` or `pandas` are missing from the top imports, add them. The existing file already imports `sqlite3` and `pd` — verify before adding duplicates.

- [x] **Step 5: Run endpoint tests**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v -k "optimizer_run or optimizer_result" 2>&1
```

Expected: 5 tests PASS

- [x] **Step 6: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/ -v --tb=short 2>&1 | tail -25
```

Expected: all tests PASS (no regressions)

- [x] **Step 7: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add routes/backtest.py tests/test_optimizer.py && git commit -m "feat(r7): add POST /api/optimizer/run + GET /api/optimizer/result endpoints"
```

---

## Task 6: Final verification + TODO update

- [x] **Step 1: Run all optimizer tests together**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_optimizer.py -v 2>&1 | tail -30
```

Expected: all tests PASS; count should be ≥ 30

- [x] **Step 2: Run full test suite one last time**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/ --tb=short -q 2>&1 | tail -10
```

Expected: no failures

- [x] **Step 3: Smoke test the API manually**

```bash
curl -s -X POST http://localhost:5001/api/optimizer/run \
  -H 'Content-Type: application/json' \
  -d '{"ticker": "BBCA", "strategy": "conservative", "capital": 50000000}' \
  | python3 -m json.tool | head -30
```

Expected: JSON with `best_params`, `oos_metrics`, `windows`, `ticker: "BBCA"`

- [x] **Step 4: Verify GET cached result**

```bash
curl -s http://localhost:5001/api/optimizer/result/BBCA/conservative | python3 -m json.tool
```

Expected: JSON with `best_params`, `oos_metrics`, `updated_at`

- [x] **Step 5: Update TODO.md — mark R7 complete**

In `TODO.md`, change:
```
- [x] **R7. Strategy parameter optimizer**
```
to:
```
- [x] **R7. Strategy parameter optimizer**
```

Add the completion note:
```
— `engine/optimizer.py`: PARAM_GRIDS (5 strategies), parameterized runners, grid_search, optimize_strategy (WF-validated), save/get DB. `POST /api/optimizer/run` + `GET /api/optimizer/result/<ticker>/<strategy>`. N unit tests. SHIPPED 2026-05-30.
```

- [x] **Step 6: Final commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add TODO.md && git commit -m "chore: mark R7 complete in TODO.md"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `engine/optimizer.py` — grid search + walk-forward validation
- ✅ VR thresholds tuned (all 4 signal-based strategies)
- ✅ ATR multipliers tuned (all 5 strategies)
- ✅ MA/period tuned (`donchian_period` in TFB)
- ✅ Per-ticker: runs on OHLCV for any ticker via REST endpoint
- ✅ DB persistence: `optimizer_results` table
- ✅ TDD throughout

**Placeholder check:** No TBDs, no "implement later", all code blocks complete.

**Type consistency:**
- `_run_*` functions return `dict` with keys: `trades`, `equity`, `initial_capital`, `final_capital`, `strategy`
- `compute_metrics()` expects exactly those keys — verified against `engine/walkforward_multi.py:29`
- `save_optimizer_result` expects `result['best_params']` and `result['oos_metrics']` — matches `optimize_strategy` return shape
- `get_optimizer_result` returns same schema expected by endpoint tests
