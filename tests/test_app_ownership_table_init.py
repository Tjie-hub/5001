"""Confirms app.py's init_runtime() ensures the new ownership_composition
table exists at process start — same pattern as init_corporate_action_events_
table()/init_broker_period_summary_table(). Source-inspection style (see
test_app_corporate_actions_table_init.py for why)."""
import inspect

import app


def test_app_imports_the_new_table_init_function():
    assert hasattr(app, "init_ownership_composition_table")


def test_init_runtime_calls_it():
    source = inspect.getsource(app.init_runtime)
    assert "init_ownership_composition_table" in source
