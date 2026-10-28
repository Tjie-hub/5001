#!/usr/bin/env python3
"""G1 for the {FQ} E/P arm (D-112): the one pre-registered test. Runs ONCE, after registration.

Implements G0_FREEZE_FQ_EP_2026-10-26.md §4 (portfolios, returns, statistic, costs) and §6 (sensitivities), on the
panel built by g0_fq_ep_breadth.py. It refuses to run until the registration record's sha256 is pinned below, so no
return is computed before the hypothesis is registered and counted (census N = 614).

    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 docs/research_programs/P-M/fq/g1_fq_ep.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from math import sqrt
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("g0_fq_ep_breadth", HERE / "g0_fq_ep_breadth.py")
G0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G0)

REG = HERE / "HYP-PM-0023_REGISTERED.md"
REG_SHA256 = "7155e1c739c890379b23382180271734173fc2de8ff4de22bf782b4bece9847b"              # HYP-PM-0023 registration, 2026-10-28 (D-115)

# ---- frozen parameters (G0 freeze §4) ----
NW_LAGS = 6
COST_RT = 0.006                            # 0.60% round trip
MECH_DROP = -0.95                          # D-065 v2 §2: excluded from means, reported separately
SPLIT_K_HI, SPLIT_K_LO, SPLIT_TOL = 1.5, 0.67, 0.25
ERA_SPLIT = date(2021, 7, 1)
# formation dates whose TTM can use a D-111 covered period: Q3-2024 (the first) is usable from 30 Nov 2024 (a
# Saturday), so the first such month-end is December 2024
COVERED = (date(2024, 12, 1), date(2026, 8, 31))


def _whole_ratio(k):
    """True if k or 1/k is within 2% of a whole number >= 2 (IDX splits/consolidations; rights issues rarely are)."""
    x = k if k >= 1 else 1 / k
    n = round(x)
    return n >= 2 and abs(x / n - 1) <= 0.02


def is_split(p0, s0, p1, s1):
    if not p0 or p0 <= 0 or p1 is None or not s0 or not s1:
        return False
    k = s1 / s0
    return (k >= SPLIT_K_HI or k <= SPLIT_K_LO) and _whole_ratio(k) and abs(p1 / p0 * k - 1) <= SPLIT_TOL


def split_adjusted_return(p0, s0, p1, s1):
    """Price return D -> D+1. A share-count jump by a whole ratio with the inverse price move (within 25%) is a
    split/consolidation and is adjusted; any other share-count change (issuance, rights) is not (G0 §4)."""
    if not p0 or p0 <= 0 or p1 is None:
        return None
    raw = p1 / p0
    return raw * (s1 / s0) - 1 if is_split(p0, s0, p1, s1) else raw - 1


def newey_west(x, lags=NW_LAGS):
    """Mean, Newey-West SE (Bartlett weights) and t of a 1-D series."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    e = x - m
    s = e @ e / n
    for lag in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - lag / (lags + 1)) * (e[lag:] @ e[:-lag]) / n
    se = sqrt(s / n)
    return m, se, (m / se if se > 0 else float("nan"))


def latest_equity(D, qs):
    """Statement equity (IDR) of the most recent quarter usable at D, unwithheld, classified, within the cap."""
    cutoff = G0.add_months_eom(D, -G0.STALE_MONTHS)
    for pe in sorted(qs, reverse=True):
        q = qs[pe]
        if pe < cutoff:
            return None
        if q["qual"] is None or q["qual"] > D or q["withheld"] or q["ccy"] is None or not q.get("equity"):
            continue
        return q["equity"] * q["rate"]
    return None


def signal(kind, D, qs, mcap):
    ttm, _ = G0.ttm_at(D, qs)
    if kind == "ep":
        return ttm / mcap if ttm is not None and ttm > 0 else None
    eq = latest_equity(D, qs)
    if kind == "bm":
        return eq / mcap if eq and eq > 0 else None
    if kind == "roe":
        return ttm / eq if ttm is not None and eq and eq > 0 else None
    raise ValueError(kind)


def form(D, uni, fin, kind="ep", weight="vw", exclude_usd=False):
    """Top and bottom tercile weights at D. uni: [(ticker, mcap)]. Returns (high, low) dicts ticker -> weight."""
    vals = []
    for t, mcap in uni:
        qs = fin.get(t)
        if not qs:
            continue
        if exclude_usd and any(q["ccy"] == "USD" for pe, q in qs.items()
                               if q["qual"] and q["qual"] <= D and pe >= G0.add_months_eom(D, -12)):
            continue
        v = signal(kind, D, qs, mcap)
        if v is not None:
            vals.append((v, t, mcap))
    vals.sort()
    k = len(vals) // 3
    if k == 0:
        return {}, {}
    def weights(leg):
        if weight == "ew":
            return {t: 1 / len(leg) for _, t, _ in leg}
        tot = sum(m for _, _, m in leg)
        return {t: m / tot for _, t, m in leg}
    return weights(vals[-k:]), weights(vals[:k])


