"""Tests for tools/agent_backfill_broker_flow_full_universe.py — the
multi-date, FULL-UNIVERSE broker_flow backfill DRIVER.

This driver is a THIN orchestration layer that composes:
  - tools/broker_flow_idx80_gap.py::canonical_trading_dates / missing_cells
    (the existing completion predicate — reused, not reimplemented)
  - tools/backfill_broker_flow_full_universe.py (the existing, tested,
    single-date full-universe fetcher — invoked as a CHILD PROCESS, never
    reimplemented)
  - tools/agent_backfill_broker_flow_idx80.py's connect_ro / other_backfill_pids
    / AgentLock (the existing safety primitives — reused, not reinvented)

Every test runs against a temporary SQLite DB and a mocked/fake subprocess.
Nothing here touches data/walkforward.db, any frozen artifact, or the
Stockbit vendor endpoint.
"""
import json
import sqlite3

import pytest

import tools.agent_backfill_broker_flow_full_universe as D
import tools.backfill_broker_flow_full_universe as R

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
FULL_UNIVERSE = ["BBCA", "BBRI", "TLKM"]


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
    for t in FULL_UNIVERSE:
        conn.execute(
            "INSERT INTO idx_tickers (ticker, status) VALUES (?, 'active')", (t,)
        )
    for d in DATES:
        conn.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        conn.execute(
            "INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,)
        )
    conn.commit()
    conn.close()
    return path


@pytest.fixture(autouse=True)
def full_universe(monkeypatch):
    """R.load_all_tickers is looked up dynamically inside resolve_universe()'s
    own module namespace at call time -- patching it here affects every call
    the driver makes to the imported resolve_universe(), without the driver
    needing its own copy of universe-resolution logic (composition, not
    duplication)."""
    monkeypatch.setattr(R, "load_all_tickers", lambda: list(FULL_UNIVERSE))
    monkeypatch.setattr(R, "FALLBACK_SIZE_FLOOR", 1)


@pytest.fixture(autouse=True)
def no_other_process(monkeypatch):
    monkeypatch.setattr(D, "other_backfill_pids", lambda *a, **k: [])


def _args(db_path, *extra, lock=None):
    args = ["--start-date", DATES[0], "--end-date", "2025-01-07", "--db", str(db_path)]
    if lock is not None:
        args += ["--lock-file", str(lock)]
    return args + list(extra)


def _run(args, capsys):
    rc = D.main(args + ["--json"])
    out = capsys.readouterr().out
    return rc, json.loads(out)


class FakeSpawn:
    """Records every invocation; returns a canned (returncode, timed_out) per
    call, in order. Never actually runs a subprocess."""

    def __init__(self, returncodes=None, timeout_at=None):
        self.calls = []
        self._returncodes = list(returncodes or [])
        self._timeout_at = timeout_at

    def __call__(self, cmd, timeout=None):
        idx = len(self.calls)
        self.calls.append({"cmd": cmd, "timeout": timeout})
        if self._timeout_at is not None and idx == self._timeout_at:
            import subprocess
            raise subprocess.TimeoutExpired(cmd, timeout)
        rc = self._returncodes[idx] if idx < len(self._returncodes) else 0

        class _R:
            pass
        r = _R()
        r.returncode = rc
        return r


# --- 1/2/3/4: date enumeration, ordering, boundaries, calendar filtering ----


def test_plan_enumerates_all_confirmed_dates_in_window(db):
    conn = D.connect_ro(db)
    plan, non_ihsg = D.plan_dates(conn, DATES[0], "2025-01-07", FULL_UNIVERSE)
    conn.close()
    assert [p["date"] for p in plan] == DATES


def test_plan_dates_are_chronological(db):
    conn = sqlite3.connect(db)
    # insert an out-of-order calendar/ohlcv row before the window start
    for d in ["2025-01-08", "2025-01-05"]:
        conn.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,))
    conn.commit()
    conn.close()
    conn = D.connect_ro(db)
    plan, _ = D.plan_dates(conn, "2025-01-02", "2025-01-09", FULL_UNIVERSE)
    conn.close()
    dates = [p["date"] for p in plan]
    assert dates == sorted(dates)


