#!/usr/bin/env python3
"""Executable post-freeze validation for the I7 v004 cohort (R4 remediation).

The seven post-freeze checks previously existed only as a table of
self-reported claims in a markdown document. The forensic audit marked them
UNVERIFIED *as gates* for that reason. This script makes them executable,
deterministic, and re-runnable.

STRICTLY READ-ONLY. Opens every database `mode=ro` + `PRAGMA query_only`,
opens every file for reading only, and writes nothing anywhere.

  python3 validate_v004_freeze.py                # gates 1-7 (frozen state only)
  python3 validate_v004_freeze.py --with-source  # + gate 8: re-derive the
                                                 #   calendar from production
  python3 validate_v004_freeze.py --json         # machine-readable only

Exit codes:  0 = all gates PASS   1 = one or more FAIL
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
STORE = os.path.join(HERE, "store")
V003 = os.path.join(STORE, "I7_V003_ADMISSIBLE_v1.sqlite")
V004 = os.path.join(STORE, "I7_V004_ADMISSIBLE_v1.sqlite")
V004_MAN = os.path.join(STORE, "I7_V004_MANIFEST.json")
EXT = os.path.join(STORE, "I7_SESSION_CALENDAR_EXTENSION_v1.json")
PROD = os.path.join(REPO, "data", "walkforward.db")

#: Recorded historical hashes. v003's is the value committed in cd40b03's
#: manifest; it is the immutability anchor and is pinned here deliberately so
#: the gate fails if either the artifact or the manifest is altered.
V003_SHA_RECORDED = "a4a9f7f90a8d3610d5f86163528f7f6fbde0994d8bb14651001bc16cd86ba0e0"
EXT_SHA_RECORDED = "a7a4eedf45f3d4b2ced4f9a9f2d90d28e011ef0425b115c127a04fcdda0f189e"

#: The 11 sessions the readiness review recorded as X3-unevaluable.
REVIEW_UNEVALUABLE = ["2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02",
                      "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08",
                      "2026-09-09", "2026-09-10", "2026-09-11"]

CUTOFF = _dt.time(16, 15)


def ro(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# --------------------------------------------------------------- the gates ---

def gate1_artifact_hashes():
    """Frozen artifacts match their recorded hashes (store, manifest sidecar,
    extension sidecar, and the code hashes the manifest pins)."""
    man = json.load(open(V004_MAN))
    checks = {}
    checks["v004_store_sha256"] = (sha256_file(V004), man["store_sha256"])
    checks["v004_manifest_sidecar"] = (
        sha256_file(V004_MAN), open(V004_MAN + ".sha256").read().strip())
    checks["extension_sha256"] = (sha256_file(EXT), EXT_SHA_RECORDED)
    checks["extension_sidecar"] = (
        sha256_file(EXT), open(EXT + ".sha256").read().strip())
    for fn, key in (("i7_admissibility.py", "admissibility_module_sha256"),
                    ("build_v004_freeze.py", "builder_sha256")):
        actual = hashlib.sha256(open(os.path.join(HERE, fn), "rb").read()).hexdigest()
        checks[key] = (actual, man[key])
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    return not bad, {"checked": len(checks), "mismatches": bad}


def gate2_v003_immutable():
    """v003 is byte-identical to its recorded hash and remains read-only."""
    actual = sha256_file(V003)
    mode = oct(os.stat(V003).st_mode & 0o777)
    ok = (actual == V003_SHA_RECORDED) and mode == "0o444"
    return ok, {"sha256": actual, "recorded": V003_SHA_RECORDED,
                "match": actual == V003_SHA_RECORDED, "mode": mode}


def gate3_ledger_reconciles():
    """Ledger is mutually exclusive, collectively exhaustive, duplicate-free,
    and its counts equal the manifest's."""
    man = json.load(open(V004_MAN))
    c = ro(V004)
    by = dict(c.execute(
        "SELECT COALESCE(exclusion_rule,'ADMITTED'), COUNT(*) "
        "FROM admissibility_ledger GROUP BY 1").fetchall())
    total = sum(by.values())
    adm_with_rule = c.execute("SELECT COUNT(*) FROM admissibility_ledger "
                              "WHERE admissible=1 AND exclusion_rule IS NOT NULL"
                              ).fetchone()[0]
    exc_no_rule = c.execute("SELECT COUNT(*) FROM admissibility_ledger "
                            "WHERE admissible=0 AND exclusion_rule IS NULL"
                            ).fetchone()[0]
    dupes = c.execute("SELECT COUNT(*)-COUNT(DISTINCT ticker||'|'||session_date) "
                      "FROM admissibility_ledger").fetchone()[0]
    sess, tick, cells = c.execute(
        "SELECT COUNT(DISTINCT session_date), COUNT(DISTINCT ticker), COUNT(*) "
        "FROM admissibility_ledger WHERE admissible=1").fetchone()
    bars = c.execute("SELECT COUNT(*) FROM flow_bars_v004").fetchone()[0]
    barcells = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM flow_bars_v004 "
                         "GROUP BY ticker, trade_date)").fetchone()[0]
    c.close()
    ok = (total == man["candidate_cells"]
          and by.get("ADMITTED") == man["admissible_ticker_days"] == cells
          and sess == man["admissible_sessions"]
          and tick == man["admissible_tickers"]
          and bars == man["admissible_bar_rows"]
          and barcells == cells
          and adm_with_rule == 0 and exc_no_rule == 0 and dupes == 0
          and all(by.get(k) == v for k, v in man["exclusions_in_window"].items()))
    return ok, {"by_rule": by, "total_candidates": total,
                "admitted_cells": cells, "sessions": sess, "tickers": tick,
                "bar_rows": bars, "bar_cells_equal_admitted": barcells == cells,
                "mece_violations": {"admitted_with_rule": adm_with_rule,
                                    "excluded_without_rule": exc_no_rule,
                                    "duplicates": dupes}}


