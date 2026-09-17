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

# ============ REVIEWER ROBUSTNESS CHECK v2 (corrected regime/tier handling) ============
# v1 reconstructed "price tier" from band width. WRONG: arb_band is REGIME-dependent
# (R1 .07, R2 .15, R3 price-tiered, R4 .15), so band==0.20 conflates regimes. Here the
# regime comes from the date (exact) and the price tier is read from the band ONLY
# inside R3, where band<->tier is bijective.
def nw_t_of(s, L=20):
    s = np.asarray(s, float)
    if len(s) < 12: return np.nan
    e = s - s.mean(); n = len(s); g = e @ e / n
    for l in range(1, min(L, n - 1) + 1):
        g += 2.0 * (1.0 - l / (L + 1.0)) * (e[l:] @ e[:-l]) / n
    return float(s.mean() / np.sqrt(g / n)) if g > 0 else np.nan

def daydiff(ma, mb, min_each=1):
    out = []
    for d in sorted(set(dt_arr[ma]) & set(dt_arr[mb])):
        a = exc[ma & (dt_arr == d)]; b = exc[mb & (dt_arr == d)]
        if len(a) >= min_each and len(b) >= min_each:
            out.append(a.mean() - b.mean())
    return np.array(out)

reg = np.array([regime(d) for d in dt_arr])
BIG = ret <= -0.02
atb  = BIG & (depth >= 0.95)
near = BIG & (depth >= 0.85) & (depth < 0.95)

print("\n" + "=" * 80)
print("REVIEWER ROBUSTNESS CHECK v2 ON EXECUTOR C1")
print("=" * 80)

print("\nR-1a  REGIME BALANCE, at-band vs near-miss")
print(f"  {'regime':8s} {'band':>6s} {'at-band':>10s} {'near-miss':>10s} {'shift':>8s}")
for rg in ("R1", "R2", "R3", "R4"):
    pa = (reg[atb] == rg).mean(); pb = (reg[near] == rg).mean()
    bw = {"R1": ".07", "R2": ".15", "R3": "tier", "R4": ".15"}[rg]
    print(f"  {rg:8s} {bw:>6s} {100*pa:9.1f}% {100*pb:9.1f}% {100*(pa-pb):+7.1f}pp")

print("\n  WITHIN-REGIME contrast:")
for rg in ("R1", "R2", "R3", "R4"):
    s = daydiff(atb & (reg == rg), near & (reg == rg))
    na, nb = int((atb & (reg == rg)).sum()), int((near & (reg == rg)).sum())
    if len(s) < 12:
        print(f"    {rg:4s} dates={len(s):4d}  (too few)   events {na} vs {nb}"); continue
    print(f"    {rg:4s} dates={len(s):4d}  day-mean {100*s.mean():+6.2f}%  "
          f"NW(20) t={nw_t_of(s):+6.2f}   events {na} vs {nb}")

print("\nR-1b  PRICE-TIER BALANCE within R3 only (band<->tier bijective there)")
in3 = reg == "R3"
tier3 = np.where(band > 0.30, "<=200", np.where(band > 0.22, "200-5000", ">5000"))
print(f"  {'tier':12s} {'at-band':>10s} {'near-miss':>10s} {'shift':>8s}")
for tg in ("<=200", "200-5000", ">5000"):
    ma, mb = atb & in3, near & in3
    if ma.sum() == 0 or mb.sum() == 0: continue
    pa = (tier3[ma] == tg).mean(); pb = (tier3[mb] == tg).mean()
    print(f"  {tg:12s} {100*pa:9.1f}% {100*pb:9.1f}% {100*(pa-pb):+7.1f}pp")

print("\nR-2b  BANDWIDTH SENSITIVITY with event counts")
print(f"  {'cut':>5s} {'window':>12s} {'n_atband':>9s} {'n_near':>8s} {'dates':>6s} "
      f"{'day-mean':>9s} {'NW t':>7s}")
for cut in (0.95, 0.97, 0.99):
    for lo in (0.85, 0.90):
        a = BIG & (depth >= cut); b = BIG & (depth >= lo) & (depth < cut)
        s = daydiff(a, b)
        print(f"  {cut:5.2f} {f'{lo:.2f}-{cut:.2f}':>12s} {int(a.sum()):9d} {int(b.sum()):8d} "
              f"{len(s):6d} {100*s.mean():+8.2f}% {nw_t_of(s):+7.2f}"
              if len(s) >= 12 else
              f"  {cut:5.2f} {f'{lo:.2f}-{cut:.2f}':>12s} {int(a.sum()):9d} {int(b.sum()):8d}  (too few)")

print("\nR-5  IS THE JUMP AT THE BAND, OR AT THE ANALYST'S 0.95 THRESHOLD?")
print("     mean excess by depth bin (all big falls), to locate any discontinuity")
edges = [(0.5,0.7),(0.7,0.8),(0.8,0.85),(0.85,0.90),(0.90,0.95),(0.95,0.97),(0.97,0.99),(0.99,1.01),(1.01,9)]
for lo, hi in edges:
    m = BIG & (depth >= lo) & (depth < hi)
    if m.sum() < 30:
        print(f"  depth [{lo:.2f},{hi:.2f}) n={int(m.sum()):5d}  (too few)"); continue
    dd = daydiff(m, BIG & (depth >= 0.70) & (depth < 0.85))
    print(f"  depth [{lo:.2f},{hi:.2f}) n={int(m.sum()):5d}  mean excess {100*exc[m].mean():+6.2f}%"
          f"   vs 0.70-0.85 baseline: {100*dd.mean():+6.2f}% t={nw_t_of(dd):+6.2f}" if len(dd) >= 12
          else f"  depth [{lo:.2f},{hi:.2f}) n={int(m.sum()):5d}  mean excess {100*exc[m].mean():+6.2f}%")
