#!/usr/bin/env python3
"""Extend the I7 session calendar through 2026-09-11 (v004 mechanical fix).

Remediates the X3 defect recorded in
`I7_REGISTRATION_READINESS_REVIEW_2026-09-14.md` section 2.4: the base calendar
(Dataset B SESSION_CALENDAR v2) ends 2026-08-27, so spec rule X3
("non-admitted sessions per session_calendar") is unevaluable for the 11
v003-era sessions 2026-08-28..2026-09-11.

This builder applies the BASE CALENDAR'S OWN ADMISSION RULE — verbatim from
`dataset_b/build_calendar_and_roster.py`: candidate = trading_calendar date;
excluded if no roster period covers it, if no IHSG bar (unconfirmed IDX
session), or if PIT-member price coverage (non-null ohlcv close) < 0.95 — to
the extension window, from source data, read-only.

NO rule is changed and NO threshold is retuned: COVERAGE_THRESHOLD=0.95 and
the IHSG-confirmation predicate are copied as they stand. The base artifact is
verified against its recorded sha256 before use and is never modified.

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

#: Copied verbatim from build_calendar_and_roster.py (declared there as
#: "0.95 is declared here, not tuned"; measured distribution is bimodal).
COVERAGE_THRESHOLD = 0.95


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
    Copied from build_calendar_and_roster.py::build_calendar; nothing added."""
    lo, hi = EXT_WINDOW
    periods = conn.execute(
        "SELECT period_label, effective_from, effective_to "
        "FROM idx80_reconstitution_periods ORDER BY effective_from").fetchall()

    def period_for(d):
        for lbl, frm, to in periods:
            if frm <= d and (to is None or d <= to):
                return lbl
        return None

    cal = [r[0] for r in conn.execute(
        "SELECT date FROM trading_calendar "
        "WHERE date >= ? AND date <= ? ORDER BY date", (lo, hi))]
    ihsg = {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv "
        "WHERE ticker='IHSG' AND date >= ? AND date <= ?", (lo, hi))}

    admitted, excluded, detail = [], [], []
    for d in cal:
        lbl = period_for(d)
        members = [r[0] for r in conn.execute(
            "SELECT ticker FROM idx80_membership_history "
            "WHERE period_label=? AND membership_status='MEMBER'", (lbl,))] \
            if lbl else []
        if not members:
            excluded.append({"date": d,
                             "reason": "no roster period covers this session"})
            continue
        if d not in ihsg:
            excluded.append({"date": d,
                             "reason": "no IHSG bar (not a confirmed IDX session)"})
            continue
        # member price coverage: one parameterized scan of the session's bars,
        # counted against the member set in Python (no dynamic IN clause)
        member_set = set(members)
        have = sum(1 for (tk,) in conn.execute(
            "SELECT ticker FROM ohlcv WHERE date=? AND close IS NOT NULL",
            (d,)) if tk in member_set)
        cov = have / len(members)
        row = {"date": d, "period": lbl, "members": len(members),
               "with_price": have, "coverage": round(cov, 4),
               "ihsg_bar": True}
        if cov < COVERAGE_THRESHOLD:
            row["verdict"] = "EXCLUDED"
            row["reason"] = "member price coverage below threshold"
            excluded.append({"date": d, "reason": row["reason"],
                             "coverage": round(cov, 4), "members": len(members)})
        else:
            row["verdict"] = "ADMITTED"
            admitted.append(d)
        detail.append(row)
    return admitted, excluded, detail


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
            "source": "dataset_b/build_calendar_and_roster.py::build_calendar "
                      "(applied verbatim; nothing added)",
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
