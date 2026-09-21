#!/usr/bin/env python3
"""IDX80 `broker_flow` backfill ORCHESTRATOR (agent wrapper).

This is NOT a fetcher. It never talks to Stockbit, never writes to any
table, and never reimplements the vendor/write path. It plans, guards, and
audits a run of the production runner
`tools/backfill_broker_flow_idx80.py`, which remains the single
implementation of the HTTP and write logic. Mirrors
`tools/agent_backfill_idx80.py` (the proven IDX80 `stockbit_flow_bars`
orchestrator) — same safety posture, same per-date supervised execution
model — trimmed to what broker_flow actually needs: no frozen fixture, no
`--cat` override (this agent's universe is IDX80, full stop, by
construction — there is no flag that can widen it).

SAFETY POSTURE (fail-closed)
----------------------------
  * Default action is `plan` — read-only, no vendor calls, no writes.
  * The DB handle is opened `mode=ro`; a write raises rather than mutating.
  * Execution requires BOTH `--action execute` (or `probe`) AND the explicit
    `--yes-run-vendor-backfill` confirmation flag.
  * Universe is always the live `idx_tickers WHERE status='active' AND
    in_idx80=1` query — there is no CLI flag to target any other category,
    so "accidentally broader than IDX80" is structurally impossible here,
    not merely checked.
  * A concurrency guard (fcntl lock + /proc scan) blocks a second writer;
    supervised date children run strictly one at a time, and the /proc scan
    is re-checked DURING a date child's poll loop too (not only before it is
    launched) — a hand-launched second writer that appears mid-date is
    caught, not just one that appears between dates.

SUPERVISED DATE-LEVEL EXECUTION
-------------------------------
`--action execute` never launches one multi-date runner for a big window.
Execution runs the runner EXACTLY ONE TRADING DATE AT A TIME:

    discover canonical IHSG-confirmed dates, in order
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

COVERAGE / COMPLETION SEMANTICS
---------------------------------
A cell is (ticker, trade_date). It is COMPLETE when `broker_flow` has rows
for it, OR `bandar_detector` carries the confirmed-empty marker
(`value=0 AND volume=0`) the runner writes after retry exhaustion still
found nothing — see `tools/broker_flow_idx80_gap.py` for the exact
predicate this mirrors set-wise (equality between the two is asserted by
tests, so they cannot drift). A `bandar_detector` row with real nonzero
data but no `broker_flow` rows is deliberately left INCOMPLETE — an
anomalous partial state gets retried, never silently accepted.

CALENDAR SEMANTICS
--------------------
Expected cells are `trading_calendar` x IDX80 — but only for calendar
dates an IHSG `ohlcv` bar actually confirms. `trading_calendar` has two
independent writers (IHSG-derived, canonical; and `scraper_eod`, a side
effect of every finalized EOD save, not itself evidence of a confirmed
session) — see `tools/broker_flow_idx80_gap.py` for the full rationale.
Excluded rows are reported in `calendar.non_ihsg_dates`, never silently
dropped. No holiday list is maintained and no calendar row is ever mutated.

EXIT CODES
----------
  0  COMPLETE  the requested interval is fully covered
  1  PARTIAL   work remains (includes a successful but budget-bounded run)
  2  FAILED    a date child timed out, stalled, exited nonzero, or left
               cells incomplete
  3  BLOCKED   not safe to run / invalid request — nothing was executed

Usage:
  # read-only plan (default)
  venv/bin/python3 tools/agent_backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 --json

  # bounded live diagnostic (BBCA only, first+last date)
  venv/bin/python3 tools/agent_backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 \
      --action probe --yes-run-vendor-backfill

  # explicit, unmistakable execution — one runner per trading date
  venv/bin/python3 tools/agent_backfill_broker_flow_idx80.py \
      --date-from 2025-01-02 --date-to 2026-08-27 \
      --action execute --yes-run-vendor-backfill --budget-s 17400 \
      --date-timeout-s 1800 --no-progress-timeout-s 600
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

from tools.broker_flow_pit_planning import required_members  # noqa: E402

DEFAULT_DB = HERE / "data" / "walkforward.db"
DEFAULT_RUNNER = HERE / "tools" / "backfill_broker_flow_idx80.py"
DEFAULT_LOCK = HERE / "logs" / "agent_backfill_broker_flow_idx80.lock"

# Mirrors tools/backfill_broker_flow_idx80.HARD_CAP_S. Duplicated
# deliberately so this read-only orchestrator does not import the vendor
# client (stockbit_fetcher -> requests) just to validate a flag.
HARD_CAP_S = 5 * 3600
TIMEOUT_MARGIN_S = 720
DEFAULT_BUDGET_S = 17400

# Broker-flow is far lighter than the bars dataset (one HTTP call/ticker/day,
# top-25-per-side cap, no bars parsing) -- a full 79-ticker date is expected
# to take low-single-digit minutes, so these defaults are much smaller than
# the bars orchestrator's (hour-scale) allowance while staying generous.
DEFAULT_DATE_TIMEOUT_S = 1800
DEFAULT_NO_PROGRESS_TIMEOUT_S = 600
PROGRESS_POLL_S = 10
KILL_GRACE_S = 15

CONFIRM_FLAG = "--yes-run-vendor-backfill"

EXIT_COMPLETE = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2
EXIT_BLOCKED = 3

STATUS_EXIT = {"COMPLETE": EXIT_COMPLETE, "PARTIAL": EXIT_PARTIAL,
              "FAILED": EXIT_FAILED, "BLOCKED": EXIT_BLOCKED}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The runner must only ever add or replace a keyed row. Anything that can
# erase or blank existing history is a stop condition, not a workaround.
_DESTRUCTIVE_SQL = re.compile(
    r"\b(DELETE\s+FROM|DROP\s+TABLE|DROP\s+INDEX|TRUNCATE|"
    r"UPDATE\s+broker_flow|UPDATE\s+bandar_detector)\b", re.IGNORECASE)


# --- process / lock coordination --------------------------------------------


def other_backfill_pids(marker: str = "tools/backfill_broker_flow_idx80.py",
                        exclude=frozenset()) -> list:
    """PIDs of any OTHER live process running the production runner.

    Matched WITH the `tools/` prefix, not the bare filename: the bare name
    "backfill_broker_flow_idx80.py" is a substring of this orchestrator's own
    test file ("tests/test_agent_backfill_broker_flow_idx80.py"), so running
    the test suite under pytest — whose own argv includes that test file
    path — made this check self-match and block every plan/execute call.
    The `tools/` prefix only ever appears in a real invocation.

    `exclude` additionally skips given PIDs beyond this process's own — the
    caller passes the PID of a runner child IT deliberately just launched.
    Without this, run_date_child()'s mid-poll recheck (added to catch a
    hand-launched second writer appearing WHILE a date child runs) matched
    the orchestrator's own intentionally-spawned child the moment it became
    visible in /proc, aborting a perfectly normal run as a false-positive
    "concurrent backfill" (2026-08-27 production incident). `os.getpid()`
    alone was never enough: the child is a DIFFERENT process whose own
    cmdline legitimately contains the marker (it *is* the runner).
    """
    me = os.getpid()
    skip = {me} | set(exclude)
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for name in entries:
        if not name.isdigit():
            continue
        pid = int(name)
        if pid in skip:
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

    Advisory only — it coordinates agent invocations with each other.
    other_backfill_pids() covers a bare, hand-launched runner.
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


def idx80_universe(conn) -> list:
    return [r[0] for r in conn.execute(
        "SELECT ticker FROM idx_tickers WHERE status='active' AND in_idx80=1 "
        "ORDER BY ticker"
    )]


def calendar_rows(conn, date_from: str, date_to: str) -> list:
    """(date, source) of every trading_calendar row in [date_from, date_to)."""
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT date, source FROM trading_calendar "
        "WHERE date >= ? AND date < ? ORDER BY date",
        (date_from, date_to))]


def ihsg_dates(conn, date_from: str, date_to: str) -> set:
    """Dates with an IHSG `ohlcv` bar — the canonical IDX session authority."""
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv "
        "WHERE ticker = 'IHSG' AND date >= ? AND date < ?",
        (date_from, date_to))}


def expected_dates(rows: list, ihsg: set) -> tuple:
    """Split calendar rows into (confirmed sessions, unconfirmed rows)."""
    confirmed = [d for d, _ in rows if d in ihsg]
    unconfirmed = [{"date": d, "source": s} for d, s in rows if d not in ihsg]
    return confirmed, unconfirmed


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
        broker_pct = (100.0 * self.present / self.expected) if self.expected else 0.0
        return {
            "expected_ticker_days": self.expected,
            "present_ticker_days": self.present,
            "complete_ticker_days": self.complete,
            "missing_ticker_days": self.missing,
            "coverage_pct": round(pct, 4),
            "broker_rows_coverage_pct": round(broker_pct, 4),
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


_BROKER_ROWS_SQL = """
    SELECT DISTINCT trade_date, ticker FROM broker_flow
    WHERE trade_date >= ? AND trade_date <= ? AND ticker IN ({marks})
