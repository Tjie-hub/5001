#!/usr/bin/env python3
"""IDX80 `broker_flow` backfill RUNNER — the production fetch/write path.

Scope is IDX80 by construction: the universe is always
`tools.broker_flow_idx80_gap.idx80_universe()` (a live query against
`idx_tickers WHERE status='active' AND in_idx80=1`) — there is no `--cat`
flag and no way to widen it from this runner. The orchestrator
(`tools/agent_backfill_broker_flow_idx80.py`) is the safety/planning layer
that supervises this runner one trading date at a time; this file never
talks to the orchestrator and never enforces its own lock (see that module's
docstring for the concurrency guard and the "why a separate orchestrator"
rationale, which this runner mirrors exactly for the sibling
`stockbit_flow_bars` dataset in `tools/backfill_flow_bars.py`).

Writes ONLY `broker_flow` and `bandar_detector` — both populated from the
SAME single call to `stockbit_fetcher.fetch_broker_flow()` (one HTTP request
returns `broker_summary` for the former and a summary rollup for the
latter). No other table is touched. `ticks`, `stockbit_flow_bars`, and
`stockbit_flow` come from a completely different vendor endpoint
(`order-trade/trade-book/chart`) and are out of scope for this agent.

EMPTY-RESPONSE HANDLING (do not skip this)
-------------------------------------------
The vendor can return HTTP 200 with genuinely empty broker arrays for a real
trading session. A single empty response is NOT proof the session has no
broker activity — it is retried EMPTY_RETRIES more times (EMPTY_RETRY_DELAY_S
apart) before being accepted. Only after every attempt comes back empty is
the cell marked EMPTY_CONFIRMED, by writing a `bandar_detector` row with
`value=0 AND volume=0` — the same durable-marker pattern
`tools/flow_bars_gap.py` uses via `stockbit_flow`'s own zero-activity rows
for the sibling bars dataset. See `tools/broker_flow_idx80_gap.py` for the
completion predicate this marker feeds.

A transient failure (network error, timeout, a 429 ladder inside
`fetch_broker_flow` itself) is a SEPARATE retry path (MAX_RETRIES, backoff)
and is NEVER treated as evidence of an empty session — it terminates in
FAILED_HTTP / FAILED_TIMEOUT / RATE_LIMITED, none of which write anything,
so a rerun retries the cell from scratch rather than wrongly concluding it
was checked and found empty.

Exit codes (mirrors tools/backfill_flow_bars.py's convention):
  0  ran to completion or a planned budget stop (state is whatever the DB
     shows -- rc==0 is NOT evidence of full coverage; recompute from the DB)
  2  authentication failure
  3  sustained fetch failure (SUSTAINED_FAIL_LIMIT consecutive non-success outcomes)
  4  database write failure

Usage:
  # plan only -- no vendor calls, no writes
  venv/bin/python3 tools/backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2025-01-10 --dry-run

  # bounded live diagnostic -- BBCA only, first+last date of the window
  venv/bin/python3 tools/backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2025-06-01 --probe

  # a single trading date (the shape the orchestrator actually launches)
  venv/bin/python3 tools/backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2025-01-03

Logs to: backfill_broker_flow_idx80.log
"""
import argparse
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from data.db import connect as db_connect  # noqa: E402
import stockbit_fetcher as sf  # noqa: E402
from tools.broker_flow_idx80_gap import (  # noqa: E402
    idx80_universe, canonical_trading_dates, missing_cells,
)
from tools.broker_flow_pit_planning import required_members  # noqa: E402

DB_PATH = HERE / "data" / "walkforward.db"
LOG_PATH = HERE / "backfill_broker_flow_idx80.log"

RATE_LIMIT_DELAY = 1.5     # between vendor requests -- matches stockbit_fetcher.RATE_LIMIT_DELAY
MAX_RETRIES = 3            # transient (network/HTTP) failures -- matches backfill_broker_flow_gap.py
RETRY_BACKOFF_S = 5        # matches backfill_broker_flow_gap.py
EMPTY_RETRIES = 2          # extra attempts before accepting a session as genuinely empty
EMPTY_RETRY_DELAY_S = 5
SUSTAINED_FAIL_LIMIT = 25  # consecutive non-success outcomes => vendor outage, abort

HARD_CAP_S = 5 * 3600
DEFAULT_BUDGET_S = 17400

# Outcome taxonomy -- every cell ends in exactly one of these.
POPULATED = "POPULATED"
SKIPPED = "SKIPPED"
EMPTY_CONFIRMED = "EMPTY_CONFIRMED"
FAILED_HTTP = "FAILED_HTTP"
FAILED_TIMEOUT = "FAILED_TIMEOUT"
RATE_LIMITED = "RATE_LIMITED"

EXIT_OK = 0
EXIT_AUTH = 2
EXIT_SUSTAINED = 3
EXIT_DB = 4


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


