"""Operational metrics APIs (Production Engine Phase 2, Workstream 2B Task
2B-2). See docs/superpowers/specs/2026-08-06-2b2-metrics-api-design.md.

Thin controllers over three existing services: engine.job_status (already
backing /api/v1/status/summary -- reused verbatim here under a
metrics-oriented path), engine.metrics (new service extraction of app.py's
Prometheus /metrics query set, added alongside this task), and
scheduler.get_scheduler() (2B-1). No new metric computation.
"""
import config
import engine.metrics as engine_metrics_mod
import scheduler as sched_pkg
from engine import job_status
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok


@api_v1_bp.route("/metrics/jobs", methods=["GET"])
def metrics_jobs():
    return ok(job_status.get_status_summary(db_path=config.DB_PATH))


@api_v1_bp.route("/metrics/engine", methods=["GET"])
def metrics_engine():
    return ok(engine_metrics_mod.get_engine_metrics(config.DB_PATH))


def _scheduler_summary() -> dict:
    sch = sched_pkg.get_scheduler()
    if sch is None:
        return {"available": False, "job_count": 0}
    return {"available": True, "job_count": len(sch.get_jobs())}


@api_v1_bp.route("/metrics", methods=["GET"])
def metrics_rollup():
    return ok({
        "jobs": job_status.get_status_summary(db_path=config.DB_PATH),
        "engine": engine_metrics_mod.get_engine_metrics(config.DB_PATH),
        "scheduler": _scheduler_summary(),
    })
