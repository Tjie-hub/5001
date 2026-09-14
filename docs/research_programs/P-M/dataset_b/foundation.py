#!/usr/bin/env python3
"""Dataset B foundation — session calendar, PIT roster, corporate-action policy,
adjustment-basis residual detector, and calendar-indexed forward returns.

READ-ONLY against the production DB. Writes nothing anywhere.

WHY DETECTION, NOT BLIND ADJUSTMENT
-----------------------------------
The obvious implementation of "handle splits" is to read every recorded split
and divide prices before its ex-date. That would be wrong here and would have
silently corrupted three tickers.

Measured on the Dataset B universe: four splits fall in the window (PTRO 10:1
2025-01-03, CUAN 10:1 2025-07-15, DSSA 25:1 2026-04-09, RAJA 5:1 2026-07-16).
`ohlcv` shows NO discontinuity at three of the four ex-dates -- it is already
split-adjusted for PTRO, CUAN and DSSA (DSSA confirmed independently: its
close/broker-VWAP ratio is 1.0007 before the ex-date and 0.9955 after). Only
RAJA is unadjusted, at 4.9536 before and 0.9928 after.

So the corpus carries a MIXED adjustment basis, and a blanket adjustment would
double-adjust the three that were already correct. This is the exact hazard
CLAUDE.md's data-integrity section names. The policy implemented here is
therefore: detect the realised basis per ticker from the data itself, and adjust
only where a recorded corporate action coincides with an actual discontinuity.

WHY QUARANTINE INSTEAD OF PATCH
-------------------------------
RAJA's `broker_flow` basis is not merely different from `ohlcv`'s -- it is
internally inconsistent. Its broker VWAP reads 885 on 2026-07-13 (post-split
terms) and 4621/4641 on 2026-07-14/15 (pre-split terms), because the vendor
restates history retroactively and those sessions were captured at different
times. A ticker whose own flow record changes basis mid-week cannot be repaired
by a single factor. Such tickers are quarantined -- recorded with a reason,
excluded from the panel -- rather than patched into a plausible-looking series.
"""
from __future__ import annotations