def test_end_date_is_exclusive_boundary(db):
    conn = D.connect_ro(db)
    plan, _ = D.plan_dates(conn, DATES[0], DATES[-1], FULL_UNIVERSE)  # excludes DATES[-1]
    conn.close()
    assert [p["date"] for p in plan] == DATES[:-1]


def test_start_date_is_inclusive_boundary(db):
    conn = D.connect_ro(db)
    plan, _ = D.plan_dates(conn, DATES[0], "2025-01-07", FULL_UNIVERSE)
    conn.close()
    assert plan[0]["date"] == DATES[0]


def test_non_ihsg_calendar_row_excluded_from_plan(db):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO trading_calendar (date, source) VALUES ('2025-01-04', 'scraper_eod')"
    )  # no IHSG ohlcv bar -> not a confirmed session
    conn.commit()
    conn.close()
    conn = D.connect_ro(db)
    plan, non_ihsg = D.plan_dates(conn, DATES[0], "2025-01-07", FULL_UNIVERSE)
    conn.close()
    assert "2025-01-04" not in [p["date"] for p in plan]
    assert non_ihsg and non_ihsg[0]["date"] == "2025-01-04"


# --- 5: already-complete dates are no-ops -----------------------------------


def test_already_complete_date_marked_skip(db):
    conn = sqlite3.connect(db)
    for t in FULL_UNIVERSE:
        _add_broker_row(conn, t, DATES[0])
    conn.commit()
    conn.close()
    conn = D.connect_ro(db)
    plan, _ = D.plan_dates(conn, DATES[0], "2025-01-07", FULL_UNIVERSE)
    conn.close()
    by_date = {p["date"]: p for p in plan}
    assert by_date[DATES[0]]["skip"] is True
    assert by_date[DATES[0]]["missing"] == 0
    assert by_date[DATES[1]]["skip"] is False


def test_confirmed_empty_marker_counts_as_complete(db):
    conn = sqlite3.connect(db)
    for t in FULL_UNIVERSE:
        _add_empty_marker(conn, t, DATES[0])
    conn.commit()
    conn.close()
    conn = D.connect_ro(db)
    plan, _ = D.plan_dates(conn, DATES[0], "2025-01-07", FULL_UNIVERSE)
    conn.close()
    assert {p["date"]: p for p in plan}[DATES[0]]["skip"] is True


def test_already_complete_date_launches_no_child(db, monkeypatch, capsys):
    conn = sqlite3.connect(db)
    for t in FULL_UNIVERSE:
        for d in DATES:
            _add_broker_row(conn, t, d)
    conn.commit()
    conn.close()
    fake = FakeSpawn()
    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert report["dates_needing_work"] == []
    assert fake.calls == []
    assert rc == D.EXIT_COMPLETE


# --- 9: dry-run makes zero vendor/subprocess calls --------------------------


