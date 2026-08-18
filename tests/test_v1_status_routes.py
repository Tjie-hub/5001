"""Tests for routes/v1/status.py -- the Production Status Registry migrated
onto the API v1 envelope (Production Engine Phase 2, Workstream A Task 1).

Ports the coverage from tests/test_status_routes.py (deleted once
routes/status.py is removed in Task 6) onto the new /api/v1/status/* paths
and the standard ok()/ApiError envelope. Unlike the old fixture, DB_PATH is
swapped via monkeypatching the `config` module attribute directly (not
env + module reload) -- api_v1_bp is a shared singleton blueprint across
routes/v1/*.py, so reloading routes.v1.status per test would re-decorate the
same long-lived blueprint object and register duplicate routes.
"""
import sqlite3
import uuid

import pytest


def _seed(db_path, **overrides):
    """Insert one job_execution_log row exactly as engine.job_status.ensure_
    job_status_table's schema expects."""
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
def client(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    sqlite3.connect(db).close()  # file must exist; schema created lazily per-call

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    from flask import Flask
    from routes.v1 import api_v1_bp
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client(), str(db)


class TestJobsRunning:
    def test_returns_running_jobs(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="running", completed_at=None)
        _seed(db, job_name="job_b", status="success")

        resp = c.get("/api/v1/status/jobs/running")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert [j["job_name"] for j in data["running"]] == ["job_a"]
        assert data["count"] == 1

    def test_empty_when_none_running(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")

        resp = c.get("/api/v1/status/jobs/running")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["running"] == []
        assert data["count"] == 0

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/jobs/running")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"running": [], "count": 0}


class TestJobsLatest:
    def test_returns_latest_per_job(self, client):
        c, db = client
        _seed(db, job_name="job_a", started_at="2026-08-01 09:00:00")
        _seed(db, job_name="job_a", started_at="2026-08-02 09:00:00")
        _seed(db, job_name="job_b", started_at="2026-08-01 10:00:00")

        resp = c.get("/api/v1/status/jobs/latest")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        by_job = {j["job_name"]: j["started_at"] for j in data["jobs"]}
        assert by_job == {"job_a": "2026-08-02 09:00:00", "job_b": "2026-08-01 10:00:00"}

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/jobs/latest")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"jobs": []}


class TestJobsFailed:
    def test_returns_failed_jobs(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="failed", error_message="boom")
        _seed(db, job_name="job_b", status="success")

        resp = c.get("/api/v1/status/jobs/failed")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert [j["job_name"] for j in data["failed"]] == ["job_a"]
        assert data["failed"][0]["error_message"] == "boom"

    def test_since_filter(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="failed", started_at="2026-08-01 09:00:00")
        _seed(db, job_name="job_b", status="failed", started_at="2026-08-03 09:00:00")

        resp = c.get("/api/v1/status/jobs/failed?since=2026-08-02+00:00:00")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert [j["job_name"] for j in data["failed"]] == ["job_b"]

    def test_empty_when_none_failed(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")

        resp = c.get("/api/v1/status/jobs/failed")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"failed": []}


class TestJobsHistory:
    def test_returns_recent_history_default_limit(self, client):
        c, db = client
        for i in range(5):
            _seed(db, job_name=f"job_{i}", started_at=f"2026-08-0{i+1} 09:00:00")

        resp = c.get("/api/v1/status/jobs/history")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["history"]) == 5
        assert data["history"][0]["job_name"] == "job_4"  # newest first

    def test_respects_limit_param(self, client):
        c, db = client
        for i in range(5):
            _seed(db, job_name=f"job_{i}", started_at=f"2026-08-0{i+1} 09:00:00")

        resp = c.get("/api/v1/status/jobs/history?limit=2")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["history"]) == 2
        assert data["history"][0]["job_name"] == "job_4"

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/jobs/history")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"history": []}

    def test_job_name_filter(self, client):
        c, db = client
        _seed(db, job_name="job_a", started_at="2026-08-01 09:00:00")
        _seed(db, job_name="job_b", started_at="2026-08-02 09:00:00")
        _seed(db, job_name="job_a", started_at="2026-08-03 09:00:00")

        resp = c.get("/api/v1/status/jobs/history?job_name=job_a")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["history"]) == 2
        assert all(j["job_name"] == "job_a" for j in data["history"])

    def test_malformed_limit_returns_400_error_envelope(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/jobs/history?limit=not-a-number")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "INVALID_LIMIT"

    def test_negative_limit_returns_400_error_envelope(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/jobs/history?limit=-5")
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_LIMIT"


class TestSummary:
    def test_returns_counts_by_status(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")
        _seed(db, job_name="job_b", status="failed")
        _seed(db, job_name="job_c", status="skipped")
        _seed(db, job_name="job_d", status="running", completed_at=None)

        resp = c.get("/api/v1/status/summary")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {
            "total": 4, "success": 1, "failed": 1, "skipped": 1, "running": 1,
        }

    def test_empty_database_all_zero(self, client):
        c, _ = client
        resp = c.get("/api/v1/status/summary")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {
            "total": 0, "success": 0, "failed": 0, "skipped": 0, "running": 0,
        }


class TestResponseShape:
    def test_no_internal_db_fields_leaked(self, client):
        """Response must not expose the raw autoincrement `id` primary key --
        run_id is the public identifier."""
        c, db = client
        _seed(db, job_name="job_a")

        resp = c.get("/api/v1/status/jobs/history")
        row = resp.get_json()["data"]["history"][0]
        assert "id" not in row
        assert row["run_id"]
        assert row["job_name"] == "job_a"

    def test_every_response_carries_v1_meta(self, client):
        c, db = client
        _seed(db, job_name="job_a")

        resp = c.get("/api/v1/status/summary")
        meta = resp.get_json()["meta"]
        assert meta["api_version"] == "v1"
        assert "request_id" in meta
        assert "timestamp" in meta
