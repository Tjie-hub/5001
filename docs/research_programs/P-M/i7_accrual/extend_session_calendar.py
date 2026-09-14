#!/usr/bin/env python3
"""Extend the I7 session calendar through 2026-09-11 (v004 mechanical fix).

Remediates the X3 defect recorded in
`I7_REGISTRATION_READINESS_REVIEW_2026-09-14.md` section 2.4: the base calendar
(Dataset B SESSION_CALENDAR v2) ends 2026-08-27, so spec rule X3
("non-admitted sessions per session_calendar") is unevaluable for the 11
v003-era sessions 2026-08-28..2026-09-11.

CORRECTION — forensic audit reservation R2 (applied post-freeze)
----------------------------------------------------------------
An earlier version of this docstring claimed the base rule was applied
"verbatim ... nothing added". THAT CLAIM WAS FALSE. The base rule in
`dataset_b/build_calendar_and_roster.py::build_calendar` has FOUR gates; the
original implementation here had THREE — the `NAMED_EXCLUSIONS` gate was
omitted.

The omission was immaterial to the frozen artifact: `NAMED_EXCLUSIONS` holds
exactly one date, 2026-08-25, which lies OUTSIDE this extension window
(2026-08-28..2026-09-11). That is proven rather than assumed —
`session_calendar_predicate.verify_extension_artifact()` re-evaluates the
window under the FULL four-gate rule and reproduces the frozen artifact's
admitted set (11/11), excluded count (0) and every per-session coverage figure
exactly. Validation gate 8 runs that proof on demand.

This module now DELEGATES to `session_calendar_predicate.admit()`, which
IMPORTS `NAMED_EXCLUSIONS` and `COVERAGE_THRESHOLD` from the base builder
instead of copying them, so the predicate cannot drift from its source. No rule
is changed and no threshold is retuned. The base artifact is verified against
its recorded sha256 before use and is never modified.

The frozen artifact `store/I7_SESSION_CALENDAR_EXTENSION_v1.json` was produced
by the three-gate version and is deliberately NOT rebuilt: it is immutable, and
its decisions are identical under the corrected predicate. Any future artifact
built by this module will carry an `excluded[].gate` field the frozen one
lacks — new versions get new files.

Output: store/I7_SESSION_CALENDAR_EXTENSION_v1.json (+ .sha256), frozen
read-only. The v004 cohort builder consumes it; the v003 freeze and the
Dataset B artifact are untouched.

All SQL statements are inline literals executed with bound parameters ('?')
only — no identifier or value is ever interpolated into a statement.

  python3 extend_session_calendar.py            # dry run: print evaluation
  python3 extend_session_calendar.py --write    # materialise + freeze
"""
from __future__ import annotations

import argparse, datetime as _dt, hashlib, json, os, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DSB = os.path.join(REPO, "docs", "research_programs", "P-M", "dataset_b")
BASE_ART = os.path.join(DSB, "artifacts", "DATASET_B_SESSION_CALENDAR_v2.json")
BASE_SHA_RECORDED = "5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa"
PROD = os.path.join(REPO, "data", "walkforward.db")
OUT = os.path.join(HERE, "store", "I7_SESSION_CALENDAR_EXTENSION_v1.json")

#: The extension window. Declared, not discovered: exactly the sessions the
#: readiness review lists as X3-unevaluable (calendar end .. v003 last session).
EXT_WINDOW = ("2026-08-28", "2026-09-11")

#: IMPORTED, never copied (R2). `session_calendar_predicate` re-exports the
#: base builder's own constant, so this cannot drift from it.
import session_calendar_predicate as SCP  # noqa: E402
from session_calendar_predicate import COVERAGE_THRESHOLD  # noqa: E402


