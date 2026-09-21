"""Tests for the PIT dynamic-universe planning layer
(tools/broker_flow_pit_planning.py) and the `--universe pit` mode of
tools/backfill_broker_flow_idx80.py.

Core principle under test: "IDX80" is the index name, not a promise that the
roster is 80 names on every historical date. For data collection, the PIT
roster is the authority (never truncated, never padded, never substituted by
today's idx_tickers); for research eligibility, confidence tiers still gate
(members_as_of never returns UNRESOLVED).

No network access: stockbit_fetcher.fetch_broker_flow is monkeypatched.
"""
import sqlite3

import pytest

import stockbit_fetcher as sf
from research.idx80_membership import (
    members_as_of, members_as_of_all_evidence,
)
import tools.backfill_broker_flow_idx80 as R
from tools.broker_flow_pit_planning import (
    required_members, pit_gap_plan, expected_nominal_count,
)

# --- synthetic PIT ledger (same schema as the live WP-D tables) -----------
# PA  PRIMARY_VERIFIED       80 members   2025-01-02 .. 2025-01-31 (inclusive)
# PB  UNRESOLVED             81 members   2025-02-01 .. 2025-02-28 (P2 analog)
# PC  PRIMARY_VERIFIED       79 members   2025-03-01 .. 2025-03-31
# PD  BRACKETED_RECONSTRUCTED 80 members  2025-04-01 .. 2025-04-30
PERIODS = [
    ("PA", "2025-01-02", "2025-01-31", "PRIMARY_VERIFIED", 80),
    ("PB", "2025-02-01", "2025-02-28", "UNRESOLVED", 81),
    ("PC", "2025-03-01", "2025-03-31", "PRIMARY_VERIFIED", 79),
    ("PD", "2025-04-01", "2025-04-30", "BRACKETED_RECONSTRUCTED", 80),
]

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
CREATE TABLE idx80_reconstitution_periods (
    period_label TEXT PRIMARY KEY, effective_from TEXT NOT NULL,
    effective_to TEXT, left_censored INTEGER NOT NULL DEFAULT 0,
    constituent_count INTEGER NOT NULL, confidence TEXT NOT NULL,
    source TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL);
CREATE TABLE idx80_membership_history (
    ticker TEXT NOT NULL, period_label TEXT NOT NULL,
    effective_from TEXT NOT NULL, effective_to TEXT,
    membership_status TEXT NOT NULL DEFAULT 'MEMBER',
    confidence TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY (ticker, period_label));
