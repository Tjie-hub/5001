"""Production Status Registry HTTP API, migrated onto the API v1 envelope
(Production Engine Phase 2, Workstream A Task 1). Supersedes routes/status.py
-- same read-only surface over engine.job_status's job_execution_log table,
same pure-read guarantee (never writes to job_execution_log, never feeds back
into scheduling or job execution), now under /api/v1/status/* using ok()/
ApiError instead of a bespoke JSON shape. Intended consumers unchanged: the
dashboard, a daily Telegram summary, and the Agent Firm.

config.DB_PATH is read via the `config` module attribute at call time (not
bound to a local at import time) so tests can monkeypatch it directly --
api_v1_bp is a shared blueprint across routes/v1/*.py, so this module is only
ever imported once per process (no per-test reload, which would re-decorate
the shared blueprint and register duplicate routes).
"""
import config
from flask import request

from engine import job_status
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok

_INTERNAL_FIELDS = ("id",)


def _public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in _INTERNAL_FIELDS}


@api_v1_bp.route("/status/jobs/running", methods=["GET"])
def status_jobs_running():
    """Jobs currently executing (status='running'), newest first."""
    rows = job_status.get_running_jobs(db_path=config.DB_PATH)
    running = [_public(r) for r in rows]
    return ok({"running": running, "count": len(running)})


@api_v1_bp.route("/status/jobs/latest", methods=["GET"])
def status_jobs_latest():
    """Most recent execution row per distinct job_name."""
    rows = job_status.get_latest_job_status(db_path=config.DB_PATH)
    return ok({"jobs": [_public(r) for r in rows]})


@api_v1_bp.route("/status/jobs/failed", methods=["GET"])
def status_jobs_failed():
    """All status='failed' rows, newest first.

    Query params:
      since -- optional 'YYYY-MM-DD HH:MM:SS' cutoff (only failures at/after
              this timestamp).
    """
    since = request.args.get("since")
    rows = job_status.get_failed_jobs(since=since, db_path=config.DB_PATH)
    return ok({"failed": [_public(r) for r in rows]})


@api_v1_bp.route("/status/jobs/history", methods=["GET"])
def status_jobs_history():
    """Recent execution history, newest first.

    Query params:
      limit    -- max rows to return (default 50); must be a positive integer.
      job_name -- optional; restrict history to one job (Job History drill-down).
    """
    raw_limit = request.args.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        raise ApiError("INVALID_LIMIT", 400,
                        f"limit must be an integer, got {raw_limit!r}")
    if limit <= 0:
        raise ApiError("INVALID_LIMIT", 400, "limit must be a positive integer")

    job_name = request.args.get("job_name")
    rows = job_status.get_recent_jobs(limit=limit, db_path=config.DB_PATH, job_name=job_name)
    return ok({"history": [_public(r) for r in rows]})


@api_v1_bp.route("/status/summary", methods=["GET"])
def status_summary():
    """Aggregate counts: total/success/failed/skipped/running."""
    return ok(job_status.get_status_summary(db_path=config.DB_PATH))
