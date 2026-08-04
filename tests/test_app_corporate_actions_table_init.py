"""Confirms app.py's init_runtime() ensures the new corporate_action_events
table exists at process start — same pattern as init_broker_period_summary_
table()/init_stockbit_screener_table(). Source-inspection style (see
test_app_broker_period_table_init.py for why)."""
import inspect

import app


def test_app_imports_the_new_table_init_function():
    assert hasattr(app, "init_corporate_action_events_table")


def test_init_runtime_calls_it():
    source = inspect.getsource(app.init_runtime)
    assert "init_corporate_action_events_table" in source
