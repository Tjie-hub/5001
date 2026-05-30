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
