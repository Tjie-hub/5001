"""Tests for tools/agent_backfill_idx80.py — the IDX80 backfill ORCHESTRATOR.

Every test runs against a temporary SQLite DB and a mocked subprocess. Nothing
here touches data/walkforward.db, the Stockbit vendor endpoint, or the real
production runner.
"""
import fcntl
import json
import sqlite3
import subprocess
import time

import pytest

import tools.agent_backfill_idx80 as A
from tools.agent_backfill_idx80 import resolve_universe as _real_resolve_universe
from tools.flow_bars_gap import bars_cell_complete


# --- fixtures ---------------------------------------------------------------

SCHEMA = """
CREATE TABLE stockbit_flow_bars (
    ticker TEXT NOT NULL, trade_date TEXT NOT NULL, bar_time TEXT NOT NULL,
    buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
    net_value INTEGER, price INTEGER, delta INTEGER,
    PRIMARY KEY (ticker, trade_date, bar_time));
CREATE TABLE stockbit_flow (
    ticker TEXT NOT NULL, trade_date TEXT NOT NULL, buy_lot INTEGER,
    sell_lot INTEGER, net_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
    net_value INTEGER, last_price INTEGER, composite_score REAL, verdict TEXT,
    smart_money TEXT, updated_at TEXT, PRIMARY KEY (ticker, trade_date));
CREATE TABLE trading_calendar (
    date TEXT PRIMARY KEY, source TEXT, updated_at TEXT);
CREATE TABLE ohlcv (
    ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER);
"""

DATES = ["2025-01-02", "2025-01-03", "2025-01-06"]
TICKERS = ["BBCA", "BBRI"]


def _add_bars(conn, ticker, date, n=3):
    conn.executemany(
        "INSERT OR REPLACE INTO stockbit_flow_bars "
        "(ticker,trade_date,bar_time,buy_lot,sell_lot,buy_freq,sell_freq,"
        "net_value,price,delta) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(ticker, date, f"09:{i:02d}", 1, 1, 1, 1, 0, 100, 0) for i in range(n)],
    )


def _add_summary(conn, ticker, date, empty):
    vals = (0, 0, 0, 0) if empty else (10, 5, 3, 2)
    conn.execute(
        "INSERT OR REPLACE INTO stockbit_flow "
        "(ticker,trade_date,buy_lot,sell_lot,net_lot,buy_freq,sell_freq,"
        "net_value,last_price,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ticker, date, vals[0], vals[1], vals[0] - vals[1], vals[2], vals[3],
         0, 100, "now"),
    )


@pytest.fixture
def db(tmp_path):
    """Empty schema + a 3-date trading calendar (mirrored into ohlcv)."""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for d in DATES:
        conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'test')", (d,))
        conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)", (d,))
    conn.commit()
    conn.close()
    return path


@pytest.fixture(autouse=True)
def idx80_two_tickers(monkeypatch):
    """Keep the universe tiny and deterministic."""
    monkeypatch.setattr(A, "resolve_universe", lambda cat: list(TICKERS))


@pytest.fixture(autouse=True)
def no_other_process(monkeypatch):
    monkeypatch.setattr(A, "other_backfill_pids", lambda: [])


@pytest.fixture(autouse=True)
def runner_targets_the_test_db(monkeypatch, db):
    """The real runner writes to its own hardcoded DB_PATH; align it with the
    temp DB so the audit and the (mocked) run refer to the same file."""
    monkeypatch.setattr(A, "runner_db_path", lambda runner: db)


@pytest.fixture
def no_subprocess(monkeypatch):
    """Fail loudly if anything tries to launch the production runner.

    Covers both spawn seams: the whole-window probe launcher and the
    supervised single-date child launcher.
    """
    def boom(cmd, *a, **kw):
        raise AssertionError(f"subprocess launched during a read-only action: {cmd}")
    monkeypatch.setattr(A, "run_backfill", boom)
    monkeypatch.setattr(A, "run_date_child", boom)


def _args(db, *extra, lock=None):
    out = ["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-07"]
    if lock is not None:
        out += ["--lock-file", str(lock)]
    return out + list(extra)


def _run(argv, capsys):
    """Run main() with --json and return (exit_code, parsed report)."""
    rc = A.main(argv + ["--json"])
    return rc, json.loads(capsys.readouterr().out)


# --- A: safe default --------------------------------------------------------


