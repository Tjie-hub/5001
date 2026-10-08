"""Market-stress reversal — OUTCOME machinery (G1 only; never imported by the
G0 census path, AST-tested).

Not one function here may run on real data before G0 approval and the
STRESS_G1_APPROVED=1 gate. Definitions frozen in PREDECLARATION.md §4-§5:

- S1 (one arm): basket = bottom-quintile liquid names by day-t return (zero-
  volume ARB names excluded), entry at the close of t, exit at the close of
  t+5 panel sessions. Per member: compounded close-to-close return over the
  window; a missing exit bar uses the LAST available close before the exit
  date and is counted. Basket return = equal-weight mean of member returns.
- Market leg: equal-weight mean of the day-t liquid set's own 5-session
  total returns (same last-available-close rule).
- beta per member: OLS slope of the member's daily returns on r_m over the
  last 250 DEFINED paired sessions strictly before t (>= 120 required);
  basket beta = mean of member betas; members without enough history take
  the mean beta of the other members (counted).
- Cost per member (D-059, `P-M/cost_liquidity/cost_by_adv.py` @ 7e039ee,
  frozen): 0.50% fees + (1/2 s_entry + 1/2 s_exit) + 2*sigma_d*sqrt(Q/ADV20),
  s = Abdi-Ranaldo spread over the 21 sessions ending t-1 floored at one
  IDX tick, sigma_d = SD of the member's daily returns over the 60 sessions
  before t, Q = Rp 100m (D-059 primary size), ADV20 = the true-rupiah ADV.
  Basket cost = mean of member costs.
- R = basket - beta * market - cost (per event; episodes are the independent
  unit, so the t statistic is mean/sd*sqrt(n) with no clustering).
"""
from __future__ import annotations

import bisect
import importlib.util
import math
from datetime import date

import numpy as np

import stress_reversal as SR

_spec = importlib.util.spec_from_file_location(
    "cost_by_adv",
    SR.REPO_ROOT / "docs" / "research_programs" / "P-M" / "cost_liquidity" / "cost_by_adv.py")
CB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CB)

FEES = 0.005
Q_SIZE = 100e6
BETA_WIN = 250
BETA_MIN = 120
SD_WIN = 60


def compute_R(basket_ret: float, beta: float, mkt_ret: float, cost: float) -> float:
    """The frozen assembly. R = basket - beta*market - cost (fractions)."""
    return basket_ret - beta * mkt_ret - cost


def _bar_index(panel: SR.Panel, t: str, d: date) -> int | None:
    g = panel.tickers.get(t)
    if g is None:
        return None
    i = bisect.bisect_left(g["d"], d)
    if i < len(g["d"]) and g["d"][i] == d:
        return i
    return None


def _bar_on_or_before(g: dict, d: date) -> int | None:
    i = bisect.bisect_right(g["d"], d) - 1
    return i if i >= 0 else None


def member_window_return(panel: SR.Panel, t: str, i_sess: int,
                         n_sessions: int) -> tuple[float, bool]:
    """Compounded close-to-close return from the close of panel session i_sess
    to the close of session i_sess + n_sessions (last panel session if past
    the end). A member with no bar in (entry, exit] returns NaN; a member
    whose last bar inside the window is before the exit date is `short`."""
    g = panel.tickers[t]
    d_entry = panel.sessions[i_sess]
    i_exit = min(i_sess + n_sessions, len(panel.sessions) - 1)
    d_exit = panel.sessions[i_exit]
    j0 = _bar_index(panel, t, d_entry)
    if j0 is None:
        return float("nan"), True
    j1 = _bar_on_or_before(g, d_exit)
    if j1 is None or j1 <= j0:
        return float("nan"), True
    return float(g["c"][j1] / g["c"][j0] - 1.0), bool(g["d"][j1] != d_exit)


def beta_for(panel: SR.Panel, t: str, d: date) -> float | None:
    """OLS slope of the member's daily returns on r_m over the last 250
    DEFINED paired sessions strictly before d."""
    g = panel.tickers.get(t)
    if g is None:
        return None
    pairs: list[tuple[float, float]] = []
    for rd, rv in zip(panel.rm_dates, panel.rm_vals):
        if rd >= d:
            break
        j = _bar_on_or_before(g, rd)
        if j is None or j == 0:
            continue
        r = g["ret"][j]
        if np.isnan(r):
            continue
        pairs.append((float(r), float(rv)))
    pairs = pairs[-BETA_WIN:]
    if len(pairs) < BETA_MIN:
        return None
    y = np.asarray([p[0] for p in pairs], float)   # member daily returns (dependent)
    x = np.asarray([p[1] for p in pairs], float)   # r_m (independent)
    if x.std() == 0:
        return None
    return float(np.polyfit(x, y, 1)[0])


