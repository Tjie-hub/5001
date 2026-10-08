"""Dividend clientele (HYP-PM-0017 draft, family {SE}, D-073) — G0-frozen module.

PRE-EVENT ONLY. This module and `g0_census.py` never compute, print or store a
return after any event's entry (D1 entry close / D2 cum close). All price reads
behind the census are strictly pre-entry: ADV20, the cum-1 close (the yield
denominator, itself pre-entry), Parkinson-60 and the pre-event volatilities the
power section needs. The outcome machinery lives in `outcomes.py`, which
neither this file nor `g0_census.py` imports (AST-tested).

Conventions frozen here (PREDECLARATION.md §2-§4):
- Sessions: the DISTINCT dates of `ohlcv` (COALESCE(is_final,1)=1), sorted.
- ADV20: mean(close*volume) over the 20 most recent of the ticker's last 21
  bars STRICTLY before the reference date (the frozen feasibility census
  convention, `structural_events_census.py`); fewer than 21 bars -> undefined.
- Park60: sqrt( mean(ln(H/L)^2) / (4*ln 2) ) over the 60 ticker sessions
  STRICTLY before the reference date; fewer than 61 bars -> undefined.
- D1 anchor: the EARLIER of (a) the latest `rups_date` 1-90 calendar days
  before cum, (b) `dividend_created` when it is < cum, < exdate, and on a
  created date shared by <= 50 dividend rows (the artefact test). No anchor ->
  dropped from D1, kept in D2.
- D1 entry: the close of the LATER of (cum - 10 sessions) and the first
  session strictly after the anchor. Window = cum - entry in sessions; kept
  only at 3..10.
- D2 population: yield = dividend / close at the session immediately before
  cum (ticker bar on that exact session; missing -> undefined), yield >= 2%.
- Exclusions (event-level, both arms): corporate-action ex-date (split, bonus,
  reverse split, rights) inside [cum-10 sessions, ex+1 session]; missing
  ticker bar at cum or ex; FORU from 2026-09-14 (D-063).
- Halves: cum <= 2023-12-31 and cum >= 2024-01-01.

Read-only DB only. `DB_PATH` (data.db) selects the pinned snapshot at run
time; the census records the snapshot sha256 and dataset fingerprint.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.db import connect as db_connect  # noqa: E402
from research.tracking import dataset_fingerprint  # noqa: E402

# --- frozen constants -------------------------------------------------------
ADV_MIN = 10.0e9
ADV_WINDOW = 20
ADV_BARS = 21            # feasibility convention: need 21 pre-bars, mean of the last 20
PARK_WINDOW = 60
PARK_BARS = 61
WINDOW_MAX = 10          # D1: entry at cum-10 sessions at the earliest
WINDOW_MIN = 3           # D1: events with a shorter window are dropped
RUPS_MIN_DAYS, RUPS_MAX_DAYS = 1, 90
CREATED_SHARE_MAX = 50   # a created date shared by more events than this is a bulk load
YIELD_MIN = 0.02
TAX_FACTOR = 0.9         # 10% resident final withholding (D-073)
ROUND_TRIP = 0.006       # frozen 0.60% round trip (arms' cost)
FORU_CUTOFF = date(2026, 9, 14)      # D-063
HALF_SPLIT = date(2023, 12, 31)      # cum <= -> half 1, else half 2
CENSUS_LEDGER = 605      # re-frozen 2026-10-08: 599 (D-071/D-072) + 2 exploratory arms
                         # (A/D-trap, volume-profile swing) + 4 NR7 post-mortem entry-time
                         # comparisons (owner re-freeze; was 601 at the first freeze)
CENSUS_N = CENSUS_LEDGER + 2          # + this G0's two arms (D1, D2)
SNAPSHOT_DEFAULT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"

# e_max_abs_z: import the frozen exact implementation (bar_v2.py, D-064 §C).
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "bar_v2", REPO_ROOT / "docs" / "research_programs" / "deflation_audit" / "bar_v2.py")
_bar = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bar)
e_max_abs_z = _bar.e_max_abs_z
BAR_EXACT = e_max_abs_z(CENSUS_N)
BAR_FROZEN = round(BAR_EXACT, 4)  # 3.2968 at N=607 (re-frozen 2026-10-08; was 3.2950 at 603)


def parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


# --- panel ------------------------------------------------------------------
class Panel:
    """Per-ticker OHLCV arrays + the market session calendar. Read-only."""

    def __init__(self, conn):
        rows = conn.execute(
            "SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
            "WHERE COALESCE(is_final,1)=1 ORDER BY ticker, date").fetchall()
        self.tickers: dict[str, dict] = {}
        sess = set()
        for t, d, o, h, l, c, v in rows:
            dd = parse_date(d)
            if dd is None:
                continue
            sess.add(dd)
            g = self.tickers.get(t)
            if g is None:
                g = self.tickers[t] = {"d": [], "o": [], "h": [], "l": [], "c": [], "v": []}
            g["d"].append(dd)
            g["o"].append(float(o) if o is not None else np.nan)
            g["h"].append(float(h) if h is not None else np.nan)
            g["l"].append(float(l) if l is not None else np.nan)
            g["c"].append(float(c) if c is not None else np.nan)
            g["v"].append(float(v) if v is not None else np.nan)
        for g in self.tickers.values():
            for k in ("o", "h", "l", "c", "v"):
                g[k] = np.asarray(g[k], float)
        self.sessions: list[date] = sorted(sess)
        self._sess_idx = {d: i for i, d in enumerate(self.sessions)}

    def session_index(self, d: date) -> int | None:
        return self._sess_idx.get(d)

    def next_session(self, d: date) -> date | None:
        """First market session STRICTLY after calendar date d."""
        i = bisect.bisect_right(self.sessions, d)
        return self.sessions[i] if i < len(self.sessions) else None

    def bar_at(self, t: str, d: date) -> int | None:
        g = self.tickers.get(t)
        if g is None:
            return None
        i = bisect.bisect_left(g["d"], d)
        if i < len(g["d"]) and g["d"][i] == d:
            return i
        return None

    def last_bar_before(self, t: str, d: date, n: int) -> tuple[int, int] | None:
        """Slice (i0, i1) of the ticker's last `n` bars STRICTLY before d."""
        g = self.tickers.get(t)
        if g is None:
            return None
        i1 = bisect.bisect_left(g["d"], d)
        if i1 < n:
            return None
        return (i1 - n, i1)

    def adv20(self, t: str, d: date) -> float | None:
        """Feasibility convention: last 21 pre-bars, mean of the most recent 20."""
        sl = self.last_bar_before(t, d, ADV_BARS)
        if sl is None:
            return None
        i0, i1 = sl
        g = self.tickers[t]
        cv = g["c"][i0 + 1:i1] * g["v"][i0 + 1:i1]
        if not np.isfinite(cv).all():
            return None
        return float(cv.mean())

    def park60(self, t: str, d: date) -> float | None:
        sl = self.last_bar_before(t, d, PARK_BARS)
        if sl is None:
            return None
        i0, i1 = sl
        g = self.tickers[t]
        hl = np.log(g["h"][i0:i1] / g["l"][i0:i1])
        if not np.isfinite(hl).all():
            return None
        return float(math.sqrt((hl ** 2).mean() / (4.0 * math.log(2.0))))

    def close_before(self, t: str, d: date):
        """(close, date) of the ticker's last bar STRICTLY before d."""
        g = self.tickers.get(t)
        if g is None:
            return None
        i1 = bisect.bisect_left(g["d"], d)
        if i1 == 0:
            return None
        return float(g["c"][i1 - 1]), g["d"][i1 - 1]

    def vol60_daily(self, t: str, d: date) -> float | None:
        """SD of close-to-close simple returns over the 60 sessions before d."""
        sl = self.last_bar_before(t, d, PARK_BARS)
        if sl is None:
            return None
        i0, i1 = sl
        c = self.tickers[t]["c"][i0:i1]
        r = c[1:] / c[:-1] - 1.0
        if not np.isfinite(r).all() or len(r) < 30:
            return None
        return float(r.std(ddof=1))

    def vol60_overnight(self, t: str, d: date) -> float | None:
        """SD of overnight (open vs prior close) returns over the 60 sessions before d."""
        sl = self.last_bar_before(t, d, PARK_BARS)
        if sl is None:
            return None
        i0, i1 = sl
        g = self.tickers[t]
        on = g["o"][i0 + 1:i1] / g["c"][i0:i1 - 1] - 1.0
        if not np.isfinite(on).all() or len(on) < 30:
            return None
        return float(on.std(ddof=1))

    def universe_decile(self, d: date, park: float) -> int | None:
        """Parkinson-60 decile (1..10) of `park` among the LIQUID universe at d
        (ADV20 through d-1 >= Rp 10bn, park60 through d-1 defined). Deciles are
        the sorted-value deciles of that day's cross-section."""
        vals = []
        for t, g in self.tickers.items():
            if bisect.bisect_left(g["d"], d) == 0:
                continue
            p = self.park60(t, d)
            if p is None:
                continue
            a = self.adv20(t, d)
            if a is not None and a >= ADV_MIN:
                vals.append(p)
        if park is None or len(vals) < 10:
            return None
        vals.sort()
        n = len(vals)
        edges = [vals[min(n - 1, int(round(q * (n - 1))))] for q in np.arange(1, 10) / 10.0]
        return int(bisect.bisect_left(edges, park * (1 + 1e-12)) + 1)


