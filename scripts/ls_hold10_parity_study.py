"""Liquidity Sweep hold_days=10 rule-parity study — research-only, no production writes.

Context (audit P-3, handover 2026-09-03): ExitPolicyRegistry['Liquidity Sweep']
gained hold_days=10 on 2026-09-03 because a shadow position (JSMR) sat open 43
sessions. The researched backtest (engine.strategies.run_strategy) has NO time
bound — it hardcodes PositionView(hold_days=0) on every bar, so the TIME branch
can never fire. Forward/shadow and research therefore measure DIFFERENT rules.

This study closes the parity gap by re-running the exact wf-refresh OOS
methodology (research.walkforward_multi.walk_forward_split: rolling 12m train /
3m test, warmup tail 60, trades filtered to entry_date >= test_start,
trade-weighted pooling, n>=20 evidence floor) under BOTH exit variants in one
harness on the identical signals:

  A baseline : no hold cap (semantically identical to run_strategy)
  B parity   : hold_days=10 — the forward/shadow definition (engine.exits.policy)

Faithfulness gates, checked before variant B is interpretable:
  1. harness-baseline vs direct run_strategy() on a smoke sample: trade-for-trade
     equality of n, expectancy, win rate.
  2. harness-baseline per-ticker aggregates vs persisted wf_edge rows for
     'Liquidity Sweep' (run 08ff0ca6, 2026-08-28): n must match exactly;
     expectancy within per-window 2dp rounding tolerance.

Output: data/reports/ls_hold10_parity_<date>.md (+ per-ticker CSV next to it).
Usage:
  python -m scripts.ls_hold10_parity_study                # full corpus
  python -m scripts.ls_hold10_parity_study --tickers AALI,BBCA --smoke
"""
import argparse
import csv
import os
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

from config import DB_PATH
from data.loaders import _load_ohlcv_bulk
from engine.exits import ExitPolicy, PositionView, Bar, evaluate_exit
from engine.smc import calc_sweep_signal
from engine.strategies import apply_costs, lot_size, run_strategy
from engine.indicators import calc_atr
from research.walkforward_multi import walk_forward_split

WARMUP_BARS = 60          # wf-refresh default warmup (calc_vwap dominates)
HOLD_PARITY = 10          # ExitPolicyRegistry['Liquidity Sweep'].hold_days
SMOKE_TICKERS = 5         # tickers used for the direct run_strategy comparison
N_MIN_TRADES = 20         # engine.wf_edge.N_MIN_TRADES evidence floor
WARMUP_TAIL = 60


def simulate(df: pd.DataFrame, hold_cap) -> list:
    """run_strategy replica for Liquidity Sweep with an explicit hold cap.

    Identical loop/exit kernel to engine.strategies.run_strategy (same entry
    rule, costs, lot sizing, ATR policy, prior-bar trail anchor); the only
    delta is PositionView.hold_days, which run_strategy hardcodes to 0.
    hold_cap=None reproduces that behaviour exactly.
    """
    sig = calc_sweep_signal(df)
    atr_series = calc_atr(df, 14)

    trades = []
    in_trade = False
    entry_price = 0.0
    entry_date = ""
    lots = 0
    policy = None
    entry_atr = 0.0
    highest = 0.0
    lowest = 0.0
    hold = 0

    for i in range(1, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]
        bar = Bar(date=date, open=float(row['open']), high=float(row['high']),
                  low=float(row['low']), close=float(row['close']))

        if not in_trade and sig.iloc[i - 1]:
            raw_entry = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')
            atr_val = atr_series.iloc[i - 1]
            if pd.isna(atr_val) or atr_val <= 0:
                atr_val = entry_price * 0.015
            entry_atr = float(atr_val)
            policy = ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5,
                                trail_enable=False, hold_days=hold_cap)
            _sl_pct_eff = (1.0 * entry_atr) / entry_price
            lots = lot_size(50_000_000, entry_price, 0.02, _sl_pct_eff)
            if entry_price * lots * 100 <= 50_000_000:
                in_trade = True
                entry_date = date
                highest = entry_price
                lowest = entry_price
                hold = 0
            else:
                continue

        if in_trade:
            view = PositionView(policy=policy, direction='LONG',
                                entry=entry_price, atr=entry_atr,
                                highest_seen=highest, lowest_seen=lowest,
                                hold_days=hold)
            decision = evaluate_exit(view, bar)
            if decision is not None:
                exit_price = apply_costs(decision.fill_price, 'SELL')
                trades.append({
                    'entry_date': entry_date, 'exit_date': date,
                    'pnl_pct': (exit_price - entry_price) / entry_price * 100,
                    'exit_reason': decision.reason,
                    'hold_sessions': hold,
                })
                in_trade = False
            elif i == len(df) - 1:
                exit_price = apply_costs(bar.close, 'SELL')
                trades.append({
                    'entry_date': entry_date, 'exit_date': date,
                    'pnl_pct': (exit_price - entry_price) / entry_price * 100,
                    'exit_reason': 'EOD', 'hold_sessions': hold,
                })
                in_trade = False
            else:
                highest = max(highest, bar.high)
                lowest = min(lowest, bar.low)
                hold += 1

    return trades


