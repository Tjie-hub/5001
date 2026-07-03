"""Live checkers must implement the exact backtested entry conditions
(plan 1C item 1.6 / audit H-3, H-5) and must not mutate the caller's df
(audit H-4: checkers added columns to the shared per-ticker frame).

The harness recomputes each backtest's signal series from the same indicator
functions the strategy uses and compares the LAST bar against the checker.
Duplication of the signal definitions here is deliberate pinning: changing a
strategy's entry must consciously update both.
"""
import numpy as np
import pandas as pd
import pytest

from engine.indicators import calc_atr, calc_delta, calc_vol_ratio, calc_vwap


def _random_df(seed, n=90):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 1000 + np.cumsum(rng.normal(0.5, 15, n))
    close = np.maximum(close, 100.0)
    open_ = close + rng.normal(0, 8, n)
    high = np.maximum(open_, close) + rng.uniform(2, 20, n)
    low = np.minimum(open_, close) - rng.uniform(2, 20, n)
    vol = rng.uniform(5e5, 4e6, n)
    if seed % 3 == 0:
        # Volume spike on the decision bar so VR-gated checkers can fire
        # (also exercises momentum's VR<=5.0 climax cap on big draws).
        vol[-1] *= rng.uniform(2.0, 4.0)
    return pd.DataFrame({"date": dates, "open": open_, "high": high,
                         "low": low, "close": close, "volume": vol})


def _expected_vol_weighted(df):
    vr = calc_vol_ratio(df, 20)
    delta = calc_delta(df)
    sig = (vr > 1.8) & (delta > 0) & (df["close"] > df["open"])
    return bool(sig.iloc[-1])


def _expected_momentum(df):
    from engine.strategies import _watch_signal_block
    vr = calc_vol_ratio(df, 20)
    streak2 = (df["close"] > df["close"].shift(1)) & \
              (df["close"].shift(1) > df["close"].shift(2))
    sig = streak2 & (vr > 1.3) & (vr <= 5.0) & ~_watch_signal_block(df)
    return bool(sig.iloc[-1])


def _expected_vwap_reversion(df):
    vwap = calc_vwap(df)                      # rolling-60, min_periods=60
    vr = calc_vol_ratio(df, 20)
    dist = (df["close"] - vwap) / vwap
    sig = (dist < -0.010) & (vr > 1.3)
    return bool(sig.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else False


def _expected_conservative(df):
    vr = calc_vol_ratio(df, 20)
    ma20 = df["close"].rolling(20).mean()
    atr = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    sig = ((vr > 1.3) & (df["close"] > df["open"]) &
           (df["close"] > ma20) & (atr < atr_ma * 1.5))
    return bool(sig.iloc[-1])


_CASES = [
    ("vol_weighted", _expected_vol_weighted),
    ("momentum", _expected_momentum),
    ("vwap_reversion", _expected_vwap_reversion),
    ("conservative", _expected_conservative),
]


@pytest.mark.parametrize("strategy,expected_fn", _CASES)
def test_checker_matches_backtest_signal(strategy, expected_fn):
    from engine.strategies import _CHECKER_DISPATCH
    checker = _CHECKER_DISPATCH[strategy]
    mismatches = []
    fired = 0
    for seed in range(60):
        df = _random_df(seed)
        expected = expected_fn(df.copy())
        got = bool(checker("TEST", df)["has_signal"])
        fired += int(expected)
        if got != expected:
            mismatches.append((seed, expected, got))
    assert not mismatches, f"{strategy}: checker != backtest on seeds {mismatches[:5]}"
    assert fired > 0, f"{strategy}: harness never fired - generator too tame"


@pytest.mark.parametrize("strategy", [s for s, _ in _CASES])
def test_checker_does_not_mutate_df(strategy):
    from engine.strategies import _CHECKER_DISPATCH
    df = _random_df(3)
    before_cols = list(df.columns)
    before = df.copy(deep=True)
    _CHECKER_DISPATCH[strategy]("TEST", df)
    assert list(df.columns) == before_cols, f"{strategy} added columns {set(df.columns) - set(before_cols)}"
    pd.testing.assert_frame_equal(df, before)
