"""Confirms app.py's init_runtime() ensures the new
stockbit_screener_results table exists at process start — same pattern as
init_flow_db()/init_screener_tables()/init_paper_table(), all called from the
same function. Source-inspection style (see
test_scheduler_stockbit_screener_registration.py for why: init_runtime()
starts a real APScheduler + Telegram poller thread, so no existing test
invokes it directly either).
"""
import inspect

import app


def test_app_imports_the_new_table_init_function():
    assert hasattr(app, "init_stockbit_screener_table")


def test_init_runtime_calls_it():
    source = inspect.getsource(app.init_runtime)
    assert "init_stockbit_screener_table" in source