def sigma_d(panel: SR.Panel, t: str, d: date, window: int = SD_WIN) -> float | None:
    """SD of the member's daily total returns over the `window` defined days
    strictly before d."""
    g = panel.tickers.get(t)
    if g is None:
        return None
    vals: list[float] = []
    for i in range(len(g["d"]) - 1, -1, -1):
        if g["d"][i] >= d:
            continue
        r = g["ret"][i]
        if not np.isnan(r):
            vals.append(float(r))
        if len(vals) >= window:
            break
    if len(vals) < 30:
        return None
    return float(np.std(vals, ddof=1))


def d059_cost(panel: SR.Panel, t: str, d: date, adv: float | None) -> float | None:
    """D-059 modelled round trip: 0.50% fees + AR spread (21 sessions ending
    t-1, floored at one tick) + 2*sigma_d*sqrt(Q/ADV20), Q = Rp 100m."""
    g = panel.tickers.get(t)
    if g is None or adv is None or adv <= 0:
        return None
    terms = []
    for i in range(len(g["d"]) - 1, -1, -1):
        if g["d"][i] >= d:
            continue
        terms.insert(0, (float(g["c"][i]), float(g["h"][i]), float(g["l"][i])))
        if len(terms) >= 22:
            break
    if len(terms) < 2:
        return None
    c = np.asarray([x[0] for x in terms])
    h = np.asarray([x[1] for x in terms])
    lo = np.asarray([x[2] for x in terms])
    ar = CB.ar_terms(c, h, lo)
    s = CB.ar_spread_from_terms(ar[:-1])
    last_close = float(c[-1])
    tick = float(CB.tick_size(np.asarray([last_close]))[0])
    s = max(s, tick / last_close)
    sd = sigma_d(panel, t, d)
    impact = 2.0 * (sd or 0.0) * math.sqrt(Q_SIZE / adv)
    return FEES + s + impact


def park60(panel: SR.Panel, t: str, d: date) -> float | None:
    """Parkinson-60 range vol over the 60 sessions strictly before d."""
    g = panel.tickers.get(t)
    if g is None:
        return None
    vals: list[float] = []
    for i in range(len(g["d"]) - 1, -1, -1):
        if g["d"][i] >= d:
            continue
        h, lo = float(g["h"][i]), float(g["l"][i])
        if h > 0 and lo > 0:
            vals.append(math.log(h / lo) ** 2)
        if len(vals) >= 60:
            break
    if len(vals) < 60:
        return None
    return math.sqrt(float(np.mean(vals)) / (4.0 * math.log(2.0)))


def _decile_edges(vals: list[float]) -> list[float]:
    vals = sorted(vals)
    n = len(vals)
    return [vals[min(n - 1, int(round(q * (n - 1))))] for q in np.arange(1, 10) / 10.0]


def decile_of(edges: list[float], p: float) -> int:
    return int(bisect.bisect_left(edges, p * (1 + 1e-12)) + 1)


def _mkt_members(panel: SR.Panel, d: date) -> list[str]:
    out = []
    for t, i in panel.by_date[d]:
        if t == "FORU" and d >= SR.FORU_CUTOFF:
            continue
        g = panel.tickers[t]
        if i >= SR.ADV_WINDOW and bool(g["liq_true"][i]) and not np.isnan(g["ret"][i]):
            out.append(t)
    return out


def assemble(panel: SR.Panel, d: date, members: list[str], horizon: int,
             i_sess: int | None = None) -> dict:
    """One assembly of the frozen arm at entry session i_sess (default: the
    session of d): basket/market 5-session legs, beta, D-059 cost, R."""
    if i_sess is None:
        i_sess = panel.sessions.index(d)
    mkt_members = _mkt_members(panel, panel.sessions[i_sess])
    mkt_rets, short_m = [], 0
    for t in mkt_members:
        r, short = member_window_return(panel, t, i_sess, horizon)
        short_m += int(short)
        if np.isfinite(r):
            mkt_rets.append(r)
    b_rets, short_b = [], 0
    for t in members:
        r, short = member_window_return(panel, t, i_sess, horizon)
        short_b += int(short)
        if np.isfinite(r):
            b_rets.append(r)
    mkt = float(np.mean(mkt_rets)) if mkt_rets else None
    basket = float(np.mean(b_rets)) if b_rets else None
    betas, fallback = [], 0
    for t in members:
        b = beta_for(panel, t, d)
        if b is None:
            fallback += 1
        else:
            betas.append(b)
    beta = float(np.mean(betas)) if betas else None
    costs = []
    for t in members:
        i = _bar_index(panel, t, d)
        adv = float(panel.tickers[t]["adv_true"][i]) if i is not None else None
        c = d059_cost(panel, t, d, adv if adv is not None and np.isfinite(adv) else None)
        if c is not None:
            costs.append(c)
    cost = float(np.mean(costs)) if costs else None
    out = {"n_basket": len(b_rets), "n_mkt": len(mkt_rets), "short_exit_basket": short_b,
           "short_exit_mkt": short_m, "beta": beta, "beta_fallback": fallback,
           "cost": cost, "basket_ret": basket, "mkt_ret": mkt}
    if None not in (basket, beta, mkt, cost):
        out["R"] = compute_R(basket, beta, mkt, cost)
    return out


