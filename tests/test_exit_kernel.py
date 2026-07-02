"""engine/exits kernel extensions (plan 1B Task 3).

- Absolute per-position level overrides (fixed-level strategies: Crash
  Recovery, VWMA-BP, POC, InsideBar, NR7, ORB).
- no_sl policies (Panic Rebound: stops + mean reversion realize entry noise
  as losses; risk is bounded by the TIME stop).
- Trailing policies IGNORE the sl_price override (trail state lives in the
  extremes; the stored sl is display/record only).
"""
from engine.exits import ExitPolicy, PositionView, Bar, evaluate_exit


def _bar(o, h, l, c, date="2026-07-01"):
    return Bar(date=date, open=o, high=h, low=l, close=c)


def _view(policy, entry=1000.0, atr=20.0, highest=None, lowest=None,
          hold=0, sl=None, tp=None):
    return PositionView(
        policy=policy, direction="LONG", entry=entry, atr=atr,
        highest_seen=highest if highest is not None else entry,
        lowest_seen=lowest if lowest is not None else entry,
        hold_days=hold, sl_price=sl, tp_price=tp,
    )


def test_absolute_sl_override_wins_over_atr_levels():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0)          # ATR stop would be 980
    v = _view(pol, sl=950.0)
    assert evaluate_exit(v, _bar(1000, 1005, 979, 990)) is None   # 979 > 950: no exit
    d = evaluate_exit(v, _bar(1000, 1005, 949, 990))
    assert d.reason == "SL" and d.fill_price == 950.0


def test_absolute_tp_override_wins_over_atr_levels():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0)          # ATR TP would be 1040
    v = _view(pol, tp=1100.0)
    assert evaluate_exit(v, _bar(1000, 1050, 995, 1045)) is None  # 1050 < 1100
    d = evaluate_exit(v, _bar(1000, 1105, 995, 1090))
    assert d.reason == "TP" and d.fill_price == 1100.0


def test_no_sl_policy_never_price_stops():
    pol = ExitPolicy(no_sl=True, tp_mult=1.5, hold_days=5)
    v = _view(pol, sl=990.0)                            # override present but ignored
    assert evaluate_exit(v, _bar(1000, 1005, 700, 750)) is None   # 30% crash: hold


def test_no_sl_time_stop_still_fires():
    pol = ExitPolicy(no_sl=True, tp_mult=1.5, hold_days=5)
    v = _view(pol, hold=5)
    d = evaluate_exit(v, _bar(1000, 1005, 995, 998))
    assert d.reason == "TIME" and d.fill_price == 998


def test_no_sl_tp_fires_at_override_level():
    pol = ExitPolicy(no_sl=True, tp_mult=1.5, hold_days=5)
    v = _view(pol, tp=1030.0)
    d = evaluate_exit(v, _bar(1000, 1035, 995, 1020))
    assert d.reason == "TP" and d.fill_price == 1030.0


def test_trailing_policy_ignores_sl_override():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0)
    # prior extreme 1100, atr 20 -> trail stop = 1040; override 900 must NOT weaken it
    v = _view(pol, highest=1100.0, sl=900.0)
    d = evaluate_exit(v, _bar(1050, 1060, 1035, 1055))
    assert d is not None and d.reason == "TRAIL" and d.fill_price == 1040.0


def test_no_sl_initial_levels_have_no_stop():
    pol = ExitPolicy(no_sl=True, tp_mult=1.5, hold_days=5)
    lv = pol.initial_levels("LONG", 1000.0, 20.0)
    assert lv.sl_price is None and lv.initial_stop is None
    assert lv.tp_price == 1030.0          # entry + 1.5*atr
    assert lv.one_r == 30.0               # tp_mult*atr as the risk unit


def test_policy_metadata_fields_exist():
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, ma_break_period=20)
    assert pol.ma_break_period == 20
    assert ExitPolicy(fixed_levels=True, sl_mult=1.0, tp_mult=2.0).fixed_levels
    assert ExitPolicy(rule_based=True).rule_based


def test_registry_covers_every_spec_strategy_explicitly():
    """Audit finding: only 5 of 14 strategies had policies; TFB / Crash
    Recovery / Panic Rebound / 'distribution' silently got DEFAULT."""
    from engine.exits.policy import ExitPolicyRegistry
    from engine.strategy_specs import SPECS
    reg = ExitPolicyRegistry()
    for name in SPECS:
        assert name in reg._by_strategy, f"{name} falls back to DEFAULT"
    assert "distribution" in reg._by_strategy   # dominant ft SHORT book


def test_registry_key_policies_match_backtests():
    from engine.exits import get_policy
    tfb = get_policy("Trend Following Breakout")
    assert tfb.trail_atr_mult == 3.0 and tfb.ma_break_period == 20 and tfb.hold_days is None
    panic = get_policy("Panic Rebound")
    assert panic.no_sl and panic.hold_days == 5
    swing = get_policy("Swing Trend")
    assert swing.rule_based
    crash = get_policy("Crash Recovery")
    assert crash.fixed_levels
    # display-name alias resolves
    assert get_policy("Momentum Following").trail_enable
