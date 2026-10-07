"""Production Status Registry (Phase 1) -- engine/job_status.py

Append-only execution ledger for every production scheduler job: one row per
execution ATTEMPT (run_id is the uniqueness anchor, not job_name), INSERTed
as 'running' before the job body executes, finalized to success/failed/
skipped on exit. Mirrors research/tracking.py::track_run() on the production
side of the research/production boundary -- can't import that module
directly, since production may not import research.* (test_architecture_
boundary.py), so the fail-soft git-commit capture below is duplicated, not
shared.

Restart-safe by construction: a process crash mid-job leaves an orphaned
'running' row rather than losing the execution record; the next execution of
the same job_name mints a fresh run_id and never collides with it.

Orphan classification is READ-ONLY (frontend-trim brief, 2026-10-06): the
append-only ledger is never rewritten, so a 'running' row left by a dead
process stays 'running' forever in the table. Reads classify instead — a
running row counts as orphaned when it started before the current process
started (fallback when the process start time is unavailable: older than
ORPHAN_MAX_AGE_S, 6 h). get_running_jobs() returns only live runs,
get_orphaned_running_jobs() only orphaned ones, and get_status_summary()
counts them under separate keys; the ledger itself is untouched.
"""
import contextvars
import os
import sqlite3
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import pytz

from config import DB_PATH as _DEFAULT_DB_PATH
from data.db import connect as db_connect

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB_PATH)

# Fallback orphan rule: when the current process's start time cannot be
# determined, a 'running' row older than this counts as orphaned.
ORPHAN_MAX_AGE_S = 6 * 3600

JOB_EXECUTION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS job_execution_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             TEXT NOT NULL UNIQUE,
    job_name           TEXT NOT NULL,
    run_type           TEXT NOT NULL,
    started_at         TEXT NOT NULL,
    completed_at       TEXT,
    duration_ms        INTEGER,
    status             TEXT NOT NULL,
    records_processed  INTEGER,
    telegram_sent      INTEGER DEFAULT 0,
    error_message      TEXT,
    retry_count        INTEGER DEFAULT 0,
    engine_version     TEXT
)
"""


def ensure_job_status_table(conn) -> None:
    """Idempotent migration -- safe to call on every track_job() invocation
    (mirrors the CREATE TABLE IF NOT EXISTS + no-op-if-present pattern used
    throughout data/db.py and research/tracking.py)."""
    conn.execute(JOB_EXECUTION_LOG_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jel_job_started "
        "ON job_execution_log(job_name, started_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_jel_status ON job_execution_log(status)"
    )


def _engine_version() -> Optional[str]:
    """Current HEAD short-hash, or None outside a repo / without git.

    Fail-soft -- duplicated (not imported) from research/tracking.py::
    git_commit(); production code may not import research.*.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


class JobRunHandle:
    """Yielded by track_job(); job code may optionally enrich it:

        handle.records_processed = 42
        handle.telegram_sent = True
    """

    def __init__(self, run_id: str, job_name: str):
        self.run_id = run_id
        self.job_name = job_name
        self.records_processed: Optional[int] = None
        self.telegram_sent: bool = False
        self._skip_reason: Optional[str] = None

    def mark_skipped(self, reason: str = None) -> None:
        self._skip_reason = reason or "skipped"


_current_job: "contextvars.ContextVar[Optional[JobRunHandle]]" = contextvars.ContextVar(
    "current_job_handle", default=None
)


def current_job() -> Optional[JobRunHandle]:
    """The JobRunHandle for the job currently executing inside a track_job()
    block on this context, or None if called outside one (e.g. directly from
    a test, or from code not wrapped by track_job/wrap_scheduled)."""
    return _current_job.get()


