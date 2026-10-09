"""Retail ownership -- OUTCOME code (G1 only). Never imported by ownership.py or g0_census.py.

Holding period: formation close K_M -> next formation close K_{M+1} (monthly, non-overlapping).
Name return: compounded daily total return (close + dividend on its ex-date) over bars in
(K_M, K_{M+1}]. A bad print (|daily r| > 35%) drops the name from that month (counted). A name
with no bar in the window has return 0 (stale, counted).
Spread S = EW(Q1) - EW(Q5) - c(Q1) - c(Q5); leg cost c = turnover x mean member round-trip cost
(cost_realised.d059_cost_realised, "normal" day, q = Rp 100m); turnover = 1 - |overlap| / |leg|
(1.0 at the first formation of an arm).
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

import cost_realised as cr  # frozen copy, sha256 65051253... (D-082)
from ownership import BAD_PRINT, H1_LAST_FORMATION, quintiles

NW_LAGS = 3
SIGMA_FALLBACK = 0.03   # members without a 60-session sigma (counted)


def name_return(panel, t: str, k0: date, k1: date) -> tuple[float, str]:
    g = panel.tickers.get(t)
    if g is None:
        return 0.0, "stale"
    d, c = g["d"], g["c"]
    i0 = g["idx"].get(k0)
    if i0 is None:
        return 0.0, "stale"
    acc, n = 1.0, 0
    j = i0 + 1
    while j < len(d) and d[j] <= k1:
        r = (c[j] + panel.divs.get((t, d[j]), 0.0)) / c[j - 1] - 1.0
        if not np.isfinite(r) or abs(r) > BAD_PRINT:
            return math.nan, "bad"
        acc *= 1.0 + r
        n += 1
        j += 1
    return (acc - 1.0, "ok") if n else (0.0, "stale")


def leg_cost(members: list[str], feats: dict[str, dict], prev: list[str] | None, counts: dict) -> float:
    if not members:
        return 0.0
    tau = 1.0 if prev is None else 1.0 - len(set(members) & set(prev)) / len(members)
    cs = []
    for t in members:
        f = feats[t]
        sd = f["sigma60"]
        if not np.isfinite(sd):
            sd = SIGMA_FALLBACK
            counts["sigma_fallback"] = counts.get("sigma_fallback", 0) + 1
        cs.append(cr.d059_cost_realised(f["adv"], sd, "normal"))
    return tau * float(np.mean(cs))


def newey_west_t(x: np.ndarray, lags: int = NW_LAGS) -> tuple[float, float, int]:
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 3:
        return math.nan, math.nan, n
    m = x.mean()
    e = x - m
    s = e @ e / n
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = math.sqrt(s / n) if s > 0 else math.nan
    return float(m), float(m / se) if se and se > 0 else math.nan, n


def _z(v):
    v = np.asarray(v, float)
    sd = v.std(ddof=1)
    return (v - v.mean()) / sd if sd > 0 else v * 0.0


def fm_coef(rows: list[dict], rets: dict[str, float], key: str) -> float:
    """One cross-section: r ~ 1 + z(signal) + z(size) + z(park60) + z(mom) + volex; signal coef."""
    rs = [r for r in rows if r["t"] in rets and np.isfinite(rets[r["t"]])
          and all(np.isfinite(r[k]) for k in (key, "size", "park60", "mom"))]
    if len(rs) < 30:
        return math.nan
    y = np.asarray([rets[r["t"]] for r in rs])
    X = np.column_stack([np.ones(len(rs)), _z([r[key] for r in rs]), _z([r["size"] for r in rs]),
                         _z([r["park60"] for r in rs]), _z([r["mom"] for r in rs]),
                         [r["volex"] for r in rs]])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[1])


def run_arm(panel, sections: list[dict], key: str) -> dict:
    """sections: build_cross_section outputs in formation order (k ascending)."""
    months, prev_q1, prev_q5 = [], None, None
    counts = {"bad": 0, "stale": 0, "sigma_fallback": 0}
    for a, b in zip(sections[:-1], sections[1:]):
        q1, q5, n = quintiles(a["rows"], key)
        if not q1:
            continue
        feats = {r["t"]: r for r in a["rows"]}
        rets = {}
        for r in a["rows"]:
            v, st = name_return(panel, r["t"], a["k"], b["k"])
            if st != "ok":
                counts[st] += 1
            rets[r["t"]] = v
        e1 = [rets[t] for t in q1 if np.isfinite(rets[t])]
        e5 = [rets[t] for t in q5 if np.isfinite(rets[t])]
        uni = [v for v in rets.values() if np.isfinite(v)]
        ex5 = [rets[r["t"]] for r in a["rows"] if r["t"] not in set(q5) and np.isfinite(rets[r["t"]])]
        c1 = leg_cost(q1, feats, prev_q1, counts)
        c5 = leg_cost(q5, feats, prev_q5, counts)
        g1, g5 = float(np.mean(e1)), float(np.mean(e5))
        months.append({"k": a["k"].isoformat(), "k_next": b["k"].isoformat(), "n": n, "q": len(q1),
                       "q1": g1, "q5": g5, "gross": g1 - g5, "c1": c1, "c5": c5,
                       "net": g1 - g5 - c1 - c5, "avoid": float(np.mean(ex5) - np.mean(uni)),
                       "fm": fm_coef(a["rows"], rets, key)})
        prev_q1, prev_q5 = q1, q5
    net = np.asarray([m["net"] for m in months])
    out = {"key": key, "months": months, "counts": counts}
    out["net_mean"], out["net_t"], out["n_months"] = newey_west_t(net)
    out["gross_mean"], out["gross_t"], _ = newey_west_t(np.asarray([m["gross"] for m in months]))
    out["fm_mean"], out["fm_t"], out["fm_n"] = newey_west_t(np.asarray([m["fm"] for m in months]))
    out["avoid_mean"], out["avoid_t"], _ = newey_west_t(np.asarray([m["avoid"] for m in months]))
    h1 = np.asarray([m["net"] for m in months if date.fromisoformat(m["k"]) <= H1_LAST_FORMATION])
    h2 = np.asarray([m["net"] for m in months if date.fromisoformat(m["k"]) > H1_LAST_FORMATION])
    out["h1_mean"], out["h1_t"], out["h1_n"] = newey_west_t(h1)
    out["h2_mean"], out["h2_t"], out["h2_n"] = newey_west_t(h2)
    return out
