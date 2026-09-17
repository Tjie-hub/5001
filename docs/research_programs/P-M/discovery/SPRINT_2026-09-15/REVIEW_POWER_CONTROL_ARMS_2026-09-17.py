#!/usr/bin/env python3
"""ADVERSARIAL CHECK on HARNESS_POWER_CONTROL_2026-09-16.py (2026-09-17).

Arms the original control did NOT run, using the SAME gate code verbatim:
  NULL       delta=0, uniform mask          -> Type I rate (never measured)
  CLUSTERED  treatment assigned by whole    -> a signal that fires on particular
             SESSIONS                          sessions (band contact, vol spikes)
  CORRELATED treated = high |volume z|      -> a signal the FM controls absorb

Only the treated-mask CONSTRUCTION differs. G1-G5 arithmetic is copied from
HARNESS_POWER_CONTROL_2026-09-16.py without modification.
"""
import sys, os, json, importlib.util
D = "/home/tjiesar/10 Projects/idx-walkforward-5001/docs/research_programs/P-M/discovery/SPRINT_2026-09-15"
sys.path.insert(0, D); os.chdir(D)
import numpy as np, pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

spec = importlib.util.spec_from_file_location(
    "hpc", os.path.join(D, "HARNESS_POWER_CONTROL_2026-09-16.py"))
hpc = importlib.util.module_from_spec(spec); spec.loader.exec_module(hpc)

SEEDS = list(range(20))

p = sl.SprintPanel()
mask0 = p.mask_base(); clean = ~build_contam(p); mask = mask0 & clean
r1 = p.ret1; ret5z = sl.trailing_z(p.ret5); volz = sl.trailing_z(p.volume)
nbz = sl.trailing_z(p.nb); adv = p.adv60.where(mask0); ter = adv.rank(axis=1, pct=True)
y = p.hold[5]
valid = mask & y.notna() & r1.notna() & ret5z.notna() & volz.notna() & ter.notna() & nbz.notna()
di, ci = np.where(valid.values)
dates = np.asarray(valid.index)[di]; tick = np.asarray(valid.columns)[ci]
yv = y.values[di, ci].astype(float)
r1v = r1.values[di, ci]; r5v = ret5z.values[di, ci]; vlv = volz.values[di, ci]
tvl = ter.values[di, ci]; nbv = nbz.values[di, ci]
half = (pd.Series(dates).str[:4] + np.where(pd.Series(dates).str[5:7].astype(int) <= 6, "-H1", "-H2")).values
pool_n = len(yv)
uniq_dates = pd.unique(dates); date_pos = {d: i for i, d in enumerate(uniq_dates)}
dpos = np.array([date_pos[d] for d in dates]); n_dates = len(uniq_dates)
print(f"pool {pool_n} cells / {n_dates} dates, base h5={yv.mean():+.5f}")

F = hpc.build_oos(); oos = {}
for era, a, b in (("2021H2-2022", "2021-07-01", "2023-01-01"), ("2023-2024", "2023-01-01", "2025-01-01")):
    Fv = F["trad"] & F["h5"].notna(); Fv = Fv[(Fv.index >= a) & (Fv.index < b)]
    oos[era] = F["h5"].loc[Fv.index].values[Fv.values].astype(float)

def pick(kind, m, seed):
    rng = np.random.default_rng(777000 + seed * 31 + m)
    if kind == "uniform":
        return rng.choice(pool_n, size=min(m, pool_n), replace=False)
    if kind == "clustered":
        order = rng.permutation(n_dates); take = []
        for dgi in order:
            rows = np.where(dpos == dgi)[0]; take.append(rows)
            if sum(len(t) for t in take) >= m: break
        allr = np.concatenate(take)
        return allr[:m]
    if kind == "correlated":
        cand = rng.choice(pool_n, size=min(3 * m, pool_n), replace=False)
        return cand[np.argsort(-vlv[cand])[:m]]
    raise ValueError(kind)

