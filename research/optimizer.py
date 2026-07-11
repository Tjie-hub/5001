"""
optimizer.py — Strategy Parameter Optimizer

Grid search + walk-forward validation for tuning VR thresholds,
ATR multipliers, and MA/period params per-ticker.

Every runner delegates to the CANONICAL engine implementation (shared exit
kernel included) — the optimizer only maps a param dict onto the canonical
function's search kwargs. It re-implements no entries, no stops (audit R-3:
the previous hand-rolled TFB copy still carried the C-8 intrabar look-ahead
that was fixed in the engine on 2026-06-30). Parity is CI-enforced by
tests/test_optimizer_parity.py.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from engine.strategies import (
    strategy_conservative,
    strategy_momentum,
    strategy_trend_following_breakout,
    strategy_vol_weighted,
    strategy_vwap_reversion,
)

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


# ─── Parameterized runners (thin canonical wrappers) ─────────────────────────

def _run_vol_weighted(df: pd.DataFrame, capital: float, params: dict) -> dict:
    return strategy_vol_weighted(
        df, capital=capital,
        vr_threshold=params.get('vr_threshold', 1.8),
        atr_sl_mult=params.get('atr_sl_mult', 1.0),
        atr_tp_mult=params.get('atr_tp_mult', 2.0))


def _run_momentum(df: pd.DataFrame, capital: float, params: dict) -> dict:
    return strategy_momentum(
        df, capital=capital,
        vr_threshold=params.get('vr_threshold', 1.3),
        atr_sl_mult=params.get('atr_sl_mult', 1.2),
        atr_tp_mult=params.get('atr_tp_mult', 2.4))


def _run_vwap_reversion(df: pd.DataFrame, capital: float, params: dict) -> dict:
    return strategy_vwap_reversion(
        df, capital=capital,
        dist_threshold=params.get('dist_threshold', -0.010),
        vr_threshold=params.get('vr_threshold', 1.3),
        atr_sl_mult=params.get('atr_sl_mult', 0.8),
        atr_tp_mult=params.get('atr_tp_mult', 1.6))


def _run_conservative(df: pd.DataFrame, capital: float, params: dict) -> dict:
    return strategy_conservative(
        df, capital=capital,
        vr_threshold=params.get('vr_threshold', 1.3),
        atr_sl_mult=params.get('atr_sl_mult', 0.7),
        atr_tp_mult=params.get('atr_tp_mult', 1.4))


def _run_tfb(df: pd.DataFrame, capital: float, params: dict) -> dict:
    # NOTE (audit R-3): the canonical TFB carries two entry gates the old
    # hand-rolled copy lacked (MA20 slope > 0.5, volume < 4x climax filter)
    # and the C-8-fixed prior-bar Chandelier trail. Optimizer results for TFB
    # therefore changed when this wrapper replaced the duplicate: they now
    # measure the strategy that actually trades.
    return strategy_trend_following_breakout(
        df, capital=capital,
        atr_mult=params.get('atr_trail_mult', 3.0),
        donchian_period=int(params.get('donchian_period', 20)),
        vol_mult=params.get('vol_mult', 1.8),
        atr_expand_mult=params.get('atr_expand_mult', 0.5))


STRATEGY_RUNNERS: dict[str, Any] = {
    'vol_weighted':             _run_vol_weighted,
    'momentum':                 _run_momentum,
    'vwap_reversion':           _run_vwap_reversion,
    'conservative':             _run_conservative,
    'trend_following_breakout': _run_tfb,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _iter_param_grid(grid: dict[str, list]) -> list[dict]:
    """Expand a param dict into a list of all combinations."""
    from itertools import product
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
    from research.walkforward_multi import compute_metrics
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
    import numpy as np
    from collections import Counter
    from research.walkforward_multi import compute_metrics, walk_forward_split

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
    param_wins         = Counter(str(w['best_params']) for w in window_results)
    winner_str         = param_wins.most_common(1)[0][0]
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
    import json
    from datetime import datetime
    from data.db import connect as db_connect
    oos  = result['oos_metrics']
    conn = db_connect(db_path)
    try:
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
    finally:
        conn.close()


def get_optimizer_result(
    ticker: str,
    strategy_key: str,
    db_path: str,
) -> dict | None:
    """Fetch cached optimizer result for (ticker, strategy). Returns None if missing."""
    import json
    from data.db import connect as db_connect
    conn = db_connect(db_path)
    try:
        conn.execute(_CREATE_TABLE_SQL)
        row = conn.execute(
            """
            SELECT best_params_json, oos_avg_sharpe, oos_avg_return_pct,
                   oos_avg_win_rate, windows_tested, updated_at
            FROM optimizer_results WHERE ticker=? AND strategy=?
            """,
            (ticker.upper(), strategy_key),
        ).fetchone()
    finally:
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
