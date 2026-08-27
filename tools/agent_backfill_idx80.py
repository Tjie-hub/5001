#!/usr/bin/env python3
"""IDX80 `stockbit_flow_bars` backfill ORCHESTRATOR (agent wrapper).

This is NOT a fetcher. It never talks to Stockbit, never writes to any table,
and never reimplements the vendor/write path. It plans, guards, and audits a
run of the production runner `tools/backfill_flow_bars.py`, which remains the
single implementation of the HTTP and write logic.

WHY THIS EXISTS
---------------
The production runner returns **exit code 0 for a planned budget stop with work
remaining**, for a frozen-fixture barrier stop, and for a genuinely finished
window alike (see its module docstring, "Exit codes"). Its only completion
signal is two log lines. So `rc == 0` is NOT evidence of coverage, and an
operator (or an agent) reading it as such is exactly how a backfill "completes"
while leaving a systematically-holed panel behind -- the failure mode already
recorded in docs/audit/STOCKBIT_FLOW_BARS_BACKFILL_STATE_2026-08-20.md
(9,341 cells silently skipped).

This wrapper therefore re-derives ticker-day coverage from the database before
AND after any execution, and reports COMPLETE only when the requested interval
is actually covered.

SAFETY POSTURE (fail-closed)
----------------------------
  * Default action is `plan` -- read-only, no vendor calls, no writes.
  * The DB handle is opened `mode=ro`; a write raises rather than mutating.
  * Execution requires BOTH `--action execute` AND the explicit
    `--yes-run-vendor-backfill` confirmation flag. There is no path that
    silently upgrades a plan into a run.
  * Default category is IDX80 (79 names). Any other category is refused unless
    `--allow-non-idx80` is passed -- this agent's mission is IDX80.
  * `--release-fixture` is NEVER passed to the runner, and a window whose only
    work is the frozen fixture date is refused outright.
  * A concurrency guard (fcntl lock + /proc scan) blocks rather than risking a
    second writer against the same SQLite file, and supervised date children
    run strictly one at a time.

SUPERVISED DATE-LEVEL EXECUTION
-------------------------------
`--action execute` never launches one multi-date runner for a big window. The
production runner was observed alive for 18+ minutes on the 325-date window
[2025-04-15, 2026-08-27) with no completion signal; its exit code 0 means
"planned budget stop" just as often as "finished", and one wedged child holds
the whole backfill hostage. Execution therefore runs the runner EXACTLY ONE
TRADING DATE AT A TIME:

    discover eligible dates (canonical IHSG-backed sessions, in order)
        -> for each date:
             skip it when the DB already shows the date complete
                (resume is derived from the DB, never from a cursor)
             launch the runner for [date, date+1day) ONLY
             enforce --date-timeout-s (wall clock) and
                --no-progress-timeout-s (no newly-complete cell), killing a
                wedged child safely (SIGTERM, then SIGKILL after a grace)
             re-derive coverage from the DB: the date is SUCCESS only when
                its cells are actually complete
             a FAILED/STALLED date never blocks the next date

Per-date outcomes are SUCCESS / SKIPPED / FAILED / STALLED. The overall
verdict stays COMPLETE / PARTIAL / FAILED / BLOCKED, and COMPLETE is only
claimed when every expected date is actually covered -- a window containing
the frozen fixture can never be COMPLETE through this agent, exactly as in
plan mode.

COVERAGE SEMANTICS -- read this before trusting a number
--------------------------------------------------------
A cell is (ticker, trade_date). Two different counts are reported, because
they answer different questions:

  present_ticker_days   cells with >= 1 row in `stockbit_flow_bars`.
  complete_ticker_days  cells the RUNNER considers done, i.e. the predicate in
                        tools/flow_bars_gap.py: bars exist, OR a `stockbit_flow`
                        summary row records a genuinely empty session.

COMPLETE/PARTIAL is decided on `complete_ticker_days`, because ~12% of IDX80
cells are legitimately empty sessions that have no bars and never will -- a
bars-only verdict could never reach COMPLETE and would re-queue those cells
forever. `present_ticker_days` is reported alongside so the two can never be
silently conflated. Row counts are never used.

CALENDAR SEMANTICS -- a real divergence, reported not hidden
------------------------------------------------------------
Expected cells are `trading_calendar` x IDX80 -- but only for calendar dates the
canonical authority actually confirmed. `trading_calendar` has two independent
writers:

  data/market_schema.py::build_trading_calendar  source='IHSG'        canonical:
      "IDX trading dates derived from IHSG bars" (that module's own definition).
  screener/idx_scraper.py::save_ohlcv_to_db      source='scraper_eod' a side
      effect of every finalized 16:15 EOD save, inserted without consulting IHSG.

They can disagree. Measured on data/walkforward.db at 2026-08-27: 1235 rows are
IHSG-backed and exactly one -- 2026-08-25, source='scraper_eod' -- has no IHSG
bar at all, while carrying 913 finalized per-ticker `ohlcv` rows and zero
`stockbit_flow_bars`. Demanding IDX80 bars for a session the canonical authority
never confirmed pins the verdict at PARTIAL forever over 79 phantom cells.

So a date is EXPECTED only when a `trading_calendar` row AND an IHSG `ohlcv` bar
both exist for it. The predicate is the IHSG bar, never the `source` string:
`INSERT OR IGNORE` means whichever writer got there first owns `source` for good,
so a date first seen by the scraper keeps source='scraper_eod' even after IHSG
confirms it. Excluded rows are listed in `calendar.non_ihsg_dates` (with their
source) and counted in `calendar.calendar_rows_in_window` -- dropped from the
expectation, never from the report. No holiday list is maintained here and no
calendar row is ever mutated; this tool cannot write.

Separately, the runner derives its own work list from `SELECT DISTINCT date FROM
ohlcv` (tools/backfill_flow_bars.py::gap_dates), so any `trading_calendar` date
absent from `ohlcv` entirely is a cell the runner CANNOT reach -- reported as
`calendar.unreachable_dates`, still measured against the raw calendar rows. That
is a strictly narrower set than `non_ihsg_dates` (no ohlcv rows at all implies no
IHSG bar); the two are kept apart because they answer different questions:
"the runner cannot iterate this date" vs "this date is not a confirmed session".

EXIT CODES
----------
  0  COMPLETE  the requested interval is fully covered
  1  PARTIAL   work remains (this includes a successful but budget-bounded run
               or a window whose only unresolved cells are the frozen fixture)
  2  FAILED    a date child timed out, stalled, exited nonzero, or left cells
               incomplete (probe: the runner exited nonzero or timed out)
  3  BLOCKED   not safe to run / invalid request -- nothing was executed

Usage:
  # read-only plan (default)
  venv/bin/python3 tools/agent_backfill_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 --json

  # explicit, unmistakable execution -- one runner per trading date
  venv/bin/python3 tools/agent_backfill_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 \
      --action execute --yes-run-vendor-backfill --budget-s 17400 \
      --date-timeout-s 3600 --no-progress-timeout-s 900
"""
import argparse
import fcntl
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date as _date, timedelta
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

