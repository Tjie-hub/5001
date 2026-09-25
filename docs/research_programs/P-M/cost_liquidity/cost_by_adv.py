"""Trading cost by liquidity, and T1 (HYP-PM-0010, spec 002) reference trades net of it.

Model, sizes, buckets and interpretation are frozen in PREDECLARATION.md; do not edit them here.
  cost/round trip = 0.50% fees + (½ s_entry + ½ s_exit) + 2·σ_d·√(Q/adv20)
  s = Abdi-Ranaldo (2017) CHL spread, trailing 21 traded sessions, known at t-1, floored at 1 tick.
Validation: Roll (1984) spread from 1-minute `ticks` against Abdi-Ranaldo on the same names and dates.

DESCRIPTIVE ONLY. FWD-PM-REGIME-002's frozen endpoint and decision rule are unchanged.

    venv/bin/python docs/research_programs/P-M/cost_liquidity/cost_by_adv.py
"""
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OA_PATH = os.path.join(HERE, "..", "overlap_audit", "overlap_audit.py")
DATA_CUTOFF = "2026-09-16"
FEES = 0.005
FROZEN_RT = 0.006
SIZES = {"Q25m": 25e6, "Q100m": 100e6, "Q500m": 500e6}
PRIMARY_Q = "Q100m"
WIN = 21
BUCKETS = [(1e9, 2e9, "1-2bn"), (2e9, 5e9, "2-5bn"), (5e9, 20e9, "5-20bn"),
           (20e9, 100e9, "20-100bn"), (100e9, np.inf, ">100bn")]
PASS_BAR, FAIL_FLOOR, T_BAR = 0.55, 0.30, 2.0


def tick_size(price):
    p = np.asarray(price, float)
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25).astype(float)


def ar_terms(close, high, low):
    """Abdi-Ranaldo two-day term 4(c_t - η_t)(c_t - η_{t+1}), indexed at t (needs t+1)."""
    c = np.log(np.asarray(close, float))
    eta = (np.log(np.asarray(high, float)) + np.log(np.asarray(low, float))) / 2
    eta_next = np.r_[eta[1:], np.nan]
    return 4 * (c - eta) * (c - eta_next)


def ar_spread_from_terms(terms):
    m = np.nanmean(terms)
    return float(np.sqrt(m)) if m > 0 else 0.0


def day_autocov(lp):
    """Within-day first-order autocovariance of Δlog p; NaN if fewer than 10 changes."""
    dp = np.diff(np.asarray(lp, float))
    if len(dp) < 10:
        return np.nan
    dp = dp - dp.mean()
    return float(np.mean(dp[1:] * dp[:-1]))


def roll_from_covs(covs):
    covs = [v for v in covs if not np.isnan(v)]
    if not covs:
        return np.nan
    m = np.mean(covs)
    return float(2 * np.sqrt(-m)) if m < 0 else 0.0


def roll_spread(log_prices_by_day):
    """Pooled Roll spread: 2·sqrt(-mean within-day first-order autocovariance of Δlog p)."""
    return roll_from_covs([day_autocov(lp) for lp in log_prices_by_day])


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def per_day_liquidity(d):
    """Spread (AR, floored) and σ_d per name-day, from traded sessions t-21..t-1 only."""
    tr = d[d.volume > 0].copy()
    g = tr.groupby("ticker", sort=False)
    parts = []
    for _, x in g:
        term = pd.Series(ar_terms(x.close.values, x.high.values, x.low.values), index=x.index)
        # term_k needs session k+1: available from row k+1; window of the last WIN-1 pairs, all <= t-1
        avail = term.shift(1)
        m = avail.rolling(WIN - 1, min_periods=WIN - 1).mean().shift(1)
        lr = np.log(x.close).diff()
        sig = lr.rolling(WIN - 1, min_periods=WIN - 1).std().shift(1)
        parts.append(pd.DataFrame({"s_ar": np.sqrt(m.clip(lower=0)), "sig_d": sig}, index=x.index))
    liq = pd.concat(parts)
    out = d.join(liq)
    out[["s_ar", "sig_d"]] = out.groupby("ticker", sort=False)[["s_ar", "sig_d"]].ffill()
    out["tick_floor"] = tick_size(out.close) / out.close
    out["s"] = np.maximum(out.s_ar, out.tick_floor)
    return out


def bucket(adv):
    lab = pd.Series("<1bn", index=adv.index)
    for lo, hi, name in BUCKETS:
        lab[(adv >= lo) & (adv < hi)] = name
    return lab


def cost_table(L):
    U = L[L.liq & L.s.notna() & L.sig_d.notna()].copy()
    U["bucket"] = bucket(U.adv20)
    rows = {}
    for _, _, name in BUCKETS:
        b = U[U.bucket == name]
        r = {"name_days": int(len(b)), "median_spread_pct": round(100 * b.s.median(), 3),
             "median_tick_floor_pct": round(100 * b.tick_floor.median(), 3),
             "share_at_tick_floor": round(float((b.s_ar <= b.tick_floor).mean()), 3),
             "median_sigma_d_pct": round(100 * b.sig_d.median(), 2)}
        for q, Q in SIZES.items():
            r[f"median_impact_rt_pct_{q}"] = round(100 * (2 * b.sig_d * np.sqrt(Q / b.adv20)).median(), 3)
        rows[name] = r
    return rows