def test_dry_run_makes_no_subprocess_calls(db, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(D.subprocess, "run", lambda *a, **k: calls.append(1))
    rc, report = _run(_args(db, "--dry-run"), capsys)
    assert calls == []
    assert report["vendor_calls_made"] is False


def test_default_invocation_without_any_mode_flag_makes_no_vendor_calls(db, monkeypatch, capsys):
    """Requirement: default invocation MUST NOT perform vendor calls, even
    if the caller forgets --dry-run entirely."""
    calls = []
    monkeypatch.setattr(D.subprocess, "run", lambda *a, **k: calls.append(1))
    rc, report = _run(_args(db), capsys)
    assert calls == []
    assert report["vendor_calls_made"] is False


def test_dry_run_reports_dates_selected_skipped_and_needing_work(db, capsys):
    conn = sqlite3.connect(db)
    for t in FULL_UNIVERSE:
        _add_broker_row(conn, t, DATES[0])
    conn.commit()
    conn.close()
    rc, report = _run(_args(db, "--dry-run"), capsys)
    assert report["dates_selected"] == DATES
    assert report["dates_skipped_already_complete"] == [DATES[0]]
    assert report["dates_needing_work"] == DATES[1:]
    assert report["estimated_missing_cells"] == len(FULL_UNIVERSE) * (len(DATES) - 1)


# --- 10: safety flag propagation --------------------------------------------


def test_live_mode_requires_confirm_flag(db, capsys):
    rc, report = _run(_args(db), capsys)  # no --yes-run-vendor-backfill, no --dry-run
    # default (no flags) is dry-run-safe, so this alone must not execute;
    # but explicitly requesting live without confirm must be BLOCKED:
    rc2, report2 = _run(_args(db, "--live"), capsys)
    assert rc2 == D.EXIT_BLOCKED
    assert report2["vendor_calls_made"] is False


def test_confirm_flag_present_in_child_command(db, monkeypatch, capsys):
    fake = FakeSpawn(returncodes=[0, 0])
    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert fake.calls, "expected at least one child invocation"
    for c in fake.calls:
        assert D.CONFIRM_FLAG in c["cmd"]


# --- 6/7: exit-code-driven stop/advance --------------------------------------


def test_zero_exit_advances_to_next_date(db, monkeypatch, capsys):
    fake = FakeSpawn(returncodes=[0, 0, 0])
    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert len(fake.calls) == 3  # all three incomplete dates attempted, in order
    assert [c["cmd"][c["cmd"].index("--date") + 1] for c in fake.calls] == DATES
    assert report["stopped_reason"] is None
    assert rc == D.EXIT_COMPLETE


def test_nonzero_exit_stops_sequence_immediately(db, monkeypatch, capsys):
    fake = FakeSpawn(returncodes=[7])  # first date fails
    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert len(fake.calls) == 1  # second date NEVER attempted
    assert report["stopped_reason"] is not None
    assert rc == D.EXIT_FAILED


def test_timeout_is_treated_as_stop_condition(db, monkeypatch, capsys):
    fake = FakeSpawn(returncodes=[0], timeout_at=0)
    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert len(fake.calls) == 1
    assert rc == D.EXIT_FAILED
    assert "timed out" in report["stopped_reason"]


# --- 8: interruption / resume semantics (DB-derived, no cursor file) -------


def test_resume_only_targets_remaining_incomplete_dates_after_partial_run(db, monkeypatch, capsys):
    def fake_spawn(cmd, timeout=None):
        # simulate the child actually completing the date it was given
        date = cmd[cmd.index("--date") + 1]
        conn = sqlite3.connect(db)
        for t in FULL_UNIVERSE:
            _add_broker_row(conn, t, date)
        conn.commit()
        conn.close()

        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake_spawn, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert rc == D.EXIT_COMPLETE
    assert report["dates_needing_work"] == DATES  # both incomplete dates at plan time

    # Re-invoking the driver now (no cursor file passed anywhere) must see
    # everything as already complete -- resume is purely DB-derived.
    rc2, report2 = _run(_args(db, "--dry-run"), capsys)
    assert report2["dates_needing_work"] == []
    assert rc2 == D.EXIT_COMPLETE


def test_resume_after_a_stop_leaves_earlier_completed_dates_skipped(db, monkeypatch, capsys):
    def fake_spawn(cmd, timeout=None):
        date = cmd[cmd.index("--date") + 1]
        if date == DATES[1]:
            class _R:
                returncode = 9
            return _R()
        conn = sqlite3.connect(db)
        for t in FULL_UNIVERSE:
            _add_broker_row(conn, t, date)
        conn.commit()
        conn.close()

        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(D, "subprocess", type("S", (), {"run": fake_spawn, "TimeoutExpired": __import__("subprocess").TimeoutExpired}))
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert rc == D.EXIT_FAILED

    rc2, report2 = _run(_args(db, "--dry-run"), capsys)
    # DATES[0] completed before the stop -> now skipped; DATES[1] & DATES[2] still pending
    assert report2["dates_skipped_already_complete"] == [DATES[0]]
    assert report2["dates_needing_work"] == DATES[1:]


# --- 11: malformed date handling --------------------------------------------


def test_malformed_start_date_is_blocked(db, capsys):
    rc, report = _run(["--start-date", "not-a-date", "--end-date", "2025-01-07",
                       "--db", str(db), "--dry-run"], capsys)
    assert rc == D.EXIT_BLOCKED
    assert report["vendor_calls_made"] is False


def test_start_after_end_is_blocked(db, capsys):
    rc, report = _run(["--start-date", "2025-01-07", "--end-date", "2025-01-02",
                       "--db", str(db), "--dry-run"], capsys)
    assert rc == D.EXIT_BLOCKED


# --- 12: empty date range ----------------------------------------------------


def test_equal_start_and_end_date_is_blocked_not_silently_empty(db, capsys):
    """--end-date is EXCLUSIVE, so start==end can only ever mean an empty
    window -- mirroring the sibling IDX80 orchestrator's own strict
    date_from < date_to validation, this is treated as a malformed request
    (BLOCKED), not silently accepted as trivially COMPLETE."""
    rc, report = _run(["--start-date", "2025-01-02", "--end-date", "2025-01-02",
                       "--db", str(db), "--dry-run"], capsys)
    assert rc == D.EXIT_BLOCKED
    assert report["dates_selected"] == []


def test_window_with_no_trading_dates_is_complete_with_no_dates(tmp_path, capsys):
    path = tmp_path / "empty.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    rc, report = _run(["--start-date", "2030-01-01", "--end-date", "2030-02-01",
                       "--db", str(path), "--dry-run"], capsys)
    assert report["dates_selected"] == []
    assert rc == D.EXIT_COMPLETE


