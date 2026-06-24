import sqlite3
import pandas as pd
import numpy as np
from engine.strategies import strategy_liquidity_sweep_flow


def _trending_df_with_sweep(n=80):
    """Build a long uptrending series with a clean bullish PDL sweep near the end."""
    dates = pd.date_range('2026-02-01', periods=n, freq='B').strftime('%Y-%m-%d')
    base = np.linspace(1000, 1400, n)
    o = base.copy(); h = base + 15; l = base - 15; c = base + 5
    vol = np.full(n, 1_000_000)
    # Inject a sweep at bar n-2: deep wick below previous low, close back up.
    l[n - 2] = base[n - 3] - 40
    h[n - 2] = base[n - 2] + 10
    c[n - 2] = base[n - 2] + 8
    vol[n - 2] = 2_000_000
    return pd.DataFrame({'date': dates, 'open': o, 'high': h, 'low': l,
                         'close': c, 'volume': vol})


def test_price_only_backtest_runs_when_ticker_none():
    df = _trending_df_with_sweep()
    result = strategy_liquidity_sweep_flow(df, ticker=None)
    assert result['strategy'] == 'Liquidity Sweep'
    assert 'trades' in result
    assert isinstance(result['final_capital'], (int, float))


def test_negative_flow_blocks_the_entry(tmp_path, monkeypatch):
    df = _trending_df_with_sweep()
    base_trades = len(strategy_liquidity_sweep_flow(df, ticker=None)['trades'])

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': False, 'source': 'daily',
                                                    'reason': 'forced', 'score': -9})
    gated_trades = len(strategy_liquidity_sweep_flow(df, ticker='BBCA')['trades'])
    assert gated_trades <= base_trades
    assert gated_trades == 0
