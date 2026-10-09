"""Online-retail broker imbalance -- OUTCOME code (G1 only). Never imported by flow.py or g0_census.py.

B1 primary: weekly. Formation at the close of the last session of ISO week w; hold to the close of
the last session of week w+1. S1 = EW(Q1) - EW(Q5), gross. Name return: compounded daily total
return (dividend add-back); a bad print (|r| > 35%) drops the name for that week; no bar = 0 (stale).
Tradeability block (required): non-overlapping 4-week blocks; signal over the block's 4 weeks;
hold 4 weeks; net of cost_realised x turnover per leg.
"""
from __future__ import annotations

import math

import numpy as np

import cost_realised as cr
import flow as FL

NW_LAGS = 4
SIGMA_FALLBACK = 0.03


def name_return(panel, t, k0, k1):
    g = panel.tickers.get(t)
    if g is None or k0 not in g["idx"]:
        return 0.0, "stale"
    d, c = g["d"], g["c"]
    j, acc, n = g["idx"][k0] + 1, 1.0, 0
    while j < len(d) and d[j] <= k1:
        r = (c[j] + panel.divs.get((t, d[j]), 0.0)) / c[j - 1] - 1.0
        if not np.isfinite(r) or abs(r) > FL.OW.BAD_PRINT:
            return math.nan, "bad"
        acc *= 1.0 + r
        n += 1
        j += 1
    return (acc - 1.0, "ok") if n else (0.0, "stale")


def newey_west_t(x, lags=NW_LAGS):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 3:
        return math.nan, math.nan, n
    m = x.mean()
    e = x - m
    s = e @ e / n
    for L in range(1, lags + 1):
        s += 2 * (1.0 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    se = math.sqrt(s / n) if s > 0 else math.nan
    return float(m), float(m / se) if se and se > 0 else math.nan, n


def _z(v):
    v = np.asarray(v, float)
    sd = v.std(ddof=1)
    return (v - v.mean()) / sd if sd > 0 else v * 0.0


def fm_coef(rows, rets):
    rs = [r for r in rows if np.isfinite(rets.get(r["t"], math.nan))]
    if len(rs) < 30:
        return math.nan
    y = np.asarray([rets[r["t"]] for r in rs])
    X = np.column_stack([np.ones(len(rs))] + [_z([r[k] for r in rs]) for k in ("ri", "fi", "prior", "ladv", "park60")])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[1])


def leg_cost(members, feats, prev, counts):
    if not members:
        return 0.0
    tau = 1.0 if prev is None else 1.0 - len(set(members) & set(prev)) / len(members)
    cs = []
    for t in members:
        sd = feats[t]["sigma60"]
        if not np.isfinite(sd):
            sd = SIGMA_FALLBACK
            counts["sigma_fallback"] += 1
        cs.append(cr.d059_cost_realised(feats[t]["adv"], sd, "normal"))
    return tau * float(np.mean(cs))


def run_weekly(panel, sections):
    counts = {"bad": 0, "stale": 0, "sigma_fallback": 0}
    out = []
    for a, b in zip(sections[:-1], sections[1:]):
        q1, q5, n = FL.quintiles(a["rows"])
        if not q1:
            continue
        rets = {}
        for r in a["rows"]:
            v, st = name_return(panel, r["t"], a["k"], b["k"])
            if st != "ok":
                counts[st] += 1
            rets[r["t"]] = v
        e1 = [rets[t] for t in q1 if np.isfinite(rets[t])]
        e5 = [rets[t] for t in q5 if np.isfinite(rets[t])]
        out.append({"k": a["k"].isoformat(), "n": n, "q": len(q1), "q1": float(np.mean(e1)),
                    "q5": float(np.mean(e5)), "gross": float(np.mean(e1) - np.mean(e5)),
                    "fm": fm_coef(a["rows"], rets)})
    return out, counts


def run_blocks(panel, blocks):
    """blocks: cross-sections whose signal spans BLOCK_WEEKS weeks, consecutive and non-overlapping."""
    counts = {"bad": 0, "stale": 0, "sigma_fallback": 0}
    out, p1, p5 = [], None, None
    for a, b in zip(blocks[:-1], blocks[1:]):
        q1, q5, n = FL.quintiles(a["rows"])
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
        c1, c5 = leg_cost(q1, feats, p1, counts), leg_cost(q5, feats, p5, counts)
        g = float(np.mean(e1) - np.mean(e5))
        out.append({"k": a["k"].isoformat(), "gross": g, "c1": c1, "c5": c5, "net": g - c1 - c5})
        p1, p5 = q1, q5
    return out, counts
