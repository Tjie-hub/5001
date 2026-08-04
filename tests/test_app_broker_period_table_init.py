"""Confirms app.py's init_runtime() ensures the new broker_period_summary
table exists at process start — same pattern as init_flow_db()/
init_stockbit_screener_table(). Source-inspection style — see
test_app_stockbit_screener_table_init.py for why (init_runtime() starts a
real APScheduler + Telegram poller thread; no existing test invokes it
directly)."""
import inspect

import app


def test_app_imports_the_new_table_init_function():
    assert hasattr(app, "init_broker_period_summary_table")


def test_init_runtime_calls_it():
    source = inspect.getsource(app.init_runtime)
    assert "init_broker_period_summary_table" in source
