#!/usr/bin/env python3
"""NF source validation — READ-ONLY, evidence-only (owner candidate, step 3).

Owner-registered candidate:
  NF_t = (aggregate_buy_value_t - aggregate_sell_value_t)
         / (aggregate_buy_value_t + aggregate_sell_value_t)
  Source: Stockbit full-market flow data (stockbit_flow: buy_lot/sell_lot in
  shares + last_price). With one price applied to both sides the value ratio
  reduces to the share ratio:
      NF = (buy_lot - sell_lot) / (buy_lot + sell_lot)
  Zero denominator -> invalid/excluded. Market-flow control only.

Validates: coverage over the frozen PIT grid, construction bounds,
non-degeneracy (must NOT be identically ~0 — that is the entire point vs
broker_flow), and the known stockbit_flow both-sides volume identity
((buy+sell) ~= 2 x ohlcv volume).
"""
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DSB = Path(HERE).parent / "dataset_b"
STORE = DSB / "store" / "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"
PROD = Path(HERE).parent.parent.parent.parent / "data" / "walkforward.db"

SQL_GRID = "SELECT DISTINCT ticker, session_date FROM capture_manifest"
SQL_SB = """
    SELECT ticker, trade_date, buy_lot, sell_lot, net_value, last_price
    FROM stockbit_flow
    WHERE trade_date >= '2025-01-02' AND trade_date <= '2026-08-27'
"""
SQL_VOL = """
    SELECT ticker, date, volume FROM ohlcv
    WHERE date >= '2025-01-02' AND date <= '2026-08-27' AND volume > 0
"""


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p / 100 * (len(vals) - 1)))] if vals else None


def main():
    store = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    store.execute("PRAGMA query_only = ON;")
    prod = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
    prod.execute("PRAGMA query_only = ON;")

    grid = {(t, d) for t, d in store.execute(SQL_GRID)}
    sb = {}
    for tk, d, bl, sl, nv, lp in prod.execute(SQL_SB):
        if bl is None or sl is None:
            continue
        sb[(tk, d)] = (bl, sl, nv, lp)

    covered = grid & set(sb)
    zero_den = sorted(k for k in covered if (sb[k][0] + sb[k][1]) <= 0)
    nfs = []
    for k in covered:
        bl, sl, _, _ = sb[k]
        if bl + sl > 0:
            nfs.append((bl - sl) / (bl + sl))
    absn = sorted(abs(x) for x in nfs)
    tiny = sum(1 for x in absn if x < 0.01)

    # both-sides volume identity: (buy+sell) / (2 x ohlcv volume)
    vol = {(t, d): v for t, d, v in prod.execute(SQL_VOL)}
    vols = []
    for k in covered:
        bl, sl, _, _ = sb[k]
        if k in vol and vol[k] and (bl + sl) > 0:
            vols.append((bl + sl) / (2.0 * vol[k]))

    print(f"coverage: {len(covered)}/{len(grid)} frozen grid cells have "
          f"stockbit_flow rows ({100 * len(covered) / len(grid):.2f}%)")
    print(f"zero-denominator cells (excluded per owner rule): {len(zero_den)} {zero_den[:5]}")
    if nfs:
        print(f"NF distribution: n={len(nfs)}")
        print(f"  min={min(nfs):+.4f} p01={pct(nfs,1):+.4f} p25={pct(nfs,25):+.4f} "
              f"p50={pct(nfs,50):+.4f} p75={pct(nfs,75):+.4f} p99={pct(nfs,99):+.4f} "
              f"max={max(nfs):+.4f}")
        print(f"  |NF|: p50={pct(absn,50):.4f} p90={pct(absn,90):.4f} "
              f"p99={pct(absn,99):.4f}  | cells |NF|<0.01: {tiny} "
              f"({100 * tiny / len(nfs):.2f}%)  [degeneracy check: broker_flow NF "
              f"was identically 0; stockbit NF must not be]")
        print(f"  out of [-1,1]: {sum(1 for x in nfs if abs(x) > 1)}")
    if vols:
        print(f"both-sides identity (buy+sell)/(2*ohlcv volume): "
              f"p10={pct(vols,10):.4f} p50={pct(vols,50):.4f} p90={pct(vols,90):.4f} "
              f"(expected ~1.0 if stockbit_flow counts each side of every trade)")
    uncovered_by_ticker = {}
    for t, d in grid - set(sb):
        uncovered_by_ticker[t] = uncovered_by_ticker.get(t, 0) + 1
    top = sorted(uncovered_by_ticker.items(), key=lambda x: -x[1])[:8]
    print(f"uncovered cells by ticker (top): {top}")


if __name__ == "__main__":
    main()
