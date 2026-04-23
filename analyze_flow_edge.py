#!/usr/bin/env python3
"""
Flow Edge Analyzer
==================
Validates whether Stockbit flow composite_score / smart_money labels carry
edge on historical paper_trades, and sweeps reject-cutoffs to suggest a
threshold.

Stockbit's tradebook endpoint is intraday-live only (no backfill), so the
dataset grows forward from the date per-minute fetching started. Expect
thin n for 3-6 months; bucket results with n<50 carry WARN labels.

Usage:
    python3 analyze_flow_edge.py                     # bucket tables
    python3 analyze_flow_edge.py --since 2026-04-20  # scope window
    python3 analyze_flow_edge.py --csv out.csv       # dump joined rows
    python3 analyze_flow_edge.py --sweep             # cutoff tuning
"""

import argparse
import csv
import math
import os
import sqlite3
import sys
from statistics import mean, median, pstdev

DB_PATH = os.environ.get(
    "WALKFORWARD_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "walkforward.db"),
)

SCORE_BUCKETS = [
    ("<=-3", lambda s: s <= -3),
    ("-2..-1", lambda s: -2 <= s <= -1),
    ("0", lambda s: s == 0),
    ("1..2", lambda s: 1 <= s <= 2),
    (">=3", lambda s: s >= 3),
]

SMART_MONEY_ORDER = [
    "STRONG_BUY", "ACCUMULATION", "NEUTRAL", "MORNING_TRAP", "STRONG_SELL",
]


