"""
walkforward_multi.py — Walk-Forward Engine + Metrics Calculator
Untuk idx-walkforward integration
"""

import pandas as pd
import numpy as np
from typing import List
from .strategies import (
    strategy_vol_weighted,
    strategy_momentum,
    strategy_vwap_reversion,
    strategy_conservative,
    strategy_volume_profile_poc,
    strategy_inside_bar_breakout,
    strategy_nr7_breakout,
    strategy_orb,
    strategy_vwma_breakout_pullback,
    strategy_swing_trend,
    strategy_trend_following_breakout,
    strategy_crash_recovery,
    strategy_panic_rebound,
    strategy_liquidity_sweep_flow,
    Trade
)
from engine.indicators import get_warmup, calc_atr, calc_adx, calc_ma_slope, calc_vwap


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────

def compute_metrics(result: dict) -> dict:
    trades: List[Trade] = result['trades']
    equity = result['equity']
    capital_init = result['initial_capital']

    if not trades:
        return {
            'strategy': result['strategy'],
            'total_trades': 0, 'total_winners': 0,
            'win_rate': 0, 'avg_pnl_pct': 0, 'avg_pnl_rp': 0,
            'total_pnl_rp': 0, 'total_return_pct': 0,
            'max_drawdown_pct': 0, 'sharpe': 0, 'profit_factor': 0,
            'avg_hold_days': 0, 'best_trade_pct': 0, 'worst_trade_pct': 0
        }

    pnls     = [t.pnl_rp  for t in trades]
    pnls_pct = [t.pnl_pct for t in trades]
    winners  = [p for p in pnls if p > 0]
    losers   = [p for p in pnls if p < 0]

    # Hold days
    hold_days = []
    for t in trades:
        try:
            d1 = pd.to_datetime(t.entry_date)
            d2 = pd.to_datetime(t.exit_date)
            hold_days.append((d2 - d1).days)
        except:
            hold_days.append(0)

    # Max Drawdown dari equity curve
    eq  = np.array(equity)
    peak = np.maximum.accumulate(eq)
    dd   = (eq - peak) / peak
    max_dd = dd.min() * 100   # negative %

    # Sharpe on per-trade returns, annualized by realized trade frequency.
    # The equity list has one point per closed trade, so pct_change() yields
    # per-trade (not daily) returns — annualizing those with sqrt(252)
    # produced the +-1000s garbage that polluted wf_scores.avg_sharpe.
    sharpe = 0.0
    if len(pnls_pct) >= 3:
        rets = np.array(pnls_pct) / 100.0
        ret_std = rets.std(ddof=1)
        if ret_std > 0:
            try:
                span_days = max(
                    (pd.to_datetime(trades[-1].exit_date)
                     - pd.to_datetime(trades[0].entry_date)).days, 1)
            except Exception:
                span_days = 365
            trades_per_year = len(rets) * 365.0 / span_days
            sharpe = float(np.clip(
                rets.mean() / ret_std * np.sqrt(trades_per_year), -10.0, 10.0))

    # Profit Factor
    gross_profit = sum(winners)
    gross_loss   = abs(sum(losers))
    pf = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    total_pnl = sum(pnls)
    total_return = (result['final_capital'] - capital_init) / capital_init * 100

    return {
        'strategy':        result['strategy'],
        'total_trades':    len(trades),
        'total_winners':   len(winners),
        'win_rate':        round(len(winners) / len(trades) * 100, 1),
        'avg_pnl_pct':     round(np.mean(pnls_pct), 2),
        'avg_pnl_rp':      round(np.mean(pnls)),
        'total_pnl_rp':    round(total_pnl),
        'total_return_pct':round(total_return, 2),
        'max_drawdown_pct':round(max_dd, 2),
        'sharpe':          round(sharpe, 2),
        'profit_factor':   round(pf, 2) if pf != float('inf') else 999,
        'avg_hold_days':   round(np.mean(hold_days), 1) if hold_days else 0,
        'best_trade_pct':  round(max(pnls_pct), 2),
        'worst_trade_pct': round(min(pnls_pct), 2),
        'exit_reasons':    _count_exits(trades)
    }


def _count_exits(trades: List[Trade]) -> dict:
    counts = {'TP': 0, 'SL': 0, 'EOD': 0, 'TRAIL': 0}
    for t in trades:
        counts[t.exit_reason] = counts.get(t.exit_reason, 0) + 1
    return counts


# ─────────────────────────────────────────────
# WALK-FORWARD
# ─────────────────────────────────────────────

