"""Aggregated operational health (Production Engine Phase 2, Workstream 2B
Task 2B-4). See docs/superpowers/specs/2026-08-06-2b4-health-api-design.md
for the exact per-component and overall rules.

Purely an aggregation over signals already built elsewhere -- no new health
probes. database is a minimal connectivity check via data.db.connect (the
one centralized entry point); scheduler reuses scheduler.get_scheduler()
(2B-1); metrics/configuration reuse engine.metrics.get_engine_metrics() /
engine.config_info.get_config_summary()+get_runtime_config() (2B-2/2B-3) --
their own return values aren't reinterpreted, only whether the call
succeeds at all, since those modules already own interpreting their data;
release reuses utils.release.release_info() (also used by /health and
/api/v1/config) and is informational only, no pass/fail status.
"""
import engine.config_info as config_info_mod
import engine.metrics as engine_metrics_mod
import scheduler as sched_pkg
import utils.release as release_mod
from data.db import connect as db_connect

_SCHEDULER_STATE_NAMES = {0: "stopped", 1: "running", 2: "paused"}


def _database_status(db_path: str) -> dict:
    try:
        conn = db_connect(db_path)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unavailable"}


def _scheduler_status() -> dict:
    sch = sched_pkg.get_scheduler()
    if sch is None:
        return {"status": "unavailable"}
    state = _SCHEDULER_STATE_NAMES.get(sch.state, "unknown")
    return {"status": "healthy" if state == "running" else "degraded", "state": state}


def _metrics_status(db_path: str) -> dict:
    try:
        engine_metrics_mod.get_engine_metrics(db_path)
        return {"status": "healthy"}
    except Exception:
        return {"status": "unavailable"}


def _configuration_status() -> dict:
    try:
        config_info_mod.get_config_summary()
        config_info_mod.get_runtime_config()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unavailable"}


def _release_info() -> dict:
    release = release_mod.release_info()
    data = {"version": release.get("version")}
    if "git_sha" in release:
        data["git_sha"] = release["git_sha"]
    return data


def get_health(db_path: str) -> dict:
    database = _database_status(db_path)
    scheduler_c = _scheduler_status()
    metrics_c = _metrics_status(db_path)
    configuration_c = _configuration_status()

    if database["status"] == "unavailable":
        overall = "unavailable"
    elif any(c["status"] != "healthy" for c in (scheduler_c, metrics_c, configuration_c)):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall": overall,
        "components": {
            "database": database,
            "scheduler": scheduler_c,
            "metrics": metrics_c,
            "configuration": configuration_c,
            "release": _release_info(),
        },
    }
