"""
Full-history walk-forward validation of TFB's ATR trailing-stop multiplier.

THE GOAL
--------
The per-window exit tune (scripts/tfb_exit_aware_rerun.py --tune) hinted that
loosening TFB's 2.5xATR trail to ~3.0-3.5xATR lifts real-exit P&L. But that
test only covered the last ~4-12 months. This script runs the SAME walk-forward
engine that produced the shipped +4.63%/trade WF number (12mo train / 3mo test
rolling folds, warmup tail, test-window trade filter) — across many tickers —
at trail mults {2.5 (shipped), 3.0, 3.5} and compares the headline metrics.

It calls the REAL engine.strategy_trend_following_breakout (now parameterized
with atr_mult, default 2.5) and mirrors research.walkforward_multi.run_walk_forward
exactly for the TFB path — so the only thing varying is the exit tightness.

DECISION
--------
If 3.0/3.5 hold or improve consistency + avg P&L/trade + PF vs shipped 2.5 on
full history, the looser exit is validated for shipping. If they degrade, stay
at 2.5 (the per-window tune edge was a recent-regime artifact).

Usage:
    venv/bin/python scripts/tfb_trail_wf.py                  # all eligible tickers
    venv/bin/python scripts/tfb_trail_wf.py --max-tickers 400
    venv/bin/python scripts/tfb_trail_wf.py --mults 2.5 3.0 3.5 4.0
"""
import sys
import os
import argparse
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from config import DB_PATH
from engine.strategies import strategy_trend_following_breakout
from research.walkforward_multi import walk_forward_split, compute_metrics
from engine.indicators import get_warmup, calc_vwap, calc_adx, calc_ma_slope, calc_atr

CAPITAL = 50_000_000
WARMUP_BARS = get_warmup([calc_vwap, calc_adx, calc_ma_slope, calc_atr])   # -> 60