def test_default_action_is_plan(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["action"] == "plan"
    assert rep["vendor_calls_made"] is False


def test_plan_makes_no_subprocess_call(db, capsys, no_subprocess, tmp_path):
    # no_subprocess raises if the runner is launched; reaching the assert is the test
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["subprocess"] is None


def test_plan_never_mutates_the_database(db, capsys, no_subprocess, tmp_path):
    before = db.read_bytes()
    _run(_args(db, lock=tmp_path / "l"), capsys)
    assert db.read_bytes() == before


def test_agent_db_handle_is_read_only(db):
    conn = A.connect_ro(db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO trading_calendar (date) VALUES ('2030-01-01')")
    conn.close()


# --- B: explicit execution --------------------------------------------------


def test_execute_without_confirmation_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--action", "execute", lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert rc == A.EXIT_BLOCKED
    assert any("confirm" in r.lower() for r in rep["reasons"])


def test_probe_without_confirmation_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--action", "probe", lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"


def test_execute_with_confirmation_launches_the_runner(db, capsys, monkeypatch, tmp_path):
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert "tools/backfill_flow_bars.py" in " ".join(launched[0][1])
    assert rep["vendor_calls_made"] is True
    assert rep["date_summary"]["launched"] == 3


# --- C: IDX80 only ----------------------------------------------------------


def test_default_category_is_idx80(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["category"] == "IDX80"


def test_non_idx80_category_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--cat", "ALL", lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("IDX80" in r for r in rep["reasons"])


def test_non_idx80_allowed_with_explicit_override(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--cat", "LQ45", A.OVERRIDE_FLAG, lock=tmp_path / "l"), capsys)
    assert rep["status"] != "BLOCKED"
    assert rep["category"] == "LQ45"


def test_resolve_universe_all_falls_back_to_idx80_like_the_runner_does(monkeypatch):
    """resolve_universe's ALL branch must match stockbit_fetcher.get_tickers's
    documented fallback -- otherwise the orchestrator's audit (BLOCKED / empty
    universe) can disagree with what the runner it audits would actually do."""
    import data.fetcher as fetcher

    def boom():
        raise RuntimeError("vendor ticker list unavailable")
    monkeypatch.setattr(fetcher, "load_all_tickers", boom)
    assert _real_resolve_universe("ALL") == fetcher.CATEGORIES["IDX80"]


# --- D: date safety ---------------------------------------------------------


def test_date_range_is_required(db, capsys):
    with pytest.raises(SystemExit):
        A.main(["--db", str(db), "--json"])


def test_inverted_date_range_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(["--db", str(db), "--date-from", "2025-06-01",
                    "--date-to", "2025-01-01", "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"


def test_equal_date_range_is_blocked_because_date_to_is_exclusive(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", DATES[0],
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"


def test_malformed_date_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(["--db", str(db), "--date-from", "02-01-2025", "--date-to", "2025-06-01",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"


def test_date_to_is_exclusive(db, capsys, no_subprocess, tmp_path):
    """Window [2025-01-02, 2025-01-03) covers exactly one calendar date."""
    rc, rep = _run(["--db", str(db), "--date-from", "2025-01-02", "--date-to", "2025-01-03",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["calendar"]["dates_in_window"] == 1
    assert rep["coverage_before"]["expected_ticker_days"] == 2  # 1 date x 2 tickers


def test_agent_never_widens_the_requested_range(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(["--db", str(db), "--date-from", "2025-01-03", "--date-to", "2025-01-07",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["calendar"]["dates_in_window"] == 2  # 01-03, 01-06 only
    cmd = " ".join(rep["proposed_command"])
    assert "--date-from 2025-01-03" in cmd and "--date-to 2025-01-07" in cmd


# --- E: coverage ------------------------------------------------------------


def test_zero_coverage(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    cov = rep["coverage_before"]
    assert cov["expected_ticker_days"] == 6
    assert cov["present_ticker_days"] == 0
    assert cov["complete_ticker_days"] == 0
    assert cov["missing_ticker_days"] == 6
    assert cov["coverage_pct"] == 0.0
    assert cov["dates_zero"] == DATES
    assert cov["dates_full"] == [] and cov["dates_partial"] == []


def test_partial_coverage(db, capsys, no_subprocess, tmp_path):
    conn = sqlite3.connect(db)
    _add_bars(conn, "BBCA", DATES[0])
    _add_bars(conn, "BBCA", DATES[1])
    _add_bars(conn, "BBRI", DATES[1])
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    cov = rep["coverage_before"]
    assert cov["complete_ticker_days"] == 3
    assert cov["missing_ticker_days"] == 3
    assert cov["coverage_pct"] == 50.0
    assert cov["dates_full"] == [DATES[1]]
    assert [p["date"] for p in cov["dates_partial"]] == [DATES[0]]
    assert cov["dates_zero"] == [DATES[2]]


def test_complete_coverage(db, capsys, no_subprocess, tmp_path):
    conn = sqlite3.connect(db)
    for d in DATES:
        for t in TICKERS:
            _add_bars(conn, t, d)
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["coverage_before"]["coverage_pct"] == 100.0
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_empty_session_counts_complete_but_not_as_bars(db, capsys, no_subprocess, tmp_path):
    """A genuinely empty session has no bars and never will — it must not be
    reported as a permanent gap (that is the fetcher's own predicate)."""
    conn = sqlite3.connect(db)
    for d in DATES:
        for t in TICKERS:
            _add_summary(conn, t, d, empty=True)
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    cov = rep["coverage_before"]
    assert cov["present_ticker_days"] == 0        # no bars rows at all
    assert cov["complete_ticker_days"] == 6       # all fetched, all legitimately empty
    assert rep["status"] == "COMPLETE"


def test_activity_summary_without_bars_is_not_complete(db, capsys, no_subprocess, tmp_path):
    """The exact defect the completion predicate exists to catch."""
    conn = sqlite3.connect(db)
    for d in DATES:
        for t in TICKERS:
            _add_summary(conn, t, d, empty=False)
    conn.commit()
    conn.close()
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["coverage_before"]["complete_ticker_days"] == 0
    assert rep["status"] == "PARTIAL"


def test_set_based_coverage_agrees_with_the_fetchers_own_predicate(db):
    """Guard against drift: the agent's bulk SQL must select exactly the cells
    tools/flow_bars_gap.py::bars_cell_complete selects, cell by cell."""
    conn = sqlite3.connect(db)
    _add_bars(conn, "BBCA", DATES[0])                  # bars -> complete
    _add_summary(conn, "BBCA", DATES[0], empty=False)  # + activity summary
    _add_summary(conn, "BBRI", DATES[0], empty=True)   # empty session -> complete
    _add_summary(conn, "BBCA", DATES[1], empty=False)  # activity, no bars -> INCOMPLETE
    conn.commit()

    ro = A.connect_ro(db)
    cov = A.compute_coverage(ro, TICKERS, DATES)
    agent_complete = {(t, d) for d, ts in cov.complete_by_date.items() for t in ts}
    predicate_complete = {(t, d) for d in DATES for t in TICKERS
                          if bars_cell_complete(conn, t, d)}
    ro.close()
    conn.close()
    assert agent_complete == predicate_complete


def test_calendar_divergence_from_ohlcv_is_reported(db, capsys, no_subprocess, tmp_path):
    """A trading_calendar date absent from ohlcv is unreachable by the fetcher,
    because the fetcher derives its work list from ohlcv."""
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES ('2025-01-07', 'test')")
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["calendar"]["unreachable_dates"] == ["2025-01-07"]


# --- M: canonical (IHSG-backed) trading dates -------------------------------
#
# data/market_schema.py defines trading_calendar as "IDX trading dates derived
# from IHSG bars" (build_trading_calendar inserts source='IHSG'), but
# screener/idx_scraper.py independently upserts source='scraper_eod' on every
# finalized EOD save. Those two authorities can disagree — measured on the
# production DB 2026-08-27: 1235 IHSG-backed rows, and exactly one row
# (2026-08-25, source='scraper_eod') with no IHSG bar at all. The agent must not
# demand IDX80 flow bars for a session the canonical authority never confirmed.


PHANTOM = "2025-01-07"   # calendar row + ohlcv rows, but NO IHSG bar


def _add_scraper_eod_row(conn, date, tickers=TICKERS):
    """Reproduce the 2026-08-25 shape: a scraper_eod calendar row plus finalized
    per-ticker ohlcv, but no IHSG bar for that date."""
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'scraper_eod')",
                 (date,))
    for t in tickers:
        conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES (?, ?, 1)", (t, date))


def test_scraper_eod_row_without_ihsg_is_not_an_expected_session(
        db, capsys, no_subprocess, tmp_path):
    """The exact 2026-08-25 case: a calendar row the IHSG authority never
    confirmed must not inflate expected_ticker_days."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    cal = rep["calendar"]
    assert cal["calendar_rows_in_window"] == 4          # the row is NOT hidden
    assert cal["dates_in_window"] == 3                  # but it is not expected
    assert [x["date"] for x in cal["non_ihsg_dates"]] == [PHANTOM]
    assert cal["non_ihsg_dates"][0]["source"] == "scraper_eod"
    assert rep["coverage_before"]["expected_ticker_days"] == 6   # 3 dates x 2
    assert PHANTOM not in rep["coverage_before"]["dates_zero"]


def test_non_ihsg_calendar_row_is_reported_not_silently_dropped(
        db, capsys, no_subprocess, tmp_path):
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert any(PHANTOM in n and "IHSG" in n for n in rep["notes"])


def test_ihsg_backed_date_remains_expected(db, capsys, no_subprocess, tmp_path):
    """The exclusion is keyed on the IHSG bar, not on the source string: a date
    that *does* have an IHSG bar stays expected whatever its calendar source."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)", (PHANTOM,))
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["calendar"]["dates_in_window"] == 4
    assert rep["calendar"]["non_ihsg_dates"] == []
    assert rep["coverage_before"]["expected_ticker_days"] == 8
    assert PHANTOM in rep["coverage_before"]["dates_zero"]


def test_non_ihsg_date_does_not_hold_a_covered_window_at_partial(
        db, capsys, no_subprocess, tmp_path):
    """Operational payoff: with every canonical session covered, an unconfirmed
    scraper_eod row must not keep the verdict at PARTIAL forever."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    for d in DATES:
        for t in TICKERS:
            _add_bars(conn, t, d)
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["coverage_before"]["missing_ticker_days"] == 0
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_window_of_only_non_ihsg_calendar_rows_is_blocked(
        db, capsys, no_subprocess, tmp_path):
    """Nothing canonical to plan — refuse rather than report a vacuous COMPLETE."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", PHANTOM, "--date-to", "2025-01-08",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"
    assert rc == A.EXIT_BLOCKED
    assert any("IHSG" in r for r in rep["reasons"])


def test_bars_cell_complete_semantics_are_untouched_by_the_calendar_change(db):
    """The calendar fix changes WHICH cells are expected, never what makes a
    cell complete. Re-assert the predicate contract on the phantom date too."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)
    _add_bars(conn, "BBCA", PHANTOM)
    _add_summary(conn, "BBRI", PHANTOM, empty=True)
    conn.commit()
    assert bars_cell_complete(conn, "BBCA", PHANTOM) is True
    assert bars_cell_complete(conn, "BBRI", PHANTOM) is True
    assert bars_cell_complete(conn, "BBCA", DATES[0]) is False
    conn.close()


# --- F: no false completion -------------------------------------------------


def test_child_exit_zero_that_leaves_cells_incomplete_is_never_complete(
        db, capsys, monkeypatch, tmp_path):
    """The single most important guarantee, at date level: a child that exits
    0 while its date's cells stay incomplete (the old whole-window 'planned
    budget stop' shape) must never read as SUCCESS/COMPLETE."""
    monkeypatch.setattr(A, "run_date_child",
                        lambda cmd, conn, tickers, date, **kw:
                        A.ChildResult(0, 1.0, False, False))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["FAILED"] * 3
    assert any("remain incomplete" in r for r in rep["reasons"])
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


def test_nonzero_exit_is_failed(db, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(A, "run_date_child",
                        lambda cmd, conn, tickers, date, **kw:
                        A.ChildResult(3, 1.0, False, False))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["FAILED"] * 3
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


def test_child_failure_is_failed_even_when_the_db_ends_up_complete(
        db, capsys, monkeypatch, tmp_path):
    """A nonzero child exit is authoritative: it is never masked by coverage
    that happens to look complete afterwards."""
    def fake(cmd, conn, tickers, date, **kw):
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        return A.ChildResult(2, 1.0, False, False)

    monkeypatch.setattr(A, "run_date_child", fake)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["FAILED"] * 3
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


def test_execute_reports_complete_only_when_coverage_is_complete(db, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(A, "run_date_child", _success_child(db))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert rep["coverage_before"]["complete_ticker_days"] == 0
    assert rep["coverage_after"]["complete_ticker_days"] == 6
    assert rep["status"] == "COMPLETE"


def test_timeout_is_failed(db, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(A, "run_date_child",
                        lambda cmd, conn, tickers, date, **kw:
                        A.ChildResult(None, 99.0, True, False))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["FAILED"] * 3
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


# --- G: existing-data safety ------------------------------------------------


def test_destructive_sql_in_the_runner_blocks_execution(db, capsys, no_subprocess, tmp_path):
    bad = tmp_path / "fake_runner.py"
    bad.write_text('conn.execute("DELETE FROM stockbit_flow_bars WHERE trade_date=?")\n')
    rc, rep = _run(_args(db, "--runner", str(bad), lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("destructive" in r.lower() for r in rep["reasons"])


def test_real_runner_passes_the_destructive_sql_scan():
    assert A.scan_runner_for_destructive_sql(A.DEFAULT_RUNNER) == []


def test_runner_db_path_is_read_from_the_real_runner_source(monkeypatch):
    monkeypatch.undo()  # drop the autouse alignment fixture
    assert A.runner_db_path(A.DEFAULT_RUNNER) == A.HERE / "data" / "walkforward.db"


def test_execute_blocked_when_the_audit_db_is_not_the_runners_db(
        db, capsys, no_subprocess, monkeypatch, tmp_path):
    """Auditing a different file than the runner writes would make the
    post-run COMPLETE/PARTIAL verdict meaningless."""
    monkeypatch.setattr(A, "runner_db_path", lambda runner: tmp_path / "other.db")
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("runner writes" in r.lower() for r in rep["reasons"])


def test_plan_only_notes_a_db_mismatch_and_does_not_block(
        db, capsys, no_subprocess, monkeypatch, tmp_path):
    monkeypatch.setattr(A, "runner_db_path", lambda runner: tmp_path / "other.db")
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["status"] != "BLOCKED"
    assert any("runner writes" in n.lower() for n in rep["notes"])


# --- H: concurrent-run coordination -----------------------------------------


def test_another_backfill_process_blocks_execution(db, capsys, monkeypatch, no_subprocess, tmp_path):
    monkeypatch.setattr(A, "other_backfill_pids", lambda: [4242])
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("4242" in r for r in rep["reasons"])


def test_held_lock_blocks_execution(db, capsys, no_subprocess, tmp_path):
    lock = tmp_path / "agent.lock"
    holder = open(lock, "w")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG, lock=lock), capsys)
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()
    assert rep["status"] == "BLOCKED"
    assert any("lock" in r.lower() for r in rep["reasons"])


def test_hand_launched_process_appearing_mid_execution_aborts_remaining_dates(
        db, capsys, monkeypatch, tmp_path):
    """The /proc concurrency guard must not be a start-of-run snapshot only:
    a bare runner hand-launched between dates during a long execute must be
    detected and stop further dates, not just at start-of-run."""
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        # 2 pre-flight checks pass clean; the per-date recheck before the
        # SECOND date discovers a hand-launched process.
        return [] if calls["n"] <= 3 else [99999]

    monkeypatch.setattr(A, "other_backfill_pids", flaky)
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [d for d, _ in launched] == [DATES[0]]   # aborted before DATES[1]/[2]
    assert rep["status"] == "BLOCKED"
    assert rc == A.EXIT_BLOCKED
    assert any("99999" in r for r in rep["reasons"])


# --- I: budget --------------------------------------------------------------


def test_budget_above_the_hard_cap_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--budget-s", "99999", lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"
    assert any("18000" in r for r in rep["reasons"])


def test_non_positive_budget_is_blocked(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--budget-s", "0", lock=tmp_path / "l"), capsys)
    assert rep["status"] == "BLOCKED"


def test_budget_at_the_hard_cap_is_accepted(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, "--budget-s", str(A.HARD_CAP_S), lock=tmp_path / "l"), capsys)
    assert rep["status"] != "BLOCKED"
    assert "--budget-s 18000" in " ".join(rep["proposed_command"])


def test_agent_constants_match_the_runners():
    """The agent duplicates these to avoid importing the vendor client; the
    copies must never drift."""
    import tools.backfill_flow_bars as B
    assert A.HARD_CAP_S == B.HARD_CAP_S
    assert A.FROZEN_FIXTURE_DATES == B.FROZEN_FIXTURE_DATES


# --- J: probe ---------------------------------------------------------------


def test_probe_passes_probe_flag_and_is_not_coverage_evidence(db, capsys, monkeypatch, tmp_path):
    seen = {}

    def fake(cmd, timeout):
        seen["cmd"] = cmd
        return A.RunResult(0, 1.0, False)

    monkeypatch.setattr(A, "run_backfill", fake)
    rc, rep = _run(_args(db, "--action", "probe", A.CONFIRM_FLAG, lock=tmp_path / "l"), capsys)
    assert "--probe" in seen["cmd"]
    assert rep["status"] == "PARTIAL"          # coverage is still empty
    assert any("probe" in n.lower() for n in rep["notes"])


# --- K: dry-run plan content ------------------------------------------------


def test_plan_contains_every_required_field(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    for key in ("category", "date_from", "date_to", "date_to_exclusive",
                "coverage_before", "proposed_command", "safety_checks",
                "execution_allowed", "status"):
        assert key in rep, key
    assert rep["date_to_exclusive"] is True
    assert rep["execution_allowed"] is True


def test_plan_reports_execution_not_allowed_when_blocked(db, capsys, monkeypatch, no_subprocess, tmp_path):
    monkeypatch.setattr(A, "other_backfill_pids", lambda: [4242])
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["execution_allowed"] is False


# --- frozen fixture ---------------------------------------------------------


def test_agent_never_passes_release_fixture(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert "--release-fixture" not in rep["proposed_command"]


def test_window_targeting_only_the_frozen_fixture_is_blocked(db, capsys, no_subprocess, tmp_path):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'test')",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", A.FROZEN_FIXTURE_DATES[0],
                    "--date-to", "2025-04-15", "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"
    assert any("fixture" in r.lower() for r in rep["reasons"])


def test_fixture_barrier_recommends_the_split_windows(db, capsys, no_subprocess, tmp_path):
    """The runner `break`s the whole date loop at the barrier, so every date
    AFTER the fixture is unreachable in one invocation. Say what to run."""
    conn = sqlite3.connect(db)
    for d in (A.FROZEN_FIXTURE_DATES[0], "2025-04-16"):
        conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'test')", (d,))
        conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)", (d,))
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-04-17",
                    "--lock-file", str(tmp_path / "l")], capsys)
    split = rep["fixture_barrier"]
    assert split["dates_after_barrier"] == 1
    assert split["split_windows"] == [[DATES[0], "2025-04-14"], ["2025-04-15", "2025-04-17"]]


def test_no_fixture_barrier_block_when_fixture_is_outside_the_window(db, capsys, no_subprocess, tmp_path):
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["fixture_barrier"] is None


def test_fixture_inside_a_wider_window_warns_but_does_not_block(db, capsys, no_subprocess, tmp_path):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'test')",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.commit()
    conn.close()
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0], "--date-to", "2025-04-15",
                    "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] != "BLOCKED"
    assert any("barrier" in n.lower() for n in rep["notes"])


# --- L: structured output ---------------------------------------------------


def test_human_output_is_default_and_json_is_opt_in(db, capsys, no_subprocess, tmp_path):
    A.main(_args(db, lock=tmp_path / "l"))
    out = capsys.readouterr().out
    assert "IDX80" in out and "Coverage" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_missing_db_is_blocked(tmp_path, capsys, no_subprocess):
    rc, rep = _run(["--db", str(tmp_path / "nope.db"), "--date-from", DATES[0],
                    "--date-to", "2025-01-07", "--lock-file", str(tmp_path / "l")], capsys)
    assert rep["status"] == "BLOCKED"
    assert rc == A.EXIT_BLOCKED


# --- N: supervised date-level execution -------------------------------------
#
# Execute mode runs the production runner EXACTLY ONE TRADING DATE at a time,
# with per-date wall-clock and no-progress supervision, DB-derived resume, and
# failure isolation. The supervisor loop is exercised through a mocked
# run_date_child; the timeout/stall mechanics themselves are exercised by
# driving run_date_child with a fake process.


def _window_of(cmd):
    return cmd[cmd.index("--date-from") + 1], cmd[cmd.index("--date-to") + 1]


def _success_child(db, launched=None):
    """A fake run_date_child that fills the date's cells and succeeds.

    It also asserts the supervisor handed it EXACTLY one date: the child's
    --date-to must be the day after its --date-from.
    """
    def fake(cmd, conn, tickers, date, **kw):
        lo, hi = _window_of(cmd)
        assert lo == date
        assert hi == A.next_day(date)
        if launched is not None:
            launched.append((date, cmd))
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        return A.ChildResult(0, 0.5, False, False)
    return fake


def test_execute_launches_one_child_per_date_each_covering_exactly_one_date(
        db, capsys, monkeypatch, tmp_path):
    """Requirements A(1)+A(2)+4: multi-date execution is split into individual
    dates, every child covers exactly one date, and each successful date is
    verified before continuing."""
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [d for d, _ in launched] == DATES          # calendar order, one each
    for d, cmd in launched:
        lo, hi = _window_of(cmd)
        assert lo == d and hi == A.next_day(d)        # EXACTLY one date
        joined = " ".join(cmd)
        assert "--cat IDX80" in joined
        assert f"--budget-s {A.DEFAULT_BUDGET_S}" in joined
        assert "--probe" not in joined and "--release-fixture" not in joined
    assert rep["execution"]["model"] == "per_date"
    assert rep["date_summary"] == {"total": 3, "success": 3, "skipped": 0,
                                   "failed": 0, "stalled": 0, "launched": 3}
    assert rep["coverage_after"]["missing_ticker_days"] == 0
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_completed_date_is_skipped_and_not_launched(db, capsys, monkeypatch, tmp_path):
    """Requirement 3: a date already complete per the coverage predicate is
    skipped, never handed to a child."""
    conn = sqlite3.connect(db)
    for t in TICKERS:
        _add_bars(conn, t, DATES[0])
    conn.commit()
    conn.close()
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [d for d, _ in launched] == DATES[1:]
    assert rep["dates"][0]["outcome"] == "SKIPPED"
    assert rep["dates"][0]["reason"] == "already complete per the coverage predicate"
    assert rep["date_summary"]["skipped"] == 1
    assert rep["status"] == "COMPLETE"


def test_execute_with_every_date_complete_launches_nothing(db, capsys, monkeypatch, tmp_path):
    conn = sqlite3.connect(db)
    for d in DATES:
        for t in TICKERS:
            _add_bars(conn, t, d)
    conn.commit()
    conn.close()

    def boom(cmd, conn, tickers, date, **kw):
        raise AssertionError(f"child launched for already-complete date {date}")

    monkeypatch.setattr(A, "run_date_child", boom)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert rep["date_summary"]["skipped"] == 3
    assert rep["vendor_calls_made"] is False
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_resume_is_derived_from_the_db_across_invocations(db, capsys, monkeypatch, tmp_path):
    """Requirement 9: resume state comes from the database, not from a cursor.
    A second invocation starts fresh and re-derives what is left from the DB
    state the first run left behind."""
    def fake(cmd, conn, tickers, date, **kw):
        if date == DATES[2]:
            return A.ChildResult(None, 5.0, False, True)      # stalls
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        return A.ChildResult(0, 0.5, False, False)

    monkeypatch.setattr(A, "run_date_child", fake)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["SUCCESS", "SUCCESS", "STALLED"]
    assert rep["status"] == "FAILED"

    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc2, rep2 = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                           lock=tmp_path / "l"), capsys)
    assert [d for d, _ in launched] == [DATES[2]]     # only the stalled date
    assert [o["outcome"] for o in rep2["dates"]] == ["SKIPPED", "SKIPPED", "SUCCESS"]
    assert rep2["status"] == "COMPLETE"
    assert rc2 == A.EXIT_COMPLETE


def test_stalled_date_does_not_block_the_next_date(db, capsys, monkeypatch, tmp_path):
    """Requirement 7: a stalled date is recorded STALLED and the next date is
    still attempted; the run never claims COMPLETE."""
    def fake(cmd, conn, tickers, date, **kw):
        if date == DATES[0]:
            return A.ChildResult(None, 5.0, False, True)      # STALLED
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        return A.ChildResult(0, 0.5, False, False)

    monkeypatch.setattr(A, "run_date_child", fake)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["STALLED", "SUCCESS", "SUCCESS"]
    assert rep["date_summary"]["stalled"] == 1
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


def test_failed_date_does_not_block_the_next_date(db, capsys, monkeypatch, tmp_path):
    """Requirement 8: a failed date is recorded FAILED and the next date is
    still attempted."""
    def fake(cmd, conn, tickers, date, **kw):
        if date == DATES[0]:
            return A.ChildResult(3, 1.0, False, False)       # FAILED
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        return A.ChildResult(0, 0.5, False, False)

    monkeypatch.setattr(A, "run_date_child", fake)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert [o["outcome"] for o in rep["dates"]] == ["FAILED", "SUCCESS", "SUCCESS"]
    assert rep["date_summary"]["failed"] == 1
    assert rep["status"] == "FAILED"
    assert rc == A.EXIT_FAILED


def test_children_are_never_run_concurrently(db, capsys, monkeypatch, tmp_path):
    """Requirement 10: the supervisor awaits each date child before launching
    the next one — the peak number of simultaneously-live children is 1."""
    active = [0]
    peak = [0]

    def fake(cmd, conn, tickers, date, **kw):
        active[0] += 1
        peak[0] = max(peak[0], active[0])
        time.sleep(0.02)
        c = sqlite3.connect(db)
        for t in tickers:
            _add_bars(c, t, date)
        c.commit()
        c.close()
        active[0] -= 1
        return A.ChildResult(0, 0.1, False, False)

    monkeypatch.setattr(A, "run_date_child", fake)
    rc, rep = _run(_args(db, "--action", "execute", A.CONFIRM_FLAG,
                         lock=tmp_path / "l"), capsys)
    assert peak[0] == 1
    assert rep["status"] == "COMPLETE"


def test_execute_never_launches_a_child_for_the_frozen_fixture(
        db, capsys, monkeypatch, tmp_path):
    """Requirement 11: the frozen fixture date is never targeted by a child;
    its cells stay reserved, so a window containing it is never COMPLETE."""
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'test')",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.execute("INSERT INTO ohlcv (ticker, date, close) VALUES ('IHSG', ?, 1)",
                 (A.FROZEN_FIXTURE_DATES[0],))
    conn.commit()
    conn.close()
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0],
                    "--date-to", "2025-04-15", "--action", "execute",
                    A.CONFIRM_FLAG, "--lock-file", str(tmp_path / "l")], capsys)
    assert A.FROZEN_FIXTURE_DATES[0] not in [d for d, _ in launched]
    assert rep["fixture_dates_excluded"] == [A.FROZEN_FIXTURE_DATES[0]]
    assert rep["status"] == "PARTIAL"                 # fixture cells missing
    assert rc == A.EXIT_PARTIAL


def test_non_ihsg_date_is_excluded_from_per_date_execution(
        db, capsys, monkeypatch, tmp_path):
    """Requirement 12 (the 2026-08-25 case): a trading_calendar row without an
    IHSG bar is not an expected session, so no child is ever launched for it —
    the exclusion comes from the canonical IHSG-backed calendar, never from a
    hard-coded holiday."""
    conn = sqlite3.connect(db)
    _add_scraper_eod_row(conn, PHANTOM)               # calendar row, ohlcv, NO IHSG bar
    conn.commit()
    conn.close()
    launched = []
    monkeypatch.setattr(A, "run_date_child", _success_child(db, launched))
    rc, rep = _run(["--db", str(db), "--date-from", DATES[0],
                    "--date-to", "2025-01-08", "--action", "execute",
                    A.CONFIRM_FLAG, "--lock-file", str(tmp_path / "l")], capsys)
    assert [d for d, _ in launched] == DATES          # phantom never launched
    assert [x["date"] for x in rep["calendar"]["non_ihsg_dates"]] == [PHANTOM]
    assert rep["status"] == "COMPLETE"
    assert rc == A.EXIT_COMPLETE


def test_non_positive_or_inverted_timeout_params_are_blocked(db, capsys, no_subprocess, tmp_path):
    for extra in (["--date-timeout-s", "0"],
                  ["--no-progress-timeout-s", "0"],
                  ["--date-timeout-s", "10", "--no-progress-timeout-s", "20"]):
        rc, rep = _run(_args(db, *extra, lock=tmp_path / "l"), capsys)
        assert rep["status"] == "BLOCKED"
        assert any("timeout" in r.lower() for r in rep["reasons"])


class FakeProc:
    """Deterministic stand-in for subprocess.Popen in run_date_child tests.

    poll() can simulate a child making progress (writing complete cells) or
    staying alive forever; wait() can simulate a child that ignores SIGTERM.
    """

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
                _add_bars(c, t, self.date)
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


def test_date_wall_clock_timeout_kills_the_child(db, capsys):
    """Requirement 5: a child that stays alive past --date-timeout-s is
    terminated and the date reported timed out — even while it is making
    progress."""
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=True)
    res = _run_date_child_with(fake, db, date_timeout_s=0.5, no_progress_s=600)
    assert res.timed_out is True and res.stalled is False
    assert res.returncode is None
    assert fake.terminated is True


def test_no_progress_timeout_marks_the_date_stalled(db, capsys):
    """Requirement 6: a child that stays alive without a single newly-complete
    cell is terminated and the date reported stalled."""
    fake = FakeProc(db=db, tickers=TICKERS, date=DATES[0], write_progress=False)
    res = _run_date_child_with(fake, db, date_timeout_s=600, no_progress_s=0.5)
    assert res.stalled is True and res.timed_out is False
    assert res.returncode is None
    assert fake.terminated is True


def test_successful_child_is_not_killed(db, capsys):
    fake = FakeProc(exit_after=1)
    res = _run_date_child_with(fake, db)
    assert res.returncode == 0
    assert res.timed_out is False and res.stalled is False
    assert fake.terminated is False and fake.killed is False


def test_stubborn_child_is_killed_after_the_grace_period(db, capsys, monkeypatch):
    """A child that ignores SIGTERM is escalated to SIGKILL, never leaked."""
    monkeypatch.setattr(A, "KILL_GRACE_S", 0.05)
    fake = FakeProc(block_grace_wait=True)
    res = _run_date_child_with(fake, db, date_timeout_s=0.3, no_progress_s=600)
    assert res.timed_out is True
    assert fake.terminated is True and fake.killed is True


def test_plan_report_has_no_date_children(db, capsys, no_subprocess, tmp_path):
    """Requirement 14: plan mode stays read-only — no dates[], no execution
    model, no subprocess."""
    rc, rep = _run(_args(db, lock=tmp_path / "l"), capsys)
    assert rep["dates"] is None
    assert rep["execution"] is None
    assert rep["subprocess"] is None
    assert rep["status"] != "FAILED"
