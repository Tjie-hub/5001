"""Tests for tools/agent_backfill_foreign_flow_idx80.py -- the IDX80
foreign-flow backfill ORCHESTRATOR.

Every test runs against a temporary SQLite DB and a mocked subprocess
(except the real-subprocess concurrency-detection tests near the end).
Nothing here touches data/walkforward.db or the Stockbit vendor endpoint.
"""
import fcntl
import json
import sqlite3
import subprocess

import pytest

import tools.agent_backfill_foreign_flow_idx80 as A
# Captured before any per-test monkeypatching of A.other_backfill_pids (the
# autouse no_other_process fixture below rebinds that module attribute for
# every test by default) -- the concurrency regression tests need the REAL
# /proc-scanning implementation to mean anything.
from tools.agent_backfill_foreign_flow_idx80 import other_backfill_pids as _real_other_backfill_pids

SCHEMA = """
CREATE TABLE idx_tickers (
    ticker TEXT PRIMARY KEY, status TEXT DEFAULT "active",
    in_idx30 INTEGER DEFAULT 0, in_lq45 INTEGER DEFAULT 0,
    in_idx80 INTEGER DEFAULT 0);
CREATE TABLE ohlcv (
    ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER);
CREATE TABLE trading_calendar (
    date TEXT PRIMARY KEY, source TEXT, updated_at TEXT);
CREATE TABLE broker_flow (
    ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
    lot INTEGER, lot_value INTEGER, value INTEGER, value_total INTEGER,
    avg_price REAL, freq INTEGER, investor_type TEXT,
    PRIMARY KEY (ticker, trade_date, broker_code, side));
CREATE TABLE bandar_detector (
    ticker TEXT, trade_date TEXT, avg_price REAL, total_buyer INTEGER,
    total_seller INTEGER, net_broker_count INTEGER, broker_accdist TEXT,
    value INTEGER, volume INTEGER, top1_accdist TEXT, top3_accdist TEXT,
    top5_accdist TEXT, top10_accdist TEXT, avg_accdist TEXT, updated_at TEXT,
    PRIMARY KEY (ticker, trade_date));
"""

DATES = ["2025-01-02", "2025-01-03", "2025-01-06"]
TICKERS = ["BBCA", "BBRI"]


def _add_foreign_row(conn, ticker, date):
    conn.execute(
        "INSERT OR REPLACE INTO broker_flow "
        "(ticker,trade_date,broker_code,side,investor_type) VALUES (?,?,'ZP','BUY','Asing')",
        (ticker, date),
    )


def _add_domestic_only_row(conn, ticker, date):
    conn.execute(
        "INSERT OR REPLACE INTO broker_flow "
        "(ticker,trade_date,broker_code,side,investor_type) VALUES (?,?,'ZP','BUY','Lokal')",
        (ticker, date),
    )


def _add_empty_marker(conn, ticker, date):
    conn.execute(
        "INSERT OR REPLACE INTO bandar_detector "
        "(ticker,trade_date,value,volume) VALUES (?,?,0,0)",
        (ticker, date),
    )


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for t in TICKERS:
        conn.execute(
            "INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES (?, 'active', 1)",
            (t,),
        )
    conn.execute(
        "INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES ('NOTIDX', 'active', 0)"
    )
    for d in DATES:
        conn.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,))
    conn.commit()
    conn.close()
    return path


