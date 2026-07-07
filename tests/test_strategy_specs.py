"""Strategy spec registry + checker output contract (audit C-1 / plan 1A).

engine/strategy_specs.py is the single source of truth about each strategy's
live capability. ensure_entry_price is the contract normalizer: any
has_signal=True checker result MUST end up with details['price'], because
scheduler/scanner.py's trade-open path reads exactly that key.
"""
import numpy as np
import pandas as pd
import pytest


def _df_last_close(close_last: float = 1234.0, n: int = 30) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = np.full(n, 1000.0)
    close[-1] = close_last
    return pd.DataFrame({
        "date": dates, "open": close - 5, "high": close + 10,
        "low": close - 10, "close": close, "volume": np.full(n, 1_000_000.0),
    })


# ── ensure_entry_price ────────────────────────────────────────────────────────

def test_ensure_price_noop_when_no_signal():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": False, "reason": "x", "details": {}}
    out = ensure_entry_price(res, _df_last_close())
    assert "price" not in out["details"]


def test_ensure_price_keeps_existing_price():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": True, "reason": "x", "details": {"price": 500.0, "close": 600.0}}
    out = ensure_entry_price(res, _df_last_close())
    assert out["details"]["price"] == 500.0


def test_ensure_price_falls_back_to_close_key():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": True, "reason": "x", "details": {"close": 600.0}}
    out = ensure_entry_price(res, _df_last_close())
    assert out["details"]["price"] == 600.0


def test_ensure_price_falls_back_to_current_price_key():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": True, "reason": "x", "details": {"current_price": 700.0}}
    out = ensure_entry_price(res, _df_last_close())
    assert out["details"]["price"] == 700.0


def test_ensure_price_falls_back_to_df_last_close():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": True, "reason": "x", "details": {"vr": 2.0}}
    out = ensure_entry_price(res, _df_last_close(1234.0))
    assert out["details"]["price"] == pytest.approx(1234.0)


def test_ensure_price_creates_details_dict_if_missing():
    from engine.strategy_specs import ensure_entry_price
    res = {"has_signal": True, "reason": "x"}
    out = ensure_entry_price(res, _df_last_close(1234.0))
    assert out["details"]["price"] == pytest.approx(1234.0)


# ── SPECS shape ───────────────────────────────────────────────────────────────

def test_specs_have_unique_canonical_names():
    from engine.strategy_specs import SPECS
    assert len(SPECS) == 14
    for name, spec in SPECS.items():
        assert spec.name == name


def test_counter_trend_specs_are_flagged():
    from engine.strategy_specs import SPECS
    ct = {n for n, s in SPECS.items() if s.counter_trend}
    assert ct == {"Crash Recovery", "Panic Rebound", "Liquidity Sweep"}


# ── contract applied end-to-end by the dispatcher ────────────────────────────

def _momentum_signal_df() -> pd.DataFrame:
    """30 bars: flat, then 2 consecutive up closes + volume spike on the last
    bar. Fires check_momentum_signal (streak>=2, VR>1.3). Kept under 100 bars
    so calc_weekly_trend soft-passes ('W:insufficient_data')."""
    n = 30
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = np.full(n, 1000.0)
    close[-2] = 1010.0
    close[-1] = 1025.0
    vol = np.full(n, 1_000_000.0)
    vol[-1] = 3_000_000.0
    df = pd.DataFrame({
        "date": dates, "open": close - 5, "high": close + 10,
        "low": close - 10, "close": close, "volume": vol,
    })
    # plan 1C: the checker now mirrors the backtest's watch-block proxy, which
    # requires close > typical price on a volume-elevated bar. Symmetric
    # high/low made typical == close (blocked); skew the last bar bullish.
    df.loc[n - 1, "high"] = 1030.0
    df.loc[n - 1, "low"] = 1012.0
    return df


def test_momentum_dispatch_result_carries_price():
    """Audit C-1 regression: momentum checker details had no 'price' key, so
    scanner's trade-open path skipped every momentum signal."""
    from engine.strategies import check_current_entry_signal
    df = _momentum_signal_df()
    res = check_current_entry_signal("TEST", "momentum", df=df)
    assert res["has_signal"] is True, res["reason"]
    assert res["details"]["price"] == pytest.approx(1025.0)


def test_unsupported_strategy_message_preserved():
    from engine.strategies import check_current_entry_signal
    df = _momentum_signal_df()
    res = check_current_entry_signal("TEST", "Nonexistent Strategy", df=df)
    assert res["has_signal"] is False
    assert "belum didukung" in res["reason"]


def test_dispatch_dict_exists_and_covers_known_checkers():
    from engine.strategies import _CHECKER_DISPATCH
    for name in ("vol_weighted", "momentum", "vwap_reversion", "conservative",
                 "Trend Following Breakout", "Crash Recovery", "Panic Rebound",
                 "Liquidity Sweep", "orb_intraday", "ORB_intraday"):
        assert name in _CHECKER_DISPATCH, name


# ── cross-map consistency (scanner ↔ specs ↔ dispatch) ───────────────────────

def test_regime_map_strategies_are_live_capable():
    """Every strategy the scanner can select MUST have a live checker.
    Audit C-1: Inside Bar Breakout / NR7 Breakout were selectable but had no
    checker at all, so they could signal nothing, silently."""
    from scheduler.scanner import _REGIME_STRATEGY_MAP
    from engine.strategy_specs import SPECS
    from engine.strategies import _CHECKER_DISPATCH
    for band, names in _REGIME_STRATEGY_MAP.items():
        for name in names:
            assert name in SPECS, f"{name} ({band}) not in SPECS"
            assert SPECS[name].live_checker, f"{name} ({band}) has no live checker"
            assert name in _CHECKER_DISPATCH, f"{name} ({band}) missing from dispatch"


def test_counter_trend_book_matches_specs():
    from scheduler.scanner import _COUNTER_TREND_BOOK
    from engine.strategy_specs import SPECS
    for name in _COUNTER_TREND_BOOK:
        assert SPECS[name].counter_trend, name


def test_live_checker_flag_matches_dispatch():
    from engine.strategies import _CHECKER_DISPATCH
    from engine.strategy_specs import SPECS
    for name, spec in SPECS.items():
        assert spec.live_checker == (name in _CHECKER_DISPATCH), name


def test_specs_match_strategy_funcs():
    from research.walkforward_multi import STRATEGY_FUNCS
    from engine.strategy_specs import SPECS
    assert set(STRATEGY_FUNCS) == set(SPECS)


def test_regime_adaptive_not_registered():
    """Audit C-7: strategy_regime_adaptive picks the regime from the LAST bar
    of the window and applies it to the whole window — look-ahead. It must not
    be a walk-forward research strategy until reimplemented per-bar."""
    from research.walkforward_multi import STRATEGY_FUNCS
    assert "Regime Adaptive" not in STRATEGY_FUNCS
