"""Tests for engine/health.py -- deterministic aggregation over the
subsystem signals already built in 2B-1 (scheduler), 2B-2 (metrics), 2B-3
(configuration), plus release_info -- Production Engine Phase 2, Workstream
2B Task 2B-4. See
docs/superpowers/specs/2026-08-06-2b4-health-api-design.md for the exact
per-component and overall rules asserted here.
"""
import sqlite3

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from engine.health import get_health
from scheduler import WIB


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "wf.db"
    sqlite3.connect(str(path)).close()
    return str(path)


@pytest.fixture
def running_scheduler(monkeypatch):
    sch = BackgroundScheduler(timezone=WIB)
    sch.add_job(lambda: None, CronTrigger(hour=9, timezone=WIB), id="job_a", name="Job A")
    sch.start()
    import scheduler as sched_pkg
    monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: sch)
    yield sch
    sch.shutdown(wait=False)


@pytest.fixture
def healthy_release(monkeypatch):
    import utils.release as release_mod
    monkeypatch.setattr(release_mod, "release_info",
                         lambda: {"version": "1.2.3", "source": "release", "git_sha": "abc1234"})


class TestAllHealthy:
    def test_overall_healthy_when_every_component_is(self, db, running_scheduler, healthy_release):
        data = get_health(db)
        assert data["overall"] == "healthy"
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["scheduler"]["status"] == "healthy"
        assert data["components"]["metrics"]["status"] == "healthy"
        assert data["components"]["configuration"]["status"] == "healthy"

    def test_release_component_has_no_status_key(self, db, running_scheduler, healthy_release):
        release = get_health(db)["components"]["release"]
        assert release["version"] == "1.2.3"
        assert release["git_sha"] == "abc1234"
        assert "status" not in release


class TestDatabaseUnavailable:
    def test_makes_overall_unavailable_even_if_everything_else_is_healthy(
        self, tmp_path, running_scheduler, healthy_release
    ):
        bad_db = str(tmp_path / "does" / "not" / "exist.db")
        data = get_health(bad_db)
        assert data["components"]["database"]["status"] == "unavailable"
        assert data["overall"] == "unavailable"


class TestSchedulerStates:
    def test_no_scheduler_is_unavailable_and_degrades_overall(self, db, healthy_release, monkeypatch):
        import scheduler as sched_pkg
        monkeypatch.setattr(sched_pkg, "get_scheduler", lambda: None)

        data = get_health(db)
        assert data["components"]["scheduler"]["status"] == "unavailable"
        assert data["overall"] == "degraded"

    def test_paused_scheduler_is_degraded_and_degrades_overall(self, db, running_scheduler, healthy_release):
        running_scheduler.pause()
        data = get_health(db)
        assert data["components"]["scheduler"]["status"] == "degraded"
        assert data["overall"] == "degraded"


class TestMetricsFailure:
    def test_metrics_exception_is_unavailable_and_degrades_overall(
        self, db, running_scheduler, healthy_release, monkeypatch
    ):
        import engine.metrics as engine_metrics_mod

        def _boom(db_path):
            raise RuntimeError("metrics db unreachable")

        monkeypatch.setattr(engine_metrics_mod, "get_engine_metrics", _boom)

        data = get_health(db)
        assert data["components"]["metrics"]["status"] == "unavailable"
        assert data["overall"] == "degraded"


class TestConfigurationFailure:
    def test_configuration_exception_is_unavailable_and_degrades_overall(
        self, db, running_scheduler, healthy_release, monkeypatch
    ):
        import engine.config_info as config_info_mod

        def _boom():
            raise RuntimeError("config unreachable")

        monkeypatch.setattr(config_info_mod, "get_config_summary", _boom)

        data = get_health(db)
        assert data["components"]["configuration"]["status"] == "unavailable"
        assert data["overall"] == "degraded"