"""

# Set-based twin of tools/broker_flow_idx80_gap.py::broker_cell_complete's
# confirmed-empty clause. COALESCE so a NULL column never reads as "activity".
_EMPTY_MARKER_SQL = """
    SELECT DISTINCT trade_date, ticker FROM bandar_detector
    WHERE trade_date >= ? AND trade_date <= ? AND ticker IN ({marks})
      AND COALESCE(value, 0)  = 0
      AND COALESCE(volume, 0) = 0
"""


def compute_coverage(conn, tickers: list, dates: list) -> Coverage:
    """Ticker-day coverage of `tickers` x `dates`. Never uses row counts."""
    cov = Coverage()
    if not tickers or not dates:
        return cov
    universe = set(tickers)
    lo, hi = min(dates), max(dates)
    present = _cells(conn, _BROKER_ROWS_SQL, tickers, lo, hi)
    empty = _cells(conn, _EMPTY_MARKER_SQL, tickers, lo, hi)

    per_date = len(universe)
    cov.expected = per_date * len(dates)
    for d in dates:
        with_rows = present.get(d, set()) & universe
        complete = with_rows | (empty.get(d, set()) & universe)
        cov.present_by_date[d] = with_rows
        cov.complete_by_date[d] = complete
        cov.present += len(with_rows)
        cov.complete += len(complete)
        if not complete:
            cov.dates_zero.append(d)
        elif len(complete) == per_date:
            cov.dates_full.append(d)
        else:
            cov.dates_partial.append({
                "date": d, "complete": len(complete), "with_broker_rows": len(with_rows),
                "expected": per_date, "missing": per_date - len(complete),
            })
    return cov


# --- runner inspection & invocation -----------------------------------------


def scan_runner_for_destructive_sql(path) -> list:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"unreadable: {e}"]
    return [m.group(0) for m in _DESTRUCTIVE_SQL.finditer(text)]


_RUNNER_DB = re.compile(
    r"^DB_PATH\s*=\s*HERE\s*/\s*\"([^\"]+)\"\s*/\s*\"([^\"]+)\"", re.MULTILINE)


def runner_db_path(runner) -> Optional[Path]:
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
    aborted_concurrent: bool = False


def next_day(d: str) -> str:
    return (_date.fromisoformat(d) + timedelta(days=1)).isoformat()


def complete_cells(conn, tickers: list, d: str) -> int:
    return compute_coverage(conn, tickers, [d]).complete


def _terminate(proc) -> None:
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

    Re-checks other_backfill_pids() on every poll, not just before spawning
    — a hand-launched second writer that appears WHILE this date's child is
    still running is caught mid-flight, not just between dates. The child WE
    just spawned is excluded by its own PID (`proc.pid`) — it is expected to
    match the marker (its cmdline literally runs the runner), so scanning
    without excluding it self-aborted every real execution the moment the
    child became visible in /proc (2026-08-27 production incident: "FAILED
    0/79 cells 0.01s ... backfill process appeared mid-run"). An unrelated,
    independently-launched runner process is still detected and still aborts
    the run — only OUR OWN intended child is exempted.
    """
    t0 = time.monotonic()
    last_complete = complete_cells(conn, tickers, date)
    last_progress = t0
    proc = spawn(cmd, cwd=str(HERE))
    child_pid = getattr(proc, "pid", None)
    exclude = {child_pid} if child_pid is not None else frozenset()
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
            if other_backfill_pids(exclude=exclude):
                _terminate(proc)
                return ChildResult(None, time.monotonic() - t0, False, False,
                                  aborted_concurrent=True)
            time.sleep(poll_s)
            complete = complete_cells(conn, tickers, date)
            if complete > last_complete:
                last_complete = complete
                last_progress = time.monotonic()
    finally:
        if proc.poll() is None:
            _terminate(proc)


