#!/usr/bin/env python3
"""Full-universe `broker_flow` backfill DRIVER — multi-date orchestrator.

This is a THIN composition layer, not a new fetcher/orchestrator implementation.
It never talks to Stockbit itself and never writes to any table. It composes,
unchanged:

  * `tools/broker_flow_idx80_gap.py::canonical_trading_dates` / `missing_cells`
    — the existing calendar + completion predicate (IHSG-confirmed dates,
    broker_flow rows OR confirmed-empty bandar_detector marker).
  * `tools/backfill_broker_flow_full_universe.py` — the existing, tested
    single-date, full-universe fetcher. Invoked as a CHILD PROCESS, one
    trading date at a time. Its vendor-fetch/write logic is not touched.
  * `tools/agent_backfill_broker_flow_idx80.py::connect_ro` /
    `other_backfill_pids` / `AgentLock` / `scan_runner_for_destructive_sql` —
    the existing safety primitives, reused rather than reimplemented.

The gap this closes: `backfill_broker_flow_full_universe.py` is deliberately
single-date only (its own docstring: "pilot/audit tool, not a backfill
scheduler"), and `agent_backfill_broker_flow_idx80.py` is deliberately
IDX80-only "by construction" (no flag can widen its universe). Neither can
run a multi-date, full-universe historical repair. This driver is exactly
that missing multi-date loop around the already-safe single-date script —
nothing else.

SAFETY POSTURE (fail-closed)
----------------------------
  * Default invocation (no mode flag at all) makes ZERO subprocess/vendor
    calls — the same posture as passing `--dry-run` explicitly.
  * Live execution requires BOTH `--live` AND the child script's own
    `--yes-run-vendor-backfill` confirmation flag, propagated unchanged to
    every child invocation — this driver does not invent a second,
    independent confirmation mechanism.
  * A `--db` path resolving under `data/frozen/` is refused outright, before
    any other check — frozen datasets (e.g. `stockbit-flow-bars-v002`) must
    never become a write target of this or any backfill tool.
  * The DB handle THIS driver opens for planning is always `connect_ro()`
    (read-only, mode=ro) — reused from the IDX80 orchestrator, never a raw
    read-write `sqlite3.connect()`. All writes happen only inside the child
    process, through the existing runner's existing `data/db.py::connect()`
    write path — this driver's own process never writes anything.
  * Concurrency: `other_backfill_pids()` (reused) is checked before launching
    each child, plus this driver holds its own `AgentLock` (a NEW lock file,
    distinct from the child script's own lock) for the duration of a live
    run, so two driver invocations cannot run concurrently. The per-date
    child still acquires its own existing lock independently.

CHRONOLOGICAL, ONE-DATE-PER-CHILD, STOP-ON-FAILURE EXECUTION
--------------------------------------------------------------
Dates are planned in ascending order. Already-complete dates (per the DB
state at plan time) are skipped as no-ops — no child is ever launched for
them. For each remaining date, exactly one child process is launched for
that date only. The FIRST child that exits non-zero, or times out, stops
the sequence immediately — no later date is attempted. There is no separate
authoritative cursor file: resume is entirely DB-derived — re-invoking this
driver over the same (or a wider) window will skip everything the DB now
shows complete and pick up exactly where the run stopped.

EXIT CODES
----------
  0  COMPLETE  every date in the window is already complete (nothing to do)
  1  PARTIAL   dry-run only: work remains, nothing was executed
  2  FAILED    a live child exited non-zero or timed out — sequence stopped
  3  BLOCKED   not safe to run / invalid request — nothing was executed

Usage:
  # plan only -- no vendor calls, no writes (also the default with no flags)
  venv/bin/python3 tools/agent_backfill_broker_flow_full_universe.py \\
      --start-date 2025-01-02 --end-date 2026-09-04 --dry-run

  # explicit, unmistakable live execution -- one child per remaining date
  venv/bin/python3 tools/agent_backfill_broker_flow_full_universe.py \\
      --start-date 2025-01-02 --end-date 2026-09-04 \\
      --live --yes-run-vendor-backfill --budget-s 17400
"""
import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from tools.broker_flow_idx80_gap import canonical_trading_dates, missing_cells  # noqa: E402
from tools.backfill_broker_flow_full_universe import (  # noqa: E402
    resolve_universe, DEFAULT_BUDGET_S, HARD_CAP_S,
    DB_PATH as RUNNER_DEFAULT_DB,
)
from tools.agent_backfill_broker_flow_idx80 import (  # noqa: E402
    connect_ro, other_backfill_pids, AgentLock, TIMEOUT_MARGIN_S,
    scan_runner_for_destructive_sql,
)

