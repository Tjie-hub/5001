"""Keep the test suite out of the real log files.

Why (2026-09-23): tests/test_auto_token.py appended ~54 fake "Token refreshed (len=86 ...)" lines
to the real logs/auto_token.log on every suite run, which made the 2026-09-21/22 token-revocation
forensics ambiguous. The tools/backfill_* tests did the same to the repo-root backfill_*.log
files, and importing app.py (setup_logging() at import) attached a handler to the real
logs/app.log, so every log line emitted during the suite landed in production's app log.
"""
import logging
import sys
import tempfile

import pytest

# Module-level log paths written at call time: (module, attribute).
_LOG_PATH_ATTRS = [
    ("auto_token", "LOG_FILE"),
    ("tools.backfill_broker_flow_idx80", "LOG_PATH"),
    ("tools.backfill_foreign_flow_idx80", "LOG_PATH"),
    ("tools.backfill_broker_flow_full_universe", "LOG_PATH"),
    ("tools.backfill_flow_bars", "LOG_PATH"),
    ("tools.backfill_broker_flow_gap", "LOG_PATH"),
]


def pytest_configure(config):
    # Must run before any test module imports app.py, which calls setup_logging() at import
    # with the default log_dir='logs'. Explicit log_dir arguments are left untouched.
    import utils.logging_config as lc
    test_log_dir = tempfile.mkdtemp(prefix="idx-test-logs-")
    orig = lc.setup_logging

    def _setup_logging(log_dir: str = None, level: int = logging.INFO) -> None:
        return orig(log_dir or test_log_dir, level)

    lc.setup_logging = _setup_logging


@pytest.fixture(autouse=True)
def _redirect_module_log_files(tmp_path, monkeypatch):
    # Only modules already imported. Every test that exercises one imports it at module level
    # (collection time), so it is in sys.modules here. Importing them eagerly instead is worse:
    # auto_token runs load_dotenv(.env) at import, putting real secrets into every test's env.
    # A test that imports one of these inside its body and writes a log is NOT redirected.
    for mod_name, attr in _LOG_PATH_ATTRS:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, attr):
            monkeypatch.setattr(mod, attr, tmp_path / f"{mod_name.rsplit('.', 1)[-1]}.log")
