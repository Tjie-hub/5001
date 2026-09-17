#!/usr/bin/env python3
"""INDEPENDENT REIMPLEMENTATION of the ARB band-contact result.

Deliberately different from ara_arb.py / band_control.py in every mechanism:
  * long-format per-ticker numpy arrays, NOT wide date x ticker pandas panels
  * forward returns by POSITIONAL lookup close[i+1+K]/close[i+1]-1, NOT cumprod ratios
  * raw as-traded prices with EXPLICIT split exclusion, NOT sprint_lib.build_adjusted
  * split ex-dates sourced from BOTH corporate_actions AND corporate_action_events
    (the first is known to be missing the July 2026 splits; a 5:1 split is a -80%
    raw move, which passes build_adjusted's |ret|>0.9 guard and would register as a
    FALSE limit-down contact in the original implementation)
  * no sprint_lib import at all
Same universe RULES (liquidity floor, price floor, suspension pad) implemented
independently, or the comparison would be meaningless.
"""
import json, sqlite3, sys
from collections import defaultdict
import numpy as np

DB = "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db"
K, LIQ, PMIN, PAD, TOUCH = 21, 1e9, 50.0, 20, 0.95

con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)

# ---- split ex-dates from BOTH sources ----------------------------------
splits = defaultdict(set)
for t, dt in con.execute("SELECT ticker,date FROM corporate_actions WHERE action='split'"):
    splits[t].add(str(dt)[:10])
n_ca = sum(len(v) for v in splits.values())
for t, j in con.execute("SELECT ticker,raw_json FROM corporate_action_events "
                        "WHERE action_type IN ('stocksplit','stock_reverse','bonus')"):
    try:
        d = json.loads(j)
        ex = str(d.get("stocksplit_exdate") or "")[:10]
        if len(ex) == 10:
            splits[t].add(ex)
    except Exception:
        pass
n_all = sum(len(v) for v in splits.values())
print(f"split ex-dates: {n_ca} from corporate_actions, {n_all} after adding "
      f"corporate_action_events (+{n_all-n_ca} the original implementation could not see)")

# ---- suspension windows ------------------------------------------------
susp = defaultdict(list)
for t, a, b in con.execute("SELECT ticker,last_normal_date,resume_date FROM suspension_events"):
    susp[t].append((str(a)[:10], str(b or a)[:10]))

rows = con.execute("SELECT ticker,date,close,volume FROM ohlcv WHERE is_final=1 "
                   "AND date>='2021-07-01' AND date<='2026-09-13' AND close>0 "
                   "ORDER BY ticker,date")
by_t = defaultdict(list)
for t, dt, c, v in rows:
    by_t[t].append((str(dt)[:10], float(c), float(v or 0)))
con.close()

def regime(day: str):
    if "2021-07-05" <= day <= "2023-06-04": return "R1"
    if "2023-06-05" <= day <= "2023-09-01": return "R2"
    if "2023-09-04" <= day <= "2025-04-07": return "R3"
    if day >= "2025-04-08":                 return "R4"
    return None

def tier_band(prev_close: float) -> float:
    if prev_close <= 200:  return 0.35
    if prev_close > 5000:  return 0.20
    return 0.25

def arb_band(day: str, prev_close: float):
    rg = regime(day)
    if rg == "R1": return 0.07
    if rg == "R2": return 0.15
    if rg == "R3": return tier_band(prev_close)
    if rg == "R4": return 0.15
    return None

recs = []
for t, series in by_t.items():
    n = len(series)
    if n < 100: continue
    days = [s[0] for s in series]
    close = np.array([s[1] for s in series])
    volu  = np.array([s[2] for s in series])
    tval  = close * volu
    # suspension mask, +/- PAD sessions, by position
    bad = np.zeros(n, dtype=bool)
    pos = {d: i for i, d in enumerate(days)}
    for a, b in susp.get(t, []):
        ia, ib = pos.get(a), pos.get(b, pos.get(a))
        if ia is None: continue
        bad[max(0, ia - PAD): min(n - 1, (ib if ib is not None else ia) + PAD) + 1] = True
    sp = splits.get(t, set())
    for i in range(60, n - K - 2):
        if bad[i]: continue
        if days[i] in sp or days[i - 1] in sp:      # split ex-date -> no band claim
            continue
        adv = np.median(tval[max(0, i - 60):i])      # trailing 60, strictly prior
        if not np.isfinite(adv) or adv < LIQ: continue
        if close[i] < PMIN: continue
        if volu[i + 1] <= 0: continue                 # tradable next session
        prev = close[i - 1]
        if prev <= 0: continue
        r = close[i] / prev - 1.0
        band = arb_band(days[i], prev)
        if band is None: continue
        fwd = close[i + 1 + K] / close[i + 1] - 1.0   # positional, entry next close
        if not np.isfinite(fwd): continue
        recs.append((days[i], t, r, band, fwd))

