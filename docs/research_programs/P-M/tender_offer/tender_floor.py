"""Tender-offer price floor (HYP-PM-0018 draft) — shared PRE-EVENT driver.

G0 machinery only: everything here may run before G0 approval PROVIDED no
close after an event's entry session is accessed. The entry close, the
spread against the (basis-adjusted) tender price, true-rupiah ADV20, the
D-059 cost and window LENGTHS (session counts, not prices) are pre-event
facts (D-074). Any return, price or book value AFTER the entry close lives
in outcomes.py, which this module must never import.

Conventions mirror the market-stress G0 (research/market-stress-reversal-2026-10):
- split-class share factors from corporate_action_events (stocksplit
  new/old, bonus stocksplit_factor, stock_reverse new/old); f_cum(t, d) =
  product of factors with ex-date STRICTLY after d; stored close =
  as-traded / f_cum.
- true-rupiah ADV20 at a bar = mean(close x f_cum(bar) x volume) over that
  bar's own previous 20 bars (ADV_WINDOW).
- dividends: IDR only, deduped by dividend_id, summed per (ticker, ex-date),
  add-back on EX dates.
- bad print: |daily return| > 35% is NaN for every return aggregation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]

WF_SNAPSHOT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"

ADV_WINDOW = 20
ADV_MIN = 1.0e9          # Rp 1bn eligibility floor (D-074)
BOOK_ADV_MIN = 1.0e10    # Rp 10bn EW comparison book
BAD_PRINT = 0.35
FORU_CUTOFF = date(2026, 9, 14)   # D-063
SPREAD_FLOOR = 0.006      # 0.60% (D-074)
FULL_PCT_CUT = 99.0       # tender_percentage >= 99 = "full" offer (data max is 90 -> all partial)
MIN_EVENTS = 20           # stop rule (owner, D-074)
MIN_WINDOW_SESSIONS = 2   # population rule 1 (brief)
WITHDRAW_FACTOR = 0.90    # withdrawn-suspect: close(end) < 0.90 x min(entry, offer)

# FROZEN BASIS RULE (settled at G0 from the diagnostic below; see
# CENSUS_G0.json: basis_check): tender_price is AS-ANNOUNCED, i.e. on the
# as-traded basis of the offer time, NOT pre-scaled to the stored basis
# (unlike dividend_value). Discriminating events (f_cum >= 1.05): LPGI 2023
# r_stored 10.42 vs r_asannounced 1.042; PTRO 2022 10.19 vs 1.019; EDGE 2021
# 2.02 vs 0.404. Rescale: adj_price = tender_price / f_cum(entry).
BASIS_RULE = "as_announced_rescale"

_spec = importlib.util.spec_from_file_location(
    "cost_by_adv",
    REPO_ROOT / "docs" / "research_programs" / "P-M" / "cost_liquidity" / "cost_by_adv.py")
CB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CB)

FEES = 0.005              # D-059 (same frozen module as the stress G0, @ 7e039ee)
Q_SIZE = 100e6            # D-059 primary size
SD_WIN = 60               # pre-entry daily-return SD window (power, cost)
SD_MIN = 30


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def load_ca(conn) -> tuple[dict[str, list[tuple[date, float]]], dict[tuple[str, date], float]]:
    """(split-class share factors per ticker, dividend add-back per (ticker, ex-date))."""
    fac: dict[str, list[tuple[date, float]]] = {}
    for at in ("stocksplit", "bonus", "stock_reverse"):
        for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                                  "WHERE action_type=?", (at,)).fetchall():
            j = json.loads(rj)
            d = parse_date(j.get("stocksplit_exdate"))
            if d is None:
                continue
            try:
                f = (float(j.get("stocksplit_factor")) if at == "bonus"
                     else float(j.get("stocksplit_new")) / float(j.get("stocksplit_old")))
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if f and f > 0:
                fac.setdefault(t, []).append((d, f))
    for t in fac:
        fac[t].sort()
    divs: dict[tuple[str, date], float] = {}
    seen = set()
    for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                              "WHERE action_type='dividend'").fetchall():
        j = json.loads(rj)
        did = str(j.get("dividend_id"))
        if did in seen:
            continue
        seen.add(did)
        if j.get("dividend_currency") != "CURRENCY_IDR":
            continue
        try:
            v = float(j.get("dividend_value"))
        except (TypeError, ValueError):
            continue
        ex = parse_date(j.get("dividend_exdate"))
        if v > 0 and ex is not None:
            k = (t, ex)
            divs[k] = divs.get(k, 0.0) + v
    return fac, divs


def f_cum(fac: dict[str, list[tuple[date, float]]], t: str, d: date) -> float:
    """Product of share-factors of split-class CA with ex-date STRICTLY after d."""
    p = 1.0
    for de, f in fac.get(t, ()):
        if de > d:
            p *= f
    return p


def adj_tender_price(price_raw: float, fac, t: str, d_entry: date) -> float:
    """Basis rule (frozen): as-announced price -> stored basis via f_cum at entry."""
    if BASIS_RULE != "as_announced_rescale":
        return price_raw
    return price_raw / f_cum(fac, t, d_entry)


def load_tenders(conn) -> list[dict]:
    rows = conn.execute("SELECT ticker, event_id, raw_json FROM corporate_action_events "
                        "WHERE action_type='tenderoffer' ORDER BY ticker, event_id").fetchall()
    out = []
    for tk, eid, rj in rows:
        j = json.loads(rj)
        out.append({
            "ticker": tk, "event_id": str(eid),
            "price_raw": _float(j.get("tender_price")),
            "start": parse_date(j.get("tender_start")),
            "end": parse_date(j.get("tender_end")),
            "paydate": parse_date(j.get("tender_paydate")),
            "pct": _float(j.get("tender_percentage")),
            "created": parse_date(j.get("tender_created")),
            "note": str(j.get("event_note") or ""),
        })
    return out


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Panel:
    """Walkforward ohlcv panel (is_final=1) with per-bar true-ADV and masked
    total returns. Access to a bar's price is the CALLER's responsibility:
    G0 code may only touch indices <= the event's entry index."""

    def __init__(self, conn, fac, divs):
        self.fac = fac
        self.divs = divs
        self.tickers: dict[str, dict] = {}
        sess = set()
        for t, d, o, h, l, c, v in conn.execute(
                "SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                "WHERE COALESCE(is_final,1)=1 ORDER BY ticker, date"):
            dd = parse_date(d)
            if dd is None:
                continue
            sess.add(dd)
            g = self.tickers.get(t)
            if g is None:
                g = self.tickers[t] = {"d": [], "c": [], "v": [], "h": [], "l": []}
            g["d"].append(dd)
            g["c"].append(float(c))
            g["v"].append(float(v))
            g["h"].append(float(h))
            g["l"].append(float(l))
        for g in self.tickers.values():
            for k in ("c", "v", "h", "l"):
                g[k] = np.asarray(g[k], float)
        self.sessions: list[date] = sorted(sess)
        self.last_session = self.sessions[-1] if self.sessions else None
        self._split_days: dict[str, set[date]] = {
            t: {d for d, _ in v} for t, v in fac.items()}
        self._rights_days = self._load_rights_days(conn)
        self._build()

    def _load_rights_days(self, conn) -> dict[str, set[date]]:
        out: dict[str, set[date]] = {}
        for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                                  "WHERE action_type='rightissue'").fetchall():
            d = parse_date(json.loads(rj).get("rightissue_exdate"))
            if d is not None:
                out.setdefault(t, set()).add(d)
        return out

    def _build(self):
        for t, g in self.tickers.items():
            n = len(g["d"])
            f = np.asarray([f_cum(self.fac, t, d) for d in g["d"]])
            cv_true = g["c"] * f * g["v"]
            adv_true = np.full(n, np.nan)
            if n > ADV_WINDOW:
                cs = np.cumsum(np.concatenate([[0.0], cv_true]))
                adv_true[ADV_WINDOW:] = (cs[ADV_WINDOW:n] - cs[:n - ADV_WINDOW]) / ADV_WINDOW
            g["f"] = f
            g["adv_true"] = adv_true          # at bar i: bars i-20..i-1
            prev = np.concatenate([[np.nan], g["c"][:-1]])
            div = np.asarray([self.divs.get((t, d), 0.0) for d in g["d"]])
            with np.errstate(invalid="ignore", divide="ignore"):
                r = (g["c"] + div) / prev - 1.0
            r[~np.isfinite(r)] = np.nan
            r[np.abs(r) > BAD_PRINT] = np.nan
            g["ret"] = r

    def bar_index(self, t: str, d: date) -> int | None:
        g = self.tickers.get(t)
        if g is None:
            return None
        import bisect
        i = bisect.bisect_left(g["d"], d)
        if i < len(g["d"]) and g["d"][i] == d:
            return i
        return None

    def session_index(self, d: date) -> int | None:
        import bisect
        i = bisect.bisect_left(self.sessions, d)
        if i < len(self.sessions) and self.sessions[i] == d:
            return i
        return None

    def last_session_before(self, d: date) -> date | None:
        import bisect
        i = bisect.bisect_left(self.sessions, d) - 1
        return self.sessions[i] if i >= 0 else None

    def last_session_on_or_before(self, d: date) -> date | None:
        import bisect
        i = bisect.bisect_right(self.sessions, d) - 1
        return self.sessions[i] if i >= 0 else None

    def sessions_in(self, d0: date, d1: date) -> int:
        import bisect
        return bisect.bisect_right(self.sessions, d1) - bisect.bisect_left(self.sessions, d0)


