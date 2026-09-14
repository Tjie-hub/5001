#!/usr/bin/env python3
"""Freq semantics probe — READ-ONLY, evidence-only (owner Option A, step 2).

Uses ONLY already-captured data:
  - frozen Dataset B store broker_flow_b (limit=150, full observed population)
  - production stockbit_flow (independent vendor daily aggregate)
  - production ticks (per-second trade tape, 2026-04-18+)

No methodology files are touched; results print to stdout and are recorded in
the governance record by the operator.

Tests:
  T1  cross-side balance at full population: SUM(freq) buy vs sell per
      (ticker, session). A per-side count of MATCHED events (fills) must
      balance exactly across sides; orders/instructions need not.
  T2  magnitude vs stockbit_flow daily buy_freq+sell_freq (matched cells).
  T3  magnitude vs ticks tape row counts (rows <= fills; per-second sampled).
  T4  implied size per freq unit: |value|/freq/avg_price in shares.
      Regular-board fills are >= 100 shares; odd-lot prints are not.
"""
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DSB = Path(HERE).parent / "dataset_b"
STORE = DSB / "store" / "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"
PROD = Path(HERE).parent.parent.parent.parent / "data" / "walkforward.db"

SQL_FREQ = """
    SELECT ticker, trade_date, side, SUM(freq), COUNT(*), SUM(abs(value))
    FROM broker_flow_b
    GROUP BY ticker, trade_date, side
"""
SQL_SB = """
    SELECT ticker, trade_date, buy_freq, sell_freq, buy_lot, sell_lot
    FROM stockbit_flow
    WHERE trade_date >= '2025-01-02' AND trade_date <= '2026-08-27'
"""
SQL_TICKS = """
    SELECT ticker, date, COUNT(*)
    FROM ticks
    WHERE date >= '2026-04-18' AND date <= '2026-08-27'
    GROUP BY ticker, date
"""
SQL_CLIPS = """
    SELECT broker_code, side, freq, abs(value), avg_price
    FROM broker_flow_b
    WHERE freq > 0 AND avg_price > 0
"""


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p / 100 * (len(vals) - 1)))] if vals else None


def main():
    store = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    store.execute("PRAGMA query_only = ON;")
    prod = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
    prod.execute("PRAGMA query_only = ON;")

    # ---- T1: cross-side balance at full population ----
    agg = {}
    for tk, d, side, f, n, v in store.execute(SQL_FREQ):
        agg.setdefault((tk, d), {})[side] = (f or 0)
    both = {k: v for k, v in agg.items() if "BUY" in v and "SELL" in v}
    eq = sum(1 for v in both.values() if v["BUY"] == v["SELL"])
    ratios = [v["BUY"] / v["SELL"] for v in both.values() if v["SELL"]]
    near = sum(1 for r in ratios if abs(r - 1) <= 0.01)
    print(f"T1 balance (cells with both sides): {len(both)}")
    print(f"  exact equal: {eq} ({100 * eq / max(len(both), 1):.2f}%)")
    print(f"  within 1%  : {near} ({100 * near / max(len(both), 1):.2f}%)")
    if ratios:
        rs = sorted(ratios)
        print(f"  ratio buy/sell p01={rs[len(rs)//100]:.4f} p50={rs[len(rs)//2]:.4f} "
              f"p99={rs[99*len(rs)//100]:.4f}")

    # ---- T2: magnitude vs stockbit_flow ----
    sb = {}
    for tk, d, bf, sf, bl, sl in prod.execute(SQL_SB):
        if bf is not None and sf is not None and (bf + sf) > 0:
            sb[(tk, d)] = bf + sf
    tot_b, tot_s, rats = 0, 0, []
    for (tk, d), v in agg.items():
        if (tk, d) in sb:
            tot_b += v.get("BUY", 0) + v.get("SELL", 0)
            tot_s += sb[(tk, d)]
            rats.append(sb[(tk, d)] / (v["BUY"] + v["SELL"]))
    print(f"T2 vs stockbit_flow (matched cells): {len(rats)}")
    print(f"  SUM broker freq = {tot_b:,} | stockbit buy+sell freq = {tot_s:,}"
          f" | ratio = {tot_b / tot_s:.4f}" if tot_s else "  no overlap")
    if rats:
        print(f"  per-cell stockbit/broker ratio p50={pct(rats,50):.1f} "
              f"p10={pct(rats,10):.1f} p90={pct(rats,90):.1f}")

    # ---- T3: vs ticks tape (per-second rows <= fills) ----
    tk_rows = {}
    for tk, d, c in prod.execute(SQL_TICKS):
        tk_rows[(tk, d)] = c
    pairs = []
    for (tk, d), v in agg.items():
        s = v.get("BUY", 0) + v.get("SELL", 0)
        if (tk, d) in tk_rows and s > 0:
            pairs.append((s, tk_rows[(tk, d)]))
    print(f"T3 vs ticks tape (matched cells): {len(pairs)}")
    if pairs:
        r = [b / t for b, t in pairs if t]
        print(f"  SUMfreq/ticks-rows p10={pct(r,10):.2f} p50={pct(r,50):.2f} "
              f"p90={pct(r,90):.2f}")
        print(f"  cells where SUMfreq < ticks rows: "
              f"{sum(1 for b, t in pairs if b < t)} / {len(pairs)}")

    # ---- T4: implied size per freq unit ----
    sizes, below100, f1 = [], 0, 0
    n_rows = 0
    for code, side, f, v, ap in store.execute(SQL_CLIPS):
        n_rows += 1
        if f == 1:
            f1 += 1
        s = v / f / ap
        sizes.append(s)
        if s < 100:
            below100 += 1
    sizes.sort()
    print(f"T4 implied shares-per-freq-unit (rows with freq>0, price>0): {n_rows}")
    print(f"  p05={sizes[int(0.05*len(sizes))]:,.0f} p25={sizes[int(0.25*len(sizes))]:,.0f} "
          f"p50={sizes[len(sizes)//2]:,.0f} p75={sizes[int(0.75*len(sizes))]:,.0f} "
          f"p95={sizes[int(0.95*len(sizes))]:,.0f}")
    print(f"  rows below 100 shares/freq-unit: {below100} ({100*below100/n_rows:.2f}%) "
          f"[below regular-board minimum -> freq cannot be plain fills for these]")
    print(f"  freq==1 rows: {f1} ({100*f1/n_rows:.2f}%)")


if __name__ == "__main__":
    main()
