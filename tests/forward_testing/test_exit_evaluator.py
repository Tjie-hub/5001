"""ExitEvaluator: direction-aware SL/TP/trail/time, deterministic order, gap fills, metrics."""
from forward_testing.positions.exit_evaluator import PositionView, Bar, evaluate_exit
from forward_testing.positions.exit_policy import ExitPolicy

LONG_FIXED = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)        # sl=99, tp=102 @ entry 100, atr 1
SHORT_TRAIL = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)  # 3xATR trail


def view(policy, direction, entry=100.0, atr=1.0, highest=100.0, lowest=100.0, hold=1):
    return PositionView(policy=policy, direction=direction, entry=entry, atr=atr,
                        highest_seen=highest, lowest_seen=lowest, hold_days=hold)


def bar(o, h, l, c, date="2026-06-27"):
    return Bar(date=date, open=o, high=h, low=l, close=c)


# ---- LONG fixed SL/TP ----

def test_long_stop_hit_level_fill():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 100.5, 98.5, 99))
    assert d.reason == "SL"
    assert d.fill_price == 99.0                  # low breached 99, open 100 > 99 -> level fill
    assert d.r_multiple == -1.0                  # (99-100)/1
    assert d.pnl_pct == -0.01


def test_long_tp_hit_level_fill():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 102.5, 99.9, 102))
    assert d.reason == "TP"
    assert d.fill_price == 102.0
    assert d.r_multiple == 2.0
    assert d.pnl_pct == 0.02


def test_long_stop_beats_tp_on_conflict_bar():
    # both SL (low<=99) and TP (high>=102) touched -> SL first
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 103, 98, 99))
    assert d.reason == "SL"
    assert d.fill_price == 99.0


def test_long_gap_below_stop_fills_at_open():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(97, 97.5, 96, 96.5))  # opens below SL
    assert d.reason == "SL"
    assert d.fill_price == 97.0                  # gap fill at open


def test_long_no_exit_returns_none():
    d = evaluate_exit(view(LONG_FIXED, "LONG", highest=100, lowest=100),
                      bar(100, 101, 99.5, 100.5))
    assert d is None                             # low 99.5 > sl 99; high 101 < tp 102


def test_long_mae_mfe_signed():
    d = evaluate_exit(view(LONG_FIXED, "LONG"), bar(100, 103, 98, 102))   # SL also hit
    assert d.mae_pct == -0.02                    # (98-100)/100
    assert d.mfe_pct == 0.03                     # (103-100)/100


# ---- LONG trailing (momentum-style: sl_mult + trail_enable) ----

def test_long_trail_ratchets_then_hits():
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    # The ratchet from a new high applies on the NEXT bar, not the bar that made
    # the high (no intrabar look-ahead -- see C3 tests below).
    # Bar 1: highest_seen 100 -> stop 98.8; high 102.3 stays under the 102.4 TP and
    # low 101.5 stays above 98.8 -> hold. The manager would advance highest_seen to 102.3.
    d = evaluate_exit(view(pol, "LONG", highest=100, lowest=99), bar(101, 102.3, 101.5, 102))
    assert d is None
    # Bar 2: highest_seen now 102.3 -> stop 102.3-1.2=101.1; bar low 101.0 <= 101.1
    # -> TRAIL at 101.1 (open 102 > stop -> level fill; high 102.2 < TP).
    d = evaluate_exit(view(pol, "LONG", highest=102.3, lowest=99), bar(102, 102.2, 101.0, 101.5))
    assert d.reason == "TRAIL"
    assert round(d.fill_price, 4) == 101.1


def test_long_trail_holds_when_low_above_ratcheted_stop():
    pol = ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True)
    # highest 100 -> stop 98.8. New high 101 -> stop 99.8; low 100 > 99.8 -> hold.
    d = evaluate_exit(view(pol, "LONG", highest=100, lowest=99), bar(100, 101, 100, 100.5))
    assert d is None


