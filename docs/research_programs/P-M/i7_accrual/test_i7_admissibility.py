#!/usr/bin/env python3
"""Tests for the I7 E-PIT admissibility gate.

Run:  python3 -m pytest test_i7_admissibility.py -q
      python3 test_i7_admissibility.py          (no-pytest fallback)

These tests are the enforcement of requirement 1(d)/1(e): a capture may not
produce an I7-admissible cell before the 16:15 WIB post-session cutoff.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i7_admissibility as ADM

# 2026-09-10 is a Thursday (grid 335); 2026-09-11 is a Friday (grid 275).
THU, FRI = "2026-09-10", "2026-09-11"


# --- E-PIT-1: wholesale historical exclusion --------------------------------

def test_epit1_excludes_entire_v002_interval():
    for sd in ("2025-01-02", "2025-08-05", "2026-04-27"):
        v = ADM.admissible(sd, f"{sd}T20:00:00", 335)
        assert not v.admissible and v.rule == "E-PIT-1", sd


def test_epit1_boundary_is_exact():
    assert ADM.admissible("2026-04-27", "2026-04-27T20:00:00", 335).rule == "E-PIT-1"
    # 2026-04-28 is a Tuesday -> grid 335; first contemporaneous session.
    assert ADM.admissible("2026-04-28", "2026-04-28T20:00:00", 335).admissible


# --- E-PIT-2: contemporaneous provenance ------------------------------------

def test_epit2_rejects_missing_provenance():
    assert ADM.admissible(THU, None, 335).rule == "E-PIT-2"


def test_epit2_rejects_backfill_lag():
    assert ADM.admissible(THU, "2026-09-12T20:00:00", 335).rule == "E-PIT-2"   # lag 2
    assert ADM.admissible(THU, "2027-01-01T20:00:00", 335).rule == "E-PIT-2"   # deep


def test_epit2_accepts_next_day_write():
    """lag == 1 is after the session by construction, so the cutoff cannot bite."""
    v = ADM.admissible(THU, "2026-09-11T09:00:00", 335)
    assert v.admissible, v.detail


def test_epit2_rejects_write_before_session():
    assert ADM.admissible(THU, "2026-09-09T20:00:00", 335).rule == "E-PIT-2"


# --- E-PIT-3: the 16:15 WIB cutoff (requirement 1e) -------------------------

def test_epit3_rejects_mid_session_capture():
    """The trap: a same-day 13:00 capture holds a partial session and would be
    mis-classified EARLY_TILTED by capture artifact rather than behaviour."""
    for hhmm in ("09:00", "12:00", "13:00", "14:00", "15:00", "15:49", "16:14"):
        v = ADM.admissible(THU, f"{THU}T{hhmm}:00", 335)
        assert not v.admissible and v.rule == "E-PIT-3", hhmm


def test_epit3_cutoff_boundary_is_exact():
    assert ADM.admissible(THU, f"{THU}T16:14:59", 335).rule == "E-PIT-3"
    assert ADM.admissible(THU, f"{THU}T16:15:00", 335).admissible


def test_epit3_accepts_the_production_cron_hour():
    """The live cron writes ~81.9% of cells at 20:00 WIB."""
    assert ADM.admissible(THU, f"{THU}T20:15:01", 335).admissible


# --- E-PIT-4: session completeness ------------------------------------------

def test_epit4_requires_the_weekday_grid():
    assert ADM.admissible(THU, f"{THU}T20:00:00", 275).rule == "E-PIT-4"   # Fri grid on Thu
    assert ADM.admissible(FRI, f"{FRI}T20:00:00", 335).rule == "E-PIT-4"   # Thu grid on Fri
    assert ADM.admissible(THU, f"{THU}T20:00:00", 334).rule == "E-PIT-4"
    assert ADM.admissible(THU, f"{THU}T20:00:00", 0).rule == "E-PIT-4"
    assert ADM.admissible(THU, f"{THU}T20:00:00", None).rule == "E-PIT-4"


def test_epit4_friday_grid_accepted():
    assert ADM.admissible(FRI, f"{FRI}T20:00:00", ADM.GRID_FRI).admissible


def test_expected_bars_matches_measured_reality():
    """Verified against v002: all 58 Fridays carry 275, all Mon-Thu carry 335."""
    assert ADM.expected_bars("2026-09-11") == 275          # Friday
    for d in ("2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10"):
        assert ADM.expected_bars(d) == 335


# --- rule precedence --------------------------------------------------------

def test_rule_precedence_is_deterministic():
    """A historical cell fails E-PIT-1 even though it also violates 3 and 4:
    the wholesale interval is tested first so accounting never double-counts."""
    v = ADM.admissible("2025-06-02", "2025-06-02T09:00:00", 7)
    assert v.rule == "E-PIT-1"


# --- operational guard (requirement 1d) -------------------------------------

def test_capture_guard_refuses_before_cutoff():
    now = _dt.datetime.fromisoformat(f"{THU}T15:30:00")
    v = ADM.capture_permitted_now(THU, now)
    assert not v.admissible and v.rule == "E-PIT-3"


def test_capture_guard_permits_after_cutoff():
    assert ADM.capture_permitted_now(
        THU, _dt.datetime.fromisoformat(f"{THU}T16:15:00")).admissible
    assert ADM.capture_permitted_now(
        THU, _dt.datetime.fromisoformat(f"{THU}T18:30:00")).admissible


def test_capture_guard_refuses_future_session():
    v = ADM.capture_permitted_now(THU, _dt.datetime.fromisoformat("2026-09-09T20:00:00"))
    assert not v.admissible and v.rule == "E-PIT-2"


def test_capture_guard_permits_next_day():
    assert ADM.capture_permitted_now(
        THU, _dt.datetime.fromisoformat("2026-09-11T09:00:00")).admissible


# --- outcome-blindness ------------------------------------------------------

def test_gate_is_outcome_blind():
    """admissible() takes only provenance + completeness. No price, no return,
    no outcome can reach it -- enforced by the signature itself."""
    import inspect
    params = set(inspect.signature(ADM.admissible).parameters)
    assert params == {"session_date", "captured_at_wib", "n_bars"}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bad = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            bad += 1
            print(f"  FAIL  {fn.__name__}  {e}")
    print(f"\n{len(fns)-bad}/{len(fns)} passed")
    raise SystemExit(1 if bad else 0)
