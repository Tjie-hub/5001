"""Tests for routes/v1/scheduler.py -- read-only scheduler visibility
(Production Engine Phase 2, Workstream 2B Task 2B-1).

Never touches the real scheduler.start_scheduler() -- see
tests/test_scheduler_instance_getter.py for why. Instead builds a small
throwaway BackgroundScheduler and monkeypatches scheduler.get_scheduler to
return it, exactly the seam get_scheduler() exists to provide.
"""
import sqlite3
import uuid

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from routes.v1 import api_v1_bp
from scheduler import WIB


def _seed_job_status(db_path, **overrides):
    from engine.job_status import ensure_job_status_table

    defaults = dict(
        run_id=None, job_name="job_a", run_type="scheduled",
        started_at="2026-08-01 09:00:00", completed_at="2026-08-01 09:00:01",
        duration_ms=1000, status="success", records_processed=None,
        telegram_sent=0, error_message=None, retry_count=0, engine_version="abc123",
    )
    defaults.update(overrides)
    if defaults["run_id"] is None:
        defaults["run_id"] = uuid.uuid4().hex

    conn = sqlite3.connect(db_path)
    ensure_job_status_table(conn)
    conn.execute(
        "INSERT INTO job_execution_log (run_id, job_name, run_type, started_at, "
        "completed_at, duration_ms, status, records_processed, telegram_sent, "
        "error_message, retry_count, engine_version) VALUES "
        "(:run_id,:job_name,:run_type,:started_at,:completed_at,:duration_ms,"
        ":status,:records_processed,:telegram_sent,:error_message,:retry_count,"
        ":engine_version)",
        defaults,
    )
    conn.commit()
    conn.close()


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    sqlite3.connect(db).close()

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    sch = BackgroundScheduler(timezone=WIB)
    sch.add_job(lambda: None, CronTrigger(hour=9, timezone=WIB), id="job_a", name="Job A")
    sch.add_job(lambda: None, CronTrigger(hour=10, timezone=WIB), id="job_b", name="Job B")
    sch.start()

    import scheduler as sched_pkg
    monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: sch)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)

    yield app.test_client(), str(db)
    sch.shutdown(wait=False)


@pytest.fixture
def client(env):
    c, _ = env
    return c


@pytest.fixture
def unavailable_client(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    sqlite3.connect(db).close()
    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    import scheduler as sched_pkg
    monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: None)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestSchedulerStatus:
    def test_reports_running_state_and_job_count(self, client):
        resp = client.get("/api/v1/scheduler")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["available"] is True
        assert data["state"] == "running"
        assert data["timezone"] == "Asia/Jakarta"
        assert data["job_count"] == 2

    def test_reports_unavailable_when_no_scheduler(self, unavailable_client):
        resp = unavailable_client.get("/api/v1/scheduler")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {
            "available": False, "state": "unavailable",
            "timezone": None, "job_count": 0,
        }


class TestSchedulerJobsList:
    def test_lists_jobs_with_trigger_and_next_run(self, client):
        resp = client.get("/api/v1/scheduler/jobs")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["count"] == 2
        by_id = {j["job_id"]: j for j in data["jobs"]}
        assert set(by_id) == {"job_a", "job_b"}
        job_a = by_id["job_a"]
        assert job_a["name"] == "Job A"
        assert "cron" in job_a["trigger"]
        assert job_a["next_run_time"] is not None
        assert job_a["paused"] is False
        assert job_a["last_run"] is None

    def test_merges_last_run_from_job_status(self, env):
        c, db = env
        _seed_job_status(db, job_name="job_a", status="success",
                          started_at="2026-08-06 09:00:00")

        resp = c.get("/api/v1/scheduler/jobs")
        by_id = {j["job_id"]: j for j in resp.get_json()["data"]["jobs"]}
        assert by_id["job_a"]["last_run"]["status"] == "success"
        assert by_id["job_a"]["last_run"]["started_at"] == "2026-08-06 09:00:00"
        assert by_id["job_b"]["last_run"] is None

    def test_paused_job_has_null_next_run_and_paused_true(self, env):
        c, db = env
        import scheduler as sched_pkg
        sched_pkg.get_scheduler().pause_job("job_b")

        resp = c.get("/api/v1/scheduler/jobs")
        by_id = {j["job_id"]: j for j in resp.get_json()["data"]["jobs"]}
        assert by_id["job_b"]["next_run_time"] is None
        assert by_id["job_b"]["paused"] is True
        assert by_id["job_a"]["paused"] is False

    def test_empty_when_scheduler_unavailable(self, unavailable_client):
        resp = unavailable_client.get("/api/v1/scheduler/jobs")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"jobs": [], "count": 0}


class TestSchedulerJobDetail:
    def test_returns_single_job(self, client):
        resp = client.get("/api/v1/scheduler/jobs/job_a")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["job_id"] == "job_a"
        assert data["name"] == "Job A"

    def test_404_for_unknown_job(self, client):
        resp = client.get("/api/v1/scheduler/jobs/does-not-exist")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "JOB_NOT_FOUND"

    def test_404_when_scheduler_unavailable(self, unavailable_client):
        resp = unavailable_client.get("/api/v1/scheduler/jobs/job_a")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "JOB_NOT_FOUND"
