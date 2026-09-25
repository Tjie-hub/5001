"""Cost-by-liquidity estimators (docs/research_programs/P-M/cost_liquidity/cost_by_adv.py).

On a simulated market with a known bid-ask spread (efficient mid-price random walk, trades printed at
bid or ask), the Abdi-Ranaldo daily estimator and the Roll intraday estimator both recover the spread,
and the per-day liquidity panel uses only sessions before t (no look-ahead).
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "docs" / "research_programs" / "P-M" / "cost_liquidity" / "cost_by_adv.py"


@pytest.fixture(scope="module")
def cb():
    spec = importlib.util.spec_from_file_location("cost_by_adv", MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _market(days, spread, rng, per_day=300, vol=0.02):
    """Minute prints at mid·exp(±spread/2); returns daily OHLC and per-day minute log prices."""
    lm = np.cumsum(rng.normal(0, vol / np.sqrt(per_day), days * per_day)) + np.log(1000)
    side = rng.choice([-1, 1], days * per_day)
    lp = (lm + side * spread / 2).reshape(days, per_day)
    return (np.exp(lp[:, -1]), np.exp(lp.max(1)), np.exp(lp.min(1))), list(lp)


def test_tick_table(cb):
    assert list(cb.tick_size([50, 199, 200, 499, 500, 1999, 2000, 4999, 5000])) == [1, 1, 2, 2, 5, 5, 10, 10, 25]


@pytest.mark.parametrize("spread", [0.005, 0.02])
def test_abdi_ranaldo_recovers_spread(cb, spread):
    rng = np.random.default_rng(7)
    (c, h, l), _ = _market(2000, spread, rng)
    est = cb.ar_spread_from_terms(cb.ar_terms(c, h, l)[:-1])
    assert est == pytest.approx(spread, rel=0.35)


@pytest.mark.parametrize("spread", [0.005, 0.02])
def test_roll_recovers_spread(cb, spread):
    rng = np.random.default_rng(11)
    _, days = _market(200, spread, rng)
    assert cb.roll_spread(days) == pytest.approx(spread, rel=0.15)


def test_liquidity_panel_uses_only_past_sessions(cb):
    rng = np.random.default_rng(3)
    (c, h, l), _ = _market(80, 0.01, rng)
    d = pd.DataFrame({"ticker": "X", "date": pd.bdate_range("2024-01-01", periods=80),
                      "close": c, "high": h, "low": l, "volume": 1.0})
    base = cb.per_day_liquidity(d)
    d2 = d.copy()
    d2.loc[50:, ["close", "high", "low"]] *= 3.0          # change everything from row 50 on
    moved = cb.per_day_liquidity(d2)
    pd.testing.assert_series_equal(base.s_ar.iloc[:51], moved.s_ar.iloc[:51])
    pd.testing.assert_series_equal(base.sig_d.iloc[:51], moved.sig_d.iloc[:51])
