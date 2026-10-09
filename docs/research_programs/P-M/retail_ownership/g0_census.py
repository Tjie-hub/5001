"""G0 census for the retail-ownership study (D-083). COUNTS ONLY -- no outcome is read.

Never imports outcomes.py. Every quantity is known at or before each formation close, except
the power estimate, which uses returns from BEFORE the first formation only (pre-sample
2001-01 .. the first formation, hard-asserted) on random sorts that carry no KSEI signal.

Run:  venv/bin/python docs/research_programs/P-M/retail_ownership/g0_census.py
Writes CENSUS_G0.json next to this file.
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402

POWER_SEED = 20261009
POWER_START = date(2002, 1, 1)


def q(v, ps=(0.1, 0.25, 0.5, 0.75, 0.9)):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    return {f"p{int(p * 100)}": round(float(np.quantile(v, p)), 4) for p in ps} if len(v) else {}


def pre_sample_power(panel, first_k: date) -> dict:
    """sigma of a monthly random-quintile L-S spread, pre-sample only (no signal, no outcome)."""
    rng = random.Random(POWER_SEED)
    sess = panel.sessions
    # pseudo-formations: 5th session of each month, POWER_START .. first_k (exclusive)
    pf, seen = [], set()
    for d in sess:
        if d < POWER_START or d >= first_k:
            continue
        ym = (d.year, d.month)
        if ym in seen:
            continue
        mon = [x for x in sess if (x.year, x.month) == ym]
        if len(mon) >= 5 and mon[4] < first_k:
            pf.append(mon[4])
            seen.add(ym)
    spreads = []
    for a, b in zip(pf[:-1], pf[1:]):
        assert b < first_k, "power estimate must stay pre-sample"
        names = []
        for t, g in panel.tickers.items():
            i = g["idx"].get(a)
            if i is None or i < OW.HIST_MIN or not (g["adv"][i] >= OW.ADV_MIN) or g["c"][i] < OW.PRICE_MIN:
                continue
            j, acc, ok = i + 1, 1.0, True
            while j < len(g["d"]) and g["d"][j] <= b:
                r = (g["c"][j] + panel.divs.get((t, g["d"][j]), 0.0)) / g["c"][j - 1] - 1.0
                if not np.isfinite(r) or abs(r) > OW.BAD_PRINT:
                    ok = False
                    break
                acc *= 1 + r
                j += 1
            if ok:
                names.append(acc - 1)
        if len(names) < 25:
            continue
        rng.shuffle(names)
        k = len(names) // 5
        spreads.append(float(np.mean(names[:k]) - np.mean(names[-k:])))
    s = np.asarray(spreads)
    return {"pre_sample_months": len(s), "window": [POWER_START.isoformat(), first_k.isoformat()],
            "sd_random_ls": round(float(s.std(ddof=1)), 5) if len(s) > 2 else None,
            "median_universe_note": "random quintiles of ADV>=1bn, price>=50, >=252-bar names"}


def main():
    t0 = time.time()
    assert OW.sha256_file(OW.HL_SNAPSHOT) == OW.HL_SHA256, "history_long snapshot changed"
    assert OW.sha256_file(OW.WF_SNAPSHOT) == OW.WF_SHA256, "walkforward snapshot changed"
    assert OW.sha256_file(OW.KSEI_CSV) == OW.KSEI_CSV_SHA256, "KSEI csv changed"
    panel, ksei = OW.load_all()
    forms = OW.formations(panel, ksei)
    files = sorted(ksei)
    sections, per = [], []
    for f in forms:
        i = files.index(f["file"])
        prev = files[i - 1] if i > 0 else None
        cs = OW.build_cross_section(panel, ksei, f, prev)
        sections.append(cs)
        q1, q5, n1 = OW.quintiles(cs["rows"], "s")
        _, _, n2 = OW.quintiles(cs["rows"], "ds")
        per.append({"file": f["file"].isoformat(), "k": f["k"].isoformat(),
                    "stamp": f["stamp"].isoformat() if f["stamp"] else None,
                    "delayed_by_stamp": f["delayed_by_stamp"],
                    "ksei_rows": len(ksei[f["file"]]), "universe": len(cs["rows"]),
                    "a1_ranked": n1, "a1_quintile": n1 // 5, "a2_ranked": n2, "a2_quintile": n2 // 5,
                    "drop": cs["drop"]})
    # testable formations: need a next formation to close the holding window
    testable = per[:-1]
    stamp_ok = all(p["stamp"] is None or p["stamp"] < p["k"] for p in per)
    lag_days = [(date.fromisoformat(p["k"]) - date.fromisoformat(p["file"])).days for p in per]
    allrows = [r for cs in sections for r in cs["rows"]]
    s = [r["s"] for r in allrows]
    s_sec = [r["s_sec"] for r in allrows]
    ok = [(a, b) for a, b in zip(s, s_sec) if np.isfinite(a) and np.isfinite(b)]
    from scipy.stats import spearmanr  # noqa: E402
    rho = float(spearmanr([a for a, _ in ok], [b for _, b in ok]).correlation) if ok else math.nan
    years = {}
    for p in testable:
        y = p["k"][:4]
        years.setdefault(y, []).append(p["universe"])
    power = pre_sample_power(panel, date.fromisoformat(per[0]["k"]))
    n_t = len(testable)
    sd = power["sd_random_ls"]
    mde = (OW.BAR_FROZEN + 0.8416) * sd / math.sqrt(n_t) if sd else None
    out = {
        "study": "retail ownership (KSEI) {OC}, D-083", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "snapshots": {"history_long": OW.HL_SHA256, "walkforward": OW.WF_SHA256,
                      "ksei_csv": OW.KSEI_CSV_SHA256, "verified": True},
        "census": {"ledger_before": OW.CENSUS_LEDGER, "arms": OW.N_ARMS, "N": OW.N_FROZEN,
                   "bar_exact": round(OW.BAR_EXACT, 6), "bar_frozen": OW.BAR_FROZEN,
                   "ledger_rows_counted": "609 after D-080 (DECISION_LOG) + A1 + A2 of this study"},
        "formations": {"total": len(per), "testable": n_t, "first_k": per[0]["k"], "last_testable_k": testable[-1]["k"],
                       "halves": {"h1_le_2017_12_31": sum(1 for p in testable if p["k"] <= "2017-12-31"),
                                  "h2": sum(1 for p in testable if p["k"] > "2017-12-31")}},
        "pit": {"rule": f"file M known from the {OW.KNOWN_LAG_SESSIONS}th panel session after its date",
                "all_zip_stamps_before_formation": stamp_ok,
                "formations_delayed_by_stamp": sum(1 for p in per if p["delayed_by_stamp"]),
                "calendar_lag_days": {"min": min(lag_days), "max": max(lag_days)},
                "regular_volume_bars_used": panel.regvol_used,
                "consolidated_volume_bars_kept_no_flow_bars": panel.regvol_missing},
        "universe": {"median": int(np.median([p["universe"] for p in testable])),
                     "min": min(p["universe"] for p in testable), "max": max(p["universe"] for p in testable),
                     "by_year_median": {y: int(np.median(v)) for y, v in sorted(years.items())},
                     "drop_totals": {k: sum(p["drop"][k] for p in per) for k in per[0]["drop"]}},
        "denominator": {"frozen": "custodied total (L_total + F_total)",
                        "s_custodied": q(s), "s_listed": q(s_sec), "spearman_s_vs_listed": round(rho, 4),
                        "custody_ratio_tot_over_listed": q([r["custody"] for r in allrows]),
                        "foreign_individual_share": q([r["fshare"] for r in allrows])},
        "signal_ds": q([r["ds"] for r in allrows]),
        "power": {**power, "n_testable_months": n_t,
                  "mde_monthly_spread_at_bar_80pct": round(mde, 5) if mde else None,
                  "note": "MDE = (bar + 0.8416) * sd / sqrt(n); NW lags ignored (optimistic)"},
        "per_formation": per,
        "runtime_s": round(time.time() - t0, 1),
    }
    (HERE / "CENSUS_G0.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("census", "formations", "pit", "universe", "denominator", "power")}, indent=1))


if __name__ == "__main__":
    main()