DEFAULT_DB = HERE / "data" / "walkforward.db"
DEFAULT_RUNNER = HERE / "tools" / "backfill_flow_bars.py"
DEFAULT_LOCK = HERE / "logs" / "agent_backfill_idx80.lock"

# Mirrors tools/backfill_flow_bars.HARD_CAP_S / FROZEN_FIXTURE_DATES. Duplicated
# deliberately so this read-only orchestrator does not import the vendor client
# (stockbit_fetcher -> requests) just to validate a flag. Equality with the
# runner is asserted by tests/test_agent_backfill_idx80.py, so the copies
# cannot drift silently.
HARD_CAP_S = 18000
FROZEN_FIXTURE_DATES = ("2025-04-14",)

# The documented Day-1 launch contract wraps budget 17400 in `timeout 18120`.
# Same 720s margin: enough for the runner's own clean shutdown, not enough to
# let a wedged process outlive its budget indefinitely.
TIMEOUT_MARGIN_S = 720
DEFAULT_BUDGET_S = 17400

# Per-date supervision (see "SUPERVISED DATE-LEVEL EXECUTION" above). The
# runner self-bounds pathological dates (25 consecutive fetch failures ->
# exit 3) and its worst documented in-flight cell is 260s, so the defaults are
# generous rather than aggressive: a full 79-ticker date is typically a few
# minutes; the wall clock allows an hour; the no-progress bound (15 minutes
# without a single newly-complete cell, where "complete" is the runner's own
# predicate) is what actually catches a child that stays alive but does
# nothing.
DEFAULT_DATE_TIMEOUT_S = 3600
DEFAULT_NO_PROGRESS_TIMEOUT_S = 900
PROGRESS_POLL_S = 15   # how often DB progress is re-checked during a date
KILL_GRACE_S = 15      # SIGTERM -> SIGKILL grace for a wedged child

MISSION_CATEGORY = "IDX80"
CONFIRM_FLAG = "--yes-run-vendor-backfill"
OVERRIDE_FLAG = "--allow-non-idx80"

EXIT_COMPLETE = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2
EXIT_BLOCKED = 3

STATUS_EXIT = {"COMPLETE": EXIT_COMPLETE, "PARTIAL": EXIT_PARTIAL,
               "FAILED": EXIT_FAILED, "BLOCKED": EXIT_BLOCKED}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The runner must only ever add or replace a keyed row. Anything that can erase
# or blank existing history is a stop condition, not something to work around.
_DESTRUCTIVE_SQL = re.compile(
    r"\b(DELETE\s+FROM|DROP\s+TABLE|DROP\s+INDEX|TRUNCATE|"
    r"UPDATE\s+stockbit_flow)\b", re.IGNORECASE)


# --- process / lock coordination --------------------------------------------


def other_backfill_pids(marker: str = "backfill_flow_bars.py") -> list:
    """PIDs of any OTHER live process running the production runner.

    There is no PID/lockfile mechanism in this repo for the backfill (the
    operations design lists it as required start-condition S2 but it was never
    built), so this scans /proc directly rather than inventing durable state.
    The only lock precedent here is auto_token.py::_refresh_lock, whose
    fcntl.LOCK_EX|LOCK_NB pattern AgentLock below reuses.
    """
    me = os.getpid()
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for name in entries:
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == me:
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as f:
                cmd = f.read().decode("utf-8", "replace")
        except OSError:
            continue
        if marker in cmd:
            found.append(pid)
    return found


class AgentLock:
    """Non-blocking exclusive lock, held for the duration of an execution.

    Advisory only -- it coordinates agent invocations with each other. It does
    NOT constrain a bare `python tools/backfill_flow_bars.py` launched by hand;
    other_backfill_pids() covers that case.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._fh = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "w")
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


# --- read-only data access ---------------------------------------------------


def connect_ro(db_path) -> sqlite3.Connection:
    """Read-only handle. Structural guarantee that this tool cannot write."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def resolve_universe(cat: str) -> list:
    """Category name, or the runner's legacy comma-separated ticker list.

    ALL mirrors stockbit_fetcher.get_tickers's fallback exactly: on any
    failure (or an empty result), fall back to IDX80 rather than raising. A
    plan/audit that raises where the runner it audits would silently proceed
    on the fallback is worse than useless -- it disagrees with reality.
    """
    if "," in cat:
        return [t.strip().upper() for t in cat.split(",") if t.strip()]
    from data.fetcher import CATEGORIES, load_all_tickers
    up = cat.upper()
    if up == "ALL":
        try:
            tickers = load_all_tickers()
            if tickers:
                return tickers
        except Exception:
            pass
        return CATEGORIES["IDX80"]
    if up not in CATEGORIES:
        raise ValueError(f"Unknown category '{cat}'. Use: IDX30, LQ45, IDX80, ALL")
    return list(dict.fromkeys(CATEGORIES[up]))


def calendar_rows(conn, date_from: str, date_to: str) -> list:
    """(date, source) of every trading_calendar row in [date_from, date_to).

    Raw membership, both writers included -- date_to EXCLUSIVE. Use
    `expected_dates()` for the sessions this agent actually demands bars for.
    """
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT date, source FROM trading_calendar "
        "WHERE date >= ? AND date < ? ORDER BY date",
        (date_from, date_to))]


