"""Live NR7 Breakout checker (the one positive-edge strategy from the 2026-07-04
re-baseline). The checker mirrors strategy_nr7_breakout's per-bar entry applied
to the last bar: bar[-2] is the narrowest-range bar of the trailing 7 (NR7) with
volume >= 0.8x its 5-bar avg, and the last bar opened above bar[-2]'s high."""
import numpy as np
import pandas as pd


def _base_df(n=30, rng_wide=40.0):
    """Wide-range, steady uptrend bars (so the seeded NR7 bar is the narrowest)."""
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    close = 1000 + np.arange(n) * 5.0
    return pd.DataFrame({
        "date": dates,
        "open": close - rng_wide / 4,
        "high": close + rng_wide / 2,
        "low": close - rng_wide / 2,
        "close": close,
        "volume": np.full(n, 1_000_000.0),
    })


def _nr7_setup(breakout=True):
    """bar[-2] = narrow NR7 bar; bar[-1] = breakout above its high (or not)."""
    df = _base_df()
    nr7_high, nr7_low = 1120.0, 1118.0          # very narrow range (2) vs others (40)
    df.loc[df.index[-2], ["open", "high", "low", "close", "volume"]] = \
        [1119.0, nr7_high, nr7_low, 1119.5, 1_000_000.0]
    last_open = nr7_high + 5.0 if breakout else nr7_high - 5.0
    df.loc[df.index[-1], ["open", "high", "low", "close", "volume"]] = \
        [last_open, last_open + 30, last_open - 20, last_open + 10, 1_200_000.0]
    return df


def test_nr7_signal_fires_on_breakout():
    from engine.strategies import check_nr7_signal
    res = check_nr7_signal(_nr7_setup(breakout=True))
    assert res["has_signal"] is True, res["reason"]
    d = res["details"]
    assert d["price"] == 1125.0                 # last bar open (breakout entry)
    assert d["sl"] == 1118                       # NR7 bar low
    assert d["tp"] > d["price"]
    assert (d["tp"] - d["price"]) / d["price"] >= 0.015


def test_nr7_no_signal_without_breakout():
    from engine.strategies import check_nr7_signal
    res = check_nr7_signal(_nr7_setup(breakout=False))
    assert res["has_signal"] is False
    assert "breakout" in res["reason"].lower()


def test_nr7_no_signal_when_last_bar_not_narrowest():
    """If bar[-2] is NOT the narrowest of the trailing 7, no signal."""
    from engine.strategies import check_nr7_signal
    df = _base_df()                              # all bars equal range -> [-2] not uniquely min
    # make an earlier bar narrower than bar[-2]
    df.loc[df.index[-4], ["high", "low"]] = [df.loc[df.index[-4], "close"] + 1,
                                             df.loc[df.index[-4], "close"] - 1]
    df.loc[df.index[-1], "open"] = df.loc[df.index[-2], "high"] + 5   # would-be breakout
    res = check_nr7_signal(df)
    assert res["has_signal"] is False


def test_nr7_insufficient_data():
    from engine.strategies import check_nr7_signal
    res = check_nr7_signal(_base_df(n=10))
    assert res["has_signal"] is False
    assert "cukup" in res["reason"].lower() or "22" in res["reason"]


def test_nr7_registered_everywhere():
    """Wiring coherence: dispatch + SPECS.live_checker + regime map must all
    agree (the consistency tests in test_strategy_specs enforce this too)."""
    from engine.strategies import _CHECKER_DISPATCH
    from engine.strategy_specs import SPECS
    from scheduler.scanner import _REGIME_STRATEGY_MAP
    assert "NR7 Breakout" in _CHECKER_DISPATCH
    assert SPECS["NR7 Breakout"].live_checker is True
    assert any("NR7 Breakout" in v for v in _REGIME_STRATEGY_MAP.values())


def test_nr7_dispatch_end_to_end():
    """check_current_entry_signal routes NR7 and applies the entry-price
    contract (details['price'] guaranteed)."""
    from engine.strategies import check_current_entry_signal
    res = check_current_entry_signal("TEST", "NR7 Breakout", df=_nr7_setup(True))
    # weekly gate soft-passes (<100 bars); signal survives with a price
    assert res["has_signal"] is True, res["reason"]
    assert res["details"]["price"] == 1125.0
