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
    """All status='running' rows, newest first -- jobs currently executing
    (or, if orphaned by a process crash, jobs that never finalized)."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_job_status_table(conn)
        rows = conn.execute(
            "SELECT * FROM job_execution_log WHERE status='running' ORDER BY id DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


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
    snapshot for a status dashboard/report. Always returns all 5 keys, zero-
    filled for statuses with no rows (never a KeyError for a quiet engine)."""
    db_path = db_path or DB_PATH
    conn = db_connect(db_path)
    try:
        ensure_job_status_table(conn)
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM job_execution_log GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    counts = {"success": 0, "failed": 0, "skipped": 0, "running": 0}
    for status, count in rows:
        if status in counts:
            counts[status] = count
    return {"total": sum(counts.values()), **counts}