# --- inputs -----------------------------------------------------------------
def load_dividend_rows(conn) -> tuple[list[dict], dict]:
    """Parsed dividend rows (deduped by dividend_id) + data-quality counters."""
    raw = conn.execute(
        "SELECT ticker, raw_json FROM corporate_action_events "
        "WHERE action_type='dividend'").fetchall()
    st = {"n_rows": len(raw), "n_dup_id": 0, "n_bad_currency": 0, "n_value_le_0": 0,
          "n_missing_dates": 0, "n_ex_le_cum": 0}
    seen, out = set(), []
    for t, rj in raw:
        j = json.loads(rj)
        did = str(j.get("dividend_id"))
        if did in seen:
            st["n_dup_id"] += 1
            continue
        seen.add(did)
        if j.get("dividend_currency") != "CURRENCY_IDR":
            st["n_bad_currency"] += 1
            continue
        try:
            val = float(j.get("dividend_value"))
        except (TypeError, ValueError):
            st["n_value_le_0"] += 1
            continue
        if not val > 0:
            st["n_value_le_0"] += 1
            continue
        cum, ex, cr = (parse_date(j.get("dividend_cumdate")),
                       parse_date(j.get("dividend_exdate")),
                       parse_date(j.get("dividend_created")))
        if cum is None or ex is None:
            st["n_missing_dates"] += 1
            continue
        if ex <= cum:
            st["n_ex_le_cum"] += 1
            continue
        out.append({"ticker": t, "dividend_id": did, "value": val,
                    "cum": cum, "ex": ex, "created": cr,
                    "paydate": parse_date(j.get("dividend_paydate"))})
    return out, st


