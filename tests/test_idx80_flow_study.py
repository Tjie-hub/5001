"""Phase A: IDX80 Stockbit flow descriptive study (research/studies/idx80_flow_study.py).

Hermetic: builds its own temp SQLite schema (idx80_reconstitution_periods,
idx80_membership_history, stockbit_flow_bars, ohlcv, trading_calendar) rather
than touching data/walkforward.db.

Column semantics locked in by inspecting stockbit_fetcher.py/flow_filter.py's
_parse_bars() and cross-checking the live DB (verified: BBCA 2025-03-03's
last bar buy_lot=1,120,303 + sell_lot=809,140, x100 shares/lot, exactly
equals that day's OHLCV volume of 192,944,300):

  - buy_lot / sell_lot : CUMULATIVE running totals through the trading day
                         -> daily value = MAX() across bars, never SUM().
  - net_value          : a genuine PER-BAR net transaction value (bounces
                         +/- minute to minute) -> daily value = SUM().
  - delta = buy_lot - sell_lot, stored per bar; since buy_lot/sell_lot are
    cumulative, delta is also cumulative and is NOT summed either.
  - n_bars             : a coverage diagnostic (bar-row count), not a feature.

Fixture universe/period layout (small, hand-built, not the real ledger):
  P0  2025-01-02..2025-01-03  left_censored=1  BRACKETED_RECONSTRUCTED  {AAAA, BBBB}
  P1  2025-01-06..2025-01-08                    PRIMARY_VERIFIED         {AAAA, CCCC}
  P2  2025-01-09..2025-01-10                     UNRESOLVED               (excluded regardless)
"""
import sqlite3

import pandas as pd
import pytest

from research.idx80_membership import RECONSTRUCTED, STRICT
from research.studies.idx80_flow_study import (
    _add_derived_features,
    _daily_flow_aggregates,
    build_flow_panel,
    coverage_audit,
    descriptive_tables,
    resolve_periods,
    run_phase_a,
)

DDL = """
CREATE TABLE idx80_reconstitution_periods (
    period_label        TEXT PRIMARY KEY,
    effective_from      TEXT NOT NULL,
    effective_to        TEXT,
    left_censored        INTEGER NOT NULL DEFAULT 0,
    constituent_count    INTEGER NOT NULL,
    confidence           TEXT NOT NULL,
    source                TEXT NOT NULL,
    notes                 TEXT,
    created_at            TEXT NOT NULL
);
CREATE TABLE idx80_membership_history (
    ticker           TEXT NOT NULL,
    period_label     TEXT NOT NULL REFERENCES idx80_reconstitution_periods(period_label),
    effective_from   TEXT NOT NULL,
    effective_to     TEXT,
    membership_status TEXT NOT NULL DEFAULT 'MEMBER',
    confidence       TEXT NOT NULL,
    source           TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    PRIMARY KEY (ticker, period_label)
);
CREATE TABLE stockbit_flow_bars (
    ticker TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    buy_lot INTEGER,
    sell_lot INTEGER,
    buy_freq INTEGER,
    sell_freq INTEGER,
    net_value INTEGER,
    price INTEGER,
    delta INTEGER,
    PRIMARY KEY (ticker, trade_date, bar_time)
);
CREATE TABLE ohlcv (
    ticker TEXT NOT NULL, date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    is_final INTEGER DEFAULT 1
);
CREATE TABLE trading_calendar (date TEXT PRIMARY KEY, source TEXT);
"""

PERIODS = [
    ("P0", "2025-01-02", "2025-01-03", 1, 2, "BRACKETED_RECONSTRUCTED"),
    ("P1", "2025-01-06", "2025-01-08", 0, 2, "PRIMARY_VERIFIED"),
    ("P2", "2025-01-09", "2025-01-10", 0, 2, "UNRESOLVED"),
]
MEMBERSHIP = {
    "P0": ["AAAA", "BBBB"],
    "P1": ["AAAA", "CCCC"],
    "P2": ["AAAA", "BBBB"],  # deliberately non-empty -- must still be excluded (UNRESOLVED)
}
TRADING_DAYS = [
    "2025-01-02", "2025-01-03",              # P0 (Thu, Fri)
    "2025-01-06", "2025-01-07", "2025-01-08",  # P1 (Mon-Wed)
    "2025-01-09", "2025-01-10",              # P2 (Thu, Fri)
]


