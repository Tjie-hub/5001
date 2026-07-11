"""Optimizer parity (research audit R-3, Phase A).

The optimizer must evaluate THE strategy production trades — the canonical
engine implementation with the shared exit kernel — not a hand-rolled copy.
Contract: at identical parameters, each optimizer runner's trade list is
identical to the canonical engine function's trade list.
"""
import numpy as np
import pandas as pd
import pytest

from engine.strategies import (
    strategy_conservative,
    strategy_momentum,
    strategy_trend_following_breakout,
    strategy_vol_weighted,
    strategy_vwap_reversion,
)
from research.optimizer import STRATEGY_RUNNERS

CAPITAL = 50_000_000


@pytest.fixture(scope="module")
def df():
    """Deterministic 400-bar two-regime series: a steep uptrend with level
    jumps every 31 bars (Donchian breakouts for TFB/momentum) followed by a
    flat segment with deep swings (VWAP reversion). Volume spikes every 7 bars
    and on jump days. Every audited strategy fires at least once (asserted by
    test_fixture_actually_trades)."""
    i1 = np.arange(250)
    jumps = 30.0 * np.cumsum((i1 % 31 == 0) & (i1 > 0))
    c1 = 1000.0 + 4.0 * i1 + 10.0 * np.sin(i1 / 5.0) + jumps
    i2 = np.arange(150)
    c2 = c1[-1] + 80.0 * np.sin(i2 / 6.0)
    close = np.concatenate([c1, c2])
    n = len(close)
    i = np.arange(n)
    spike = ((i % 7 == 0) | ((i % 31 == 0) & (i < 250))).astype(float)
    volume = 1_000_000.0 * (1.0 + 2.0 * spike)
    dates = pd.bdate_range("2024-01-01", periods=n).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": dates, "open": close - 3.0,
                         "high": close + 6.0, "low": close - 6.0,
                         "close": close, "volume": volume})


def _trades(result):
    return [(t.entry_date, t.exit_date, round(t.entry_price, 6),
             round(t.exit_price, 6), t.lots, t.exit_reason,
             round(t.pnl_rp, 2), round(t.pnl_pct, 4))
            for t in result["trades"]]


CASES = [
    ("vol_weighted", strategy_vol_weighted, {}),
    ("momentum", strategy_momentum, {}),
    ("vwap_reversion", strategy_vwap_reversion, {}),
    ("conservative", strategy_conservative, {}),
    ("trend_following_breakout", strategy_trend_following_breakout,
     {"atr_trail_mult": 3.0}),   # canonical default trail
]


@pytest.mark.parametrize("key,canonical,params", CASES,
                         ids=[c[0] for c in CASES])
def test_runner_matches_canonical_at_defaults(df, key, canonical, params):
    runner_out = STRATEGY_RUNNERS[key](df, CAPITAL, dict(params))
    canonical_out = canonical(df.copy(), capital=CAPITAL)
    assert _trades(runner_out) == _trades(canonical_out)
    assert runner_out["final_capital"] == pytest.approx(
        canonical_out["final_capital"])


def test_fixture_actually_trades(df):
    """Parity on an empty trade list proves nothing — the fixture must make
    every audited strategy fire."""
    for key, canonical, _ in CASES:
        n = len(canonical(df.copy(), capital=CAPITAL)["trades"])
        assert n > 0, f"fixture produces no trades for {key}"


def test_canonical_accepts_search_params(df):
    """The grid's parameters must be injectable into the canonical functions —
    the optimizer may not re-implement entries/exits to vary a threshold."""
    out = strategy_trend_following_breakout(
        df.copy(), capital=CAPITAL, atr_mult=2.0, donchian_period=15,
        vol_mult=1.5, atr_expand_mult=0.3)
    assert "trades" in out
    out2 = strategy_vol_weighted(df.copy(), capital=CAPITAL, vr_threshold=2.5,
                                 atr_sl_mult=0.8, atr_tp_mult=1.6)
    assert "trades" in out2
    out3 = strategy_vwap_reversion(df.copy(), capital=CAPITAL,
                                   dist_threshold=-0.005, vr_threshold=1.2,
                                   atr_sl_mult=0.6, atr_tp_mult=1.2)
    assert "trades" in out3
    out4 = strategy_momentum(df.copy(), capital=CAPITAL, vr_threshold=2.0,
                             atr_sl_mult=0.8, atr_tp_mult=2.0)
    assert "trades" in out4
    out5 = strategy_conservative(df.copy(), capital=CAPITAL, vr_threshold=1.5,
                                 atr_sl_mult=0.5, atr_tp_mult=1.2)
    assert "trades" in out5


def test_no_hand_rolled_stop_logic_in_optimizer():
    """Source guard: the optimizer may not contain its own trailing-stop or
    bar-loop execution — the C-8 intrabar look-ahead lived in exactly such a
    duplicate. Signals/exits belong to engine.strategies + the exit kernel."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "research" / "optimizer.py"
           ).read_text(encoding="utf-8")
    for needle in ("trail_stop", "df.iloc[i]", "in_trade"):
        assert needle not in src, (
            f"research/optimizer.py re-implements execution ({needle!r} found)")
