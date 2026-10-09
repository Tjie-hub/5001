"""Cost-model audit for liquid names (Task A) — READ-ONLY.

Measures the REALISED spread from the 5001 `ticks` trade prints and compares
it with D-059's Abdi-Ranaldo (AR) spread + 1-tick floor + impact, by ADV
bucket (D-059's own bucket edges) and day-type.

ESTIMATOR (stated): Roll (1984) on tick data — 2*sqrt(-mean within-day
first-order autocovariance of dlog p) over 1-minute prints, per name, pooled
per (bucket, day-type) cell, floored at the name's median 1-tick/close —
exactly D-059's own validation convention (cost_by_adv.validate / roll_spread
/ day_autocov, imported from the frozen module, not re-implemented). The
Lee-Ready/tick-test signed effective spread is NOT used: the corpus has no
quotes (ticks = prints only; tick_type is the exchange direction marker), and
a signed effective spread needs a quote midpoint — with a price-change proxy
it would be a noisy transform of the same information Roll already extracts.

Day types (pre-defined, market-data only — no strategy outcome anywhere):
  normal    — all ticks sessions not in the two below
  wide      — top decile of daily EW-market |r| (mean |close-to-close return|
              across names with volume > 0) over the ticks window
  stress    — the 63 D-079 stress first-days (STRESS_DATES.json; dates only,
              no returns read; 3 fall inside the ticks window 2026-04-18..)

Streaming: one session at a time over the ticks table (indexed on date,
ticker) — the full table does not fit in memory. All reads mode=ro on the
pinned 2026-10-08 snapshot. Recomputes COSTS ONLY, never any R.

Run: venv/bin/python docs/research_programs/P-M/cost_audit/cost_audit.py
Writes COST_AUDIT.json next to this file.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SNAP = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"
FEES = 0.005
Q = 100e6  # D-059 primary size
BUCKETS = [("1-2bn", 1e9, 2e9), ("2-5bn", 2e9, 5e9), ("5-20bn", 5e9, 20e9),
           ("20-100bn", 20e9, 100e9), (">100bn", 100e9, np.inf)]

_spec = importlib.util.spec_from_file_location(
    "cost_by_adv", HERE.parents[0] / "cost_liquidity" / "cost_by_adv.py")
CB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CB)


def pd_(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def load_ca(conn):
    fac = {}
    for at in ("stocksplit", "bonus", "stock_reverse"):
        for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                                  "WHERE action_type=?", (at,)).fetchall():
            j = json.loads(rj)
            d = pd_(j.get("stocksplit_exdate"))
            if d is None:
                continue
            try:
                f = (float(j.get("stocksplit_factor")) if at == "bonus"
                     else float(j.get("stocksplit_new")) / float(j.get("stocksplit_old")))
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if f and f > 0:
                fac.setdefault(t, []).append((d, f))
    return fac


def f_cum(fac, t, d):
    p = 1.0
    for de, f in fac.get(t, ()):
        if de > d:
            p *= f
    return p


def bucket_of(adv):
    for name, lo, hi in BUCKETS:
        if lo <= adv < hi:
            return name
    return None


def main() -> None:
    t0 = time.time()
    conn = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
    ticks_lo, ticks_hi = conn.execute("SELECT MIN(date), MAX(date) FROM ticks").fetchone()

    # ---- ohlcv features over a window with 21+ sessions of history before ticks_lo
    win_lo = "2026-01-05"
    d = pd.read_sql("SELECT ticker, date, high, low, close, volume FROM ohlcv "
                    "WHERE COALESCE(is_final,1)=1 AND date >= ? AND date <= ?",
                    conn, params=(win_lo, ticks_hi))
    d = d[d.volume > 0].copy()
    fac = load_ca(conn)
    d["f"] = [f_cum(fac, t, pd_(x)) for t, x in zip(d.ticker, d.date)]
    d["rupiah"] = d.close * d.volume
    d["rupiah_true"] = d.close * d.f * d.volume

    feats = []
    for t, x in d.groupby("ticker", sort=False):
        x = x.sort_values("date")
        term = pd.Series(CB.ar_terms(x.close.values, x.high.values, x.low.values), index=x.index)
        avail = term.shift(1)
        m = avail.rolling(20, min_periods=20).mean().shift(1)
        s_ar = np.sqrt(m.clip(lower=0))
        sig = np.log(x.close).diff().rolling(20, min_periods=20).std().shift(1)
        adv20 = x.rupiah_true.rolling(20, min_periods=20).mean().shift(1)
        adv20_naive = x.rupiah.rolling(20, min_periods=20).mean().shift(1)
        floor = pd.Series(CB.tick_size(x.close.values) / x.close.values, index=x.index)
        f2 = pd.DataFrame({"ticker": t, "date": x.date, "s_ar": s_ar, "sig_d": sig,
                           "adv20": adv20, "adv20_naive": adv20_naive,
                           "tick_floor": floor}).dropna(subset=["adv20"])
        feats.append(f2)
    F = pd.concat(feats, ignore_index=True)
    F["s"] = np.maximum(F.s_ar, F.tick_floor)          # D-059 floored spread
    F["impact"] = 2 * F.sig_d * np.sqrt(Q / F.adv20)

    # ---- EW-market |r| per session -> wide-range days (top decile, pre-defined)
    d2 = d.sort_values(["ticker", "date"])
    d2["r"] = d2.groupby("ticker").close.pct_change()
    ew_absr = d2[["date", "r"]].dropna().groupby("date").r.apply(lambda s: s.abs().mean())
    ew_window = ew_absr[(ew_absr.index >= ticks_lo) & (ew_absr.index <= ticks_hi)]
    wide_days = set(ew_window[ew_window >= ew_window.quantile(0.9)].index)

    stress_dates = set(x for x in json.loads((HERE / "STRESS_DATES.json").read_text())["dates"]
                       if ticks_lo <= x <= ticks_hi)

    def daytype(x):
        if x in stress_dates:
            return "stress"
        if x in wide_days:
            return "wide"
        return "normal"

    F["daytype"] = [daytype(x) for x in F.date]

    # ---- stream ticks per session; per (ticker, date): within-day autocov of dlog p
    dates = [r[0] for r in conn.execute("SELECT DISTINCT date FROM ticks ORDER BY date")]
    covs = defaultdict(list)          # (ticker, date) -> cov
    nprints = {}
    for dt in dates:
        x = pd.read_sql("SELECT ticker, time, price FROM ticks WHERE date=? AND price>0",
                        conn, params=(dt,))
        x = x.sort_values(["ticker", "time"])
        x["lp"] = np.log(x.price.astype(float))
        for t, v in x.groupby("ticker", sort=False).lp:
            cv = CB.day_autocov(v.values)
            covs[(t, dt)].append(cv)
            nprints[(t, dt)] = len(v)
    conn.close()

    rows = []
    cov_df = pd.DataFrame([{"ticker": t, "date": dt, "cov": v[0] if v else np.nan,
                            "n": nprints.get((t, dt), 0)}
                           for (t, dt), v in covs.items()])
    M = cov_df.merge(F, on=["ticker", "date"], how="inner")
    M = M[M.n >= 10]                                   # day_autocov needs >= 10 changes
    M["bucket"] = [bucket_of(a) for a in M.adv20]
    M = M.dropna(subset=["bucket"])
    summary = {}
    for (bk, dt_), g in M.groupby(["bucket", "daytype"]):
        min_nd = 2 if dt_ == "stress" else 5   # only 3 stress days exist in the ticks window
        per_name_roll = {}
        for t, gg in g.groupby("ticker"):
            if len(gg) < min_nd or gg["cov"].isna().all():
                continue
            m_cov = float(gg["cov"].mean())
            s_roll = 2 * np.sqrt(-m_cov) if m_cov < 0 else 0.0
            s_roll = max(s_roll, float(gg.tick_floor.median()))
            per_name_roll[t] = s_roll
        if not per_name_roll:
            summary[f"{bk}|{dt_}"] = {"name_days": int(len(g)), "names_roll": 0}
            continue
        rv = np.asarray(list(per_name_roll.values()))
        summary[f"{bk}|{dt_}"] = {
            "name_days": int(len(g)), "names_roll": len(rv),
            "s_roll_median": round(float(np.median(rv)), 6),
            "s_ar_median": round(float(g.s.median()), 6),
            "tick_floor_median": round(float(g.tick_floor.median()), 6),
            "sigma_d_median": round(float(g.sig_d.median()), 6),
            "impact_median": round(float(g.impact.median()), 6),
            "cost_ar_rt": round(FEES + float(g.s.median()) + float(g.impact.median()), 6),
            "cost_realised_rt": round(FEES + float(np.median(rv)) + float(g.impact.median()), 6),
            "ar_overstatement_ratio": round(float(g.s.median() / np.median(rv)), 2)
            if np.median(rv) > 0 else None,
        }
    # liquid names (>=10bn) on wide/stress days: the stress-basket decomposition cells
    liquid = {}
    for dt_ in ("normal", "wide", "stress"):
        g = M[(M.adv20 >= 1e10) & (M.daytype == dt_)]
        if not len(g):
            continue
        pn = {}
        for t, gg in g.groupby("ticker"):
            if len(gg) >= (2 if dt_ == "stress" else 3) and not gg["cov"].isna().all():
                mc = float(gg["cov"].mean())
                sr = 2 * np.sqrt(-mc) if mc < 0 else 0.0
                pn[t] = max(sr, float(gg.tick_floor.median()))
        if pn:
            rv = np.asarray(list(pn.values()))
            liquid[dt_] = {
                "names": len(rv), "name_days": int(len(g)),
                "s_roll_median": round(float(np.median(rv)), 6),
                "s_ar_median": round(float(g.s.median()), 6),
                "impact_median": round(float(g.impact.median()), 6),
                "fees": FEES,
                "cost_ar_rt": round(FEES + float(g.s.median()) + float(g.impact.median()), 6),
                "cost_realised_rt": round(FEES + float(np.median(rv)) + float(g.impact.median()), 6),
            }
    out = {
        "snapshot": {"path": SNAP,
                     "note": "pinned 2026-10-08 walkforward snapshot, read-only"},
        "ticks_window": [ticks_lo, ticks_hi], "n_ticks_sessions": len(dates),
        "estimator": ("Roll (1984) on 1-minute tick prints, D-059's own validation "
                      "convention (cost_by_adv validate/roll_spread/day_autocov imported "
                      "from the frozen module); Lee-Ready NOT used - no quotes in corpus"),
        "wide_range_rule": ("top decile of daily EW-market |r| (all names volume>0) over "
                            f"the ticks window; {len(wide_days)} days: "
                            + ", ".join(sorted(wide_days))),
        "stress_days_in_window": sorted(stress_dates),
        "buckets": "D-059 BUCKETS; adv20 = TRUE rupiah (close x f_cum x volume, 20 bars, "
                   "known at t-1); naive adv reported alongside in cells",
        "cells": summary,
        "liquid_ge10bn": liquid,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_minutes": round((time.time() - t0) / 60.0, 1),
    }
    (HERE / "COST_AUDIT.json").write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE COST_AUDIT.json")
    for k, v in summary.items():
        print(k, json.dumps(v))
    print("liquid_ge10bn:", json.dumps(liquid, indent=1))
    print("runtime_minutes:", out["runtime_minutes"])


if __name__ == "__main__":
    main()
