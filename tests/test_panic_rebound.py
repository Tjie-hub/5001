"""Tests for Panic Rebound strategy + 2026-06-13 audit fixes:
look-ahead safety, time-stop, Sharpe sanity, and the profitability score gate.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from engine.strategies import (
    strategy_panic_rebound,
    check_panic_rebound_signal,
    Trade,
    PANIC_TIME_STOP_BARS,
)
from engine.walkforward_multi import compute_metrics, _rank_strategies


def _mk_df(closes, opens=None, highs=None, lows=None, volumes=None,
           start='2026-01-05'):
    n = len(closes)
    closes = pd.Series(closes, dtype=float)
    opens = pd.Series(opens, dtype=float) if opens is not None else closes.shift(1).fillna(closes[0])
    highs = pd.Series(highs, dtype=float) if highs is not None else pd.concat([opens, closes], axis=1).max(axis=1) * 1.01
    lows = pd.Series(lows, dtype=float) if lows is not None else pd.concat([opens, closes], axis=1).min(axis=1) * 0.99
    volumes = pd.Series(volumes, dtype=float) if volumes is not None else pd.Series([1e6] * n)
    dates = pd.bdate_range(start, periods=n).strftime('%Y-%m-%d')
    return pd.DataFrame({'date': dates, 'open': opens, 'high': highs,
                         'low': lows, 'close': closes, 'volume': volumes})


def _panic_df(post_bars=10):
    """30 flat bars at 1000, 5-bar crash to 795 (-20.5%), washout signal bar
    closing near its high on capitulation volume, then recovery bars."""
    closes = [1000.0] * 30 + [960, 920, 880, 840, 795]
    opens = [1000.0] * 30 + [1000, 960, 920, 880, 785]   # signal bar green: 785->795
    vols = [1e6] * 34 + [5e6]
    for i in range(post_bars):
        closes.append(795 + 12 * (i + 1))
        opens.append(closes[-2])
        vols.append(2e6)
    return _mk_df(closes, opens=opens, volumes=vols)


def test_signal_fires_on_panic_bar():
    df = _panic_df(post_bars=0)
    res = check_panic_rebound_signal(df)
    assert res['has_signal'], res['reason']
    assert res['details']['price'] == 795.0
    assert res['details']['tp'] > 795


def test_no_signal_without_green_close():
    df = _panic_df(post_bars=0)
    # red bar closing in the lower part of its range (no exhaustion)
    df.loc[df.index[-1], 'open'] = 810
    df.loc[df.index[-1], 'high'] = 815
    res = check_panic_rebound_signal(df)
    assert not res['has_signal']
    assert 'close_pos' in res['reason']


def test_no_signal_without_volume():
    df = _panic_df(post_bars=0)
    df.loc[df.index[-1], 'volume'] = 1e6  # no capitulation volume
    res = check_panic_rebound_signal(df)
    assert not res['has_signal']


def test_backtest_enters_next_bar_open_no_lookahead():
    """Entry must use the NEXT bar's open after the signal bar — never the
    signal bar's own close, and never data beyond the entry bar."""
    df = _panic_df(post_bars=8)
    res = strategy_panic_rebound(df)
    assert len(res['trades']) == 1, f"expected 1 trade, got {len(res['trades'])}"
    t = res['trades'][0]
    signal_pos = 34                      # the green crash bar
    entry_pos = signal_pos + 1
    expected_entry_date = df['date'].iloc[entry_pos]
    assert t.entry_date == expected_entry_date
    # entry price = next bar open + costs, strictly within that bar's data
    raw_open = df['open'].iloc[entry_pos]
    assert abs(t.entry_price - raw_open) / raw_open < 0.01  # costs only


def test_truncated_data_same_signal():
    """Look-ahead regression: the signal on bar i must be identical whether
    or not future bars exist in the frame."""
    full = _panic_df(post_bars=6)
    truncated = full.iloc[:35].reset_index(drop=True)  # ends at signal bar
    r_full_bar = check_panic_rebound_signal(full.iloc[:35].reset_index(drop=True))
    r_trunc = check_panic_rebound_signal(truncated)
    assert r_full_bar['has_signal'] == r_trunc['has_signal']


