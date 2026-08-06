"""Tests for routes/v1/health.py -- GET /api/v1/health (Production Engine
Phase 2, Workstream 2B Task 2B-4).

HTTP status is always 200 here -- the API call itself succeeded (it
computed and returned a health report); health state lives in the body
(data.overall / data.components), matching app.py's existing /health route,
which likewise never changes its HTTP status on a degraded/error result.
"""
import sqlite3

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from routes.v1 import api_v1_bp
from scheduler import WIB


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    sqlite3.connect(str(db)).close()

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    sch = BackgroundScheduler(timezone=WIB)
    sch.add_job(lambda: None, CronTrigger(hour=9, timezone=WIB), id="job_a", name="Job A")
    sch.start()
    import scheduler as sched_pkg
    monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: sch)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)

    yield app.test_client()
    sch.shutdown(wait=False)


class TestHealthEndpoint:
    def test_returns_200_with_ok_true_via_standard_envelope(self, env):
        resp = env.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["meta"]["api_version"] == "v1"

    def test_data_has_overall_and_components(self, env):
        data = env.get("/api/v1/health").get_json()["data"]
        assert data["overall"] in ("healthy", "degraded", "unavailable")
        assert set(data["components"]) == {
            "database", "scheduler", "metrics", "configuration", "release",
        }

    def test_still_returns_200_when_overall_is_unavailable(self, env, monkeypatch):
        import scheduler as sched_pkg
        monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: None)
        import config
        monkeypatch.setattr(config, "DB_PATH", "/does/not/exist.db")

        resp = env.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["data"]["overall"] == "unavailable"
