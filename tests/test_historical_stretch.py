"""Phase 9 tests — Stretch indexing is t-9 … t (inclusive of the setup day).

Recovered primary formulation (handover §4): evaluated at the conclusion of
setup day t, 10-day window ending AT the setup day; execution day is t+1 and
must NEVER contribute. This file is the deterministic proof demanded by the
tasking (§7).
"""
import pytest

from engine.historical.stretch import stretch_at_setup


def _series(day_distances, setup_distance=None):
    """Bars where min(|O−H|, |O−L|) == the given per-day distance."""
    opens, highs, lows = [], [], []
    for i, d in enumerate(day_distances):
        o = 100.0
        opens.append(o)
        highs.append(o + d)
        lows.append(o - d)
    return opens, highs, lows


def test_stretch_is_average_of_ten_closest_extreme_distances():
    # Distances 1..10 average to 5.5.
    opens, highs, lows = _series([float(i) for i in range(1, 11)])
    assert stretch_at_setup(opens, highs, lows, setup_t=9, lookback=10) \
        == pytest.approx(5.5)


def test_window_is_t_minus_9_through_t_inclusive():
    """Setup day t IS in the window: zeroing its distance changes the average
    from 5.5 to (0+1+…+9)/10 = 4.5."""
    opens, highs, lows = _series([float(i) for i in range(1, 10)], )
    opens.append(100.0)
    highs.append(100.0)   # setup day distance 0
    lows.append(100.0)
    assert stretch_at_setup(opens, highs, lows, setup_t=9, lookback=10) \
        == pytest.approx(4.5)


def test_execution_day_is_never_in_the_window():
    """The execution day (index 10) carries a colossal distance; the Stretch
    used on it must still be the average of days 0..9 = 5.5."""
    distances = [float(i) for i in range(1, 11)] + [10_000.0]
    opens, highs, lows = _series(distances)
    assert stretch_at_setup(opens, highs, lows, setup_t=9, lookback=10) \
        == pytest.approx(5.5)


def test_uses_min_of_open_high_and_open_low():
    # Asymmetric day: |O−H| = 3, |O−L| = 7 → the min (3) is used, not the range.
    opens, highs, lows = [100.0], [103.0], [93.0]
    assert stretch_at_setup(opens, highs, lows, setup_t=0, lookback=1) \
        == pytest.approx(3.0)


def test_insufficient_history_raises():
    opens, highs, lows = _series([1.0, 2.0])
    with pytest.raises(ValueError, match="insufficient_history"):
        stretch_at_setup(opens, highs, lows, setup_t=9, lookback=10)