def ihsg_dates(conn, date_from: str, date_to: str) -> set:
    """Dates with an IHSG `ohlcv` bar -- the canonical IDX session authority.

    This is exactly the set data/market_schema.py::build_trading_calendar
    derives `trading_calendar` from; reading it directly is what lets this
    read-only tool tell a canonical row from a scraper_eod-only one without
    maintaining a holiday list or trusting the (first-writer-wins) source column.
    """
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv "
        "WHERE ticker = 'IHSG' AND date >= ? AND date < ?",
        (date_from, date_to))}


def expected_dates(rows: list, ihsg: set) -> tuple:
    """Split calendar rows into (confirmed sessions, unconfirmed rows).

    Confirmed = a trading_calendar row AND an IHSG bar. Unconfirmed rows are
    returned so they can be reported rather than silently dropped.
    """
    confirmed = [d for d, _ in rows if d in ihsg]
    unconfirmed = [{"date": d, "source": s} for d, s in rows if d not in ihsg]
    return confirmed, unconfirmed


def ohlcv_dates(conn, date_from: str, date_to: str) -> list:
    """The dates the RUNNER will actually iterate (its own work-list source)."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv WHERE date >= ? AND date < ? ORDER BY date",
        (date_from, date_to))]


@dataclass
class Coverage:
    expected: int = 0
    present: int = 0
    complete: int = 0
    present_by_date: dict = field(default_factory=dict)
    complete_by_date: dict = field(default_factory=dict)
    dates_zero: list = field(default_factory=list)
    dates_partial: list = field(default_factory=list)
    dates_full: list = field(default_factory=list)

    @property
    def missing(self) -> int:
        return self.expected - self.complete

    def as_dict(self) -> dict:
        pct = (100.0 * self.complete / self.expected) if self.expected else 0.0
        bars_pct = (100.0 * self.present / self.expected) if self.expected else 0.0
        return {
            "expected_ticker_days": self.expected,
            "present_ticker_days": self.present,
            "complete_ticker_days": self.complete,
            "missing_ticker_days": self.missing,
            "coverage_pct": round(pct, 4),
            "bars_coverage_pct": round(bars_pct, 4),
            "dates_total": len(self.dates_zero) + len(self.dates_partial) + len(self.dates_full),
            "dates_zero": self.dates_zero,
            "dates_zero_count": len(self.dates_zero),
            "dates_partial": self.dates_partial,
            "dates_partial_count": len(self.dates_partial),
            "dates_full": self.dates_full,
            "dates_full_count": len(self.dates_full),
        }


def _cells(conn, sql: str, tickers: list, lo: str, hi: str) -> dict:
    out = {}
    marks = ",".join("?" * len(tickers))
    for d, t in conn.execute(sql.format(marks=marks), (lo, hi, *tickers)):
        out.setdefault(d, set()).add(t)
    return out


_BARS_SQL = """
    SELECT DISTINCT trade_date, ticker FROM stockbit_flow_bars
    WHERE trade_date >= ? AND trade_date <= ? AND ticker IN ({marks})
"""

# Set-based twin of tools/flow_bars_gap.py::bars_cell_complete's empty-session
# clause. COALESCE so a NULL column never reads as "activity". Agreement with
# the per-cell predicate is asserted by test_set_based_coverage_agrees_with_
# the_fetchers_own_predicate, so this cannot drift from the runner.
_EMPTY_SQL = """
    SELECT DISTINCT trade_date, ticker FROM stockbit_flow
    WHERE trade_date >= ? AND trade_date <= ? AND ticker IN ({marks})
      AND COALESCE(buy_lot, 0)  = 0
      AND COALESCE(sell_lot, 0) = 0
      AND COALESCE(buy_freq, 0) = 0
      AND COALESCE(sell_freq, 0) = 0
"""


def compute_coverage(conn, tickers: list, dates: list) -> Coverage:
    """Ticker-day coverage of `tickers` x `dates`. Never uses row counts."""
    cov = Coverage()
    if not tickers or not dates:
        return cov
    universe = set(tickers)
    lo, hi = min(dates), max(dates)
    bars = _cells(conn, _BARS_SQL, tickers, lo, hi)
    empty = _cells(conn, _EMPTY_SQL, tickers, lo, hi)

    per_date = len(universe)
    cov.expected = per_date * len(dates)
    for d in dates:
        present = bars.get(d, set()) & universe
        complete = present | (empty.get(d, set()) & universe)
        cov.present_by_date[d] = present
        cov.complete_by_date[d] = complete
        cov.present += len(present)
        cov.complete += len(complete)
        if not complete:
            cov.dates_zero.append(d)
        elif len(complete) == per_date:
            cov.dates_full.append(d)
        else:
            cov.dates_partial.append({
                "date": d, "complete": len(complete), "with_bars": len(present),
                "expected": per_date, "missing": per_date - len(complete),
            })
    return cov


# --- runner inspection & invocation -----------------------------------------


def scan_runner_for_destructive_sql(path) -> list:
    """Requirement G: if the runner itself could destroy existing data, STOP.

    The runner today writes only `INSERT OR REPLACE` against primary keys
    (ticker, trade_date, bar_time) / (ticker, trade_date), so a re-fetch can
    replace a keyed row but can never delete, truncate or blank-fill history.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"unreadable: {e}"]
    return [m.group(0) for m in _DESTRUCTIVE_SQL.finditer(text)]


_RUNNER_DB = re.compile(
    r"^DB_PATH\s*=\s*HERE\s*/\s*\"([^\"]+)\"\s*/\s*\"([^\"]+)\"", re.MULTILINE)


def runner_db_path(runner) -> Optional[Path]:
    """The SQLite file the runner actually writes.

    The runner hardcodes `DB_PATH = HERE / "data" / "walkforward.db"` and takes
    no --db flag. This agent's --db steers only its own audit, so the two can
    disagree — and a coverage verdict measured against a different file than the
    one that was written is worthless. Parsed rather than imported so this
    read-only tool does not pull in the vendor client.
    """
    try:
        m = _RUNNER_DB.search(Path(runner).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return HERE / m.group(1) / m.group(2) if m else None


@dataclass
class RunResult:
    returncode: Optional[int]
    duration_s: float
    timed_out: bool


@dataclass
class ChildResult:
    """Outcome of one supervised single-date runner invocation."""
    returncode: Optional[int]
    duration_s: float
    timed_out: bool
    stalled: bool


def next_day(d: str) -> str:
    """The exclusive upper bound of a single-date window [d, d+1day)."""
    return (_date.fromisoformat(d) + timedelta(days=1)).isoformat()


def complete_cells(conn, tickers: list, d: str) -> int:
    """Complete (ticker, d) cells per the runner's own completion predicate.

    This is the supervisor's progress signal: the runner commits per cell, so
    a strictly increasing count is direct evidence the backfill is advancing,
    while a child that stays alive without one is a stall.
    """
    return compute_coverage(conn, tickers, [d]).complete


def _terminate(proc) -> None:
    """Stop a wedged child safely: SIGTERM, then SIGKILL after KILL_GRACE_S."""
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=KILL_GRACE_S)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        proc.wait()