def run_backfill(cmd: list, timeout: int) -> RunResult:
    """Launch the runner as one whole-window invocation (probe only)."""
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(HERE), timeout=timeout)
        return RunResult(proc.returncode, time.time() - t0, False)
    except subprocess.TimeoutExpired:
        return RunResult(None, time.time() - t0, True)


def default_python() -> str:
    venv = HERE / "venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


def build_command(python: str, runner, date_from: str, date_to: str,
                  budget_s: int, probe: bool, universe: str = "live") -> list:
    cmd = [python, str(runner), "--date-from", date_from, "--date-to", date_to,
          "--budget-s", str(budget_s)]
    if probe:
        cmd.append("--probe")
    if universe == "pit":
        cmd += ["--universe", "pit"]
    return cmd


def compute_coverage_pit(conn, dates: list) -> Coverage:
    """Coverage against the PER-DATE PIT rosters (data-collection authority).

    Each date is measured against its own resolved membership
    (tools.broker_flow_pit_planning.required_members -- all-evidence tier,
    never truncated/padded, never idx_tickers). Roster sizes != 80 are
    expected here and are surfaced as advisories in the report, not errors.
    """
    cov = Coverage()
    for d in dates:
        roster, _advisory = required_members(conn, d)
        if not roster:
            cov.dates_zero.append(d)
            cov.present_by_date[d] = set()
            cov.complete_by_date[d] = set()
            continue
        part = compute_coverage(conn, roster, [d])
        cov.expected += part.expected
        cov.present += part.present
        cov.complete += part.complete
        cov.present_by_date[d] = part.present_by_date.get(d, set())
        cov.complete_by_date[d] = part.complete_by_date.get(d, set())
        if d in part.dates_zero:
            cov.dates_zero.append(d)
        elif any(x.get("date") == d for x in part.dates_partial):
            # compute_coverage stores PARTIAL dates as dicts
            # {"date": ..., "complete": ..., ...}; bare-string membership
            # would always be False and misclassify every partial date as
            # full (2026-08-31 plan-audit defect). Re-emit the same dict
            # shape so pit and live plan output stay identical.
            cov.dates_partial.extend(
                x for x in part.dates_partial if x.get("date") == d)
        else:
            cov.dates_full.append(d)
    return cov