BIG4 = {"BBCA", "BBRI", "BMRI", "BBNI"}


def s1_event(panel: SR.Panel, d: date, drop: set[str] = frozenset()) -> dict | None:
    """The frozen S1 arm at event day d plus every frozen variant:
    next-day entry, horizons 1/10/20 (report only), ex-big-4 and ex-ex-date
    controls, the Parkinson-60-decile-matched control, and S2 (report only)."""
    members, k, arb = panel.basket(d, drop)
    if not members:
        return None
    i_e = panel.sessions.index(d)
    out = {"date": str(d), "rm": panel.market[d][0], "sigma": panel.sigma[d],
           "multiple": panel.flags[d], "basket_size": k, "arb_excluded": arb}
    core = assemble(panel, d, members, SR.HORIZON)
    out.update(core)
    if "R" in core:
        out["R"] = core["R"]
    # next-day entry: close t+1 -> close t+6
    if i_e + 1 < len(panel.sessions):
        nxt = assemble(panel, d, members, SR.HORIZON, i_sess=i_e + 1)
        if "R" in nxt:
            out["R_next_day"] = nxt["R"]
    # horizons 1/10/20 (report only)
    for h in (1, 10, 20):
        v = assemble(panel, d, members, h)
        if "R" in v:
            out[f"R_h{h}"] = v["R"]
    # control: exclude the big-4 banks (HYP-PM-0014) from the basket
    mb = [t for t in members if t not in BIG4]
    if mb:
        v = assemble(panel, d, mb, SR.HORIZON)
        if "R" in v:
            out["R_ex_big4"] = v["R"]
    # control: exclude members with ANY ex-date (dividend incl.) in t-1..t+5
    def has_exdate(t):
        g = panel.tickers[t]
        d_ex = set()
        for (tt, dd), v in panel.divs.items():
            if tt == t:
                d_ex.add(dd)
        for dd, _ in panel.fac.get(t, ()):
            d_ex.add(dd)
        lo, hi = panel.sessions[max(0, i_e - 1)], panel.sessions[min(len(panel.sessions) - 1, i_e + SR.HORIZON)]
        return any(lo <= x <= hi for x in d_ex)
    mx = [t for t in members if not has_exdate(t)]
    if mx:
        v = assemble(panel, d, mx, SR.HORIZON)
        if "R" in v:
            out["R_ex_exdate"] = v["R"]
        out["n_ex_exdate_dropped"] = len(members) - len(mx)
    # Parkinson-60-decile-matched control over the same window
    parks = {}
    for t in _mkt_members(panel, d):
        p = park60(panel, t, d)
        if p is not None:
            parks[t] = p
    if len(parks) >= 10:
        edges = _decile_edges(list(parks.values()))
        basket_set = set(members)
        ctrl = []
        for t in members:
            pp = parks.get(t)
            if pp is None:
                continue
            b = decile_of(edges, pp)
            mates = [x for x, px in parks.items()
                     if x not in basket_set and decile_of(edges, px) == b]
            rs = []
            for x in mates:
                r, _ = member_window_return(panel, x, i_e, SR.HORIZON)
                if np.isfinite(r):
                    rs.append(r)
            if rs:
                ctrl.append(float(np.mean(rs)))
        out["decile_ctrl_n"] = len(ctrl)
        if ctrl and core.get("basket_ret") is not None and core.get("cost") is not None:
            out["R_park_ctrl"] = core["basket_ret"] - float(np.mean(ctrl)) - core["cost"]
    # S2 (report only): the EW liquid market over t->t+5 minus its trailing-250
    # mean 5-session return (all strictly before t)
    if core.get("mkt_ret") is not None:
        starts = [i for i in range(max(0, i_e - 255), i_e - 5)]
        vals = []
        for i in starts:
            w = 1.0
            ok = True
            for h in range(1, 6):
                dd = panel.sessions[i + h]
                if dd in panel.market:
                    w *= 1.0 + panel.market[dd][0]
                else:
                    ok = False
                    break
            if ok:
                vals.append(w - 1.0)
        if vals:
            out["S2"] = core["mkt_ret"] - float(np.mean(vals))
            out["S2_baseline_n"] = len(vals)
    return out
