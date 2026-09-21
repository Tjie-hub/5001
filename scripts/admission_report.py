#!/usr/bin/env python3
"""scripts/admission_report.py — replay the real admission chain and print why.

Read-only. Answers, for the live database and the live registry:

    for every (ticker, strategy) the regime map can route,
    is it admissible right now, and if not, which gate stopped it?

This is the tool the 2026-09-02 audit had to write by hand to discover that the
scanner could not admit a single strategy for any of 877 tickers, in any regime,
and had produced no BUY signal since 2026-07-01 with no alert anywhere.

Usage:
    python -m scripts.admission_report                 # summary
    python -m scripts.admission_report --verbose       # one line per blocked pair
    python -m scripts.admission_report --ticker BBCA   # single ticker detail
"""
from __future__ import annotations

import argparse
import collections
import sqlite3
import sys

from config import DB_PATH
from engine import admission
from engine.rule_identity import live_rule_id, research_rule_id, rule_parity
from engine.registry_loader import startup_summary


def _bands():
    from scheduler.scanner import _REGIME_STRATEGY_MAP, _COUNTER_TREND_BOOK
    return _REGIME_STRATEGY_MAP, _COUNTER_TREND_BOOK


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="admission_report")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--ticker")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap tickers scanned (0 = all)")
    args = ap.parse_args(argv)

    from scheduler.scanner import _get_disabled_strategies
    regime_map, counter_trend = _bands()
    disabled = _get_disabled_strategies()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=30)
    try:
        if args.ticker:
            tickers = [args.ticker]
        else:
            tickers = [r[0] for r in conn.execute(
                "SELECT DISTINCT ticker FROM wf_edge ORDER BY ticker")]
            if args.limit:
                tickers = tickers[:args.limit]

        print(f"registry: {startup_summary()}")
        print(f"disabled_strategies: {sorted(disabled)}")
        print()
        print("rule parity (audit L-1) — live rule vs the rule research measured:")
        for st in sorted({s for v in regime_map.values() for s in v}):
            ok, why = rule_parity(st)
            print(f"  {st:28s} {'OK ' if ok else 'MISMATCH'}  live={live_rule_id(st)}")
            if not ok:
                print(f"  {'':28s}          researched={research_rule_id(st)}")
        print()

        overall = collections.Counter()
        per_band = {}
        blocked_examples = collections.defaultdict(list)

        for band, cands in regime_map.items():
            counts = collections.Counter()
            admitted_tickers = 0
            for t in tickers:
                any_ok = False
                for st in cands:
                    v = admission.evaluate(conn, t, st, disabled=disabled,
                                           require_registry=False)
                    counts[v.stage] += 1
                    overall[v.stage] += 1
                    if v.admitted:
                        any_ok = True
                    elif len(blocked_examples[(band, st)]) < 1:
                        blocked_examples[(band, st)].append(v.reason)
                if any_ok:
                    admitted_tickers += 1
            per_band[band] = (admitted_tickers, counts)

        for band, (n_ok, counts) in per_band.items():
            print(f"{band}: {n_ok}/{len(tickers)} tickers with >=1 admitted strategy")
            for st in regime_map[band]:
                ex = blocked_examples.get((band, st))
                note = f" — e.g. {ex[0]}" if ex else ""
                mark = "counter-trend" if st in counter_trend else ""
                print(f"    {st:28s} {mark:14s}{note}")
            print()

        print("blocking stage totals across all (band, ticker, strategy) pairs:")
        for stage, n in overall.most_common():
            print(f"  {stage:22s} {n}")

        admitted = overall.get(admission.STAGE_ADMITTED, 0)
        print()
        print(f"RESULT: {admitted} admitted pair(s).")
        if admitted == 0:
            print("The live scanner cannot produce a BUY signal in this state.")
            print("This is reported, not worked around — see the stage totals above.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
