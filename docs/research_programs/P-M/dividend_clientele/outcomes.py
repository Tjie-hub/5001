"""Dividend clientele — OUTCOME machinery (G1 only; never imported by the G0
census path, AST-tested).

Not one function here may run on real data before G0 approval and the
DIVIDEND_G1_APPROVED=1 gate (see g1_run.py). Definitions frozen in
PREDECLARATION.md §3-§4:

- EW liquid book, total return: members are names with ADV20 (through t-1)
  >= Rp 10bn, a bar at t and at the prior session, and no split/bonus/
  reverse-split/rights ex-date at t. On a member's IDR dividend ex-date the
  dividend is added back into that day's return (gross; the book is the
  benchmark). An event stock is excluded from its own book and from its own
  decile-matched book.
- D1 net = (stock close_entry -> close_cum) - (book over the same sessions)
  - 0.60% round trip.
- D2 net = (open_ex + 0.9*dividend - close_cum)/close_cum - 0.60%
  - (book cum close -> ex open, dividends of ex-morning members added back).
- Volatility control: the same arithmetic against the EW book of liquid names
  in the event stock's Parkinson-60 decile at entry (computed on the 60
  sessions before entry), instead of the plain EW book.
- Primary t per arm: min( month-mean t, two-way (cum-month x ticker)
  cluster-robust t, Cameron-Gelbach-Miller with G/(G-1) small-sample factors ).
"""
from __future__ import annotations

import bisect
import math
from datetime import date

import numpy as np

from dividend_clientele import (ADV_MIN, ROUND_TRIP, TAX_FACTOR, Panel,
                                build_events, created_date_freq, load_ca_exdates,
                                load_dividend_rows, load_rups)


class Book:
    """Daily total-return series of the EW liquid book (and per-day member
    returns so per-event exclusions and decile-matched books are exact)."""

    def __init__(self, panel: Panel, ca_ex: dict[str, list[date]],
                 div_addback: dict[tuple[str, date], float]):
        self.panel = panel
        self.ca_ex = ca_ex
        self.div = div_addback
        self.member_ret: dict[date, dict[str, float]] = {}
        self.member_open_ret: dict[date, dict[str, float]] = {}
        self._build()

    def _build(self):
        p = self.panel
        sess = p.sessions
        for i in range(1, len(sess)):
            t, tp = sess[i], sess[i - 1]
            rets: dict[str, float] = {}
            open_rets: dict[str, float] = {}
            for tk, g in p.tickers.items():
                if t in self.ca_ex.get(tk, ()):
                    continue  # split/bonus/reverse/rights ex-date today: dropped
                it = p.bar_at(tk, t)
                if it is None:
                    continue
                ip = p.bar_at(tk, tp)
                if ip is None:
                    continue
                c0, c1, o1 = g["c"][ip], g["c"][it], g["o"][it]
                if not (np.isfinite(c0) and np.isfinite(c1) and np.isfinite(o1)) or c0 <= 0:
                    continue
                a = p.adv20(tk, t)
                if a is None or a < ADV_MIN:
                    continue
                d = self.div.get((tk, t), 0.0)
                rets[tk] = (c1 + d) / c0 - 1.0
                open_rets[tk] = (o1 + d) / c0 - 1.0
            if rets:
                self.member_ret[t] = rets
                self.member_open_ret[t] = open_rets

    def ew_return(self, t: date, exclude: str | None = None) -> float | None:
        r = self.member_ret.get(t)
        if not r:
            return None
        vals = [v for k, v in r.items() if k != exclude]
        return float(np.mean(vals)) if vals else None

    def ew_open_return(self, t: date, exclude: str | None = None) -> float | None:
        r = self.member_open_ret.get(t)
        if not r:
            return None
        vals = [v for k, v in r.items() if k != exclude]
        return float(np.mean(vals)) if vals else None

    def window_return(self, t0: date, t1: date, exclude: str | None = None) -> float | None:
        """Compound EW-book return over the sessions whose daily returns span
        close(t0) -> close(t1): every session strictly after t0 through t1."""
        w = 1.0
        any_r = False
        for d in self.panel.sessions:
            if d <= t0 or d > t1:
                continue
            r = self.ew_return(d, exclude)
            if r is None:
                continue
            w *= 1.0 + r
            any_r = True
        return w - 1.0 if any_r else None

    def decile_book(self, d: date, decile: int, panel: Panel) -> list[str]:
        """Liquid names in `decile` of the Parkinson-60 cross-section at d."""
        members = []
        for tk in panel.tickers:
            a = panel.adv20(tk, d)
            if a is None or a < ADV_MIN:
                continue
            p60 = panel.park60(tk, d)
            if p60 is None:
                continue
            if panel.universe_decile(d, p60) == decile:
                members.append(tk)
        return members

    def decile_return(self, t: date, members: list[str],
                      exclude: str | None = None) -> float | None:
        r = self.member_ret.get(t)
        if not r:
            return None
        vals = [r[k] for k in members if k in r and k != exclude]
        return float(np.mean(vals)) if vals else None

    def decile_window_return(self, t0: date, t1: date, members: list[str],
                             exclude: str | None = None) -> float | None:
        w, any_r = 1.0, False
        for d in self.panel.sessions:
            if d <= t0 or d > t1:
                continue
            r = self.decile_return(d, members, exclude)
            if r is None:
                continue
            w *= 1.0 + r
            any_r = True
        return w - 1.0 if any_r else None