def sigma_d(panel: Panel, t: str, d_entry: date) -> float | None:
    """SD of the ticker's daily total returns over the defined returns
    strictly before the entry session (up to SD_WIN values, >= SD_MIN)."""
    g = panel.tickers.get(t)
    if g is None:
        return None
    i_e = panel.bar_index(t, d_entry)
    stop = i_e if i_e is not None else int(np.searchsorted(g["d"], d_entry))
    vals = [float(x) for x in g["ret"][:stop][~np.isnan(g["ret"][:stop])]][-SD_WIN:]
    if len(vals) < SD_MIN:
        return None
    return float(np.std(vals, ddof=1))


def d059_cost(panel: Panel, t: str, d_entry: date, adv: float | None) -> float | None:
    """D-059 round trip at entry (PRE-event: the 21 bars ending the bar before
    entry): 0.50% fees + AR spread floored at one tick + 2*sigma_d*sqrt(Q/ADV)."""
    g = panel.tickers.get(t)
    if g is None or adv is None or adv <= 0:
        return None
    i_e = panel.bar_index(t, d_entry)
    stop = i_e if i_e is not None else int(np.searchsorted(g["d"], d_entry))
    lo = max(0, stop - 21)
    terms = [(float(g["c"][i]), float(g["h"][i]), float(g["l"][i])) for i in range(lo, stop)]
    if len(terms) < 2:
        return None
    c = np.asarray([x[0] for x in terms])
    h = np.asarray([x[1] for x in terms])
    lo_ = np.asarray([x[2] for x in terms])
    ar = CB.ar_terms(c, h, lo_)
    s = CB.ar_spread_from_terms(ar[:-1])
    last_close = float(c[-1])
    tick = float(CB.tick_size(np.asarray([last_close]))[0])
    s = max(s, tick / last_close)
    sd = sigma_d(panel, t, d_entry)
    impact = 2.0 * (sd or 0.0) * math.sqrt(Q_SIZE / adv)
    return FEES + s + impact


