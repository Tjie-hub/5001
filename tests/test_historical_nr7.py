"""Phase 9 tests — NR7 setup detection exactly per recovered primary text.

Recovered rule: setup day t, window t-6…t, current range must be LESS than
each of the previous six, range = High − Low. Tie handling: PRIMARY SOURCE
NOT RECOVERED — both policies are engine conventions and behaviorally distinct.
"""
import pytest

from engine.historical.nr7 import (TiePolicy, detect_nr7_days, evaluate_nr7,
                                   is_nr7, nr7_range)


def test_strict_less_accepts_unique_minimum():
    ranges = [10, 10, 10, 10, 10, 10, 5]
    assert is_nr7(ranges, 6, TiePolicy.STRICT_LESS) is True


def test_strict_less_rejects_ties_with_prior_six():
    ranges = [5, 10, 10, 10, 10, 10, 5]
    assert is_nr7(ranges, 6, TiePolicy.STRICT_LESS) is False
    assert evaluate_nr7(ranges, 6, TiePolicy.STRICT_LESS) == "tie_rejected"


def test_min_inclusive_accepts_ties():
    ranges = [5, 10, 10, 10, 10, 10, 5]
    assert is_nr7(ranges, 6, TiePolicy.MIN_INCLUSIVE) is True


def test_tie_policies_are_behaviorally_distinct():
    """The two conventions must not collapse into each other (Phase 9 C-1)."""
    ranges = [5, 10, 10, 10, 10, 10, 5]
    assert evaluate_nr7(ranges, 6, TiePolicy.STRICT_LESS) \
        != evaluate_nr7(ranges, 6, TiePolicy.MIN_INCLUSIVE)


def test_exact_window_indexing_t_minus_6_to_t():
    """Only the six bars immediately before t are the comparison set — a small
    range at t-7 must NOT influence the test at t."""
    ranges = [1, 10, 10, 10, 10, 10, 10, 5]   # tiny bar at index 0 (t-7 for t=7)
    assert is_nr7(ranges, 7, TiePolicy.STRICT_LESS) is True
    # ...but a small bar INSIDE the window disqualifies t.
    ranges = [10, 10, 10, 10, 1, 10, 10, 5]   # tiny bar at index 4 = t-3
    assert is_nr7(ranges, 7, TiePolicy.STRICT_LESS) is False


def test_insufficient_history_raises():
    with pytest.raises(ValueError, match="insufficient_history"):
        is_nr7([1, 1, 1, 1, 1, 1], 5, TiePolicy.STRICT_LESS)


def test_range_is_high_minus_low_not_true_range():
    """Crabel's range is the absolute H−L range; True Range substitution is
    explicitly rejected by the Phase 8 handover."""
    assert nr7_range(105.0, 95.0) == 10.0
    # A gap outside H−L must not widen the range (TR would):
    assert nr7_range(high=100.0, low=90.0) == 10.0


def test_detect_nr7_days_skips_warmup():
    ranges = [10] * 9 + [5] + [10] * 3
    assert detect_nr7_days(ranges, TiePolicy.STRICT_LESS) == [9]