DEFAULT_DB = HERE / "data" / "walkforward.db"
DEFAULT_RUNNER = HERE / "tools" / "backfill_broker_flow_full_universe.py"
DEFAULT_LOCK = HERE / "logs" / "agent_backfill_broker_flow_full_universe.lock"
FROZEN_DIR = HERE / "data" / "frozen"

CONFIRM_FLAG = "--yes-run-vendor-backfill"

EXIT_COMPLETE = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2
EXIT_BLOCKED = 3
STATUS_EXIT = {"COMPLETE": EXIT_COMPLETE, "PARTIAL": EXIT_PARTIAL,
              "FAILED": EXIT_FAILED, "BLOCKED": EXIT_BLOCKED}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(s: str) -> bool:
    if not _ISO_DATE.match(s or ""):
        return False
    try:
        _date.fromisoformat(s)
    except ValueError:
        return False
    return True


def is_frozen_path(db_path) -> bool:
    """True iff db_path resolves under data/frozen/ -- refuse it as a write
    target unconditionally. Frozen artifacts (e.g. stockbit-flow-bars-v002)
    must never be touched by any backfill tool."""
    try:
        Path(db_path).resolve().relative_to(FROZEN_DIR.resolve())
        return True
    except ValueError:
        return False


def default_python() -> str:
    venv = HERE / "venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


def plan_dates(conn, date_from: str, date_to: str, tickers: list) -> tuple:
    """Chronological plan for [date_from, date_to) -- EXCLUSIVE upper bound.

    Returns (plan, non_ihsg) where plan is a list of
    {"date": ..., "missing": int, "skip": bool} in ascending date order, and
    non_ihsg is canonical_trading_dates()'s own excluded-row report, passed
    through unchanged.
    """
    confirmed, non_ihsg = canonical_trading_dates(conn, date_from, date_to)
    plan = []
    for d in confirmed:
        need = missing_cells(conn, d, tickers)
        plan.append({"date": d, "missing": len(need), "skip": len(need) == 0})
    return plan, non_ihsg


def build_child_command(python: str, runner, date: str, budget_s: int, db_path) -> list:
    return [python, str(runner), "--date", date, "--budget-s", str(budget_s),
           CONFIRM_FLAG, "--db", str(db_path)]


@dataclass
class ChildResult:
    date: str
    returncode: Optional[int]
    timed_out: bool
    command: list


def run_one_date(cmd: list, date: str, timeout: int, spawn=None) -> ChildResult:
    spawn = spawn or subprocess.run
    try:
        proc = spawn(cmd, timeout=timeout)
        return ChildResult(date, proc.returncode, False, cmd)
    except subprocess.TimeoutExpired:
        return ChildResult(date, None, True, cmd)


