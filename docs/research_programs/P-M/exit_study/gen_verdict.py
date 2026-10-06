"""Render VERDICT.md tables from the G1 RESULT json (deterministic; no hand
transcription of numbers). Executed once, 2026-10-06, after the G1 run.
Narrative sections are authored in the file afterwards — this script only
emits the numeric tables and frozen-rule outputs.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ["X0", "X1", "X2", "X3", "X4", "X5", "X6", "P0", "P1", "P2", "P3", "P4"]
POPS = ["E_SN", "E_RND", "E_BRK"]
ERA_LABEL = {"E1": "E1 2001-01..2021-09 (discovery)", "E2": "E2 2021-10..2026-09 (confirmation)"}


def pct(x, digits=2):
    return "—" if x is None else f"{100 * x:.{digits}f}%"


def num(x, digits=2):
    return "—" if x is None else f"{x:.{digits}f}"


def t_num(x):
    if x is None:
        return "n/a*"
    return f"{x:+.2f}" if abs(x) < 1e6 else ("+inf" if x > 0 else "-inf")


def main() -> None:
    result_path = sorted(glob.glob(str(HERE / "RESULT_*.json")))[-1]
    R = json.loads(Path(result_path).read_text())
    L = []
    w = L.append

    w("| metric table | n | mean net% | median net% | expectancy R | win rate | avg win% | avg loss% | mean hold |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for pop in POPS:
        for era in ("E1", "E2"):
            for arm in ARMS:
                m = R["arms"][pop][era]["metrics"][arm]
                w(f"| {pop} {era} {arm} | {m['n']} | {pct(m['mean_net_pct'])} | "
                  f"{pct(m['median_net_pct'])} | {num(m['expectancy_R'])} | "
                  f"{pct(m['win_rate'], 1)} | {pct(m['avg_win'])} | {pct(m['avg_loss'])} | "
                  f"{num(m['mean_hold'], 1)} |")
    w("")
    w("Portfolio (equal-risk, 1% risk, max 10 concurrent):")
    w("| population | era | arm | CAGR | max DD | worst 12m | n_taken/n_signals | final equity |")
    w("|---|---|---|---:|---:|---:|---:|---:|")
    for pop in POPS:
        for era in ("E1", "E2"):
            for arm in ARMS:
                p = R["arms"][pop][era]["portfolio"][arm]
                w(f"| {pop} | {era} | {arm} | {pct(p['cagr'])} | {pct(p['max_dd'], 1)} | "
                  f"{pct(p['worst_12m'], 1)} | {p['n_taken']}/{p['n_signals']} | "
                  f"{num(p['final_equity'], 2)} |")
    w("")
    w("Paired vs baseline (paired difference t on matched trades, H1: arm > baseline):")
    w("| population | era | arm | paired t (R) | mean R diff | n matched |")
    w("|---|---|---|---:|---:|---:|")
    for pop in POPS:
        for era in ("E1", "E2"):
            for arm in ARMS:
                pv = R["arms"][pop][era]["paired_vs_base"].get(arm)
                if pv is None:
                    continue
                w(f"| {pop} | {era} | {arm} | {t_num(pv['paired_t_R'])} | "
                  f"{num(pv['mean_R_diff'])} | {pv['n_matched']} |")
    w("")
    w("Frozen recommendation rule (both eras: expectancy higher AND paired t >= 2.0 AND "
      "max DD not worse by >20% relative):")
    for pop in ("E_SN", "E_RND"):
        w(f"| {pop} arm | verdict | E1 t | E1 expHigher | E1 dd_ok | E2 t | E2 expHigher | E2 dd_ok |")
        w("|---|---|---:|---|---|---:|---|---|")
        for arm, rec in R["recommendations"][pop].items():
            e = rec["per_era"]
            w(f"| {arm} | **{rec['verdict']}** | {t_num(e['E1']['t'])} | "
              f"{e['E1']['expHigher']} | {e['E1']['dd_ok']} | {t_num(e['E2']['t'])} | "
              f"{e['E2']['expHigher']} | {e['E2']['dd_ok']} |")
    w("")
    w("E-SN vs E-RND per arm (does the sniper entry itself add anything; paired on matched controls):")
    w("| arm | era | paired t (R) | n matched |")
    w("|---|---|---:|---:|")
    for arm in ARMS:
        for era in ("E1", "E2"):
            d = R["e_sn_vs_e_rnd"][arm][era]
            w(f"| {arm} | {era} | {t_num(d['paired_t_R'])} | {d['n_matched']} |")
    w("")
    w("P2 (averaging down) worst-5% tail question vs P0:")
    w("| population | arm | worst-5% mean net% | win rate | expectancy R |")
    w("|---|---|---:|---:|---:|")
    for pop in ("E_SN", "E_RND"):
        for label in ("P0", "P2"):
            d = R["p2_tail"][pop][label]
            w(f"| {pop} | {label} | {pct(d['worst5pct_mean'])} | {pct(d['win_rate'], 1)} | "
              f"{num(d['expectancy_R'])} |")
    w("")
    w("Year-by-year mean net% (E_SN, owner screen; full per-arm/per-era tables in the RESULT):")
    years = sorted({y for arm in ARMS for y in R["arms"]["E_SN"]["E1"]["by_year"][arm]}
                   | {y for arm in ARMS for y in R["arms"]["E_SN"]["E2"]["by_year"][arm]})
    w("| year | " + " | ".join(ARMS) + " |")
    w("|---|" + "---:|" * len(ARMS))
    for y in years:
        row = []
        for arm in ARMS:
            v = None
            for era in ("E1", "E2"):
                d = R["arms"]["E_SN"][era]["by_year"][arm].get(y)
                if d is not None:
                    v = d["mean_net_pct"]
            row.append(pct(v, 1))
        w(f"| {y} | " + " | ".join(row) + " |")
    w("")
    w("\\* paired t `n/a` = fewer than 3 matched pairs, or zero-variance differences "
      "(the frozen paired_t returns ±inf there; serialized as null).")
    (HERE / "_verdict_tables.md").write_text("\n".join(L) + "\n")
    print("tables written to _verdict_tables.md from", Path(result_path).name)


if __name__ == "__main__":
    main()
