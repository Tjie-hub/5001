#!/usr/bin/env python3
"""Single shared session-admission predicate (R2 remediation).

WHY THIS EXISTS
---------------
`extend_session_calendar.py` (which built the frozen extension artifact)
re-implemented the base calendar's admission rule and its docstring claimed the
rule was "copied verbatim ... nothing added". The forensic audit established
that claim was FALSE: the base rule in
`dataset_b/build_calendar_and_roster.py::build_calendar` has FOUR gates and the
extension implemented THREE -- the `NAMED_EXCLUSIONS` gate was omitted.

The omission was immaterial for the frozen window: `NAMED_EXCLUSIONS` contains
exactly one date, 2026-08-25, which lies OUTSIDE the extension window
2026-08-28..2026-09-11. Proven, not assumed, by `verify_extension_artifact()`
below and by `test_i7_x3.py`.

This module removes the divergence structurally rather than by copying more
text: `NAMED_EXCLUSIONS` and `COVERAGE_THRESHOLD` are **imported from the base
builder**, so they cannot drift from it. No threshold is redeclared here.

WHAT THIS IS NOT
----------------
Not a new rule, not a retuning, and not a change to any cohort. The frozen
extension artifact and the frozen v004 store are untouched by this module; it
exists to (a) give future extensions one authoritative predicate and (b) let
the validation suite prove the frozen artifact satisfies the FULL base rule.

Read-only. Opens the production DB `mode=ro` + `PRAGMA query_only`.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DSB = os.path.join(REPO, "docs", "research_programs", "P-M", "dataset_b")
sys.path.insert(0, DSB)

# Imported, never copied -- this is the R2 fix. If the base builder ever
# changes a threshold or adds a named exclusion, this predicate follows it.
from build_calendar_and_roster import (  # noqa: E402
    NAMED_EXCLUSIONS,
    COVERAGE_THRESHOLD,
)

EXT_ARTIFACT = os.path.join(HERE, "store",
                            "I7_SESSION_CALENDAR_EXTENSION_v1.json")

#: Gate order, verbatim from build_calendar_and_roster.py::build_calendar
#: (lines 141-160). Order is part of the predicate: it determines which reason
#: a session is recorded under when several gates would fire.
GATE_ORDER = ("no_roster_period", "named_exclusion", "no_ihsg_bar",
              "coverage_below_threshold")


def ro(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def _periods(conn):
    return conn.execute(
        "SELECT period_label, effective_from, effective_to "
        "FROM idx80_reconstitution_periods ORDER BY effective_from").fetchall()


def _period_for(periods, d):
    for lbl, frm, to in periods:
        if frm <= d and (to is None or d <= to):
            return lbl
    return None


def admit(conn, lo: str, hi: str):
    """The base calendar's admission rule over [lo, hi].

    Returns (admitted:list[str], excluded:list[dict], detail:list[dict]).

    Gates, in the base builder's exact order:
      1. no roster period covers the session
      2. NAMED_EXCLUSIONS            <-- the gate the extension omitted
      3. no IHSG bar (unconfirmed IDX session)
      4. member price coverage < COVERAGE_THRESHOLD

    Gate 4 counts roster members having a NON-NULL `ohlcv.close` for that
    session. This is a PRESENCE test: the close VALUE is never read, compared,
    or returned. No forward-dated row is touched -- the scan is
    `WHERE date = ?` for the session itself.
    """
    periods = _periods(conn)
    cal = [r[0] for r in conn.execute(
        "SELECT date FROM trading_calendar WHERE date >= ? AND date <= ? "
        "ORDER BY date", (lo, hi))]
    ihsg = {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv WHERE ticker='IHSG' "
        "AND date >= ? AND date <= ?", (lo, hi))}

    admitted, excluded, detail = [], [], []
    for d in cal:
        lbl = _period_for(periods, d)
        members = {r[0] for r in conn.execute(
            "SELECT ticker FROM idx80_membership_history "
            "WHERE period_label=? AND membership_status='MEMBER'", (lbl,))} \
            if lbl else set()

        if not members:
            excluded.append({"date": d, "gate": "no_roster_period",
                             "reason": "no roster period covers this session"})
            continue
        if d in NAMED_EXCLUSIONS:
            excluded.append({"date": d, "gate": "named_exclusion",
                             "reason": NAMED_EXCLUSIONS[d]})
            continue
        if d not in ihsg:
            excluded.append({"date": d, "gate": "no_ihsg_bar",
                             "reason": "no IHSG bar (not a confirmed IDX session)"})
            continue

        have = sum(1 for (tk,) in conn.execute(
            "SELECT ticker FROM ohlcv WHERE date=? AND close IS NOT NULL",
            (d,)) if tk in members)
        cov = have / len(members)
        row = {"date": d, "period": lbl, "members": len(members),
               "with_price": have, "coverage": round(cov, 4)}
        if cov < COVERAGE_THRESHOLD:
            row["verdict"] = "EXCLUDED"
            excluded.append({"date": d, "gate": "coverage_below_threshold",
                             "reason": "member price coverage below threshold",
                             "coverage": round(cov, 4)})
        else:
            row["verdict"] = "ADMITTED"
            admitted.append(d)
        detail.append(row)
    return admitted, excluded, detail


def verify_extension_artifact(conn):
    """Prove the FROZEN extension artifact satisfies the FULL base rule.

    Re-evaluates the artifact's own window under this predicate (which includes
    the omitted NAMED_EXCLUSIONS gate) and compares the admitted set and every
    per-session coverage figure. Returns (ok: bool, report: dict).

    This is the R2 proof: it does not rebuild the artifact, it re-derives its
    decisions and shows the omitted gate changes nothing.
    """
    art = json.load(open(EXT_ARTIFACT))
    lo, hi = art["extension_window"]
    admitted, excluded, detail = admit(conn, lo, hi)
    art_cov = {r["date"]: r["coverage"] for r in art["evaluation_detail"]}
    new_cov = {r["date"]: r["coverage"] for r in detail}
    report = {
        "window": [lo, hi],
        "artifact_admitted": art["admitted_sessions"],
        "recomputed_admitted": admitted,
        "admitted_match": art["admitted_sessions"] == admitted,
        "artifact_excluded_count": len(art["excluded"]),
        "recomputed_excluded_count": len(excluded),
        "excluded_match": len(art["excluded"]) == len(excluded),
        "coverage_match": art_cov == new_cov,
        "named_exclusions_in_window": [d for d in NAMED_EXCLUSIONS
                                       if lo <= d <= hi],
        "coverage_threshold": COVERAGE_THRESHOLD,
    }
    ok = (report["admitted_match"] and report["excluded_match"]
          and report["coverage_match"])
    return ok, report


if __name__ == "__main__":
    PROD = os.path.join(REPO, "data", "walkforward.db")
    c = ro(PROD)
    ok, rep = verify_extension_artifact(c)
    c.close()
    print(json.dumps(rep, indent=1))
    print("FULL-BASE-RULE REPRODUCTION:", "OK" if ok else "MISMATCH")
    raise SystemExit(0 if ok else 1)
