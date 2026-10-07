"""G1FIX one-shot runner — Step 2 of ZCODE_BRIEF_EXIT_STUDY_P4_FIX_2026-10-07.md.

Executed ONCE, after the disclosed re-freeze (Amendment 2026-10-07, commit
006ef6a) deleted the P4 same-day top-up fill block from the frozen driver.
NOT one of the three frozen artifacts nor of the four PORTFOLIO_FIX mini-freeze
files — this is an orchestration runner like g1_run.py, introducing no settings
of its own: same panel (pinned to G1's 2026-10-06 horizon as G1-bis does), same
owner mask/indicators/seed as census_g0(), the frozen evaluate() assembly.

Gate (the brief): every NON-P4 arm x population must be BIT-IDENTICAL to G1's
RESULT_20261006T142027Z.json. Any difference -> STOP, no result written. P4
rows are expected to change (that is the point of the fix); everything else
must not.
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
    raise SystemExit("G1FIX is gated: set EXIT_STUDY_G1_APPROVED=1 only after "
                     "owner approval (P4-fix brief, 2026-10-07).")

import exit_study as E                     # noqa: E402  (frozen driver, amended)
from data.db import connect as db_connect  # noqa: E402

TRIO = ("PREDECLARATION.md", "exit_study.py", "test_pit_exit_study.py")
MINIFREEZE = ("PORTFOLIO_FIX.md", "portfolio_v2.py", "test_portfolio_v2.py", "g1bis_run.py")
G1_FINGERPRINT = "f42275e34cb4525d3101fdf3effb14674b7192627db7b6a77a2bac9c5da5e73e"
PANEL_PIN = "2026-10-06"                    # G1's exact panel horizon
POPS = ("E_SN", "E_RND", "E_BRK")
G1_COUNTS = {"E_SN": 3682, "E_RND": 3682, "E_BRK": 5141}
ARMS = tuple(E.EXIT_ARMS) + tuple(E.POS_ARMS)


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


def canon(o) -> str:
    return json.dumps(to_pure(o), sort_keys=True, separators=(",", ":"))


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
    print("freeze checks: trio OK (amended 006ef6a), mini-freeze OK")

    result_path = sorted(glob.glob(str(HERE / "RESULT_2*.json")))[-1]
    if "RESULT_20261006T142027Z" not in result_path:
        raise SystemExit(f"unexpected G1 RESULT file: {result_path}")
    G1 = json.loads(Path(result_path).read_text())

    P = E.load_panel()
    for k in list(P):
        P[k] = P[k].loc[:PANEL_PIN]
    C = P["close"]
    with db_connect(read_only=True) as conn:
        fp = E.dataset_fingerprint(conn)
    print("fingerprint:", fp["sha256"][:16], "| drift vs G1:",
          fp["sha256"] != G1_FINGERPRINT)
    if fp["sha256"] != G1_FINGERPRINT:
        raise SystemExit("STOP: dataset fingerprint drifted from G1's f42275e3…")

    adv20 = (C * P["volume"]).rolling(20, min_periods=20).mean()
    owner = adv20 >= E.ADV20_MIN
    I_by_stock = {}
    for tk in C.columns:
        if C[tk].notna().sum() >= E.PIVOT_WINDOW + 2 * E.PIVOT_HALF + 2:
            I_by_stock[tk] = E.stock_indicators(
                P["open"][tk].values.astype(float), P["high"][tk].values.astype(float),
                P["low"][tk].values.astype(float), C[tk].values.astype(float),
                P["volume"][tk].values.astype(float))
    print("indicators built:", len(I_by_stock))

    result = E.evaluate(P, I_by_stock, {"owner_adv20_10bn": owner})
    counts = {k: result["populations"][k]["n_trades"] for k in POPS}
    print("populations:", counts)
    if counts != G1_COUNTS:
        raise SystemExit(f"STOP: population drift {counts} != G1's {G1_COUNTS}")

    # ── identity gate: every non-P4 arm bit-identical to G1 ──────────────────
    mismatches = []
    for pname in POPS:
        for era in ("E1", "E2"):
            g1_blk, fx_blk = G1["arms"][pname][era], result["arms"][pname][era]
            if g1_blk["n"] != fx_blk["n"]:
                mismatches.append((pname, era, "n", g1_blk["n"], fx_blk["n"]))
            for arm in ARMS:
                if arm == "P4":
                    continue
                for field in ("metrics", "portfolio", "paired_vs_base", "by_year"):
                    a, b = canon(g1_blk[field][arm]), canon(fx_blk[field][arm])
                    if a != b:
                        mismatches.append((pname, era, f"{field}.{arm}"))
    # recommendations and e_sn_vs_e_rnd are per-arm (not per-era tables):
    # recommend() emits only the 10 non-baseline arms — no X0/P0 keys exist
    for pname in ("E_SN", "E_RND"):
        for arm in G1["recommendations"][pname]:
            if arm == "P4":
                continue
            a = canon(G1["recommendations"][pname][arm])
            b = canon(result["recommendations"][pname][arm])
            if a != b:
                mismatches.append((pname, "both", f"recommendations.{arm}"))
    for arm in ARMS:
        if arm == "P4":
            continue
        for era in ("E1", "E2"):
            a = canon(G1["e_sn_vs_e_rnd"][arm][era])
            b = canon(result["e_sn_vs_e_rnd"][arm][era])
            if a != b:
                mismatches.append(("E_SN-vs-E_RND", era, f"{arm}"))
    if canon(G1["p2_tail"]) != canon(result["p2_tail"]):
        mismatches.append(("-", "-", "p2_tail"))
    if G1["e_rnd_unmatched"] != result["e_rnd_unmatched"]:
        mismatches.append(("-", "-", "e_rnd_unmatched",
                           G1["e_rnd_unmatched"], result["e_rnd_unmatched"]))

    print("identity gate: mismatches (non-P4):", len(mismatches))
    for m in mismatches[:20]:
        print("  MISMATCH:", m)
    if mismatches:
        raise SystemExit("STOP: non-P4 bit-identity gate FAILED — no result written")
    print("P4 rows changed (expected):")
    for pname in POPS:
        for era in ("E1", "E2"):
            pt = result["arms"][pname][era]["paired_vs_base"]["P4"]
            m = result["arms"][pname][era]["metrics"]["P4"]
            print(f"  {pname} {era}: t {pt['paired_t_R']:+.4f} "
                  f"meanRdiff {pt['mean_R_diff']:+.4f} expR {m['expectancy_R']:+.4f} "
                  f"(G1 recorded t "
                  f"{G1['arms'][pname][era]['paired_vs_base']['P4']['paired_t_R']:+.4f})")

    result["dataset_fingerprint"] = fp
    result["git_commit"] = E.git_commit()
    result["frozen_artifact_sha256"] = {n: sha256_file(HERE / n) for n in TRIO}
    result["minifreeze_sha256"] = {n: sha256_file(HERE / n) for n in MINIFREEZE}
    result["g1_result_file"] = Path(result_path).name
    result["g1_fingerprint"] = G1_FINGERPRINT
    result["generated_utc"] = datetime.now(timezone.utc).isoformat()
    result["runtime_seconds"] = round(time.time() - t0, 1)
    result["gates"] = {
        "env": "EXIT_STUDY_G1_APPROVED=1 (owner approval of the P4-fix brief, 2026-10-07)",
        "single_run": True,
        "data_access": "read-only (PKLs + mode=ro DB for the fingerprint)",
        "panel_pin": PANEL_PIN,
        "identity_gate": "every non-P4 arm x population bit-identical to "
                         "RESULT_20261006T142027Z.json (canonical-JSON equality)",
    }

    out = HERE / f"RESULT_G1FIX_{stamp}.json"
    out.write_text(json.dumps(to_pure(result), indent=1) + "\n")
    print("WROTE", out.name)
    print("runtime_s:", result["runtime_seconds"])


if __name__ == "__main__":
    main()
