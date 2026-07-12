import pandas as pd

from research.regime.transitions import detect_transitions


def _labels(rows):
    return pd.DataFrame(rows)


def test_transition_flagged_within_k_bars_of_a_regime_change():
    # A synthetic per-date regime label series: BULL x5, then SIDEWAYS x5.
    regimes = ["BULL"] * 5 + ["SIDEWAYS"] * 5
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=2)
    by_date = dict(zip(out["date"], out["state"]))
    # The change happens at index 5; bars 5 and 6 are within k=2 of it -> TRANSITION.
    assert by_date[dates[5]] == "TRANSITION"
    assert by_date[dates[6]] == "TRANSITION"
    # Bar 8 is > k bars past the change -> back to STEADY.
    assert by_date[dates[8]] == "STEADY"


def test_direction_records_from_and_to_regime():
    regimes = ["BULL"] * 5 + ["SIDEWAYS"] * 5
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=2)
    row = out[out["date"] == dates[5]].iloc[0]
    assert row["direction"] == "BULL->SIDEWAYS"


def test_steady_run_has_no_transitions():
    regimes = ["BULL"] * 10
    dates = pd.date_range("2024-01-01", periods=len(regimes), freq="B").strftime("%Y-%m-%d")
    df = _labels({"date": list(dates), "regime": regimes})
    out = detect_transitions(df, k_bars=3)
    assert (out["state"] == "STEADY").all()