"""

CANON_DATES = ["2025-01-02", "2025-01-03",           # PA
               "2025-02-02", "2025-02-03",           # PB
               "2025-03-02",                          # PC
               "2025-04-30"]                          # PD (== effective_to)


def _members_for(period, n):
    return [f"{period}{i:03d}" for i in range(n)]


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    for label, f, t, conf, n in PERIODS:
        c.execute("INSERT INTO idx80_reconstitution_periods (period_label, "
                  "effective_from, effective_to, left_censored, "
                  "constituent_count, confidence, source, notes, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?)",
                  (label, f, t, 0, n, conf, "fixture", None, "2026-08-31"))
        for tkr in _members_for(label, n):
            c.execute("INSERT INTO idx80_membership_history (ticker, "
                      "period_label, effective_from, effective_to, "
                      "membership_status, confidence, source, created_at) "
                      "VALUES (?,?,?,?, 'MEMBER', ?, 'fixture', '2026-08-31')",
                      (tkr, label, f, t, conf))
    # today's live roster: two names, NEITHER in any PIT period except LIVE1==PA000
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) "
              "VALUES ('LIVE1','active',1)")   # also a PA member (PA000 alias? no: distinct)
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) "
              "VALUES ('LIVE2','active',1)")   # in NO PIT period at all
    c.execute("INSERT INTO idx_tickers (ticker, status, in_idx80) "
              "VALUES ('GONE','inactive',0)")  # historical name, no longer active
    for d in CANON_DATES:
        c.execute("INSERT INTO ohlcv (ticker, date) VALUES ('IHSG', ?)", (d,))
        c.execute("INSERT INTO trading_calendar (date, source) VALUES (?, 'IHSG')", (d,))
    # completed cells on 2025-01-02: PA000 via broker_flow row, PA001 via
    # bandar_detector confirmed-empty marker
    c.execute("INSERT INTO broker_flow (ticker, trade_date, broker_code, side, "
              "lot, lot_value, value, value_total, avg_price, freq, "
              "investor_type) VALUES ('PA000','2025-01-02','ZP','BUY',1,1,2,3,"
              "9000.0,4,'Asing')")
    c.execute("INSERT INTO bandar_detector (ticker, trade_date, value, volume) "
              "VALUES ('PA001','2025-01-02',0,0)")
    c.commit()
    monkeypatch.setattr(R.time, "sleep", lambda *a, **k: None)
    yield c
    c.close()


def _no_vendor_calls(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("vendor called")
    monkeypatch.setattr(sf, "fetch_broker_flow", boom)


# --- requirement: nominal size is metadata, not a filter ------------------

def test_expected_nominal_count_is_metadata_constant():
    assert expected_nominal_count() == 80


# --- 1. 80-member PIT date -------------------------------------------------

def test_pit_date_with_80_members_resolves_all_80_no_advisory(conn):
    members, advisory = required_members(conn, "2025-01-02")
    assert len(members) == 80
    assert advisory is None
    assert members[0] == "PA000" and "PA079" in members


# --- 2. 81-member PIT date (UNRESOLVED period, collection authority) -------

def test_pit_date_with_81_members_fetches_all_81_and_warns(conn):
    members, advisory = required_members(conn, "2025-02-02")
    assert len(members) == 81
    assert advisory is not None
    assert advisory["member_count"] == 81
    assert advisory["expected_nominal_count"] == 80
    assert advisory["confidence"] == "UNRESOLVED"
    assert advisory["period_label"] == "PB"
    assert "No members dropped" in advisory["message"]


# --- 3. <80-member PIT date -------------------------------------------------

def test_pit_date_with_79_members_fetches_all_79_and_warns(conn):
    members, advisory = required_members(conn, "2025-03-02")
    assert len(members) == 79
    assert advisory is not None
    assert "no members invented" in advisory["message"]
    assert advisory["member_count"] == 79


# --- 4. historical ticker absent from today's idx_tickers ------------------

def test_historical_member_absent_from_live_roster_is_still_required(conn):
    members, _ = required_members(conn, "2025-01-02")
    live = {r[0] for r in conn.execute(
        "SELECT ticker FROM idx_tickers WHERE status='active' AND in_idx80=1")}
    # PA roster contains many names that are NOT in the live roster at all
    assert "PA005" in members
    assert "PA005" not in live
    # and the plan requires them
    need = [t for t in members
            if not conn.execute("SELECT 1 FROM broker_flow WHERE ticker=? AND "
                                "trade_date='2025-01-02'", (t,)).fetchone()]
    assert "PA005" in need


# --- 5. no fallback to today's idx_tickers ---------------------------------

def test_no_pit_period_means_no_members_no_live_fallback(conn):
    members, advisory = required_members(conn, "2025-06-01")
    assert members == []
    assert advisory is not None
    assert advisory["member_count"] == 0
    # the live roster would have been ['LIVE1','LIVE2'] -- never substituted
    assert "LIVE1" not in members and "LIVE2" not in members


def test_runner_pit_mode_never_fetches_live_only_names(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None:
                        calls.append((ticker, date)) or
                        _populated(ticker, date))
    R.run("2025-06-01", "2025-06-02", conn=conn, token="tok",
          universe_mode="pit")
    assert calls == []          # uncovered date: nothing fetched, no fallback


# --- 6. no truncation when roster > 80 --------------------------------------

def test_no_truncation_on_81_member_roster(conn):
    members, _ = required_members(conn, "2025-02-03")
    seeded = {r[0] for r in conn.execute(
        "SELECT ticker FROM idx80_membership_history WHERE period_label='PB'")}
    assert set(members) == seeded          # all 81 present, none dropped
    assert len(members) == 81


# --- 7. completed cells are skipped ------------------------------------------

def test_completed_cells_not_replanned(conn):
    members, _ = required_members(conn, "2025-01-02")
    from tools.broker_flow_idx80_gap import missing_cells
    need = missing_cells(conn, "2025-01-02", members)
    assert "PA000" not in need   # complete via broker_flow row
    assert "PA001" not in need   # complete via confirmed-empty bandar marker
    assert "PA002" in need


# --- 8. missing cells are selected -------------------------------------------

def test_gap_plan_selects_exactly_the_missing_cells(conn):
    from tools.broker_flow_idx80_gap import missing_cells
    dates = R.gap_dates(conn, "2025-01-02", "2025-01-04")
    plan = pit_gap_plan(conn, dates, missing_cells)
    d2 = next(x for x in plan["dates"] if x["date"] == "2025-01-02")
    assert d2["member_count"] == 80
    assert d2["missing_count"] == 78            # 80 - PA000 (row) - PA001 (marker)
    assert d2["missing_cells"] == sorted(d2["missing_cells"])
    assert "PA000" not in d2["missing_cells"]
    assert d2["advisory"] is None
    assert plan["required_ticker_days"] == 160
    assert plan["missing_ticker_days"] == 158


# --- 9. P2-analog: strict research excludes, collection includes -------------

def test_unresolved_period_invisible_to_strict_tier(conn):
    assert members_as_of(conn, "2025-02-02", "reconstructed") == frozenset()
    assert len(members_as_of_all_evidence(conn, "2025-02-02")) == 81


def test_planning_layer_is_collection_authority_all_evidence(conn):
    # the planning layer must see the UNRESOLVED roster (data collection),
    # while flagging it as an anomaly for research consumers
    members, advisory = required_members(conn, "2025-02-03")
    assert len(members) == 81
    assert advisory["confidence"] == "UNRESOLVED"


# --- 10. boundary dates use inclusive effective_to ---------------------------

def test_boundary_date_on_effective_to_resolves_to_that_period(conn):
    members, _ = required_members(conn, "2025-01-31")     # PA effective_to
    assert len(members) == 80 and members[0] == "PA000"
    members, _ = required_members(conn, "2025-04-30")     # PD effective_to
    assert len(members) == 80 and members[0] == "PD000"


# --- 11. live mode behavior remains unchanged --------------------------------

def test_runner_default_mode_is_live(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None:
                        calls.append((ticker, date)) or
                        _populated(ticker, date))
    stats = R.run("2025-01-02", "2025-01-04", conn=conn, token="tok")
    # live roster = LIVE1+LIVE2 on both dates; nothing complete -> 4 fetches
    assert sorted(calls) == [("LIVE1", "2025-01-02"), ("LIVE1", "2025-01-03"),
                             ("LIVE2", "2025-01-02"), ("LIVE2", "2025-01-03")]
    assert stats["planned_cells"] == 4


def test_runner_cli_default_is_live():
    args = R.build_parser().parse_args(["--date-from", "2025-01-02",
                                        "--date-to", "2025-01-04"])
    assert args.universe == "live"


def test_runner_cli_accepts_pit():
    args = R.build_parser().parse_args(["--date-from", "2025-01-02",
                                        "--date-to", "2025-01-04",
                                        "--universe", "pit"])
    assert args.universe == "pit"


# --- 12. deterministic ordering ------------------------------------------------

def test_required_members_is_deterministically_sorted(conn):
    a, _ = required_members(conn, "2025-02-02")
    b, _ = required_members(conn, "2025-02-02")
    assert a == b == sorted(a)


# --- runner integration: pit mode fetches PIT gaps only -----------------------

def _populated(ticker, date):
    return {"broker_rows": [{
        "ticker": ticker, "trade_date": date, "broker_code": "ZP",
        "side": "BUY", "lot": 1, "lot_value": 1, "value": 2,
        "value_total": 3, "avg_price": 9000.0, "freq": 4,
        "investor_type": "Asing"}],
        "bandar": {"ticker": ticker, "trade_date": date,
                   "avg_price": 9000.0, "total_buyer": 1, "total_seller": 1,
                   "net_broker_count": 1, "broker_accdist": "A",
                   "value": 100, "volume": 50, "top1_accdist": "A",
                   "top3_accdist": "A", "top5_accdist": "A",
                   "top10_accdist": "A", "avg_accdist": "A",
                   "updated_at": "2025-01-02T00:00:00"},
        "trade_date": date}


def test_runner_pit_mode_fetches_pit_gaps_only(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(sf, "fetch_broker_flow",
                        lambda token, ticker, date=None:
                        calls.append((ticker, date)) or
                        _populated(ticker, date))
    stats = R.run("2025-01-02", "2025-01-04", conn=conn, token="tok",
                  universe_mode="pit")
    # PA roster (80) on both dates; PA000+PA001 complete on 01-02 only
    assert ("PA000", "2025-01-02") not in calls
    assert ("PA001", "2025-01-02") not in calls
    assert ("PA002", "2025-01-02") in calls
    assert ("PA000", "2025-01-03") in calls
    assert not any(t.startswith("LIVE") for t, _ in calls)
    assert stats["planned_cells"] == 160       # 80 x 2 dates
    assert stats["populated"] == 158
    assert stats["skipped"] == 2


def test_runner_pit_dry_run_reports_advisories_without_vendor(conn, monkeypatch):
    _no_vendor_calls(monkeypatch)
    stats = R.run("2025-02-02", "2025-02-04", conn=conn, token="tok",
                  dry_run=True, universe_mode="pit")
    assert stats["planned_cells"] == 162       # 81 x 2 dates
    assert stats["advisories"] == 2            # one per date (81 != 80)
    assert all(a["member_count"] == 81 for a in stats["advisory_log"])


# --- orchestrator: PIT-aware planning/supervision ---------------------------

import tools.agent_backfill_broker_flow_idx80 as A


def test_build_command_live_has_no_universe_flag():
    cmd = A.build_command("python", "runner.py", "2025-01-02", "2025-01-03",
                          600, False)
    assert "--universe" not in cmd


def test_build_command_pit_appends_flag():
    cmd = A.build_command("python", "runner.py", "2025-01-02", "2025-01-03",
                          600, False, universe="pit")
    assert cmd[-2:] == ["--universe", "pit"]


def test_compute_coverage_pit_uses_rosters_not_live(conn):
    cov = A.compute_coverage_pit(conn, ["2025-01-02", "2025-01-03"])
    d = cov.as_dict()
    # PIT accounting: 80-member roster on both dates, 2 complete on 01-02
    assert d["expected_ticker_days"] == 160
    assert d["complete_ticker_days"] == 2
    assert d["missing_ticker_days"] == 158
    # live roster (2 names) would have produced expected=4 -- never used
    assert d["expected_ticker_days"] != 4


def test_orchestrator_cli_default_live_and_pit_accepted():
    args = A.build_parser().parse_args(["--date-from", "2025-01-02",
                                        "--date-to", "2025-01-03"])
    assert args.universe == "live"
    args = A.build_parser().parse_args(["--date-from", "2025-01-02",
                                        "--date-to", "2025-01-03",
                                        "--universe", "pit"])
    assert args.universe == "pit"


def test_supervise_dates_pit_uses_roster_accounting(conn, tmp_path, monkeypatch):
    # stub child runner: exits 0 immediately, fetches nothing
    stub = tmp_path / "stub_runner.py"
    stub.write_text("import sys; sys.exit(0)\n")
    rosters = {d: A.required_members(conn, d)[0]
               for d in ("2025-01-02", "2025-01-03")}
    outcomes, launched, aborted = A.supervise_dates(
        None, ["LIVE1", "LIVE2"], ["2025-01-02", "2025-01-03"],
        "python", str(stub), budget_s=60, date_timeout_s=60,
        no_progress_s=60, poll_s=1, universe_mode="pit", rosters=rosters,
        conn=conn)
    by_date = {o["date"]: o for o in outcomes}
    assert by_date["2025-01-02"]["expected_cells"] == 80   # PIT roster, not live 2
    assert by_date["2025-01-02"]["outcome"] == "FAILED"    # 78 cells still missing
    assert by_date["2025-01-03"]["expected_cells"] == 80
    assert launched == 2


# --- regression: plan date-classification + advisory surfacing --------------

def test_compute_coverage_pit_classifies_partial_dates_correctly(conn):
    # 2025-01-02: 2 of 80 complete -> PARTIAL; 2025-01-03: 0 -> ZERO.
    # compute_coverage stores partial entries as DICTS, so string membership
    # (d in dates_partial) silently misclassifies every date as full.
    cov = A.compute_coverage_pit(conn, ["2025-01-02", "2025-01-03"])
    d = cov.as_dict()
    assert d["dates_total"] == 2
    assert d["dates_partial_count"] == 1
    assert d["dates_zero_count"] == 1
    assert d["dates_full_count"] == 0
    assert [x["date"] for x in d["dates_partial"]] == ["2025-01-02"]
    assert d["dates_zero"] == ["2025-01-03"]


def test_full_date_still_classified_full(conn, monkeypatch):
    import stockbit_fetcher as sf2
    monkeypatch.setattr(sf2, "fetch_broker_flow", None)  # unused here
    # complete PA roster on 2025-01-02 for the classification-full case
    for i in range(80):
        tkr = f"PA{i:03d}"
        if tkr == "PA001":
            continue
        con_row = (tkr, "2025-01-02", "ZP", "BUY", 1, 1, 2, 3, 9000.0, 4, "Asing")
        conn.execute("INSERT OR REPLACE INTO broker_flow (ticker, trade_date, "
                     "broker_code, side, lot, lot_value, value, value_total, "
                     "avg_price, freq, investor_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     con_row)
    conn.execute("INSERT OR REPLACE INTO bandar_detector (ticker, trade_date, "
                 "value, volume) VALUES ('PA001','2025-01-02',0,0)")
    conn.commit()
    cov = A.compute_coverage_pit(conn, ["2025-01-02"])
    assert cov.as_dict()["dates_full_count"] == 1
    assert cov.missing == 0
