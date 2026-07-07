"""Walk-forward validation for the Panic Rebound strategy (Phase 1.2).

Replicates run_walk_forward's window/warmup mechanics for a single strategy
across the full universe, then reports per-quarter traded-window stats —
the same view the 2026-06-13 audit used to rank the existing strategies.

Acceptance: avg return per traded window > 0 overall AND > +1% in the
2026-Q1/Q2 buckets, with >= 100 traded windows.

Usage: venv/bin/python scripts/wf_panic_rebound.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics as st
from collections import defaultdict

import pandas as pd

from engine.strategies import strategy_panic_rebound
from research.walkforward_multi import walk_forward_split
from scheduler.utils import _load_ohlcv_bulk

WARMUP_BARS = 60


def main():
    ohlcv_map = _load_ohlcv_bulk()
    buckets = defaultdict(list)   # quarter -> [window return %]
    n_tickers = 0
    n_windows = 0

    for ticker, df in ohlcv_map.items():
        if ticker == 'IHSG' or df is None or len(df) < 60:
            continue
        try:
            windows = walk_forward_split(df, train_months=12, test_months=3)
        except Exception:
            continue
        if not windows:
            continue
        n_tickers += 1
        for w in windows:
            n_windows += 1
            train_df, test_df = w['train'], w['test']
            warmup = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
            extended = pd.concat([warmup, test_df], ignore_index=True)
            try:
                raw = strategy_panic_rebound(extended, capital=50_000_000)
            except Exception as e:
                print(f"[{ticker}] window error: {e}")
                continue
            kept = [t for t in raw['trades'] if t.entry_date >= w['test_start']]
            if not kept:
                continue
            ret = sum(t.pnl_rp for t in kept) / 50_000_000 * 100
            q = w['test_start'][:7]
            buckets[q].append(ret)

    print(f"\ntickers={n_tickers} windows={n_windows}")
    all_rets = [r for v in buckets.values() for r in v]
    if not all_rets:
        print("NO TRADED WINDOWS — strategy never fired")
        return
    print(f"\n{'bucket':8} {'n':>5} {'avg':>7} {'med':>7} {'pos%':>6} {'min':>7} {'max':>7}")
    for q in sorted(buckets):
        rets = buckets[q]
        pos = 100 * sum(1 for r in rets if r > 0) / len(rets)
        print(f"{q:8} {len(rets):5d} {st.mean(rets):7.2f} {st.median(rets):7.2f} "
              f"{pos:6.1f} {min(rets):7.2f} {max(rets):7.2f}")
    pos = 100 * sum(1 for r in all_rets if r > 0) / len(all_rets)
    print(f"{'TOTAL':8} {len(all_rets):5d} {st.mean(all_rets):7.2f} "
          f"{st.median(all_rets):7.2f} {pos:6.1f}")

    ok_n = len(all_rets) >= 100
    ok_avg = st.mean(all_rets) > 0
    rets_2026 = [r for q, v in buckets.items() if q >= '2026-01' for r in v]
    ok_2026 = bool(rets_2026) and st.mean(rets_2026) > 1.0
    print(f"\nacceptance: n>=100 {'PASS' if ok_n else 'FAIL'} | "
          f"avg>0 {'PASS' if ok_avg else 'FAIL'} | "
          f"2026 avg>+1% {'PASS' if ok_2026 else 'FAIL'}"
          f" (2026 n={len(rets_2026)}, avg={st.mean(rets_2026):.2f}%)" if rets_2026 else "")


if __name__ == '__main__':
    main()
