"""P0.E2.S2.T2 -- startup logs resolved DB path + file identity (H-7).

`data.db.log_db_identity()` positively identifies the database file in use
at startup -- not merely the configured path string -- by logging
stat-derived identity (device/inode, size, mtime) alongside the resolved
absolute path from the canonical DB_PATH resolution chain (P0.E2.S2.T1).
Pre-figures the Phase 1 Certifier DB-identity check (PLAN-001 P1.E4.S1);
this task is intentionally just the log line, not that check.
"""
import importlib
import inspect
import logging

import config
import data.db as data_db


def test_log_db_identity_when_db_exists(tmp_path, caplog):
    db_file = tmp_path / "wf.db"
    db_file.write_bytes(b"sqlite-fake-content")

    with caplog.at_level(logging.INFO, logger="data.db"):
        data_db.log_db_identity(str(db_file))

    records = [r for r in caplog.records if r.name == "data.db"]
    assert len(records) == 1
    r = records[0]
    assert r.db_path == str(db_file)
    assert r.db_exists is True
    assert r.db_size_bytes == len(b"sqlite-fake-content")
    assert isinstance(r.db_mtime, str) and r.db_mtime  # ISO-8601 UTC timestamp
    assert hasattr(r, "db_dev")
    assert hasattr(r, "db_ino")


def test_log_db_identity_when_db_missing(tmp_path, caplog):
    missing = tmp_path / "does_not_exist.db"

    with caplog.at_level(logging.INFO, logger="data.db"):
        data_db.log_db_identity(str(missing))

    records = [r for r in caplog.records if r.name == "data.db"]
    assert len(records) == 1
    r = records[0]
    assert r.db_path == str(missing)
    assert r.db_exists is False
    assert not hasattr(r, "db_size_bytes")
    assert not hasattr(r, "db_dev")


def test_log_db_identity_defaults_to_module_db_path(tmp_path, monkeypatch, caplog):
    """No path argument -> uses data.db.DB_PATH, the already-resolved
    canonical value -- proves no second/duplicate path resolution."""
    db_file = tmp_path / "default.db"
    db_file.write_bytes(b"x")
    monkeypatch.setattr(data_db, "DB_PATH", str(db_file))

    with caplog.at_level(logging.INFO, logger="data.db"):
        data_db.log_db_identity()

    records = [r for r in caplog.records if r.name == "data.db"]
    assert records[0].db_path == str(db_file)


def test_log_db_identity_reflects_env_resolved_db_path(monkeypatch, tmp_path, caplog):
    """DB_PATH sourced from the env var (mirroring .env's own
    DB_PATH=data/walkforward.db) reaches log_db_identity via the
    canonical resolve_db_path() chain from P0.E2.S2.T1 -- not a second,
    independent computation in this module."""
    db_file = tmp_path / "env.db"
    db_file.write_bytes(b"y")
    monkeypatch.setenv("DB_PATH", str(db_file))
    importlib.reload(config)
    importlib.reload(data_db)
    try:
        with caplog.at_level(logging.INFO, logger="data.db"):
            data_db.log_db_identity()
        records = [r for r in caplog.records if r.name == "data.db"]
        assert records[0].db_path == str(db_file)
        assert records[0].db_exists is True
    finally:
        importlib.reload(config)
        importlib.reload(data_db)


def test_log_db_identity_resolves_relative_env_value_absolute(monkeypatch, caplog):
    """Root-cause regression guard shared with P0.E2.S2.T1: a relative
    DB_PATH env value (this repo's real .env ships one) must still reach
    log_db_identity() as an absolute path, proving no bypass of
    resolve_db_path() anywhere in this call chain."""
    import pathlib
    monkeypatch.setenv("DB_PATH", "data/walkforward.db")
    importlib.reload(config)
    importlib.reload(data_db)
    try:
        with caplog.at_level(logging.INFO, logger="data.db"):
            data_db.log_db_identity()
        records = [r for r in caplog.records if r.name == "data.db"]
        assert pathlib.Path(records[0].db_path).is_absolute()
    finally:
        importlib.reload(config)
        importlib.reload(data_db)


def test_app_startup_calls_log_db_identity_exactly_once_inside_main_guard():
    """Static source check (no Flask app / scheduler actually started --
    app.run() blocks and scheduler/telegram side effects are out of this
    task's scope to mock): log_db_identity() is called exactly once in
    app.py, and only inside the `if __name__ == "__main__":` guard --
    never at module level (which would fire on every import/test
    reload, e.g. test_health_endpoint.py's importlib.reload(app_module))
    and never more than once (the task's own 'not repeatedly' requirement)."""
    import app as app_module
    source = inspect.getsource(app_module)

    call_count = source.count("log_db_identity()")
    assert call_count == 1, f"expected exactly 1 call to log_db_identity(), found {call_count}"

    main_guard_idx = source.index('if __name__ == "__main__":')
    call_idx = source.index("log_db_identity()")
    assert call_idx > main_guard_idx, (
        "log_db_identity() must be called inside the __main__ guard, not at module level"
    )