def run_date_child(cmd: list, conn, tickers: list, date: str, *,
                   date_timeout_s: int, no_progress_s: int, poll_s: int,
                   spawn=subprocess.Popen) -> ChildResult:
    """Run the production runner for EXACTLY ONE trading date, supervised.

    The wall-clock timeout and the no-progress timeout are enforced from this
    side because the runner's exit code cannot signal a wedge (exit 0 also
    means "planned budget stop"). Progress is defined as newly-complete
    (ticker, date) cells in the DB. A wedged child is terminated (SIGTERM,
    then SIGKILL) and reported timed_out/stalled; the caller records the date
    FAILED/STALLED and continues. `spawn` is a seam for tests; the default is
    the real Popen with inherited stdout.
    """
    t0 = time.monotonic()
    last_complete = complete_cells(conn, tickers, date)
    last_progress = t0
    proc = spawn(cmd, cwd=str(HERE))
    try:
        while True:
            rc = proc.poll()
            if rc is not None:
                return ChildResult(rc, time.monotonic() - t0, False, False)
            now = time.monotonic()
            if now - t0 > date_timeout_s:
                _terminate(proc)
                return ChildResult(None, time.monotonic() - t0, True, False)
            if now - last_progress > no_progress_s:
                _terminate(proc)
                return ChildResult(None, time.monotonic() - t0, False, True)
            time.sleep(poll_s)
            complete = complete_cells(conn, tickers, date)
            if complete > last_complete:
                last_complete = complete
                last_progress = time.monotonic()
    finally:
        # Safety net: never leak a live child, including on unexpected errors.
        if proc.poll() is None:
            _terminate(proc)


def run_backfill(cmd: list, timeout: int) -> RunResult:
    """Launch the production runner as one whole-window invocation (probe only).

    Execute mode does NOT use this: it runs the runner once per trading date
    through run_date_child, which adds wall-clock and no-progress supervision.
    """
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(HERE), timeout=timeout)
        return RunResult(proc.returncode, time.time() - t0, False)
    except subprocess.TimeoutExpired:
        return RunResult(None, time.time() - t0, True)


def default_python() -> str:
    venv = HERE / "venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


def build_command(python: str, runner, cat: str, date_from: str, date_to: str,
                  budget_s: int, probe: bool) -> list:
    """The exact production invocation. `--release-fixture` is never emitted:
    the frozen 2025-04-14 discrimination fixture is reserved for the Day-1
    sign-off test and this agent has no authority to consume it."""
    cmd = [python, str(runner), "--cat", cat,
           "--date-from", date_from, "--date-to", date_to,
           "--budget-s", str(budget_s)]
    if probe:
        cmd.append("--probe")
    return cmd


def supervise_dates(db_path, tickers: list, dates: list, python: str,
                    runner, cat: str, budget_s: int,
                    date_timeout_s: int, no_progress_s: int,
                    poll_s: int) -> tuple:
    """Execute the backfill ONE TRADING DATE AT A TIME.

    Returns (outcomes, launched, aborted). Resume is derived from the DB: a
    date whose cells are already complete is skipped without launching
    anything. Every incomplete date is handed to the runner as
    [date, date+1day) and verified afterwards -- a date only becomes SUCCESS
    when its cells are actually complete. FAILED/STALLED dates are recorded
    and never stop the loop (failure isolation). The frozen fixture date is
    never launched.

    `aborted` is None, or a reason string when a hand-launched second writer
    was detected mid-run: the concurrency guard is re-checked before EVERY
    date launch, not just once before this loop starts, because a run can
    span hours and a bare `python tools/backfill_flow_bars.py` can appear at
    any point during it.
    """
    processable = [d for d in dates if d not in FROZEN_FIXTURE_DATES]
    outcomes = []
    launched = 0
    for i, d in enumerate(processable, 1):
        conn = connect_ro(db_path)
        try:
            before = compute_coverage(conn, tickers, [d])
        finally:
            conn.close()
        if before.complete >= before.expected:
            outcomes.append({
                "date": d, "outcome": "SKIPPED",
                "reason": "already complete per the coverage predicate",
                "returncode": None, "duration_s": 0.0,
                "timed_out": False, "stalled": False,
                "complete_cells": before.complete,
                "expected_cells": before.expected, "command": None,
            })
            continue
        pids = other_backfill_pids()
        if pids:
            aborted = (f"backfill process appeared mid-run before {d} "
                      f"(pid {pids}) — aborting remaining dates, nothing "
                      f"launched for {d}")
            print(f"[supervisor {i}/{len(processable)} {d}] ABORTED: {aborted}",
                  file=sys.stderr, flush=True)
            return outcomes, launched, aborted
        cmd = build_command(python, runner, cat, d, next_day(d), budget_s,
                            probe=False)
        launched += 1
        spawn_error = None
        conn = connect_ro(db_path)
        try:
            try:
                res = run_date_child(cmd, conn, tickers, d,
                                     date_timeout_s=date_timeout_s,
                                     no_progress_s=no_progress_s,
                                     poll_s=poll_s)
            except Exception as e:  # per-date isolation: never stop the loop
                res = ChildResult(None, 0.0, False, False)
                spawn_error = str(e)
        finally:
            conn.close()
        conn = connect_ro(db_path)
        try:
            after = compute_coverage(conn, tickers, [d])
        finally:
            conn.close()
        if spawn_error:
            outcome, reason = "FAILED", f"could not launch child: {spawn_error}"
        elif res.timed_out:
            outcome, reason = "FAILED", \
                f"child exceeded --date-timeout-s {date_timeout_s}s"
        elif res.stalled:
            outcome, reason = "STALLED", \
                f"no new complete cell for --no-progress-timeout-s " \
                f"{no_progress_s}s"
        elif res.returncode != 0:
            outcome, reason = "FAILED", f"child exited {res.returncode}"
        elif after.complete < after.expected:
            outcome, reason = "FAILED", \
                f"child exited 0 but {after.expected - after.complete} " \
                f"cell(s) remain incomplete"
        else:
            outcome, reason = "SUCCESS", None
        outcomes.append({
            "date": d, "outcome": outcome, "reason": reason,
            "returncode": res.returncode,
            "duration_s": round(res.duration_s, 2),
            "timed_out": res.timed_out, "stalled": res.stalled,
            "complete_cells": after.complete,
            "expected_cells": after.expected,
            "command": cmd,
        })
        print(f"[supervisor {i}/{len(processable)} {d}] {outcome}"
              f"{' rc=' + str(res.returncode) if res.returncode is not None else ''}"
              f" {after.complete}/{after.expected} cells"
              f" {res.duration_s:.1f}s", file=sys.stderr, flush=True)
    return outcomes, launched, None


