"""
Backtest Engine Core Utilities

Extracted from strategies.py for modular architecture.

Provides:
- Trade dataclass
- Position sizing (lot_size)
- TP/SL calculation (atr_tp_sl)
- Cost application (apply_costs)
- Generic backtest runner (run_strategy)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

from engine.indicators import calc_atr, calc_delta, calc_vol_ratio, calc_vwap


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
COMMISSION_BUY = 0.0015  # 0.15%
COMMISSION_SELL = 0.0025  # 0.25%
SLIPPAGE = 0.001  # 0.10%


@dataclass
class Trade:
    """Trade record for backtest results."""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    lots: int
    direction: str  # BUY
    exit_reason: str  # TP / SL / EOD / TRAIL
    pnl_rp: float
    pnl_pct: float
    strategy: str


# ─────────────────────────────────────────────
# POSITION SIZING
# ─────────────────────────────────────────────

def lot_size(capital: float, price: float, risk_pct: float, sl_pct: float) -> int:
    """
    Calculate lot size (1 lot = 100 shares) based on risk per trade.

    Args:
        capital: Available capital
        price: Entry price per share
        risk_pct: Risk percentage of capital (e.g., 0.02 = 2%)
        sl_pct: Stop loss percentage from entry

    Returns:
        Number of lots (min 1, capped at 30% of capital)
    """
    risk_rp = capital * risk_pct
    risk_per_lot = price * 100 * sl_pct

    # NaN/inf guard
    if not np.isfinite(risk_per_lot) or risk_per_lot <= 0 or not np.isfinite(risk_rp):
        return 1

    lots = int(risk_rp / risk_per_lot)

    # Cap: max 30% capital per trade
    max_lots = int((capital * 0.30) / (price * 100))
    lots = min(lots, max_lots)

    return max(1, lots)


# ─────────────────────────────────────────────
# TP/SL CALCULATION
# ─────────────────────────────────────────────

def atr_tp_sl(entry: float, atr: float, sl_mult: float = 1.0, min_rr: float = 2.0):
    """
    Compute ATR-based TP and SL ensuring minimum R/R ratio.

    Args:
        entry: Entry price
        atr: ATR value
        sl_mult: Stop loss multiplier (default 1.0x ATR)
        min_rr: Minimum risk/reward ratio (default 2.0)

    Returns:
        Tuple of (tp_price, sl_price, tp_pct, sl_pct)
    """
    sl_dist = atr * sl_mult
    sl_price = entry - sl_dist
    tp_price = entry + sl_dist * min_rr
    tp_pct = (tp_price - entry) / entry
    sl_pct = sl_dist / entry
    return tp_price, sl_price, tp_pct, sl_pct


# ─────────────────────────────────────────────
# COST APPLICATION
# ─────────────────────────────────────────────

def apply_costs(price: float, side: str) -> float:
    """
    Apply commission and slippage to price.

    Args:
        price: Base price
        side: 'BUY' or 'SELL'

    Returns:
        Price after costs
    """
    if side == 'BUY':
        return price * (1 + COMMISSION_BUY + SLIPPAGE)
    else:
        return price * (1 - COMMISSION_SELL - SLIPPAGE)


# ─────────────────────────────────────────────
# BASE BACKTEST ENGINE
# ─────────────────────────────────────────────

def run_strategy(df: pd.DataFrame, signals: pd.Series,
                 tp_pct: float = None, sl_pct: float = None,
                 strategy_name: str = '',
                 initial_capital: float = 50_000_000,
                 risk_per_trade: float = 0.02,
                 trail_sl: bool = False,
                 filters: list = None,
                 atr_sl_mult: float = None,
                 atr_tp_mult: float = None,
                 min_rr: float = 2.0) -> dict:
    """
    Generic backtest engine.

    Args:
        df: OHLCV DataFrame
        signals: Series of True/False per bar indicating entry signals
        tp_pct: Fixed take profit percentage (if not using ATR)
        sl_pct: Fixed stop loss percentage (if not using ATR)
        strategy_name: Name for trade records
        initial_capital: Starting capital
        risk_per_trade: Risk percentage per trade
        trail_sl: Enable trailing stop loss
        filters: List of filter functions (applied to signals)
        atr_sl_mult: ATR multiplier for SL (enables ATR-based TP/SL)
        atr_tp_mult: ATR multiplier for TP
        min_rr: Minimum risk/reward ratio for ATR-based TP/SL

    Returns:
        Dict with strategy, trades, equity, final_capital, initial_capital
    """
    from engine.strategies.filters import apply_filters  # Avoid circular import

    if filters:
        filter_mask = apply_filters(df, filters)
        signals = signals & filter_mask

    atr_series = calc_atr(df, 14) if atr_sl_mult is not None else None

    capital = initial_capital
    equity = [capital]
    trades = []
    in_trade = False
    entry_price = exit_price = 0.0
    entry_date = ""
    lots = 0
    peak_price = 0.0
    _tp_pct = tp_pct or 0.04
    _sl_pct = sl_pct or 0.02
    _tp_level = 0.0
    _sl_level_base = 0.0

    for i in range(1, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]

        if in_trade:
            hi = row['high']
            lo = row['low']
            cur = row['close']

            if trail_sl and row['high'] > peak_price:
                peak_price = row['high']

            sl_level = (peak_price * (1 - _sl_pct)) if trail_sl else _sl_level_base
            tp_level = _tp_level

            exit_reason = None
            if lo <= sl_level:
                exit_price = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'

            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name
                ))
                in_trade = False

        elif signals.iloc[i - 1]:
            raw_entry = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')

            if atr_sl_mult is not None and atr_series is not None:
                atr_val = atr_series.iloc[i - 1]
                if pd.isna(atr_val) or atr_val <= 0:
                    atr_val = entry_price * 0.015  # fallback 1.5%
                tp_price, sl_price, _tp_pct, _sl_pct = atr_tp_sl(
                    entry_price, atr_val, atr_sl_mult,
                    atr_tp_mult / atr_sl_mult if atr_tp_mult else min_rr
                )
                _tp_level = tp_price
                _sl_level_base = sl_price
            else:
                _tp_pct = tp_pct
                _sl_pct = sl_pct
                _tp_level = entry_price * (1 + _tp_pct)
                _sl_level_base = entry_price * (1 - _sl_pct)

            lots = lot_size(capital, entry_price, risk_per_trade, _sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital:
                in_trade = True
                entry_date = date
                peak_price = entry_price

        equity.append(capital)

    return {
        'strategy': strategy_name,
        'trades': trades,
        'equity': equity,
        'final_capital': capital,
        'initial_capital': initial_capital
    }