def walk_forward_split(df: pd.DataFrame,
                       train_months: int = 12,
                       test_months:  int = 3) -> List[dict]:
    """
    Bagi df menjadi rolling train/test windows.
    Returns list of {'train': df, 'test': df, 'window': N}
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    windows = []
    start   = df['date'].min()
    end     = df['date'].max()

    step_months = test_months
    window_num  = 0

    cur = start
    while True:
        train_end = cur + pd.DateOffset(months=train_months)
        test_end  = train_end + pd.DateOffset(months=test_months)

        if test_end > end:
            break

        train_df = df[(df['date'] >= cur) & (df['date'] < train_end)].reset_index(drop=True)
        test_df  = df[(df['date'] >= train_end) & (df['date'] < test_end)].reset_index(drop=True)

        if len(train_df) > 60 and len(test_df) > 15:
            windows.append({
                'window':    window_num,
                'train_start': str(cur.date()),
                'train_end':   str(train_end.date()),
                'test_start':  str(train_end.date()),
                'test_end':    str(test_end.date()),
                'train': train_df,
                'test':  test_df
            })
            window_num += 1

        cur += pd.DateOffset(months=step_months)

    return windows


PF_SENTINEL = 999   # profit_factor stand-in for "no losing trades" (inf)


def _summarize_strategy(name: str, window_list: list) -> dict:
    """Aggregate per-window metrics into one strategy summary row.

    avg_profit_factor averages only the FINITE-PF windows; when every window
    was lossless (all PF == PF_SENTINEL) the mean of an empty list is NaN
    (audit item 2.7) — report the sentinel instead. total_trades exposes the
    pooled sample size so consumers can see how thin a score is.
    """
    n = len(window_list)
    avg_wr  = float(np.mean([w['win_rate']        for w in window_list]))
    avg_ret = float(np.mean([w['total_return_pct'] for w in window_list]))
    avg_dd  = float(np.mean([w['max_drawdown_pct'] for w in window_list]))
    avg_sh  = float(np.mean([w['sharpe']           for w in window_list]))

    finite_pf = [w['profit_factor'] for w in window_list
                 if w['profit_factor'] < PF_SENTINEL]
    if finite_pf:
        avg_pf = round(float(np.mean(finite_pf)), 2)
    else:
        avg_pf = PF_SENTINEL   # every window lossless -> keep the sentinel, never NaN

    n_profitable = sum(1 for w in window_list if w['total_return_pct'] > 0)
    total_trades = sum(w.get('total_trades', 0) for w in window_list)

    return {
        'strategy':            name,
        'windows_tested':      n,
        'windows_profitable':  n_profitable,
        'consistency_pct':     round(n_profitable / n * 100, 1),
        'avg_win_rate':        round(avg_wr, 1),
        'avg_return_pct':      round(avg_ret, 2),
        'avg_max_drawdown':    round(avg_dd, 2),
        'avg_sharpe':          round(avg_sh, 2),
        'avg_profit_factor':   avg_pf,
        'total_trades':        total_trades,
        'windows':             window_list,
    }


STRATEGY_FUNCS = {
    'vol_weighted':              strategy_vol_weighted,
    'momentum':                  strategy_momentum,
    'vwap_reversion':            strategy_vwap_reversion,
    'conservative':              strategy_conservative,
    'Volume Profile POC':        strategy_volume_profile_poc,
    'Inside Bar Breakout':       strategy_inside_bar_breakout,
    'NR7 Breakout':              strategy_nr7_breakout,
    'ORB':                       strategy_orb,
    'VWMA Breakout Pullback':    strategy_vwma_breakout_pullback,
    'Swing Trend':               strategy_swing_trend,
    'Trend Following Breakout':  strategy_trend_following_breakout,
    'Crash Recovery':            strategy_crash_recovery,
    'Panic Rebound':             strategy_panic_rebound,
    'Liquidity Sweep':           strategy_liquidity_sweep_flow,
    # 'Regime Adaptive' deregistered 2026-07-02 (audit C-7): whole-window
    # look-ahead — regime chosen from the window's LAST bar. The function
    # remains in engine/regime_filter.py; re-register only after a per-bar
    # reimplementation.
}


def run_all_strategies(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> List[dict]:
    """Full backtest semua strategi terdaftar pada df penuh."""
    results = []
    for name, func in STRATEGY_FUNCS.items():
        if func.__name__ == "strategy_vwma_breakout_pullback":
            raw = func(df, capital=capital)   # takes no filters kwarg
        else:
            raw = func(df, capital=capital, filters=filters)
        metrics = compute_metrics(raw)
        metrics['equity'] = raw['equity']
        metrics['trades_detail'] = [
            {
                'entry_date':  t.entry_date,
                'exit_date':   t.exit_date,
                'entry_price': round(t.entry_price),
                'exit_price':  round(t.exit_price),
                'lots':        t.lots,
                'exit_reason': t.exit_reason,
                'pnl_rp':      round(t.pnl_rp),
                'pnl_pct':     round(t.pnl_pct, 2),
            }
            for t in raw['trades']
        ]
        results.append(metrics)
    return results


def run_walk_forward(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Walk-forward: train 12 bulan, test 3 bulan, rolling.
    Returns summary per strategy + per window.
    """
    windows = walk_forward_split(df, train_months=12, test_months=3)
    if not windows:
        return {'error': 'Data tidak cukup untuk walk-forward (butuh minimal 15 bulan)'}

    wf_results = {name: [] for name in STRATEGY_FUNCS}

    # Warmup tail prepended to each test_df so indicator-heavy strategies
    # (TFB needs 60-bar ATR median, Swing Trend needs 50-bar MA) can compute
    # indicators when the test slice (~65 bars) is shorter than their warmup.
    # Trades opened during the warmup portion are filtered out post-hoc.
    # Derived from the heaviest-warmup indicators across all strategies:
    # calc_vwap(window=60) dominates; calc_adx(28), calc_ma_slope(25), calc_atr(14) follow.
    WARMUP_BARS = get_warmup([calc_vwap, calc_adx, calc_ma_slope, calc_atr])  # → 60

    for w in windows:
        test_df = w['test']
        train_df = w['train']
        test_start_str = w['test_start']

        warmup_tail = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended_df = pd.concat([warmup_tail, test_df], ignore_index=True)

        for name, func in STRATEGY_FUNCS.items():
            if func.__name__ == "strategy_vwma_breakout_pullback":
                raw = func(extended_df, capital=capital)   # takes no filters kwarg
            else:
                raw = func(extended_df, capital=capital, filters=filters)

            # Filter to test-window-only trades; rebuild equity & final_capital.
            kept = [t for t in raw['trades'] if t.entry_date >= test_start_str]
            new_equity = [capital]
            cur_cap = capital
            for t in kept:
                cur_cap += t.pnl_rp
                new_equity.append(cur_cap)
            raw['trades'] = kept
            raw['equity'] = new_equity
            raw['final_capital'] = cur_cap
            raw['initial_capital'] = capital

            metrics = compute_metrics(raw)
            metrics['window']      = w['window']
            metrics['test_start']  = w['test_start']
            metrics['test_end']    = w['test_end']
            metrics['train_start'] = w['train_start']
            wf_results[name].append(metrics)

    # Summary per strategy
    summary = {}
    for name, window_list in wf_results.items():
        if not window_list:
            continue
        summary[name] = _summarize_strategy(name, window_list)

    # Rank: weighted score — profit-first (return 40%, others 15% each).
    # Rebalanced 2026-05-18: pure consistency was picking strategies that
    # bleed money (vwap_reversion, vol_weighted, conservative) over the
    # actually-profitable ones (TFB, momentum, NR7 Breakout).
    ranked = _rank_strategies(summary)

    return {
        'mode':     'walk_forward',
        'windows':  len(windows),
        'summary':  summary,
        'ranked':   ranked,
        'best':     ranked[0]['strategy'] if ranked else None
    }


def _rank_strategies(summary: dict) -> List[dict]:
    rows = list(summary.values())
    if not rows:
        return []

    # Normalize each metric 0–1
    def norm(vals):
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [0.5] * len(vals)
        return [(v - mn) / (mx - mn) for v in vals]

    wr   = norm([r['avg_win_rate']       for r in rows])
    ret  = norm([r['avg_return_pct']     for r in rows])
    sh   = norm([r['avg_sharpe']         for r in rows])
    cons = norm([r['consistency_pct']    for r in rows])
    dd   = norm([-r['avg_max_drawdown']  for r in rows])  # less negative = better

    for i, r in enumerate(rows):
        r['score'] = round(
            wr[i]   * 0.15 +
            ret[i]  * 0.40 +
            sh[i]   * 0.15 +
            cons[i] * 0.15 +
            dd[i]   * 0.15, 3
        )
        # Hard profitability gate: normalization is relative within ticker,
        # so the "best of a losing bunch" could still score near 1.0 and get
        # routed live by adaptive_strategy_selector. A strategy that loses
        # money on average is never selectable, period.
        if r['avg_return_pct'] <= 0:
            r['score'] = 0.0

    return sorted(rows, key=lambda x: x['score'], reverse=True)
