"""Tests for engine/portfolio_backtest.py"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch


def _make_df(n=80, seed=42):
    np.random.seed(seed)
    close = np.cumprod(1 + np.random.normal(0.0005, 0.02, n)) * 1000
    return pd.DataFrame({
        'date':   pd.date_range('2024-01-02', periods=n, freq='B').strftime('%Y-%m-%d'),
        'open':   (close * 0.99).round(0),
        'high':   (close * 1.02).round(0),
        'low':    (close * 0.97).round(0),
        'close':  close.round(0),
        'volume': np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })


def test_run_returns_expected_keys():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')
    assert 'portfolio' in result
    assert 'per_ticker' in result
    assert 'correlation' in result
    assert 'tickers_used' in result
    assert 'tickers_skipped' in result


def test_equity_curve_length_equals_date_intersection():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    assert len(result['portfolio']['equity_curve']) == 80


def test_portfolio_return_equals_equal_weight_average():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    r_a = result['per_ticker'][0]['total_return_pct']
    r_b = result['per_ticker'][1]['total_return_pct']
    expected = (r_a + r_b) / 2
    assert abs(result['portfolio']['total_return_pct'] - expected) < 1.0


def test_correlation_matrix_symmetric_and_diagonal_one():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_a = _make_df(80, seed=1)
    df_b = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_a if ticker == 'AAA' else df_b

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')

    m = result['correlation']['matrix']
    assert m[0][0] == 1.0
    assert m[1][1] == 1.0
    assert abs(m[0][1] - m[1][0]) < 0.001


def test_ticker_skipped_if_less_than_60_bars():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_short = _make_df(30, seed=1)
    df_ok    = _make_df(80, seed=2)

    def _mock(ticker, db_path):
        return df_short if ticker == 'SHORT' else df_ok

    with patch('engine.portfolio_backtest._load_ohlcv', side_effect=_mock):
        result = run_portfolio_backtest(['SHORT', 'OK'], 'vol_weighted', 10_000_000, ':memory:')

    assert 'SHORT' in result['tickers_skipped']
    assert 'OK' in result['tickers_used']


def test_all_skipped_raises_value_error():
    from engine.portfolio_backtest import run_portfolio_backtest
    df_short = _make_df(30, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df_short):
        with pytest.raises(ValueError, match='No tickers with sufficient data'):
            run_portfolio_backtest(['AAA', 'BBB'], 'vol_weighted', 10_000_000, ':memory:')


def test_unknown_strategy_raises_value_error():
    from engine.portfolio_backtest import run_portfolio_backtest
    with pytest.raises(ValueError, match='Unknown strategy'):
        run_portfolio_backtest(['AAA'], 'nonexistent_strat', 10_000_000, ':memory:')


def test_single_ticker_correlation_is_one_by_one():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA'], 'vol_weighted', 10_000_000, ':memory:')
    assert result['correlation']['matrix'] == [[1.0]]
    assert result['correlation']['tickers'] == ['AAA']


def test_per_ticker_allocation_sums_to_capital():
    from engine.portfolio_backtest import run_portfolio_backtest
    df = _make_df(80, seed=1)
    with patch('engine.portfolio_backtest._load_ohlcv', return_value=df):
        result = run_portfolio_backtest(['AAA', 'BBB', 'CCC'], 'vol_weighted', 9_000_000, ':memory:')
    total = sum(t['allocation'] for t in result['per_ticker'])
    assert abs(total - 9_000_000) < 10