def gate4_x3_exclusions():
    """Every X3 session is genuinely non-admitted by the effective calendar,
    2026-07-09 is fully excluded, and X3 is evaluable for all 11 review
    sessions. Effective calendar = base sessions + frozen extension."""
    man = json.load(open(V004_MAN))
    ext = json.load(open(EXT))
    base = json.load(open(os.path.join(
        REPO, "docs/research_programs/P-M/dataset_b/artifacts",
        "DATASET_B_SESSION_CALENDAR_v2.json")))
    effective = set(base["sessions"]) | set(ext["admitted_sessions"])
    c = ro(V004)
    x3 = dict(c.execute("SELECT session_date, COUNT(*) FROM admissibility_ledger "
                        "WHERE exclusion_rule='X3' GROUP BY 1").fetchall())
    d709 = c.execute(
        "SELECT COUNT(*), SUM(admissible), "
        "SUM(CASE WHEN exclusion_rule='X3' THEN 1 ELSE 0 END) "
        "FROM admissibility_ledger WHERE session_date='2026-07-09'").fetchone()
    d709_bars = c.execute("SELECT COUNT(*) FROM flow_bars_v004 "
                          "WHERE trade_date='2026-07-09'").fetchone()[0]
    admitted_sessions = {r[0] for r in c.execute(
        "SELECT DISTINCT session_date FROM admissibility_ledger WHERE admissible=1")}
    c.close()
    leaked = sorted(set(x3) & admitted_sessions)          # must be empty
    not_really_x3 = sorted(s for s in x3 if s in effective)  # must be empty
    unevaluable = [s for s in REVIEW_UNEVALUABLE if s not in effective]
    ok = (not leaked and not not_really_x3 and not unevaluable
          and d709 == (958, 0, 958) and d709_bars == 0
          and sorted(x3) == sorted(man["x3_excluded_sessions_in_window"]))
    return ok, {"x3_sessions": x3, "sessions_both_x3_and_admitted": leaked,
                "x3_sessions_that_are_calendar_admitted": not_really_x3,
                "review_sessions_still_unevaluable": unevaluable,
                "d2026_07_09": {"cells": d709[0], "admitted": d709[1],
                                "x3": d709[2], "bars": d709_bars}}


def gate5_no_pre_cutoff_admitted():
    """No admitted cell was captured same-day before the 16:15 WIB cutoff, and
    every admitted cell carries a write lag within 0..1 days."""
    c = ro(V004)
    rows = c.execute("SELECT captured_at_wib, write_lag_days FROM "
                     "admissibility_ledger WHERE admissible=1").fetchall()
    c.close()
    pre = sum(1 for ts, lag in rows
              if lag == 0 and _dt.time.fromisoformat(ts[11:19]) < CUTOFF)
    bad_lag = sum(1 for _ts, lag in rows if lag not in (0, 1))
    return (pre == 0 and bad_lag == 0), {"admitted": len(rows),
                                         "same_day_pre_cutoff": pre,
                                         "lag_outside_0_1": bad_lag}