def evaluate(idx, delta):
    """G1-G5 verbatim from the control script."""
    flag = np.zeros(pool_n); flag[idx] = 1.0
    y_syn = yv.copy(); y_syn[idx] += delta
    ev_mean = float(y_syn[idx].mean())
    g1 = (ev_mean - 0.006) >= 0.003
    hm = {}
    for h in sorted(pd.unique(half)):
        v = y_syn[idx][half[idx] == h]; hm[h] = float(v.mean()) if len(v) > 30 else np.nan
    pos_halves = sum(1 for v in hm.values() if not np.isnan(v) and v > 0)
    g2 = pos_halves >= 3
    n_t = len(np.unique(tick[idx])); g4 = (len(idx) >= 1000) and (n_t >= 50)
    g3, fm_beta, fm_t, n_betas = False, np.nan, np.nan, 0
    if g1 and g2 and g4:
        betas = []; y_full = yv + delta * flag
        for dgi in range(n_dates):
            rows = np.where(dpos == dgi)[0]
            if rows.size < 30: continue
            if np.abs(flag[rows]).sum() == 0: continue
            Xd = np.column_stack([np.ones(rows.size), flag[rows], r1v[rows], r5v[rows],
                                  vlv[rows], tvl[rows], nbv[rows]])
            b, *_ = np.linalg.lstsq(Xd, y_full[rows], rcond=None); betas.append(b[1])
        betas = np.array(betas); n_betas = len(betas)
        if n_betas > 1:
            fm_beta = float(betas.mean()); se = betas.std(ddof=1) / np.sqrt(n_betas)
            fm_t = fm_beta / se if se > 0 else np.nan
            g3 = (fm_beta > 0) and (abs(fm_t) >= 2)
    ok5 = True
    for era in oos:
        yy = oos[era]; k = min(len(idx), len(yy))
        rr = np.random.default_rng(int(delta * 1e4) + k)
        mu = float(yy[rr.choice(len(yy), size=k, replace=False)].mean() + delta)
        ok5 = ok5 and (mu > 0)
    first = None
    for g, v in (("G1", g1), ("G2", g2), ("G3", g3), ("G4", g4), ("G5", ok5)):
        if not v: first = g; break
    return dict(det=first is None, first=first, ev=ev_mean, t=fm_t, nb=n_betas,
                nt=n_t, ph=pos_halves)

print("\narm          m      delta   detect   first-gate kills            median fm_t  median #FM dates")
rows = []
plan = [("uniform", 0), ("clustered", 0), ("correlated", 0),
        ("uniform", 80), ("clustered", 80), ("correlated", 80),
        ("clustered", 150), ("correlated", 150), ("clustered", 300)]
for kind, dbp in plan:
    for m in (2500, 10000):
        delta = dbp / 1e4
        res = [evaluate(pick(kind, m, s), delta) for s in SEEDS]
        det = sum(r["det"] for r in res)
        kills = {}
        for r in res:
            if r["first"]: kills[r["first"]] = kills.get(r["first"], 0) + 1
        ts = [r["t"] for r in res if r["t"] == r["t"]]
        nbs = [r["nb"] for r in res if r["nb"] > 0]
        print(f"{kind:11s} {m:6d} {dbp:+5d}bp  {det:2d}/20 {det/20:4.0%}  {str(kills):26s} "
              f"{(np.median(ts) if ts else float('nan')):>8.2f}   {(int(np.median(nbs)) if nbs else 0):>6d}")
        rows.append(dict(arm=kind, m=m, delta_bp=dbp, detect=det,
                         kills=kills, median_t=(float(np.median(ts)) if ts else None),
                         median_fm_dates=(int(np.median(nbs)) if nbs else 0),
                         median_ev_bp=float(np.median([r["ev"] for r in res]) * 1e4),
                         median_tickers=int(np.median([r["nt"] for r in res]))))
json.dump(rows, open(os.path.join(D, "cache", "review_power_control_arms.json"), "w"), indent=1)
print("\nwrote adv_power_check.json")