def _finalize(db_path, run_id, started_monotonic, status, error,
              records_processed, telegram_sent) -> None:
    conn = db_connect(db_path)
    try:
        conn.execute(
            "UPDATE job_execution_log SET completed_at=?, duration_ms=?, status=?, "
            "records_processed=?, telegram_sent=?, error_message=? WHERE run_id=?",
            (
                datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
                int(round((time.monotonic() - started_monotonic) * 1000)),
                status, records_processed, int(telegram_sent), error, run_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def track_job(job_name: str, run_type: str = "scheduled", retry_count: int = 0,
              db_path: str = None):
    """Record one job execution in job_execution_log (append-only).

    INSERTs a 'running' row up front (before the job body runs), yields a
    JobRunHandle, and finalizes to success/failed on exit. Exceptions are
    recorded then RE-RAISED -- callers (e.g. scheduler/__init__.py's
    EVENT_JOB_ERROR listener) still see them; this wrapper must never
    swallow a job's exception.
    """
    db_path = db_path or DB_PATH
    run_id = uuid.uuid4().hex
    started = time.monotonic()
    conn = db_connect(db_path)
    try:
        ensure_job_status_table(conn)
        conn.execute(
            "INSERT INTO job_execution_log (run_id, job_name, run_type, started_at, "
            "status, retry_count, engine_version) VALUES (?,?,?,?,'running',?,?)",
            (
                run_id, job_name, run_type,
                datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
                retry_count, _engine_version(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    handle = JobRunHandle(run_id, job_name)
    token = _current_job.set(handle)
    try:
        yield handle
    except BaseException as e:
        _finalize(db_path, run_id, started, "failed", str(e)[:1000],
                   handle.records_processed, handle.telegram_sent)
        raise
    else:
        status = "skipped" if handle._skip_reason else "success"
        _finalize(db_path, run_id, started, status, handle._skip_reason,
                   handle.records_processed, handle.telegram_sent)
    finally:
        _current_job.reset(token)


def wrap_scheduled(func, job_name: str, run_type: str = "scheduled", db_path: str = None):
    """Wrap a job callable so every call is tracked automatically, without
    the job body needing to know about the registry. Used by
    scheduler/__init__.py's _add_job() at job-registration time."""

    def _wrapped(*args, **kwargs):
        with track_job(job_name, run_type=run_type, db_path=db_path):
            return func(*args, **kwargs)

    _wrapped.__name__ = getattr(func, "__name__", job_name)
    return _wrapped


def _row_to_dict(row) -> dict:
    return dict(row)


def get_latest_job_status(job_name: str = None, db_path: str = None):
    """Most recent execution row for `job_name` as a dict (or None if it has
    never run); if job_name is omitted, the most recent row per distinct
    job_name across every job, as a list of dicts ordered by job_name."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        if job_name is not None:
            row = conn.execute(
                "SELECT * FROM job_execution_log WHERE job_name=? "
                "ORDER BY id DESC LIMIT 1", (job_name,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        rows = conn.execute(
            "SELECT * FROM job_execution_log WHERE id IN "
            "(SELECT MAX(id) FROM job_execution_log GROUP BY job_name) "
            "ORDER BY job_name"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_last_success(job_name: str, db_path: str = None):
    """Most recent status='success' row for `job_name` as a dict, or None if
    it has never succeeded."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        row = conn.execute(
            "SELECT * FROM job_execution_log WHERE job_name=? AND status='success' "
            "ORDER BY id DESC LIMIT 1", (job_name,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_failed_jobs(since=None, db_path: str = None):
    """All status='failed' rows, newest first, optionally restricted to
    started_at >= since (a 'YYYY-MM-DD HH:MM:SS' string or a datetime)."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        if since is not None:
            since_str = since.strftime("%Y-%m-%d %H:%M:%S") if isinstance(since, datetime) else since
            rows = conn.execute(
                "SELECT * FROM job_execution_log WHERE status='failed' AND started_at>=? "
                "ORDER BY id DESC", (since_str,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM job_execution_log WHERE status='failed' ORDER BY id DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_jobs_since(since, db_path: str = None):
    """All rows (any status, any job) with started_at >= since, newest first."""
    db_path = db_path or DB_PATH
    since_str = since.strftime("%Y-%m-%d %H:%M:%S") if isinstance(since, datetime) else since
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        rows = conn.execute(
            "SELECT * FROM job_execution_log WHERE started_at>=? ORDER BY id DESC",
            (since_str,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_running_jobs(db_path: str = None):
    """Live running rows only, newest first.

    A status='running' row that started before the CURRENT process started is
    orphaned (left by a crashed/restarted process — the ledger is append-only,
    so the row is never rewritten) and is NOT returned here; see
    get_orphaned_running_jobs(). When the process start time is unavailable,
    the fallback rule applies: a running row older than ORPHAN_MAX_AGE_S (6 h)
    counts as orphaned. A row with an unparsable started_at stays visible as
    live (fail-open — never hide a possibly-running job).
    """
    live, _orphaned = _running_partition(db_path)
    return live


def get_orphaned_running_jobs(db_path: str = None):
    """Orphaned running rows only, newest first — the complement of
    get_running_jobs(). See there for the classification rule."""
    _live, orphaned = _running_partition(db_path)
    return orphaned


def _running_partition(db_path: str = None):
    """Split status='running' rows into (live, orphaned). Read-only."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        rows = conn.execute(
            "SELECT * FROM job_execution_log WHERE status='running' ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    return _partition_running([_row_to_dict(r) for r in rows])


def _partition_running(rows, now_epoch: Optional[float] = None,
                       process_start: Optional[float] = None):
    """Classify running rows into (live, orphaned).

    Orphan rule (read-only classification; the row itself is never mutated):
      primary   — started before the current process started;
      fallback  — process start unavailable → older than ORPHAN_MAX_AGE_S.

    `now_epoch`/`process_start` are injection points for tests; None means
    "compute now" / "probe /proc then fall back to the age rule".
    """
    now_epoch = time.time() if now_epoch is None else now_epoch
    if process_start is None:
        process_start = process_start_epoch()
    live, orphaned = [], []
    for row in rows:
        started = _started_at_epoch(row.get("started_at"))
        if started is None:
            live.append(row)  # undatable — keep visible, never hide
        elif process_start is not None:
            (orphaned if started < process_start else live).append(row)
        else:
            (orphaned if (now_epoch - started) > ORPHAN_MAX_AGE_S else live).append(row)
    return live, orphaned


def _started_at_epoch(started_at) -> Optional[float]:
    """Parse a ledger started_at ('%Y-%m-%d %H:%M:%S', WIB wall time) to a
    Unix epoch; None when missing or unparsable."""
    if not started_at:
        return None
    try:
        return WIB.localize(
            datetime.strptime(str(started_at), "%Y-%m-%d %H:%M:%S")
        ).timestamp()
    except (ValueError, TypeError):
        return None


def process_start_epoch() -> Optional[float]:
    """Unix epoch when the CURRENT process started, via Linux /proc
    (/proc/self/stat's starttime in clock ticks since boot, anchored to
    /proc/stat's btime). None when unavailable — non-Linux, restricted /proc,
    or unparsable — which switches the orphan rule to the ORPHAN_MAX_AGE_S
    age fallback."""
    try:
        with open("/proc/self/stat", "rb") as fh:
            # comm can contain spaces/parens: split after the closing paren.
            fields = fh.read().decode("ascii", "replace").rsplit(")", 1)[1].split()
        ticks = float(fields[19])  # overall field 22 (starttime); 3 fields consumed
        hertz = os.sysconf("SC_CLK_TCK")
        with open("/proc/stat") as fh:
            for line in fh:
                if line.startswith("btime"):
                    return float(line.split()[1]) + ticks / hertz
    except Exception:
        pass
    return None


_RECENT_JOBS_DEFAULT_LIMIT = 50
_RECENT_JOBS_MAX_LIMIT = 500


def get_recent_jobs(limit: int = _RECENT_JOBS_DEFAULT_LIMIT, db_path: str = None,
                     job_name: str = None):
    """Most recent `limit` rows, newest first, optionally restricted to one
    `job_name` (Operations Dashboard job-detail drill-down: the per-job
    execution history behind a single row of /scheduler/jobs). `limit` is
    clamped to [1, _RECENT_JOBS_MAX_LIMIT] so a careless caller can't force
    an unbounded table scan/response."""
    db_path = db_path or DB_PATH
    limit = max(1, min(int(limit), _RECENT_JOBS_MAX_LIMIT))
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        if job_name is not None:
            rows = conn.execute(
                "SELECT * FROM job_execution_log WHERE job_name=? "
                "ORDER BY id DESC LIMIT ?", (job_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM job_execution_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_status_summary(db_path: str = None) -> dict:
    """Aggregate counts by status, plus a total -- the at-a-glance health
    snapshot for a status dashboard/report. Always returns all 6 keys, zero-
    filled for statuses with no rows (never a KeyError for a quiet engine).

    'running' counts only LIVE runs; rows orphaned by a process restart are
    counted under 'orphaned' (read-only classification — the ledger is
    append-only and those rows are never rewritten). total is the count of
    all rows, so it is unchanged by the split.
    """
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM job_execution_log "
            "WHERE status != 'running' GROUP BY status"
        ).fetchall()
        running_rows = conn.execute(
            "SELECT started_at FROM job_execution_log WHERE status='running'"
        ).fetchall()
    finally:
        conn.close()
    counts = {"success": 0, "failed": 0, "skipped": 0}
    for status, count in rows:
        if status in counts:
            counts[status] = count
    live, orphaned = _partition_running([dict(r) for r in running_rows])
    counts["running"] = len(live)
    counts["orphaned"] = len(orphaned)
    return {"total": sum(counts.values()), **counts}