# ---- SHORT pure trail (distribution DEFAULT) ----

def test_short_trail_ratchets_down_then_hits():
    # entry 100, trail 3 -> stop starts 103. bar1 low 97 -> new lowest 97 -> stop 100; high 99<100 hold.
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=100),
                      bar(100, 99, 97, 98))
    assert d is None
    # next: lowest 97 -> stop 100; bar high 100.5 >= 100 -> TRAIL at 100 (level; open 99<100)
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=97),
                      bar(99, 100.5, 99, 100))
    assert d.reason == "TRAIL"
    assert d.fill_price == 100.0
    assert d.r_multiple == 0.0                   # (100-100)/3


def test_short_pure_trail_favourable_move_holds():
    # favourable (low 97 -> stop 100) but high 99.5 < stop -> holds; pure trail has no TP.
    d = evaluate_exit(view(SHORT_TRAIL, "SHORT", highest=100, lowest=100),
                      bar(99, 99.5, 97, 98))
    assert d is None


def test_short_fixed_stop_gap_fills_at_open():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0)   # short: sl=101, tp=98
    d = evaluate_exit(view(pol, "SHORT"), bar(103, 104, 102.5, 103))  # opens above SL 101
    assert d.reason == "SL"
    assert d.fill_price == 103.0                 # gap fill at open


# ---- C3: intrabar trailing-stop look-ahead bias ----
# A trailing stop must be set from the extreme established BEFORE this bar opened.
# It must never ratchet to THIS bar's high and then be triggered by THIS bar's low,
# because there is no guarantee the high printed before the low. Doing so fabricates
# exits at inflated levels and biases trailing-stop P&L upward.

def test_long_trail_does_not_use_current_bar_high_to_trigger_same_bar_low():
    # entry 100, atr 10, trail 3x -> stop entering the bar = highest_seen(100) - 30 = 70.
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    v = view(pol, "LONG", entry=100.0, atr=10.0, highest=100.0, lowest=100.0)
    # Bar rallies to 160 then dips to 125. Low 125 never reaches the 70 stop that
    # existed at bar open, so the position must HOLD. The buggy code ratchets the
    # stop to 160-30=130 using this bar's high, then triggers it on this bar's low
    # (125 <= 130) and reports a fabricated TRAIL exit at 130 (+30%).
    d = evaluate_exit(v, bar(140, 160, 125, 130))
    assert d is None, (
        f"intrabar look-ahead: stop trailed to this bar's high and fired on the "
        f"same bar's low -> {d}"
    )


def test_short_trail_does_not_use_current_bar_low_to_trigger_same_bar_high():
    # Mirror image for SHORT. entry 100, atr 10, trail 3x -> stop entering bar = 130.
    pol = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)
    v = view(pol, "SHORT", entry=100.0, atr=10.0, highest=100.0, lowest=100.0)
    # Drops to 40 then rebounds to 75. High 75 never reaches the 130 stop at bar open
    # -> must HOLD. Buggy code ratchets stop to 40+30=70 on this bar's low, then fires
    # on this bar's high (75 >= 70).
    d = evaluate_exit(v, bar(60, 75, 40, 70))
    assert d is None, (
        f"intrabar look-ahead (short): stop trailed to this bar's low and fired on "
        f"the same bar's high -> {d}"
    )


# ---- TIME stop ----

def test_time_stop_exits_at_close_when_hold_reached():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0, hold_days=5)
    d = evaluate_exit(view(pol, "LONG", hold=5), bar(100, 100.5, 99.8, 100.2))
    assert d.reason == "TIME"
    assert d.fill_price == 100.2                 # time exits at close


def test_stop_takes_precedence_over_time_on_same_bar():
    pol = ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0, hold_days=1)
    d = evaluate_exit(view(pol, "LONG", hold=1), bar(100, 100.5, 98.5, 99))   # SL also hit
    assert d.reason == "SL"
