"""Run: python -m pytest atr_plan/test_atr_exits.py -q   (or python atr_plan/test_atr_exits.py)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atr_exits import (Costs, ExitSpec, atr_position_size, cost_filter_ok,  # noqa: E402
                       round_down_tick, round_up_tick, simulate_trade, tick_size, wilder_atr)

C0 = Costs(0.0, 0.0)


def arr(*x):
    return np.array(x, dtype=float)


def run(o, h, l, c, spec, atr=100.0, i=1, entry=None, **kw):
    n = len(c)
    a = np.full(n, atr)
    hh = pd.Series(h).rolling(1).max().to_numpy()
    return simulate_trade(arr(*o), arr(*h), arr(*l), arr(*c), a, a, hh, i,
                          entry if entry is not None else o[i], spec, C0, **kw)


def test_ticks():
    assert tick_size(150) == 1 and tick_size(300) == 2 and tick_size(1500) == 5
    assert tick_size(3000) == 10 and tick_size(9000) == 25
    assert round_down_tick(1503) == 1500 and round_up_tick(1501) == 1505


def test_wilder_atr_constant_range():
    df = pd.DataFrame({"high": [110.0] * 30, "low": [100.0] * 30, "close": [105.0] * 30})
    assert abs(wilder_atr(df, 14).iloc[-1] - 10) < 1e-9


def test_gap_through_stop_fills_at_open():
    spec = ExitSpec("fixed", tp_pct=0.05, sl_pct=0.02)
    # entry 1000 @ bar1, stop 980; bar2 opens 950
    r = run([1000, 1000, 950], [1000, 1005, 960], [1000, 995, 940], [1000, 1000, 955], spec)
    assert r["reason"] == "gap_stop" and r["exit"] == 950


def test_same_bar_stop_first_vs_ohlc():
    spec = ExitSpec("fixed", tp_pct=0.02, sl_pct=0.02)
    # bar2 opens 1000, high 1030 (tp 1020), low 975 (stop 980); open nearer HIGH? o-l=25 < h-o=30 -> low first
    o, h, l, c = [1000, 1000, 1000], [1000, 1005, 1030], [1000, 995, 975], [1000, 1000, 1000]
    assert run(o, h, l, c, spec, same_bar="stop_first")["reason"] == "stop"
    assert run(o, h, l, c, spec, same_bar="ohlc")["reason"] == "stop"
    # now open near low: o-l=5? make low 978 with o=1000 -> 22 < 30 still low first; flip: high 1021
    o, h, l, c = [1000, 1000, 1000], [1000, 1005, 1021], [1000, 995, 975], [1000, 1000, 1000]
    assert run(o, h, l, c, spec, same_bar="ohlc")["reason"] == "tp"      # 21 < 25 -> high first
    assert run(o, h, l, c, spec, same_bar="stop_first")["reason"] == "stop"


def test_min_stop_three_ticks():
    spec = ExitSpec("fixed", tp_pct=0.5, sl_pct=0.001)     # 0.1% stop on Rp400 stock -> 3 ticks = Rp6
    r = run([400, 400, 400], [400, 400, 400], [400, 400, 393], [400, 400, 395], spec)
    assert r["stop0"] == 394


def test_time_stop():
    spec = ExitSpec("atr_tpsl", stop_k=1.5, tp_k=1.5, time_stop=3, max_hold=5)
    o = [1000] * 8
    r = run(o, [1010] * 8, [990] * 8, [1001] * 8, spec, atr=100)
    assert r["reason"] == "time" and r["bars"] == 3


def test_chandelier_exits_next_open():
    spec = ExitSpec("chandelier", stop_k=5.0, chand_k=1.0, max_hold=30)
    # atr 10; hh=high; bar3 high 1100 -> level 1090; bar3 close 1080 < 1090 -> exit bar4 open
    o = [1000, 1000, 1050, 1095, 1070]
    h = [1000, 1010, 1060, 1100, 1075]
    l = [1000, 995, 1045, 1075, 1060]
    c = [1000, 1005, 1055, 1080, 1065]
    r = run(o, h, l, c, spec, atr=10)
    assert r["reason"] == "trail" and r["exit_i"] == 4 and r["exit"] == 1070


def test_entry_bar_buy_stop_ohlc_ignores_prior_low():
    spec = ExitSpec("fixed", tp_pct=0.10, sl_pct=0.01)
    # entry via buy-stop at 1010 on bar1; bar1 low 990 printed before trigger (open 995 nearer low)
    o, h, l, c = [1000, 995, 1012], [1000, 1015, 1020], [1000, 990, 1005], [1000, 1012, 1015]
    assert run(o, h, l, c, spec, entry=1010, entry_mid=True, same_bar="ohlc")["reason"] != "stop"
    assert run(o, h, l, c, spec, entry=1010, entry_mid=True, same_bar="stop_first")["reason"] == "stop"


def test_sizing_and_cost_filter():
    assert atr_position_size(100e6, 1000, 950) == 15000          # 750k / 50 = 15,000 sh; cap 30,000
    assert atr_position_size(100e6, 1000, 999) == 30000          # capped at 30%
    assert atr_position_size(1e6, 9000, 8000) == 0               # 1 lot > cap
    assert cost_filter_ok(0.02) and not cost_filter_ok(0.01)


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("ok", k)
