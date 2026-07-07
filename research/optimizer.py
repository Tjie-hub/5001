"""
optimizer.py — Strategy Parameter Optimizer

Grid search + walk-forward validation for tuning VR thresholds,
ATR multipliers, and MA/period params per-ticker.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from engine.indicators import calc_atr, calc_delta, calc_vol_ratio, calc_vwap
from engine.strategies import (
    Trade,
    apply_costs,
    lot_size,
    run_strategy,
    _watch_signal_block,
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
    watch_block = _watch_signal_block(df)
    sig = streak2 & (vr > vr_threshold) & (vr <= 5.0) & ~watch_block
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

    start_bar = 65
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
    import sqlite3
    from datetime import datetime
    oos  = result['oos_metrics']
    conn = sqlite3.connect(db_path)
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
    import sqlite3
    conn = sqlite3.connect(db_path)
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
