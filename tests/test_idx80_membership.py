"""Point-in-time IDX80 membership accessor (research/idx80_membership.py).

Hermetic: builds its own temp SQLite schema mirroring the live
idx80_reconstitution_periods / idx80_membership_history tables (see
docs/research_programs/P-A/WP-D/DATA_DICTIONARY.md for provenance) rather than
touching data/walkforward.db.

Fixture mirrors the real P0-P7 period ledger (period_label, effective_from,
effective_to, left_censored, constituent_count, confidence):

    P0  2025-01-02..2025-02-02  left_censored=1  80  BRACKETED_RECONSTRUCTED
    P1  2025-02-03..2025-04-30                    80  PRIMARY_VERIFIED
    P2  2025-05-02..2025-07-31                    81  UNRESOLVED
    P3  2025-08-01..2025-11-02                    80  PRIMARY_VERIFIED
    P4  2025-11-03..2026-02-01                    80  BRACKETED_RECONSTRUCTED
    P5  2026-02-02..2026-05-03                    80  PRIMARY_VERIFIED
    P6  2026-05-04..2026-08-02                    80  PRIMARY_VERIFIED
    P7  2026-08-03..(open)                         80  CROSS_VALIDATED

Note the P1->P2 gap (2025-05-01, a market-holiday day with no period row) is
reproduced deliberately: it is a real gap in the source data, not a bug.
"""
import sqlite3

import pytest

from research.idx80_membership import (
    ALL_EVIDENCE,
    RECONSTRUCTED,
    STRICT,
    members_as_of,
    members_as_of_all_evidence,
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


def _mk_db(tmp_path):
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
    conn.commit()
    return conn


@pytest.fixture
def conn(tmp_path):
    c = _mk_db(tmp_path)
    yield c
    c.close()


# --- requirement 8: the eight required date/tier cases -----------------

def test_2025_01_02_p0_left_censored_strict_excludes_bracketed(conn):
    # P0 is BRACKETED_RECONSTRUCTED; strict tier is PRIMARY_VERIFIED-only.
    assert members_as_of(conn, "2025-01-02", STRICT) == frozenset()


def test_2025_01_02_p0_left_censored_reconstructed_tier_includes_it(conn):
    result = members_as_of(conn, "2025-01-02", RECONSTRUCTED)
    assert len(result) == 80
    assert all(t.startswith("P0T") for t in result)


def test_2025_02_03_p1_primary_verified_strict(conn):
    result = members_as_of(conn, "2025-02-03", STRICT)
    assert len(result) == 80
    assert all(t.startswith("P1T") for t in result)


def test_2025_06_15_p2_unresolved_strict_returns_zero(conn):
    assert members_as_of(conn, "2025-06-15", STRICT) == frozenset()


def test_2025_06_15_p2_unresolved_reconstructed_tier_returns_zero(conn):
    # reconstructed opt-in still excludes UNRESOLVED.
    assert members_as_of(conn, "2025-06-15", RECONSTRUCTED) == frozenset()


def test_2025_06_15_p2_unresolved_all_evidence_returns_81(conn):
    result = members_as_of_all_evidence(conn, "2025-06-15")
    assert len(result) == 81
    assert all(t.startswith("P2T") for t in result)


def test_2026_06_15_p6_primary_verified_strict_returns_80(conn):
    result = members_as_of(conn, "2026-06-15", STRICT)
    assert len(result) == 80
    assert all(t.startswith("P6T") for t in result)


def test_p7_open_ended_current_period(conn):
    # P7 has no effective_to; confidence is CROSS_VALIDATED (not PRIMARY_VERIFIED).
    assert members_as_of(conn, "2026-08-15", STRICT) == frozenset()
    result = members_as_of(conn, "2026-08-15", RECONSTRUCTED)
    assert len(result) == 80
    assert all(t.startswith("P7T") for t in result)


def test_p7_open_ended_far_future_date_still_resolves(conn):
    result = members_as_of(conn, "2030-01-01", RECONSTRUCTED)
    assert len(result) == 80
    assert all(t.startswith("P7T") for t in result)


# --- boundary dates ------------------------------------------------------

def test_boundary_effective_to_is_inclusive_not_exclusive(conn):
    # P1.effective_to = 2025-04-30 is a Wednesday (real trading day); the
    # data's period-to-period gaps (see module docstring) prove effective_to
    # is the last INCLUSIVE valid day, not an exclusive cutoff -- a naive
    # `date < effective_to` implementation would wrongly return zero here.
    result = members_as_of(conn, "2025-04-30", STRICT)
    assert len(result) == 80
    assert all(t.startswith("P1T") for t in result)


def test_boundary_effective_from_is_inclusive(conn):
    result = members_as_of(conn, "2025-02-03", STRICT)
    assert len(result) == 80


def test_boundary_gap_day_between_periods_returns_empty(conn):
    # 2025-05-01 is a real calendar gap between P1.effective_to (2025-04-30)
    # and P2.effective_from (2025-05-02) in the source ledger -- no period
    # covers it, so the accessor must not silently impute membership.
    assert members_as_of(conn, "2025-05-01", STRICT) == frozenset()
    assert members_as_of(conn, "2025-05-01", RECONSTRUCTED) == frozenset()
    assert members_as_of_all_evidence(conn, "2025-05-01") == frozenset()


def test_boundary_before_left_censored_start_returns_empty_even_all_evidence(conn):
    # Nothing is known before P0's left-censored start (2025-01-02): this is
    # what "left-censored" means, not "assume it matches P0".
    assert members_as_of(conn, "2024-12-01", STRICT) == frozenset()
    assert members_as_of(conn, "2024-12-01", RECONSTRUCTED) == frozenset()
    assert members_as_of_all_evidence(conn, "2024-12-01") == frozenset()


# --- other requirements ---------------------------------------------------

def test_no_duplicate_members(conn):
    result = members_as_of(conn, "2025-02-03", STRICT)
    assert len(result) == len(set(result))


def test_invalid_confidence_tier_raises(conn):
    with pytest.raises(ValueError):
        members_as_of(conn, "2025-02-03", "all_evidence")
    with pytest.raises(ValueError):
        members_as_of(conn, "2025-02-03", "bogus")


def test_all_evidence_not_reachable_via_members_as_of_string(conn):
    # The tier literal used by the all-evidence path must not double as a
    # valid confidence_tier value for members_as_of -- opting into UNRESOLVED
    # must go through the separate, explicitly-named function.
    assert ALL_EVIDENCE not in (STRICT, RECONSTRUCTED)
    with pytest.raises(ValueError):
        members_as_of(conn, "2025-02-03", ALL_EVIDENCE)


def test_all_evidence_includes_every_confidence_tier_when_all_present(conn):
    # P1 is PRIMARY_VERIFIED-only in the fixture; sanity check all-evidence
    # matches strict here (no UNRESOLVED/BRACKETED rows to add).
    assert members_as_of_all_evidence(conn, "2025-02-03") == members_as_of(conn, "2025-02-03", STRICT)
