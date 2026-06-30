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
    # highest 100 -> stop 98.8. New high 103 -> stop ratchets to 103-1.2=101.8;
    # bar low 100.7 <= 101.8 -> trail hit at 101.8 (open 102 > stop -> level fill).
    d = evaluate_exit(view(pol, "LONG", highest=100, lowest=99), bar(102, 103, 100.7, 102.5))
    assert d.reason == "TRAIL"
    assert d.fill_price == 101.8


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
