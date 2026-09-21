#!/usr/bin/env python3
"""Full-universe `broker_flow` / `bandar_detector` fetch — ONE trading date.

`tools/backfill_broker_flow_idx80.py` is IDX80-only "by construction" (its
own docstring): `universe()` always calls `idx80_universe()` and there is no
`--cat`/roster override on that runner at all — unlike the sibling
`stockbit_flow_bars` runner (`tools/backfill_flow_bars.py`), which already
defaults to the full universe. This script closes that gap for broker_flow
WITHOUT touching the IDX80 runner or its orchestrator: it imports and calls
the exact same `fetch_and_store_cell()` (same vendor call, same retry/empty-
confirmation logic, same write path) with a full-universe roster instead of
the IDX80-only one. No new vendor integration, no modified production file.

Deliberately narrower than the IDX80 orchestrator: single trading date only
(no date-range iteration — this is a pilot/audit tool, not a backfill
scheduler), no PIT roster mode, no per-date timeout/stall supervision (one
date is fast enough not to need it). For an actual multi-date historical
broker-flow repair, extend `tools/agent_backfill_broker_flow_idx80.py`
instead of this script.

CONCURRENCY
-----------
There is no live cron for broker_flow (checked `deploy/crontab` 2026-09-01:
only `stockbit_fetcher.py` OHLCV @ 08:50 and `flow` @ 18:30 are scheduled —
neither touches broker_flow/bandar_detector). The only realistic collision
is a human-launched `tools/backfill_broker_flow_idx80.py`,
`tools/agent_backfill_broker_flow_idx80.py`,
`tools/backfill_foreign_flow_idx80.py`, or
`tools/agent_backfill_foreign_flow_idx80.py` running at the same time — all
four write the identical tables. This script reuses
`tools.agent_backfill_broker_flow_idx80.other_backfill_pids()` (the existing
`/proc`-scan helper, `tools/`-prefixed marker matching) against all four
markers, plus its own fcntl lock against a second copy of itself. It does
NOT retrofit the four existing tools to recognize this script's own marker —
this is a manually-supervised, one-off pilot tool, not a scheduled writer,
so that asymmetry is accepted rather than justifying an edit to tested
production orchestrators for a one-time run.

FAIL-CLOSED UNIVERSE GUARD
---------------------------
`data.fetcher.load_all_tickers()` silently falls back to the 79-name IDX80
constant if `idx_tickers` and `data/idx_master.csv` are both unavailable.
A "full universe" run must never silently execute at IDX80 scale under the
FULL label — see FALLBACK_SIZE_FLOOR below.

Exit codes (extends the sibling runner's taxonomy with one new state):
  0  EXIT_OK         ran to completion or a planned budget stop
  2  EXIT_AUTH       authentication failure
  3  EXIT_SUSTAINED  sustained fetch failure (consecutive non-success outcomes)
  5  EXIT_BLOCKED    fail-closed universe guard tripped, OR a concurrent
                     writer was detected, OR the date is not a trading day

Usage:
  # plan only -- no vendor calls, no writes
  venv/bin/python3 tools/backfill_broker_flow_full_universe.py \
      --date 2026-08-31 --dry-run

  # real run (single trading date, full universe)
  venv/bin/python3 tools/backfill_broker_flow_full_universe.py \
      --date 2026-08-31 --yes-run-vendor-backfill

Logs to: backfill_broker_flow_full_universe.log
"""
import argparse
import fcntl
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from data.db import connect as db_connect  # noqa: E402
from data.fetcher import load_all_tickers  # noqa: E402
import stockbit_fetcher as sf  # noqa: E402
from tools.broker_flow_idx80_gap import canonical_trading_dates, missing_cells  # noqa: E402
from tools.backfill_broker_flow_idx80 import (  # noqa: E402
    fetch_and_store_cell, POPULATED, EMPTY_CONFIRMED, FAILED_HTTP,
    FAILED_TIMEOUT, RATE_LIMITED, RATE_LIMIT_DELAY, SUSTAINED_FAIL_LIMIT,
    DEFAULT_BUDGET_S, HARD_CAP_S,
)
from tools.agent_backfill_broker_flow_idx80 import other_backfill_pids  # noqa: E402