def _write_populated(conn, result: dict) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO broker_flow
        (ticker,trade_date,broker_code,side,lot,lot_value,value,
         value_total,avg_price,freq,investor_type)
        VALUES (:ticker,:trade_date,:broker_code,:side,:lot,:lot_value,
                :value,:value_total,:avg_price,:freq,:investor_type)""",
        result["broker_rows"],
    )
    b = result.get("bandar") or {}
    if b:
        conn.execute(
            """INSERT OR REPLACE INTO bandar_detector
            (ticker,trade_date,avg_price,total_buyer,total_seller,
             net_broker_count,broker_accdist,value,volume,
             top1_accdist,top3_accdist,top5_accdist,top10_accdist,
             avg_accdist,updated_at)
            VALUES (:ticker,:trade_date,:avg_price,:total_buyer,:total_seller,
                    :net_broker_count,:broker_accdist,:value,:volume,
                    :top1_accdist,:top3_accdist,:top5_accdist,:top10_accdist,
                    :avg_accdist,:updated_at)""",
            b,
        )
    conn.commit()


def _write_confirmed_empty(conn, ticker: str, trade_date: str) -> None:
    """Durable 'fetched, retried, genuinely empty' marker -- see module
    docstring. Only broker_flow has nothing to write for an empty session;
    bandar_detector is what makes the empty result durable and distinguishable
    from 'not yet fetched'."""
    conn.execute(
        """INSERT OR REPLACE INTO bandar_detector
        (ticker,trade_date,avg_price,total_buyer,total_seller,
         net_broker_count,broker_accdist,value,volume,
         top1_accdist,top3_accdist,top5_accdist,top10_accdist,
         avg_accdist,updated_at)
        VALUES (?,?,NULL,NULL,NULL,NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,?)""",
        (ticker, trade_date, datetime.now().isoformat()),
    )
    conn.commit()


def _fetch_with_outer_retry(token: str, ticker: str, trade_date: str):
    """Wrap sf.fetch_broker_flow with MAX_RETRIES against transient
    network/timeout errors (NOT against an empty-but-successful payload --
    that is a separate, outer retry loop in fetch_and_store_cell).

    Returns (terminal_outcome, result): terminal_outcome is None on a request
    that actually completed (result is the fetch_broker_flow return value,
    itself None on a plain non-429 HTTP failure), or one of
    RATE_LIMITED/FAILED_TIMEOUT/FAILED_HTTP when every retry was exhausted.
    """
    outcome = FAILED_HTTP
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return None, sf.fetch_broker_flow(token, ticker, trade_date)
        except sf.RateLimitExceeded:
            return RATE_LIMITED, None
        except requests.exceptions.Timeout:
            outcome = FAILED_TIMEOUT
        except Exception:
            outcome = FAILED_HTTP
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_S * attempt)
    return outcome, None


def fetch_and_store_cell(conn, token: str, ticker: str, trade_date: str) -> str:
    """Fetch + write ONE (ticker, trade_date) cell. Returns the outcome
    taxonomy constant. Never called for a cell the gap predicate already
    considers complete -- that decision belongs to the caller (run())."""
    for empty_attempt in range(1, EMPTY_RETRIES + 2):
        terminal, result = _fetch_with_outer_retry(token, ticker, trade_date)
        if terminal is not None:
            return terminal
        if result is None:
            return FAILED_HTTP
        if result.get("broker_rows"):
            _write_populated(conn, result)
            return POPULATED
        if empty_attempt < EMPTY_RETRIES + 1:
            time.sleep(EMPTY_RETRY_DELAY_S)
    _write_confirmed_empty(conn, ticker, trade_date)
    return EMPTY_CONFIRMED


def run(date_from: str, date_to: str, conn=None, db_path=None,
       budget_s: int = DEFAULT_BUDGET_S, dry_run: bool = False,
       probe: bool = False, token: str = None,
       universe_mode: str = "live") -> dict:
    """Run the IDX80 broker-flow backfill over [date_from, date_to).

    `conn` is a seam for tests (an already-open connection is reused as-is,
    never closed here); production callers leave it None and get a fresh
    `data.db.connect()` handle against `db_path` (default DB_PATH), closed on
    return. Gap detection is entirely DB-derived -- resume needs no cursor.

    universe_mode: "live" (default -- today's active idx_tickers roster;
    unchanged historical behavior) or "pit" (per-date point-in-time roster
    from the WP-D ledger via tools.broker_flow_pit_planning -- the roster is
    the data-collection authority: never truncated to the nominal 80, never
    padded, never substituted by idx_tickers; !=80 roster sizes and
    uncovered dates emit advisory WARNING lines and never filter cells).
    """
    if universe_mode not in ("live", "pit"):
        raise ValueError(f"universe_mode must be 'live' or 'pit', "
                         f"got {universe_mode!r}")
    owns_conn = conn is None
    if owns_conn:
        conn = db_connect(str(db_path or DB_PATH))

    tickers = universe(conn)
    dates = gap_dates(conn, date_from, date_to)

    rosters = None
    advisories = []
    if universe_mode == "pit":
        rosters = {}
        for d in dates:
            roster, advisory = required_members(conn, d)
            rosters[d] = roster
            if advisory is not None:
                advisories.append(advisory)
                log(f"WARNING: {advisory['message']} [date={d} "
                    f"period={advisory['period_label']} "
                    f"confidence={advisory['confidence']}]")

    def _roster(d):
        return tickers if rosters is None else rosters[d]

    if probe:
        if not dates:
            log(f"PROBE: no canonical trading dates in [{date_from},{date_to}) "
                f"-- nothing to probe, no vendor calls made")
            if owns_conn:
                conn.close()
            return {"dry_run": False, "probe": True, "universe_mode": universe_mode,
                    "planned_cells": 0,
                    "populated": 0, "empty_confirmed": 0, "skipped": 0,
                    "failed_http": 0, "failed_timeout": 0, "rate_limited": 0,
                    "dates": [], "elapsed_s": 0.0, "sustained_abort": False,
                    "advisories": 0, "advisory_log": []}
        dates = [dates[0]] if len(dates) == 1 else [dates[0], dates[-1]]
        tickers = ["BBCA"] if "BBCA" in tickers else tickers[:1]
        if universe_mode == "pit":
            log("NOTE: probe is a vendor-endpoint diagnostic (BBCA only); "
                "it does not exercise the PIT roster")
        rosters = None   # a probe exercises the endpoint, not roster planning

    stats = {
        "dry_run": dry_run, "probe": probe, "universe_mode": universe_mode,
        "planned_cells": (sum(len(rosters[d]) for d in dates)
                          if rosters is not None
                          else len(tickers) * len(dates)),
        "populated": 0, "empty_confirmed": 0, "skipped": 0,
        "failed_http": 0, "failed_timeout": 0, "rate_limited": 0,
        "dates": dates, "sustained_abort": False,
        "advisories": len(advisories), "advisory_log": advisories,
    }

    if dry_run:
        log(f"=== DRY RUN: {len(dates)} date(s) x "
            f"{'PIT roster' if rosters is not None else f'{len(tickers)} IDX80 ticker(s)'} "
            f"[{date_from},{date_to}) -- no vendor calls, no writes ===")
        for d in dates:
            roster = _roster(d)
            need = missing_cells(conn, d, roster)
            suffix = (f" (PIT roster={len(roster)})"
                      if rosters is not None else "")
            log(f"  [plan] {d}: {len(need)} incomplete cells{suffix}")
        stats["elapsed_s"] = 0.0
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

    log(f"=== Backfill start: {len(dates)} date(s) x "
        f"{'PIT' if rosters is not None else f'{len(tickers)} IDX80'} "
        f"universe [{date_from},{date_to}) budget={budget_s}s probe={probe} "
        f"universe_mode={universe_mode} ===")

    t0 = time.time()
    consec_fail = 0
    for di, d in enumerate(dates, 1):
        roster = _roster(d)
        need = missing_cells(conn, d, roster)
        stats["skipped"] += len(roster) - len(need)
        if not need:
            log(f"[{di}/{len(dates)}] {d}: already complete -- skip")
            continue
        log(f"[{di}/{len(dates)}] {d}: {len(need)} missing cells")
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
    log(f"=== DONE: populated={stats['populated']} "
        f"empty_confirmed={stats['empty_confirmed']} skipped={stats['skipped']} "
        f"failed_http={stats['failed_http']} failed_timeout={stats['failed_timeout']} "
        f"rate_limited={stats['rate_limited']} in {stats['elapsed_s']/60:.1f}min ===")
    log("CHECKPOINT: gaps are recomputed from DB state on next run -- "
        "resume needs no cursor, no ordering")
    if owns_conn:
        conn.close()
    return stats


def build_parser():
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
    ap.add_argument("--universe", choices=("live", "pit"), default="live",
                    help="live (default): today's active idx_tickers IDX80 "
                         "roster -- unchanged historical behavior. pit: "
                         "per-date point-in-time roster from the WP-D ledger "
                         "(idx80_reconstitution_periods / "
                         "idx80_membership_history) via "
                         "tools.broker_flow_pit_planning -- the roster is "
                         "the data-collection authority: all resolved "
                         "members are fetched, never truncated to 80, "
                         "never padded, never substituted by idx_tickers; "
                         "roster sizes != 80 emit advisories, not filters")
    ap.add_argument("--db", default=str(DB_PATH))
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    budget_s = min(args.budget_s, HARD_CAP_S)
    stats = run(args.date_from, args.date_to, db_path=args.db,
               budget_s=budget_s, dry_run=args.dry_run, probe=args.probe,
               universe_mode=args.universe)

    if stats.get("auth_failed"):
        return EXIT_AUTH
    if stats.get("sustained_abort"):
        return EXIT_SUSTAINED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
