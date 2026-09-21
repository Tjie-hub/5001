#!/usr/bin/env python3
"""scripts/parity_evidence_report.py — does ANY strategy pass OOS + rule parity
+ freshness under the rule production actually executes?

Read-only. This is the deliverable of the 2026-09-02 remediation: a single
command that answers the promotion question honestly, from the rule-indexed
study (`wf_edge_rule`) rather than the bare-rule one (`wf_edge`).

A strategy is reported as PASSING only if, for at least one ticker:
  * evidence exists under the LIVE rule_id (rule parity by construction),
  * pooled OOS sample >= engine.wf_edge.N_MIN_TRADES,
  * pooled OOS expectancy > 0 (net of costs),
  * evidence is fresher than engine.admission.WF_EDGE_MAX_AGE_DAYS,
  * the strategy is not in disabled_strategies,
  * it has a live checker (otherwise admission produces nothing anyway).

Nothing here promotes anything: registry promotion stays a human, receipt-bound
act (R-10). This only reports whether the evidence would support one.

Usage:  python -m scripts.parity_evidence_report [--db PATH] [--json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date

from config import DB_PATH


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="parity_evidence_report")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    from engine import admission
    from engine.wf_edge import N_MIN_TRADES
    from engine.rule_identity import live_rule_id, research_rule_id, rule_parity
    from engine.strategies import STRATEGY_FUNCS, _CHECKER_DISPATCH
    from scheduler.scanner import _get_disabled_strategies, _REGIME_STRATEGY_MAP

    disabled = _get_disabled_strategies()
    routed = {s for v in _REGIME_STRATEGY_MAP.values() for s in v}
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=60)
    today = date.today()
    report = {"generated": today.isoformat(), "strategies": {}, "passing": []}

    try:
        try:
            runs = conn.execute(
                "SELECT strategy, rule_id, tickers_scored, rows_written, "
                "       warmup_bars, gates, last_computed "
                "FROM wf_rule_study ORDER BY strategy").fetchall()
        except sqlite3.Error:
            runs = []
        studied = {(r[0], r[1]) for r in runs}
        report["rule_studies"] = [
            {"strategy": r[0], "rule_id": r[1], "tickers_scored": r[2],
             "rows_written": r[3], "warmup_bars": r[4], "gates": r[5],
             "last_computed": r[6]} for r in runs]

        if not args.json:
            print("rule-indexed studies actually RUN (wf_rule_study):")
            if not runs:
                print("  none — run: python -m research.cli wf-parity")
            for r in runs:
                print(f"  {r[0]:26s} scored={r[2]:<5} qualifying_rows={r[3]:<6} "
                      f"warmup={r[4]} gates={r[5]} @{r[6]}")
            print("  (rows_written=0 means the study RAN and no (ticker, strategy)")
            print("   cell reached the n>=20 evidence floor — not that it was skipped)")
            print()

        for strategy in sorted(STRATEGY_FUNCS):
            live = live_rule_id(strategy)
            parity_ok, _ = rule_parity(strategy)
            bare_is_live = (live == research_rule_id(strategy))
            table = "wf_edge" if bare_is_live else "wf_edge_rule"
            try:
                if bare_is_live:
                    rows = conn.execute(
                        "SELECT ticker, expectancy_pct, n_trades, last_computed "
                        "FROM wf_edge WHERE strategy=?", (strategy,)).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT ticker, expectancy_pct, n_trades, last_computed "
                        "FROM wf_edge_rule WHERE strategy=? AND rule_id=?",
                        (strategy, live)).fetchall()
            except sqlite3.Error:
                rows = []

            fresh = []
            for t, exp, n, lc in rows:
                age = admission._age_days(lc, today)
                if (n or 0) >= N_MIN_TRADES and (exp or 0) > 0 and \
                        age is not None and age <= admission.WF_EDGE_MAX_AGE_DAYS:
                    fresh.append((t, exp, n, age))
            fresh.sort(key=lambda x: -x[1])
            bare_is_live_flag = bare_is_live

            # EVIDENCE criteria — the question actually asked: OOS + rule parity
            # + freshness. Nothing here is a policy judgement.
            evidence_blockers = []
            was_studied = (strategy, live) in studied or bare_is_live
            if not rows and not was_studied:
                evidence_blockers.append(f"no {table} study under the live rule")
            elif not fresh:
                evidence_blockers.append(
                    "no ticker clears n>=20 AND expectancy>0 AND freshness")

            # POLICY / PLUMBING gates — separate, and separately reversible. A
            # strategy can satisfy every evidence criterion and still be
            # correctly excluded (e.g. a dated no-edge decision), so these are
            # reported apart rather than folded into one verdict.
            policy_blockers = []
            if strategy in disabled:
                policy_blockers.append("disabled_strategies")
            if strategy not in _CHECKER_DISPATCH:
                policy_blockers.append("no live checker")
            if strategy not in routed:
                policy_blockers.append("not routed by any regime band")

            entry = {
                "rule_id": live,
                "rule_parity_by_ruleset": parity_ok,
                "evidence_table": table,
                "evidence_rows": len(rows),
                "qualifying_tickers": len(fresh),
                "best": ({"ticker": fresh[0][0], "expectancy_pct": round(fresh[0][1], 3),
                          "n_trades": fresh[0][2], "age_days": fresh[0][3]}
                         if fresh else None),
                "study_run": was_studied,
                "evidence_blockers": evidence_blockers,
                "policy_blockers": policy_blockers,
                "passes_evidence": not evidence_blockers,
                "admissible": not evidence_blockers and not policy_blockers,
            }
            report["strategies"][strategy] = entry
            if entry["passes_evidence"]:
                report["passing"].append(strategy)
            if entry["admissible"]:
                report.setdefault("admissible", []).append(strategy)

        if args.json:
            print(json.dumps(report, indent=2))
            return 0

        print(f"{'strategy':28s} {'evidence study':14s} {'rows':>6} {'qualify':>8}  "
              f"{'OOS+parity+fresh':17s} policy gates")
        print("-" * 112)
        for s, e in sorted(report["strategies"].items()):
            ev = "PASS" if e["passes_evidence"] else "; ".join(e["evidence_blockers"])
            pol = "; ".join(e["policy_blockers"]) or "-"
            print(f"{s:28s} {e['evidence_table']:14s} {e['evidence_rows']:>6} "
                  f"{e['qualifying_tickers']:>8}  {ev:17s} {pol}")
            if e["best"]:
                b = e["best"]
                print(f"{'':28s} best ticker: {b['ticker']} "
                      f"exp={b['expectancy_pct']:+.3f}% n={b['n_trades']} "
                      f"age={b['age_days']}d")
        print()
        passing = report["passing"]
        admissible = report.get("admissible", [])
        if passing:
            print(f"EVIDENCE: {len(passing)} strategy(ies) satisfy OOS + rule parity + "
                  f"freshness: {', '.join(passing)}")
        else:
            print("EVIDENCE: NO strategy satisfies OOS + rule parity + freshness.")
        if admissible:
            print(f"ADMISSIBLE: {', '.join(admissible)}")
            print("This is EVIDENCE ONLY. Registry promotion to APPROVED remains a")
            print("human, receipt-bound act (R-10); nothing here promotes anything.")
        else:
            print("ADMISSIBLE: none. The live scanner will continue to produce no BUY")
            print("signal, which is the correct output given the evidence.")
            if passing:
                print()
                print("NOTE: a strategy above satisfies the evidence criteria but is held")
                print("out by a policy gate. Read its own record before reversing that —")
                print("a per-ticker positive tail inside a negative cross-ticker mean is")
                print("what an uncontrolled multiplicity search looks like, not an edge.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
