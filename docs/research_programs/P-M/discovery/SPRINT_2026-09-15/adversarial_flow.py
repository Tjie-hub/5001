#!/usr/bin/env python3
"""Adversarial pass — flow candidates: A5 combination grid, A4 controlled
comparison, interaction tree, avoidance quantification.

PREDECLARED KILL RULES (stated before running):
- A conditioning branch SURVIVES only if: incremental h5 >= +30bp vs its parent
  AND positive in >= 3 of 4 half-years at h5 AND net-of-60bp positive at h10.
- Otherwise the branch is KILLED. No threshold iteration after seeing results.
- All UP3-based branches use the suspension-clean event set (the adversarial
  base established in adversarial_up3.py section G).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {"kill_rule": "incr h5>=30bp & pos>=3/4 halves & net60(h10)>0"}


def build_contam(p):
    """Suspension contamination matrix: events within +/-20 sessions of a
    suspension window (generous exclusion)."""
    susp = sl.load_suspensions()
    dates_idx = {d: i for i, d in enumerate(p.close.index)}
    contam = pd.DataFrame(False, index=p.close.index, columns=p.close.columns)
    for _, row in susp.iterrows():
        tk = row["ticker"]
        if tk not in contam.columns:
            continue
        i_ln = dates_idx.get(row["last_normal_date"])
        if i_ln is None:
            continue
        i_rs = dates_idx.get(row["resume_date"], i_ln)
        contam.iloc[max(0, i_ln - 20): min(len(contam.index) - 1, i_rs + 20) + 1,
                    contam.columns.get_loc(tk)] = True
    return contam


def cell(name, sel, holds, out):
    row = {"id": name, "n": int(sel.values.sum())}
    for k in (5, 10, 20):
        v = holds[k][sel].values; v = v[~np.isnan(v)]
        row[f"h{k}"] = float(np.mean(v)) if len(v) > 30 else None
    if row["h5"] is not None:
        r = holds[5][sel]
        sp = {}
        for lab, (lo, hi) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                              "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
            sub = r[(r.index >= lo) & (r.index < hi)]
            vv = sub.values[sub.notna().values]
            sp[lab] = round(float(np.mean(vv)), 5) if len(vv) > 30 else None
        row["subs"] = sp
        vals = [x for x in sp.values() if x is not None]
        row["pos_halves"] = sum(1 for x in vals if x > 0)
        row["net60_h10"] = (row["h10"] - 0.006) if row["h10"] is not None else None
    print(f"  {name:44s} n={row['n']:6d} h5={row['h5'] if row['h5'] is None else round(row['h5'],4)} "
          f"h10={row['h10'] if row['h10'] is None else round(row['h10'],4)} h20={row['h20'] if row['h20'] is None else round(row['h20'],4)}"
          + (f" pos_halves={row['pos_halves']}/4" if "pos_halves" in row else ""))
    out.append(row)
    return row


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    r1 = p.ret1
    holds = {5: p.hold[5], 10: p.hold[10], 20: p.hold[20]}
    contam = build_contam(p)
    clean = ~contam

    nbz = sl.trailing_z(p.nb)
    nb5 = p.nb.rolling(5, min_periods=3).sum()
    accel_z = sl.trailing_z(nb5 - nb5.shift(5))
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    adv = p.adv60.where(mask)
    adv_ter = adv.rank(axis=1, pct=True)

    # ---------- 2. A5 COMBINATION GRID ----------
    print("=" * 70); print("2. A5 COMBINATION GRID (predeclared parents)"); print("=" * 70)
    up3c = (r1 >= 0.03) & mask & clean            # suspension-clean UP3 parent
    rows = []
    print("-- parent references --")
    cell("PARENT UP3-suspension-clean", up3c, holds, rows)
    cell("PARENT A5 standalone (accel_z>=1.5)", mask & clean & (accel_z >= 1.5), holds, rows)
    print("-- A5 x UP3 --")
    cell("UP3c & accel_z>=+1.5", up3c & (accel_z >= 1.5), holds, rows)
    cell("UP3c & accel neutral", up3c & (accel_z.abs() <= 1.0), holds, rows)
    cell("UP3c & accel_z<=-1.5", up3c & (accel_z <= -1.5), holds, rows)
    print("-- A5 x liquidity (standalone A5 by ADV tercile) --")
    a5 = mask & clean & (accel_z >= 1.5)
    cell("A5 & ADV top-3rd", a5 & (adv_ter >= 0.667), holds, rows)
    cell("A5 & ADV mid-3rd", a5 & (adv_ter >= 0.333) & (adv_ter < 0.667), holds, rows)
    cell("A5 & ADV bot-3rd", a5 & (adv_ter < 0.333), holds, rows)
    print("-- A5 x volatility --")
    cell("A5 & vol_z>=+1.5", a5 & (volz >= 1.5), holds, rows)
    cell("A5 & vol_z<=0", a5 & (volz <= 0), holds, rows)
    print("-- A5 x prior return state --")
    cell("A5 & ret5>0", a5 & (p.ret5 > 0), holds, rows)
    cell("A5 & ret5<0", a5 & (p.ret5 < 0), holds, rows)
    print("-- A5 x volume state --")
    cell("A5 & volume rising (vol>vol(t-1))", a5 & (p.volume > p.volume.shift(1)), holds, rows)
    cell("A5 & volume falling", a5 & (p.volume <= p.volume.shift(1)), holds, rows)
    OUT["a5_grid"] = rows

    # ---------- 3. A4 CONTROLLED COMPARISON ----------
    print(); print("=" * 70); print("3. A4 vs raw flow vs A5 vs A4+A5 (portfolio + FM)"); print("=" * 70)
    ret5z_ = ret5z
    rawf = mask & clean & (nbz >= 2.0)
    a4 = mask & clean & ((p.nb / p.adv60) >= 0.05)
    for nm, sel in (("rawflow z>=2", rawf), ("A4 noa>=5%", a4), ("A5 accel", a5)):
        v5 = holds[5][sel].values; v5 = v5[~np.isnan(v5)]
        v10 = holds[10][sel].values; v10 = v10[~np.isnan(v10)]
        print(f"  {nm:14s}: n={len(v5):6d} h5={np.mean(v5):+.4f} h10={np.mean(v10):+.4f}")
    fm_incr = {}
    ctrls = [r1, ret5z_, volz]
    for nm, flag in (("A4 | ctrl", (p.nb / p.adv60 >= 0.05).astype(float)),
                     ("A5 | ctrl", (accel_z >= 1.5).astype(float)),
                     ("A5 | ctrl+rawflow", (accel_z >= 1.5).astype(float)),
                     ("A4 | ctrl+A5", (p.nb / p.adv60 >= 0.05).astype(float)),
                     ("rawflow | ctrl+A5", (nbz >= 2.0).astype(float))):
        cs = list(ctrls)
        if "A5" in nm.split("|")[1]:
            cs.append((accel_z >= 1.5).astype(float))
        if "rawflow" in nm.split("|")[1]:
            cs.append((nbz >= 2.0).astype(float))
        r = sl.fm_regression(p, flag, mask & clean, controls=cs, k=5)
        fm_incr[nm] = r
        print(f"  FM {nm:20s}: beta={r['fm_mean']:+.5f} t={r['fm_t']:+.2f} n_dates={r['n_dates']}")
    OUT["a4_compare"] = fm_incr

    # ---------- 4. INTERACTION TREE (small, disciplined) ----------
    print(); print("=" * 70); print("4. INTERACTION TREE on UP3-suspension-clean"); print("=" * 70)
    tree = []
    print("-- branch: UP3c x accel x liquidity --")
    cell("UP3c & accel>=1.5 & ADV bot-3rd", up3c & (accel_z >= 1.5) & (adv_ter < 0.333), holds, tree)
    cell("UP3c & accel>=1.5 & ADV top-3rd", up3c & (accel_z >= 1.5) & (adv_ter >= 0.667), holds, tree)
    print("-- branch: UP3c x volatility --")
    cell("UP3c & vol_z>=2", up3c & (volz >= 2), holds, tree)
    cell("UP3c & vol_z<=0", up3c & (volz <= 0), holds, tree)
    print("-- branch: UP3c x flow direction (avoid cells) --")
    cell("UP3c & nbz<=-0.5 (retail selling INTO up-move)", up3c & (nbz <= -0.5), holds, tree)
    cell("UP3c & nbz>=+0.5 (chase confirmed)", up3c & (nbz >= 0.5), holds, tree)
    cell("UP3c & |nbz|<0.5 (flow neutral)", up3c & (nbz.abs() < 0.5), holds, tree)
    OUT["tree"] = tree

    # ---------- 5. AVOIDANCE QUANTIFICATION ----------
    print(); print("=" * 70); print("5. NEGATIVE INFORMATION / AVOIDANCE SPREADS (h5)"); print("=" * 70)
    avoid = []
    dn3 = (r1 <= -0.03) & mask & clean
    cell("DOWN3 parent (dip-buy baseline)", dn3, holds, avoid)
    cell("DOWN3 & retail buying (nbz>=0.5) [AVOID]", dn3 & (nbz >= 0.5), holds, avoid)
    cell("DOWN3 & capitulation (nbz<=-0.5) [AVOID]", dn3 & (nbz <= -0.5), holds, avoid)
    cell("DOWN3 & flow neutral [KEEP]", dn3 & (nbz.abs() < 0.5), holds, avoid)
    cell("DOWN3 & accel_z>=1.5 [AVOID]", dn3 & (accel_z >= 1.5), holds, avoid)
    print("-- UP3 side: avoid up-moves with heavy opposing flow --")
    cell("UP3c & nbz<=-0.5 [AVOID]", up3c & (nbz <= -0.5), holds, avoid)
    cell("UP3c ex nbz<=-0.5 [filtered parent]", up3c & (nbz > -0.5), holds, avoid)
    OUT["avoidance"] = avoid

    # avoid-spread subperiod stability (DOWN3 neutral vs extremes)
    def spread_subs(sel_bad, sel_good):
        res = {}
        for k in (5,):
            rb = holds[k][sel_bad]; rg = holds[k][sel_good]
            for lab, (lo, hi) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                                  "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
                vb = rb[(rb.index >= lo) & (rb.index < hi)]; vb = vb.values[~np.isnan(vb.values)]
                vg = rg[(rg.index >= lo) & (rg.index < hi)]; vg = vg.values[~np.isnan(vg.values)]
                if len(vb) > 30 and len(vg) > 30:
                    res[lab] = round(float(np.mean(vb) - np.mean(vg)), 5)
        return res
    OUT["avoid_spread_down_buying"] = spread_subs(dn3 & (nbz >= 0.5), dn3 & (nbz.abs() < 0.5))
    OUT["avoid_spread_up_selling"] = spread_subs(up3c & (nbz <= -0.5), up3c & (nbz.abs() < 0.5))
    print("avoid-spread by half (DOWN3 buying vs neutral):", OUT["avoid_spread_down_buying"])
    print("avoid-spread by half (UP3 selling vs neutral): ", OUT["avoid_spread_up_selling"])

    with open(os.path.join(HERE, "cache", "adv_flow.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    print("\nsaved -> cache/adv_flow.json")


if __name__ == "__main__":
    main()
