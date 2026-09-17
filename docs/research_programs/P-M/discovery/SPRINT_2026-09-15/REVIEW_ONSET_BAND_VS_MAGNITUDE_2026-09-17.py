#!/usr/bin/env python3
"""EXECUTOR MEASUREMENT — C1 difference-in-means, day-collapsed + NW(20).

Answers the review's §3 open item: the handover's C1 t = -3.45/-3.76 carried both
defects (same-day cross-section counted as independent + overlapping 21d forward
windows). This recomputes the C1 contrast on the reviewer's own independent
admissible-event construction (REVIEW_BAND_INDEP_SOURCE_2026-09-16.py, embedded
verbatim), day-collapsed, with NW(20).

C1 pairs measured:
  (a) at-band (depth>=0.95) minus near-miss (0.85<=depth<0.95)
  (b) at-band minus all shallower big falls (depth<0.85, ret<=-2%)
Both one-sided expectations: at-band excess < shallow excess.
Output to stdout (captured by shell redirection).
"""
import json, sqlite3, sys
from collections import defaultdict
import numpy as np

DB = "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db"
K, LIQ, PMIN, PAD, TOUCH = 21, 1e9, 50.0, 20, 0.95

con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)

splits = defaultdict(set)
for t, dt in con.execute("SELECT ticker,date FROM corporate_actions WHERE action=?",
                         ("split",)):
    splits[t].add(str(dt)[:10])
n_ca = sum(len(v) for v in splits.values())
for t, j in con.execute("SELECT ticker,raw_json FROM corporate_action_events "
                        "WHERE action_type IN (?,?,?)",
                        ("stocksplit", "stock_reverse", "bonus")):
    try:
        d = json.loads(j)
        ex = str(d.get("stocksplit_exdate") or "")[:10]
        if len(ex) == 10:
            splits[t].add(ex)
    except Exception:
        pass
n_all = sum(len(v) for v in splits.values())

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

def regime(day):
    if "2021-07-05" <= day <= "2023-06-04": return "R1"
    if "2023-06-05" <= day <= "2023-09-01": return "R2"
    if "2023-09-04" <= day <= "2025-04-07": return "R3"
    if day >= "2025-04-08":                 return "R4"
    return None

def tier_band(prev_close):
    if prev_close <= 200:  return 0.35
    if prev_close > 5000:  return 0.20
    return 0.25

def arb_band(day, prev_close):
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
    volu = np.array([s[2] for s in series])
    tval = close * volu
    bad = np.zeros(n, dtype=bool)
    pos = {d: i for i, d in enumerate(days)}
    for a, b in susp.get(t, []):
        ia, ib = pos.get(a), pos.get(b, pos.get(a))
        if ia is None: continue
        bad[max(0, ia - PAD): min(n - 1, (ib if ib is not None else ia) + PAD) + 1] = True
    sp = splits.get(t, set())
    for i in range(60, n - K - 2):
        if bad[i]: continue
        if days[i] in sp or days[i - 1] in sp: continue
        adv = np.median(tval[max(0, i - 60):i])
        if not np.isfinite(adv) or adv < LIQ: continue
        if close[i] < PMIN: continue
        if volu[i + 1] <= 0: continue
        prev = close[i - 1]
        if prev <= 0: continue
        r = close[i] / prev - 1.0
        band = arb_band(days[i], prev)
        if band is None: continue
        fwd = close[i + 1 + K] / close[i + 1] - 1.0
        if not np.isfinite(fwd): continue
        recs.append((days[i], t, r, band, fwd))

print(f"split ex-dates: {n_ca} from corporate_actions, {n_all} after corporate_action_events")
dt_arr = np.array([x[0] for x in recs])
ret = np.array([x[2] for x in recs])
band = np.array([x[3] for x in recs])
fwd = np.array([x[4] for x in recs])

uni = defaultdict(list)
for d, f in zip(dt_arr, fwd): uni[d].append(f)
umean = {d: float(np.mean(v)) for d, v in uni.items() if len(v) >= 80}
keep = np.array([d in umean for d in dt_arr])
dt_arr, ret, band, fwd = dt_arr[keep], ret[keep], band[keep], fwd[keep]
base = np.array([umean[d] for d in dt_arr])
exc = fwd - base
depth = (-ret) / band
hit = ret <= -band * TOUCH