def created_date_freq(rows: list[dict]) -> dict[date, int]:
    f: dict[date, int] = {}
    for r in rows:
        if r["created"] is not None:
            f[r["created"]] = f.get(r["created"], 0) + 1
    return f


def created_is_artefact(r: dict, freq: dict[date, int]) -> str | None:
    """The frozen artefact test. Returns None (usable) or the reason string."""
    cr = r["created"]
    if cr is None:
        return "created_missing"
    if r["ex"] is not None and cr >= r["ex"]:
        return "created_ge_exdate"
    if freq.get(cr, 0) > CREATED_SHARE_MAX:
        return "created_bulk_load"
    return None


def load_ca_exdates(conn) -> dict[str, list[date]]:
    """Split/bonus/reverse-split/rights ex-dates per ticker (the exclusion set)."""
    out: dict[str, list[date]] = {}
    for at, field in (("stocksplit", "stocksplit_exdate"), ("bonus", "stocksplit_exdate"),
                      ("stock_reverse", "stocksplit_exdate"), ("rightissue", "rightissue_exdate")):
        for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                                  "WHERE action_type=?", (at,)).fetchall():
            d = parse_date(json.loads(rj).get(field))
            if d is not None:
                out.setdefault(t, []).append(d)
    return {t: sorted(set(v)) for t, v in out.items()}


def load_rups(conn) -> dict[str, list[date]]:
    out: dict[str, list[date]] = {}
    for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                              "WHERE action_type='rups'").fetchall():
        d = parse_date(json.loads(rj).get("rups_date"))
        if d is not None:
            out.setdefault(t, []).append(d)
    return {t: sorted(set(v)) for t, v in out.items()}