def leg_return(w, rows_d, rows_n, delist_minus100=False, splits=None):
    """Weighted D -> D+1 return of one leg; returns (ret, dropped) with mechanical drops excluded and renormalised.
    Split-adjusted names are appended to `splits` (listed in the result for inspection)."""
    tot = wsum = 0.0
    dropped = []
    for t, wt in w.items():
        s0, p0 = rows_d[t]
        if t not in rows_n:
            r = -1.0 if delist_minus100 else 0.0   # exit at the last KSEI print (D)
        else:
            s1, p1 = rows_n[t]
            if splits is not None and is_split(p0, s0, p1, s1):
                splits.append(t)
            r = split_adjusted_return(p0, s0, p1, s1)
            if r is None:
                continue
            if r < MECH_DROP:
                dropped.append(t)
                continue
        tot += wt * r
        wsum += wt
    return (tot / wsum if wsum else None), dropped


def turnover(prev, cur):
    names = set(prev) | set(cur)
    return 0.5 * sum(abs(cur.get(t, 0.0) - prev.get(t, 0.0)) for t in names)


def run_variant(by_date, fin, kind="ep", weight="vw", top_n=None, exclude_usd=False, delist_minus100=False,
                keep=lambda D: True):
    dates = sorted(by_date)
    kdate = {(d.year, d.month): d for d in dates}
    for qs in fin.values():
        for q in qs.values():
            q["qual"] = G0.first_qualifying(q["deadline"], kdate) if q["deadline"] else None
    forms = [d for d in dates if G0.FIRST_D <= (d.year, d.month) <= G0.LAST_D and keep(d)]
    idx = {d: i for i, d in enumerate(dates)}
    old_top = G0.TOP_N
    if top_n:
        G0.TOP_N = top_n
    try:
        series, dropped, tos, legs, split_rows = [], [], [], [], []
        prev_h, prev_l = {}, {}
        for D in forms:
            i = idx[D]
            if i + 1 >= len(dates):
                continue
            m1 = by_date[dates[i - 1]] if i >= 1 else {}
            m2 = by_date[dates[i - 2]] if i >= 2 else {}
            uni = G0.universe_at(by_date[D], m1, m2)
            hi, lo = form(D, uni, fin, kind, weight, exclude_usd)
            if not hi:
                continue
            sp: list = []
            rh, dh = leg_return(hi, by_date[D], by_date[dates[i + 1]], delist_minus100, sp)
            rl, dl = leg_return(lo, by_date[D], by_date[dates[i + 1]], delist_minus100, sp)
            split_rows += [(D.isoformat(), t) for t in sp]
            if rh is None or rl is None:
                continue
            series.append((D.isoformat(), rh - rl))
            dropped += [(D.isoformat(), t) for t in dh + dl]
            tos.append(turnover(prev_h, hi) + turnover(prev_l, lo))
            legs.append((D.isoformat(), len(hi), len(lo)))
            prev_h, prev_l = hi, lo
    finally:
        G0.TOP_N = old_top
    x = [r for _, r in series]
    if len(x) < 3:
        return {"n_months": len(x)}
    m, se, t = newey_west(x)
    to = float(np.mean(tos[1:])) if len(tos) > 1 else None
    net = m - COST_RT * to if to is not None else None
    return {"n_months": len(x), "mean_monthly": m, "nw_se": se, "t": t, "turnover_monthly": to,
            "net_mean_monthly": net, "net_t": (net / se if net is not None and se > 0 else None),
            "dropped_mech": dropped, "split_adjusted": split_rows, "legs": legs, "series": series}


def main(argv=None) -> int:
    if REG_SHA256 is None or not REG.exists() or hashlib.sha256(REG.read_bytes()).hexdigest() != REG_SHA256:
        print("Registration not pinned or changed; refusing to run (no return is computed before registration).")
        return 2
    yahoo = G0.load_yahoo()
    by_date = G0.load_ksei()
    mk = lambda: G0.load_fin(withheld=G0.load_withheld(), fyx=G0.load_fyx(), yahoo=yahoo)
    primary = run_variant(by_date, mk())
    passed = primary.get("t", float("-inf")) >= G0.BAR
    sens = {
        "bm": run_variant(by_date, mk(), kind="bm"),
        "roe": run_variant(by_date, mk(), kind="roe"),
        "ew": run_variant(by_date, mk(), weight="ew"),
        "delist_minus100": run_variant(by_date, mk(), delist_minus100=True),
        "pre_2021_07": run_variant(by_date, mk(), keep=lambda D: D < ERA_SPLIT),
        "post_2021_07": run_variant(by_date, mk(), keep=lambda D: D >= ERA_SPLIT),
        "without_covered_window": run_variant(by_date, mk(), keep=lambda D: not (COVERED[0] <= D <= COVERED[1])),
        "usd_excluded": run_variant(by_date, mk(), exclude_usd=True),
        "top_100": run_variant(by_date, mk(), top_n=100),
    }
    res = {"hypothesis": "HYP-PM-0023", "registration_sha256": REG_SHA256, "bar": G0.BAR,
           "primary": primary, "passed_one_sided": passed,
           "sensitivities": {k: {kk: v.get(kk) for kk in ("n_months", "mean_monthly", "t", "net_mean_monthly")}
                             for k, v in sens.items()}}
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%dT%H%M%S")
    out = HERE / f"G1_RESULT_{stamp}.json"
    out.write_text(json.dumps(res, indent=1, default=str))
    print(f"G1 E/P: {primary.get('n_months')} months, mean {primary.get('mean_monthly', float('nan')):.4%}/mo, "
          f"NW t {primary.get('t', float('nan')):.2f} vs bar {G0.BAR:.4f} -> {'PASS' if passed else 'FAIL'}; "
          f"{out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
