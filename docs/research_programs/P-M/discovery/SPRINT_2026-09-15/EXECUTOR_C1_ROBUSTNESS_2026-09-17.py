#!/usr/bin/env python3
"""EXECUTOR round-2 — independent reproduction of the reviewer's adverse evidence
on C1 (band contact vs depth-matched near-miss):

  R-A  cutoff purification: at-band cut in {0.95, 0.97, 0.99} x near-miss window
       in {0.70-cut, 0.80-cut, 0.85-cut, 0.90-cut} (+ the executor's original
       0.85-0.95 and 0.90-0.95 cells at cut 0.95). Day-collapsed NW(20).
  R-B  min_each sensitivity on the headline cell (1/2/3/5).
  R-C  depth-bin profile: mean excess per depth bin against a FIXED 0.70-0.85
       baseline bin, with NW(20) t of (bin - baseline) on the daily difference.

Same admissible-event construction as EXECUTOR_C1_DAYCOLLAPSED_2026-09-17.py
(both split tables unioned, suspension pad +/-20, liquidity floor Rp1e9, price
floor 50, positional 21d forward, entry next close). Output to stdout.
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


def nw_se(x, L):
    x = np.asarray(x, dtype=float)
    n = len(x)
    e = x - x.mean()
    g = e @ e / n
    for l in range(1, min(L, n - 1) + 1):
        w = 1.0 - l / (L + 1.0)
        g += 2.0 * w * (e[l:] @ e[:-l]) / n
    s2 = g
    if s2 <= 0:
        return np.nan
    return float(np.sqrt(s2 / n))


def day_diff(mask_a, mask_b, min_each=1):
    dates, vals = [], []
    for d in sorted(set(dt_arr[mask_a]) & set(dt_arr[mask_b])):
        a = exc[mask_a & (dt_arr == d)]
        b = exc[mask_b & (dt_arr == d)]
        if len(a) >= min_each and len(b) >= min_each:
            dates.append(d)
            vals.append(a.mean() - b.mean())
    return np.array(dates), np.array(vals)


def rd(cut, lo, hi, min_each=1):
    a = (ret <= -0.02) & (depth >= cut)
    b = (ret <= -0.02) & (depth >= lo) & (depth < min(hi, cut))
    dts, s = day_diff(a, b, min_each)
    if len(s) < 10:
        return None
    t = s.mean() / nw_se(s, 20) if nw_se(s, 20) > 0 else np.nan
    return len(s), float(s.mean()), float(t)


print("=== R-A  CUTOFF PURIFICATION (day-collapsed NW(20)) ===")
print("  cut   near-miss window   dates   day-mean    NW(20) t")
rows_out = []
for cut in (0.95, 0.97, 0.99):
    for lo, hi, lab in ((0.70, cut, "0.70-cut"), (0.80, cut, "0.80-cut"),
                        (0.85, cut, "0.85-cut"), (0.90, cut, "0.90-cut"),
                        (0.85, 0.95, "0.85-0.95"), (0.90, 0.95, "0.90-0.95")):
        if lo >= min(hi, cut):
            continue
        rr = rd(cut, lo, hi)
        if rr is None:
            print(f"   {cut:.2f}  {lab:12s}   dates<10")
            continue
        n_, m_, t_ = rr
        rows_out.append({"cut": cut, "lo": lo, "hi": hi, "lab": lab,
                         "dates": n_, "day_mean": m_, "nw_t": t_})
        print(f"   {cut:.2f}  {lab:12s}   {n_:5d}   {m_:+7.2f}%   {t_:+6.2f}")

print("\n=== R-B  MIN_EACH SENSITIVITY (cut 0.95, near-miss 0.85-0.95) ===")
a = (ret <= -0.02) & (depth >= 0.95)
b = (ret <= -0.02) & (depth >= 0.85) & (depth < 0.95)
for me in (1, 2, 3, 5):
    rr = rd(0.95, 0.85, 0.95, me)
    if rr is None:
        print(f"  min_each={me}: dates<10")
        continue
    n_, m_, t_ = rr
    print(f"  min_each={me}: dates={n_:4d}  day-mean={m_:+7.2f}%  NW(20) t={t_:+6.2f}")

print("\n=== R-C  DEPTH-BIN PROFILE vs FIXED 0.70-0.85 BASELINE ===")
big = (ret <= -0.02) & mask_ok if False else (ret <= -0.02)
bins = [(0.70, 0.80), (0.80, 0.85), (0.85, 0.90), (0.90, 0.95),
        (0.95, 0.97), (0.97, 0.99), (0.99, 1.01), (1.01, 99.0)]
bl_mask = (ret <= -0.02) & (depth >= 0.70) & (depth < 0.85)
base_mu = float(exc[bl_mask].mean())
base_daily = {}
for d in sorted(set(dt_arr[bl_mask])):
    v = exc[bl_mask & (dt_arr == d)]
    if len(v):
        base_daily[d] = v.mean()
print(f"  baseline 0.70-0.85: n={int(bl_mask.sum())} mean excess={base_mu:+.4f}")
for lo, hi in bins:
    sel = (ret <= -0.02) & (depth >= lo) & (depth < hi)
    n = int(sel.sum())
    if n < 8:
        print(f"  depth {lo:.2f}-{hi:.2f}: n={n}  (too few)")
        continue
    mu = float(exc[sel].mean())
    # daily (bin - baseline) on shared dates, NW(20)
    ds, dv = [], []
    for d in sorted(set(dt_arr[sel])):
        vb = exc[sel & (dt_arr == d)]
        vb = vb[~np.isnan(vb)]
        if d in base_daily and len(vb):
            ds.append(d)
            dv.append(vb.mean() - base_daily[d])
    t_nw = (np.array(dv).mean() / nw_se(dv, 20)) if len(dv) > 10 and nw_se(dv, 20) > 0 else np.nan
    print(f"  depth {lo:.2f}-{hi:.2f}: n={n:6d}  mean excess={mu:+8.4f}  "
          f"vs baseline {100*(mu-base_mu):+6.2f}%  NW(20) t(diff)={t_nw:+6.2f}")