def run_sequence(dates_needing_work: list, python: str, runner, budget_s: int,
                 db_path, timeout_margin_s: int, spawn=None) -> tuple:
    """Chronological, one-child-per-date, stop-on-first-failure execution.

    Returns (outcomes: list[ChildResult], stopped_reason: str | None).
    A None stopped_reason means every date in dates_needing_work succeeded.
    """
    outcomes = []
    for d in dates_needing_work:
        cmd = build_child_command(python, runner, d, budget_s, db_path)
        res = run_one_date(cmd, d, timeout=budget_s + timeout_margin_s, spawn=spawn)
        outcomes.append(res)
        if res.timed_out:
            return outcomes, f"date {d} timed out after {budget_s + timeout_margin_s}s"
        if res.returncode != 0:
            return outcomes, f"date {d} exited {res.returncode}"
    return outcomes, None


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="agent_backfill_broker_flow_full_universe.py",
        description="Full-universe broker_flow backfill DRIVER -- plans and, "
                    "only with explicit authorization, supervises "
                    "tools/backfill_broker_flow_full_universe.py one trading "
                    "date at a time. Never fetches itself.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 COMPLETE, 1 PARTIAL, 2 FAILED, 3 BLOCKED.\n"
               "Default (no flags) is a dry-run plan: read-only, no vendor calls.",
    )
    ap.add_argument("--start-date", required=True, help="inclusive lower bound, YYYY-MM-DD")
    ap.add_argument("--end-date", required=True, help="EXCLUSIVE upper bound, YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit plan-only mode (also the default with no mode flag)")
    ap.add_argument("--live", action="store_true",
                    help="required (with the confirm flag below) to execute for real")
    ap.add_argument(CONFIRM_FLAG, action="store_true",
                    help="REQUIRED for --live. Propagated unchanged to every child "
                         "invocation -- this driver adds no second confirmation gate.")
    ap.add_argument("--budget-s", type=int, default=DEFAULT_BUDGET_S,
                    help=f"per-date wall-clock budget passed to each child "
                         f"(1..{HARD_CAP_S}; default {DEFAULT_BUDGET_S})")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB to plan against / write to")
    ap.add_argument("--runner", default=str(DEFAULT_RUNNER),
                    help="single-date full-universe implementation to supervise")
    ap.add_argument("--lock-file", default=str(DEFAULT_LOCK))
    ap.add_argument("--python", default=None, help="interpreter for child subprocesses")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON only")
    return ap