def prefacts(panel: Panel, ev: dict) -> dict | None:
    """PRE-EVENT facts only (PIT test (a) target): entry session/close, the
    basis-adjusted offer, spread, true-ADV20 and the D-059 cost. Reads bars
    at indices <= the entry index only. None if no entry bar exists."""
    d_entry = panel.last_session_before(ev["start"])
    if d_entry is None:
        return None
    i_e = panel.bar_index(ev["ticker"], d_entry)
    if i_e is None:
        return None
    c_entry = float(panel.tickers[ev["ticker"]]["c"][i_e])
    out = {"d_entry": d_entry, "i_entry": i_e, "close_entry": c_entry,
           "volume_entry": float(panel.tickers[ev["ticker"]]["v"][i_e]),
           "prebars": i_e,
           "f_cum_entry": f_cum(panel.fac, ev["ticker"], d_entry)}
    out["price_adj"] = adj_tender_price(ev["price_raw"], panel.fac, ev["ticker"], d_entry)
    out["spread"] = out["price_adj"] / c_entry - 1.0
    if i_e >= ADV_WINDOW:
        out["adv20"] = float(panel.tickers[ev["ticker"]]["adv_true"][i_e])
        if np.isfinite(out["adv20"]) and out["adv20"] > 0:
            out["cost"] = d059_cost(panel, ev["ticker"], d_entry, out["adv20"])
    out["sigma_d"] = sigma_d(panel, ev["ticker"], d_entry)
    return out


