"""P0.E2.S1.T2 — minimal last-bar freshness guard (audit H-3).

Unit tests for the shared `engine.freshness.is_fresh` helper: normal
fresh-data path, stale-data path, and boundary conditions (exact session
counts, weekend crossing, missing/future dates).
"""
from datetime import date

from engine.freshness import is_fresh

# 2026-07-30 is a Thursday (confirmed trading day, no IDX holiday in
# engine/calendar_filter.py's 2026 holiday list around this date).
TODAY = date(2026, 7, 30)


def test_same_day_bar_is_fresh():
    assert is_fresh(TODAY, as_of=TODAY) is True


def test_one_session_old_bar_is_fresh_default_threshold():
    """Yesterday (Wed 2026-07-29, a trading day) -> 1 session old -> fresh (<=1)."""
    assert is_fresh(date(2026, 7, 29), as_of=TODAY, max_age_sessions=1) is True


def test_two_sessions_old_bar_is_stale_default_threshold():
    """Tue 2026-07-28 -> 2 trading sessions before Thu 2026-07-30 -> stale (>1)."""
    assert is_fresh(date(2026, 7, 28), as_of=TODAY, max_age_sessions=1) is False


def test_weekend_crossing_does_not_count_against_freshness():
    """Friday's bar is still fresh on the following Monday: the two weekend
    days between them are not trading sessions, so 0 sessions have elapsed."""
    friday = date(2026, 7, 24)
    monday = date(2026, 7, 27)
    assert is_fresh(friday, as_of=monday, max_age_sessions=1) is True


def test_missing_last_date_is_never_fresh():
    assert is_fresh(None, as_of=TODAY) is False


def test_future_last_date_is_treated_as_fresh_not_stale():
    """A bar dated after as_of (clock skew / data anomaly) must not be
    reported as stale — this guard's job is catching lagging data, not
    validating future dates."""
    assert is_fresh(date(2026, 7, 31), as_of=TODAY) is True


def test_string_date_accepted_same_as_date_object():
    assert is_fresh("2026-07-30", as_of=TODAY) is True
    assert is_fresh("2026-07-28", as_of=TODAY) is False


def test_max_age_sessions_zero_makes_even_one_session_old_stale():
    """Boundary: threshold of 0 sessions means only same-day bars are fresh."""
    assert is_fresh(date(2026, 7, 29), as_of=TODAY, max_age_sessions=0) is False
    assert is_fresh(TODAY, as_of=TODAY, max_age_sessions=0) is True


def test_max_age_sessions_boundary_is_inclusive():
    """Exactly max_age_sessions old is fresh; one more session is not."""
    assert is_fresh(date(2026, 7, 28), as_of=TODAY, max_age_sessions=2) is True
    assert is_fresh(date(2026, 7, 27), as_of=TODAY, max_age_sessions=2) is False
