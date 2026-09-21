"""Research universe-selection integration for IDX80-scoped studies.

Covers the new idx80_universe_as_of() wrapper (research/idx80_membership.py)
that future IDX80 flow-vs-return work must call instead of ever touching
idx_tickers.in_idx80, plus regression coverage proving the existing
non-IDX80 universe providers (liquid_universe, _default_universe) are
untouched by this integration.
"""
import sqlite3

import pytest

from research.idx80_membership import (
    RECONSTRUCTED,
    STRICT,
    idx80_universe_as_of,
)

PERIODS = [
    # label, from, to, left_censored, count, confidence
    ("P0", "2025-01-02", "2025-02-02", 1, 80, "BRACKETED_RECONSTRUCTED"),
    ("P1", "2025-02-03", "2025-04-30", 0, 80, "PRIMARY_VERIFIED"),
    ("P2", "2025-05-02", "2025-07-31", 0, 81, "UNRESOLVED"),
    ("P3", "2025-08-01", "2025-11-02", 0, 80, "PRIMARY_VERIFIED"),
    ("P4", "2025-11-03", "2026-02-01", 0, 80, "BRACKETED_RECONSTRUCTED"),
    ("P5", "2026-02-02", "2026-05-03", 0, 80, "PRIMARY_VERIFIED"),
    ("P6", "2026-05-04", "2026-08-02", 0, 80, "PRIMARY_VERIFIED"),
    ("P7", "2026-08-03", None, 0, 80, "CROSS_VALIDATED"),
]

# A representative in-period trading date for each period, and the tier
# under which strict membership is non-empty (P0/P2/P7 are not
# PRIMARY_VERIFIED so strict returns nothing there -- see test_idx80_membership.py).
STRICT_NONEMPTY_PERIODS = [
    ("P1", "2025-02-15"),
    ("P3", "2025-09-01"),
    ("P5", "2026-03-01"),
    ("P6", "2026-06-15"),
]
RECONSTRUCTED_ONLY_PERIODS = [
    ("P4", "2025-12-01"),
    ("P7", "2026-08-15"),
]


