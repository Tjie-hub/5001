"""Confirms scheduler.start_scheduler() actually registers
run_stockbit_screener_fetch — i.e. "the scheduler discovers the job".

start_scheduler() is never invoked directly in this test suite anywhere
(it opens a real BackgroundScheduler and touches the production DB_PATH
for schema bootstrap) — every existing app-level test stubs it out entirely
(see tests/test_api_ticker_full.py, tests/test_health_endpoint.py). This
follows the same source-inspection style already used elsewhere in the repo
for "is X wired in" checks (tests/test_cron_contract.py,
tests/test_architecture_boundary.py) rather than introducing a new pattern
that runs the real scheduler in-process.
"""
import inspect

import scheduler as sched
import scheduler.jobs as jobs


def test_run_stockbit_screener_fetch_is_reexported_from_scheduler_package():
    assert sched.run_stockbit_screener_fetch is jobs.run_stockbit_screener_fetch


def test_start_scheduler_registers_stockbit_screener_job():
    source = inspect.getsource(sched.start_scheduler)
    assert "run_stockbit_screener_fetch" in source
    assert '"stockbit_screener_fetch"' in source or "'stockbit_screener_fetch'" in source


def test_start_scheduler_registers_job_with_cron_trigger_not_a_new_mechanism():
    """Guards against introducing a parallel scheduling mechanism — the new
    job must go through the same CronTrigger/scheduler.add_job path as every
    other job in start_scheduler(), not e.g. its own thread/while-loop."""
    source = inspect.getsource(sched.start_scheduler)
    idx = source.index("run_stockbit_screener_fetch")
    window = source[max(0, idx - 200):idx + 200]
    assert "add_job" in window
    assert "CronTrigger" in window
