"""Confirms scheduler.start_scheduler() routes every job registration through
the Production Status Registry (engine.job_status.wrap_scheduled) via a local
_add_job() helper, instead of calling scheduler.add_job() directly.

Source-inspection style, matching test_scheduler_broker_period_registration.py
and siblings -- start_scheduler() is never invoked directly in this suite (it
opens a real BackgroundScheduler and touches the production DB_PATH for
schema bootstrap)."""
import inspect

import scheduler as sched


def test_add_job_helper_exists_and_wraps_with_job_status_tracking():
    source = inspect.getsource(sched)
    assert "def _add_job(scheduler, func, trigger, **kwargs):" in source
    assert "wrap_scheduled" in source


def test_start_scheduler_uses_add_job_helper_not_raw_scheduler_add_job():
    source = inspect.getsource(sched.start_scheduler)
    assert "scheduler.add_job(" not in source
    assert source.count("_add_job(scheduler, ") >= 20


def test_start_scheduler_still_uses_add_listener_directly():
    """add_listener is a different APScheduler API (not a job registration)
    and must NOT be routed through _add_job."""
    source = inspect.getsource(sched.start_scheduler)
    assert "scheduler.add_listener(" in source


def test_add_job_helper_derives_job_name_from_id_kwarg(monkeypatch):
    from unittest.mock import MagicMock
    from apscheduler.triggers.cron import CronTrigger

    wrapped_calls = []

    def _spy_wrap(func, job_name, run_type="scheduled", db_path=None):
        wrapped_calls.append((job_name, run_type))
        return func

    monkeypatch.setattr(sched, "wrap_scheduled", _spy_wrap)
    fake_scheduler = MagicMock()

    def _dummy():
        pass

    sched._add_job(fake_scheduler, _dummy, CronTrigger(hour=1), id="my_job_id")

    assert wrapped_calls == [("my_job_id", "scheduled")]
    fake_scheduler.add_job.assert_called_once()
