"""Confirms scheduler.start_scheduler() registers run_corporate_actions_fetch
on a daily (Mon-Fri) cadence. Source-inspection style — see
test_scheduler_broker_period_registration.py for why (start_scheduler() is
never invoked directly anywhere in this suite)."""
import inspect

import scheduler as sched
import scheduler.jobs as jobs


def test_run_corporate_actions_fetch_is_reexported():
    assert sched.run_corporate_actions_fetch is jobs.run_corporate_actions_fetch


def test_start_scheduler_registers_corporate_actions_job():
    source = inspect.getsource(sched.start_scheduler)
    assert "run_corporate_actions_fetch" in source
    assert ('"corporate_actions_fetch"' in source
           or "'corporate_actions_fetch'" in source)


def test_registration_uses_existing_add_job_cron_trigger_path():
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_corporate_actions_fetch")
    window = source[max(0, idx - 200):idx + 250]
    assert "add_job" in window
    assert "CronTrigger" in window


def test_registration_is_daily_not_weekly():
    """Cadence requirement (opposite of broker_period_summary): corporate
    actions are discrete, time-sensitive catalysts, so this job must run
    Mon-Fri, not be scoped to a single day of the week."""
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_corporate_actions_fetch")
    window = source[max(0, idx - 400):idx + 400]
    assert 'day_of_week="mon-fri"' in window
