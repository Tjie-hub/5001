"""Tests for routes/v1/metrics.py -- /api/v1/metrics, /metrics/jobs,
/metrics/engine (Production Engine Phase 2, Workstream 2B Task 2B-2).

Never touches the real scheduler.start_scheduler() (see
tests/test_scheduler_instance_getter.py); the rollup's scheduler slice is
exercised against a throwaway BackgroundScheduler, same as
tests/test_v1_scheduler_routes.py.
"""
import sqlite3
import uuid

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from routes.v1 import api_v1_bp
from scheduler import WIB


def _make_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE paper_trades (status TEXT);
        CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT);
        CREATE TABLE agent_decisions (scan_time TEXT);
        CREATE TABLE ohlcv (ticker TEXT, date TEXT);
        CREATE TABLE market_risk_log (score REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE daily_screen (date TEXT, ticker TEXT, vpin REAL);
    """)
    conn.commit()
    conn.close()


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
    _make_db(str(db))

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

    yield app.test_client(), str(db)
    sch.shutdown(wait=False)


@pytest.fixture
def client(env):
    c, _ = env
    return c


class TestMetricsJobs:
    def test_returns_job_status_summary_shape(self, client, env):
        _, db = env
        _seed_job_status(db, job_name="job_a", status="success")
        _seed_job_status(db, job_name="job_b", status="failed")

        resp = client.get("/api/v1/metrics/jobs")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        # 2026-10-06 orphan split: 'running' counts live runs only, 'orphaned'
        # counts restart strays (zero here — no running rows seeded).
        assert data == {"total": 2, "success": 1, "failed": 1, "skipped": 0,
                        "running": 0, "orphaned": 0}


class TestMetricsEngine:
    def test_returns_engine_metrics(self, env):
        c, db = env
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO paper_trades VALUES ('OPEN')")
        conn.commit()
        conn.close()

        resp = c.get("/api/v1/metrics/engine")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["open_trades"] == 1
        assert "signals_today_total" in data
        assert "market_risk_score" in data

    def test_subsystem_failure_returns_standard_500_envelope(self, client, monkeypatch):
        import engine.metrics as engine_metrics_mod

        def _boom(db_path):
            raise RuntimeError("db unreachable")

        monkeypatch.setattr(engine_metrics_mod, "get_engine_metrics", _boom)

        resp = client.get("/api/v1/metrics/engine")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "db unreachable" not in data["error"]["message"]


class TestMetricsRollup:
    def test_combines_jobs_engine_and_scheduler(self, env):
        c, db = env
        _seed_job_status(db, job_name="job_a", status="success")

        resp = c.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["jobs"]["total"] == 1
        assert "open_trades" in data["engine"]
        assert data["scheduler"] == {"available": True, "job_count": 1}

    def test_scheduler_unavailable_in_rollup(self, client, monkeypatch):
        import scheduler as sched_pkg
        monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: None)

        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["scheduler"] == {"available": False, "job_count": 0}
