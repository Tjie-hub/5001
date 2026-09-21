#!/usr/bin/env python3
"""IDX80 foreign-flow (`broker_flow` `investor_type='Asing'`) backfill
RUNNER -- the production fetch/write path for the foreign-flow AUDIT LAYER.

This is NOT a new fetcher and does NOT talk to a new vendor endpoint. Every
HTTP fetch and every write is delegated to
`tools.backfill_broker_flow_idx80.fetch_and_store_cell()` -- the SAME
vendor call (`stockbit_fetcher.fetch_broker_flow`, which already requests
`investor_type=INVESTOR_TYPE_ALL` and returns Asing/Lokal/Pemerintah broker
rows together in one response) already used to populate `broker_flow`. See
`tools/foreign_flow_idx80_gap.py`'s module docstring for the evidence that
no separate foreign-flow schema or endpoint exists.

The ONLY thing this runner owns is WHICH cells get attempted:
`tools.foreign_flow_idx80_gap`'s foreign-specific gap predicate, instead of
`tools.broker_flow_idx80_gap`'s. Because it delegates the fetch/write path,
this inherits UNCHANGED: retry on transient HTTP/timeout (MAX_RETRIES),
429/Retry-After handling via `stockbit_fetcher.RateLimitExceeded`,
empty-response retry-then-confirm (EMPTY_RETRIES) before writing the
`bandar_detector` zero-value marker, INSERT-OR-REPLACE-only writes to
`broker_flow`/`bandar_detector`, and DB-derived resume (no cursor). Scope is
IDX80 by construction: the universe is always
`tools.foreign_flow_idx80_gap.idx80_universe()` -- there is no `--cat` flag
and no way to widen it.

CONCURRENCY WITH tools/backfill_broker_flow_idx80.py
-------------------------------------------------------
This runner and the broker_flow runner write the SAME tables via the SAME
vendor call. Running both against overlapping cells at once is wasteful (a
duplicate vendor call) but not corrupting -- INSERT OR REPLACE is
idempotent, and data/db.py's WAL+busy_timeout absorbs the write race. The
orchestrator (`tools/agent_backfill_foreign_flow_idx80.py`) is what actually
refuses to run this concurrently with either runner; see that module's
docstring for the dual-marker concurrency guard.

EMPTY-RESPONSE / RETRY / EXIT-CODE / OUTCOME TAXONOMY
----------------------------------------------------------
Identical to `tools/backfill_broker_flow_idx80.py` -- this module re-exports
its outcome constants (POPULATED, EMPTY_CONFIRMED, FAILED_HTTP,
FAILED_TIMEOUT, RATE_LIMITED) and exit codes rather than redefining them, so
the two can never drift.

Usage:
  # plan only -- no vendor calls, no writes
  venv/bin/python3 tools/backfill_foreign_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2025-01-10 --dry-run

  # bounded live diagnostic -- BBCA only, first+last date of the window
  venv/bin/python3 tools/backfill_foreign_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 --probe

  # a single trading date (the shape the orchestrator actually launches)
  venv/bin/python3 tools/backfill_foreign_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2025-01-03

Logs to: backfill_foreign_flow_idx80.log
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from data.db import connect as db_connect  # noqa: E402
import stockbit_fetcher as sf  # noqa: E402
from tools import backfill_broker_flow_idx80 as B  # noqa: E402
from tools.foreign_flow_idx80_gap import (  # noqa: E402
    idx80_universe,
    canonical_trading_dates,
    missing_cells,
    foreign_cell_state,
    STATE_PRESENT,
    STATE_CONFIRMED_EMPTY_FOREIGN_ONLY,
    STATE_CONFIRMED_EMPTY_SESSION,
    STATE_MISSING,
)

DB_PATH = HERE / "data" / "walkforward.db"
LOG_PATH = HERE / "backfill_foreign_flow_idx80.log"

# Re-exported, not redefined -- see module docstring "EMPTY-RESPONSE / RETRY
# / EXIT-CODE / OUTCOME TAXONOMY".
RATE_LIMIT_DELAY = B.RATE_LIMIT_DELAY
MAX_RETRIES = B.MAX_RETRIES
EMPTY_RETRIES = B.EMPTY_RETRIES
SUSTAINED_FAIL_LIMIT = B.SUSTAINED_FAIL_LIMIT

HARD_CAP_S = B.HARD_CAP_S
DEFAULT_BUDGET_S = B.DEFAULT_BUDGET_S

POPULATED = B.POPULATED
SKIPPED = B.SKIPPED
EMPTY_CONFIRMED = B.EMPTY_CONFIRMED
FAILED_HTTP = B.FAILED_HTTP
FAILED_TIMEOUT = B.FAILED_TIMEOUT
RATE_LIMITED = B.RATE_LIMITED

EXIT_OK = 0
EXIT_AUTH = 2
EXIT_SUSTAINED = 3
EXIT_DB = 4

# The single fetch+write implementation this runner delegates to -- see
# module docstring. Exposed at module level (rather than called only via
# `B.fetch_and_store_cell`) so callers/tests can monkeypatch or invoke it
# the same way they would a locally-defined function.
fetch_and_store_cell = B.fetch_and_store_cell


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def universe(conn) -> list:
    return idx80_universe(conn)


def gap_dates(conn, date_from: str, date_to: str) -> list:
    """Canonical IHSG-confirmed trading dates in [date_from, date_to)."""
    confirmed, _non_ihsg = canonical_trading_dates(conn, date_from, date_to)
    return confirmed


def foreign_breakdown(conn, tickers: list, dates: list) -> dict:
    """Diagnostic-only foreign-specific state counts across the window.

    Never used for gap-only decisions -- those go through missing_cells().
    Distinguishes genuine foreign activity from a confirmed-zero-foreign
    session and from a not-yet-fetched cell, per
    tools/foreign_flow_idx80_gap.py's state taxonomy.
    """
    counts = {
        STATE_PRESENT: 0,
        STATE_CONFIRMED_EMPTY_FOREIGN_ONLY: 0,
        STATE_CONFIRMED_EMPTY_SESSION: 0,
        STATE_MISSING: 0,
    }
    for d in dates:
        for t in tickers:
            counts[foreign_cell_state(conn, t, d)] += 1
    return counts


def run(date_from: str, date_to: str, conn=None, db_path=None,
       budget_s: int = DEFAULT_BUDGET_S, dry_run: bool = False,
       probe: bool = False, token: str = None) -> dict:
    """Run the IDX80 foreign-flow backfill over [date_from, date_to).

    Gap-only: this function only decides WHICH cells to attempt (the
    foreign-specific gap) and reports foreign-specific coverage. The actual
    fetch+write of every attempted cell is delegated to
    tools.backfill_broker_flow_idx80.fetch_and_store_cell.

    `conn` is a seam for tests (an already-open connection is reused as-is,
    never closed here); production callers leave it None and get a fresh
    `data.db.connect()` handle against `db_path` (default DB_PATH), closed on
    return. Gap detection is entirely DB-derived -- resume needs no cursor.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = db_connect(str(db_path or DB_PATH))

    tickers = universe(conn)
    dates = gap_dates(conn, date_from, date_to)

    if probe:
        if not dates:
            log(f"PROBE: no canonical trading dates in [{date_from},{date_to}) "
                f"-- nothing to probe, no vendor calls made")
            if owns_conn:
                conn.close()
            return {"dry_run": False, "probe": True, "planned_cells": 0,
                    "populated": 0, "empty_confirmed": 0, "skipped": 0,
                    "failed_http": 0, "failed_timeout": 0, "rate_limited": 0,
                    "dates": [], "elapsed_s": 0.0, "sustained_abort": False}
        dates = [dates[0]] if len(dates) == 1 else [dates[0], dates[-1]]
        tickers = ["BBCA"] if "BBCA" in tickers else tickers[:1]

    stats = {
        "dry_run": dry_run, "probe": probe,
        "planned_cells": len(tickers) * len(dates),
        "populated": 0, "empty_confirmed": 0, "skipped": 0,
        "failed_http": 0, "failed_timeout": 0, "rate_limited": 0,
        "dates": dates, "sustained_abort": False,
    }

    if dry_run:
        log(f"=== DRY RUN (foreign-flow): {len(dates)} date(s) x {len(tickers)} "
            f"IDX80 ticker(s) [{date_from},{date_to}) -- no vendor calls, no writes ===")
        for d in dates:
            need = missing_cells(conn, d, tickers)
            log(f"  [plan] {d}: {len(need)} incomplete foreign-flow cells")
        stats["elapsed_s"] = 0.0
        stats["foreign_breakdown"] = foreign_breakdown(conn, tickers, dates)
        if owns_conn:
            conn.close()
        return stats

    if token is None:
        token = sf.ensure_valid_token(None)
    if not token:
        log("ABORT: could not obtain a valid token (authentication failure)")
        if owns_conn:
            conn.close()
        stats["auth_failed"] = True
        return stats

    log(f"=== Foreign-flow backfill start: {len(dates)} date(s) x {len(tickers)} "
        f"IDX80 ticker(s) [{date_from},{date_to}) budget={budget_s}s probe={probe} ===")

    t0 = time.time()
    consec_fail = 0
    for di, d in enumerate(dates, 1):
        need = missing_cells(conn, d, tickers)
        stats["skipped"] += len(tickers) - len(need)
        if not need:
            log(f"[{di}/{len(dates)}] {d}: already complete (foreign) -- skip")
            continue
        log(f"[{di}/{len(dates)}] {d}: {len(need)} missing foreign-flow cells")
        for t in need:
            if time.time() - t0 > budget_s:
                log(f"BUDGET hit before {t} {d} -- safe stop; rerun to resume")
                stats["elapsed_s"] = time.time() - t0
                if owns_conn:
                    conn.close()
                return stats
            outcome = fetch_and_store_cell(conn, token, t, d)
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
                        f"at {d} {t} -- sustained vendor error/rate-limit condition")
                    stats["sustained_abort"] = True
                    stats["elapsed_s"] = time.time() - t0
                    if owns_conn:
                        conn.close()
                    return stats
            time.sleep(RATE_LIMIT_DELAY)

    stats["elapsed_s"] = time.time() - t0
    stats["foreign_breakdown"] = foreign_breakdown(conn, tickers, dates)
    log(f"=== DONE: populated={stats['populated']} "
        f"empty_confirmed={stats['empty_confirmed']} skipped={stats['skipped']} "
        f"failed_http={stats['failed_http']} failed_timeout={stats['failed_timeout']} "
        f"rate_limited={stats['rate_limited']} in {stats['elapsed_s']/60:.1f}min ===")
    log(f"FOREIGN BREAKDOWN: {stats['foreign_breakdown']}")
    log("CHECKPOINT: gaps are recomputed from DB state on next run -- "
        "resume needs no cursor, no ordering")
    if owns_conn:
        conn.close()
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True, help="EXCLUSIVE upper bound")
    ap.add_argument("--budget-s", type=int, default=DEFAULT_BUDGET_S,
                    help=f"wall-clock budget in seconds, clamped to {HARD_CAP_S}")
    ap.add_argument("--probe", action="store_true",
                    help="bounded live diagnostic: BBCA only, first+last "
                         "canonical date of the window")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only: no vendor calls, no writes")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args(argv)

    budget_s = min(args.budget_s, HARD_CAP_S)
    stats = run(args.date_from, args.date_to, db_path=args.db,
               budget_s=budget_s, dry_run=args.dry_run, probe=args.probe)

    if stats.get("auth_failed"):
        return EXIT_AUTH
    if stats.get("sustained_abort"):
        return EXIT_SUSTAINED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