def ro(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def verify_base_artifact():
    """Fail-closed: recompute the base artifact's recorded content sha256
    using the same canonicalisation as dataset_b/foundation.load_artifact."""
    obj = json.load(open(BASE_ART))
    recorded = obj["sha256"]
    if recorded != BASE_SHA_RECORDED:
        raise SystemExit("ABORT: base calendar artifact sha mismatch vs pin")
    body = {k: v for k, v in obj.items()
            if k not in ("sha256", "built_at_utc", "git_commit", "builder",
                         "source_db")}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode()
    if hashlib.sha256(canon).hexdigest() != recorded:
        raise SystemExit("ABORT: base calendar artifact content hash mismatch")
    return obj


def evaluate_extension(conn):
    """The base calendar's admission rule, applied to the extension window.

    R2: this now DELEGATES to `session_calendar_predicate.admit()` — the single
    shared implementation of the base rule, including the `NAMED_EXCLUSIONS`
    gate this module originally omitted. Nothing is copied and no threshold is
    redeclared; the predicate imports both from
    `dataset_b/build_calendar_and_roster.py`.
    """
    lo, hi = EXT_WINDOW
    return SCP.admit(conn, lo, hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    base = verify_base_artifact()
    base_last = base["sessions"][-1]
    conn = ro(PROD)
    admitted, excluded, detail = evaluate_extension(conn)
    conn.close()

    print("=== I7 SESSION CALENDAR EXTENSION — evaluation ===")
    print(f"base artifact        : DATASET_B_SESSION_CALENDAR_v2 (sha ok, "
          f"ends {base_last})")
    print(f"extension window     : {EXT_WINDOW[0]} .. {EXT_WINDOW[1]}")
    print(f"admitted sessions    : {len(admitted)}")
    for d in admitted:
        print(f"  ADMIT  {d}")
    print(f"excluded sessions    : {len(excluded)}")
    for e in excluded:
        print(f"  EXCLUDE  {e['date']}  {e['reason']}")
    # continuity: the extension must begin after the base calendar ends
    if admitted and admitted[0] <= base_last:
        raise SystemExit("ABORT: extension overlaps the base calendar")
    if admitted:
        gap = (_dt.date.fromisoformat(admitted[0])
               - _dt.date.fromisoformat(base_last)).days
        print(f"gap from base end to first extension session: {gap} calendar days")

    if not a.write:
        print("\nDRY RUN — nothing written. Pass --write to materialise.")
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        print(f"\nREFUSING: {OUT} already exists. New versions get new files.")
        return 2
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                         cwd=REPO, text=True).strip()
    except Exception:
        commit = "unknown"
    doc = {
        "artifact": "I7_SESSION_CALENDAR_EXTENSION",
        "version": "v1",
        "purpose": "extends the X3 session-calendar coverage through 2026-09-11 "
                   "(readiness review section 2.4 remediation); rule unchanged",
        "base_calendar": {"artifact": "DATASET_B_SESSION_CALENDAR_v2.json",
                          "sha256": BASE_SHA_RECORDED,
                          "last_session": base_last},
        "admission_rule": {
            "source": "dataset_b/build_calendar_and_roster.py::build_calendar, "
                      "applied via the shared predicate "
                      "i7_accrual/session_calendar_predicate.py::admit, which "
                      "IMPORTS NAMED_EXCLUSIONS and COVERAGE_THRESHOLD from "
                      "that module rather than copying them",
            "gates": list(SCP.GATE_ORDER),
            "r2_note": "the frozen v1 artifact was produced by an earlier "
                       "three-gate implementation that omitted NAMED_EXCLUSIONS; "
                       "immaterial here (its only member, 2026-08-25, is outside "
                       "this window) and proven identical by "
                       "session_calendar_predicate.verify_extension_artifact()",
            "coverage_threshold": COVERAGE_THRESHOLD,
            "ihsg_confirmation": True,
            "membership_source": "idx80_membership_history (status='MEMBER') "
                                 "via idx80_reconstitution_periods",
        },
        "extension_window": list(EXT_WINDOW),
        "admitted_sessions": admitted,
        "admitted_count": len(admitted),
        "excluded": excluded,
        "evaluation_detail": detail,
        "built_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "git_commit": commit,
        "source_db": PROD,
        "outcome_blind": "no close/return/outcome column is read for the "
                         "admission decision (membership price coverage over "
                         "ohlcv is the base rule's own predicate, unchanged)",
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(OUT, 0o444)
    print(f"\nFROZEN: {OUT}")
    print(f"  sha256: {sha256_file(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