@pytest.fixture(autouse=True)
def no_other_process(monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", lambda *a, **k: [])


@pytest.fixture(autouse=True)
def runner_targets_the_test_db(monkeypatch, db):
    """The real runner writes to its own hardcoded DB_PATH; align it with the
    temp DB so the audit and the (mocked) run refer to the same file."""
    monkeypatch.setattr(A, "runner_db_path", lambda runner: db)


@pytest.fixture
def runner_script(tmp_path):
    """A harmless stand-in runner file for destructive-SQL scan tests --
    never actually executed (subprocess is always mocked)."""
    p = tmp_path / "fake_runner.py"
    p.write_text(
        f'DB_PATH = A_HERE / "data" / "walkforward.db"\n'
        '"""fetch_and_store_cell = B.fetch_and_store_cell"""\n'
    )
    return p


def _args(db_path, *extra, lock=None):
    args = ["--date-from", DATES[0], "--date-to", "2025-01-07", "--db", str(db_path)]
    if lock is not None:
        args += ["--lock-file", str(lock)]
    return args + list(extra)


def _run(args, capsys):
    rc = A.main(args + ["--json"])
    out = capsys.readouterr().out
    return rc, json.loads(out)


# --- universe --------------------------------------------------------------


def test_universe_is_always_idx80_no_override_flag_exists(db, capsys):
    rc, rep = _run(_args(db), capsys)
    assert rep["universe_size"] == 2  # NOTIDX excluded
    assert "--cat" not in " ".join(A.build_parser().format_help().split())


def test_universe_recomputed_from_db_not_hardcoded(db, capsys, tmp_path):
    conn = sqlite3.connect(db)
    conn.execute("UPDATE idx_tickers SET in_idx80=0 WHERE ticker='BBRI'")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db), capsys)
    assert rep["universe_size"] == 1


def test_refuses_when_universe_is_empty(db, capsys):
    conn = sqlite3.connect(db)
    conn.execute("UPDATE idx_tickers SET in_idx80=0")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db), capsys)
    assert rc == A.EXIT_BLOCKED
    names = {c["name"] for c in rep["safety_checks"] if not c["ok"]}
    assert "universe_is_idx80_and_non_empty" in names


# --- calendar ----------------------------------------------------------------


def test_non_ihsg_calendar_row_excluded_from_expected(db, capsys):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES ('2025-01-07', 'scraper_eod')")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", "2025-01-08"), capsys)
    assert rep["calendar"]["non_ihsg_dates_count"] == 1
    assert rep["calendar"]["dates_in_window"] == len(DATES)


def test_date_to_is_exclusive(db, capsys):
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    assert rep["calendar"]["dates_in_window"] == 1


def test_no_canonical_dates_in_window_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--date-from", "2030-01-01", "--date-to", "2030-01-02"), capsys)
    assert rc == A.EXIT_BLOCKED


# --- coverage ------------------------------------------------------------


def test_coverage_counts_foreign_rows_as_present(db, capsys):
    conn = sqlite3.connect(db)
    _add_foreign_row(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["foreign_present_ticker_days"] == 1
    assert cov["complete_ticker_days"] == 1


def test_coverage_counts_domestic_only_row_as_confirmed_empty_foreign_only(db, capsys):
    """A ticker-day with only Lokal broker rows is foreign-complete (the
    atomic vendor fetch already checked Asing and found nothing) -- it must
    count toward `complete`, but NOT toward `foreign_present`."""
    conn = sqlite3.connect(db)
    _add_domestic_only_row(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["foreign_present_ticker_days"] == 0
    assert cov["confirmed_empty_foreign_only_ticker_days"] == 1
    assert cov["complete_ticker_days"] == 1


def test_coverage_counts_confirmed_empty_session_marker_as_complete(db, capsys):
    conn = sqlite3.connect(db)
    _add_empty_marker(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["confirmed_empty_session_ticker_days"] == 1
    assert cov["complete_ticker_days"] == 1


def test_coverage_does_not_count_nonzero_bandar_without_broker_rows(db, capsys):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
        "VALUES ('BBCA', ?, 12345, 678)", (DATES[0],),
    )
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["complete_ticker_days"] == 0


def test_plan_status_complete_when_fully_covered(db, capsys):
    conn = sqlite3.connect(db)
    for d in DATES:
        for t in TICKERS:
            _add_foreign_row(conn, t, d)
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db), capsys)
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_plan_status_partial_when_gaps_remain(db, capsys):
    rc, rep = _run(_args(db), capsys)
    assert rep["status"] == "PARTIAL"
    assert rc == A.EXIT_PARTIAL


# --- plan is read-only -------------------------------------------------------


