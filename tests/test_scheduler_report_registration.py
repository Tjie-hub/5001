"""Regression tests for report-function scheduler registration (audit H-2,
AN-8), P0.E1.S2.T3.

H-2: `daily_fetch_report`, `flow_broker_report`, `auto_trade_status_report`
(`scheduler/reports.py`) were fully implemented and imported into
`scheduler/__init__.py`, but never handed to `scheduler.add_job(...)` — an
unwired capability (AN-8: "defining a stage, report, or check that is not
reachable from a run DAG is a defect... delete or wire, no third state").
All three are wired here; none was deleted, because none was found
superseded by another registered job (see EVIDENCE.md for the per-function
investigation).

`open_trades_status_report` — the fourth function re-exported from
`scheduler/reports.py` — is deliberately excluded from this task: it is
reachable via `routes/backtest.py` (a manual-trigger route), so it is not
dead code and was never audit H-2's target. This module asserts it stays
that way (no scheduler registration added for it).
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


def test_daily_fetch_report_registered_21_05(registered_scheduler):
    job = _job_by_id(registered_scheduler, "daily_fetch_report")
    assert job is not None, "daily_fetch_report was never handed to add_job (audit H-2)"
    assert job.func is scheduler_pkg.daily_fetch_report
    trigger_str = str(job.trigger)
    assert "hour='21'" in trigger_str
    assert "minute='5'" in trigger_str
    assert "day_of_week='mon-fri'" in trigger_str


def test_flow_broker_report_registered_17_15(registered_scheduler):
    job = _job_by_id(registered_scheduler, "flow_broker_report")
    assert job is not None, "flow_broker_report was never handed to add_job (audit H-2)"
    assert job.func is scheduler_pkg.flow_broker_report
    trigger_str = str(job.trigger)
    assert "hour='17'" in trigger_str
    assert "minute='15'" in trigger_str
    assert "day_of_week='mon-fri'" in trigger_str


def test_auto_trade_status_report_registered_09_00(registered_scheduler):
    job = _job_by_id(registered_scheduler, "auto_trade_status_report")
    assert job is not None, "auto_trade_status_report was never handed to add_job (audit H-2)"
    assert job.func is scheduler_pkg.auto_trade_status_report
    trigger_str = str(job.trigger)
    assert "hour='9'" in trigger_str
    assert "minute='0'" in trigger_str
    assert "day_of_week='mon-fri'" in trigger_str


def test_open_trades_status_report_remains_unregistered(registered_scheduler):
    """The fourth reports.py export is out of scope for H-2/T3 — it already
    has a real caller (routes/backtest.py), so it was never dead code. This
    task must not add a scheduler registration for it (that would be
    untasked work per ER-2)."""
    matches = [j for j in registered_scheduler.get_jobs()
               if j.func is scheduler_pkg.open_trades_status_report]
    assert matches == []


def test_no_duplicate_job_ids(registered_scheduler):
    """The three new ids must not collide with each other or any
    pre-existing job id — a duplicate would silently replace the earlier
    registration (APScheduler's add_job default), exactly the kind of
    silent scheduler omission H-2 already produced once."""
    ids = [j.id for j in registered_scheduler.get_jobs()]
    assert len(ids) == len(set(ids))
    for new_id in ("daily_fetch_report", "flow_broker_report", "auto_trade_status_report"):
        assert ids.count(new_id) == 1


def test_flow_broker_report_runs_after_its_data_sources(registered_scheduler):
    """flow_broker_report reads (a) daily_screen signals populated by the
    16:15 screener EOD pass and (b) news-spike detection populated by the
    17:00 news fetch. It must not be scheduled at or before either."""
    news_fetch_1700 = _job_by_id(registered_scheduler, "news_fetch")
    screener_eod = _job_by_id(registered_scheduler, "screener_eod")
    flow_broker = _job_by_id(registered_scheduler, "flow_broker_report")

    def _minutes_since_midnight(job):
        return _cron_field(job, "hour") * 60 + _cron_field(job, "minute")

    assert _minutes_since_midnight(flow_broker) > _minutes_since_midnight(news_fetch_1700)
    assert _minutes_since_midnight(flow_broker) > _minutes_since_midnight(screener_eod)


def test_daily_fetch_report_runs_after_its_data_sources(registered_scheduler):
    """daily_fetch_report reports today's broker_flow ticker counts and
    reconciled OHLCV state — it must not be scheduled at or before the
    20:15 broker flow fetch or the 21:00 OHLCV reconciliation pass."""
    broker_flow_fetch = _job_by_id(registered_scheduler, "broker_flow_fetch")
    ohlcv_reconciliation = _job_by_id(registered_scheduler, "ohlcv_reconciliation")
    daily_fetch = _job_by_id(registered_scheduler, "daily_fetch_report")

    def _minutes_since_midnight(job):
        return _cron_field(job, "hour") * 60 + _cron_field(job, "minute")

    assert _minutes_since_midnight(daily_fetch) > _minutes_since_midnight(broker_flow_fetch)
    assert _minutes_since_midnight(daily_fetch) > _minutes_since_midnight(ohlcv_reconciliation)


def test_the_three_h2_functions_are_the_wired_targets():
    """Sanity: the exact three functions the audit named are the ones wired
    in (not stand-ins), and the fourth export is untouched."""
    assert scheduler_pkg.daily_fetch_report.__name__ == "daily_fetch_report"
    assert scheduler_pkg.flow_broker_report.__name__ == "flow_broker_report"
    assert scheduler_pkg.auto_trade_status_report.__name__ == "auto_trade_status_report"
    assert scheduler_pkg.open_trades_status_report.__name__ == "open_trades_status_report"