# --- event build (pre-event only) -------------------------------------------
def build_events(panel: Panel, rows: list[dict], freq: dict[date, int],
                 ca_ex: dict[str, list[date]], rups: dict[str, list[date]]) -> dict:
    """One event per (ticker, cum date), dividends summed; then the frozen
    exclusion funnel. NOTHING after an event's entry/cum close is read."""
    merged: dict[tuple[str, date], dict] = {}
    for r in rows:
        k = (r["ticker"], r["cum"])
        if k in merged:
            merged[k]["value"] += r["value"]
            merged[k]["n_merged"] += 1
        else:
            merged[k] = dict(r, n_merged=1)
    events = sorted(merged.values(), key=lambda r: (r["cum"], r["ticker"]))
    funnel = {"n_rows": len(rows), "n_events_merged": len(events)}

    kept, drop = [], {k: 0 for k in (
        "cum_not_session", "ex_mismatch", "ca_in_window", "missing_bar_cum",
        "missing_bar_ex", "foru", "not_liquid")}
    for ev in events:
        t, cum = ev["ticker"], ev["cum"]
        ci = panel.session_index(cum)
        if ci is None:
            drop["cum_not_session"] += 1
            continue
        exs = panel.next_session(cum)
        if exs != ev["ex"]:
            drop["ex_mismatch"] += 1
            continue
        ev["cum_session"], ev["ex_session"] = ci, panel.session_index(exs)
        ev["cum_session_date"], ev["ex_session_date"] = cum, exs
        # corporate-action exclusion: any CA ex-date in [cum-10 sessions, ex+1 session]
        lo = panel.sessions[max(0, ci - WINDOW_MAX)]
        hi = panel.sessions[min(len(panel.sessions) - 1, ev["ex_session"] + 1)]
        if any(lo <= d <= hi for d in ca_ex.get(t, ())):
            drop["ca_in_window"] += 1
            continue
        if panel.bar_at(t, cum) is None:
            drop["missing_bar_cum"] += 1
            continue
        if panel.bar_at(t, ev["ex"]) is None:
            drop["missing_bar_ex"] += 1
            continue
        if t == "FORU" and cum >= FORU_CUTOFF:
            drop["foru"] += 1
            continue
        adv = panel.adv20(t, cum)
        ev["adv20"] = adv
        if adv is None or adv < ADV_MIN:
            drop["not_liquid"] += 1
            continue
        kept.append(ev)
    funnel["drops"] = drop
    funnel["n_liquid"] = len(kept)

    # pre-event metrics on the liquid set
    for ev in kept:
        t, cum = ev["ticker"], ev["cum"]
        cb = panel.close_before(t, cum)          # yield denominator: close at cum-1
        ev["yield_close_date"] = cb[1] if cb else None
        ev["yield"] = ev["value"] / cb[0] if cb else None
        ev["entry_max_session"] = ev["cum_session"] - WINDOW_MAX
        # anchor (a): latest rups_date in [cum-90, cum-1] calendar days
        cands = [d for d in rups.get(t, ())
                 if cum - timedelta(days=RUPS_MAX_DAYS) <= d <= cum - timedelta(days=RUPS_MIN_DAYS)]
        ev["rups_anchor"] = max(cands) if cands else None
        # anchor (b): non-artefact created before cum
        ev["created_artefact"] = created_is_artefact(ev, freq)
        ev["created_anchor"] = (ev["created"] if (ev["created_artefact"] is None
                                                  and ev["created"] is not None
                                                  and ev["created"] < cum) else None)
        anchors = [d for d in (ev["rups_anchor"], ev["created_anchor"]) if d is not None]
        ev["anchor"] = min(anchors) if anchors else None
        if ev["anchor"] is not None:
            nxt = panel.next_session(ev["anchor"])
            ei = max(ev["entry_max_session"], panel.session_index(nxt) or 0)
            ev["entry_session"] = ei if ei < ev["cum_session"] else None
        else:
            ev["entry_session"] = None
        ev["window"] = (ev["cum_session"] - ev["entry_session"]
                        if ev["entry_session"] is not None else None)
        ev["entry_session_date"] = (panel.sessions[ev["entry_session"]]
                                    if ev["entry_session"] is not None else None)
        ev["entry_bar_ok"] = bool(ev["entry_session"] is not None
                                  and panel.bar_at(t, ev["entry_session_date"]) is not None)
        ev["park60_entry"] = panel.park60(t, cum) if ev["entry_session"] is None \
            else panel.park60(t, ev["entry_session_date"])
        ev["park_decile_entry"] = (panel.universe_decile(ev["entry_session_date"], ev["park60_entry"])
                                   if ev["entry_session"] is not None
                                   else panel.universe_decile(cum, ev["park60_entry"]))
        ev["vol60_entry"] = panel.vol60_daily(t, ev["entry_session_date"] or cum)
        ev["vol60_on_cum"] = panel.vol60_overnight(t, cum)
        half = 1 if cum <= HALF_SPLIT else 2
        ev["half"] = half
        ev["month"] = cum.strftime("%Y-%m")
        ev["agm_season"] = cum.month in (5, 6, 7)
    return {"events": kept, "funnel": funnel}


