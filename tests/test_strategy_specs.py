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