def _insert_bars(conn, ticker, trade_date, bars):
    """bars: list of (bar_time, buy_lot, sell_lot, net_value) -- cumulative
    buy/sell lot, per-bar net_value, as in the real feed."""
    for bar_time, buy_lot, sell_lot, net_value in bars:
        conn.execute(
            "INSERT INTO stockbit_flow_bars "
            "(ticker, trade_date, bar_time, buy_lot, sell_lot, buy_freq, sell_freq, "
            " net_value, price, delta) VALUES (?,?,?,?,?,0,0,?,8000,?)",
            (ticker, trade_date, bar_time, buy_lot, sell_lot, net_value, buy_lot - sell_lot),
        )


def _mk_db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "wf.db"))
    conn.executescript(DDL)

    for label, eff_from, eff_to, left_censored, count, confidence in PERIODS:
        conn.execute(
            "INSERT INTO idx80_reconstitution_periods VALUES (?,?,?,?,?,?, 'fixture', '', '2025-01-01')",
            (label, eff_from, eff_to, left_censored, count, confidence),
        )
        for ticker in MEMBERSHIP[label]:
            conn.execute(
                "INSERT INTO idx80_membership_history VALUES (?,?,?,?, 'MEMBER', ?, 'fixture', '2025-01-01')",
                (ticker, label, eff_from, eff_to, confidence),
            )

    for d in TRADING_DAYS:
        conn.execute("INSERT INTO trading_calendar VALUES (?, 'fixture')", (d,))

    # --- P0 window: AAAA normal both days; BBBB zero-activity on day 1, MISSING on day 2 ---
    _insert_bars(conn, "AAAA", "2025-01-02", [
        ("09:00", 100, 50, 1_000_000),
        ("09:01", 150, 80, -200_000),
    ])
    _insert_bars(conn, "BBBB", "2025-01-02", [("09:00", 0, 0, 0)])   # zero-activity, present
    _insert_bars(conn, "AAAA", "2025-01-03", [
        ("09:00", 40, 60, 500_000),
        ("09:01", 90, 100, 300_000),
        ("09:02", 120, 140, -400_000),
    ])
    # BBBB/2025-01-03: no rows at all -> MISSING ticker-day.

    # Boundary-leakage probes: BEFORE P0's left-censored start, and AFTER P0's
    # effective_to (spilling into the P0->P1 gap) -- neither must be counted
    # in P0's stats.
    _insert_bars(conn, "AAAA", "2025-01-01", [("09:00", 999_999, 1, 0)])
    _insert_bars(conn, "AAAA", "2025-01-04", [("09:00", 999_999, 1, 0)])

    # --- P1 window: AAAA, CCCC normal ---
    for d, vals in [
        ("2025-01-06", [("09:00", 200, 100, 10_000)]),
        ("2025-01-07", [("09:00", 210, 150, -5_000), ("09:01", 260, 170, 2_000)]),
        ("2025-01-08", [("09:00", 300, 200, 1_000)]),
    ]:
        _insert_bars(conn, "AAAA", d, vals)
        _insert_bars(conn, "CCCC", d, [(t, b + 10, s + 5, nv) for t, b, s, nv in vals])

    # BBBB is NOT a P1 member -- a stray bar for it inside the P1 window must
    # never surface in P1's panel/coverage (no accidental universe leakage).
    _insert_bars(conn, "BBBB", "2025-01-06", [("09:00", 777, 1, 0)])

    # Future-leakage probe: a bar dated inside P2's window (after P1 ends) for
    # a P1 member -- must never be attributed to P1.
    _insert_bars(conn, "AAAA", "2025-01-09", [("09:00", 888_888, 1, 0)])

    # OHLCV: finalized volume for most ticker-days; one is_final=0-only day to
    # prove flow_intensity is NaN (not 0) when no finalized volume exists.
    ohlcv_rows = [
        ("AAAA", "2025-01-02", 23000.0, 1),
        ("BBBB", "2025-01-02", 5000.0, 1),
        ("AAAA", "2025-01-06", 30000.0, 1),
        ("CCCC", "2025-01-06", 21000.0, 1),
        ("AAAA", "2025-01-03", 999.0, 0),   # provisional only -> excluded
    ]
    for ticker, d, vol, is_final in ohlcv_rows:
        conn.execute(
            "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) "
            "VALUES (?,?,8000,8100,7900,8000,?,?)",
            (ticker, d, vol, is_final),
        )

    conn.commit()
    return conn


@pytest.fixture
def conn(tmp_path):
    c = _mk_db(tmp_path)
    yield c
    c.close()


