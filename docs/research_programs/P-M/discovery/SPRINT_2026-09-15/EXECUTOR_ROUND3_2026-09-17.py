#!/usr/bin/env python3
"""EXECUTOR round-3 — blocking items 4a/4b/4c from the reviewer.

4a  at-band headline and C1 pairs EXCLUDING depth > 1.0 (contaminated tail);
    delta vs the including form reported.
4b  identification and classification of the depth >= 1.01 rows (ticker, date,
    ret, band, depth; nearest corporate_action_event action_type and lag;
    verdict on CA-type union vs band-tied magnitude guard).
4c  redundancy: monthly overlap between the depth>=0.90 / >=0.95 fall-event
    ticker sets and the LIVE FWD-PM-VOLEX-001 Parkinson-60 top-decile
    exclusion set (top-200 liquid universe per run_forward.py).
Output to stdout (captured by shell redirection).
"""
import sys, os, json, sqlite3
from collections import defaultdict
import numpy as np
import pandas as pd

DB = "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db"
K, LIQ, PMIN, PAD, TOUCH = 21, 1e9, 50.0, 20, 0.95
PARK_WIN = 60

con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)

# ---- CA events: ALL action types, from the events table (richest source) ----
ca_rows = con.execute("SELECT ticker, event_date, action_type FROM corporate_action_events "
                      "WHERE event_date IS NOT NULL").fetchall()
ca_all = defaultdict(list)   # ticker -> [(date_iso, action_type)]
for t, ed, at in ca_rows:
    d = str(ed)[:10]
    if len(d) != 10:
        continue
    ca_all[t].append((d, str(at)))

splits = defaultdict(set)
for t, dt in con.execute("SELECT ticker,date FROM corporate_actions WHERE action=?", ("split",)):
    splits[t].add(str(dt)[:10])
for t, j in con.execute("SELECT ticker,raw_json FROM corporate_action_events "
                        "WHERE action_type IN (?,?,?)",
                        ("stocksplit", "stock_reverse", "bonus")):
    try:
        ex = str(json.loads(j).get("stocksplit_exdate") or "")[:10]
        if len(ex) == 10:
            splits[t].add(ex)
    except Exception:
        pass
n_split_union = sum(len(v) for v in splits.values())

susp = defaultdict(list)
for t, a, b in con.execute("SELECT ticker,last_normal_date,resume_date FROM suspension_events"):
    susp[t].append((str(a)[:10], str(b or a)[:10]))

rows = con.execute("SELECT ticker,date,close,volume,high,low FROM ohlcv WHERE is_final=1 "
                   "AND date>='2021-07-01' AND date<='2026-09-13' AND close>0 "
                   "ORDER BY ticker,date")
by_t = defaultdict(list)
for t, dt, c, v, h, l in rows:
    by_t[t].append((str(dt)[:10], float(c), float(v or 0), float(h or 0), float(l or 0)))
con.close()


def regime(day):
    if "2021-07-05" <= day <= "2023-06-04": return "R1"
    if "2023-06-05" <= day <= "2023-09-01": return "R2"
    if "2023-09-04" <= day <= "2025-04-07": return "R3"
    if day >= "2025-04-08":                 return "R4"
    return None


def tier_band(pc):
    if pc <= 200:  return 0.35
    if pc > 5000:  return 0.20
    return 0.25


def arb_band(day, pc):
    rg = regime(day)
    if rg == "R1": return 0.07
    if rg == "R2": return 0.15
    if rg == "R3": return tier_band(pc)
    if rg == "R4": return 0.15
    return None


