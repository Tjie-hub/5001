#!/usr/bin/env python3
"""Discovery sprint — incrementality (Fama-MacBeth) + cross-family ranking.

Incrementality: per-date cross-sectional OLS of hold5 on [candidate, ret1,
ret5_z, vol_z]; the candidate coefficient's date-series mean and NW t tell us
whether the candidate adds information beyond simple price/volume. Descriptive
only — ranking is economic (magnitude, consistency, breadth, cost survival).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

CAND = [
    # binary activation flags (the tradable object is the flag, not the dose)
    ("FLAG-A4-flow-over-adv", lambda p, X: ((p.nb / p.adv60) >= 0.05).astype(float)),
    ("FLAG-A5-flow-accel", lambda p, X: (X["accel_z"] >= 1.5).astype(float)),
    ("FLAG-C1-flow-streak4of5", lambda p, X: ((X["streak"] >= 4) & (X["nbz"] > 0)).astype(float)),
    ("FLAG-E1-volspike+buyflow", lambda p, X: ((X["volz"] >= 2.0) & (X["nbz"] >= 1.0)).astype(float)),
    ("FLAG-E3-bigmove+confirm", lambda p, X: ((X["r1"].abs() >= 0.03) & (np.sign(X["nbz"]) == np.sign(X["r1"])) & (X["r1"].abs() >= 0.03)).astype(float)),
    ("FLAG-BL-momentum", lambda p, X: (X["ret5z"] >= 1.5).astype(float)),
    ("FLAG-BL-volspike", lambda p, X: (X["volz"] >= 2.0).astype(float)),
]

# pairwise-controlled incrementality: candidate flag + its natural no-flow twin
PAIRS = [
    ("E1 vs volspike", "FLAG-E1-volspike+buyflow", ["FLAG-BL-volspike"]),
    ("E3 vs momentum", "FLAG-E3-bigmove+confirm", ["FLAG-BL-momentum"]),
    ("A4 vs raw-flow", "FLAG-A4-flow-over-adv", ["RAW-nbz"]),
]


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    nbz = sl.trailing_z(p.nb)
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    r1 = p.ret1
    nb5 = p.nb.rolling(5, min_periods=3).sum()
    accel_z = sl.trailing_z(nb5 - nb5.shift(5))
    streak = (p.nb > 0).astype(float).rolling(5).sum()
    X = {"nbz": nbz, "volz": volz, "ret5z": ret5z, "r1": r1, "accel_z": accel_z, "streak": streak,
         "RAW-nbz": nbz}

    results = {}
    for cid, builder in CAND:
        sig = builder(p, X)
        r = sl.fm_regression(p, sig, mask, controls=[r1, ret5z, volz], k=5)
        results[cid] = r
        print(f"{cid:30s} FM(h5|ret1,ret5z,volz): beta={r['fm_mean']:+.5f} t={r['fm_t']:+.2f} n_dates={r['n_dates']}")

    print("\npairwise-controlled incrementality (h5):")
    builders = dict(CAND)
    X["FLAG-bigmoves-only"] = (r1.abs() >= 0.03).astype(float)   # same event basket, no flow
    PAIRS.append(("E3 vs bigmove-only", "FLAG-E3-bigmove+confirm", ["FLAG-bigmoves-only"]))
    pair_out = {}
    for label, cid, ctrl in PAIRS:
        sig = builders[cid](p, X)
        cs = [builders[c](p, X) if c in builders else X[c] for c in ctrl]
        r = sl.fm_regression(p, sig, mask, controls=[r1, ret5z, volz] + cs, k=5)
        pair_out[label] = r
        print(f"  {label:22s} beta={r['fm_mean']:+.5f} t={r['fm_t']:+.2f} n_dates={r['n_dates']}")

    # merge ledgers -> combined summary
    here = os.path.dirname(os.path.abspath(__file__))
    merged = []
    for f in ("ledger_daily.json", "ledger_broker.json", "ledger_intraday.json"):
        fp = os.path.join(here, "cache", f)
        if os.path.exists(fp):
            merged.extend(json.load(open(fp)))
    for m in merged:
        if m["id"] in results:
            m["fm_incrementality"] = results[m["id"]]
    with open(os.path.join(here, "cache", "ledger_all.json"), "w") as f:
        json.dump({"candidates": merged, "fm_flag": results, "fm_pairwise": pair_out},
                  f, indent=1, default=str)
    print(f"\ncombined ledger: {len(merged)} candidates -> cache/ledger_all.json")

    # ---- E3 parameter-robustness grid (declared ex ante; report all rows) ----
    print("\nE3 parameter grid (h5 gross / net of 60bp floor):")
    grid = []
    for rt in (0.02, 0.03, 0.05):
        for zt in (0.5, 1.0):
            sig = nbz.where((r1.abs() >= rt) & (np.sign(nbz) == np.sign(r1)) & (nbz >= zt), 0.0)
            e = sl.eval_signal(f"GRID-E3_r{rt}_z{zt}", sig, mask, p, None,
                               {"family": "E3-grid", "def": f"|ret1|>={rt:.0%} & sign(nb_z)=sign(ret1) & nb_z>={zt}"})
            h5 = e.get("h5")
            grid.append(e)
            print(f"  |r1|>={rt:.0%} nbz>={zt}: n={e['n_obs']:6d} "
                  + (f"h5 gross={h5['gross_mean']:+.4f} net={h5['net_floor']:+.4f} "
                     f"subs={list(h5['by_subperiod'].values())}" if h5 else "no-data"))
    with open(os.path.join(here, "cache", "ledger_e3grid.json"), "w") as f:
        json.dump(grid, f, indent=1, default=str)


if __name__ == "__main__":
    main()