def _mk_db_with_decoy(tmp_path):
    conn = _mk_db(tmp_path)
    conn.execute("CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY, in_idx80 INTEGER)")
    for t in ("LIVE1", "LIVE2"):
        conn.execute("INSERT INTO idx_tickers VALUES (?, 1)", (t,))
    conn.commit()
    return conn


@pytest.fixture
def conn_decoy(tmp_path):
    c = _mk_db_with_decoy(tmp_path)
    yield c
    c.close()


# --- PIT universe resolution -------------------------------------------

def test_resolve_periods_strict_excludes_p0_and_p1_is_primary_verified(conn):
    periods = {p["period_label"]: p for p in resolve_periods(conn, STRICT)}
    assert periods["P0"]["included"] is False
    assert periods["P0"]["universe"] == ()
    assert periods["P1"]["included"] is True
    assert set(periods["P1"]["universe"]) == {"AAAA", "CCCC"}


def test_resolve_periods_reconstructed_includes_p0(conn):
    periods = {p["period_label"]: p for p in resolve_periods(conn, RECONSTRUCTED)}
    assert periods["P0"]["included"] is True
    assert set(periods["P0"]["universe"]) == {"AAAA", "BBBB"}


def test_resolve_periods_reports_p2_explicitly_not_silently(conn):
    periods = {p["period_label"]: p for p in resolve_periods(conn, RECONSTRUCTED)}
    assert "P2" in periods
    assert periods["P2"]["included"] is False
    assert periods["P2"]["confidence"] == "UNRESOLVED"


# --- P2 exclusion --------------------------------------------------------