def _recompute_coverage(db_path, tickers: list, dates: list):
    """Fresh read-only coverage pass after execution. The runner commits per
    cell, so a brand-new connection sees the just-written state."""
    conn = connect_ro(db_path)
    try:
        return compute_coverage(conn, tickers, dates)
    finally:
        conn.close()


# --- CLI ---------------------------------------------------------------------


def _valid_date(s: str) -> bool:
    if not _ISO_DATE.match(s or ""):
        return False
    try:
        _date.fromisoformat(s)
    except ValueError:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="agent_backfill_idx80.py",
        description="IDX80 stockbit_flow_bars backfill orchestrator "
                    "(plans and audits tools/backfill_flow_bars.py; never fetches itself)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 COMPLETE, 1 PARTIAL, 2 FAILED, 3 BLOCKED.\n"
               "Default action is `plan`: read-only, no vendor calls, no writes.",
    )
    ap.add_argument("--action", choices=("plan", "probe", "execute"), default="plan",
                    help="plan (default, read-only) | probe (bounded vendor "
                         "diagnostic) | execute (real backfill)")
    ap.add_argument("--date-from", required=True, help="inclusive lower bound, YYYY-MM-DD")
    ap.add_argument("--date-to", required=True,
                    help="EXCLUSIVE upper bound, YYYY-MM-DD (a date equal to "
                         "--date-from covers nothing)")
    ap.add_argument("--cat", default=MISSION_CATEGORY,
                    help=f"ticker category (default {MISSION_CATEGORY}; anything "
                         f"else requires {OVERRIDE_FLAG})")
    ap.add_argument(OVERRIDE_FLAG, action="store_true",
                    help="documented override: operate on a non-IDX80 category. "
                         "This agent's mission is IDX80; use only when a named "
                         "task explicitly calls for another universe.")
    ap.add_argument("--budget-s", type=int, default=DEFAULT_BUDGET_S,
                    help=f"wall-clock budget passed to the runner "
                         f"(1..{HARD_CAP_S}; default {DEFAULT_BUDGET_S})")
    ap.add_argument("--date-timeout-s", type=int, default=DEFAULT_DATE_TIMEOUT_S,
                    help=f"per-date child wall-clock timeout in seconds "
                         f"(default {DEFAULT_DATE_TIMEOUT_S}). Execution runs "
                         f"the runner once per trading date; a child exceeding "
                         f"this is terminated and the date recorded FAILED.")
    ap.add_argument("--no-progress-timeout-s", type=int,
                    default=DEFAULT_NO_PROGRESS_TIMEOUT_S,
                    help=f"seconds without a single newly-complete cell before "
                         f"the child is terminated and the date recorded "
                         f"STALLED (default {DEFAULT_NO_PROGRESS_TIMEOUT_S})")
    ap.add_argument(CONFIRM_FLAG, action="store_true",
                    help="REQUIRED for --action execute/probe. Without it, "
                         "execution is refused. This is the only way to make "
                         "vendor calls happen.")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB to audit (read-only)")
    ap.add_argument("--runner", default=str(DEFAULT_RUNNER),
                    help="production backfill implementation to orchestrate")
    ap.add_argument("--lock-file", default=str(DEFAULT_LOCK))
    ap.add_argument("--python", default=None, help="interpreter for the runner subprocess")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON only")
    return ap


