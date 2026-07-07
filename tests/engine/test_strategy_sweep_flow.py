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


from engine.strategies import check_sweep_flow_signal


def test_live_check_fires_on_current_bar_sweep(monkeypatch):
    df = _trending_df_with_sweep()
    # Move the sweep to the LAST bar so the live check considers it current.
    n = len(df)
    df.loc[n - 1, 'low'] = df.loc[n - 2, 'low'] - 40
    df.loc[n - 1, 'close'] = df.loc[n - 2, 'low'] + 8
    df.loc[n - 1, 'high'] = df.loc[n - 1, 'close'] + 5

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': True, 'source': 'daily',
                                                    'reason': 'cs +5', 'score': 5})
    r = check_sweep_flow_signal(df, 'BBCA')
    assert r['has_signal'] is True
    assert 'sweep' in r['reason'].lower()


def test_live_check_blocked_by_negative_flow(monkeypatch):
    df = _trending_df_with_sweep()
    n = len(df)
    df.loc[n - 1, 'low'] = df.loc[n - 2, 'low'] - 40
    df.loc[n - 1, 'close'] = df.loc[n - 2, 'low'] + 8
    df.loc[n - 1, 'high'] = df.loc[n - 1, 'close'] + 5

    import engine.smc_flow as smc_flow
    monkeypatch.setattr(smc_flow, 'confirm_sweep_flow',
                        lambda t, d, db_path=None: {'confirmed': False, 'source': 'daily',
                                                    'reason': 'cs -3', 'score': -3})
    r = check_sweep_flow_signal(df, 'BBCA')
    assert r['has_signal'] is False
    assert 'flow' in r['reason'].lower()


def test_registered_in_strategy_funcs():
    from research.walkforward_multi import STRATEGY_FUNCS
    assert 'Liquidity Sweep' in STRATEGY_FUNCS


def test_dispatcher_routes_liquidity_sweep(monkeypatch):
    import engine.strategies as strat
    captured = {}

    def fake_check(df, ticker):
        captured['called'] = True
        return {'has_signal': False, 'reason': 'stub', 'details': {}}

    monkeypatch.setattr(strat, 'check_sweep_flow_signal', fake_check)
    df = _trending_df_with_sweep()
    strat.check_current_entry_signal('BBCA', 'Liquidity Sweep', df)
    assert captured.get('called') is True


def test_scanner_regime_wiring():
    from scheduler.scanner import _REGIME_STRATEGY_MAP, _COUNTER_TREND_BOOK, _MOMENTUM_FAMILY
    assert 'Liquidity Sweep' in _REGIME_STRATEGY_MAP['BEAR']
    assert 'Liquidity Sweep' in _REGIME_STRATEGY_MAP['SIDEWAYS']
    # NOT in the counter-trend book: its price-only backtest showed no edge, so
    # it is subject to the wf_scores consistency gate (must earn live status)
    # rather than bypassing it like Crash Recovery / Panic Rebound.
    assert 'Liquidity Sweep' not in _COUNTER_TREND_BOOK
    assert 'Liquidity Sweep' not in _MOMENTUM_FAMILY   # not panic-stripped