def load_rows(since=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    q = """
        SELECT t.ticker, t.entry_date, t.pnl_pct,
               f.composite_score, f.smart_money, f.verdict
        FROM paper_trades t
        LEFT JOIN stockbit_flow f
          ON f.ticker = t.ticker
         AND f.trade_date = t.entry_date
        WHERE t.status = 'CLOSED'
          AND t.pnl_pct IS NOT NULL
          AND f.composite_score IS NOT NULL
    """
    params = []
    if since:
        q += " AND t.entry_date >= ?"
        params.append(since)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def bucket_stats(pnl_list):
    n = len(pnl_list)
    if n == 0:
        return None
    wins = sum(1 for p in pnl_list if p > 0)
    m = mean(pnl_list)
    std = pstdev(pnl_list) if n > 1 else 0.0
    sharpe = (m / std) if std > 0 else float("nan")
    return {
        "n": n,
        "win_rate": wins / n,
        "avg_pnl_pct": m,
        "median_pnl_pct": median(pnl_list),
        "stdev": std,
        "sharpe_ish": sharpe,
    }


def fmt_row(label, s):
    warn = "  WARN n<50" if s["n"] < 50 else ""
    return (
        f"| {label:<14} | {s['n']:>5} | {s['win_rate']*100:>6.1f}% "
        f"| {s['avg_pnl_pct']:>+7.2f}% | {s['median_pnl_pct']:>+7.2f}% "
        f"| {s['stdev']:>6.2f} | {s['sharpe_ish']:>+6.2f} |{warn}"
    )


HEADER = (
    "| bucket         |     n | win-rt | avg pnl  | med pnl  | stdev  | sharpe |\n"
    "|----------------|-------|--------|----------|----------|--------|--------|"
)


def print_score_table(rows):
    print("\n### By composite_score bucket\n")
    print(HEADER)
    for label, pred in SCORE_BUCKETS:
        pnls = [r["pnl_pct"] for r in rows if pred(r["composite_score"])]
        s = bucket_stats(pnls)
        if s:
            print(fmt_row(label, s))
        else:
            print(f"| {label:<14} |     0 |      - |        - |        - |      - |      - |")


def print_smart_money_table(rows):
    print("\n### By smart_money category\n")
    print(HEADER)
    for sm in SMART_MONEY_ORDER:
        pnls = [r["pnl_pct"] for r in rows if r["smart_money"] == sm]
        s = bucket_stats(pnls)
        if s:
            print(fmt_row(sm, s))
        else:
            print(f"| {sm:<14} |     0 |      - |        - |        - |      - |      - |")


def print_crosstab(rows):
    total = len(rows)
    if total < 100:
        print(f"\n(Skipping score x smart_money cross-tab: n={total}, need >=100)")
        return
    print("\n### Cross-tab (score bucket x smart_money) — win-rate / n\n")
    header = "| bucket         |" + "".join(f" {sm:<14} |" for sm in SMART_MONEY_ORDER)
    sep = "|----------------|" + "".join("----------------|" for _ in SMART_MONEY_ORDER)
    print(header)
    print(sep)
    for label, pred in SCORE_BUCKETS:
        cells = [f"| {label:<14} |"]
        for sm in SMART_MONEY_ORDER:
            pnls = [r["pnl_pct"] for r in rows
                    if pred(r["composite_score"]) and r["smart_money"] == sm]
            if pnls:
                wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
                cells.append(f" {wr:>5.1f}% / {len(pnls):<5} |")
            else:
                cells.append(f" {'-':<14} |")
        print("".join(cells))


def sweep_thresholds(rows):
    print("\n### Threshold sweep (BUY-reject cutoff)\n")
    rows_sorted = sorted(rows, key=lambda r: r["entry_date"])
    n = len(rows_sorted)
    split = int(n * 0.7)
    train = rows_sorted[:split]
    holdout = rows_sorted[split:]
    print(f"Split by entry_date: train n={len(train)}, holdout n={len(holdout)}")

    def perf(trades, cutoff):
        kept = [t for t in trades if t["composite_score"] > cutoff]
        rejected = [t for t in trades if t["composite_score"] <= cutoff]
        if not kept:
            return None
        pnls = [t["pnl_pct"] for t in kept]
        m = mean(pnls)
        std = pstdev(pnls) if len(pnls) > 1 else 0.0
        sharpe = (m / std) if std > 0 else float("nan")
        return {
            "n_kept": len(kept),
            "n_rejected": len(rejected),
            "rejection_rate": len(rejected) / len(trades),
            "win_rate": sum(1 for p in pnls if p > 0) / len(pnls),
            "cum_pnl_pct": sum(pnls),
            "avg_pnl_pct": m,
            "sharpe_ish": sharpe,
        }

    print(
        "\n| cutoff | n_kept | rej%  | win-rt | cum pnl  | avg pnl  | sharpe | split  |\n"
        "|--------|--------|-------|--------|----------|----------|--------|--------|"
    )
    train_results = []
    for c in range(-5, 1):
        tr = perf(train, c)
        ho = perf(holdout, c) if holdout else None
        if tr:
            train_results.append((c, tr))
            print(
                f"| {c:>+6} | {tr['n_kept']:>6} | {tr['rejection_rate']*100:>4.1f}% "
                f"| {tr['win_rate']*100:>5.1f}% | {tr['cum_pnl_pct']:>+7.2f}% "
                f"| {tr['avg_pnl_pct']:>+7.2f}% | {tr['sharpe_ish']:>+6.2f} | train  |"
            )
            if ho:
                print(
                    f"| {c:>+6} | {ho['n_kept']:>6} | {ho['rejection_rate']*100:>4.1f}% "
                    f"| {ho['win_rate']*100:>5.1f}% | {ho['cum_pnl_pct']:>+7.2f}% "
                    f"| {ho['avg_pnl_pct']:>+7.2f}% | {ho['sharpe_ish']:>+6.2f} | holdout|"
                )

    max_rejected = max((r["n_rejected"] for _, r in train_results), default=0)
    if max_rejected < 30:
        print(
            f"\nInsufficient history — max rejected at any cutoff = {max_rejected} (<30). "
            "Revisit after more trades accumulate."
        )
        return

    eligible = [(c, r) for c, r in train_results
                if r["rejection_rate"] < 0.40 and not math.isnan(r["sharpe_ish"])]
    if not eligible:
        print("\nNo cutoff satisfies rejection_rate<40% with finite Sharpe.")
        return
    best_c, best = max(eligible, key=lambda x: x[1]["sharpe_ish"])
    print(
        f"\nRecommended cutoff: reject BUY if composite_score <= {best_c}  "
        f"(train Sharpe={best['sharpe_ish']:+.2f}, win-rt={best['win_rate']*100:.1f}%, "
        f"rejection={best['rejection_rate']*100:.1f}%)"
    )
    if holdout:
        ho = perf(holdout, best_c)
        if ho and not math.isnan(ho["sharpe_ish"]) and not math.isnan(best["sharpe_ish"]):
            drift = abs(ho["sharpe_ish"] - best["sharpe_ish"]) / max(abs(best["sharpe_ish"]), 1e-6)
            if drift > 0.30:
                print(
                    f"WARN: OOS Sharpe drifts {drift*100:.0f}% from IS "
                    f"({ho['sharpe_ish']:+.2f} vs {best['sharpe_ish']:+.2f}) — "
                    "threshold may not generalize."
                )
    print("\n(Advisory only — flow_filter.py is not modified automatically.)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD lower bound on entry_date")
    ap.add_argument("--csv", help="dump joined rows to this CSV path")
    ap.add_argument("--sweep", action="store_true", help="run threshold tuning")
    args = ap.parse_args()

    rows = load_rows(since=args.since)
    print(f"Loaded {len(rows)} closed trades with flow data"
          + (f" since {args.since}" if args.since else ""))

    if not rows:
        print("No rows. Either no closed paper_trades, or no matching stockbit_flow "
              "on their entry_date. Nothing to analyze.")
        return

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows)} rows to {args.csv}")

    print_score_table(rows)
    print_smart_money_table(rows)
    print_crosstab(rows)

    if len(rows) < 200:
        print(f"\nNOTE: n={len(rows)} (<200) — bucket results are indicative only. "
              "No threshold recommendation emitted; re-run --sweep once dataset grows.")

    if args.sweep:
        if len(rows) < 50:
            print("\n--sweep: need at least 50 joined rows; skipping.")
        else:
            sweep_thresholds(rows)


if __name__ == "__main__":
    main()