DB_PATH = HERE / "data" / "walkforward.db"
LOG_PATH = HERE / "backfill_broker_flow_full_universe.log"
DEFAULT_LOCK = HERE / "logs" / "backfill_broker_flow_full_universe.lock"

# Below this, load_all_tickers() has almost certainly hit its IDX80-sized
# fallback (79 names) rather than resolved the real ~900-ticker universe.
# See module docstring, FAIL-CLOSED UNIVERSE GUARD.
FALLBACK_SIZE_FLOOR = 200

CONFLICTING_MARKERS = (
    "tools/backfill_broker_flow_idx80.py",
    "tools/agent_backfill_broker_flow_idx80.py",
    "tools/backfill_foreign_flow_idx80.py",
    "tools/agent_backfill_foreign_flow_idx80.py",
)

EXIT_OK = 0
EXIT_AUTH = 2
EXIT_SUSTAINED = 3
EXIT_BLOCKED = 5


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


class AgentLock:
    """fcntl-based mutual exclusion against a second copy of this script.
    Mirrors the pattern in tools/agent_backfill_broker_flow_idx80.py."""

    def __init__(self, path):
        self._path = Path(path)
        self._fh = None

    def acquire(self) -> bool:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self._path, "w")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        return True

    def release(self) -> None:
        if self._fh is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
            self._fh = None


def resolve_universe() -> list:
    """Full ticker universe, fail-closed if it collapses to the IDX80-sized
    fallback. Raises RuntimeError rather than returning a silently-shrunk
    list -- see module docstring."""
    tickers = load_all_tickers()
    if len(tickers) < FALLBACK_SIZE_FLOOR:
        raise RuntimeError(
            f"load_all_tickers() resolved only {len(tickers)} tickers "
            f"(below the {FALLBACK_SIZE_FLOOR} fail-closed floor) -- this "
            f"looks like the IDX80-sized fallback, not the real full "
            f"universe. Refusing to run a FULL-UNIVERSE pass at IDX80 "
            f"scale. Check idx_tickers/data/idx_master.csv availability."
        )
    return tickers


def check_no_concurrent_writer(exclude_pid=None) -> list:
    """Returns a list of (marker, pid) pairs for any conflicting writer
    found running. Empty list means clear to proceed."""
    exclude = frozenset({exclude_pid}) if exclude_pid else frozenset()
    found = []
    for marker in CONFLICTING_MARKERS:
        for pid in other_backfill_pids(marker=marker, exclude=exclude):
            found.append((marker, pid))
    return found