def _check(checks, name, ok, detail, blocking=True):
    checks.append({"name": name, "ok": bool(ok), "blocking": blocking, "detail": detail})
    return ok


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    confirmed = getattr(args, CONFIRM_FLAG.lstrip("-").replace("-", "_"))
    override = getattr(args, OVERRIDE_FLAG.lstrip("-").replace("-", "_"))

    checks, reasons, notes = [], [], []
    report = {
        "action": args.action,
        "status": "BLOCKED",
        "category": args.cat,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "date_to_exclusive": True,
        "budget_s": args.budget_s,
        "db": args.db,
        "runner": args.runner,
        "universe_size": None,
        "calendar": None,
        "fixture_barrier": None,
        "coverage_before": None,
        "coverage_after": None,
        "proposed_command": [],
        "subprocess": None,
        "execution": None,
        "dates": None,
        "date_summary": None,
        "fixture_dates_excluded": [],
        "vendor_calls_made": False,
        "safety_checks": checks,
        "execution_allowed": False,
        "reasons": reasons,
        "notes": notes,
    }

    # --- checks that need no database ---------------------------------------
    if not _check(checks, "category_is_idx80",
                  args.cat.upper() == MISSION_CATEGORY or override,
                  f"category={args.cat}; this agent's mission is {MISSION_CATEGORY}"):
        reasons.append(f"category '{args.cat}' is not {MISSION_CATEGORY}; "
                       f"pass {OVERRIDE_FLAG} to operate on another universe")
    if args.cat.upper() != MISSION_CATEGORY and override:
        notes.append(f"NON-IDX80 OVERRIDE in force: operating on '{args.cat}'")

    dates_ok = (_valid_date(args.date_from) and _valid_date(args.date_to)
                and args.date_from < args.date_to)
    if not _check(checks, "date_range_valid", dates_ok,
                  f"[{args.date_from}, {args.date_to}) — --date-to is EXCLUSIVE"):
        reasons.append(f"invalid date range [{args.date_from}, {args.date_to}): "
                       f"both must be YYYY-MM-DD and --date-from must be strictly "
                       f"before the exclusive --date-to")

    budget_ok = 0 < args.budget_s <= HARD_CAP_S
    if not _check(checks, "budget_valid", budget_ok,
                  f"budget_s={args.budget_s} (runner clamps to {HARD_CAP_S})"):
        reasons.append(f"--budget-s must be 1..{HARD_CAP_S}; the runner clamps "
                       f"anything larger to {HARD_CAP_S}, so a larger value would "
                       f"silently mean something other than what was asked")

    timeout_ok = (args.date_timeout_s > 0 and args.no_progress_timeout_s > 0
                  and args.no_progress_timeout_s <= args.date_timeout_s)
    if not _check(checks, "timeout_params_valid", timeout_ok,
                  f"date_timeout_s={args.date_timeout_s}, "
                  f"no_progress_timeout_s={args.no_progress_timeout_s}"):
        reasons.append(f"--date-timeout-s and --no-progress-timeout-s must be "
                       f"positive and the no-progress bound must not exceed "
                       f"the wall clock (got date_timeout_s="
                       f"{args.date_timeout_s}, no_progress_timeout_s="
                       f"{args.no_progress_timeout_s})")

    destructive = scan_runner_for_destructive_sql(args.runner)
    if not _check(checks, "runner_non_destructive", not destructive,
                  f"destructive SQL found: {destructive}" if destructive
                  else "runner only INSERTs OR REPLACEs keyed rows"):
        reasons.append(f"runner {args.runner} contains destructive SQL "
                       f"{destructive} — STOPPING rather than orchestrating a tool "
                       f"that can erase existing data")

    pids = other_backfill_pids()
    if not _check(checks, "no_concurrent_backfill", not pids,
                  f"other backfill processes: {pids}" if pids else "none running"):
        reasons.append(f"another backfill process is running (pid {pids}) — "
                       f"refusing to add a second writer to this SQLite file")

    # --- database-dependent checks ------------------------------------------
    conn = None
    db_ok = Path(args.db).exists()
    if db_ok:
        try:
            conn = connect_ro(args.db)
        except sqlite3.Error as e:
            db_ok = False
            reasons.append(f"cannot open {args.db} read-only: {e}")
    else:
        reasons.append(f"database not found: {args.db}")
    _check(checks, "db_readable", db_ok, args.db)

    tickers = []
    dates = []
    if conn is not None and dates_ok:
        try:
            tickers = resolve_universe(args.cat)
        except Exception as e:
            reasons.append(f"cannot resolve universe for '{args.cat}': {e}")
        report["universe_size"] = len(tickers)
        _check(checks, "universe_non_empty", bool(tickers), f"{len(tickers)} tickers")
        if not tickers:
            reasons.append(f"universe for '{args.cat}' is empty")

        rows = calendar_rows(conn, args.date_from, args.date_to)
        ihsg = ihsg_dates(conn, args.date_from, args.date_to)
        dates, non_ihsg = expected_dates(rows, ihsg)
        runner_dates = ohlcv_dates(conn, args.date_from, args.date_to)
        unreachable = sorted({d for d, _ in rows} - set(runner_dates))
        report["calendar"] = {
            "expected_source": "trading_calendar AND an IHSG ohlcv bar "
                               "(data/market_schema.py::build_trading_calendar)",
            "runner_work_source": "ohlcv (tools/backfill_flow_bars.py::gap_dates)",
            "calendar_rows_in_window": len(rows),
            "dates_in_window": len(dates),
            "runner_dates_in_window": len(runner_dates),
            "non_ihsg_dates": non_ihsg,
            "non_ihsg_dates_count": len(non_ihsg),
            "unreachable_dates": unreachable,
            "sources_agree": not unreachable,
        }
        if not _check(checks, "calendar_has_trading_dates", bool(dates),
                      f"{len(dates)} IHSG-confirmed trading dates in window "
                      f"({len(rows)} calendar row(s))"):
            reasons.append(f"no IHSG-confirmed trading dates in [{args.date_from}, "
                           f"{args.date_to}) — {len(rows)} trading_calendar row(s) in "
                           f"the window, none of them backed by an IHSG ohlcv bar. "
                           f"Nothing to plan")
        if non_ihsg:
            notes.append(
                f"{len(non_ihsg)} trading_calendar row(s) in this window have NO "
                f"IHSG ohlcv bar and are therefore NOT counted as expected IDX80 "
                f"sessions: {[x['date'] for x in non_ihsg[:5]]}"
                f"{'...' if len(non_ihsg) > 5 else ''} "
                f"(sources: {sorted({x['source'] for x in non_ihsg})}). "
                f"trading_calendar has two independent writers — IHSG-derived "
                f"(canonical) and screener/idx_scraper.py's scraper_eod EOD "
                f"upsert — and only the canonical one defines an IDX session. "
                f"Nothing was mutated; this tool is read-only.")
        if unreachable:
            notes.append(f"{len(unreachable)} trading_calendar date(s) are absent "
                         f"from ohlcv and therefore UNREACHABLE by the runner: "
                         f"{unreachable[:5]}{'...' if len(unreachable) > 5 else ''}")

        # Frozen fixture: barrier inside a wider window, refusal when targeted.
        in_window = [d for d in FROZEN_FIXTURE_DATES
                     if args.date_from <= d < args.date_to]
        targeted = bool(in_window) and set(dates) == set(in_window)
        if not _check(checks, "frozen_fixture_not_targeted", not targeted,
                      f"fixture dates in window: {in_window}"):
            reasons.append(f"this window's entire work list is the frozen Day-1 "
                           f"discrimination fixture {in_window}; the runner would "
                           f"refuse it (exit 5) and this agent never passes "
                           f"--release-fixture")
        elif in_window:
            # The runner does not skip the fixture date -- it `break`s out of the
            # whole date loop (tools/backfill_flow_bars.py). So EVERY date after
            # the barrier is unreachable in one invocation, not just the fixture.
            barrier = min(in_window)
            after = [d for d in dates if d > barrier]
            nxt = (_date.fromisoformat(barrier) + timedelta(days=1)).isoformat()
            report["fixture_barrier"] = {
                "barrier_date": barrier,
                "dates_after_barrier": len(after),
                "split_windows": [[args.date_from, barrier], [nxt, args.date_to]],
            }
            notes.append(
                f"frozen fixture {barrier} lies inside this window. The runner "
                f"BREAKS its date loop at that barrier (exit 0), so the {len(after)} date(s) "
                f"after it are unreachable in one invocation — COMPLETE is "
                f"impossible for this window. Run it as two windows instead: "
                f"[{args.date_from}, {barrier}) then [{nxt}, {args.date_to}). "
                f"The fixture itself stays reserved for the Day-1 sign-off test.")

        if tickers and dates:
            report["coverage_before"] = compute_coverage(conn, tickers, dates).as_dict()

    # The runner has no --db flag: it writes wherever its own DB_PATH points.
    # Blocking for a real run (the post-run verdict would measure the wrong
    # file); only a note when planning, where auditing another DB is legitimate.
    target = runner_db_path(args.runner)
    same_db = target is not None and Path(args.db).resolve() == target.resolve()
    if not same_db:
        detail = (f"agent audits {args.db}; runner writes "
                  f"{target if target else 'UNKNOWN (could not parse DB_PATH)'}")
        _check(checks, "audit_db_is_the_runner_target", False, detail,
               blocking=(args.action in ("probe", "execute")))
        (reasons if args.action in ("probe", "execute") else notes).append(
            f"the runner writes to a different database than this agent audits "
            f"— {detail}. A coverage verdict would not describe what was written.")
    else:
        _check(checks, "audit_db_is_the_runner_target", True, str(target))

    python = args.python or default_python()
    if dates_ok and budget_ok:
        report["proposed_command"] = build_command(
            python, args.runner, args.cat, args.date_from, args.date_to,
            args.budget_s, probe=(args.action == "probe"))

    blocking_failed = [c["name"] for c in checks if c["blocking"] and not c["ok"]]
    report["execution_allowed"] = not blocking_failed

    # --- explicit-confirmation gate -----------------------------------------
    wants_vendor = args.action in ("probe", "execute")
    if wants_vendor and not confirmed:
        _check(checks, "execution_confirmed", False,
               f"{CONFIRM_FLAG} not supplied")
        reasons.append(f"--action {args.action} makes real Stockbit calls; it "
                       f"requires the explicit {CONFIRM_FLAG} confirmation flag. "
                       f"Refusing — a plan never becomes a run implicitly.")
        blocking_failed.append("execution_confirmed")
    elif wants_vendor:
        _check(checks, "execution_confirmed", True, f"{CONFIRM_FLAG} supplied")

    # --- decide & (only then) act -------------------------------------------
    if blocking_failed:
        report["status"] = "BLOCKED"
    elif not wants_vendor:
        cov = report["coverage_before"]
        report["status"] = "COMPLETE" if cov and cov["missing_ticker_days"] == 0 else "PARTIAL"
    else:
        lock = AgentLock(args.lock_file)
        if not lock.acquire():
            reasons.append(f"another agent invocation holds the lock "
                           f"{args.lock_file} — refusing to run concurrently")
            _check(checks, "agent_lock_acquired", False, str(args.lock_file))
            report["execution_allowed"] = False
            report["status"] = "BLOCKED"
        else:
            _check(checks, "agent_lock_acquired", True, str(args.lock_file))
            try:
                # Re-check immediately before spawning: the /proc scan above is a
                # snapshot, and a hand-launched runner can appear in between.
                late = other_backfill_pids()
                if late:
                    reasons.append(f"backfill process appeared before launch "
                                   f"(pid {late}) — aborting, nothing executed")
                    report["execution_allowed"] = False
                    report["status"] = "BLOCKED"
                else:
                    report["vendor_calls_made"] = True
                    if args.action == "probe":
                        notes.append("PROBE is an endpoint diagnostic only: a "
                                     "successful probe is NOT evidence of historical "
                                     "coverage. Read coverage_after for that.")
                        res = run_backfill(report["proposed_command"],
                                           timeout=args.budget_s + TIMEOUT_MARGIN_S)
                        report["subprocess"] = {
                            "returncode": res.returncode,
                            "duration_s": round(res.duration_s, 2),
                            "timed_out": res.timed_out,
                            "timeout_s": args.budget_s + TIMEOUT_MARGIN_S,
                        }
                        # Re-derive coverage from the DB. The runner returns 0
                        # for a planned budget stop with work remaining, so its
                        # exit code can never be the completion signal.
                        after = _recompute_coverage(args.db, tickers, dates)
                        report["coverage_after"] = after.as_dict() if after else None
                        if res.timed_out or res.returncode != 0:
                            report["status"] = "FAILED"
                            reasons.append(
                                "runner timed out" if res.timed_out
                                else f"runner exited {res.returncode} "
                                     f"(2=auth, 3=sustained fetch failure, 4=db, "
                                     f"5=frozen fixture)")
                        elif after is not None and after.missing == 0:
                            report["status"] = "COMPLETE"
                        else:
                            report["status"] = "PARTIAL"
                            remaining = after.missing if after is not None else "unknown"
                            reasons.append(
                                f"runner exited 0 but {remaining} ticker-day "
                                f"cell(s) remain uncovered — exit code 0 also "
                                f"means 'planned budget stop, work remains'. "
                                f"NOT COMPLETE.")
                    else:  # execute: supervised, one trading date per child
                        report["execution"] = {
                            "model": "per_date",
                            "date_timeout_s": args.date_timeout_s,
                            "no_progress_timeout_s": args.no_progress_timeout_s,
                            "progress_poll_s": PROGRESS_POLL_S,
                        }
                        excluded = [d for d in dates
                                    if d in FROZEN_FIXTURE_DATES]
                        report["fixture_dates_excluded"] = excluded
                        if excluded:
                            notes.append(
                                f"frozen fixture date(s) {excluded} lie inside "
                                f"the window and are EXCLUDED from per-date "
                                f"execution — a child is never launched for the "
                                f"fixture itself. Its cells stay reserved for "
                                f"the Day-1 sign-off test, so this window can "
                                f"never be COMPLETE through this agent.")
                        outcomes, launches, aborted = supervise_dates(
                            args.db, tickers, dates, python, args.runner,
                            args.cat, args.budget_s,
                            args.date_timeout_s, args.no_progress_timeout_s,
                            PROGRESS_POLL_S)
                        report["vendor_calls_made"] = launches > 0
                        report["dates"] = outcomes
                        report["date_summary"] = {
                            "total": len(outcomes),
                            "success": sum(1 for o in outcomes
                                           if o["outcome"] == "SUCCESS"),
                            "skipped": sum(1 for o in outcomes
                                           if o["outcome"] == "SKIPPED"),
                            "failed": sum(1 for o in outcomes
                                          if o["outcome"] == "FAILED"),
                            "stalled": sum(1 for o in outcomes
                                           if o["outcome"] == "STALLED"),
                            "launched": launches,
                        }
                        first = next((o for o in outcomes if o["command"]), None)
                        if first is not None:
                            report["proposed_command"] = first["command"]
                        report["subprocess"] = {
                            "launches": launches,
                            "duration_s": round(
                                sum(o["duration_s"] for o in outcomes), 2),
                            "timed_out": any(o["timed_out"] for o in outcomes),
                            "stalled": any(o["stalled"] for o in outcomes),
                        }
                        after = _recompute_coverage(args.db, tickers, dates)
                        report["coverage_after"] = after.as_dict() if after else None
                        hard = [o for o in outcomes
                                if o["outcome"] in ("FAILED", "STALLED")]
                        if aborted:
                            report["status"] = "BLOCKED"
                            report["execution_allowed"] = False
                            reasons.append(aborted)
                        elif hard:
                            report["status"] = "FAILED"
                            reasons.append(
                                f"{len(hard)} date(s) did not complete: "
                                f"{[o['date'] for o in hard][:10]}"
                                f"{'...' if len(hard) > 10 else ''} — "
                                f"the run must not claim COMPLETE while expected "
                                f"dates remain unresolved")
                            for o in hard:
                                reasons.append(
                                    f"date {o['date']}: {o['outcome']}"
                                    f" — {o['reason']}")
                        elif after is not None and after.missing == 0:
                            report["status"] = "COMPLETE"
                        else:
                            report["status"] = "PARTIAL"
                            remaining = after.missing if after is not None else "unknown"
                            reasons.append(
                                f"{remaining} ticker-day cell(s) remain "
                                f"uncovered (e.g. the frozen fixture) — "
                                f"NOT COMPLETE.")
            finally:
                lock.release()

    if conn is not None:
        conn.close()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print_report(report)
    return STATUS_EXIT[report["status"]]


