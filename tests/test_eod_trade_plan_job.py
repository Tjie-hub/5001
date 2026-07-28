"""Tests for the EOD trade plan job's dedup guard (16:40 WIB job, scheduler.jobs).

Only covers the dedup-guard lock-handling path — the message-building logic
lives in engine.trade_plan and is covered by tests/test_trade_plan.py. Mirrors
tests/test_premarket_firm_scan.py::test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock
(RC1 F-3, 2026-07-28): run_eod_trade_plan's dedup insert now fails open on
sqlite3.OperationalError the same way run_premarket_firm_scan's does.
"""
import sqlite3


class _LockedSentinelConn:
    """Fake db_connect() return whose dedup-guard INSERT always finds the DB locked.

    Mirrors a real write-contention window (e.g. a long EOD write on the WAL db)
    outlasting the connection's busy_timeout. Identical to the fixture in
    tests/test_premarket_firm_scan.py, duplicated locally to keep this file
    independent of that one.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("INSERT"):
            raise sqlite3.OperationalError("database is locked")
        return None


def test_run_eod_trade_plan_fails_open_on_sentinel_db_lock(monkeypatch, caplog):
    """A locked DB on the dedup-guard insert must degrade the job, not crash it.

    EOD's own code comment states its 16:40 slot is more exposed to write
    contention than premarket's quiet 08:35 slot (it can overlap a long EOD
    write on the 2.5GB WAL db) — before RC1 F-3 it had no OperationalError
    handler at all, unlike premarket, which was patched for this exact failure
    mode after the 2026-07-24 08:35:30 production crash.
    """
    import scheduler.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "db_connect", lambda *a, **k: _LockedSentinelConn())

    def _must_not_run(*a, **k):
        raise AssertionError(
            "gather_long_candidates ran despite the dedup guard being locked out"
        )

    monkeypatch.setattr("engine.trade_plan.gather_long_candidates", _must_not_run)

    with caplog.at_level("WARNING"):
        jobs_mod.run_eod_trade_plan()  # must not raise

    assert any("database is locked" in r.message for r in caplog.records)
