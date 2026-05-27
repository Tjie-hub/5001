"""
meta_filter_check.py — Is the equal-weight edge real, or a no-trade artifact?

Reuses the cached backtest dataset + the leakage-free meta loop from meta_validate,
then re-cuts the comparison to remove "inaction" (strategies/windows with no trades):

  A) Equal-weight over TRADED strategies only (vs over all 10).
  B) Selection arms (ML / score) restricted to windows where the PICKED strategy
     actually traded — apples-to-apples selection among active choices.

A strategy-window is "no trade" when compute_metrics returned all-zeros
(return == win_rate == max_dd == profit_factor == 0). Verified ~0.1% ambiguous.

Read-only. Run after meta_validate.py has produced out/meta_dataset_backtest.json:
  venv/bin/python meta_filter_check.py
"""
import json
from pathlib import Path

import numpy as np

from meta_validate import walk_forward_meta

CACHE = Path("out/meta_dataset_backtest.json")
OUT = Path("out/meta_filter_report.md")


def traded(m: dict) -> bool:
    return not (m["return"] == 0.0 and m["win_rate"] == 0.0
                and m["max_dd"] == 0.0 and m["profit_factor"] == 0.0)


def main():
    examples = json.loads(CACHE.read_text())
    index = {(e["ticker"], e["test_start"]): e for e in examples}

    res = walk_forward_meta(examples)
    ev = res["evaluated"]

    rows = []
    for r in ev:
        ex = index[(r["ticker"], r["test_start"])]
        metrics = ex["metrics"]
        traded_rets = [m["return"] for m in metrics.values() if traded(m)]
        rows.append({
            **r,
            "eqw_all": float(np.mean([m["return"] for m in metrics.values()])),
            "eqw_traded": float(np.mean(traded_rets)) if traded_rets else None,
            "n_traded": len(traded_rets),
            "ml_traded": traded(metrics[r["ml_strat"]]),
            "score_traded": traded(metrics[r["score_strat"]]),
        })

    def avg(rs, key):
        vals = [x[key] for x in rs if x[key] is not None]
        return float(np.mean(vals)) if vals else float("nan")

    n = len(rows)
    L = ["# Filtered Check — removing no-trade inaction\n"]
    L.append(f"_Evaluated windows: {n}_\n")

    # How much of each arm is just "picked a strategy that didn't trade"?
    ml_idle = sum(1 for x in rows if not x["ml_traded"])
    sc_idle = sum(1 for x in rows if not x["score_traded"])
    L.append("## How often each arm 'picks' inaction (0.00% no-trade strategy)\n")
    L.append(f"- ML-pick chose a no-trade strategy   : **{ml_idle}/{n}** ({ml_idle/n*100:.0f}%)")
    L.append(f"- Score-pick chose a no-trade strategy : **{sc_idle}/{n}** ({sc_idle/n*100:.0f}%)\n")

    # A) Equal-weight: all-10 vs traded-only
    L.append("## A) Equal-weight, all-10 vs traded-only\n")
    L.append("| Arm | Avg return %/window |")
    L.append("|---|---:|")
    L.append(f"| Equal-weight (all 10, incl. no-trade 0.00s) | {avg(rows,'eqw_all'):.2f} |")
    L.append(f"| Equal-weight (traded strategies only) | {avg(rows,'eqw_traded'):.2f} |")
    L.append(f"| Score-pick (current system) | {avg(rows,'score_ret'):.2f} |")
    L.append(f"| ML-pick | {avg(rows,'ml_ret'):.2f} |")
    L.append(f"| Oracle | {avg(rows,'oracle_ret'):.2f} |\n")

    # B) Selection only where the picked strategy actually traded
    both_active = [x for x in rows if x["ml_traded"] and x["score_traded"]]
    L.append(f"## B) Windows where BOTH arms picked a strategy that traded (n={len(both_active)})\n")
    if both_active:
        ml_b = avg(both_active, "ml_ret")
        sc_b = avg(both_active, "score_ret")
        eqt_b = avg(both_active, "eqw_traded")
        orc_b = avg(both_active, "oracle_ret")
        ml_wins = sum(1 for x in both_active if x["ml_ret"] > x["score_ret"])
        ties = sum(1 for x in both_active if x["ml_ret"] == x["score_ret"])
        L.append("| Arm | Avg return %/window | vs Score |")
        L.append("|---|---:|---:|")
        L.append(f"| Oracle | {orc_b:.2f} | {orc_b-sc_b:+.2f} |")
        L.append(f"| Equal-weight (traded) | {eqt_b:.2f} | {eqt_b-sc_b:+.2f} |")
        L.append(f"| ML-pick | {ml_b:.2f} | {ml_b-sc_b:+.2f} |")
        L.append(f"| Score-pick | {sc_b:.2f} | — |")
        L.append(f"\n- Head-to-head: ML better {ml_wins}, tie {ties}, score better "
                 f"{len(both_active)-ml_wins-ties}\n")

    # Verdict
    eqt = avg(rows, "eqw_traded")
    sc = avg(rows, "score_ret")
    L.append("## Read\n")
    if eqt > sc + 0.15:
        L.append(f"- Equal-weight (traded-only) **still beats** score-pick "
                 f"({eqt:.2f} vs {sc:.2f}). The diversification edge is **real**, not "
                 f"just averaging in no-trade zeros — selecting one strategy is leaving money on the table.")
    elif eqt < sc - 0.15:
        L.append(f"- Once no-trade zeros are removed, equal-weight ({eqt:.2f}) **loses** to "
                 f"score-pick ({sc:.2f}). The earlier equal-weight edge was an **inaction artifact** — "
                 f"your selection is fine; it was being unfairly diluted by 0.00% entries.")
    else:
        L.append(f"- Equal-weight (traded-only, {eqt:.2f}) and score-pick ({sc:.2f}) are "
                 f"effectively tied. Selection adds little but isn't actively harmful once "
                 f"inaction is excluded.")
    L.append(f"- {ml_idle/n*100:.0f}% of ML picks and {sc_idle/n*100:.0f}% of score picks were "
             f"no-trade strategies — much of both arms' returns is literally 'sat out at 0.00%'.")

    report = "\n".join(L) + "\n"
    OUT.write_text(report)
    print(f"Wrote {OUT}\n")
    print(report)


if __name__ == "__main__":
    main()