def d1_event_return(panel: Panel, book: Book, ev: dict) -> dict:
    """Stock close_entry -> close_cum minus the book, net of the round trip."""
    i0 = panel.bar_at(ev["ticker"], ev["entry_session_date"])
    i1 = panel.bar_at(ev["ticker"], ev["cum_session_date"])
    g = panel.tickers[ev["ticker"]]
    stock = g["c"][i1] / g["c"][i0] - 1.0
    bench = book.window_return(ev["entry_session_date"], ev["cum_session_date"],
                               exclude=ev["ticker"])
    dec_members = book.decile_book(ev["entry_session_date"], ev["park_decile_entry"], panel) \
        if ev["park_decile_entry"] else []
    bench_dec = book.decile_window_return(ev["entry_session_date"], ev["cum_session_date"],
                                          dec_members, exclude=ev["ticker"]) \
        if dec_members else None
    out = {"excess": stock - bench - ROUND_TRIP if bench is not None else None,
           "excess_decile": stock - bench_dec - ROUND_TRIP if bench_dec is not None else None,
           "stock": float(stock), "bench": bench, "bench_decile": bench_dec}
    return out


def d2_event_return(panel: Panel, book: Book, ev: dict) -> dict:
    """(open_ex + 0.9*div - close_cum)/close_cum - round trip - book overnight."""
    g = panel.tickers[ev["ticker"]]
    ic = panel.bar_at(ev["ticker"], ev["cum_session_date"])
    ie = panel.bar_at(ev["ticker"], ev["ex_session_date"])
    raw = (g["o"][ie] + TAX_FACTOR * ev["value"] - g["c"][ic]) / g["c"][ic]
    raw_gross = (g["o"][ie] + ev["value"] - g["c"][ic]) / g["c"][ic]
    bench = book.ew_open_return(ev["ex_session_date"], exclude=ev["ticker"])
    dec_members = book.decile_book(ev["cum_session_date"], ev["park_decile_entry"], panel) \
        if ev["park_decile_entry"] else []
    # D2's exposure is the overnight; the matched book is read over the same night
    bench_dec = None
    if dec_members:
        r = book.member_open_ret.get(ev["ex_session_date"], {})
        vals = [r[k] for k in dec_members if k in r and k != ev["ticker"]]
        bench_dec = float(np.mean(vals)) if vals else None
    out = {"excess": raw - ROUND_TRIP - bench if bench is not None else None,
           "excess_gross": raw_gross - ROUND_TRIP - bench if bench is not None else None,
           "excess_decile": raw - ROUND_TRIP - bench_dec if bench_dec is not None else None,
           "raw": float(raw), "raw_gross": float(raw_gross),
           "drop_ratio": float((g["c"][ic] - g["o"][ie]) / ev["value"]),
           "bench": bench, "bench_decile": bench_dec}
    return out


# --- inference (frozen) -----------------------------------------------------
def month_mean_t(xs: list[float], months: list[str]) -> float:
    agg: dict[str, list[float]] = {}
    for x, m in zip(xs, months):
        agg.setdefault(m, []).append(x)
    ms = np.asarray([np.mean(v) for v in agg.values()], float)
    if len(ms) < 2 or ms.std(ddof=1) == 0:
        return float("nan")
    return float(ms.mean() / ms.std(ddof=1) * math.sqrt(len(ms)))


def two_way_cluster_t(xs: list[float], months: list[str], tickers: list[str]) -> float:
    """CGM two-way cluster-robust t of the mean (regression on a constant)."""
    x = np.asarray(xs, float)
    n = len(x)
    if n < 2:
        return float("nan")
    m = x.mean()
    s = x - m
    def vcv(groups):
        tot: dict = {}
        for si, g in zip(s, groups):
            tot[g] = tot.get(g, 0.0) + si
        v = sum(v_ * v_ for v_ in tot.values())
        G = len(tot)
        return v * G / (G - 1) if G > 1 else 0.0
    vm = vcv(months) / n ** 2
    vt = vcv(tickers) / n ** 2
    vmt = vcv(list(zip(months, tickers))) / n ** 2
    v = max(vm + vt - vmt, 1e-24)
    return float(m / math.sqrt(v))


def primary_t(xs, months, tickers) -> dict:
    tm = month_mean_t(xs, months)
    tc = two_way_cluster_t(xs, months, tickers)
    return {"t_month": tm, "t_two_way_cluster": tc, "primary_t": min(tm, tc)}


def arm_pass(cond: dict) -> bool:
    return bool(cond["mean"] > 0 and cond["primary_t"] >= cond["bar"]
                and cond["half1_mean"] > 0 and cond["half2_mean"] > 0
                and cond["decile_mean"] > 0 and cond["extra"])
