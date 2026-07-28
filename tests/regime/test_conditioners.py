import numpy as np
import pandas as pd

from research.regime.conditioners import vol_tier, liq_tier


def _series(segments):
    """Build a close series from (n_bars, daily_sigma) segments (deterministic seed)."""
    rng = np.random.default_rng(0)
    close = [100.0]
    for n, sigma in segments:
        for step in rng.normal(0, sigma, n):
            close.append(close[-1] * (1 + step))
    close = np.array(close[1:])
    dates = pd.date_range("2024-01-01", periods=len(close), freq="B")
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": close})


def test_vol_tier_high_when_recent_vol_exceeds_ticker_median():
    # Calm history then a turbulent recent window -> recent vol >> median -> HIGH_VOL.
    df = _series([(120, 0.005), (20, 0.04)])
    entry = df["date"].iloc[-1]
    assert vol_tier(df, entry, window=20, median_lookback=120) == "HIGH_VOL"


def test_vol_tier_low_when_recent_vol_below_ticker_median():
    # Turbulent history then a calm recent window -> recent vol << median -> LOW_VOL.
    df = _series([(120, 0.04), (20, 0.005)])
    entry = df["date"].iloc[-1]
    assert vol_tier(df, entry, window=20, median_lookback=120) == "LOW_VOL"


def test_vol_tier_no_lookahead_uses_only_bars_up_to_entry():
    df = _series([(120, 0.005), (20, 0.04)])
    entry = df["date"].iloc[100]
    # Corrupting bars STRICTLY AFTER the entry must not change the tier at the entry.
    df2 = df.copy()
    df2.loc[101:, "close"] = df2.loc[101:, "close"] * 100
    assert (vol_tier(df, entry, window=20, median_lookback=120)
            == vol_tier(df2, entry, window=20, median_lookback=120))


def test_liq_tier_high_when_adv_at_least_multiple_of_floor():
    # VALUE_LIQ_MIN_IDR = 5e9; high_multiple 2.0 -> HIGH at >= 1e10
    assert liq_tier(adv_value=1.2e10, high_multiple=2.0) == "HIGH_LIQ"
    assert liq_tier(adv_value=6.0e9, high_multiple=2.0) == "LOW_LIQ"


def test_liq_tier_none_adv_is_low():
    assert liq_tier(adv_value=None, high_multiple=2.0) == "LOW_LIQ"