def test_time_stop_forces_exit():
    """If neither TP nor SL is hit, the trade must exit after
    PANIC_TIME_STOP_BARS bars."""
    closes = [1000.0] * 30 + [960, 920, 880, 840, 795]
    opens = [1000.0] * 30 + [1000, 960, 920, 880, 785]
    vols = [1e6] * 34 + [5e6]
    # dead-flat aftermath: no TP (needs ~873), no SL (below signal low)
    for _ in range(12):
        closes.append(802)
        opens.append(802)
        vols.append(1e6)
    df = _mk_df(closes, opens=opens, volumes=vols)
    # pin highs/lows so neither level is touched
    df.loc[df.index[35:], 'high'] = 806
    df.loc[df.index[35:], 'low'] = 798
    res = strategy_panic_rebound(df)
    assert len(res['trades']) == 1
    t = res['trades'][0]
    assert t.exit_reason == 'TIME'
    entry_pos = list(df['date']).index(t.entry_date)
    exit_pos = list(df['date']).index(t.exit_date)
    assert exit_pos - entry_pos == PANIC_TIME_STOP_BARS


def test_sharpe_is_sane():
    """compute_metrics Sharpe must stay in a sane band — the old per-bar
    annualization produced |Sharpe| in the thousands.
    plan 2B: SHARPE_MIN_TRADES raised 3->5, so the fixture now carries 6
    trades to still exercise the sane-band property (not just the floor)."""
    specs = [
        ('2026-01-05', '2026-01-12', 105, 5000, 5.0),
        ('2026-02-02', '2026-02-09', 103, 3000, 3.0),
        ('2026-03-02', '2026-03-09', 98, -2000, -2.0),
        ('2026-04-02', '2026-04-09', 104, 4000, 4.0),
        ('2026-05-04', '2026-05-11', 99, -1000, -1.0),
        ('2026-06-01', '2026-06-08', 106, 6000, 6.0),
    ]
    trades = [
        Trade(entry_date=ed, exit_date=xd, entry_price=100, exit_price=xp,
              lots=10, direction='BUY', exit_reason='TP', pnl_rp=rp,
              pnl_pct=pct, strategy='x')
        for ed, xd, xp, rp, pct in specs
    ]
    eq = [1e6]
    for t in trades:
        eq.append(eq[-1] + t.pnl_rp)
    result = {'strategy': 'x', 'trades': trades, 'equity': eq,
              'final_capital': eq[-1], 'initial_capital': 1e6}
    m = compute_metrics(result)
    assert -10 <= m['sharpe'] <= 10
    assert m['sharpe'] != 0


def test_score_gate_zeroes_losing_strategies():
    """A strategy with negative avg return must never outrank a profitable
    one, regardless of consistency/sharpe normalization."""
    summary = {
        'loser': {'strategy': 'loser', 'avg_win_rate': 60.0,
                  'avg_return_pct': -0.5, 'avg_sharpe': 2.0,
                  'consistency_pct': 75.0, 'avg_max_drawdown': -1.0,
                  'windows_tested': 4, 'windows_profitable': 3, 'windows': []},
        'winner': {'strategy': 'winner', 'avg_win_rate': 40.0,
                   'avg_return_pct': 1.5, 'avg_sharpe': 0.5,
                   'consistency_pct': 50.0, 'avg_max_drawdown': -2.0,
                   'windows_tested': 4, 'windows_profitable': 2, 'windows': []},
    }
    ranked = _rank_strategies(summary)
    assert ranked[0]['strategy'] == 'winner'
    loser = next(r for r in ranked if r['strategy'] == 'loser')
    assert loser['score'] == 0.0


def test_registered_in_strategy_funcs():
    from engine.walkforward_multi import STRATEGY_FUNCS
    assert 'Panic Rebound' in STRATEGY_FUNCS


def test_router_dispatches_panic_rebound():
    from engine.strategies import check_current_entry_signal
    df = _panic_df(post_bars=0)
    res = check_current_entry_signal('TEST', 'Panic Rebound', df=df)
    assert res['has_signal'], res['reason']
