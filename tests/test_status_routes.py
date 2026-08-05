"""Tests for routes/status.py — the Production Status Registry's HTTP API.

Read-only endpoints over engine.job_status's job_execution_log table. Follows
the same standalone-blueprint test pattern as tests/test_chart_routes.py:
temp DB + monkeypatched DB_PATH + a minimal Flask app registering only this
blueprint (no scheduler init / other blueprint side effects).
"""
import sqlite3

import pytest


def _seed(db_path, **overrides):
    """Insert one job_execution_log row exactly as engine.job_status.ensure_
    job_status_table's schema expects. Mirrors tests/engine/test_job_status.py's
    own _seed_row helper, duplicated locally to keep this file independent."""
    from engine.job_status import ensure_job_status_table

    defaults = dict(
        run_id=None, job_name="job_a", run_type="scheduled",
        started_at="2026-08-01 09:00:00", completed_at="2026-08-01 09:00:01",
        duration_ms=1000, status="success", records_processed=None,
        telegram_sent=0, error_message=None, retry_count=0, engine_version="abc123",
    )
    defaults.update(overrides)
    if defaults["run_id"] is None:
        import uuid
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

    monkeypatch.setenv("DB_PATH", str(db))
    import importlib
    import config
    importlib.reload(config)
    import engine.job_status as job_status_mod
    importlib.reload(job_status_mod)
    from routes import status as status_mod
    importlib.reload(status_mod)

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(status_mod.status_bp)
    return app.test_client(), str(db)


class TestJobsRunning:
    def test_returns_running_jobs(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="running", completed_at=None)
        _seed(db, job_name="job_b", status="success")

        resp = c.get("/api/status/jobs/running")
        assert resp.status_code == 200
        data = resp.get_json()
        assert [j["job_name"] for j in data["running"]] == ["job_a"]
        assert data["count"] == 1

    def test_empty_when_none_running(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")

        resp = c.get("/api/status/jobs/running")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["running"] == []
        assert data["count"] == 0

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/status/jobs/running")
        assert resp.status_code == 200
        assert resp.get_json() == {"running": [], "count": 0}


class TestJobsLatest:
    def test_returns_latest_per_job(self, client):
        c, db = client
        _seed(db, job_name="job_a", started_at="2026-08-01 09:00:00")
        _seed(db, job_name="job_a", started_at="2026-08-02 09:00:00")
        _seed(db, job_name="job_b", started_at="2026-08-01 10:00:00")

        resp = c.get("/api/status/jobs/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        by_job = {j["job_name"]: j["started_at"] for j in data["jobs"]}
        assert by_job == {"job_a": "2026-08-02 09:00:00", "job_b": "2026-08-01 10:00:00"}

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/status/jobs/latest")
        assert resp.status_code == 200
        assert resp.get_json() == {"jobs": []}


class TestJobsFailed:
    def test_returns_failed_jobs(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="failed", error_message="boom")
        _seed(db, job_name="job_b", status="success")

        resp = c.get("/api/status/jobs/failed")
        assert resp.status_code == 200
        data = resp.get_json()
        assert [j["job_name"] for j in data["failed"]] == ["job_a"]
        assert data["failed"][0]["error_message"] == "boom"

    def test_since_filter(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="failed", started_at="2026-08-01 09:00:00")
        _seed(db, job_name="job_b", status="failed", started_at="2026-08-03 09:00:00")

        resp = c.get("/api/status/jobs/failed?since=2026-08-02+00:00:00")
        assert resp.status_code == 200
        data = resp.get_json()
        assert [j["job_name"] for j in data["failed"]] == ["job_b"]

    def test_empty_when_none_failed(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")

        resp = c.get("/api/status/jobs/failed")
        assert resp.status_code == 200
        assert resp.get_json() == {"failed": []}


class TestJobsHistory:
    def test_returns_recent_history_default_limit(self, client):
        c, db = client
        for i in range(5):
            _seed(db, job_name=f"job_{i}", started_at=f"2026-08-0{i+1} 09:00:00")

        resp = c.get("/api/status/jobs/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["history"]) == 5
        # newest first
        assert data["history"][0]["job_name"] == "job_4"

    def test_respects_limit_param(self, client):
        c, db = client
        for i in range(5):
            _seed(db, job_name=f"job_{i}", started_at=f"2026-08-0{i+1} 09:00:00")

        resp = c.get("/api/status/jobs/history?limit=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["history"]) == 2
        assert data["history"][0]["job_name"] == "job_4"

    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/status/jobs/history")
        assert resp.status_code == 200
        assert resp.get_json() == {"history": []}

    def test_malformed_limit_returns_400(self, client):
        c, _ = client
        resp = c.get("/api/status/jobs/history?limit=not-a-number")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_negative_limit_returns_400(self, client):
        c, _ = client
        resp = c.get("/api/status/jobs/history?limit=-5")
        assert resp.status_code == 400


class TestSummary:
    def test_returns_counts_by_status(self, client):
        c, db = client
        _seed(db, job_name="job_a", status="success")
        _seed(db, job_name="job_b", status="failed")
        _seed(db, job_name="job_c", status="skipped")
        _seed(db, job_name="job_d", status="running", completed_at=None)

        resp = c.get("/api/status/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {"total": 4, "success": 1, "failed": 1, "skipped": 1, "running": 1}

    def test_empty_database_all_zero(self, client):
        c, _ = client
        resp = c.get("/api/status/summary")
        assert resp.status_code == 200
        assert resp.get_json() == {"total": 0, "success": 0, "failed": 0,
                                   "skipped": 0, "running": 0}


class TestResponseShape:
    def test_no_internal_db_fields_leaked(self, client):
        """Response must not expose the raw autoincrement `id` primary key —
        run_id is the public identifier."""
        c, db = client
        _seed(db, job_name="job_a")

        resp = c.get("/api/status/jobs/history")
        row = resp.get_json()["history"][0]
        assert "id" not in row
        assert row["run_id"]
        assert row["job_name"] == "job_a"