def eligibility(panel: Panel, ev: dict) -> dict:
    """The frozen population (D-074 + brief). PRE-EVENT ONLY: every price it
    touches is at or before the entry close (prefacts); window "length" is a
    session COUNT (calendar fact), never a post-entry price."""
    out = dict(ev)
    out["stage"] = None
    # rule 1: fields parse, price > 0, start < end, >= 2 window sessions
    if (out["price_raw"] is None or out["price_raw"] <= 0
            or out["start"] is None or out["end"] is None
            or not (out["start"] < out["end"])):
        out["stage"] = "S1_rule1"
        return out
    if panel.sessions_in(out["start"], out["end"]) < MIN_WINDOW_SESSIONS:
        out["stage"] = "S1_rule1"
        return out
    # settled: tender_end on or before the panel's last session (open offers
    # belong to the forward recorder, not the historical population)
    if panel.last_session is None or out["end"] > panel.last_session:
        out["stage"] = "S2_settled"
        return out
    d_exit = panel.last_session_on_or_before(out["end"])
    pf = prefacts(panel, out)
    if pf is None or pf["close_entry"] <= 0:
        out["stage"] = "S3_entry"
        return out
    out.update(pf)
    out["d_exit"] = d_exit
    out["window_sessions"] = panel.sessions_in(pf["d_entry"], d_exit) - 1  # sessions in (entry, exit]
    if pf["prebars"] < ADV_WINDOW:
        out["stage"] = "S4_prebars"
        return out
    if pf["volume_entry"] <= 0:
        out["stage"] = "S5_volume"
        return out
    if not (out["spread"] > 0):
        out["stage"] = "S6_above"
        return out
    if not (np.isfinite(out.get("adv20", np.nan)) and out["adv20"] >= ADV_MIN):
        out["stage"] = "S7_adv"
        return out
    if out.get("cost") is None or not (out["spread"] >= SPREAD_FLOOR + out["cost"]):
        out["stage"] = "S8_spread"
        return out
    # guards: split/bonus/reverse/rights ex-date inside (entry, exit]; FORU
    if out["ticker"] == "FORU" and out["start"] >= FORU_CUTOFF:
        out["stage"] = "S9_guard"
        return out
    ex = (panel._split_days.get(out["ticker"], set())
          | panel._rights_days.get(out["ticker"], set()))
    if any(pf["d_entry"] < x <= d_exit for x in ex):
        out["stage"] = "S9_guard"
        out["guard_hit"] = "ca_exdate_in_window"
        return out
    out["stage"] = "ELIGIBLE"
    return out
