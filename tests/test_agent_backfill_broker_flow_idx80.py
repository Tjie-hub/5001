"""Tests for tools/agent_backfill_broker_flow_idx80.py — the IDX80
broker_flow backfill ORCHESTRATOR.

Every test runs against a temporary SQLite DB and a mocked subprocess.
Nothing here touches data/walkforward.db or the Stockbit vendor endpoint.
"""
import fcntl
import json
import sqlite3
import subprocess

import pytest

import tools.agent_backfill_broker_flow_idx80 as A
# Captured before any per-test monkeypatching of A.other_backfill_pids (the
# autouse no_other_process fixture below rebinds that module attribute for
# every test by default) -- the false-positive-concurrency regression tests
# need the REAL /proc-scanning implementation to mean anything.
from tools.agent_backfill_broker_flow_idx80 import other_backfill_pids as _real_other_backfill_pids

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


def _add_broker_row(conn, ticker, date):
    conn.execute(
        "INSERT OR REPLACE INTO broker_flow "
        "(ticker,trade_date,broker_code,side) VALUES (?,?,'ZP','BUY')",
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
        '"""INSERT OR REPLACE INTO broker_flow ..."""\n'
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
    """Structural safety: there is no CLI flag to widen scope beyond IDX80."""
    parser = A.build_parser()
    flags = {a.option_strings[0] for a in parser._actions if a.option_strings}
    assert not any("cat" in f or "idx80" in f.lower() and "allow" in f.lower() for f in flags)
    rc, rep = _run(_args(db), capsys)
    assert rep["universe_size"] == 2  # BBCA, BBRI -- NOTIDX excluded


def test_universe_recomputed_from_db_not_hardcoded(db, capsys, tmp_path):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) VALUES ('TLKM','active',1)")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db), capsys)
    assert rep["universe_size"] == 3


def test_refuses_when_universe_is_empty(db, capsys):
    conn = sqlite3.connect(db)
    conn.execute("UPDATE idx_tickers SET in_idx80=0")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("empty" in r.lower() or "universe" in r.lower() for r in rep["reasons"])


# --- canonical calendar ------------------------------------------------


def test_non_ihsg_calendar_row_excluded_from_expected(db, capsys):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES ('2025-01-08','scraper_eod')")
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", "2025-01-09"), capsys)
    non_ihsg_dates = [x["date"] for x in rep["calendar"]["non_ihsg_dates"]]
    assert "2025-01-08" in non_ihsg_dates


def test_date_to_is_exclusive(db, capsys):
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["expected_ticker_days"] == len(TICKERS) * 1  # only DATES[0]


def test_no_canonical_dates_in_window_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--date-from", "2030-01-01", "--date-to", "2030-01-02"), capsys)
    assert rep["status"] == "BLOCKED"


# --- coverage / gap-only -------------------------------------------------


