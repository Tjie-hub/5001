"""Confirms scheduler.start_scheduler() registers run_ownership_fetch on a
monthly (day-of-month, not day-of-week) cadence. Source-inspection style —
see test_scheduler_corporate_actions_registration.py for why (start_scheduler()
is never invoked directly anywhere in this suite)."""
import inspect

import scheduler as sched
import scheduler.jobs as jobs


def test_run_ownership_fetch_is_reexported():
    assert sched.run_ownership_fetch is jobs.run_ownership_fetch


def test_start_scheduler_registers_ownership_job():
    source = inspect.getsource(sched.start_scheduler)
    assert "run_ownership_fetch" in source
    assert ('"ownership_fetch"' in source or "'ownership_fetch'" in source)


def test_registration_uses_existing_add_job_cron_trigger_path():
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_ownership_fetch")
    window = source[max(0, idx - 200):idx + 250]
    assert "add_job" in window
    assert "CronTrigger" in window


def test_registration_is_monthly_not_daily_or_weekly():
    """Cadence requirement: ownership composition barely changes between
    monthly registry publications (verified empirically — see the job's own
    docstring), so this must be scoped by day-of-month, not day-of-week or
    every weekday."""
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_ownership_fetch")
    window = source[max(0, idx - 400):idx + 400]
    assert 'day_of_week="mon-fri"' not in window
    assert 'day_of_week="fri"' not in window
    assert "day=" in window  # day-of-month trigger present