# --- 13: logging / exit-code / JSON report shape ----------------------------


def test_json_report_has_expected_keys(db, capsys):
    rc, report = _run(_args(db, "--dry-run"), capsys)
    for key in ("dates_selected", "dates_skipped_already_complete",
               "dates_needing_work", "estimated_missing_cells",
               "vendor_calls_made", "stopped_reason", "status",
               "safety_checks"):
        assert key in report


# --- frozen-artifact write-target guard -------------------------------------


def test_refuses_frozen_directory_as_db_target(tmp_path, capsys, monkeypatch):
    frozen_dir = D.FROZEN_DIR
    fake_frozen_db = frozen_dir / "stockbit-flow-bars-v002" / "stockbit-flow-bars-v002.db"
    rc = D.main(["--start-date", "2025-01-02", "--end-date", "2025-01-07",
                "--db", str(fake_frozen_db), "--dry-run", "--json"])
    out = capsys.readouterr().out
    report = json.loads(out)
    assert rc == D.EXIT_BLOCKED
    assert any("frozen" in r.lower() for r in report["reasons"])


# --- concurrency / lock reuse ------------------------------------------------


def test_refuses_when_concurrent_backfill_detected(db, monkeypatch, capsys):
    monkeypatch.setattr(D, "other_backfill_pids", lambda *a, **k: [12345])
    rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill"), capsys)
    assert rc == D.EXIT_BLOCKED
    assert report["vendor_calls_made"] is False


def test_lock_blocks_concurrent_execute(db, tmp_path, capsys):
    import fcntl
    lock_path = tmp_path / "held.lock"
    fh = open(lock_path, "w")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        rc, report = _run(_args(db, "--live", "--yes-run-vendor-backfill", lock=lock_path), capsys)
        assert rc == D.EXIT_BLOCKED
        assert report["vendor_calls_made"] is False
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


# --- static safety: the real runner this driver composes has no destructive SQL ---


def test_real_runner_has_no_destructive_sql():
    from tools.agent_backfill_broker_flow_idx80 import scan_runner_for_destructive_sql
    assert scan_runner_for_destructive_sql(D.DEFAULT_RUNNER) == []