import hashlib, json, sqlite3
from bisect import bisect_left
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
DB_PATH = Path("/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

# close / broker-VWAP must sit within this band for a ticker to be admitted.
# Declared, not tuned: the measured separation is enormous -- 78 clean roster
# tickers sit in 0.995-1.000, RAJA sits at 4.95. Any tolerance between 1% and
# 300% selects the same set; 5% is chosen as a round number well outside
# ordinary intraday VWAP-vs-close dispersion.
VWAP_RATIO_TOLERANCE = 0.05
# A ticker whose own ratio swings by more than this across the window has an
# internally inconsistent basis and is quarantined regardless of its median.
VWAP_RATIO_INSTABILITY = 0.50
MIN_RATIO_OBSERVATIONS = 30

# IDX auto-rejection bands (LC-PM-0006 Fact 2, "current regime"). A daily move
# INSIDE these bands is ordinary market behaviour on this exchange, however large
# it looks: a Rp150 stock may legally rise 35% in one session. A flat percentage
# threshold is therefore the wrong integrity test here -- it produces false
# positives on genuine limit-up days (BUMI 2025-11-11 closed +32.00% with a high
# of 202 against a 202.5 ceiling; KIJA 2026-08-18 closed +34.96% with a high of
# 166 against a 166.05 ceiling -- both landed ON the regulatory limit, which a
# data artifact would not do).
#
# The bands are also a far better corporate-action detector than a flat rule,
# because ARB is -15% for every price tier: RAJA's unadjusted 5:1 split shows
# -80.98%, exceeding the floor by more than five times.
# IDX auto-rejection bands are REGIME-DEPENDENT, and the Dataset B window
# straddles a regime boundary. LC-PM-0009 (this program's own literature card)
# reconstructs the timeline:
#
#   R3  2023-09-04 -> 2025-04-07   SYMMETRIC   ARB = ARA = 35/25/20%
#   R4  2025-04-08 -> present      ASYMMETRIC  ARB = -15% at every tier
#                                  (SK Direksi BEI Kep-00003/BEI/04-2025)
#
# Getting this wrong is not cosmetic. A flat -15% floor applied across the whole
# window flags 13 ordinary sessions as data defects -- every one of them a legal
# R3 down-move (PTRO -24.61% against a symmetric 25% tier, TPIA -19.44% against
# 20%, and so on), and every one before 2025-04-08. Under the regime-aware model
# all 13 resolve and RAJA's unadjusted split remains the sole breach.
#
# LC-PM-0009 also states the consequence for study design directly: "Any pooled
# study across this window measures three different substrates as one and is void
# under B8." Dataset B therefore LABELS each session with its regime rather than
# silently pooling. Restricting or conditioning on it is a study-design decision,
# not a dataset one, but the dataset must make it possible.
BAND_REGIMES = (
    ("R3", "2023-09-04", "2025-04-07", True),    # symmetric
    ("R4", "2025-04-08", None,          False),  # ARB -15%
)
ARA_TIERS = ((200.0, 0.35), (5000.0, 0.25), (float("inf"), 0.20))
ARB_ASYMMETRIC = -0.15
# Tolerance on the band edge: the reference price here is the previous close,
# while IDX computes it from the pre-opening reference, and prices round to the
# tick ladder. IPO first days (2x bands, referenced to the offer price) and Papan
# Pemantauan Khusus call-auction names are NOT modelled -- a hit on either is
# reported for review, never silently excused.
BAND_TOLERANCE = 0.02


def band_regime(session: str) -> str | None:
    for label, frm, to, _ in BAND_REGIMES:
        if frm <= session and (to is None or session <= to):
            return label
    return None


def ara_arb(prev_close: float, session: str) -> tuple[float, float]:
    """(upper, lower) legal daily move for a reference price on a given session."""
    ara = next(a for c, a in ARA_TIERS if prev_close <= c)
    for label, frm, to, symmetric in BAND_REGIMES:
        if frm <= session and (to is None or session <= to):
            return ara, (-ara if symmetric else ARB_ASYMMETRIC)
    return ara, ARB_ASYMMETRIC


def exceeds_band(prev_close: float, close: float, session: str):
    """Is this move outside what IDX would have permitted on that session?
    Returns (exceeds, realised_return, upper_bound, lower_bound, regime)."""
    r = close / prev_close - 1.0
    up, dn = ara_arb(prev_close, session)
    return (r > up + BAND_TOLERANCE or r < dn - BAND_TOLERANCE), r, up, dn, band_regime(session)


def ro_connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Read-only connection. Deliberately not data.db.connect(): a research-side
    builder must be structurally incapable of writing to the production DB."""
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_artifact(name: str, version: str = "v1") -> dict:
    """Load a frozen artifact and verify its recorded SHA-256.

    The whole point of the artifact is that verification reads THIS FILE and
    never re-queries idx_tickers. A hash mismatch is fatal, not a warning."""
    p = ART / f"DATASET_B_{name}_{version}.json"
    obj = json.loads(p.read_text())
    recorded = obj.pop("sha256")
    body = {k: v for k, v in obj.items()
            if k not in ("built_at_utc", "git_commit", "builder", "source_db")}
    actual = hashlib.sha256(_canonical(body).encode()).hexdigest()
    if actual != recorded:
        raise ValueError(f"{p.name}: SHA-256 mismatch — recorded {recorded[:16]}…, "
                         f"recomputed {actual[:16]}…. The artifact has been altered.")
    obj["sha256"] = recorded
    return obj


# ------------------------------------------------------------- calendar ----
@dataclass
class SessionCalendar:
    """The dataset's declared trading sessions. `k_ahead` counts SESSIONS on
    this calendar -- never rows in whatever frame a caller happens to hold,
    which is how positional shift(-k) silently produced 8- and 9-session
    windows for a nominal k=7."""
    sessions: list[str]
    excluded: dict[str, str]
    sha256: str
    _idx: dict[str, int] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, version: str = "v1") -> "SessionCalendar":
        a = load_artifact("SESSION_CALENDAR", version)
        c = cls(sessions=list(a["sessions"]),
                excluded={e["date"]: e["reason"] for e in a["excluded"]},
                sha256=a["sha256"])
        c._idx = {d: i for i, d in enumerate(c.sessions)}
        return c

    def __contains__(self, d: str) -> bool:
        return d in self._idx

    def index(self, d: str) -> int | None:
        return self._idx.get(d)

    def k_ahead(self, d: str, k: int) -> str | None:
        """The session exactly k sessions after d, or None if it runs off the
        end. Never substitutes a nearby session."""
        i = self._idx.get(d)
        if i is None or i + k >= len(self.sessions):
            return None
        return self.sessions[i + k]

    def spans_excluded(self, start: str, end: str) -> list[str]:
        """Excluded sessions falling strictly inside (start, end]. Used by the
        strict contiguity policy: an excluded session must not sit inside a
        forward window, not merely at its endpoints."""
        return [d for d in self.excluded if start < d <= end]


# --------------------------------------------------------------- roster ----
@dataclass
class PitRoster:
    universe: list[str]
    session_members: dict[str, list[str]]
    periods: list[dict]
    sha256: str
    _period_members: dict[str, list[str]] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, version: str = "v1") -> "PitRoster":
        a = load_artifact("PIT_ROSTER", version)
        return cls(universe=list(a["universe"]), session_members=a["session_members"],
                   periods=a["periods"], sha256=a["sha256"],
                   _period_members=a.get("period_members", {}))

    def members(self, session: str) -> list[str]:
        return self.session_members.get(session, [])

    def is_member(self, ticker: str, session: str) -> bool:
        return ticker in self.session_members.get(session, ())

    def members_by_period(self, session: str) -> list[str]:
        """Membership for ANY session in a period's interval, including sessions
        the calendar excluded. session_members only covers admitted sessions, so
        the gap classifier — which must reason about excluded dates — needs this."""
        m = self.session_members.get(session)
        if m is not None:
            return m
        for p in self.periods:
            if p["effective_from"] <= session and (
                    p["effective_to"] is None or session <= p["effective_to"]):
                return self._period_members.get(p["period_label"], [])
        return []

    def confidence(self, session: str) -> str | None:
        for p in self.periods:
            if p["effective_from"] <= session and (
                    p["effective_to"] is None or session <= p["effective_to"]):
                return p["confidence"]
        return None


# --------------------------------------------------- corporate actions -----
def load_corporate_actions(conn, universe: Iterable[str],
                           start: str, end: str) -> list[dict]:
    """Splits and reverse splits from `corporate_action_events` (PRIMARY) with
    `corporate_actions` as a secondary cross-check.

    corporate_action_events is primary because it is the source that actually
    carries the event this dataset needs: RAJA's 2026-07-16 5:1 split is present
    there (stocksplit_new=5, stocksplit_old=1) and absent from
    corporate_actions, whose latest write predates the window end."""
    uni = set(universe)
    out = []
    for tk, atype, eid, edate, raw in conn.execute(
            "SELECT ticker, action_type, event_id, event_date, raw_json "
            "FROM corporate_action_events WHERE action_type IN ('stocksplit','stock_reverse') "
            "AND event_date >= ? AND event_date <= ?", (start, end)):
        if tk not in uni:
            continue
        j = json.loads(raw)
        pre = "stocksplit" if atype == "stocksplit" else "stock_reverse"
        try:
            new = float(j.get(f"{pre}_new") or 0)
            old = float(j.get(f"{pre}_old") or 0)
        except (TypeError, ValueError):
            new = old = 0.0
        if not new or not old:
            out.append({"ticker": tk, "ex_date": edate, "type": atype, "factor": None,
                        "event_id": eid, "source": "corporate_action_events",
                        "note": "ratio not recoverable from payload"})
            continue
        out.append({"ticker": tk, "ex_date": edate, "type": atype,
                    "factor": new / old, "event_id": eid,
                    "source": "corporate_action_events"})
    secondary = {(r[0], r[1]): r[2] for r in conn.execute(
        "SELECT ticker, date, value FROM corporate_actions "
        "WHERE action='split' AND date >= ? AND date <= ?", (start, end))}
    for e in out:
        e["secondary_factor"] = secondary.get((e["ticker"], e["ex_date"]))
    return sorted(out, key=lambda e: (e["ticker"], e["ex_date"]))


def detect_unapplied_splits(conn, actions: list[dict], jump_tol: float = 0.25) -> list[dict]:
    """For each recorded split, decide whether `ohlcv` ALREADY reflects it.

    Test: the raw close-to-close return across the ex-date. If the series is
    unadjusted the return is approximately 1/factor - 1 (a 5:1 split shows about
    -80%). If it is already adjusted the return is an ordinary daily move."""
    res = []
    for a in actions:
        if not a["factor"]:
            a = {**a, "applied_in_ohlcv": None, "observed_return": None}
            res.append(a); continue
        row = conn.execute(
            "SELECT date, close FROM ohlcv WHERE ticker=? AND date < ? "
            "ORDER BY date DESC LIMIT 1", (a["ticker"], a["ex_date"])).fetchone()
        cur = conn.execute("SELECT close FROM ohlcv WHERE ticker=? AND date=?",
                           (a["ticker"], a["ex_date"])).fetchone()
        if not row or not cur or not row[1]:
            res.append({**a, "applied_in_ohlcv": None, "observed_return": None,
                        "note": "no adjacent ohlcv bars"}); continue
        obs = cur[0] / row[1] - 1.0
        expected_if_unadjusted = 1.0 / a["factor"] - 1.0
        unadjusted = abs(obs - expected_if_unadjusted) < jump_tol
        res.append({**a, "applied_in_ohlcv": not unadjusted,
                    "observed_return": round(obs, 6),
                    "return_if_unadjusted": round(expected_if_unadjusted, 6)})
    return res


# ------------------------------------------- adjustment-basis detector -----
def vwap_ratio_report(conn, universe: Iterable[str], sessions: list[str]) -> dict:
    """close / broker-flow-VWAP per ticker: the realised adjustment basis.

    ohlcv and broker_flow are independent measurements of the same prices, so
    their ratio is 1.0 whenever they share a basis. A ticker whose median
    departs from 1.0 has a basis mismatch; one whose spread is wide has an
    internally inconsistent basis and cannot be repaired by any single factor."""
    uni = sorted(set(universe)); ss = set(sessions)
    ph = ",".join("?" * len(uni))
    rows = conn.execute(
        f"SELECT o.ticker, o.date, o.close, "
        f"  (SELECT SUM(b.avg_price*b.lot_value)*1.0/NULLIF(SUM(b.lot_value),0) "
        f"   FROM broker_flow b WHERE b.ticker=o.ticker AND b.trade_date=o.date) "
        f"FROM ohlcv o WHERE o.ticker IN ({ph}) AND o.date >= ? AND o.date <= ?",
        uni + [min(sessions), max(sessions)]).fetchall()
    per: dict[str, list[float]] = {}
    for tk, d, close, vwap in rows:
        if d not in ss or not vwap or not close:
            continue
        per.setdefault(tk, []).append(close / vwap)
    report = {"tolerance": VWAP_RATIO_TOLERANCE, "instability": VWAP_RATIO_INSTABILITY,
              "min_observations": MIN_RATIO_OBSERVATIONS,
              "tickers": {}, "flagged": [], "insufficient": []}
    for tk, r in per.items():
        r.sort(); n = len(r)
        med = r[n // 2]
        lo, hi = r[max(0, int(0.05 * n))], r[min(n - 1, int(0.95 * n))]
        entry = {"n": n, "median": round(med, 5), "p5": round(lo, 5), "p95": round(hi, 5),
                 "spread": round(hi - lo, 5)}
        if n < MIN_RATIO_OBSERVATIONS:
            entry["verdict"] = "INSUFFICIENT"; report["insufficient"].append(tk)
        elif abs(med - 1.0) > VWAP_RATIO_TOLERANCE:
            entry["verdict"] = "BASIS_MISMATCH"; report["flagged"].append(tk)
        elif (hi - lo) > VWAP_RATIO_INSTABILITY:
            entry["verdict"] = "BASIS_UNSTABLE"; report["flagged"].append(tk)
        else:
            entry["verdict"] = "CLEAN"
        report["tickers"][tk] = entry
    report["flagged"].sort(); report["insufficient"].sort()
    return report


# ------------------------------------------- calendar-indexed outcomes -----
def forward_returns(conn, roster: PitRoster, cal: SessionCalendar, k: int,
                    quarantined: Iterable[str] = (),
                    strict_contiguity: bool = True) -> tuple[list[dict], dict]:
    """Forward returns indexed on the declared session calendar.

    Every returned observation satisfies, by construction:
      * formation and outcome are both admitted sessions
      * exactly k sessions separate them on this calendar
      * the ticker is a PIT member on the formation session
      * no substitution ever occurred -- a missing bar drops the observation
      * under strict_contiguity, no excluded session lies inside the window
    """
    q = set(quarantined)
    ss = cal.sessions
    ph = ",".join("?" * len(roster.universe))
    px: dict[tuple[str, str], float] = {}
    for tk, d, close in conn.execute(
            f"SELECT ticker, date, close FROM ohlcv WHERE ticker IN ({ph}) "
            f"AND date >= ? AND date <= ?", sorted(roster.universe) + [ss[0], ss[-1]]):
        if close:
            px[(tk, d)] = close
    out, stats = [], {"k": k, "candidates": 0, "kept": 0,
                      "dropped_quarantine": 0, "dropped_no_formation_price": 0,
                      "dropped_no_outcome_price": 0, "dropped_off_calendar": 0,
                      "dropped_crosses_excluded": 0, "strict_contiguity": strict_contiguity}
    for i, f_date in enumerate(ss):
        o_date = cal.k_ahead(f_date, k)
        for tk in roster.members(f_date):
            stats["candidates"] += 1
            if tk in q:
                stats["dropped_quarantine"] += 1; continue
            if o_date is None:
                stats["dropped_off_calendar"] += 1; continue
            p0 = px.get((tk, f_date))
            if p0 is None:
                stats["dropped_no_formation_price"] += 1; continue
            p1 = px.get((tk, o_date))
            if p1 is None:
                stats["dropped_no_outcome_price"] += 1; continue
            if strict_contiguity and cal.spans_excluded(f_date, o_date):
                stats["dropped_crosses_excluded"] += 1; continue
            out.append({"ticker": tk, "formation": f_date, "outcome": o_date,
                        "k": k, "session_distance": cal.index(o_date) - cal.index(f_date),
                        "fwd_ret": p1 / p0 - 1.0,
                        "period_confidence": roster.confidence(f_date)})
            stats["kept"] += 1
    return out, stats
