"""Tender-offer floor — OUTCOME machinery (G1 only; never imported by the
G0 census path, AST-tested).

Nothing here may run on real data before G0 approval and the
TENDER_G1_APPROVED=1 gate. Definitions frozen in PREDECLARATION.md (D-074):

- T1 (one arm): R = (close(tender_end session) + dividends with ex-date in
  (entry, exit]) / close(entry) - 1 - D-059 cost (market exit at the
  tender_end close; last session on or before tender_end).
- Test: pooled mean of R with month-clustered t (entry calendar month,
  Cameron one-way cluster with G/(G-1) small-sample correction).
- Required: mean excess over the EW liquid book (true-ADV20 >= Rp 10bn at
  the entry session, total return, same window) > 0; excess = R - book.
- Report only: acceptance upper bound (offer paid on paydate, no proration,
  net of cost), convergence ratio, per-event table, 5 worst, splits by
  tender_percentage (>= 99 full) and ADV tier (1-10bn vs >= 10bn),
  withdrawn-suspect (close(end) < 0.90 x min(entry close, adj offer)) and
  proration (pct < 99) diagnostics for the D-074 falsification clause 2.
"""
from __future__ import annotations

import bisect
from datetime import date

import numpy as np

import tender_floor as TF


def _exit_index(panel: TF.Panel, t: str, d_exit: date) -> int | None:
    """Last bar index on or before d_exit."""
    g = panel.tickers.get(t)
    if g is None:
        return None
    i = bisect.bisect_right(g["d"], d_exit) - 1
    return i if i >= 0 else None


def total_return(panel: TF.Panel, t: str, i_entry: int, d_entry: date, d_exit: date) -> tuple[float, bool, float]:
    """(close(exit) + divs ex in (entry, exit]) / close(entry) - 1.
    Returns (ret, short_exit, div_addback). short_exit = last available bar
    strictly before d_exit (counted, never dropped)."""
    g = panel.tickers[t]
    i_x = _exit_index(panel, t, d_exit)
    if i_x is None or i_x <= i_entry:
        return float("nan"), True, 0.0
    div = 0.0
    for (tt, dd), v in panel.divs.items():
        if tt == t and d_entry < dd <= d_exit:
            div += v
    ret = (float(g["c"][i_x]) + div) / float(g["c"][i_entry]) - 1.0
    return ret, bool(g["d"][i_x] != d_exit), div


def ew_book(panel: TF.Panel, d_entry: date, d_exit: date) -> tuple[float, int]:
    """EW total return of names with true-ADV20 >= BOOK_ADV_MIN at the entry
    session (membership known at entry), same window, same last-bar rule."""
    rets = []
    for t in panel.tickers:
        if t == "FORU" and d_entry >= TF.FORU_CUTOFF:
            continue
        i_e = panel.bar_index(t, d_entry)
        if i_e is None or i_e < TF.ADV_WINDOW:
            continue
        adv = panel.tickers[t]["adv_true"][i_e]
        if not (np.isfinite(adv) and adv >= TF.BOOK_ADV_MIN):
            continue
        r, _, _ = total_return(panel, t, i_e, d_entry, d_exit)
        if np.isfinite(r):
            rets.append(r)
    return (float(np.mean(rets)) if rets else float("nan")), len(rets)


def month_clustered_t(vals: list[float], months: list[str]) -> tuple[float, float, float, int]:
    """mean, one-way cluster-robust se (entry month), t, n_clusters.
    V = G/(G-1) * sum_g (sum_i e_i)^2 / n^2, e_i = R_i - mean (k=1)."""
    x = np.asarray(vals, float)
    n = len(x)
    mean = float(x.mean())
    e = x - mean
    clusters: dict[str, float] = {}
    for m, ei in zip(months, e):
        clusters[m] = clusters.get(m, 0.0) + float(ei)
    G = len(clusters)
    if G < 2:
        return mean, float("nan"), float("nan"), G
    v = (G / (G - 1.0)) * sum(v ** 2 for v in clusters.values()) / (n ** 2)
    se = float(np.sqrt(v))
    t = mean / se if se > 0 else float("nan")
    return mean, se, t, G


def t1_event(panel: TF.Panel, facts: dict) -> dict:
    """The frozen T1 arm + every frozen report-only variant for one event."""
    out = {"ticker": facts["ticker"], "event_id": facts["event_id"],
           "start": str(facts["start"]), "end": str(facts["end"]),
           "d_entry": str(facts["d_entry"]), "d_exit": str(facts["d_exit"]),
           "spread": facts["spread"], "cost": facts["cost"],
           "adv20_idrbn": facts["adv20"] / 1e9,
           "window_sessions": facts["window_sessions"],
           "pct": facts["pct"]}
    i_e = panel.bar_index(facts["ticker"], facts["d_entry"])
    r, short, div = total_return(panel, facts["ticker"], i_e, facts["d_entry"], facts["d_exit"])
    out["gross_ret"] = r
    out["short_exit"] = short
    out["div_addback"] = div
    out["R"] = r - facts["cost"]
    book, book_n = ew_book(panel, facts["d_entry"], facts["d_exit"])
    out["book_ret"] = book
    out["book_n"] = book_n
    out["excess"] = out["R"] - book if np.isfinite(book) else float("nan")
    # acceptance upper bound (report only): offer paid on paydate, no proration
    out["acceptance_ub"] = facts["price_adj"] / facts["close_entry"] - 1.0 - facts["cost"]
    # convergence ratio
    gap = facts["price_adj"] - facts["close_entry"]
    i_x = _exit_index(panel, facts["ticker"], facts["d_exit"])
    c_end = float(panel.tickers[facts["ticker"]]["c"][i_x])
    out["close_end"] = c_end
    out["convergence"] = (c_end - facts["close_entry"]) / gap if gap > 0 else float("nan")
    # falsification-clause-2 diagnostics
    out["withdrawn_suspect"] = bool(c_end < TF.WITHDRAW_FACTOR * min(facts["close_entry"], facts["price_adj"]))
    out["proration_suspect"] = bool(facts["pct"] is not None and facts["pct"] < TF.FULL_PCT_CUT)
    out["adv_tier"] = "1-10bn" if facts["adv20"] < TF.BOOK_ADV_MIN else ">=10bn"
    return out