def validate(L):
    sys.path.insert(0, ROOT)
    from data.db import connect
    # 65M rows do not fit in memory: stream one session at a time (indexed on date, ticker)
    covs = {}
    with connect(read_only=True) as c:
        dates = [r[0] for r in c.execute("SELECT DISTINCT date FROM ticks ORDER BY date")]
        for dt in dates:
            x = pd.read_sql("SELECT ticker,time,price FROM ticks WHERE date=? AND price>0", c, params=(dt,))
            x = x.sort_values(["ticker", "time"])
            x["lp"] = np.log(x.price.astype(float))
            for t, v in x.groupby("ticker", sort=False).lp:
                covs.setdefault(t, []).append(day_autocov(v.values))
    lo, hi = pd.Timestamp(dates[0]), pd.Timestamp(dates[-1])
    W = L[(L.date >= lo) & (L.date <= hi) & (L.volume > 0)]
    out = []
    for t, cv in covs.items():
        w = W[W.ticker == t]
        if len(w) < 40:
            continue
        s_roll = roll_from_covs(cv)
        s_ar = ar_spread_from_terms(ar_terms(w.close.values, w.high.values, w.low.values)[:-1])
        floor = float(np.median(tick_size(w.close) / w.close))
        out.append((t, float(w.adv20.median()), max(s_ar, floor), s_roll if np.isnan(s_roll) else max(s_roll, floor)))
    V = pd.DataFrame(out, columns=["ticker", "adv20", "s_ar", "s_roll"]).dropna()
    V["bucket"] = bucket(V.adv20)
    res = {"ticks_window": [str(lo.date()), str(hi.date())], "names": int(len(V))}
    for _, _, name in BUCKETS:
        b = V[V.bucket == name]
        if len(b) < 5:
            res[name] = {"names": int(len(b))}
            continue
        res[name] = {"names": int(len(b)), "median_ar_pct": round(100 * b.s_ar.median(), 3),
                     "median_roll_pct": round(100 * b.s_roll.median(), 3),
                     "spearman": round(float(b.s_ar.corr(b.s_roll, method="spearman")), 2)}
    sub = V[(V.adv20 >= 1e9) & (V.adv20 < 5e9)]
    ratio = sub.s_roll.median() / sub.s_ar.median() if len(sub) else np.nan
    res["ratio_roll_over_ar_1_5bn"] = round(float(ratio), 2)
    res["model_uncertainty_flag"] = bool(not (0.5 <= ratio <= 2.0))
    return res


def t1_net(OA, T, L, cal):
    E = L[["ticker", "date", "s", "sig_d", "adv20"]]
    T = T.merge(E, on=["ticker", "date"], how="left")
    X = L[["ticker", "date", "s"]].rename(columns={"date": "exit", "s": "s_exit"})
    T = T.merge(X, on=["ticker", "exit"], how="left")
    T = T.dropna(subset=["s", "s_exit", "sig_d", "adv20"]).copy()
    T["gross_exc"] = T.exc + FROZEN_RT
    T["bucket"] = bucket(T.adv20)
    res = {"trades_costed": int(len(T))}
    periods = {"FULL": T, "ex-2025": T[pd.DatetimeIndex(T.date).year != 2025]}
    for pname, P in periods.items():
        pr = {}
        for q, Q in SIZES.items():
            cost = FEES + 0.5 * P.s + 0.5 * P.s_exit + 2 * P.sig_d * np.sqrt(Q / P.adv20)
            net = P.gross_exc - cost
            cells = {"all": np.ones(len(P), bool), "A5 in (>=5bn)": (P.adv20 >= 5e9).values,
                     "A5 out (<5bn)": (P.adv20 < 5e9).values}
            for _, _, name in BUCKETS:
                cells[name] = (P.bucket == name).values
            qr = {}
            for cname, m in cells.items():
                if m.sum() < 30:
                    qr[cname] = {"N": int(m.sum())}
                    continue
                x, dates = net.values[m], P.date.values[m]
                months = pd.DatetimeIndex(dates).to_period("M").astype(str)
                mu, _ = OA.cluster_t(x, dates)
                qr[cname] = {"N": int(m.sum()), "mean_net_pct": round(100 * mu, 3),
                             "mean_cost_pct": round(100 * float(cost.values[m].mean()), 3),
                             "t_month": round(OA.cluster_t(x, months)[1], 2),
                             "t_dk60": round(OA.dk_t(x, dates, cal, 60)[1], 2)}
            pr[q] = qr
        res[pname] = pr
    p = res["ex-2025"][PRIMARY_Q]["A5 out (<5bn)"]
    if p["mean_net_pct"] >= PASS_BAR and p["t_dk60"] >= T_BAR:
        v = "survives cost"
    elif p["mean_net_pct"] <= FAIL_FLOOR:
        v = "friction"
    else:
        v = "unclear"
    res["verdict_primary_cell"] = {"cell": f"ex-2025, adv20 < Rp 5bn, {PRIMARY_Q}", **p, "verdict": v}
    return res


def main():
    OA = load_module(OA_PATH, "overlap_audit")
    D, ca = OA.load(DATA_CUTOFF)
    T, d, _ = OA.t1_trades(D, ca)
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))
    L = per_day_liquidity(d)
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "data_cutoff": DATA_CUTOFF, "predeclaration": "PREDECLARATION.md", "descriptive_only": True,
           "cost_table": cost_table(L)}
    print(json.dumps(out["cost_table"], indent=1), flush=True)
    out["validation"] = validate(L)
    print(json.dumps(out["validation"], indent=1), flush=True)
    out["t1"] = t1_net(OA, T, L, cal)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(HERE, f"RESULT_{stamp}.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out["t1"], indent=1, default=str))
    print(f"\nwritten {path}")


if __name__ == "__main__":
    main()
