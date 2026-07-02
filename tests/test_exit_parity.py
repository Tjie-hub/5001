"""Backtest exits must match the engine/exits kernel (plan 1B Tasks 5-6).

The C-8 scenario: a bar makes a new high AND a deep low. The old percent
trail ratcheted from the same bar's high and exited on that bar's low —
look-ahead (no guarantee the high printed first). The kernel only trails
from the PRIOR bar's extreme.
"""
import numpy as np
import pandas as pd
import pytest


def _flat_df(n=20, close=1000.0, rng=20.0):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "open": np.full(n, close), "high": np.full(n, close + rng / 2),
        "low": np.full(n, close - rng / 2), "close": np.full(n, close),
        "volume": np.full(n, 1_000_000.0),
    })


def test_trailing_stop_does_not_ratchet_from_same_bar_high():
    """Audit C-8. Signal at bar 18 -> entry bar 19. Bar 20 spikes high=1100
    then low=1041 (still above every stop derived from PRIOR extremes).
    Old code: stop ratchets to ~1100*(1-2%)=1078 intrabar -> bogus exit.
    New kernel: stop for bar 20 comes from prior extreme (1010) -> hold,
    and the trade closes EOD on the last bar."""
    from engine.strategies import run_strategy

    df = _flat_df(22)                       # bars 0..21, ATR14 = 20 everywhere
    df.loc[19, ["open", "high", "low", "close"]] = [1000, 1010, 995, 1005]
    df.loc[20, ["open", "high", "low", "close"]] = [1050, 1100, 1041, 1050]
    # bar 21 stays above the LEGITIMATE prior-extreme stop (1100 - 20 = 1080)
    df.loc[21, ["open", "high", "low", "close"]] = [1090, 1095, 1085, 1092]

    signals = pd.Series(False, index=df.index)
    signals.iloc[18] = True                 # entry at bar 19 open

    result = run_strategy(df, signals, atr_sl_mult=1.0, atr_tp_mult=100.0,
                          min_rr=1.0, trail_sl=True, strategy_name="t")
    assert len(result["trades"]) == 1
    t = result["trades"][0]
    assert t.exit_reason == "EOD", (
        f"expected EOD hold-through, got {t.exit_reason} @ {t.exit_price} "
        f"on {t.exit_date} — same-bar trail ratchet (C-8) still present"
    )
    assert t.exit_date == "2026-01-22"      # last bar