def test_coverage_counts_broker_rows_as_complete(db, capsys):
    conn = sqlite3.connect(db)
    _add_broker_row(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["complete_ticker_days"] == 1
    assert cov["missing_ticker_days"] == 1  # BBRI still missing


def test_coverage_counts_confirmed_empty_marker_as_complete(db, capsys):
    conn = sqlite3.connect(db)
    _add_empty_marker(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["complete_ticker_days"] == 1


def test_coverage_does_not_count_nonzero_bandar_without_broker_rows(db, capsys):
    """Anomalous partial state must stay incomplete (retried), not silently
    accepted as done."""
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO bandar_detector (ticker,trade_date,value,volume) VALUES ('BBCA',?,999,50)",
        (DATES[0],),
    )
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["complete_ticker_days"] == 0


def test_plan_status_complete_when_fully_covered(db, capsys):
    conn = sqlite3.connect(db)
    for t in TICKERS:
        _add_broker_row(conn, t, DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_plan_status_partial_when_gaps_remain(db, capsys):
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    assert rep["status"] == "PARTIAL"
    assert rc == A.EXIT_PARTIAL


# --- plan mode is strictly read-only ----------------------------------


def test_plan_mode_makes_no_subprocess_calls(db, capsys, monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: called.append(1))
    rc, rep = _run(_args(db), capsys)
    assert called == []
    assert rep["vendor_calls_made"] is False


def test_plan_mode_writes_nothing(db, capsys):
    before = db.stat().st_mtime
    _run(_args(db), capsys)
    # DB file untouched -- opened read-only throughout plan mode
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    assert conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()[0] == 0
    conn.close()


def test_execute_without_confirm_flag_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--action", "execute"), capsys)
    assert rep["status"] == "BLOCKED"
    assert rc == A.EXIT_BLOCKED
    assert any("yes-run-vendor-backfill" in r for r in rep["reasons"])


# --- safety checks -------------------------------------------------------


def test_refuses_when_db_missing(tmp_path, capsys):
    missing = tmp_path / "nope.db"
    rc, rep = _run(_args(missing), capsys)
    assert rep["status"] == "BLOCKED"


def test_refuses_when_runner_has_destructive_sql(db, capsys, tmp_path):
    bad_runner = tmp_path / "bad_runner.py"
    bad_runner.write_text('conn.execute("DELETE FROM broker_flow")')
    rc, rep = _run(_args(db, "--runner", str(bad_runner)), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("destructive" in r.lower() for r in rep["reasons"])


def test_refuses_when_concurrent_backfill_detected(db, capsys, monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", lambda *a, **k: [12345])
    rc, rep = _run(_args(db), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("12345" in r for r in rep["reasons"])


def test_invalid_date_range_is_blocked(db, capsys):
    rc, rep = _run(_args(db, "--date-from", "2025-01-10", "--date-to", "2025-01-05"), capsys)
    assert rep["status"] == "BLOCKED"


# --- locking ---------------------------------------------------------------


def test_lock_blocks_concurrent_execute(db, capsys, tmp_path, monkeypatch):
    conn = sqlite3.connect(db)
    for t in TICKERS:
        _add_broker_row(conn, t, DATES[0])
        _add_broker_row(conn, t, DATES[1])
        _add_broker_row(conn, t, DATES[2])
    conn.commit()
    conn.close()

    lock_path = tmp_path / "lock"
    held = open(lock_path, "w")
    fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        rc, rep = _run(
            _args(db, "--action", "execute", "--yes-run-vendor-backfill", lock=lock_path),
            capsys,
        )
        assert rep["status"] == "BLOCKED"
        assert any("lock" in r.lower() for r in rep["reasons"])
    finally:
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
        held.close()


# --- per-date supervised execution ---------------------------------------


class FakeProc:
    def __init__(self, db=None, tickers=None, date=None, exit_after=None,
                write_progress=False, block_grace_wait=False):
        self.db, self.tickers, self.date = db, tickers, date
        self.exit_after = exit_after
        self.write_progress = write_progress
        self.block_grace_wait = block_grace_wait
        self.polls = 0
        self.terminated = False
        self.killed = False

    def poll(self):
        self.polls += 1
        if self.write_progress and self.db is not None:
            c = sqlite3.connect(self.db)
            for t in self.tickers:
                _add_broker_row(c, t, self.date)
            c.commit()
            c.close()
        if self.exit_after is not None and self.polls >= self.exit_after:
            return 0
        return None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        if self.block_grace_wait and not self.killed:
            raise subprocess.TimeoutExpired("fake child", timeout)
        return 0


def _run_date_child_with(fake, db, date_timeout_s=600, no_progress_s=600):
    conn = A.connect_ro(db)
    try:
        return A.run_date_child(["fake", "runner"], conn, TICKERS, DATES[0],
                                date_timeout_s=date_timeout_s,
                                no_progress_s=no_progress_s,
                                poll_s=0.01,
                                spawn=lambda cmd, cwd: fake)
    finally:
        conn.close()


def test_date_wall_clock_timeout_kills_child(db):
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=True)
    res = _run_date_child_with(fake, db, date_timeout_s=0.3, no_progress_s=600)
    assert res.timed_out is True
    assert fake.terminated is True


def test_no_progress_timeout_marks_stalled(db):
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=False)
    res = _run_date_child_with(fake, db, date_timeout_s=600, no_progress_s=0.3)
    assert res.stalled is True
    assert fake.terminated is True


def test_successful_child_not_killed(db):
    fake = FakeProc(exit_after=1)
    res = _run_date_child_with(fake, db)
    assert res.returncode == 0
    assert fake.terminated is False


def test_already_complete_date_launches_no_child(db, monkeypatch):
    conn = sqlite3.connect(db)
    for t in TICKERS:
        _add_broker_row(conn, t, DATES[0])
    conn.commit()
    conn.close()

    launched = []

    def fake_spawn(cmd, cwd=None):
        launched.append(cmd)
        return FakeProc(exit_after=1)

    outcomes, n_launched, aborted = A.supervise_dates(
        db, TICKERS, [DATES[0]], "python3", "runner.py",
        budget_s=100, date_timeout_s=5, no_progress_s=5, poll_s=0.01,
    )
    assert n_launched == 0
    assert outcomes[0]["outcome"] == "SKIPPED"


def test_concurrency_recheck_during_a_long_date_child(db, monkeypatch):
    """A hand-launched second writer that appears WHILE a date child is
    still running (not just before it starts) must be detected too."""
    calls = {"n": 0}

    def flaky_pids(marker=None, exclude=frozenset()):
        calls["n"] += 1
        return [999] if calls["n"] > 1 else []

    monkeypatch.setattr(A, "other_backfill_pids", flaky_pids)
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=False)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(["fake"], conn, TICKERS, DATES[0],
                               date_timeout_s=600, no_progress_s=600,
                               poll_s=0.01, spawn=lambda cmd, cwd: fake)
    finally:
        conn.close()
    assert res.aborted_concurrent is True
    assert fake.terminated is True


# --- regression: false-positive mid-run self-detection (2026-08-27) -------
#
# Production incident: agent_backfill_broker_flow_idx80.py --action execute
# reported "backfill process appeared mid-run" and aborted a perfectly normal
# date, 0.01s after launch, with no independent process running. Root cause:
# other_backfill_pids() excluded only the ORCHESTRATOR's own PID
# (os.getpid()), never the CHILD's PID -- and the child it just spawned is a
# real process whose cmdline legitimately contains the marker (it *is* the
# runner). The very first mid-poll recheck in run_date_child() therefore
# matched its own intended child and aborted the run.
#
# These tests spawn REAL short-lived subprocesses whose /proc cmdline
# contains the marker (via a trailing argv token), reproducing the exact
# mechanism the incident hit -- not a mocked stand-in for it.

import time as _time


def _spawn_marker_process(extra_argv=()):
    """A real, short-lived process whose /proc cmdline contains the marker
    string, exactly as a real runner invocation's argv would."""
    return subprocess.Popen(
        ["python3", "-c", "import time; time.sleep(5)",
         "tools/backfill_broker_flow_idx80.py", *extra_argv],
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
    """Requirement 2/5: the orchestrator's own just-launched child (a real
    process whose cmdline matches the marker) must NOT be reported as an
    'other' backfill when its PID is excluded -- reproduces the exact
    production false-positive at the other_backfill_pids() level. Uses the
    REAL implementation directly (not the autouse no_other_process mock)."""
    proc = _spawn_marker_process(("--date-from", "2025-12-01", "--date-to", "2025-12-02"))
    try:
        assert _wait_until_visible(proc.pid)
        found = _real_other_backfill_pids(exclude={proc.pid})
        assert proc.pid not in found
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_unrelated_independent_runner_pid_is_still_detected():
    """Requirement 1/7: an independently-launched runner process (NOT the
    orchestrator's own child, i.e. not in `exclude`) must still be caught --
    the fix must not weaken the original safety guarantee."""
    proc = _spawn_marker_process(("--date-from", "2025-12-01", "--date-to", "2025-12-02"))
    try:
        assert _wait_until_visible(proc.pid)
        # No exclude at all -- simulates a genuinely independent second writer.
        found = _real_other_backfill_pids()
        assert proc.pid in found
        # Excluding some OTHER pid (e.g. our own intended child from a
        # different, unrelated run) must not hide this one either.
        found2 = _real_other_backfill_pids(exclude={proc.pid + 1})
        assert proc.pid in found2
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_run_date_child_does_not_self_abort_on_its_own_spawned_child(db, monkeypatch):
    """Requirement 6: end-to-end reproduction of the reported incident through
    run_date_child() itself -- spawn a REAL marker-matching child (standing in
    for the production runner) via the real subprocess.Popen path, and confirm
    the date completes/times out normally rather than reporting
    aborted_concurrent. Uses a short date_timeout_s so the test doesn't wait
    for the full 5s sleep. Restores the REAL other_backfill_pids for this test
    -- the autouse mock would hide the bug entirely."""
    monkeypatch.setattr(A, "other_backfill_pids", _real_other_backfill_pids)
    conn = A.connect_ro(db)
    try:
        res = A.run_date_child(
            ["python3", "-c", "import time; time.sleep(5)",
             "tools/backfill_broker_flow_idx80.py"],
            conn, TICKERS, DATES[0],
            date_timeout_s=0.5, no_progress_s=600, poll_s=0.02,
            spawn=subprocess.Popen,
        )
    finally:
        conn.close()
    # It times out (the fake "runner" just sleeps and never writes cells) --
    # the point is what it must NOT be: a false concurrency abort.
    assert res.timed_out is True
    assert res.aborted_concurrent is False


def test_run_date_child_still_aborts_for_a_genuinely_independent_process(db, monkeypatch):
    """Requirement 7 at the run_date_child level: an unrelated marker-matching
    process running ALONGSIDE (not launched by this call) must still trigger
    aborted_concurrent, proving the fix didn't weaken the guarantee end-to-end."""
    monkeypatch.setattr(A, "other_backfill_pids", _real_other_backfill_pids)
    independent = _spawn_marker_process(("--date-from", "1999-01-01", "--date-to", "1999-01-02"))
    try:
        assert _wait_until_visible(independent.pid)
        fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=False)
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
    """populated / empty_confirmed / missing must be derivable purely from
    DB state after a run -- no reliance on runner stdout parsing."""

    def fake_spawn(cmd, cwd=None):
        # cmd[-2] is the date-from arg value in build_command's positional order
        return FakeProc(exit_after=1)

    monkeypatch.setattr(subprocess, "Popen", fake_spawn)

    def fake_supervise(db_path, tickers, dates, python, runner, budget_s,
                       date_timeout_s, no_progress_s, poll_s):
        conn = sqlite3.connect(db_path)
        _add_broker_row(conn, "BBCA", DATES[0])
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
    _add_broker_row(conn, "BBCA", DATES[0])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, "--date-to", DATES[1]), capsys)
    cov = rep["coverage_before"]
    assert cov["missing_ticker_days"] == 1
    assert cov["dates_partial_count"] == 1