recs = []
park_excl = defaultdict(set)   # ticker -> set of months inside the live overlay
park_months = set()
for t, series in by_t.items():
    n = len(series)
    if n < 100: continue
    days = [s[0] for s in series]
    close = np.array([s[1] for s in series])
    volu = np.array([s[2] for s in series])
    highs = np.array([s[3] for s in series])
    lows = np.array([s[4] for s in series])
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
    # Parkinson-60 (same formula as run_forward.py), on the same series
    with np.errstate(divide="ignore", invalid="ignore"):
        rl = np.log(highs / np.where(lows > 0, lows, np.nan)) ** 2
    pk = np.sqrt(pd.Series(rl).rolling(PARK_WIN, min_periods=PARK_WIN // 2).mean().values
                 / (4 * np.log(2)))

    # parkinson top-decile membership per month-end, top-200 liquid universe
    elig = []
    for i in range(PARK_WIN, n):
        if not np.isfinite(pk[i]) or volu[i] <= 0 or close[i] < PMIN or bad[i]:
            continue
        adv = np.median(tval[max(0, i - 60):i])
        if adv >= LIQ:
            elig.append((days[i], i, float(pk[i]), float(adv)))
    bymonth = defaultdict(list)
    for d, i, pkv, adv in elig:
        bymonth[d[:7]].append((pkv, t, d, adv))
    for mo, lst in bymonth.items():
        if len(lst) < 5:
            continue
        lst.sort(reverse=True)
        top200 = lst[:200]
        cut = top200[min(len(top200), 20) - 1][0]   # top decile of 200 = 20 names
        for pkv, t_, d_, _ in top200:
            if pkv >= cut:
                park_excl[t_].add(mo)

# ================= 4a / 4b / 4c =================
dt_arr = np.array([x[0] for x in recs])
tk_arr = np.array([x[1] for x in recs])
ret = np.array([x[2] for x in recs])
band = np.array([x[3] for x in recs])
fwd = np.array([x[4] for x in recs])

uni = defaultdict(list)
for d, f in zip(dt_arr, fwd): uni[d].append(f)
umean = {d: float(np.mean(v)) for d, v in uni.items() if len(v) >= 80}
keep = np.array([d in umean for d in dt_arr])
dt_arr, tk_arr, ret, band, fwd = (dt_arr[keep], tk_arr[keep], ret[keep],
                                  band[keep], fwd[keep])
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


def c1(name, mask_a, mask_b, min_each=1):
    dts, s = day_diff(mask_a, mask_b, min_each)
    if len(s) < 10:
        print(f"  {name:52s} dates={len(s)} (too few)")
        return
    se = nw_se(s, 20)
    t = s.mean() / se if se and se > 0 else np.nan
    print(f"  {name:52s} dates={len(s):4d}  day-mean {100*s.mean():+6.2f}%  NW(20) t={t:+6.2f}")


atb_all = (ret <= -0.02) & (depth >= 0.95)
atb_clean = (ret <= -0.02) & (depth >= 0.95) & (depth <= 1.0)
near = (ret <= -0.02) & (depth >= 0.85) & (depth < 0.95)
shal = (ret <= -0.02) & (depth < 0.85)
deep = atb_all & (depth > 1.0)

print("\n=== 4a  AT-BAND HEADLINE EXCLUDING depth>1.0 ===")
v_in = exc[atb_all]; v_cl = exc[atb_clean]; v_dp = exc[deep]
c1("at-band incl. deep tail", atb_all, near)
c1("at-band EXCL depth>1.0 (0.95-1.00)", atb_clean, near)
c1("C1(b) at-band-excl vs shallower (<85%)", atb_clean, shal)
c1("C1(c) at-band-excl vs ALL other big falls", atb_clean, (ret <= -0.02) & (depth < 0.95))
print(f"  incl n={len(v_in)} mean={100*v_in.mean():+.2f}% | excl-deep n={len(v_cl)} "
      f"mean={100*v_cl.mean():+.2f}% | deep tail n={int(deep.sum())} "
      f"mean={100*v_dp.mean():+.2f}%")

print("\n=== 4b  DEPTH >= 1.01 ROWS: identification and classification ===")
deep_rows = [(tk_arr[i], dt_arr[i], float(ret[i]), float(band[i]), float(depth[i]))
             for i in np.where(deep)[0]]
deep_rows.sort(key=lambda x: -x[4])
ca_hits = defaultdict(int)
unmatched = []
for t, d, r, bd, dp in deep_rows:
    best = None
    for ed, at in ca_all.get(t, []):
        lag = abs((np.datetime64(d) - np.datetime64(ed)).astype(int))
        if lag <= 10 and (best is None or lag < best[0]):
            best = (lag, at, ed)
    if best:
        ca_hits[best[1]] += 1
    else:
        unmatched.append((t, d, r, bd, dp))
print(f"  count: {len(deep_rows)}")
print(f"  with a CA event within +/-10 days: {len(deep_rows)-len(unmatched)}")
print(f"  action_type histogram: {dict(ca_hits)}")
import collections as _cl
ret_h = _cl.Counter(round(abs(r), 3) for _t, _d, r, _b, _dp in unmatched)
print(f"  unmatched |ret| histogram (top 8): {ret_h.most_common(8)}")
bd_h = _cl.Counter(round(bd, 2) for _t, _d, r, bd, _dp in unmatched)
print(f"  unmatched band histogram: {dict(sorted(bd_h.items()))}")
print(f"  WITHOUT any CA event nearby: {len(unmatched)}")
for t, d, r, bd, dp in unmatched[:15]:
    print(f"    {t:6s} {d}  ret={r:+.3f} band={bd:.2f} depth={dp:.2f}")

print("\n=== 4c  REDUNDANCY vs LIVE FWD-PM-VOLEX-001 OVERLAY ===")
for cut, lab in ((0.90, "depth>=0.90"), (0.95, "depth>=0.95")):
    sel = (ret <= -0.02) & (depth >= cut)
    sel_tk = tk_arr[sel]
    sel_dt = dt_arr[sel]
    fall_mo = defaultdict(set)
    for t, d in zip(sel_tk, sel_dt):
        fall_mo[d[:7]].add(t)
    tot_rows = []
    for mo in sorted(fall_mo):
        ft = fall_mo[mo]
        pt = {t for t, mos in park_excl.items() if mo in mos}
        tot_rows.append((mo, len(ft), len(pt), len(ft & pt)))
    inter_t = sum(r[3] for r in tot_rows)
    ft_t = sum(r[1] for r in tot_rows)
    distinct = len(set(tk_arr[sel]))
    ever_ov = sum(1 for t in set(sel_tk) if park_excl.get(t))
    print(f"  {lab}: distinct fall tickers={distinct}, "
          f"tickers ever inside overlay={ever_ov} ({ever_ov/max(1,distinct):.0%})")
    print(f"    ticker-months: fall={ft_t}, overlay-eligible months sum={sum(r[2] for r in tot_rows)}, "
          f"intersections={inter_t} (share={inter_t/max(1,ft_t):.1%})")
    sample = [(mo, nf, po, i) for mo, nf, po, i in tot_rows if nf >= 5][:8]
    print(f"    sample (mo, fall, overlay, inter): {sample}")
    shares = [i / nf for mo, nf, po, i in tot_rows if nf >= 3]
    if shares:
        print(f"    monthly overlap share of fall tickers: mean={np.mean(shares):.0%} "
              f"median={np.median(shares):.0%} over {len(shares)} months")

print("\n(executor round-3 complete)")
