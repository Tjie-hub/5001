"""G1-bis one-shot runner — the portfolio-layer re-run (2026-10-07).

Executed ONCE, after the owner approved G1-bis (brief
ZCODE_BRIEF_EXIT_STUDY_G1BIS_PORTFOLIO_2026-10-07.md, fix/telegram-curation @ 6dbcd3b).
Not one of the three frozen artifacts nor of the four PORTFOLIO_FIX mini-freeze
files' logic — this file IS one of the mini-freeze files. It re-derives G1's
deterministic trade set (same seed, same panel pinned to dates <= 2026-10-06),
proves leg-vs-frozen parity (net_pct within 1e-9) for EVERY trade x arm, then
runs the fixed portfolio engine and re-applies the frozen recommendation rule
with G1's unchanged t-statistics and expectancies.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if os.environ.get("EXIT_STUDY_G1_APPROVED") != "1":
    raise SystemExit("G1-bis is gated: set EXIT_STUDY_G1_APPROVED=1 only after "
                     "owner approval (G1-bis, 2026-10-07).")

import exit_study as E                     # noqa: E402  (frozen driver)
import portfolio_v2 as PV                  # noqa: E402  (mini-frozen portfolio layer)
from data.db import connect as db_connect  # noqa: E402

TRIO = ("PREDECLARATION.md", "exit_study.py", "test_pit_exit_study.py")
MINIFREEZE = ("PORTFOLIO_FIX.md", "portfolio_v2.py", "test_portfolio_v2.py", "g1bis_run.py")
G1_FINGERPRINT = "f42275e34cb4525d3101fdf3effb14674b7192627db7b6a77a2bac9c5da5e73e"
PANEL_PIN = "2026-10-06"                    # G1's exact panel horizon
ARMS = tuple(E.EXIT_ARMS) + tuple(E.POS_ARMS)
POPS = ("E_SN", "E_RND", "E_BRK")
G1_COUNTS = {"E_SN": 3682, "E_RND": 3682, "E_BRK": 5141}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def to_pure(o):
    if isinstance(o, dict):
        return {str(k): to_pure(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_pure(v) for v in o]
    if isinstance(o, bool) or isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, int) or isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if np.isfinite(v) else None
    if o is None or isinstance(o, str):
        return o
    return str(o)


def main() -> None:
    t0 = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    sidecar = {}
    for line in (HERE / "PREDECLARATION.sha256").read_text().strip().splitlines():
        h, n = line.split()
        sidecar[n] = h
    for n in TRIO:
        if sidecar.get(n) != sha256_file(HERE / n):
            raise SystemExit(f"frozen-trio check FAILED for {n}")
    mini = {}
    for line in (HERE / "PORTFOLIO_FIX.sha256").read_text().strip().splitlines():
        h, n = line.split()
        mini[n] = h
    for n in MINIFREEZE:
        if mini.get(n) != sha256_file(HERE / n):
            raise SystemExit(f"mini-freeze check FAILED for {n}")
    print("freeze checks: trio OK, mini-freeze OK")

    result_path = sorted(glob.glob(str(HERE / "RESULT_2*.json")))[-1]
    if "RESULT_20261006T142027Z" not in result_path:
        raise SystemExit(f"unexpected G1 RESULT file: {result_path}")
    G1 = json.loads(Path(result_path).read_text())

    # panel pinned to G1's horizon
    P = E.load_panel()
    for k in list(P):
        P[k] = P[k].loc[:PANEL_PIN]
    C = P["close"]
    with db_connect(read_only=True) as conn:
        fp = E.dataset_fingerprint(conn)
    drift = fp["sha256"] != G1_FINGERPRINT
    print("fingerprint:", fp["sha256"][:16], "| drift vs G1:", drift)

    adv20 = (C * P["volume"]).rolling(20, min_periods=20).mean()
    owner = adv20 >= E.ADV20_MIN
    I_by_stock = {}
    for tk in C.columns:
        if C[tk].notna().sum() >= E.PIVOT_WINDOW + 2 * E.PIVOT_HALF + 2:
            I_by_stock[tk] = E.stock_indicators(
                P["open"][tk].values.astype(float), P["high"][tk].values.astype(float),
                P["low"][tk].values.astype(float), C[tk].values.astype(float),
                P["volume"][tk].values.astype(float))
    pop = E.entry_population(P, I_by_stock, owner)
    rng = np.random.default_rng(E.SEED)
    controls, unmatched = E.random_controls(P, I_by_stock, pop["sniper"], rng)
    pops = {"E_SN": pop["sniper"], "E_RND": controls, "E_BRK": pop["brk"]}
    for name in POPS:
        if len(pops[name]) != G1_COUNTS[name]:
            raise SystemExit(f"STOP: population {name} = {len(pops[name])} != G1's "
                             f"{G1_COUNTS[name]} (data drift?)")
    print("populations match G1 exactly:", {k: len(v) for k, v in pops.items()})

    closes = {tk: C[tk].values.astype(float) for tk in C.columns}
    dates_index = C.index
    parity = {"checked": 0, "max_abs_diff": 0.0, "exit_mismatches": 0}
    out = {"populations": {k: {"n_trades": len(v)} for k, v in pops.items()}}
    for pname in POPS:
        for era in ("E1", "E2"):
            trades_e = [t for t in pops[pname] if E.month_to_era(t["month"]) == era]
            for arm in ARMS:
                legs_by_key = {}
                for tr in trades_e:
                    key = (tr["ticker"], tr["s"])
                    lg = PV.simulate_legs(tr, arm, P, I_by_stock)
                    oc = E.simulate_trade(tr, arm, P, I_by_stock)
                    legs_by_key[key] = lg["legs"]
                    parity["checked"] += 1
                    parity["max_abs_diff"] = max(parity["max_abs_diff"],
                                                 abs(lg["net_pct"] - oc["net_pct"]))
                    if lg["exit_idx"] != oc["exit_idx"] or lg["exit_reason"] != oc["reason"]:
                        parity["exit_mismatches"] += 1
                port = PV.run_portfolio_v2(trades_e, legs_by_key, closes, dates_index, era)
                out.setdefault("portfolio", {}).setdefault(pname, {}).setdefault(era, {})[arm] = port
    print("parity:", parity)
    if parity["max_abs_diff"] > 1e-9 or parity["exit_mismatches"] > 0:
        raise SystemExit(f"STOP: parity gate FAILED {parity} — no verdict written")

    # frozen recommendation rule: G1's t / expectancy + G1-bis max DD
    recs = {}
    for pname in ("E_SN", "E_RND"):
        blocks = {}
        for arm in ARMS:
            blocks[arm] = {}
            for era in ("E1", "E2"):
                blocks[arm][era] = {
                    "expectancy_R": G1["arms"][pname][era]["metrics"][arm]["expectancy_R"],
                    "paired_t_vs_base": (G1["arms"][pname][era]["paired_vs_base"][arm]
                                         or {}).get("paired_t_R"),
                    "port_max_dd": out["portfolio"][pname][era][arm]["max_dd"],
                }
        recs[pname] = E.recommend(blocks)
    out["recommendations"] = recs

    out["p4_vs_p0_drawdown"] = {
        pname: {era: {"p0_max_dd": out["portfolio"][pname][era]["P0"]["max_dd"],
                      "p4_max_dd": out["portfolio"][pname][era]["P4"]["max_dd"],
                      "deepens": out["portfolio"][pname][era]["P4"]["max_dd"]
                      < out["portfolio"][pname][era]["P0"]["max_dd"]}
                for era in ("E1", "E2")}
        for pname in ("E_SN", "E_RND")}

    out.update({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - t0, 1),
        "git_commit": E.git_commit(),
        "gates": {"env": "EXIT_STUDY_G1_APPROVED=1 (owner approval of G1-bis, 2026-10-07)",
                  "single_run": True, "data_access": "read-only",
                  "panel_pin": PANEL_PIN},
        "dataset_fingerprint": fp,
        "g1_fingerprint": G1_FINGERPRINT,
        "fingerprint_drift_vs_g1": drift,
        "parity": parity,
        "g1_result_file": Path(result_path).name,
        "frozen_artifact_sha256": {n: sha256_file(HERE / n) for n in TRIO},
        "minifreeze_sha256": {n: sha256_file(HERE / n) for n in MINIFREEZE},
        "e_rnd_unmatched": unmatched,
    })
    outfile = HERE / f"RESULT_G1BIS_{stamp}.json"
    outfile.write_text(json.dumps(to_pure(out), indent=1) + "\n")
    print("WROTE", outfile.name)
    print("P4 deepens DD:", to_pure(out["p4_vs_p0_drawdown"]))
    print("recs E_SN:", {a: r["verdict"] for a, r in recs["E_SN"].items()})
    print("runtime_s:", out["runtime_seconds"])


if __name__ == "__main__":
    main()
