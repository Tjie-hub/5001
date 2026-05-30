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