def test_plan_mode_makes_no_subprocess_calls(db, capsys, monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: called.append(1))
    _run(_args(db), capsys)
    assert called == []


def test_plan_mode_writes_nothing(db, capsys):
    before = db.stat().st_mtime
    _run(_args(db), capsys)
    assert db.stat().st_mtime == before


def test_execute_without_confirm_flag_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--action", "execute"), capsys)
    assert rc == A.EXIT_BLOCKED
    assert rep["vendor_calls_made"] is False


# --- safety checks ------------------------------------------------------


def test_refuses_when_db_missing(tmp_path, capsys):
    rc, rep = _run(_args(tmp_path / "nope.db"), capsys)
    assert rc == A.EXIT_BLOCKED


def test_refuses_when_runner_has_destructive_sql(db, capsys, tmp_path, monkeypatch):
    bad_runner = tmp_path / "bad_runner.py"
    bad_runner.write_text('conn.execute("DELETE FROM broker_flow")')
    rc, rep = _run(_args(db, "--runner", str(bad_runner)), capsys)
    names = {c["name"] for c in rep["safety_checks"] if not c["ok"]}
    assert "runner_non_destructive" in names


def test_refuses_when_delegate_has_destructive_sql(db, capsys, tmp_path, monkeypatch):
    """Even a perfectly clean foreign-flow runner must be refused if the
    file it delegates to (tools/backfill_broker_flow_idx80.py, by default)
    contains destructive SQL -- see module docstring 'DESTRUCTIVE-SQL SCAN
    -- TWO FILES, NOT ONE'."""
    clean_runner = tmp_path / "clean_runner.py"
    clean_runner.write_text('DB_PATH = HERE / "data" / "walkforward.db"\n')
    bad_delegate = tmp_path / "bad_delegate.py"
    bad_delegate.write_text('conn.execute("TRUNCATE broker_flow")')
    monkeypatch.setattr(A, "DELEGATE_RUNNER", bad_delegate)
    rc, rep = _run(_args(db, "--runner", str(clean_runner)), capsys)
    names = {c["name"] for c in rep["safety_checks"] if not c["ok"]}
    assert "runner_non_destructive" in names


def test_refuses_when_concurrent_backfill_detected(db, capsys, monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", lambda *a, **k: [12345])
    rc, rep = _run(_args(db), capsys)
    names = {c["name"] for c in rep["safety_checks"] if not c["ok"]}
    assert "no_concurrent_backfill" in names


def test_invalid_date_range_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--date-from", "2025-01-05", "--date-to", "2025-01-02"), capsys)
    assert rc == A.EXIT_BLOCKED


def test_lock_blocks_concurrent_execute(db, capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn"))
    lock_path = tmp_path / "held.lock"
    fh = open(lock_path, "w")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        rc, rep = _run(
            _args(db, "--action", "execute", "--yes-run-vendor-backfill", lock=lock_path),
            capsys,
        )
        assert rc == A.EXIT_BLOCKED
        names = {c["name"] for c in rep["safety_checks"] if not c["ok"]}
        assert "agent_lock_acquired" in names
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


# --- supervised per-date execution (mocked subprocess) ----------------------


class FakeProc:
    """Stand-in for subprocess.Popen with controllable poll()/terminate()."""

    def __init__(self, db=None, tickers=None, date=None, write_progress=True,
                exit_after=None, never_exit=False):
        self.db = db
        self.tickers = tickers or []
        self.date = date
        self.write_progress = write_progress
        self.exit_after = exit_after
        self.never_exit = never_exit
        self.polls = 0
        self.terminated = False
        self.pid = 999999

    def poll(self):
        self.polls += 1
        if self.never_exit:
            return None
        if self.exit_after is not None and self.polls >= self.exit_after:
            if self.write_progress and self.db is not None:
                conn = sqlite3.connect(self.db)
                for t in self.tickers:
                    _add_foreign_row(conn, t, self.date)
                conn.commit()
                conn.close()
            return 0
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if timeout is not None:
            raise subprocess.TimeoutExpired("fake child", timeout)
        return 0

    def kill(self):
        self.terminated = True


def test_date_wall_clock_timeout_kills_child(db):
    fake = FakeProc(never_exit=True)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["fake"], conn, TICKERS, DATES[0],
            date_timeout_s=0, no_progress_s=600, poll_s=0.01,
            spawn=lambda cmd, cwd: fake,
        )
    finally:
        conn.close()
    assert res.timed_out is True
    assert fake.terminated is True


def test_no_progress_timeout_marks_stalled(db):
    fake = FakeProc(never_exit=True)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["fake"], conn, TICKERS, DATES[0],
            date_timeout_s=600, no_progress_s=0, poll_s=0.01,
            spawn=lambda cmd, cwd: fake,
        )
    finally:
        conn.close()
    assert res.stalled is True
    assert fake.terminated is True


