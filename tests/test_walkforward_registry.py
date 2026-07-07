"""run_all_strategies must run every registered strategy without error.

Regression: strategy_vwma_breakout_pullback takes no `filters` kwarg;
run_all_strategies passed filters=... to every strategy → TypeError, silently
swallowed by _refresh_backtest_cache's per-ticker except since 2026-07-02.
"""
import numpy as np
import pandas as pd


def _ohlcv(n=120):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 1000 + np.cumsum(rng.normal(2, 10, n))
    close = np.maximum(close, 100.0)
    return pd.DataFrame({
        "date": dates,
        "open": close - 5, "high": close + 15, "low": close - 15,
        "close": close, "volume": rng.uniform(1e6, 3e6, n),
    })


def test_run_all_strategies_covers_registry_without_errors():
    from research.walkforward_multi import run_all_strategies, STRATEGY_FUNCS
    results = run_all_strategies(_ohlcv(), capital=50_000_000)
    names = {r["strategy"] for r in results}
    assert len(results) == len(STRATEGY_FUNCS)
    # result['strategy'] uses display names which differ from the snake_case
    # registry keys for a few entries; assert count + no duplicates.
    assert len(names) == len(results)