# --- census (counts only) ---------------------------------------------------
def census_g0(db_path: str | None = None) -> dict:
    """COUNTS ONLY. No return after any entry/cum close is computed, printed or
    stored here (see module docstring; AST-tested in the PIT suite)."""
    conn = db_connect(path=db_path, read_only=True)
    fp = dataset_fingerprint(conn)
    panel = Panel(conn)
    rows, dq = load_dividend_rows(conn)
    freq = created_date_freq(rows)
    ca_ex = load_ca_exdates(conn)
    rups = load_rups(conn)
    conn.close()
    built = build_events(panel, rows, freq, ca_ex, rups)
    ev = built["events"]

    # dividend_created distribution + artefact tallies
    created_year: dict[int, int] = {}
    for r in rows:
        if r["created"] is not None:
            created_year[r["created"].year] = created_year.get(r["created"].year, 0) + 1
    art = {"created_missing": 0, "created_ge_exdate": 0, "created_bulk_load": 0, "usable": 0}
    for r in rows:
        a = created_is_artefact(r, freq)
        art[a or "usable"] += 1
    top_shared = sorted(((d.isoformat(), n) for d, n in freq.items()),
                        key=lambda kv: -kv[1])[:10]

    # D1 / D2 populations
    d1 = [e for e in ev if e["anchor"] is not None and e["window"] is not None
          and WINDOW_MIN <= e["window"] <= WINDOW_MAX and e["entry_bar_ok"]]
    d1_no_entry_bar = [e for e in ev if e["anchor"] is not None and e["window"] is not None
                       and WINDOW_MIN <= e["window"] <= WINDOW_MAX and not e["entry_bar_ok"]]
    d2 = [e for e in ev if e["yield"] is not None and e["yield"] >= YIELD_MIN]
    d2_no_yield = sum(1 for e in ev if e["yield"] is None)

    def by_year(es):
        y: dict[int, int] = {}
        for e in es:
            y[e["cum"].year] = y.get(e["cum"].year, 0) + 1
        return {str(k): v for k, v in sorted(y.items())}

    def halves(es):
        return {"h1_le_2023_12_31": sum(1 for e in es if e["half"] == 1),
                "h2_ge_2024_01_01": sum(1 for e in es if e["half"] == 2)}

    win: dict[int, int] = {}
    for e in d1:
        win[e["window"]] = win.get(e["window"], 0) + 1
    rups_gaps = sorted((e["cum"] - e["rups_anchor"]).days for e in ev if e["rups_anchor"])
    created_gaps = sorted((e["cum"] - e["created_anchor"]).days
                          for e in ev if e["created_anchor"])

    ys = sorted(e["yield"] for e in d2)
    tert = (ys[int(0.33333 * (len(ys) - 1))], ys[int(0.66667 * (len(ys) - 1))])

    def med(v):
        v = sorted(x for x in v if x is not None)
        return float(np.median(v)) if v else None

    # power, pre-event sigma only
    d1_sig = med([e["vol60_entry"] for e in d1])
    d2_sig = med([e["vol60_on_cum"] for e in d2])
    d1_h = med([e["window"] for e in d1]) or 0
    n1m = len({e["month"] for e in d1})
    power = {
        "bar_frozen": BAR_FROZEN,
        "d1": {"n": len(d1), "median_window_sessions": d1_h,
               "sigma_daily_median": d1_sig,
               "mde_independent": BAR_EXACT * (d1_sig or 0) * math.sqrt(d1_h) / math.sqrt(len(d1) or 1),
               "n_months": n1m,
               "mde_month_clustered": BAR_EXACT * (d1_sig or 0) * math.sqrt(d1_h) / math.sqrt(n1m or 1)},
        "d2": {"n": len(d2), "sigma_overnight_median": d2_sig,
               "mde_independent": BAR_EXACT * (d2_sig or 0) / math.sqrt(len(d2) or 1)},
    }

    deciles: dict[int, int] = {}
    for e in ev:
        if e["park_decile_entry"] is not None:
            deciles[e["park_decile_entry"]] = deciles.get(e["park_decile_entry"], 0) + 1

    # PIT asserts on the real population (metadata only)
    assert all(e["anchor"] < e["entry_session_date"] for e in d1)
    assert all(WINDOW_MIN <= e["window"] <= WINDOW_MAX for e in d1)

    return {
        "rule": "COUNTS ONLY: no return after any event's entry/cum close was computed, "
                "printed or stored (D-070 rule 1; PREDECLARATION §9)",
        "snapshot": {"path": db_path or SNAPSHOT_DEFAULT,
                     "sha256": _sha256(db_path or SNAPSHOT_DEFAULT),
                     "dataset_fingerprint": fp},
        "census": {"ledger": CENSUS_LEDGER,
                   "ledger_rows_counted": [
                       "599 after D-071/D-072 (D-071's ratified 595 in its 9 components "
                       "+ HYP-PM-0016's 4 configurations)",
                       "+2 exploratory arms run 2026-10-08 (A/D 'trap' check, "
                       "volume-profile swing check), both null (D-075 census note)",
                       "+4 NR7 post-mortem entry-time comparisons run 2026-10-08 (gap size, "
                       "stop distance in ATR, planned R:R, ADV; each across both halves with "
                       "a permutation test)"],
                   "n_this_g0_arms": 2,
                   "N": CENSUS_N, "bar_exact": round(BAR_EXACT, 6),
                   "bar_frozen": BAR_FROZEN},
        "dividend_rows": dq,
        "events_merged": built["funnel"],
        "created": {"per_year": {str(k): v for k, v in sorted(created_year.items())},
                    "top_shared_dates": top_shared,
                    "artefact_tally": art,
                    "usable_created_lt_cum": sum(1 for r in rows if r["created"] is not None
                                                 and created_is_artefact(r, freq) is None
                                                 and r["created"] < r["cum"])},
        "rups": {"tickers": len(rups),
                 "earliest": min((d for v in rups.values() for d in v), default=None).__str__(),
                 "anchor_gaps_cal_days_p25_p50_p75": [
                     rups_gaps[len(rups_gaps) // 4], rups_gaps[len(rups_gaps) // 2],
                     rups_gaps[3 * len(rups_gaps) // 4]] if rups_gaps else [],
                 "created_gap_cal_days_p25_p50_p75": [
                     created_gaps[len(created_gaps) // 4], created_gaps[len(created_gaps) // 2],
                     created_gaps[3 * len(created_gaps) // 4]] if created_gaps else []},
        "liquid_events": {"n": len(ev), "per_year": by_year(ev), "halves": halves(ev),
                          "agm_season_share": round(sum(e["agm_season"] for e in ev) / len(ev), 4)
                          if ev else None,
                          "park_decile_distribution": {str(k): v for k, v in sorted(deciles.items())}},
        "d1": {"n_final": len(d1), "n_no_entry_bar": len(d1_no_entry_bar),
               "n_no_anchor": sum(1 for e in ev if e["anchor"] is None),
               "n_short_window": sum(1 for e in ev if e["window"] is not None
                                     and e["window"] < WINDOW_MIN),
               "anchor_rups_only": sum(1 for e in ev if e["rups_anchor"] and not e["created_anchor"]),
               "anchor_created_only": sum(1 for e in ev if e["created_anchor"] and not e["rups_anchor"]),
               "anchor_both": sum(1 for e in ev if e["created_anchor"] and e["rups_anchor"]),
               "window_distribution": {str(k): v for k, v in sorted(win.items())},
               "per_year": by_year(d1), "halves": halves(d1)},
        "d2": {"n_yield_ge_2pct": len(d2), "n_yield_undefined": d2_no_yield,
               "yield_tercile_edges": tert, "per_year": by_year(d2), "halves": halves(d2)},
        "power": power,
    }


def _sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()