def eligible_tickers(max_tickers):
    """Tickers with enough history for >=1 WF fold (>=~15 months, >=200 bars)."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticker, COUNT(*) n, MIN(date) mn, MAX(date) mx FROM ohlcv "
        "GROUP BY ticker HAVING n >= 200 AND julianday(mx) - julianday(mn) >= 450 "
        "ORDER BY n DESC"
    ).fetchall()
    conn.close()
    if max_tickers and max_tickers > 0:
        rows = rows[:max_tickers]
    return [r[0] for r in rows]


def load_ohlcv(ticker):
    conn = sqlite3.connect(DB_PATH)
    import pandas as pd
    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM ohlcv "
        "WHERE ticker=? ORDER BY date ASC", conn, params=(ticker,))
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    for c in ('open', 'high', 'low', 'close', 'volume'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna(subset=['open', 'high', 'low', 'close', 'volume']).reset_index(drop=True)


def run_mult(df, folds, atr_mult):
    """Run TFB at one trail mult across all folds of one ticker.

    Mirrors run_walk_forward's TFB path: warmup tail + extended_df, filter
    trades to the test window, rebuild equity, compute_metrics. Returns
    (window_metrics, trade_pnls).
    """
    import pandas as pd
    window_metrics, trade_pnls = [], []
    for w in folds:
        train_df, test_df = w['train'], w['test']
        test_start = w['test_start']
        warmup_tail = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
        extended_df = pd.concat([warmup_tail, test_df], ignore_index=True)

        raw = strategy_trend_following_breakout(extended_df, capital=CAPITAL,
                                                atr_mult=atr_mult)
        kept = [t for t in raw['trades'] if t.entry_date >= test_start]
        new_equity, cur = [CAPITAL], CAPITAL
        for t in kept:
            cur += t.pnl_rp
            new_equity.append(cur)
        raw['trades'] = kept
        raw['equity'] = new_equity
        raw['final_capital'] = cur
        raw['initial_capital'] = CAPITAL

        m = compute_metrics(raw)
        window_metrics.append(m)
        trade_pnls.extend(t.pnl_pct for t in kept)
    return window_metrics, trade_pnls


def aggregate(window_metrics, trade_pnls):
    wins = [m for m in window_metrics if m['total_trades'] > 0]
    n_win = sum(1 for m in wins if m['total_return_pct'] > 0)
    tp = np.array(trade_pnls, dtype=float) if trade_pnls else np.array([])
    pos = tp[tp > 0]
    neg = tp[tp < 0]
    gross_w = float(pos.sum())
    gross_l = float(abs(neg.sum()))
    pooled_pf = gross_w / gross_l if gross_l > 0 else float('inf')
    return dict(
        windows=len(window_metrics),
        windows_traded=len(wins),
        consistency=100.0 * n_win / len(wins) if wins else 0.0,
        trades=len(tp),
        avg_pnl_trade=float(tp.mean()) if len(tp) else 0.0,         # the +4.63% analog
        med_pnl_trade=float(np.median(tp)) if len(tp) else 0.0,
        worst_trade=float(tp.min()) if len(tp) else 0.0,
        win_rate=100.0 * (tp > 0).mean() if len(tp) else 0.0,
        avg_return=float(np.mean([m['total_return_pct'] for m in wins])) if wins else 0.0,
        avg_pf=float(np.mean([m['profit_factor'] for m in wins if m['profit_factor'] < 999])) if wins else 0.0,
        pooled_pf=pooled_pf,
        avg_sharpe=float(np.mean([m['sharpe'] for m in wins])) if wins else 0.0,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-tickers', type=int, default=0, help='0 = all eligible')
    ap.add_argument('--mults', type=float, nargs='+', default=[2.5, 3.0, 3.5])
    args = ap.parse_args()

    tickers = eligible_tickers(args.max_tickers)
    mults = sorted(set(args.mults))
    print(f"=== TFB trailing-stop FULL-HISTORY walk-forward ===")
    print(f"tickers={len(tickers)}  mults={mults}  folds=12mo/3mo rolling  warmup={WARMUP_BARS}\n")

    # per_mult[atr_mult] = {'wm': [], 'tp': []}
    per_mult = {m: {'wm': [], 'tp': []} for m in mults}

    t0 = time.time()
    n_done = 0
    for tk in tickers:
        df = load_ohlcv(tk)
        folds = walk_forward_split(df, train_months=12, test_months=3)
        if not folds:
            continue
        for m in mults:
            wm, tp = run_mult(df, folds, m)
            per_mult[m]['wm'].extend(wm)
            per_mult[m]['tp'].extend(tp)
        n_done += 1
        if n_done % 50 == 0:
            print(f"  ...{n_done}/{len(tickers)} tickers, {time.time()-t0:.0f}s", flush=True)

    elapsed = time.time() - t0
    print(f"done: {n_done} tickers in {elapsed:.0f}s\n")

    hdr = (f"{'mult':>5} {'windows':>7} {'traded':>7} {'consist':>8} {'trades':>7} "
           f"{'avgP&L/t':>9} {'win%':>6} {'avgRet%':>8} {'avgPF':>6} {'avgShp':>7}")
    print(hdr)
    print("-" * len(hdr))
    base = None
    rows = {}
    for m in mults:
        a = aggregate(per_mult[m]['wm'], per_mult[m]['tp'])
        rows[m] = a
        if abs(m - 2.5) < 1e-9:
            base = a
        print(f"{m:>5.1f} {a['windows']:>7} {a['windows_traded']:>7} "
              f"{a['consistency']:>7.1f}% {a['trades']:>7} {a['avg_pnl_trade']:>+8.2f}% "
              f"{a['win_rate']:>5.1f} {a['avg_return']:>+7.2f} {a['avg_pf']:>6.2f} "
              f"{a['avg_sharpe']:>+6.2f}")

    # Risk view — pooled PF (global, robust) vs window-avg PF; median + worst trade
    print("\nRisk view (pooled across all trades):")
    rhdr = f"{'mult':>5} {'pooledPF':>9} {'winAvgPF':>9} {'medianP&L':>10} {'worstTrade':>11}"
    print(rhdr)
    for m in mults:
        a = rows[m]
        pp = f"{a['pooled_pf']:.2f}" if a['pooled_pf'] != float('inf') else 'inf'
        print(f"{m:>5.1f} {pp:>9} {a['avg_pf']:>9.2f} {a['med_pnl_trade']:>+9.2f}% "
              f"{a['worst_trade']:>+10.2f}%")

    # Delta vs shipped 2.5
    if base and len(mults) > 1:
        print("\nDelta vs shipped 2.5:")
        print(f"{'mult':>5} {'dP&L/t':>8} {'dConsist':>9} {'dWin%':>7} {'dPF':>6} {'dShp':>7}")
        for m in mults:
            if abs(m - 2.5) < 1e-9:
                continue
            a = rows[m]
            print(f"{m:>5.1f} {a['avg_pnl_trade']-base['avg_pnl_trade']:>+7.2f}% "
                  f"{a['consistency']-base['consistency']:>+8.1f} "
                  f"{a['win_rate']-base['win_rate']:>+6.1f} "
                  f"{a['avg_pf']-base['avg_pf']:>+5.2f} "
                  f"{a['avg_sharpe']-base['avg_sharpe']:>+6.2f}")

    # Decision
    print("\n" + "=" * 72)
    cand = [m for m in mults if abs(m - 2.5) > 1e-9]
    if not cand or not base:
        print("baseline only; add mults to compare.")
        return
    better = [m for m in cand
              if rows[m]['avg_pnl_trade'] > base['avg_pnl_trade']
              and rows[m]['consistency'] >= base['consistency'] - 1.0]
    if better:
        bm = max(better, key=lambda m: rows[m]['avg_pnl_trade'])
        print(f"=> Looser trail VALIDATED on full history: {bm} improves avg P&L/trade "
              f"{base['avg_pnl_trade']:+.2f}% -> {rows[bm]['avg_pnl_trade']:+.2f}% "
              f"with consistency {rows[bm]['consistency']:.1f}% (vs {base['consistency']:.1f}%).")
        print(f"   Ship atr_mult={bm} as the new TFB default (after a live checker sanity pass).")
    else:
        print(f"=> Shipped 2.5 holds on full history. The per-window tune edge was a")
        print(f"   recent-regime artifact — do NOT change the live exit.")
    print("=" * 72)


if __name__ == '__main__':
    main()
