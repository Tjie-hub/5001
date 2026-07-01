"""ExitPolicy registry: per-strategy configs, DEFAULT fallback, initial-level math."""
import math
from forward_testing.positions.exit_policy import ExitPolicy, ExitPolicyRegistry


def test_registry_returns_named_strategies_with_real_params():
    reg = ExitPolicyRegistry()
    assert reg.get("vol_weighted") == ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    assert reg.get("momentum") == ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    assert reg.get("vwap_reversion") == ExitPolicy(sl_mult=0.8, tp_mult=1.6, min_rr=2.0)
    assert reg.get("conservative") == ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0)
    assert reg.get("Liquidity Sweep") == ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5)


def test_registry_default_for_distribution_and_unknown():
    reg = ExitPolicyRegistry()
    expected = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    assert reg.get("distribution") == expected
    assert reg.get("something_unknown") == expected


def test_initial_levels_long_fixed_sl_tp():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.sl_price == 99.0
    assert lv.tp_price == 102.0
    assert lv.one_r == 1.0
    assert lv.trailing is False
    assert lv.initial_stop == 99.0


def test_initial_levels_min_rr_clamps_tp_outward():
    # sl_mult=0.7 -> R=0.7; tp_mult=1.4 -> 0.98 < min_rr*R=1.4 -> tp clamped to entry+1.4
    pol = ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert math.isclose(lv.tp_price, 101.4)
    assert lv.sl_price == 99.3


def test_initial_levels_short_mirrors_signs():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)
    lv = pol.initial_levels("SHORT", entry=100.0, atr=1.0)
    assert lv.sl_price == 101.0          # SL above entry for a short
    assert lv.tp_price == 98.0           # TP below entry
    assert lv.initial_stop == 101.0


def test_initial_levels_pure_trail_long():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.sl_price is None and lv.tp_price is None
    assert lv.one_r == 3.0
    assert lv.trailing is True
    assert lv.trail_mult == 3.0
    assert lv.initial_stop == 97.0       # 100 - 3*1


def test_initial_levels_pure_trail_short():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    lv = pol.initial_levels("SHORT", entry=100.0, atr=1.0)
    assert lv.initial_stop == 103.0      # 100 + 3*1


def test_trail_enable_with_fixed_sl_uses_sl_mult_as_trail_distance():
    # momentum: sl_mult=1.2 + trail_enable -> trailing stop distance = 1.2 ATR
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    lv = pol.initial_levels("LONG", entry=100.0, atr=1.0)
    assert lv.trailing is True
    assert lv.trail_mult == 1.2
    assert lv.initial_stop == 98.8
    assert lv.tp_price == 102.4
