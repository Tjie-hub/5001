"""
Engine Strategies Module

Provides:
- Strategy registry with decorator-based registration
- Core backtest utilities

Usage:
    # Register new strategies
    from engine.strategies.registry import register_strategy

    @register_strategy('My Strategy')
    def strategy_my_thing(df, capital, filters=None):
        ...

    # Get all strategies
    from engine.strategies.registry import STRATEGY_FUNCS
    for name, func in STRATEGY_FUNCS.items():
        ...

    # Use backtest utilities
    from engine.strategies.backtest import Trade, run_strategy, lot_size
"""

# Registry system
from .registry import register_strategy, STRATEGY_FUNCS, get_strategy, list_strategies, register_manual

# Core backtest utilities
from .backtest import Trade, lot_size, atr_tp_sl, apply_costs, run_strategy

# Filters
from .filters import (
    filter_vwma_above,
    filter_above_ma50,
    filter_low_atr,
    filter_vr_min,
    filter_uptrend,
    apply_filters,
)

__all__ = [
    # Registry
    'register_strategy',
    'register_manual',
    'STRATEGY_FUNCS',
    'get_strategy',
    'list_strategies',

    # Backtest utilities
    'Trade',
    'lot_size',
    'atr_tp_sl',
    'apply_costs',
    'run_strategy',

    # Filters
    'filter_vwma_above',
    'filter_above_ma50',
    'filter_low_atr',
    'filter_vr_min',
    'filter_uptrend',
    'apply_filters',
]