def test_p2_contributes_zero_rows_to_flow_panel(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    assert "P2" not in set(panel["period_label"])


def test_p2_excluded_in_coverage_audit_but_still_listed(conn):
    cov = coverage_audit(conn, RECONSTRUCTED)
    p2 = cov[cov["period_label"] == "P2"].iloc[0]
    assert p2["included"] == False
    assert p2["expected_ticker_days"] == 0
    assert p2["available_ticker_days"] == 0


# --- period boundary dates -----------------------------------------------

def test_boundary_dates_included_and_no_leakage_before_or_after(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    p0 = panel[panel["period_label"] == "P0"]
    dates = set(p0["trade_date"])
    assert "2025-01-02" in dates   # effective_from (left-censored start)
    assert "2025-01-03" in dates   # effective_to
    assert "2025-01-01" not in dates  # before left-censored start
    assert "2025-01-04" not in dates  # after effective_to, before P1 starts

    aaaa_p0_day1 = p0[(p0["ticker"] == "AAAA") & (p0["trade_date"] == "2025-01-02")].iloc[0]
    assert aaaa_p0_day1["buy_lot"] == 150   # MAX across the day's bars, not the leaked 999999 row


# --- aggregation of multiple 1-minute bars into one ticker-day -----------

def test_multi_bar_aggregation_uses_max_for_cumulative_lots_and_sum_for_net_value(conn):
    raw = _daily_flow_aggregates(conn, ("AAAA",), "2025-01-02", "2025-01-02")
    row = raw.iloc[0]
    assert row["buy_lot"] == 150     # MAX(100, 150)
    assert row["sell_lot"] == 80     # MAX(50, 80)
    assert row["net_value"] == 800_000   # SUM(1_000_000, -200_000)
    assert row["n_bars"] == 2


def test_three_bar_day_aggregation(conn):
    raw = _daily_flow_aggregates(conn, ("AAAA",), "2025-01-03", "2025-01-03")
    row = raw.iloc[0]
    assert row["buy_lot"] == 120
    assert row["sell_lot"] == 140
    assert row["net_value"] == 400_000  # 500_000 + 300_000 - 400_000
    assert row["n_bars"] == 3


# --- buy/sell/net-value derived features ---------------------------------

def test_derived_features_buy_minus_sell_and_total_flow_lots():
    raw = pd.DataFrame([{"ticker": "X", "trade_date": "2025-01-02",
                         "buy_lot": 150, "sell_lot": 80, "net_value": 800_000, "n_bars": 2}])
    out = _add_derived_features(raw)
    row = out.iloc[0]
    assert row["buy_minus_sell"] == 70
    assert row["total_flow_lots"] == 230
    assert abs(row["imbalance"] - (70 / 230)) < 1e-9
    assert row["zero_activity"] == False


# --- zero-activity handling ------------------------------------------------

def test_zero_activity_session_has_defined_not_nan_zero_imbalance(conn):
    raw = _daily_flow_aggregates(conn, ("BBBB",), "2025-01-02", "2025-01-02")
    out = _add_derived_features(raw)
    row = out.iloc[0]
    assert row["buy_lot"] == 0 and row["sell_lot"] == 0
    assert row["zero_activity"] == True
    assert pd.isna(row["imbalance"])   # 0/0 is undefined -- must be NaN, not 0 or an error


def test_zero_activity_counted_in_coverage_audit(conn):
    cov = coverage_audit(conn, RECONSTRUCTED)
    p0 = cov[cov["period_label"] == "P0"].iloc[0]
    assert p0["zero_activity_ticker_days"] == 1  # BBBB/2025-01-02


# --- missing-data handling -------------------------------------------------

def test_missing_ticker_day_absent_from_panel_not_zero_filled(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    bbbb_p0 = panel[(panel["ticker"] == "BBBB") & (panel["period_label"] == "P0")]
    assert set(bbbb_p0["trade_date"]) == {"2025-01-02"}  # 2025-01-03 genuinely absent


def test_missing_ticker_day_counted_in_coverage_audit(conn):
    cov = coverage_audit(conn, RECONSTRUCTED)
    p0 = cov[cov["period_label"] == "P0"].iloc[0]
    # universe=2 (AAAA,BBBB) x 2 trading days = 4 expected; BBBB/01-03 missing -> 3 available
    assert p0["expected_ticker_days"] == 4
    assert p0["available_ticker_days"] == 3
    assert p0["missing_ticker_days"] == 1


def test_p1_never_sees_non_member_bbbb_stray_bar(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    p1_tickers = set(panel[panel["period_label"] == "P1"]["ticker"])
    assert "BBBB" not in p1_tickers


def test_future_dated_bar_does_not_leak_into_earlier_period(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    p1 = panel[panel["period_label"] == "P1"]
    assert "2025-01-09" not in set(p1["trade_date"])  # P2's window, not P1's


# --- flow intensity vs OHLCV volume ("where valid") -----------------------

def test_flow_intensity_computed_when_finalized_volume_present(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    row = panel[(panel["ticker"] == "AAAA") & (panel["trade_date"] == "2025-01-02")].iloc[0]
    # total_flow_lots=230 lots * 100 shares/lot = 23000 shares == ohlcv volume 23000
    assert abs(row["flow_intensity"] - 1.0) < 1e-6


def test_flow_intensity_nan_when_only_provisional_ohlcv_exists(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    row = panel[(panel["ticker"] == "AAAA") & (panel["trade_date"] == "2025-01-03")].iloc[0]
    assert pd.isna(row["flow_intensity"])  # only is_final=0 OHLCV exists for this day


# --- deterministic output --------------------------------------------------

def test_build_flow_panel_deterministic(conn):
    first = build_flow_panel(conn, RECONSTRUCTED)
    second = build_flow_panel(conn, RECONSTRUCTED)
    pd.testing.assert_frame_equal(first, second)


def test_coverage_audit_deterministic(conn):
    first = coverage_audit(conn, RECONSTRUCTED)
    second = coverage_audit(conn, RECONSTRUCTED)
    pd.testing.assert_frame_equal(first, second)


def test_descriptive_tables_deterministic(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    first = descriptive_tables(panel)
    second = descriptive_tables(panel)
    for key in first:
        pd.testing.assert_frame_equal(first[key], second[key])


# --- no access to idx_tickers.in_idx80 ------------------------------------

def test_never_touches_idx_tickers_decoy(conn_decoy):
    panel = build_flow_panel(conn_decoy, RECONSTRUCTED)
    cov = coverage_audit(conn_decoy, RECONSTRUCTED)
    assert not any(t in {"LIVE1", "LIVE2"} for t in panel["ticker"])
    assert set(cov["period_label"]) == {"P0", "P1", "P2"}


# --- descriptive tables shape ----------------------------------------------

def test_descriptive_tables_by_period_and_overall_and_ticker_and_date(conn):
    panel = build_flow_panel(conn, RECONSTRUCTED)
    tables = descriptive_tables(panel)
    assert set(tables) == {"overall", "by_period", "by_ticker", "by_date"}
    assert len(tables["overall"]) == 1
    assert set(tables["by_period"]["period_label"]) == {"P0", "P1"}
    assert "n" in tables["overall"].columns
    assert "buy_lot_mean" in tables["overall"].columns
    assert "imbalance_median" in tables["overall"].columns


def test_run_phase_a_returns_full_bundle(conn):
    result = run_phase_a(conn, RECONSTRUCTED)
    assert set(result) >= {"coverage", "panel", "overall", "by_period", "by_ticker", "by_date"}