def test_successful_child_not_killed(db):
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], exit_after=1)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["fake"], conn, TICKERS, DATES[0],
            date_timeout_s=600, no_progress_s=600, poll_s=0.01,
            spawn=lambda cmd, cwd: fake,
        )
    finally:
        conn.close()
    assert res.returncode == 0
    assert fake.terminated is False


def test_already_complete_date_launches_no_child(db, monkeypatch):
    conn = sqlite3.connect(db)
    for t in TICKERS:
        _add_foreign_row(conn, t, DATES[0])
    conn.commit()
    conn.close()
    spawned = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: spawned.append(1))
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(_args(db, "--date-to", DATES[1], "--action", "execute",
                          "--yes-run-vendor-backfill", "--json"))
    rep = json.loads(buf.getvalue())
    assert spawned == []
    assert rep["date_summary"]["skipped"] == 1
    assert rc == A.EXIT_COMPLETE


def test_concurrency_recheck_during_a_long_date_child(db, monkeypatch):
    # Baseline sanity: with no_other_process's [] stub still in effect (the
    # autouse fixture), a long-running child times out normally, never aborts.
    fake = FakeProc(never_exit=True)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["fake"], conn, TICKERS, DATES[0],
            date_timeout_s=0.3, no_progress_s=600, poll_s=0.01,
            spawn=lambda cmd, cwd: fake,
        )
    finally:
        conn.close()
    assert res.aborted_concurrent is False
    assert res.timed_out is True

    calls = {"n": 0}

    def flaky_check(*a, **k):
        calls["n"] += 1
        return [4242] if calls["n"] > 2 else []

    monkeypatch.setattr(A, "other_backfill_pids", flaky_check)
    fake2 = FakeProc(never_exit=True)
    conn = A.connect_ro(db)
    try:
        res2 = A.run_date_child(
            ["fake"], conn, TICKERS, DATES[0],
            date_timeout_s=600, no_progress_s=600, poll_s=0.01,
            spawn=lambda cmd, cwd: fake2,
        )
    finally:
        conn.close()
    assert res2.aborted_concurrent is True
    assert fake2.terminated is True


# --- real /proc concurrency detection ---------------------------------------
#
# These tests spawn REAL short-lived subprocesses whose /proc cmdline
# contains one of the two markers (via a trailing argv token), mirroring the
# fix verified this way for the sibling broker_flow orchestrator.

import time as _time


def _spawn_marker_process(marker: str, extra_argv=()):
    """A real, short-lived process whose /proc cmdline contains `marker`,
    exactly as a real runner invocation's argv would."""
    return subprocess.Popen(
        ["python3", "-c", "import time; time.sleep(5)", marker, *extra_argv],
    )


def _wait_until_visible(pid, timeout=5.0):
    """Poll /proc until the spawned process's cmdline is readable -- avoids
    a race where the scan runs before the kernel has populated /proc/<pid>."""
    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if f.read():
                    return True
        except OSError:
            pass
        _time.sleep(0.02)
    return False


