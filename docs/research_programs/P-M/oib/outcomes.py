"""Daily OIB continuation -- OUTCOME code (G1 only). Never imported by oib.py or g0_census.py.

Daily (mechanism): formation close t, S_cc = EW(Q5) - EW(Q1) of close(t) -> close(t+1) total return.
Daily (next-open entry): S_oc = same legs, open(t+1) -> close(t+1).
Block (tradeability): OIB over a 5-session block; entry at the open of the next session, exit at the
open of the session after the next block; net of cost_realised x turnover per leg.
A bad print (|daily r| > 35%) or a missing bar drops the name for that observation (counted).
"""
from __future__ import annotations

import math

import numpy as np

import cost_realised as cr
import oib as OI

NW_LAGS = 5
SIGMA_FALLBACK = 0.03


def newey_west_t(x, lags=NW_LAGS):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 3:
        return math.nan, math.nan, n
    m = x.mean()
    e = x - m
    s = e @ e / n
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    se = math.sqrt(s / n) if s > 0 else math.nan
    return float(m), float(m / se) if se and se > 0 else math.nan, n


def next_session(panel, d):
    import bisect
    i = bisect.bisect_right(panel.sessions, d)
    return panel.sessions[i] if i < len(panel.sessions) else None


def r_cc(panel, t, a, b):
    g = panel.tickers.get(t)
    if g is None or a not in g["idx"] or b not in g["idx"]:
        return math.nan
    i, j = g["idx"][a], g["idx"][b]
    acc = 1.0
    for m in range(i + 1, j + 1):
        r = (g["c"][m] + panel.divs.get((t, g["d"][m]), 0.0)) / g["c"][m - 1] - 1
        if not np.isfinite(r) or abs(r) > OI.OW.BAD_PRINT:
            return math.nan
        acc *= 1 + r
    return acc - 1


def r_open(panel, opens, t, e, x):
    """open(e) -> open(x) if x is given, else open(e) -> close(e); dividends with ex-date in (e, x]."""
    g = panel.tickers.get(t)
    o = opens.get((t, e))
    if g is None or not o or e not in g["idx"]:
        return math.nan
    if x is None:
        r = g["c"][g["idx"][e]] / o - 1
    else:
        ox = opens.get((t, x))
        if not ox or x not in g["idx"]:
            return math.nan
        div = sum(panel.divs.get((t, d), 0.0) for d in g["d"][g["idx"][e] + 1:g["idx"][x] + 1])
        r = (ox + div) / o - 1
    return r if np.isfinite(r) and abs(r) <= OI.OW.BAD_PRINT * 2 else math.nan


def _z(v):
    v = np.asarray(v, float)
    sd = v.std(ddof=1)
    return (v - v.mean()) / sd if sd > 0 else v * 0


def fm_coef(rows, rets):
    rs = [r for r in rows if np.isfinite(rets.get(r["t"], math.nan))]
    if len(rs) < 50:
        return math.nan
    y = np.asarray([rets[r["t"]] for r in rs])
    X = np.column_stack([np.ones(len(rs))] + [_z([r[k] for r in rs]) for k in ("oib", "r_t", "ladv", "park60")])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[1])


def _spread(q1, q5, rets):
    a = [rets[t] for t in q5 if np.isfinite(rets.get(t, math.nan))]
    b = [rets[t] for t in q1 if np.isfinite(rets.get(t, math.nan))]
    return float(np.mean(a) - np.mean(b)) if a and b else math.nan


def run_daily(panel, opens, secs):
    out, bad = [], 0
    for cs in secs:
        t1 = next_session(panel, cs["k"])
        if t1 is None:
            continue
        q1, q5, n = OI.quintiles(cs["rows"])
        rc = {r["t"]: r_cc(panel, r["t"], cs["k"], t1) for r in cs["rows"]}
        ro = {r["t"]: r_open(panel, opens, r["t"], t1, None) for r in cs["rows"]}
        bad += sum(1 for v in rc.values() if not np.isfinite(v))
        out.append({"k": cs["k"].isoformat(), "n": n, "q": len(q1), "s_cc": _spread(q1, q5, rc),
                    "s_oc": _spread(q1, q5, ro), "fm": fm_coef(cs["rows"], rc)})
    return out, {"dropped_name_days": bad}


def leg_cost(members, feats, prev, counts):
    if not members:
        return 0.0
    tau = 1.0 if prev is None else 1 - len(set(members) & set(prev)) / len(members)
    cs = []
    for t in members:
        sd = feats[t]["sigma60"]
        if not np.isfinite(sd):
            sd = SIGMA_FALLBACK
            counts["sigma_fallback"] += 1
        cs.append(cr.d059_cost_realised(feats[t]["adv"], sd, "normal"))
    return tau * float(np.mean(cs))


def run_blocks(panel, opens, bsecs):
    out, p1, p5, counts = [], None, None, {"sigma_fallback": 0}
    for a, b in zip(bsecs[:-1], bsecs[1:]):
        e, x = next_session(panel, a["k"]), next_session(panel, b["k"])
        if e is None or x is None:
            continue
        q1, q5, n = OI.quintiles(a["rows"])
        if not q1:
            continue
        feats = {r["t"]: r for r in a["rows"]}
        rets = {r["t"]: r_open(panel, opens, r["t"], e, x) for r in a["rows"]}
        g = _spread(q1, q5, rets)
        c1, c5 = leg_cost(q1, feats, p1, counts), leg_cost(q5, feats, p5, counts)
        out.append({"k": a["k"].isoformat(), "gross": g, "c1": c1, "c5": c5, "net": g - c1 - c5})
        p1, p5 = q1, q5
    return out, counts
