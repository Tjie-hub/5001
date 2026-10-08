"""Market-stress reversal (HYP-PM-0019 draft, D-075) — G0-frozen module.

PRE-EVENT ONLY. This module and `g0_census.py` never compute a return after
any stress day's close: the day-t market return r_m(t) is the trigger itself
(D-075: "day-t returns ... define the event"); nothing at t+1 or later enters
any computation here. Basket membership (names) is a decision-side fact known
at the close of t; the basket's RETURN lives in `outcomes.py`, which neither
this file nor `g0_census.py` imports (AST-tested).

Panels (frozen):
- **E1** `data/history_long.db::ohlcv_long` — built by `atr_plan/build_long_db.py`:
  pre-2021-07-05 from the yfinance-derived `hist_pre2021.pkl` (split-adjusted,
  NOT dividend-adjusted; zero-volume bars already dropped), 2021-07-05+ from
  walkforward `ohlcv` is_final=1 (byte-identical vendor basis, verified).
  `adj_close` is a COPY of `close` (builder sets it so), so returns use
  `close` + the dividend add-back (below).
- **E2** walkforward `ohlcv` (is_final=1, raw vendor bars, same basis).
- **Dividend add-back (total return):** `corporate_action_events` IDR cash
  dividends, deduped by dividend_id, summed per (ticker, ex-date). The vendor
  pre-scales `dividend_value` to the stored price basis (verified: AKRA
  2021-08 = 60 = 300/5 for its 1:5 split of 2022-01; ASRM 2021-07 = 194/4.2
  for its 4.2 bonus), so r_t = (close_t + div_on_t)/close_{t-1} - 1 is a
  total-return construction on BOTH panels. CA coverage starts 2009: events
  in 2007-2008 keep price-only legs and are counted.
- **ADV20 (true rupiah):** mean(close x f_cum x volume) over the 20 bars
  strictly before t. Stored closes are split-adjusted to the fetch basis
  (stored = as-traded / f_cum) while volume is as-traded, so the naive
  close x volume understates pre-split rupiah ADV by f_cum; f_cum is the
  product of share-factors of split-class CA rows with ex-date > t
  (stocksplit new/old, bonus stocksplit_factor, stock_reverse new/old).
  The naive-ADV counts are ALSO reported (planner comparison).
- **Bad print:** a name-day with |return| > 35% is dropped (name excluded
  from r_m and basket eligibility that day).

Event (D-075, fixed): liquid set = ADV20 >= Rp 10bn with >= 30 names;
r_m(t) = equal-weight mean of day-t returns over the liquid set; sigma(t) =
SD of the last 250 DEFINED r_m values strictly before t (>= 120 required);
stress day: r_m(t) <= -2.5 sigma(t); a stress day starts a NEW episode iff no
stress day in the previous 5 panel sessions; ONLY the first day of an episode
is an event. E1 events 2007-01-01..2021-06-30 (long panel), E2 from
2021-07-01 (walkforward). Basket = bottom quintile of day-t return among
liquid names with a valid return and volume > 0 (zero-volume ARB names
excluded; E2 additionally drops names with a split-class ex-date at t from
the market and basket that day — raw vendor bars, per D-075).

Read-only DBs. DB_PATH selects the pinned snapshots at run time.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.db import connect as db_connect  # noqa: E402

STRESS_MULT = -2.5
SIG_WIN = 250
SIG_MIN = 120
LIQ_MIN = 30
ADV_MIN = 10.0e9
ADV_WINDOW = 20
QUINTILE = 5
HORIZON = 5
EPISODE_GAP = 5
BAD_PRINT = 0.35
E1_END = date(2021, 6, 30)
E2_START = date(2021, 7, 1)
H1_END = date(2020, 12, 31)
OVERLAP_START = E2_START
PRE_CLOSE_1549 = "15:49"
NEAR_MISS_LO, NEAR_MISS_HI = -3.0, -2.0
WF_SNAPSHOT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"
HL_SNAPSHOT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/history_long_snapshot_2026-10-08.db"
WF_SHA256 = "a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47"
HL_SHA256 = "7d298068fbc5633277ef0c032ed0257f935c9ef902068b16daa75ac0ba5e5714"
CENSUS_LEDGER = 601
N_EXPECTED = 604          # ledger 601 + D-073's 2 arms (registered at Task-1 G0 approval) + 1
N_IF_D074 = 605           # + D-074's 1 arm if registered before this one
FORU_CUTOFF = date(2026, 9, 14)

import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "bar_v2", REPO_ROOT / "docs" / "research_programs" / "deflation_audit" / "bar_v2.py")
_bar = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bar)
e_max_abs_z = _bar.e_max_abs_z
BAR_EXACT_604 = e_max_abs_z(N_EXPECTED)
BAR_EXACT_605 = e_max_abs_z(N_IF_D074)
BAR_FROZEN_604 = round(BAR_EXACT_604, 4)   # 3.2954
BAR_FROZEN_605 = round(BAR_EXACT_605, 4)   # 3.2959


def parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


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
    """Product of share-factors of split-class CA with ex-date STRICTLY after d.
    stored_price(d) = as_traded(d) / f_cum  =>  true ADV uses close * f_cum."""
    p = 1.0
    for de, f in fac.get(t, ()):
        if de > d:
            p *= f
    return p


class Panel:
    """One panel: per-ticker arrays + per-date market aggregation (pre-event)."""

    def __init__(self, conn, fac, divs, name: str):
        self.name = name
        self.fac = fac
        self.divs = divs
        self.tickers: dict[str, dict] = {}
        sess = set()
        if name == "E1":
            rows = conn.execute("SELECT ticker, date, open, high, low, close, volume"
                                " FROM ohlcv_long ORDER BY ticker, date")
        else:
            rows = conn.execute("SELECT ticker, date, open, high, low, close, volume"
                                " FROM ohlcv WHERE COALESCE(is_final,1)=1"
                                " ORDER BY ticker, date")
        for t, d, o, h, l, c, v in rows:
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
        self._sess_set = set(self.sessions)
        self._split_days: dict[str, set[date]] = {}
        for t in fac:
            self._split_days[t] = {d for d, _ in fac[t]}
        self._build()

    def _build(self):
        """Per-ticker: f-cum-adjusted ADV20 (true rupiah) and naive ADV20, both
        for the bar's OWN date, using only that ticker's 20 previous bars;
        daily total-return with dividend add-back; bad-print mask."""
        for t, g in self.tickers.items():
            n = len(g["d"])
            f = np.asarray([f_cum(self.fac, t, d) for d in g["d"]])
            cv_true = g["c"] * f * g["v"]
            cv_naive = g["c"] * g["v"]
            adv_true = np.full(n, np.nan)
            adv_naive = np.full(n, np.nan)
            if n > ADV_WINDOW:
                cs = np.cumsum(np.concatenate([[0.0], cv_true]))
                adv_true[ADV_WINDOW:] = (cs[ADV_WINDOW:n] - cs[:n - ADV_WINDOW]) / ADV_WINDOW
                cs2 = np.cumsum(np.concatenate([[0.0], cv_naive]))
                adv_naive[ADV_WINDOW:] = (cs2[ADV_WINDOW:n] - cs2[:n - ADV_WINDOW]) / ADV_WINDOW
            g["f"] = f
            g["adv_true"] = adv_true     # ADV at bar i uses bars i-20..i-1 (strictly before)
            g["adv_naive"] = adv_naive
            g["liq_true"] = adv_true >= ADV_MIN
            g["liq_naive"] = adv_naive >= ADV_MIN
            prev = np.concatenate([[np.nan], g["c"][:-1]])
            div = np.asarray([self.divs.get((t, d), 0.0) for d in g["d"]])
            with np.errstate(invalid="ignore", divide="ignore"):
                r = (g["c"] + div) / prev - 1.0
            r[~np.isfinite(r)] = np.nan
            r[np.abs(r) > BAD_PRINT] = np.nan     # bad print: name-day dropped
            if self.name == "E2":                 # raw bars: split day untrustworthy
                for i, d in enumerate(g["d"]):
                    if d in self._split_days.get(t, ()):
                        r[i] = np.nan
                g["split_today"] = np.asarray([d in self._split_days.get(t, ())
                                               for d in g["d"]])
            else:
                g["split_today"] = np.zeros(n, bool)
            g["ret"] = r
        # per-date liquid membership (true ADV), day-t valid returns
        self.by_date: dict[date, list[tuple[str, int]]] = {d: [] for d in self.sessions}
        for t, g in self.tickers.items():
            for i, d in enumerate(g["d"]):
                self.by_date[d].append((t, i))
        self.market: dict[date, tuple[float, int, int, int]] = {}
        rm_series: list[tuple[date, float]] = []
        for d in self.sessions:
            rets = []
            arb = split = bad = 0
            for t, i in self.by_date[d]:
                if t == "FORU" and d >= FORU_CUTOFF:
                    continue
                g = self.tickers[t]
                if not (i >= ADV_WINDOW and bool(g["liq_true"][i])):
                    continue
                r = g["ret"][i]
                if np.isnan(r):
                    if g["split_today"][i]:
                        split += 1
                    else:
                        bad += 1
                    continue
                if g["v"][i] <= 0:
                    arb += 1                       # counted; excluded from the BASKET only
                rets.append((r, t))
            n_liq = len(rets)
            if n_liq >= LIQ_MIN and rets:
                rm = float(np.mean([x[0] for x in rets]))
                self.market[d] = (rm, n_liq, arb, split)
                rm_series.append((d, rm))
        self.rm_dates = [d for d, _ in rm_series]
        self.rm_vals = np.asarray([v for _, v in rm_series], float)
        self.sigma: dict[date, float] = {}
        for i, (d, _) in enumerate(rm_series):
            lo = max(0, i - SIG_WIN)
            w = self.rm_vals[lo:i]
            if len(w) >= SIG_MIN:
                s = float(np.std(w, ddof=1))
                if s > 0:
                    self.sigma[d] = s
        self.flags: dict[date, float] = {}
        for d, _ in rm_series:
            if d in self.sigma and self.market[d][0] <= STRESS_MULT * self.sigma[d]:
                self.flags[d] = self.market[d][0] / self.sigma[d]

    def episodes(self) -> list[date]:
        """First stress day of each episode (gap > EPISODE_GAP sessions)."""
        out = []
        last = None
        sess = self.sessions
        idx = {d: i for i, d in enumerate(sess)}
        for d in sorted(self.flags):
            if last is None or idx[d] - idx[last] > EPISODE_GAP:
                out.append(d)
            last = d
        return out

    def basket(self, d: date, drop_tickers: set[str] = frozenset()) -> tuple[list[str], int, int]:
        """Bottom-quintile liquid names by day-t return at the EVENT day d
        (decision-side names only, no forward data). Zero-volume names and
        `drop_tickers` (e.g. FORU) excluded; ties by (return, ticker)."""
        rows = []
        arb = 0
        for t, i in self.by_date[d]:
            g = self.tickers[t]
            if not (i >= ADV_WINDOW and bool(g["liq_true"][i])) or t in drop_tickers:
                continue
            r = g["ret"][i]
            if np.isnan(r):
                continue
            if g["v"][i] <= 0:
                arb += 1
                continue
            rows.append((float(r), t))
        rows.sort()
        n = len(rows)
        k = max(1, n // QUINTILE)
        return [t for _, t in rows[:k]], k, arb

    def liquid_count(self, d: date) -> int:
        return len([1 for t, i in self.by_date.get(d, ())
                    if i >= ADV_WINDOW and bool(self.tickers[t]["liq_true"][i])])


def overlap_agreement(e1: Panel, e2: Panel) -> dict:
    """Stress-flag agreement on both panels over the common 2021-07.. window."""
    common = sorted((set(e1.flags) | set(e1.sigma)) & (set(e2.flags) | set(e2.sigma))
                    & {d for d in e1.rm_dates if d >= OVERLAP_START}
                    & {d for d in e2.rm_dates if d >= OVERLAP_START})
    f1 = {d for d in common if d in e1.flags}
    f2 = {d for d in common if d in e2.flags}
    union = f1 | f2
    disagree = (f1 ^ f2)
    return {
        "window": [str(min(common)) if common else None, str(max(common)) if common else None],
        "days_compared": len(common),
        "flagged_e1": len(f1), "flagged_e2": len(f2), "union": len(union),
        "agree": len(union) - len(disagree), "disagree": len(disagree),
        "disagree_rate_union": round(len(disagree) / len(union), 4) if union else None,
        "disagree_rate_e2": round(len(f2 - f1) / len(f2), 4) if f2 else None,
        "e1_only_dates": sorted(str(d) for d in (f1 - f2)),
        "e2_only_dates": sorted(str(d) for d in (f2 - f1)),
    }
