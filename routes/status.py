"""Production Status Registry HTTP API — read-only endpoints over engine.
job_status's job_execution_log table (Phase 1 Task 2, Production Engine
readiness). Canonical interface for job health: intended consumers are the
existing dashboard (a future page), a future daily Telegram summary, and the
Agent Firm (e.g. checking whether upstream data-collector jobs are healthy
before trusting their output) — all can share this one HTTP contract instead
of each hand-rolling their own job_execution_log query.

Pure read layer: never writes to job_execution_log, never feeds back into
scheduling or job execution. GET-only, JSON-only, matches the existing
routes/flow.py dashboard-endpoint conventions (thin handler, error -> 500
with {"error": ...}, no raw stack traces).
"""
from flask import Blueprint, jsonify, request

from config import DB_PATH
from engine import job_status

status_bp = Blueprint("status", __name__)

# Internal-only columns stripped from every row before it leaves this API —
# the raw autoincrement PK is an implementation detail; run_id is the public
# identifier (see engine.job_status's own docstring on why run_id, not
# job_name, is the uniqueness anchor).
_INTERNAL_FIELDS = ("id",)


def _public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in _INTERNAL_FIELDS}


@status_bp.route("/api/status/jobs/running", methods=["GET"])
def api_status_jobs_running():
    """Jobs currently executing (status='running'), newest first."""
    rows = job_status.get_running_jobs(db_path=DB_PATH)
    running = [_public(r) for r in rows]
    return jsonify({"running": running, "count": len(running)})


@status_bp.route("/api/status/jobs/latest", methods=["GET"])
def api_status_jobs_latest():
    """Most recent execution row per distinct job_name."""
    rows = job_status.get_latest_job_status(db_path=DB_PATH)
    return jsonify({"jobs": [_public(r) for r in rows]})


@status_bp.route("/api/status/jobs/failed", methods=["GET"])
def api_status_jobs_failed():
    """All status='failed' rows, newest first.

    Query params:
      since — optional 'YYYY-MM-DD HH:MM:SS' cutoff (only failures at/after
              this timestamp).
    """
    since = request.args.get("since")
    rows = job_status.get_failed_jobs(since=since, db_path=DB_PATH)
    return jsonify({"failed": [_public(r) for r in rows]})


@status_bp.route("/api/status/jobs/history", methods=["GET"])
def api_status_jobs_history():
    """Recent execution history (any status, any job), newest first.

    Query params:
      limit — max rows to return (default 50, clamped to a sane cap
              server-side; must be a positive integer).
    """
    raw_limit = request.args.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        return jsonify({"error": f"limit must be an integer, got {raw_limit!r}"}), 400
    if limit <= 0:
        return jsonify({"error": "limit must be a positive integer"}), 400

    rows = job_status.get_recent_jobs(limit=limit, db_path=DB_PATH)
    return jsonify({"history": [_public(r) for r in rows]})


@status_bp.route("/api/status/summary", methods=["GET"])
def api_status_summary():
    """Aggregate counts: total/success/failed/skipped/running."""
    return jsonify(job_status.get_status_summary(db_path=DB_PATH))