def _mk_db(tmp_path, *, with_idx_tickers_decoy=False):
    path = tmp_path / "walkforward.db"
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE idx80_reconstitution_periods (
            period_label        TEXT PRIMARY KEY,
            effective_from      TEXT NOT NULL,
            effective_to        TEXT,
            left_censored        INTEGER NOT NULL DEFAULT 0 CHECK (left_censored IN (0,1)),
            constituent_count    INTEGER NOT NULL,
            confidence           TEXT NOT NULL CHECK (confidence IN (
                                      'PRIMARY_VERIFIED',
                                      'BRACKETED_RECONSTRUCTED',
                                      'CROSS_VALIDATED',
                                      'UNRESOLVED'
                                  )),
            source                TEXT NOT NULL,
            notes                 TEXT,
            created_at            TEXT NOT NULL
        )
    """)
    conn.execute("""
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
        )
    """)
    for label, eff_from, eff_to, left_censored, count, confidence in PERIODS:
        conn.execute(
            "INSERT INTO idx80_reconstitution_periods "
            "(period_label, effective_from, effective_to, left_censored, "
            " constituent_count, confidence, source, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'fixture', '', '2026-08-31')",
            (label, eff_from, eff_to, left_censored, count, confidence),
        )
        for i in range(count):
            ticker = f"{label}T{i:03d}"
            conn.execute(
                "INSERT INTO idx80_membership_history "
                "(ticker, period_label, effective_from, effective_to, "
                " membership_status, confidence, source, created_at) "
                "VALUES (?, ?, ?, ?, 'MEMBER', ?, 'fixture', '2026-08-31')",
                (ticker, label, eff_from, eff_to, confidence),
            )
    if with_idx_tickers_decoy:
        # A live "current membership" table sitting in the SAME connection,
        # deliberately populated with a DIFFERENT roster than any PIT period
        # (mimicking today's idx_tickers.in_idx80) -- proves the wrapper
        # never reads it, no matter what as_of_date is queried.
        conn.execute("CREATE TABLE idx_tickers (ticker TEXT PRIMARY KEY, in_idx80 INTEGER)")
        for i in range(80):
            conn.execute(
                "INSERT INTO idx_tickers (ticker, in_idx80) VALUES (?, 1)",
                (f"LIVE_DECOY{i:03d}",),
            )
    conn.commit()
    return conn


@pytest.fixture
def conn(tmp_path):
    c = _mk_db(tmp_path)
    yield c
    c.close()


@pytest.fixture
def conn_with_decoy(tmp_path):
    c = _mk_db(tmp_path, with_idx_tickers_decoy=True)
    yield c
    c.close()


# --- historical P1/P3/P4/P5/P6/P7 membership selection --------------------

@pytest.mark.parametrize("label,as_of", STRICT_NONEMPTY_PERIODS)
def test_historical_strict_universe_selection(conn, label, as_of):
    universe = idx80_universe_as_of(conn, as_of, STRICT)
    assert len(universe) == 80
    assert all(t.startswith(f"{label}T") for t in universe)


@pytest.mark.parametrize("label,as_of", RECONSTRUCTED_ONLY_PERIODS)
def test_historical_reconstructed_universe_selection(conn, label, as_of):
    assert idx80_universe_as_of(conn, as_of, STRICT) == ()
    universe = idx80_universe_as_of(conn, as_of, RECONSTRUCTED)
    assert len(universe) == 80
    assert all(t.startswith(f"{label}T") for t in universe)


# --- P2 exclusion -----------------------------------------------------

def test_p2_excluded_under_strict(conn):
    assert idx80_universe_as_of(conn, "2025-06-15", STRICT) == ()


def test_p2_excluded_under_reconstructed_too(conn):
    assert idx80_universe_as_of(conn, "2025-06-15", RECONSTRUCTED) == ()


# --- boundary-date inclusivity ------------------------------------------

def test_boundary_effective_to_inclusive(conn):
    universe = idx80_universe_as_of(conn, "2025-04-30", STRICT)  # P1 last day
    assert len(universe) == 80
    assert all(t.startswith("P1T") for t in universe)


def test_boundary_effective_from_inclusive(conn):
    universe = idx80_universe_as_of(conn, "2025-02-03", STRICT)  # P1 first day
    assert len(universe) == 80


# --- no fallback to live idx_tickers.in_idx80 --------------------------

def test_never_falls_back_to_idx_tickers_in_idx80(conn_with_decoy):
    # Even with a same-connection idx_tickers table advertising a totally
    # different "current" roster, every as_of_date must resolve strictly
    # from the PIT ledger (or return empty), never the decoy.
    for as_of, tier, expected_prefix in [
        ("2025-02-15", STRICT, "P1T"),
        ("2026-06-15", STRICT, "P6T"),
        ("2026-08-15", RECONSTRUCTED, "P7T"),
    ]:
        universe = idx80_universe_as_of(conn_with_decoy, as_of, tier)
        assert universe, f"expected non-empty universe for {as_of}/{tier}"
        assert all(t.startswith(expected_prefix) for t in universe)
        assert not any(t.startswith("LIVE_DECOY") for t in universe)


def test_no_hardcoded_current_universe_leaks_into_2025(conn_with_decoy):
    # A 2025 as_of_date must never resolve to the 2026 P6/P7 roster (or the
    # idx_tickers decoy) -- each period's own ticker set is disjoint here.
    universe_2025 = idx80_universe_as_of(conn_with_decoy, "2025-02-15", STRICT)
    universe_2026 = idx80_universe_as_of(conn_with_decoy, "2026-06-15", STRICT)
    assert set(universe_2025).isdisjoint(universe_2026)
    assert not any(t.startswith("LIVE_DECOY") for t in universe_2025)


# --- deterministic universe selection -----------------------------------

def test_deterministic_across_repeated_calls(conn):
    first = idx80_universe_as_of(conn, "2025-02-15", STRICT)
    second = idx80_universe_as_of(conn, "2025-02-15", STRICT)
    assert first == second
    assert isinstance(first, tuple)
    assert list(first) == sorted(first)  # stable, sorted order -- not set iteration order


def test_as_of_date_has_no_default_value():
    import inspect
    sig = inspect.signature(idx80_universe_as_of)
    assert sig.parameters["as_of_date"].default is inspect.Parameter.empty


# --- preservation of existing non-IDX80 universe behavior -----------------

def test_default_universe_unchanged(tmp_path):
    """gatekeeper.cli._default_universe must still be the plain distinct-ticker
    query over ohlcv (excluding IHSG) -- untouched by the IDX80 PIT work."""
    from research.gatekeeper.cli import _default_universe

    path = tmp_path / "wf.db"
    prod = sqlite3.connect(str(path))
    prod.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    prod.executemany(
        "INSERT INTO ohlcv VALUES (?, ?)",
        [("BBCA", "2026-01-01"), ("BBRI", "2026-01-01"), ("IHSG", "2026-01-01")],
    )
    prod.commit()
    universe = _default_universe(prod)
    prod.close()
    assert set(universe) == {"BBCA", "BBRI"}


def test_liquid_universe_still_importable_and_unrelated_to_idx80_module():
    # Regression guard: liquid_universe must not have been rewired to import
    # from research.idx80_membership -- it is a distinct, ADV-liquidity-based
    # universe used by NR7/regime studies, deliberately left alone.
    import research.studies.nr7_generalization_study as ns
    import inspect
    source = inspect.getsource(ns.liquid_universe)
    assert "idx80" not in source.lower()
