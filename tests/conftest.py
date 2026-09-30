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
from pathlib import Path

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


# --- Real-database isolation (2026-09-30) --------------------------------
# Root conftest.py pins DB_PATH for the whole process, which covers the
# `from config import DB_PATH` bindings that ~20 modules freeze at import
# time. This adds the per-test layer: the two call-time resolvers --
# os.getenv("DB_PATH", ...) (security/audit_trail.py:32) and config.DB_PATH
# -- are re-pointed at a per-test scratch file, and every test is wrapped
# with a snapshot of the repo's real data/ directory (which is also a Python
# package) so a test that creates or modifies a database there fails naming
# the file.
_REPO_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DB_FILE_SUFFIXES = (".db", ".db-wal", ".db-shm", ".db-journal")

# Modules that bypass config/env with their own module-level DB path computed
# from __file__ (news_filter.py:28 does exactly this). Same shape and same
# caveat as _LOG_PATH_ATTRS above: only modules already imported at collection
# time are redirected; the per-test data/ snapshot catches any others.
_DB_PATH_ATTRS = [
    ("news_filter", "_DB_PATH"),
]


def _real_db_files() -> set:
    if not _REPO_DATA_DIR.is_dir():
        return set()
    found = set()
    for p in _REPO_DATA_DIR.iterdir():
        if p.is_file() and p.name.endswith(_DB_FILE_SUFFIXES):
            st = p.stat()
            found.add((p.name, st.st_size, st.st_mtime_ns))
    return found


# Snapshot at conftest import = before any test module runs, so a
# pre-existing real database (a dev checkout's data/walkforward.db) never
# trips the guard; only files the suite itself created or modified do.
_SESSION_START_DB_FILES = _real_db_files()


@pytest.fixture(autouse=True)
def _isolate_db_path(tmp_path, monkeypatch):
    import config as config_module

    scratch = tmp_path / "test_walkforward.db"
    monkeypatch.setenv("DB_PATH", str(scratch))
    monkeypatch.setattr(config_module, "DB_PATH", str(scratch), raising=False)
    for mod_name, attr in _DB_PATH_ATTRS:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, attr):
            monkeypatch.setattr(mod, attr, str(scratch))
    before = _real_db_files()
    yield
    offenders = _real_db_files() - before
    assert not offenders, (
        f"this test created/modified real database file(s) under {_REPO_DATA_DIR}: "
        f"{sorted(name for name, _, _ in offenders)}; route DB writes through "
        "db_path=/tmp_path instead (see _isolate_db_path in tests/conftest.py)")


def pytest_sessionfinish(session, exitstatus):
    """Session-level sweep: the run FAILS (nonzero exit status) if anything
    created or modified a database under the repo's real data/ directory.

    Compares against _SESSION_START_DB_FILES (snapshotted at conftest import,
    before any test module runs), so it also catches writes the per-test
    wrapper cannot attribute -- import-time side effects between tests,
    collection-time activity, or writes from code that ignores DB_PATH
    entirely. Supported way to fail the session from this hook: wrap_session
    assigns session.exitstatus BEFORE this hook runs and RETURNS the same
    attribute afterwards (_pytest/main.py::wrap_session), so setting it here
    changes the status pytest returns to the shell.
    """
    offenders = _real_db_files() - _SESSION_START_DB_FILES
    if not offenders:
        return
    names = sorted(name for name, _, _ in offenders)
    sys.stderr.write(
        f"\n=== DB-ISOLATION GUARD: the session created/modified real database "
        f"file(s) under {_REPO_DATA_DIR}: {names} ===\n"
        f"=== DB writes must go through db_path=/tmp_path (see "
        f"_isolate_db_path in tests/conftest.py); failing the session. ===\n")
    session.exitstatus = pytest.ExitCode.TESTS_FAILED