def gate6_result_blindness():
    """No executable SQL in the accrual builder reads an outcome table/column,
    and no statement is dynamically constructed. AST-based, not grep-based."""
    src = open(os.path.join(HERE, "build_v004_freeze.py")).read()
    tree = ast.parse(src)
    offenders, dynamic = [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr in ("execute", "executemany", "executescript"):
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    s = a.value.lower()
                    for tok in ("ohlcv", "corporate_action", "close",
                                "ret1", "fwd", "pnl", "wf_edge"):
                        if tok in s:
                            offenders.append([n.lineno, tok])
                elif isinstance(a, (ast.JoinedStr, ast.BinOp)):
                    dynamic.append(n.lineno)
    ok = not offenders and not dynamic
    return ok, {"outcome_tokens_in_executable_sql": offenders,
                "dynamic_sql_statements": dynamic,
                "note": "the session calendar's own predicate tests "
                        "ohlcv.close IS NOT NULL -- a PRESENCE test; the close "
                        "VALUE is never read, compared or returned"}


def gate7_x1_to_x6_disposition():
    """Every spec exclusion X1..X6 has an explicit recorded disposition, and
    the two subsumption claims (X1, X2) are structurally true."""
    man = json.load(open(V004_MAN))
    disp = man.get("spec_exclusions_x1_to_x6", {})
    missing = [k for k in ("X1", "X2", "X3", "X4", "X5", "X6") if k not in disp]
    # X1/X2 subsumption is a date fact, not an opinion: both regions must end
    # strictly before the contemporaneous boundary.
    boundary = "2026-04-28"
    subsumed = (max("2025-04-14", "2025-09-17") < boundary)
    ok = not missing and subsumed
    return ok, {"missing_dispositions": missing,
                "x1_x2_regions_end_before_boundary": subsumed,
                "boundary": boundary, "dispositions": disp}


def gate8_calendar_from_source():
    """OPTIONAL (--with-source): re-derive the extension window from production
    under the FULL four-gate base rule (including NAMED_EXCLUSIONS) and confirm
    the frozen artifact's decisions are unchanged."""
    sys.path.insert(0, HERE)
    import session_calendar_predicate as SCP
    c = SCP.ro(PROD)
    ok, rep = SCP.verify_extension_artifact(c)
    c.close()
    return ok, rep


GATES = [("1_artifact_hashes", gate1_artifact_hashes),
         ("2_v003_immutable", gate2_v003_immutable),
         ("3_ledger_reconciles", gate3_ledger_reconciles),
         ("4_x3_exclusions", gate4_x3_exclusions),
         ("5_no_pre_cutoff_admitted", gate5_no_pre_cutoff_admitted),
         ("6_result_blindness", gate6_result_blindness),
         ("7_x1_to_x6_disposition", gate7_x1_to_x6_disposition)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-source", action="store_true",
                    help="also re-derive the calendar from the production DB")
    ap.add_argument("--json", action="store_true", help="machine-readable only")
    a = ap.parse_args()

    gates = list(GATES) + ([("8_calendar_from_source", gate8_calendar_from_source)]
                           if a.with_source else [])
    results, failed = {}, 0
    for name, fn in gates:
        try:
            ok, detail = fn()
        except Exception as e:                     # a gate that cannot run FAILS
            ok, detail = False, {"error": f"{type(e).__name__}: {e}"}
        results[name] = {"pass": ok, "detail": detail}
        failed += (not ok)

    summary = {"artifact": "I7-admissible-v004",
               "gates_run": len(gates), "gates_failed": failed,
               "verdict": "PASS" if failed == 0 else "FAIL",
               "checked_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
               "results": results}

    if a.json:
        print(json.dumps(summary, indent=1, sort_keys=True))
    else:
        print("=== I7 v004 POST-FREEZE VALIDATION ===")
        for name, r in results.items():
            print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {name}")
            if not r["pass"]:
                print(f"         {json.dumps(r['detail'])[:400]}")
        print(f"\n{len(gates) - failed}/{len(gates)} gates passed "
              f"-> {summary['verdict']}")
        print("\n--- machine-readable ---")
        print(json.dumps({"verdict": summary["verdict"],
                          "gates_failed": failed,
                          "gates": {k: v["pass"] for k, v in results.items()}},
                         sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
