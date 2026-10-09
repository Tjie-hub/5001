"""G1 one-shot runner for the retail-ownership study -- WRITTEN AT G0, NOT RUN.

Executes only with OC_G1_APPROVED=1, after owner approval of the G0. One run of both arms (A1 level
`s`, A2 flow `ds`) through outcomes.run_arm; pass conditions are COMPUTED booleans, frozen here:

  per arm, ALL must hold:
    1. strength:     net_mean > 0 and Newey-West t (3 lags) >= BAR_FROZEN (N = 611, 3.2987)
    2. both halves:  mean net spread > 0 for formations <= 2017-12-31 and for later formations
    3. incremental:  Fama-MacBeth signal coefficient (controls: size, Parkinson-60, 12-1 momentum,
                     VOLEX flag) has mean < 0 and NW t <= -2.0

Report only (never rescue a failed arm): gross spread, the avoidance book (EW universe ex-Q5 minus
EW universe), the listed-shares denominator variant of A1 (`s_sec`), per-year means, counts.
Snapshot and KSEI hashes are re-verified BEFORE any outcome; a mismatch exits.

Run:  OC_G1_APPROVED=1 venv/bin/python docs/research_programs/P-M/retail_ownership/g1_run.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402

FM_T_MAX = -2.0


def verdict(a: dict) -> dict:
    c = {"strength": bool(a["net_mean"] > 0 and a["net_t"] >= OW.BAR_FROZEN),
         "both_halves": bool(a["h1_mean"] > 0 and a["h2_mean"] > 0),
         "incremental": bool(a["fm_mean"] < 0 and a["fm_t"] <= FM_T_MAX)}
    c["pass"] = all(c.values())
    return c


def main():
    if os.environ.get("OC_G1_APPROVED") != "1":
        raise SystemExit("G1 not approved: set OC_G1_APPROVED=1 only after the owner approves the G0")
    for p, h in ((OW.HL_SNAPSHOT, OW.HL_SHA256), (OW.WF_SNAPSHOT, OW.WF_SHA256), (OW.KSEI_CSV, OW.KSEI_CSV_SHA256)):
        if OW.sha256_file(p) != h:
            raise SystemExit(f"hash mismatch: {p}")
    census = json.loads((HERE / "CENSUS_G0.json").read_text())
    if census["census"]["N"] != OW.N_FROZEN:
        raise SystemExit("census N differs from the frozen N")
    import outcomes as OC  # imported only after every gate
    panel, ksei = OW.load_all()
    forms = OW.formations(panel, ksei)
    files = sorted(ksei)
    sections = []
    for f in forms:
        i = files.index(f["file"])
        sections.append(OW.build_cross_section(panel, ksei, f, files[i - 1] if i > 0 else None))
    res = {"generated_utc": datetime.now(timezone.utc).isoformat(), "N": OW.N_FROZEN, "bar": OW.BAR_FROZEN,
           "arms": {}}
    for name, key in (("A1_level", "s"), ("A2_flow", "ds")):
        a = OC.run_arm(panel, sections, key)
        a["verdict"] = verdict(a)
        res["arms"][name] = a
    rep = OC.run_arm(panel, sections, "s_sec")
    res["report_only"] = {"A1_listed_denominator": {k: rep[k] for k in rep if k != "months"}}
    for name, a in res["arms"].items():
        yr = {}
        for m in a["months"]:
            yr.setdefault(m["k"][:4], []).append(m["net"])
        a["by_year_net_mean"] = {y: round(sum(v) / len(v), 5) for y, v in sorted(yr.items())}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (HERE / f"RESULT_{stamp}.json").write_text(json.dumps(res, indent=1, default=str))
    for name, a in res["arms"].items():
        print(name, {k: a[k] for k in ("net_mean", "net_t", "h1_mean", "h2_mean", "fm_mean", "fm_t", "n_months")},
              a["verdict"])


if __name__ == "__main__":
    main()
