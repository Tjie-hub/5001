"""Guard: the suite must leave the repo's real data/ directory untouched.

Companion to tests/conftest.py::_isolate_db_path, which fails the individual
test that creates or modifies a database under data/. This test sweeps the
whole directory against the session-start snapshot (taken at conftest import,
before any test module runs), so it also catches writes that bypass the
per-test wrapper, e.g. import-time side effects between tests. Named
test_zz_* to run after the rest of the suite.
"""
from tests.conftest import _REPO_DATA_DIR, _SESSION_START_DB_FILES, _real_db_files


def test_suite_left_real_data_dir_untouched():
    offenders = _real_db_files() - _SESSION_START_DB_FILES
    assert not offenders, (
        f"the suite created/modified real database file(s) under {_REPO_DATA_DIR}: "
        f"{sorted(name for name, _, _ in offenders)}; DB writes must go through "
        "db_path=/tmp_path (DB_PATH is redirected in conftest.py)")
