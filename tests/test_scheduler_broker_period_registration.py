"""Confirms scheduler.start_scheduler() registers run_broker_period_summary_fetch
on a weekly (Friday-only) cadence. Source-inspection style — see
test_scheduler_stockbit_screener_registration.py for why (start_scheduler()
is never invoked directly anywhere in this suite; it opens a real
BackgroundScheduler and touches the production DB_PATH for schema
bootstrap — every existing app-level test stubs it out entirely instead).
"""
import inspect

import scheduler as sched
import scheduler.jobs as jobs


def test_run_broker_period_summary_fetch_is_reexported():
    assert sched.run_broker_period_summary_fetch is jobs.run_broker_period_summary_fetch


def test_start_scheduler_registers_broker_period_summary_job():
    source = inspect.getsource(sched.start_scheduler)
    assert "run_broker_period_summary_fetch" in source
    assert ('"broker_period_summary_fetch"' in source
           or "'broker_period_summary_fetch'" in source)


def test_registration_uses_existing_add_job_cron_trigger_path():
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_broker_period_summary_fetch")
    window = source[max(0, idx - 200):idx + 250]
    assert "add_job" in window
    assert "CronTrigger" in window


def test_registration_is_weekly_not_daily():
    """Cadence requirement: this job must NOT run Mon-Fri like broker_flow —
    it should be scoped to a single day of the week (see the job's own
    docstring for the reasoning: a rolling accumulation window barely moves
    day to day, so a daily refetch would be mostly duplicate work)."""
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_broker_period_summary_fetch")
    window = source[max(0, idx - 400):idx + 400]
    assert 'day_of_week="mon-fri"' not in window