print(f"admissible ticker-days: {len(recs):,}")
dt_arr = np.array([x[0] for x in recs])
ret    = np.array([x[2] for x in recs])
band   = np.array([x[3] for x in recs])
fwd    = np.array([x[4] for x in recs])

# universe mean per date, computed from the same admissible set
uni = defaultdict(list)
for d, f in zip(dt_arr, fwd): uni[d].append(f)
umean = {d: float(np.mean(v)) for d, v in uni.items() if len(v) >= 80}
keep = np.array([d in umean for d in dt_arr])
dt_arr, ret, band, fwd = dt_arr[keep], ret[keep], band[keep], fwd[keep]
base = np.array([umean[d] for d in dt_arr])
exc = fwd - base
depth = (-ret) / band
hit = ret <= -band * TOUCH

def stat(mask, lab):
    v = exc[mask]
    if len(v) < 8: print(f"  {lab:34s} n={len(v):6d}  (too few)"); return
    se = v.std(ddof=1) / np.sqrt(len(v))
    print(f"  {lab:34s} n={len(v):6d}  excess {100*v.mean():+7.2f}%  t={v.mean()/se:+7.2f}")

print("\nEVENT COUNTS BY REGIME (independent)")
reg = np.array([regime(d) for d in dt_arr])
for rg in ("R1", "R2", "R3", "R4"):
    m = reg == rg
    print(f"  {rg}  admissible {int(m.sum()):7d}   ARB contacts {int((m & hit).sum()):6d}")

print("\nC1  MAGNITUDE-MATCHED (independent)")
for lo_, hi_, lab in ((0, .5, "<50% of band"), (.5, .7, "50-70%"), (.7, .85, "70-85%"),
                      (.85, .95, "85-95% (near-miss)"), (.95, 9, ">=95% (AT BAND)")):
    stat((ret <= -0.02) & (depth >= lo_) & (depth < hi_), lab)

near = (ret <= -0.02) & (depth >= .85) & (depth < .95)
atb  = (ret <= -0.02) & (depth >= .95)
d_ = exc[atb].mean() - exc[near].mean()
sed = np.sqrt(exc[atb].var(ddof=1)/atb.sum() + exc[near].var(ddof=1)/near.sum())
print(f"  DIFFERENCE (band minus near-miss): {100*d_:+.2f}%  t={d_/sed:+.2f}")

print("\nC2  REGRESSION excess ~ fall size + band dummy (day-clustered, independent)")
co = []
for d in sorted(set(dt_arr[ret <= -0.02])):
    m = (dt_arr == d) & (ret <= -0.02)
    if m.sum() < 30 or len(set(hit[m])) < 2: continue
    X = np.column_stack([np.ones(m.sum()), ret[m], hit[m].astype(float)])
    try: b_, *_ = np.linalg.lstsq(X, exc[m], rcond=None)
    except np.linalg.LinAlgError: continue
    co.append(b_[1:])
C = np.array(co); mm = C.mean(0); tt = mm / (C.std(0, ddof=1) / np.sqrt(len(C)))
print(f"  days={len(C)}")
print(f"  fall size (ret)  coef {100*mm[0]:+8.3f}%  t={tt[0]:+6.2f}")
print(f"  BAND DUMMY       coef {100*mm[1]:+8.3f}%  t={tt[1]:+6.2f}")

print("\nALL ARB CONTACTS, pooled (independent)")
stat(hit, "ARB contact")

print("\nPER-REGIME ARB EXCESS (independent) — the amendment claims all three negative")
for rg in ("R1","R3","R4"):
    stat(hit & (reg==rg), f"ARB contact, {rg}")
print("\nARA placebo by regime (independent)")
ara_band = np.array([0.35 if p_<=200 else (0.20 if p_>5000 else 0.25) for p_ in
                     [None]*0]) if False else None