def _check(checks, name, ok, detail, blocking=True):
    checks.append({"name": name, "ok": bool(ok), "blocking": blocking, "detail": detail})
    return ok


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    live_requested = args.live
    confirmed_flag = getattr(args, CONFIRM_FLAG.lstrip("-").replace("-", "_"))

    checks, reasons = [], []
    report = {
        "start_date": args.start_date, "end_date": args.end_date,
        "end_date_exclusive": True, "db": args.db, "runner": args.runner,
        "budget_s": args.budget_s,
        "dates_selected": [], "dates_skipped_already_complete": [],
        "dates_needing_work": [], "estimated_missing_cells": 0,
        "non_ihsg_dates": [],
        "vendor_calls_made": False, "outcomes": [], "stopped_reason": None,
        "status": "BLOCKED", "safety_checks": checks, "reasons": reasons,
    }

    dates_ok = (_valid_date(args.start_date) and _valid_date(args.end_date)
               and args.start_date < args.end_date)
    if not _check(checks, "date_range_valid", dates_ok,
                 f"[{args.start_date}, {args.end_date}) -- --end-date is EXCLUSIVE"):
        reasons.append(f"invalid window [{args.start_date}, {args.end_date}): "
                       f"both must be YYYY-MM-DD and --start-date must be strictly "
                       f"before the exclusive --end-date")

    frozen = is_frozen_path(args.db)
    if not _check(checks, "db_not_a_frozen_artifact", not frozen,
                 f"{args.db} resolves under {FROZEN_DIR}" if frozen
                 else f"{args.db} is not under {FROZEN_DIR}"):
        reasons.append(f"refusing to plan or write against {args.db} -- it resolves "
                       f"under {FROZEN_DIR}, a frozen-artifact directory. Frozen "
                       f"datasets must never be a backfill write target.")

    destructive = scan_runner_for_destructive_sql(args.runner)
    if not _check(checks, "runner_non_destructive", not destructive,
                 f"destructive SQL found: {destructive}" if destructive
                 else "runner only INSERTs OR REPLACEs keyed rows"):
        reasons.append(f"runner {args.runner} contains destructive SQL "
                       f"{destructive} -- refusing to orchestrate it")

    pids = other_backfill_pids()
    if not _check(checks, "no_concurrent_backfill", not pids,
                 f"other backfill processes: {pids}" if pids else "none running"):
        reasons.append(f"another backfill process is running (pid {pids}) -- "
                       f"refusing to add a second writer")

    db_exists = Path(args.db).exists()
    _check(checks, "db_exists", db_exists, args.db, blocking=False)

    if dates_ok and not frozen and db_exists:
        conn = connect_ro(args.db)
        try:
            tickers = resolve_universe()
            plan, non_ihsg = plan_dates(conn, args.start_date, args.end_date, tickers)
        finally:
            conn.close()
        report["dates_selected"] = [p["date"] for p in plan]
        report["dates_skipped_already_complete"] = [p["date"] for p in plan if p["skip"]]
        report["dates_needing_work"] = [p["date"] for p in plan if not p["skip"]]
        report["estimated_missing_cells"] = sum(p["missing"] for p in plan)
        report["non_ihsg_dates"] = non_ihsg
    elif dates_ok and not frozen and not db_exists:
        reasons.append(f"database not found: {args.db}")

    blocking_failed = [c["name"] for c in checks if c["blocking"] and not c["ok"]]

    if live_requested and not confirmed_flag:
        _check(checks, "execution_confirmed", False, f"{CONFIRM_FLAG} not supplied")
        reasons.append(f"--live requires the explicit {CONFIRM_FLAG} confirmation "
                       f"flag -- it makes real Stockbit calls")
        blocking_failed.append("execution_confirmed")

    if blocking_failed:
        report["status"] = "BLOCKED"
    elif not live_requested:
        report["status"] = "COMPLETE" if not report["dates_needing_work"] else "PARTIAL"
    else:
        lock = AgentLock(args.lock_file)
        if not lock.acquire():
            reasons.append(f"another driver invocation holds the lock "
                           f"{args.lock_file} -- refusing to run concurrently")
            _check(checks, "driver_lock_acquired", False, str(args.lock_file))
            report["status"] = "BLOCKED"
        else:
            _check(checks, "driver_lock_acquired", True, str(args.lock_file))
            try:
                late = other_backfill_pids()
                if late:
                    reasons.append(f"backfill process appeared before launch "
                                   f"(pid {late}) -- aborting, nothing executed")
                    report["status"] = "BLOCKED"
                elif not report["dates_needing_work"]:
                    report["status"] = "COMPLETE"
                else:
                    python = args.python or default_python()
                    report["vendor_calls_made"] = True
                    outcomes, stopped = run_sequence(
                        report["dates_needing_work"], python, args.runner,
                        args.budget_s, args.db, TIMEOUT_MARGIN_S)
                    report["outcomes"] = [
                        {"date": o.date, "returncode": o.returncode,
                         "timed_out": o.timed_out, "command": o.command}
                        for o in outcomes
                    ]
                    report["stopped_reason"] = stopped
                    report["status"] = "FAILED" if stopped else "COMPLETE"
                    if stopped:
                        reasons.append(stopped)
            finally:
                lock.release()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print_report(report)
    return STATUS_EXIT[report["status"]]


def print_report(r: dict) -> None:
    print("=== broker_flow full-universe backfill DRIVER ===")
    print(f"Window:  [{r['start_date']}, {r['end_date']})  -- --end-date is EXCLUSIVE")
    print(f"Status:  {r['status']}")
    print(f"Dates selected:            {len(r['dates_selected'])}")
    print(f"Dates skipped (complete):  {len(r['dates_skipped_already_complete'])}")
    print(f"Dates needing work:        {len(r['dates_needing_work'])}")
    print(f"Estimated missing cells:   {r['estimated_missing_cells']}")
    print(f"Vendor calls made:         {r['vendor_calls_made']}")
    if r["stopped_reason"]:
        print(f"Stopped:                   {r['stopped_reason']}")
    print("\nSafety checks:")
    for c in r["safety_checks"]:
        mark = "✓" if c["ok"] else ("✗" if c["blocking"] else "~")
        print(f"  {mark} {c['name']}: {c['detail']}")
    for x in r["reasons"]:
        print(f"REASON: {x}")


if __name__ == "__main__":
    sys.exit(main())