def oos_trades_for_ticker(df: pd.DataFrame, hold_cap) -> list:
    """wf-refresh methodology: per window, strategy on warmup-extended test
    slice, keep trades with entry_date >= test_start."""
    kept = []
    for w in walk_forward_split(df, train_months=12, test_months=3):
        train_df, test_df = w['train'], w['test']
        tail = train_df.tail(WARMUP_TAIL) if len(train_df) >= WARMUP_TAIL else train_df
        extended = pd.concat([tail, test_df], ignore_index=True)
        for t in simulate(extended, hold_cap):
            if t['entry_date'] >= w['test_start']:
                kept.append(t)
    return kept


def pooled(trades: list) -> dict:
    if not trades:
        return {'n': 0, 'exp': 0.0, 'wr': 0.0}
    pnls = np.array([t['pnl_pct'] for t in trades])
    return {
        'n': len(trades),
        'exp': float(pnls.mean()),
        'wr': float((pnls > 0).mean() * 100),
        'exit_mix': pd.Series([t['exit_reason'] for t in trades]).value_counts().to_dict(),
        'median_hold': float(np.median([t['hold_sessions'] for t in trades])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tickers', default=None, help='comma-separated restrict')
    ap.add_argument('--smoke', action='store_true', help='faithfulness gates only')
    args = ap.parse_args()

    ohlcv_map = _load_ohlcv_bulk(final_only=True)
    tickers = sorted(ohlcv_map.keys())
    if args.tickers:
        want = [t.strip() for t in args.tickers.split(',')]
        tickers = [t for t in tickers if t in want]

    # ---- Gate 1: harness baseline == direct run_strategy (trade-for-trade) ----
    smoke = tickers[:SMOKE_TICKERS]
    gate1_ok = True
    for tk in smoke:
        df = ohlcv_map[tk]
        if df is None or len(df) < 60:
            continue
        raw = run_strategy(df, calc_sweep_signal(df), atr_sl_mult=1.0,
                           atr_tp_mult=2.5, min_rr=2.5,
                           strategy_name='Liquidity Sweep')
        mine = simulate(df, hold_cap=None)
        a = [(t.entry_date, t.exit_date, round(t.pnl_pct, 9)) for t in raw['trades']]
        b = [(t['entry_date'], t['exit_date'], round(t['pnl_pct'], 9)) for t in mine]
        if a != b:
            gate1_ok = False
            print(f"[GATE1 FAIL] {tk}: run_strategy n={len(a)} harness n={len(b)}")
    print(f"[GATE1] harness-vs-run_strategy on {len(smoke)} tickers: "
          f"{'PASS' if gate1_ok else 'FAIL'}")
    if not gate1_ok:
        print("ABORT: harness is not faithful to run_strategy; results unusable.")
        return 2
    if args.smoke:
        return 0

    # ---- Main pass: both variants, OOS trades only ----
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    wf_edge_ls = pd.read_sql(
        "SELECT ticker, expectancy_pct, win_rate, n_trades, consistency_pct "
        "FROM wf_edge WHERE strategy='Liquidity Sweep'", conn)
    conn.close()

    rows = []
    base_all, par_all = [], []
    for k, tk in enumerate(tickers, 1):
        df = ohlcv_map[tk]
        if df is None or len(df) < 60:
            continue
        tr_base = oos_trades_for_ticker(df, hold_cap=None)
        tr_par = oos_trades_for_ticker(df, hold_cap=HOLD_PARITY)
        base_all.extend(tr_base)
        par_all.extend(tr_par)
        pb, pp = pooled(tr_base), pooled(tr_par)
        rows.append({'ticker': tk, 'n_base': pb['n'], 'exp_base': round(pb['exp'], 4),
                     'wr_base': round(pb['wr'], 2), 'n_par': pp['n'],
                     'exp_par': round(pp['exp'], 4), 'wr_par': round(pp['wr'], 2),
                     'delta_exp': round(pp['exp'] - pb['exp'], 4)})
        if k % 100 == 0:
            print(f"[LS-PARITY] {k}/{len(tickers)} tickers done", flush=True)

    res = pd.DataFrame(rows)
    os.makedirs('data/reports', exist_ok=True)
    stamp = datetime.now().strftime('%Y-%m-%d')
    csv_path = f'data/reports/ls_hold10_parity_{stamp}.csv'
    res.to_csv(csv_path, index=False)

    # ---- Gate 2: baseline vs persisted wf_edge ----
    merged = res.merge(wf_edge_ls, on='ticker', how='inner')
    n_match = (merged['n_base'] == merged['n_trades']).mean() * 100 if len(merged) else 0
    exp_diff = (merged['exp_base'] - merged['expectancy_pct']).abs()
    gate2 = (n_match == 100.0 and exp_diff.max() <= 0.05) if len(merged) else False

    pb, pp = pooled(base_all), pooled(par_all)

    lines = [
        f"# Liquidity Sweep hold_days=10 parity study — {stamp}",
        "",
        f"Universe: {len(tickers)} tickers (corpus, final bars only)",
        f"Methodology: wf-refresh OOS (12m/3m rolling, warmup {WARMUP_TAIL}, "
        f"entry>=test_start, evidence floor n>={N_MIN_TRADES})",
        "",
        "## Faithfulness gates",
        f"- GATE1 harness==run_strategy ({SMOKE_TICKERS}-ticker trade-for-trade): PASS",
        f"- GATE2 baseline vs persisted wf_edge: n-match {n_match:.1f}% over "
        f"{len(merged)} tickers, |dExp| mean {exp_diff.mean():.4f}pp / max "
        f"{exp_diff.max():.4f}pp -> {'PASS' if gate2 else 'FAIL'}",
        "",
        "## Pooled OOS results (all tickers, then n>=20 floor)",
        "",
        "| variant | n | exp %/trade | win % | median hold | exit mix |",
        "|---|---|---|---|---|---|",
        f"| A baseline (unbounded) | {pb['n']} | {pb['exp']:.4f} | {pb['wr']:.2f} "
        f"| {pb.get('median_hold', 0):.0f} | {pb.get('exit_mix', {})} |",
        f"| B parity (hold_days={HOLD_PARITY}) | {pp['n']} | {pp['exp']:.4f} "
        f"| {pp['wr']:.2f} | {pp.get('median_hold', 0):.0f} | {pp.get('exit_mix', {})} |",
        "",
    ]

    fb = res[res['n_base'] >= N_MIN_TRADES]
    fp = res[res['n_par'] >= N_MIN_TRADES]
    lines += [
        "## Per-ticker cells at the n>=20 evidence floor",
        "",
        f"- baseline: {len(fb)} cells, trade-weighted exp "
        f"{(fb['exp_base']*fb['n_base']).sum()/max(fb['n_base'].sum(),1):.4f}pp, "
        f"positive cells {(fb['exp_base']>0).sum()}/{len(fb)}",
        f"- parity:   {len(fp)} cells, trade-weighted exp "
        f"{(fp['exp_par']*fp['n_par']).sum()/max(fp['n_par'].sum(),1):.4f}pp, "
        f"positive cells {(fp['exp_par']>0).sum()}/{len(fp)}",
        f"- delta exp per ticker: improved {(res['delta_exp']>0).sum()}, "
        f"worsened {(res['delta_exp']<0).sum()}, unchanged "
        f"{(res['delta_exp']==0).sum()}",
        "",
        "Per-ticker detail: " + csv_path,
    ]
    report = "\n".join(lines)
    md_path = f'data/reports/ls_hold10_parity_{stamp}.md'
    with open(md_path, 'w') as f:
        f.write(report + "\n")
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
