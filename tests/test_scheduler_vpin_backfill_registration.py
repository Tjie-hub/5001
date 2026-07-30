"""Regression test for run_vpin_backfill scheduler registration (DEBT-003,
new AN-8 finding surfaced by P0.E1.S2.T4; dispositioned by P0.E1.S2.T6).

run_vpin_backfill(days=90) was fully implemented and imported into
scheduler/__init__.py, but never handed to scheduler.add_job(...) — an
unwired capability. Unlike run_foreign_snapshot (P0.E1.S2.T2, deleted as
superseded), this function is not superseded by anything: it heals gaps
in vpin_scores from prior-day failures, complementing (not duplicating)
the daily run_vpin_daily_batch, which only ever covers "today". It is
idempotent (skips dates already fully scored for every ticker), so a
daily schedule costs almost nothing when there is nothing to heal —
disposition is register, not delete, following the same daily cadence
already used by this codebase's other reconciliation-style jobs
(run_ohlcv_reconciliation, run_ohlcv_coverage_check).
"""
import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import scheduler as scheduler_pkg


@pytest.fixture
def registered_scheduler(monkeypatch):
    """start_scheduler() with every non-job-registration side effect
    (schema init, watchlist init, registry announce, actually starting
    background threads) neutralized, so only add_job calls run."""
    monkeypatch.setattr(BackgroundScheduler, "start", lambda self: None)
    monkeypatch.setattr("engine.watchlist.ensure_table", lambda *a, **k: None)
    monkeypatch.setattr("data.market_schema.ensure_market_data_schema", lambda *a, **k: None)
    monkeypatch.setattr("engine.registry_loader.announce_registry", lambda *a, **k: None)
    return scheduler_pkg.start_scheduler()


def _job_by_id(sched, job_id):
    return sched.get_job(job_id)


def _cron_field(job, name):
    field = next(f for f in job.trigger.fields if f.name == name)
    return field.expressions[0].first


def test_vpin_backfill_registered_18_15(registered_scheduler):
    job = _job_by_id(registered_scheduler, "vpin_backfill")
    assert job is not None, "run_vpin_backfill was never handed to add_job (AN-8/DEBT-003)"
    assert job.func is scheduler_pkg.run_vpin_backfill
    trigger_str = str(job.trigger)
    assert "hour='18'" in trigger_str
    assert "minute='15'" in trigger_str
    assert "day_of_week='mon-fri'" in trigger_str


def test_vpin_backfill_runs_after_vpin_daily_batch(registered_scheduler):
    """The backfill heals gaps the daily batch may have left; it must run
    after, not before or concurrently with, its own data source."""
    daily_batch = _job_by_id(registered_scheduler, "vpin_daily_batch")
    backfill = _job_by_id(registered_scheduler, "vpin_backfill")

    def _minutes_since_midnight(job):
        return _cron_field(job, "hour") * 60 + _cron_field(job, "minute")

    assert _minutes_since_midnight(backfill) > _minutes_since_midnight(daily_batch)


def test_vpin_backfill_job_id_unique(registered_scheduler):
    ids = [j.id for j in registered_scheduler.get_jobs()]
    assert ids.count("vpin_backfill") == 1
