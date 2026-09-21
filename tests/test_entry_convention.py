"""L-2 regression suite: no signal may ever be filled at a price that had
already printed before the signal timestamp.

The defect: check_nr7_signal returned details['price'] = today's OPEN, and
scheduler/scanner.py passed it straight to open_trade() from a 10:05/11:05/14:35
scan. The bias was systematically favourable because the NR7 trigger IS "the open
gapped above the setup bar's high" -- only the fills that had already gone the
right way were taken.
"""
import pandas as pd
import pytest

from engine import entry_convention as ec


def _df(n=30, last_close=1000.0, last_open=980.0):
    return pd.DataFrame({
        "date": pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d"),
        "open": [900.0] * (n - 1) + [last_open],
        "high": [1100.0] * n,
        "low": [800.0] * n,
        "close": [950.0] * (n - 1) + [last_close],
        "volume": [1_000_000.0] * n,
    })


class TestConvention:

    def test_the_validated_convention_is_next_session_open(self):
        assert ec.ENTRY_RULE_NEXT_OPEN == "NEXT_SESSION_OPEN"

    def test_session_open_is_classified_retrospective(self):
        assert ec.is_retrospective(ec.BASIS_SESSION_OPEN)

    def test_last_close_is_not_retrospective(self):
        assert not ec.is_retrospective(ec.BASIS_LAST_CLOSE)

    def test_decision_price_is_the_last_bar_close(self):
        dp = ec.decision_price(_df(last_close=1234.0))
        assert dp.price == 1234.0
        assert dp.basis == ec.BASIS_LAST_CLOSE
        assert dp.bar_date

    def test_decision_price_handles_empty_frame(self):
        dp = ec.decision_price(pd.DataFrame())
        assert dp.price is None


class TestNoRetrospectiveFill:

    def test_session_open_basis_never_fills(self):
        """The exact L-2 shape: a checker reporting the session open."""
        res = ec.executable_entry(
            {"price": 980.0, "price_basis": ec.BASIS_SESSION_OPEN}, _df())
        assert res.action == ec.ACTION_STAGE
        assert res.fill_price is None
        assert "retrospective" in res.reason

    def test_last_close_basis_also_stages_not_fills(self):
        """Live scans never fill at all -- the validated convention is the NEXT
        session's open, which does not exist yet at scan time."""
        res = ec.executable_entry(
            {"price": 1000.0, "price_basis": ec.BASIS_LAST_CLOSE}, _df())
        assert res.action == ec.ACTION_STAGE
        assert res.fill_price is None
        assert res.entry_rule == ec.ENTRY_RULE_NEXT_OPEN

    def test_no_resolution_ever_returns_a_fill_price(self):
        for basis in (ec.BASIS_SESSION_OPEN, ec.BASIS_LAST_CLOSE, ec.BASIS_NEXT_OPEN, None):
            res = ec.executable_entry({"price": 1.0, "price_basis": basis}, _df())
            assert res.fill_price is None
            assert not res.is_fill

    def test_missing_price_rejects(self):
        res = ec.executable_entry({}, pd.DataFrame())
        assert res.action == ec.ACTION_REJECT

    def test_decision_price_is_carried_even_when_staged(self):
        res = ec.executable_entry(
            {"price": 980.0, "price_basis": ec.BASIS_SESSION_OPEN},
            _df(last_close=1010.0))
        assert res.decision.price == 1010.0     # what the market is NOW
        assert res.decision.price != 980.0      # not the stale open


class TestCheckerContract:

    def test_nr7_declares_its_price_basis_as_the_session_open(self):
        """NR7 must not hide that its price is a past print."""
        from engine.strategies import check_nr7_signal
        import numpy as np
        n = 40
        df = pd.DataFrame({
            "date": pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d"),
            "open": np.linspace(1000, 1040, n),
            "high": np.linspace(1010, 1050, n),
            "low": np.linspace(990, 1030, n),
            "close": np.linspace(1005, 1045, n),
            "volume": np.full(n, 1_000_000.0),
        })
        res = check_nr7_signal(df)
        assert res["details"]["price_basis"] == ec.BASIS_SESSION_OPEN
        assert res["details"]["entry_rule"] == ec.ENTRY_RULE_NEXT_OPEN

    def test_ensure_entry_price_stamps_a_basis_on_every_signal(self):
        from engine.strategy_specs import ensure_entry_price
        out = ensure_entry_price({"has_signal": True, "details": {"close": 500.0}})
        assert out["details"]["price"] == 500.0
        assert out["details"]["price_basis"] == ec.BASIS_LAST_CLOSE
        assert out["details"]["entry_rule"] == ec.ENTRY_RULE_NEXT_OPEN

    def test_ensure_entry_price_does_not_overwrite_a_declared_basis(self):
        from engine.strategy_specs import ensure_entry_price
        out = ensure_entry_price({"has_signal": True,
                                  "details": {"price": 1.0,
                                              "price_basis": ec.BASIS_SESSION_OPEN}})
        assert out["details"]["price_basis"] == ec.BASIS_SESSION_OPEN


class TestBacktestParity:

    def test_backtest_fills_at_the_next_bar_open(self):
        """The convention this module enforces is not new policy: it is what
        every walk-forward strategy function already does. If a strategy stops
        filling at row['open'] of the bar after the setup bar, this must be
        revisited deliberately."""
        import inspect
        from engine import strategies
        for name in ("strategy_nr7_breakout", "strategy_inside_bar_breakout",
                     "strategy_orb", "strategy_volume_profile_poc",
                     "strategy_crash_recovery", "strategy_panic_rebound"):
            src = inspect.getsource(getattr(strategies, name))
            assert "raw_entry" in src and "row['open']" in src, name
        tfb = inspect.getsource(strategies.strategy_trend_following_breakout)
        assert "row['open']" in tfb
