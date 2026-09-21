#!/usr/bin/env python3
"""scripts/scanner_replay.py — point-in-time replay of the live signal path.

Read-only. For each historical session date D, rebuild each ticker's frame using
ONLY bars with date <= D, then run the production functions in order:

    adaptive_strategy_selector  (regime -> registry -> rule parity -> OOS
                                 evidence -> staleness -> disabled)
    check_current_entry_signal  (the live checker + weekly MTF gate)
    entry_convention.executable_entry  (the fill guard)

and report what the scanner WOULD have produced. Nothing is written; no future
bar is ever visible to a decision.

This is the harness the 2026-09-02 audit lacked: it answers "would this have
fired, on what evidence, and at what obtainable price?" without touching
production state.

Usage:
    python -m scripts.scanner_replay --days 30
    python -m scripts.scanner_replay --days 5 --tickers BBCA,BBRI --verbose
"""
from __future__ import annotations

import argparse
import collections
import sqlite3
import sys

import pandas as pd

from config import DB_PATH

_COLS = ["date", "open", "high", "low", "close", "volume"]


def _sessions(conn, n):
    rows = conn.execute(
        "SELECT DISTINCT date FROM ohlcv WHERE ticker='IHSG' ORDER BY date DESC "
        "LIMIT ?", (n,)).fetchall()
    return [r[0] for r in reversed(rows)]


def _frames(conn, tickers, upto):
    """Bars strictly up to and including `upto` — the information boundary."""
    out = {}
    for t in tickers:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? AND date<=? ORDER BY date", (t, upto)).fetchall()
        if len(rows) >= 60:
            out[t] = pd.DataFrame(rows, columns=_COLS)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scanner_replay")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--tickers", default="")
    ap.add_argument("--limit-tickers", type=int, default=120)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    from scheduler.scanner import adaptive_strategy_selector, _get_disabled_strategies
    from engine.strategies import check_current_entry_signal
    from engine import admission, entry_convention as ec
    import scheduler.scanner as scanner_mod

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=60)
    # Point the production selector at this read-only handle. It only SELECTs.
    scanner_mod.DB_PATH = f"file:{args.db}?mode=ro"

    try:
        sessions = _sessions(conn, args.days)
        if args.tickers:
            tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        else:
            tickers = [r[0] for r in conn.execute(
                "SELECT DISTINCT ticker FROM wf_edge ORDER BY ticker")][:args.limit_tickers]

        print(f"replaying {len(sessions)} session(s) x {len(tickers)} ticker(s)")
        print(f"window: {sessions[0]} .. {sessions[-1]}")
        print()

        stages = collections.Counter()
        signals = []
        fills = collections.Counter()

        for d in sessions:
            frames = _frames(conn, tickers, d)
            for t, df in frames.items():
                record = []
                try:
                    strats = adaptive_strategy_selector(t, df, record=record)
                except Exception as e:
                    print(f"  [{d} {t}] selector error: {e}")
                    continue
                for v in record:
                    stages[v.stage] += 1
                for st in strats:
                    try:
                        sig = check_current_entry_signal(t, st, df=df)
                    except Exception:
                        continue
                    if not sig.get("has_signal"):
                        continue
                    res = ec.executable_entry(sig.get("details") or {}, df)
                    fills[res.action] += 1
                    adm = next((v for v in record
                                if v.strategy == st and v.admitted), None)
                    signals.append({
                        "date": d, "ticker": t, "strategy": st,
                        "rule_id": adm.rule_id if adm else None,
                        "expectancy": adm.wf_expectancy_pct if adm else None,
                        "n_trades": adm.wf_n_trades if adm else None,
                        "last_computed": adm.wf_last_computed if adm else None,
                        "registry": adm.registry_state if adm else None,
                        "action": res.action,
                        "decision_price": res.decision.price,
                        "basis": res.decision.basis,
                        "entry_rule": res.entry_rule,
                    })
            if args.verbose:
                print(f"  {d}: {len(frames)} frames, {len(signals)} cumulative signal(s)")

        print("admission stage totals (point-in-time):")
        for k, n in stages.most_common():
            print(f"  {k:22s} {n}")
        print()
        print(f"signals produced: {len(signals)}")
        print(f"fill resolutions: {dict(fills) or '{}'}")
        print()

        if not signals:
            print("RESULT: zero BUY signals over the replay window.")
            print("Consistent with zero admissible strategies — reported, not")
            print("worked around.")
            return 0

        bad = [s for s in signals
               if not s["strategy"] or not s["rule_id"]
               or (s["registry"] != "APPROVED" and (s["expectancy"] is None
                                                    or s["expectancy"] <= 0))]
        for s in signals[:40]:
            print(f"  {s['date']} {s['ticker']:6s} {s['strategy']:26s} "
                  f"{s['registry']:12s} exp={s['expectancy']} n={s['n_trades']} "
                  f"{s['action']} @{s['decision_price']} ({s['basis']})")
        print()
        retro = [s for s in signals if s["action"] == ec.ACTION_FILL]
        print(f"traceability: {len(signals) - len(bad)}/{len(signals)} signals carry "
              f"a strategy, a rule_id and OOS evidence (or APPROVED registry admission)")
        print(f"retrospective fills: {len(retro)} (must be 0)")
        return 0 if not bad and not retro else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