def run(date: str, conn=None, db_path=None, budget_s: int = DEFAULT_BUDGET_S,
        dry_run: bool = False, token: str = None) -> dict:
    """Run the full-universe broker-flow fetch for ONE trading date.

    `conn` is a seam for tests, mirroring tools/backfill_broker_flow_idx80.py::run.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = db_connect(str(db_path or DB_PATH))

    tickers = resolve_universe()
    confirmed, non_ihsg = canonical_trading_dates(conn, date, _next_day(date))

    stats = {
        "date": date, "dry_run": dry_run,
        "universe_size": len(tickers),
        "is_trading_day": bool(confirmed),
        "non_ihsg_calendar_rows": non_ihsg,
        "planned_cells": 0,
        "populated": 0, "empty_confirmed": 0, "skipped": 0,
        "failed_http": 0, "failed_timeout": 0, "rate_limited": 0,
        "sustained_abort": False, "elapsed_s": 0.0,
    }

    if not confirmed:
        log(f"BLOCKED: {date} is not a confirmed IDX trading date "
            f"(no trading_calendar+IHSG evidence) -- refusing to fetch")
        stats["blocked_reason"] = "not_a_trading_day"
        if owns_conn:
            conn.close()
        return stats

    need = missing_cells(conn, date, tickers)
    stats["planned_cells"] = len(tickers)
    stats["skipped"] = len(tickers) - len(need)

    if dry_run:
        log(f"=== DRY RUN: {date} x {len(tickers)} full-universe tickers -- "
            f"{len(need)} incomplete cells -- no vendor calls, no writes ===")
        if owns_conn:
            conn.close()
        return stats

    if token is None:
        token = sf.ensure_valid_token(None)
    if not token:
        log("ABORT: could not obtain a valid token (authentication failure)")
        stats["auth_failed"] = True
        if owns_conn:
            conn.close()
        return stats

    log(f"=== Full-universe broker-flow start: {date} x {len(tickers)} "
        f"tickers -- {len(need)} incomplete cells budget={budget_s}s ===")
    t0 = time.time()
    consec_fail = 0
    for t in need:
        if time.time() - t0 > budget_s:
            log(f"BUDGET hit before {t} -- safe stop; rerun to resume")
            break
        outcome = fetch_and_store_cell(conn, token, t, date)
        if outcome == POPULATED:
            stats["populated"] += 1
            consec_fail = 0
        elif outcome == EMPTY_CONFIRMED:
            stats["empty_confirmed"] += 1
            consec_fail = 0
        else:
            consec_fail += 1
            if outcome == FAILED_HTTP:
                stats["failed_http"] += 1
            elif outcome == FAILED_TIMEOUT:
                stats["failed_timeout"] += 1
            elif outcome == RATE_LIMITED:
                stats["rate_limited"] += 1
            if consec_fail >= SUSTAINED_FAIL_LIMIT:
                log(f"ABORT: {consec_fail} consecutive non-success outcomes "
                    f"at {t} -- sustained vendor error/rate-limit condition")
                stats["sustained_abort"] = True
                break
        time.sleep(RATE_LIMIT_DELAY)

    stats["elapsed_s"] = time.time() - t0
    log(f"=== DONE: populated={stats['populated']} "
        f"empty_confirmed={stats['empty_confirmed']} skipped={stats['skipped']} "
        f"failed_http={stats['failed_http']} failed_timeout={stats['failed_timeout']} "
        f"rate_limited={stats['rate_limited']} in {stats['elapsed_s']/60:.1f}min ===")
    if owns_conn:
        conn.close()
    return stats


def _next_day(date: str) -> str:
    return (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", required=True, help="single trading date, YYYY-MM-DD")
    ap.add_argument("--budget-s", type=int, default=DEFAULT_BUDGET_S,
                    help=f"wall-clock budget in seconds, clamped to {HARD_CAP_S}")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only: no vendor calls, no writes")
    ap.add_argument("--yes-run-vendor-backfill", action="store_true",
                    help="required to make real vendor calls (safety gate)")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--lock-file", default=str(DEFAULT_LOCK))
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if not args.dry_run and not args.yes_run_vendor_backfill:
        log("BLOCKED: real run requires --yes-run-vendor-backfill "
            "(pass --dry-run to plan without it)")
        return EXIT_BLOCKED

    lock = AgentLock(args.lock_file)
    if not lock.acquire():
        log(f"BLOCKED: could not acquire {args.lock_file} -- "
            f"another instance of this script is already running")
        return EXIT_BLOCKED

    try:
        conflicts = check_no_concurrent_writer()
        if conflicts and not args.dry_run:
            for marker, pid in conflicts:
                log(f"BLOCKED: conflicting writer detected -- {marker} (pid={pid})")
            return EXIT_BLOCKED

        try:
            budget_s = min(args.budget_s, HARD_CAP_S)
            stats = run(args.date, db_path=args.db, budget_s=budget_s,
                       dry_run=args.dry_run)
        except RuntimeError as e:
            log(f"BLOCKED: {e}")
            return EXIT_BLOCKED

        if stats.get("blocked_reason"):
            return EXIT_BLOCKED
        if stats.get("auth_failed"):
            return EXIT_AUTH
        if stats.get("sustained_abort"):
            return EXIT_SUSTAINED
        return EXIT_OK
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
