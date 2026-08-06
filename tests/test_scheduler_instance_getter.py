"""Tests for scheduler.get_scheduler() -- Production Engine Phase 2, Task
2B-1. start_scheduler() has always returned the live BackgroundScheduler,
but every caller (app.py's __main__ block, gunicorn.conf.py's
post_worker_init hook) discards the return value, so nothing else in the
process could reach it. This adds a module-level getter for it.

Never calls the real start_scheduler() -- see
tests/test_scheduler_corporate_actions_registration.py for why (it spins up
the production ~20-job cron table as a live background thread and touches
config.DB_PATH at import time); source-inspection instead, matching that
file's established style for exercising start_scheduler() safely.
"""
import inspect

import scheduler as sched


def test_get_scheduler_defaults_to_none():
    assert sched.get_scheduler() is None


def test_get_scheduler_returns_whatever_was_set():
    sentinel = object()
    try:
        sched._scheduler_instance = sentinel
        assert sched.get_scheduler() is sentinel
    finally:
        sched._scheduler_instance = None


def test_start_scheduler_stores_the_instance_it_returns_before_returning():
    source = inspect.getsource(sched.start_scheduler)
    assert "_scheduler_instance" in source
    assign_idx = source.index("_scheduler_instance =")
    return_idx = source.rindex("return scheduler")
    assert assign_idx < return_idx, (
        "must store the instance before returning it, not after"
    )