def test_intended_child_pid_is_excluded_from_own_marker_match():
    proc = _spawn_marker_process(A.FOREIGN_MARKER,
                                 ("--date-from", "2025-12-01", "--date-to", "2025-12-02"))
    try:
        assert _wait_until_visible(proc.pid)
        found = _real_other_backfill_pids(exclude={proc.pid})
        assert proc.pid not in found
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_unrelated_independent_foreign_runner_pid_is_still_detected():
    proc = _spawn_marker_process(A.FOREIGN_MARKER,
                                 ("--date-from", "2025-12-01", "--date-to", "2025-12-02"))
    try:
        assert _wait_until_visible(proc.pid)
        found = _real_other_backfill_pids()
        assert proc.pid in found
        found2 = _real_other_backfill_pids(exclude={proc.pid + 1})
        assert proc.pid in found2
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_sibling_broker_flow_runner_pid_is_detected_too():
    """Requirement: 'refuse execution if another relevant backfill is
    genuinely running' -- the broker_flow runner writes the SAME tables via
    the SAME vendor call, so it counts as relevant even though it isn't
    this dataset's own runner. See module docstring 'CONCURRENCY -- DUAL
    MARKER'."""
    proc = _spawn_marker_process(A.BROKER_MARKER,
                                 ("--date-from", "2025-12-01", "--date-to", "2025-12-02"))
    try:
        assert _wait_until_visible(proc.pid)
        found = _real_other_backfill_pids()
        assert proc.pid in found
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_run_date_child_does_not_self_abort_on_its_own_spawned_child(db, monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", _real_other_backfill_pids)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["python3", "-c", "import time; time.sleep(5)", A.FOREIGN_MARKER],
            conn, TICKERS, DATES[0],
            date_timeout_s=0.5, no_progress_s=600, poll_s=0.02,
            spawn=subprocess.Popen,
        )
    finally:
        conn.close()
    assert res.timed_out is True
    assert res.aborted_concurrent is False


def test_run_date_child_still_aborts_for_a_genuinely_independent_process(db, monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", _real_other_backfill_pids)
    independent = _spawn_marker_process(A.FOREIGN_MARKER, ("--date-from", "1999-01-01", "--date-to", "1999-01-02"))
    try:
        assert _wait_until_visible(independent.pid)
        fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=False, never_exit=True)
        conn = A.connect_ro(db)
        try:
            res = A.run_date_child(
                ["fake"], conn, TICKERS, DATES[0],
                date_timeout_s=600, no_progress_s=600, poll_s=0.02,
                spawn=lambda cmd, cwd: fake,
            )
        finally:
            conn.close()
        assert res.aborted_concurrent is True
        assert fake.terminated is True
    finally:
        independent.terminate()
        independent.wait(timeout=5)


# --- reporting / resumability ---------------------------------------------


def test_execute_reconstructs_outcome_counts_from_db_state(db, capsys, monkeypatch):
    """foreign coverage must be derivable purely from DB state after a run
    -- no reliance on runner stdout parsing."""

    def fake_spawn(cmd, cwd=None):
        return FakeProc(exit_after=1)

    monkeypatch.setattr(subprocess, "Popen", fake_spawn)

    def fake_supervise(db_path, tickers, dates, python, runner, budget_s,
                       date_timeout_s, no_progress_s, poll_s):
        conn = sqlite3.connect(db_path)
        _add_foreign_row(conn, "BBCA", DATES[0])
        _add_empty_marker(conn, "BBRI", DATES[0])
        conn.commit()
        conn.close()
        return (
            [{"date": DATES[0], "outcome": "SUCCESS", "reason": None,
              "returncode": 0, "duration_s": 1.0, "timed_out": False,
              "stalled": False, "complete_cells": 2, "expected_cells": 2,
              "command": ["fake"]}],
            1, None,
        )

    monkeypatch.setattr(A, "supervise_dates", fake_supervise)
    rc, rep = _run(
        _args(db, "--date-to", DATES[1], "--action", "execute",
             "--yes-run-vendor-backfill"),
        capsys,
    )
    assert rep["coverage_after"]["complete_ticker_days"] == 2
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_rerun_only_targets_remaining_gaps(db, capsys):
    conn = sqlite3.connect(db)
    _add_foreign_row(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["missing_ticker_days"] == 1
