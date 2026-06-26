"""
Strategy Registry with Decorator-Based Auto-Discovery

Eliminates manual STRATEGY_FUNCS updates when adding new strategies.
Use @register_strategy decorator on strategy functions.

Usage:
    from engine.strategies.registry import register_strategy, STRATEGY_FUNCS

    @register_strategy('My Strategy')
    def strategy_my_thing(df, capital, filters=None):
        ...

Then in walkforward_multi.py:
    from engine.strategies.registry import STRATEGY_FUNCS
"""

from typing import Callable, Dict, Any

# Central registry — single source of truth
_strategies: Dict[str, Callable] = {}


def register_strategy(name: str) -> Callable:
    """
    Decorator to register a strategy function in the central registry.

    Args:
        name: Strategy name (will be used in STRATEGY_FUNCS dict key)

    Example:
        @register_strategy('Trend Following Breakout')
        def strategy_trend_following_breakout(df, capital, filters=None):
            ...
    """
    def decorator(func: Callable) -> Callable:
        _strategies[name] = func
        return func

    return decorator


def get_strategies() -> Dict[str, Callable]:
    """
    Get the complete strategy registry.

    Returns:
        Dict mapping strategy names to their implementation functions.
    """
    return _strategies.copy()


def get_strategy(name: str) -> Callable | None:
    """
    Get a specific strategy by name.

    Args:
        name: Strategy name

    Returns:
        Strategy function or None if not found.
    """
    return _strategies.get(name)


def list_strategies() -> list[str]:
    """
    List all registered strategy names.

    Returns:
        Sorted list of strategy names.
    """
    return sorted(_strategies.keys())


# Alias for backward compatibility with existing code
STRATEGY_FUNCS = _strategies


# ────────────────────────────────────────────────────────────────────────────────
# Legacy: Manual registration for strategies that can't use the decorator
# (e.g., strategies from other modules like regime_filter.py)
# ────────────────────────────────────────────────────────────────────────────────

def register_manual(name: str, func: Callable) -> None:
    """
    Manually register a strategy (for strategies from other modules).

    Args:
        name: Strategy name
        func: Strategy function
    """
    _strategies[name] = func


if __name__ == '__main__':
    # Test: Show all registered strategies
    print("Registered Strategies:")
    for name in list_strategies():
        func = get_strategy(name)
        print(f"  {name}: {func.__name__ if func else 'None'}")
    print(f"\nTotal: {len(_strategies)}")
