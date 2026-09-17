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


def day_diff_series(mask_a, mask_b, min_each=1):
    """Daily series of mean(exc|A) - mean(exc|B) on dates where both non-empty."""
    dates, vals = [], []
    for d in sorted(set(dt_arr[mask_a]) & set(dt_arr[mask_b])):
        a = exc[mask_a & (dt_arr == d)]
        b = exc[mask_b & (dt_arr == d)]
        if len(a) >= min_each and len(b) >= min_each:
            dates.append(d)
            vals.append(a.mean() - b.mean())
    return np.array(dates), np.array(vals)


def report_pair(name, mask_a, mask_b, pooled=False):
    if pooled:
        # event-weighted two-sample contrast, iid SE (the handover's form)
        a = exc[mask_a]; b = exc[mask_b]
        ev = a.mean() - b.mean()
        se = float(np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))
        print(f"  {name:44s} [POOLED-EVENT] events {len(a)}/{len(b)}  "
              f"contrast {100*ev:+6.2f}%  t_iid={ev/se:+6.2f}")
        return
    dts, s = day_diff_series(mask_a, mask_b)
    if len(s) < 10:
        print(f"  {name:44s} dates={len(s)}  (too few)")
        return
    se_nw = nw_se(s, 20)
    t = s.mean() / se_nw if se_nw and se_nw > 0 else np.nan
    a_all = exc[mask_a]; b_all = exc[mask_b]
    ev = a_all.mean() - b_all.mean()
    # lag-1 autocorr of the day series
    if len(s) > 2:
        r1c = np.corrcoef(s[:-1], s[1:])[0, 1]
    else:
        r1c = np.nan
    print(f"  {name:44s} dates={len(s):4d}  day-mean {100*s.mean():+6.2f}%  "
          f"NW(20) t={t:+6.2f}   rho1={r1c:+.2f}   event-w contrast {100*ev:+6.2f}% "
          f"(events {int(mask_a.sum())} vs {int(mask_b.sum())})")


atb = (ret <= -0.02) & (depth >= 0.95)
near = (ret <= -0.02) & (depth >= 0.85) & (depth < 0.95)
shal = (ret <= -0.02) & (depth < 0.85)

print("\n=== C1 DIFFERENCE-IN-MEANS, DAY-COLLAPSED + NW(20) ===")
report_pair("(a) at-band vs near-miss (85-95%)", atb, near)
report_pair("(b) at-band vs shallower big falls (<85%)", atb, shal)
report_pair("(c) at-band vs ALL other big falls", atb, (ret <= -0.02) & (depth < 0.95))
# also: near-miss vs shallow (the monotonicity claim inside C1)
report_pair("(d) near-miss vs shallow (monotonicity)", near, shal)

print("\n=== reference: pooled-event form (MEASURED, fixes executor defect 1) ===")
report_pair("(ref) at-band vs near-miss [pooled-event]", atb, near, pooled=True)
print("\n(split ex-dates unioned from both tables; suspension pad +/-20; "
      "liquidity floor Rp1e9; price floor 50; same construction as "
      "REVIEW_BAND_INDEP_SOURCE_2026-09-16.py)")
