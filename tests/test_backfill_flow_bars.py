"""Regression tests for tools/backfill_flow_bars.py (Day-1 blockers B2/B3,
2026-08-21): 5-hour budget boundary arithmetic, exit-code signalling, and the
frozen discrimination-fixture barrier. All external effects (DB, vendor,
token) are monkeypatched — these tests never touch network or walkforward.db.
"""
import sqlite3

import pytest

import tools.backfill_flow_bars as B

DATE = "2025-04-14"          # the frozen fixture
OTHER = "2025-01-02"


@pytest.fixture(autouse=True)
def quiet_log(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "LOG_PATH", tmp_path / "test_backfill.log")


@pytest.fixture
def sandbox(monkeypatch):
    """Neuter every external effect; return a call-counter dict.

    Default world: one non-fixture date, two tickers, valid token, every cell
    incomplete, fetch and write succeed.
    """
    calls = {"fetch": 0, "write": 0}
    conn = sqlite3.connect(":memory:")
    monkeypatch.setattr(B, "gap_dates", lambda f, t: [OTHER])
    monkeypatch.setattr(B, "bars_cell_complete", lambda c, t, d: False)
    monkeypatch.setattr(B.sf, "get_tickers", lambda cat: ["BBCA", "ABDA"])
    monkeypatch.setattr(B.sf, "init_flow_db", lambda: conn)
    monkeypatch.setattr(B.sf, "ensure_valid_token", lambda *a, **k: "TOKEN")
    monkeypatch.setattr(B.sf, "verify_token", lambda t: True)

    def fake_fetch(token, ticker, date=None):
        calls["fetch"] += 1
        return {"ticker": ticker, "trade_date": date, "buy_lot": 1, "sell_lot": 0,
                "net_lot": 1, "buy_freq": 1, "sell_freq": 0, "net_value": 0,
                "last_price": None, "_raw_data": None}

    def fake_write(c, flow):
        calls["write"] += 1

    monkeypatch.setattr(B.sf, "fetch_flow", fake_fetch)
    monkeypatch.setattr(B, "_write", fake_write)
    monkeypatch.setattr(B, "RATE_DELAY", 0)
    return calls


# --- B3: 5-hour boundary arithmetic -----------------------------------------


def test_margin_covers_documented_worst_case_cell():
    assert B.WORST_CASE_CELL_S == 260
    assert B.CELL_MARGIN_S >= B.WORST_CASE_CELL_S


def test_budget_clamped_to_5h_hard_cap():
    assert B.HARD_CAP_S == 5 * 3600
    assert B.effective_budget(999_999) == B.HARD_CAP_S
    assert B.effective_budget(1_000) == 1_000


def test_structural_5h_guarantee():
    """A cell started at the last permitted instant plus the worst-case
    in-flight cell must still finish inside the hard cap."""
    last_start = B.HARD_CAP_S - B.CELL_MARGIN_S
    assert last_start + B.WORST_CASE_CELL_S <= B.HARD_CAP_S


def test_budget_boundary_exact_edges():
    t0 = 1000.0
    # budget 1000 > margin 300 -> full margin applies
    assert B.budget_expired(t0, 1000, now=t0 + 699) is False   # last allowed start
    assert B.budget_expired(t0, 1000, now=t0 + 700) is False   # boundary itself
    assert B.budget_expired(t0, 1000, now=t0 + 701) is True    # one second past
    # deliberately small budget: reduced margin, bounded overshoot allowed
    assert B.effective_margin(90) == 15
    assert B.effective_margin(300) == 50
    assert B.effective_margin(301) == B.CELL_MARGIN_S


# --- B2: exit-code signalling ------------------------------------------------


def test_auth_failure_at_launch_exits_nonzero(sandbox, monkeypatch):
    monkeypatch.setattr(B.sf, "ensure_valid_token", lambda *a, **k: None)
    assert B.main([]) == B.EXIT_AUTH


def test_auth_failure_midrun_exits_nonzero(sandbox, monkeypatch):
    monkeypatch.setattr(B.sf, "verify_token", lambda t: False)
    monkeypatch.setattr(B.sf, "ensure_valid_token", lambda *a, **k: None)
    assert B.main(["--date-from", OTHER, "--date-to", "2025-01-03"]) == B.EXIT_AUTH


def test_sustained_fetch_failure_exits_nonzero(sandbox, monkeypatch):
    monkeypatch.setattr(B, "SUSTAINED_FAIL_LIMIT", 2)
    monkeypatch.setattr(B.sf, "fetch_flow", lambda *a, **k: None)
    # trips on the 2nd consecutive failure (checkpoint logs nodata=2)
    assert B.main(["--date-from", OTHER, "--date-to", "2025-01-03"]) == B.EXIT_SUSTAINED


def test_db_error_on_fetch_exits_nonzero(sandbox, monkeypatch):
    def boom(*a, **k):
        raise sqlite3.OperationalError("locked")
    monkeypatch.setattr(B.sf, "fetch_flow", boom)
    assert B.main(["--date-from", OTHER, "--date-to", "2025-01-03"]) == B.EXIT_DB


def test_db_error_on_write_exits_nonzero(sandbox, monkeypatch):
    def boom(c, flow):
        raise sqlite3.OperationalError("disk full")
    monkeypatch.setattr(B, "_write", boom)
    assert B.main(["--date-from", OTHER, "--date-to", "2025-01-03"]) == B.EXIT_DB
    assert sandbox["fetch"] == 1


def test_planned_budget_stop_is_success(sandbox):
    assert B.main(["--budget-s", "1"]) == B.EXIT_OK
    assert sandbox["fetch"] == 0  # expired before the first cell


def test_completes_and_writes_with_exit_zero(sandbox):
    assert B.main(["--date-from", OTHER, "--date-to", "2025-01-03"]) == B.EXIT_OK
    assert sandbox["fetch"] == 2 and sandbox["write"] == 2


# --- frozen discrimination fixture ------------------------------------------


def test_targeting_frozen_fixture_without_release_refused(sandbox, monkeypatch):
    monkeypatch.setattr(B, "gap_dates", lambda f, t: [DATE])

    def no_fetch(*a, **k):
        raise AssertionError("vendor call on frozen fixture!")
    monkeypatch.setattr(B.sf, "fetch_flow", no_fetch)
    assert B.main(["--date-from", DATE, "--date-to", "2025-04-15"]) == B.EXIT_FROZEN_FIXTURE
    assert sandbox["fetch"] == 0


def test_frozen_fixture_is_a_barrier_not_consumed(sandbox, monkeypatch):
    monkeypatch.setattr(B, "gap_dates", lambda f, t: [OTHER, DATE])
    monkeypatch.setattr(B, "bars_cell_complete", lambda c, t, d: True)

    def no_fetch(*a, **k):
        raise AssertionError("vendor call despite barrier/skip!")
    monkeypatch.setattr(B.sf, "fetch_flow", no_fetch)
    assert B.main(["--date-from", OTHER, "--date-to", "2025-04-15"]) == B.EXIT_OK
    assert sandbox["fetch"] == 0


def test_release_fixture_processes_it(sandbox, monkeypatch):
    monkeypatch.setattr(B, "gap_dates", lambda f, t: [DATE])
    assert B.main(["--date-from", DATE, "--date-to", "2025-04-15",
                   "--release-fixture"]) == B.EXIT_OK
    assert sandbox["fetch"] == 2  # both tickers fetched on the fixture date
