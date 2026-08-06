"""Read-only scheduler visibility (Production Engine Phase 2, Workstream 2B
Task 2B-1). See docs/superpowers/specs/2026-08-06-2b1-scheduler-api-design.md.

Reads the live BackgroundScheduler via scheduler.get_scheduler() (added
alongside this task -- previously unreachable from a request) for
schedule/trigger state (next run, paused), and engine.job_status for
execution history (last run), joined on job_name == APScheduler job id
(exact, not a heuristic -- see scheduler._add_job's own docstring). Neither
source is duplicated: this module only reads and reshapes what already
exists. Degrades to an empty/"unavailable" response rather than erroring
when no scheduler has started yet in this process (e.g. under pytest),
matching the fail-soft posture already used for registry loading elsewhere
in this repo.
"""
import config
import scheduler as sched_pkg
from engine import job_status
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok

_INTERNAL_FIELDS = ("id",)


def _public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in _INTERNAL_FIELDS}


def _job_dict(job, last_run_by_name: dict) -> dict:
    next_run = getattr(job, "next_run_time", None)
    return {
        "job_id": job.id,
        "name": job.name,
        "trigger": str(job.trigger),
        "next_run_time": next_run.isoformat() if next_run else None,
        "paused": next_run is None,
        "last_run": last_run_by_name.get(job.id),
    }


def _last_run_by_name() -> dict:
    rows = job_status.get_latest_job_status(db_path=config.DB_PATH)
    return {r["job_name"]: _public(r) for r in rows}


@api_v1_bp.route("/scheduler", methods=["GET"])
def scheduler_status():
    sch = sched_pkg.get_scheduler()
    if sch is None:
        return ok({"available": False, "state": "unavailable",
                    "timezone": None, "job_count": 0})

    state_names = {0: "stopped", 1: "running", 2: "paused"}
    return ok({
        "available": True,
        "state": state_names.get(sch.state, "unknown"),
        "timezone": str(sch.timezone),
        "job_count": len(sch.get_jobs()),
    })


@api_v1_bp.route("/scheduler/jobs", methods=["GET"])
def scheduler_jobs():
    sch = sched_pkg.get_scheduler()
    if sch is None:
        return ok({"jobs": [], "count": 0})

    last_run_by_name = _last_run_by_name()
    jobs = [_job_dict(j, last_run_by_name) for j in sch.get_jobs()]
    return ok({"jobs": jobs, "count": len(jobs)})


@api_v1_bp.route("/scheduler/jobs/<job_id>", methods=["GET"])
def scheduler_job_detail(job_id):
    sch = sched_pkg.get_scheduler()
    job = sch.get_job(job_id) if sch is not None else None
    if job is None:
        raise ApiError("JOB_NOT_FOUND", 404, f"no scheduler job with id {job_id!r}")

    return ok(_job_dict(job, _last_run_by_name()))