def supervise_dates(db_path, tickers: list, dates: list, python: str,
                    runner, budget_s: int,
                    date_timeout_s: int, no_progress_s: int,
                    poll_s: int, universe_mode: str = "live",
                    rosters: dict = None, conn=None) -> tuple:
    """Execute the backfill ONE TRADING DATE AT A TIME.

    Returns (outcomes, launched, aborted). Resume is derived from the DB.
    universe_mode="pit" measures each date against its own per-date PIT
    roster (`rosters`, resolved once by the caller via the planning layer)
    and launches children with `--universe pit`; the child resolves the same
    roster independently from the same frozen ledger. `conn` is a test seam
    (a provided connection is reused and never closed).
    """
    def roster_for(d):
        return rosters[d] if rosters is not None else tickers

    def coverage_for(d):
        c = conn if conn is not None else connect_ro(db_path)
        owned = conn is None
        try:
            return compute_coverage(c, roster_for(d), [d])
        finally:
            if owned:
                c.close()

    outcomes = []
    launched = 0
    for i, d in enumerate(dates, 1):
        before = coverage_for(d)
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
            print(f"[supervisor {i}/{len(dates)} {d}] ABORTED: {aborted}",
                  file=sys.stderr, flush=True)
            return outcomes, launched, aborted
        cmd = build_command(python, runner, d, next_day(d), budget_s,
                            probe=False, universe=universe_mode)
        launched += 1
        spawn_error = None
        child_conn = conn if conn is not None else connect_ro(db_path)
        try:
            try:
                res = run_date_child(cmd, child_conn, roster_for(d), d,
                                     date_timeout_s=date_timeout_s,
                                     no_progress_s=no_progress_s,
                                     poll_s=poll_s)
            except Exception as e:  # per-date isolation: never stop the loop
                res = ChildResult(None, 0.0, False, False)
                spawn_error = str(e)
        finally:
            if conn is None:
                child_conn.close()
        after = coverage_for(d)
        if spawn_error:
            outcome, reason = "FAILED", f"could not launch child: {spawn_error}"
        elif getattr(res, "aborted_concurrent", False):
            aborted = (f"backfill process appeared mid-run during {d} — "
                      f"child terminated, aborting remaining dates")
            outcomes.append({
                "date": d, "outcome": "FAILED", "reason": aborted,
                "returncode": res.returncode,
                "duration_s": round(res.duration_s, 2),
                "timed_out": False, "stalled": False,
                "complete_cells": after.complete, "expected_cells": after.expected,
                "command": cmd,
            })
            return outcomes, launched, aborted
        elif res.timed_out:
            outcome, reason = "FAILED", \
                f"child exceeded --date-timeout-s {date_timeout_s}s"
        elif res.stalled:
            outcome, reason = "STALLED", \
                f"no new complete cell for --no-progress-timeout-s {no_progress_s}s"
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
            "complete_cells": after.complete, "expected_cells": after.expected,
            "command": cmd,
        })
        print(f"[supervisor {i}/{len(dates)} {d}] {outcome}"
              f"{' rc=' + str(res.returncode) if res.returncode is not None else ''}"
              f" {after.complete}/{after.expected} cells"
              f" {res.duration_s:.1f}s", file=sys.stderr, flush=True)
    return outcomes, launched, None