def print_report(r: dict) -> None:
    print("=== IDX80 stockbit_flow_bars backfill agent ===")
    print(f"Action:     {r['action']}   Status: {r['status']}")
    print(f"Category:   {r['category']} ({r['universe_size']} tickers)")
    print(f"Window:     [{r['date_from']}, {r['date_to']})   "
          f"— --date-to is EXCLUSIVE")
    if r["calendar"]:
        c = r["calendar"]
        print(f"Calendar:   {c['dates_in_window']} IHSG-confirmed trading date(s) "
              f"of {c['calendar_rows_in_window']} trading_calendar row(s); "
              f"runner sees {c['runner_dates_in_window']} from ohlcv")
        if c["non_ihsg_dates"]:
            shown = [f"{x['date']}({x['source']})" for x in c["non_ihsg_dates"][:10]]
            print(f"            ⚠ not IHSG-confirmed, excluded from expected: "
                  f"{shown}{'...' if len(c['non_ihsg_dates']) > 10 else ''}")
        if c["unreachable_dates"]:
            print(f"            ⚠ unreachable by runner: {c['unreachable_dates']}")
    for label, key in (("before", "coverage_before"), ("after", "coverage_after")):
        cov = r.get(key)
        if not cov:
            continue
        print(f"\nCoverage ({label}):")
        print(f"  expected ticker-days : {cov['expected_ticker_days']}")
        print(f"  with bars            : {cov['present_ticker_days']} "
              f"({cov['bars_coverage_pct']}%)")
        print(f"  complete (predicate) : {cov['complete_ticker_days']} "
              f"({cov['coverage_pct']}%)")
        print(f"  missing              : {cov['missing_ticker_days']}")
        print(f"  dates full/partial/zero: {cov['dates_full_count']}/"
              f"{cov['dates_partial_count']}/{cov['dates_zero_count']}")
        if cov["dates_zero"]:
            z = cov["dates_zero"]
            print(f"  zero-coverage dates  : {z[:10]}{'...' if len(z) > 10 else ''}")
    print("\nSafety checks:")
    for c in r["safety_checks"]:
        mark = "✓" if c["ok"] else ("✗" if c["blocking"] else "~")
        print(f"  {mark} {c['name']}: {c['detail']}")
    print(f"\nExecution allowed: {r['execution_allowed']}")
    print(f"Proposed command:\n  {' '.join(r['proposed_command'])}")
    if r.get("execution"):
        e = r["execution"]
        print(f"\nExecution model: {e['model']} — one trading date per child; "
              f"date-timeout {e['date_timeout_s']}s, no-progress "
              f"{e['no_progress_timeout_s']}s")
    if r.get("dates"):
        print("Per-date outcomes:")
        for o in r["dates"][:12]:
            tail = f" ({o['reason']})" if o["reason"] else ""
            print(f"  [{o['date']}] {o['outcome']}"
                  f"{' rc=' + str(o['returncode']) if o['returncode'] is not None else ''}"
                  f" {o['complete_cells']}/{o['expected_cells']} cells"
                  f" {o['duration_s']}s{tail}")
        if len(r["dates"]) > 12:
            print(f"  ... {len(r['dates']) - 12} more")
    if r["subprocess"]:
        s = r["subprocess"]
        if "returncode" in s:
            print(f"\nRunner: rc={s['returncode']} in {s['duration_s']}s "
                  f"(timed_out={s['timed_out']})")
        else:
            print(f"\nRunner: {s['launches']} date child(ren), "
                  f"{s['duration_s']}s total (timed_out={s['timed_out']}, "
                  f"stalled={s['stalled']})")
    for n in r["notes"]:
        print(f"NOTE: {n}")
    for x in r["reasons"]:
        print(f"REASON: {x}")


if __name__ == "__main__":
    sys.exit(main())