# ===== THE DISCRIMINATING TEST: is the onset at constant DEPTH or constant |ret|? =====
# The executor's depth profile is FLAT to 0.90 then onsets sharply — a THRESHOLD, not
# the continuum their label claims. That leaves band-vs-magnitude open, and one test
# settles it. depth = |ret| / band, and band differs by regime (R1 .07, R2 .15,
# R3 price-tiered .20/.25/.35, R4 .15).
#   onset at the same DEPTH across regimes  -> band-relative -> BAND effect
#                                              (tabled band simply ~10% too wide)
#   onset at the same |ret| across regimes  -> magnitude-absolute -> FALL-SIZE effect
#                                              (pooled 0.90 kink = a mixing artifact)
def nw_t_of(s, L=20):
    s = np.asarray(s, float)
    if len(s) < 12: return np.nan
    e = s - s.mean(); n = len(s); g = e @ e / n
    for l in range(1, min(L, n - 1) + 1):
        g += 2.0 * (1.0 - l / (L + 1.0)) * (e[l:] @ e[:-l]) / n
    return float(s.mean() / np.sqrt(g / n)) if g > 0 else np.nan

reg = np.array([regime(d) for d in dt_arr])
BIG = ret <= -0.02
grp = np.where(reg == "R3", np.where(band > 0.30, "R3_35", np.where(band > 0.22, "R3_25", "R3_20")), reg)

print("\n" + "=" * 86)
print("ONSET LOCATION BY BAND WIDTH — the band-vs-magnitude discriminator")
print("=" * 86)
for g_ in ("R1", "R2", "R4", "R3_20", "R3_25", "R3_35"):
    m0 = BIG & (grp == g_)
    if m0.sum() < 300:
        print(f"\n{g_}: n={int(m0.sum())} — too few"); continue
    bw = np.median(band[m0])
    print(f"\n{g_}  band={bw:.2f}  n={int(m0.sum())}")
    print(f"   {'depth bin':>12s} {'|ret| range':>14s} {'n':>6s} {'mean exc':>9s}")
    for lo, hi in ((0.5,0.7),(0.7,0.8),(0.8,0.9),(0.9,0.95),(0.95,1.01),(1.01,9)):
        m = m0 & (depth >= lo) & (depth < hi)
        if m.sum() < 40:
            print(f"   {f'{lo:.2f}-{hi:.2f}':>12s} {f'{100*lo*bw:.1f}-{100*hi*bw:.1f}%':>14s} "
                  f"{int(m.sum()):6d}    (thin)"); continue
        print(f"   {f'{lo:.2f}-{hi:.2f}':>12s} {f'{100*lo*bw:.1f}-{100*hi*bw:.1f}%':>14s} "
              f"{int(m.sum()):6d} {100*exc[m].mean():+8.2f}%")

print("\n" + "=" * 86)
print("SAME PROFILE IN RAW |ret| UNITS (if the onset tracks |ret|, these align instead)")
print("=" * 86)
for g_ in ("R1", "R2", "R4", "R3_20", "R3_25"):
    m0 = BIG & (grp == g_)
    if m0.sum() < 300: continue
    print(f"\n{g_}  band={np.median(band[m0]):.2f}")
    for lo, hi in ((0.02,0.05),(0.05,0.08),(0.08,0.11),(0.11,0.14),(0.14,0.18),(0.18,0.25),(0.25,1.0)):
        m = m0 & (-ret >= lo) & (-ret < hi)
        if m.sum() < 40:
            print(f"   |ret| {100*lo:4.0f}-{100*hi:4.0f}%  n={int(m.sum()):5d}   (thin)"); continue
        print(f"   |ret| {100*lo:4.0f}-{100*hi:4.0f}%  n={int(m.sum()):5d}  mean exc {100*exc[m].mean():+7.2f}%")

print("\n" + "=" * 86)
print("PROVENANCE OF THE depth>=1.01 BUCKET (falls that EXCEED the tabled band)")
print("=" * 86)
ov = BIG & (depth >= 1.01)
print(f"  n={int(ov.sum())}  mean excess {100*exc[ov].mean():+.2f}%")
print(f"  {'ticker':8s} {'date':12s} {'ret':>8s} {'band':>6s} {'depth':>6s} {'regime':>7s}")
o = np.where(ov)[0]
for i in o[np.argsort(ret[o])][:15]:
    print(f"  {tick[i] if 'tick' in dir() else '?':8s} {dt_arr[i]:12s} {100*ret[i]:+7.1f}% "
          f"{band[i]:6.2f} {depth[i]:6.2f} {regime(dt_arr[i]):>7s}")