def _recompute_coverage(db_path, tickers: list, dates: list,
                        universe_mode: str = "live"):
    if universe_mode == "pit":
        conn = connect_ro(db_path)
        try:
            return compute_coverage_pit(conn, dates)
        finally:
            conn.close()
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
        prog="agent_backfill_broker_flow_idx80.py",
        description="IDX80 broker_flow backfill orchestrator (plans and "
                    "audits tools/backfill_broker_flow_idx80.py; never "
                    "fetches itself)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 COMPLETE, 1 PARTIAL, 2 FAILED, 3 BLOCKED.\n"
               "Default action is `plan`: read-only, no vendor calls, no writes.\n"
               "Universe is always IDX80 -- there is no flag to widen it.",
    )
    ap.add_argument("--action", choices=("plan", "probe", "execute"), default="plan",
                    help="plan (default, read-only) | probe (bounded vendor "
                         "diagnostic, BBCA only) | execute (real backfill)")
    ap.add_argument("--date-from", required=True, help="inclusive lower bound, YYYY-MM-DD")
    ap.add_argument("--date-to", required=True,
                    help="EXCLUSIVE upper bound, YYYY-MM-DD")
    ap.add_argument("--budget-s", type=int, default=DEFAULT_BUDGET_S,
                    help=f"wall-clock budget passed to the runner "
                         f"(1..{HARD_CAP_S}; default {DEFAULT_BUDGET_S})")
    ap.add_argument("--date-timeout-s", type=int, default=DEFAULT_DATE_TIMEOUT_S,
                    help=f"per-date child wall-clock timeout in seconds "
                         f"(default {DEFAULT_DATE_TIMEOUT_S})")
    ap.add_argument("--no-progress-timeout-s", type=int,
                    default=DEFAULT_NO_PROGRESS_TIMEOUT_S,
                    help=f"seconds without a newly-complete cell before the "
                         f"child is terminated and the date recorded STALLED "
                         f"(default {DEFAULT_NO_PROGRESS_TIMEOUT_S})")
    ap.add_argument(CONFIRM_FLAG, action="store_true",
                    help="REQUIRED for --action execute/probe. Without it, "
                         "execution is refused.")
    ap.add_argument("--universe", choices=("live", "pit"), default="live",
                    help="live (default): expected coverage measured against "
                         "today's active idx_tickers roster -- unchanged "
                         "historical behavior. pit: each date is measured "
                         "against its own point-in-time roster from the WP-D "
                         "ledger via tools.broker_flow_pit_planning (all "
                         "resolved members, never truncated to 80, never "
                         "substituted by idx_tickers); children are launched "
                         "with --universe pit; roster sizes != 80 are "
                         "advisories, not errors")
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

    checks, reasons, notes = [], [], []
    report = {
        "action": args.action,
        "status": "BLOCKED",
        "category": "IDX80",
        "date_from": args.date_from,
        "date_to": args.date_to,
        "date_to_exclusive": True,
        "budget_s": args.budget_s,
        "db": args.db,
        "runner": args.runner,
        "universe_size": None,
        "calendar": None,
        "coverage_before": None,
        "coverage_after": None,
        "proposed_command": [],
        "subprocess": None,
        "execution": None,
        "dates": None,
        "date_summary": None,
        "vendor_calls_made": False,
        "safety_checks": checks,
        "execution_allowed": False,
        "reasons": reasons,
        "notes": notes,
    }

    # --- checks that need no database ---------------------------------------
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
        reasons.append(f"--budget-s must be 1..{HARD_CAP_S}")

    timeout_ok = (args.date_timeout_s > 0 and args.no_progress_timeout_s > 0
                 and args.no_progress_timeout_s <= args.date_timeout_s)
    if not _check(checks, "timeout_params_valid", timeout_ok,
                 f"date_timeout_s={args.date_timeout_s}, "
                 f"no_progress_timeout_s={args.no_progress_timeout_s}"):
        reasons.append(f"--date-timeout-s and --no-progress-timeout-s must be "
                       f"positive and the no-progress bound must not exceed "
                       f"the wall clock")

    destructive = scan_runner_for_destructive_sql(args.runner)
    if not _check(checks, "runner_non_destructive", not destructive,
                 f"destructive SQL found: {destructive}" if destructive
                 else "runner only INSERTs OR REPLACEs keyed rows"):
        reasons.append(f"runner {args.runner} contains destructive SQL "
                       f"{destructive} — STOPPING rather than orchestrating a "
                       f"tool that can erase existing data")

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
            tickers = idx80_universe(conn)
        except Exception as e:
            reasons.append(f"cannot resolve IDX80 universe: {e}")
        report["universe_size"] = len(tickers)
        report["universe_mode"] = args.universe
        if args.universe == "pit":
            # PIT mode: today's live roster is NOT the expected-coverage
            # authority; each date is measured against its own resolved
            # WP-D ledger membership. The live check is informational only.
            _check(checks, "universe_is_idx80_and_non_empty", True,
                   f"universe_mode=pit: per-date PIT rosters from the WP-D "
                   f"ledger (idx80_reconstitution_periods / "
                   f"idx80_membership_history); live roster "
                   f"({len(tickers)} names) not used for expected coverage")
        elif not _check(checks, "universe_is_idx80_and_non_empty", bool(tickers),
                     f"{len(tickers)} active IDX80 ticker(s) "
                     f"(status='active' AND in_idx80=1)"):
            reasons.append("active IDX80 universe is empty — refusing to "
                           "plan/execute against an empty or misconfigured "
                           "universe")

        rows = calendar_rows(conn, args.date_from, args.date_to)
        ihsg = ihsg_dates(conn, args.date_from, args.date_to)
        dates, non_ihsg = expected_dates(rows, ihsg)
        report["calendar"] = {
            "expected_source": "trading_calendar AND an IHSG ohlcv bar",
            "calendar_rows_in_window": len(rows),
            "dates_in_window": len(dates),
            "non_ihsg_dates": non_ihsg,
            "non_ihsg_dates_count": len(non_ihsg),
        }
        if not _check(checks, "calendar_has_trading_dates", bool(dates),
                     f"{len(dates)} IHSG-confirmed trading date(s) in window "
                     f"({len(rows)} calendar row(s))"):
            reasons.append(f"no IHSG-confirmed trading dates in "
                           f"[{args.date_from}, {args.date_to}) — nothing to plan")
        if non_ihsg:
            notes.append(
                f"{len(non_ihsg)} trading_calendar row(s) in this window have "
                f"NO IHSG ohlcv bar and are therefore NOT counted as expected "
                f"IDX80 sessions: {[x['date'] for x in non_ihsg[:5]]}"
                f"{'...' if len(non_ihsg) > 5 else ''}. Nothing was mutated; "
                f"this tool is read-only.")

        if tickers and dates:
            if args.universe == "pit":
                report["coverage_before"] = compute_coverage_pit(conn, dates).as_dict()
                # surface the per-date roster advisories (sizes != 80,
                # uncovered dates) in PLAN output too -- not just at execute.
                advisories = []
                for d in dates:
                    _roster, advisory = required_members(conn, d)
                    if advisory is not None:
                        advisories.append(advisory)
                report["pit_advisories"] = advisories
            else:
                report["coverage_before"] = compute_coverage(conn, tickers, dates).as_dict()

    target = runner_db_path(args.runner)
    same_db = target is not None and Path(args.db).resolve() == target.resolve()
    if not same_db:
        detail = (f"agent audits {args.db}; runner writes "
                 f"{target if target else 'UNKNOWN (could not parse DB_PATH)'}")
        _check(checks, "audit_db_is_the_runner_target", False, detail,
              blocking=(args.action in ("probe", "execute")))
        (reasons if args.action in ("probe", "execute") else notes).append(
            f"the runner writes to a different database than this agent audits "
            f"— {detail}.")
    else:
        _check(checks, "audit_db_is_the_runner_target", True, str(target))

    python = args.python or default_python()
    if dates_ok and budget_ok:
        report["proposed_command"] = build_command(
            python, args.runner, args.date_from, args.date_to,
            args.budget_s, probe=(args.action == "probe"),
            universe=args.universe)

    blocking_failed = [c["name"] for c in checks if c["blocking"] and not c["ok"]]
    report["execution_allowed"] = not blocking_failed

    wants_vendor = args.action in ("probe", "execute")
    if wants_vendor and not confirmed:
        _check(checks, "execution_confirmed", False, f"{CONFIRM_FLAG} not supplied")
        reasons.append(f"--action {args.action} makes real Stockbit calls; it "
                       f"requires the explicit {CONFIRM_FLAG} confirmation flag.")
        blocking_failed.append("execution_confirmed")
    elif wants_vendor:
        _check(checks, "execution_confirmed", True, f"{CONFIRM_FLAG} supplied")

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
                                     "successful probe is NOT evidence of "
                                     "historical coverage. Read coverage_after.")
                        res = run_backfill(report["proposed_command"],
                                           timeout=args.budget_s + TIMEOUT_MARGIN_S)
                        report["subprocess"] = {
                            "returncode": res.returncode,
                            "duration_s": round(res.duration_s, 2),
                            "timed_out": res.timed_out,
                            "timeout_s": args.budget_s + TIMEOUT_MARGIN_S,
                        }
                        after = _recompute_coverage(args.db, tickers, dates, args.universe)
                        report["coverage_after"] = after.as_dict() if after else None
                        if res.timed_out or res.returncode != 0:
                            report["status"] = "FAILED"
                            reasons.append(
                                "runner timed out" if res.timed_out
                                else f"runner exited {res.returncode} "
                                     f"(2=auth, 3=sustained fetch failure)")
                        elif after is not None and after.missing == 0:
                            report["status"] = "COMPLETE"
                        else:
                            report["status"] = "PARTIAL"
                            remaining = after.missing if after is not None else "unknown"
                            reasons.append(
                                f"runner exited 0 but {remaining} ticker-day "
                                f"cell(s) remain uncovered. NOT COMPLETE.")
                    else:  # execute: supervised, one trading date per child
                        report["execution"] = {
                            "model": "per_date",
                            "date_timeout_s": args.date_timeout_s,
                            "no_progress_timeout_s": args.no_progress_timeout_s,
                            "progress_poll_s": PROGRESS_POLL_S,
                        }
                        rosters = None
                        if args.universe == "pit":
                            rosters = {}
                            for d in dates:
                                roster, advisory = required_members(conn, d)
                                rosters[d] = roster
                                if advisory is not None:
                                    report.setdefault(
                                        "pit_advisories", []).append(advisory)
                            outcomes, launches, aborted = supervise_dates(
                                args.db, tickers, dates, python, args.runner,
                                args.budget_s,
                                args.date_timeout_s,
                                args.no_progress_timeout_s,
                                PROGRESS_POLL_S, universe_mode="pit",
                                rosters=rosters)
                        else:
                            outcomes, launches, aborted = supervise_dates(
                                args.db, tickers, dates, python, args.runner,
                                args.budget_s,
                                args.date_timeout_s, args.no_progress_timeout_s,
                                PROGRESS_POLL_S)
                        report["vendor_calls_made"] = launches > 0
                        report["dates"] = outcomes
                        report["date_summary"] = {
                            "total": len(outcomes),
                            "success": sum(1 for o in outcomes if o["outcome"] == "SUCCESS"),
                            "skipped": sum(1 for o in outcomes if o["outcome"] == "SKIPPED"),
                            "failed": sum(1 for o in outcomes if o["outcome"] == "FAILED"),
                            "stalled": sum(1 for o in outcomes if o["outcome"] == "STALLED"),
                            "launched": launches,
                        }
                        first = next((o for o in outcomes if o["command"]), None)
                        if first is not None:
                            report["proposed_command"] = first["command"]
                        report["subprocess"] = {
                            "launches": launches,
                            "duration_s": round(sum(o["duration_s"] for o in outcomes), 2),
                            "timed_out": any(o["timed_out"] for o in outcomes),
                            "stalled": any(o["stalled"] for o in outcomes),
                        }
                        after = _recompute_coverage(args.db, tickers, dates, args.universe)
                        report["coverage_after"] = after.as_dict() if after else None
                        hard = [o for o in outcomes if o["outcome"] in ("FAILED", "STALLED")]
                        if aborted:
                            report["status"] = "BLOCKED"
                            report["execution_allowed"] = False
                            reasons.append(aborted)
                        elif hard:
                            report["status"] = "FAILED"
                            reasons.append(
                                f"{len(hard)} date(s) did not complete: "
                                f"{[o['date'] for o in hard][:10]}"
                                f"{'...' if len(hard) > 10 else ''}")
                            for o in hard:
                                reasons.append(f"date {o['date']}: {o['outcome']} — {o['reason']}")
                        elif after is not None and after.missing == 0:
                            report["status"] = "COMPLETE"
                        else:
                            report["status"] = "PARTIAL"
                            remaining = after.missing if after is not None else "unknown"
                            reasons.append(f"{remaining} ticker-day cell(s) remain uncovered.")
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
    print("=== IDX80 broker_flow backfill agent ===")
    print(f"Action:     {r['action']}   Status: {r['status']}")
    print(f"Category:   {r['category']} ({r['universe_size']} tickers)")
    print(f"Window:     [{r['date_from']}, {r['date_to']})   — --date-to is EXCLUSIVE")
    if r["calendar"]:
        c = r["calendar"]
        print(f"Calendar:   {c['dates_in_window']} IHSG-confirmed trading date(s) "
              f"of {c['calendar_rows_in_window']} trading_calendar row(s)")
        if c["non_ihsg_dates"]:
            shown = [f"{x['date']}({x['source']})" for x in c["non_ihsg_dates"][:10]]
            print(f"            ⚠ not IHSG-confirmed, excluded: {shown}")
    for label, key in (("before", "coverage_before"), ("after", "coverage_after")):
        cov = r.get(key)
        if not cov:
            continue
        print(f"\nCoverage ({label}):")
        print(f"  expected ticker-days : {cov['expected_ticker_days']}")
        print(f"  with broker rows     : {cov['present_ticker_days']} "
              f"({cov['broker_rows_coverage_pct']}%)")
        print(f"  complete (predicate) : {cov['complete_ticker_days']} "
              f"({cov['coverage_pct']}%)")
        print(f"  missing              : {cov['missing_ticker_days']}")
        print(f"  dates full/partial/zero: {cov['dates_full_count']}/"
              f"{cov['dates_partial_count']}/{cov['dates_zero_count']}")
    print("\nSafety checks:")
    for c in r["safety_checks"]:
        mark = "✓" if c["ok"] else ("✗" if c["blocking"] else "~")
        print(f"  {mark} {c['name']}: {c['detail']}")
    print(f"\nExecution allowed: {r['execution_allowed']}")
    print(f"Proposed command:\n  {' '.join(r['proposed_command'])}")
    if r.get("dates"):
        print("Per-date outcomes:")
        for o in r["dates"][:12]:
            tail = f" ({o['reason']})" if o["reason"] else ""
            print(f"  [{o['date']}] {o['outcome']} {o['complete_cells']}/"
                  f"{o['expected_cells']} cells {o['duration_s']}s{tail}")
    for n in r["notes"]:
        print(f"NOTE: {n}")
    for x in r["reasons"]:
        print(f"REASON: {x}")


if __name__ == "__main__":
    sys.exit(main())
