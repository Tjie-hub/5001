"""Phase 2C item 2.6 — RegimeClassifier honesty.

train() must stop reporting IN-SAMPLE accuracy as the headline. It now reports
a temporal-holdout accuracy (fit on the early portion, evaluated on a later
portion with a forward_days embargo so the forward-looking labels don't leak
across the split) plus whether that beats the holdout majority baseline. The
deployed model is still fit on ALL data (evaluate on holdout, deploy on full).
"""
import pytest
import numpy as np
import pandas as pd

from engine.regime_filter import RegimeClassifier


def _mixed_df(cycles=5):
    """Interleaved up/down/flat segments repeated so EVERY temporal slice
    (train and holdout) contains all 3 regime classes. Segments are steep
    enough that the 5-day forward return crosses the ±2% BULL/BEAR label
    threshold (a 100-price series needs ~2pt/5d moves)."""
    up   = [i * 0.8 for i in range(25)]              # +BULL
    down = [-i * 0.8 for i in range(25)]             # -BEAR
    flat = [0.15 * (i % 3 - 1) for i in range(20)]   # ~SIDEWAYS
    deltas = (up + down + flat) * cycles
    close = [100.0]
    for d in deltas:
        close.append(max(20.0, close[-1] + d))
    n = len(close)
    dates = pd.date_range("2023-01-02", periods=n, freq="B").strftime("%Y-%m-%d")
    close = np.array(close)
    return pd.DataFrame({
        "date": dates, "open": close - 0.2, "high": close + 1.0,
        "low": close - 1.0, "close": close, "volume": np.full(n, 1e6),
    })


def test_train_reports_holdout_not_only_in_sample():
    clf = RegimeClassifier()
    m = clf.train(_mixed_df())
    assert "error" not in m, m.get("error")
    # honest headline present + separated from in-sample
    assert "holdout_accuracy" in m and "in_sample_accuracy" in m
    assert "holdout_baseline" in m and "beats_baseline" in m
    assert 0.0 <= m["holdout_accuracy"] <= 1.0
    assert 0.0 <= m["in_sample_accuracy"] <= 1.0
    # the classifier is stored + usable
    assert clf.is_trained
    assert clf.holdout_accuracy == pytest.approx(m["holdout_accuracy"], abs=1e-4)


def test_headline_accuracy_is_the_holdout_number():
    clf = RegimeClassifier()
    m = clf.train(_mixed_df())
    # 'accuracy' (back-compat key) must now be the honest OOS number, not in-sample
    assert m["accuracy"] == m["holdout_accuracy"]


def test_beats_baseline_is_a_bool_flag():
    clf = RegimeClassifier()
    m = clf.train(_mixed_df())
    assert isinstance(m["beats_baseline"], bool)
    assert m["beats_baseline"] == (m["holdout_accuracy"] > m["holdout_baseline"])


def test_class_counts_still_sum_to_n_samples_full_data():
    """The deployed model is fit on ALL labeled data — class_counts/n_samples
    describe the full set (invariant relied on by test_regime_3class)."""
    clf = RegimeClassifier()
    m = clf.train(_mixed_df())
    assert sum(m["class_counts"].values()) == m["n_samples"]


def test_deployed_model_predicts_valid_label():
    clf = RegimeClassifier()
    clf.train(_mixed_df())
    regime, conf = clf.predict(_mixed_df())
    assert regime in ("BULL", "BEAR", "SIDEWAYS")
    assert 0.0 <= conf <= 1.0
