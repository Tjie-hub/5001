"""PIT (point-in-time) and mechanics tests for the exit-study driver — G0 gate.

They read NO outcomes: synthetic panels and hand-built bar arrays only, no DB,
no real data, no census. Each test pins one predeclared claim from
PREDECLARATION.md:

  PIT — setups/levels use only bars up to the signal day (pivot confirmation
  lag, truncation identity); the entry state machine never reuses a locked
  stock; random controls are seeded and deterministic.
  MECHANICS — limit/stop/target fills with gap rules; the frozen same-day
  precedence (stop first); hold/time/MA20/trail exits; the position arms' leg
  rules; cost and R arithmetic; portfolio sizing/cap.

Run:  pytest docs/research_programs/P-M/exit_study/test_pit_exit_study.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import exit_study as E  # noqa: E402

SEED = 20261006


def bars(n, price=100.0, seed=1, vol=0.01):
    """Flat-ish OHLCV arrays with a small seeded wiggle."""
    rng = np.random.default_rng(seed)
    c = price * np.exp(np.cumsum(rng.normal(0, vol, n)))
    o = c * (1 + rng.normal(0, vol / 2, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    v = np.full(n, 2.0e8)
    return o, h, lo, c, v


def mk_panel(dict_of_arrays, n_days):
    """{field: {ticker: array}} -> pivots dict."""
    P = {}
    for field, cols in dict_of_arrays.items():
        P[field] = pd.DataFrame(cols, index=pd.bdate_range("2020-01-02", periods=n_days))
    return P


# ── pivot / group PIT (jurnal26 parity, G0-bis) ───────────────────────────────

def test_pivot_confirmed_only_after_five_sessions():
    """A pivot at bar i needs its 5 right-side bars (jurnal26 w=5): NOT visible
    at s < i+5; visible from s = i+5."""
    x = np.array([9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    flags = E.pivot_flags_1d(x)
    assert flags[6]                       # the V-bottom
    for s in range(6, 11):
        j_top = s - E.PIVOT_HALF
        visible = [i for i in np.where(flags)[0] if i <= j_top]
        assert 6 not in visible, f"pivot leaked at s={s}"
    s = 11
    assert 6 in [i for i in np.where(flags)[0] if i <= s - E.PIVOT_HALF]


def test_plateau_counts_once():
    x = np.array([9.0, 9.0, 9.0, 9.0, 9.0, 5.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    flags = E.pivot_flags_1d(x)
    assert flags[5] and not flags[6]      # first bar of the plateau only


def test_groups_pooled_sorted_chained_on_lowest_price():
    """jurnal26 _levels grouping: an ascending pool; a pivot joins the current
    group iff p <= group[0] * 1.04 (anchored on the group's LOWEST price — the
    chain does not slide), else it opens a new group."""
    g = E.groups_from_pivots([104.1, 100.0, 103.9, 108.0, 102.0])
    assert len(g) == 2
    assert g[0] == {"mean": (100.0 + 102.0 + 103.9) / 3, "count": 3,
                    "min": 100.0, "max": 103.9}
    # 104.1 > 100*1.04 opens a new group; 108.0 <= 104.1*1.04 joins it
    assert g[1] == {"mean": (104.1 + 108.0) / 2, "count": 2,
                    "min": 104.1, "max": 108.0}


def test_zone_context_pools_highs_and_lows_into_one_group():
    """A pivot high and a pivot low within 4% land in ONE pooled group (the
    old logic kept support and resistance zones apart)."""
    n = 40
    L = np.full(n, 100.0)
    H = np.full(n, 100.0)
    I = {"lo_idx": np.array([10]), "lo_vals": np.array([100.0]),
         "hi_idx": np.array([20]), "hi_vals": np.array([101.0])}
    groups = E.zone_context(L, H, I, 30)
    assert len(groups) == 1
    assert groups[0]["count"] == 2
    assert groups[0]["min"] == 100.0 and groups[0]["max"] == 101.0
    assert groups[0]["mean"] == pytest.approx(100.5)


def test_sniper_support_target_selection_matches_jurnal26(monkeypatch):
    """G0-bis selection: support = the highest-MEAN pooled group below the
    close (not the highest max); target = the MIN of the lowest-mean group
    above the close; a target at/below the zone top falls back to the 52-week
    high (jurnal26 watchlist._sniper)."""
    n = 300
    c = np.linspace(80.0, 120.0, n)
    o = np.concatenate([[c[0]], c[:-1]])
    h = o + 1.0
    lo = o - 1.0                      # TR = 2 exactly -> ATR14 = 2
    v = np.full(n, 2.0e8)
    I = E.stock_indicators(o, h, lo, c, v)
    k = 280
    last = float(c[k])
    assert I["atr14"][k] == pytest.approx(2.0)

    def groups_far(L_, H_, I_, k_):
        return [{"mean": last - 20.0, "count": 2, "min": last - 22.0, "max": last - 18.0},
                {"mean": last - 2.0,  "count": 2, "min": last - 3.0,  "max": last - 1.0},
                {"mean": last + 15.0, "count": 2, "min": last + 12.0, "max": last + 18.0}]

    monkeypatch.setattr(E, "zone_context", groups_far)
    sig = E.sniper_signal_at(k, o, h, lo, c, I)
    # support = the C-2 group (highest MEAN below), not the deeper C-20 group
    assert sig["zone_low"] == pytest.approx(last - 3.0)
    assert sig["zone_top"] == pytest.approx(last - 1.0)   # min(max(zmax, zlow+ATR), C)
    assert sig["stop"] == pytest.approx(last - 3.0 - 1.5)
    assert sig["target"] == pytest.approx(last + 12.0)    # min of the lowest-mean above group

    # degenerate: the above group's MIN sits at/below the zone top -> 52-week high
    def groups_low(L_, H_, I_, k_):
        return [{"mean": last - 2.0,  "count": 2, "min": last - 3.0, "max": last - 1.0},
                {"mean": last + 15.0, "count": 2, "min": last - 2.0, "max": last + 18.0}]

    monkeypatch.setattr(E, "zone_context", groups_low)
    sig = E.sniper_signal_at(k, o, h, lo, c, I)
    assert sig["target"] == pytest.approx(I["hi250"][k])

    # nothing above the close -> the 52-week high
    def groups_none(L_, H_, I_, k_):
        return [{"mean": last - 2.0, "count": 2, "min": last - 3.0, "max": last - 1.0}]

    monkeypatch.setattr(E, "zone_context", groups_none)
    sig = E.sniper_signal_at(k, o, h, lo, c, I)
    assert sig["target"] == pytest.approx(I["hi250"][k])


def test_sniper_signal_truncation_identity():
    """Setups at day k are identical (or both None) on full vs truncated bars."""
    n = 420
    rng = np.random.default_rng(7)
    drift = np.concatenate([np.full(200, -0.004), np.full(n - 200, 0.003)])
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.02)))
    o = c * (1 + rng.normal(0, 0.005, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.008, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.008, n)))
    v = np.full(n, 5.0e8)
    I_full = E.stock_indicators(o, h, lo, c, v)
    checked = 0
    for k in range(300, n - 3):
        sig_full = E.sniper_signal_at(k, o, h, lo, c, I_full)
        I_tr = E.stock_indicators(o[:k + 1], h[:k + 1], lo[:k + 1], c[:k + 1], v[:k + 1])
        sig_tr = E.sniper_signal_at(k, o[:k + 1], h[:k + 1], lo[:k + 1], c[:k + 1], I_tr)
        if sig_full is None:
            assert sig_tr is None, k
        else:
            assert sig_tr is not None, k
            for key in ("zone_low", "zone_top", "stop", "target", "atr"):
                assert sig_full[key] == pytest.approx(sig_tr[key], rel=1e-12, abs=1e-12), (k, key)
            checked += 1
    assert checked >= 3, "fixture produced no setups; test is vacuous"


# ── fill mechanics ────────────────────────────────────────────────────────────

def test_fill_limit_at_order_and_gap_at_open():
    L = np.array([101.0, 99.5, 98.0])
    O = np.array([102.0, 100.5, 97.0])
    assert E.fill_limit(L, O, 100.0, 0, 2) == (1, 100.0)   # touched: at the order
    assert E.fill_limit(L, O, 99.0, 0, 2) == (2, 97.0)     # gapped through: at the open
    assert E.fill_limit(L, O, 95.0, 0, 2) is None          # never reached
    assert E.fill_limit(L, O, 98.5, 1, 1) is None          # window excludes day 2
    assert E.fill_limit(L, O, 98.5, 1, 2) == (2, 97.0)     # ...and fills on day 2


def test_stop_gap_fills_at_open_and_stop_first_precedence():
    # hand-built trade: entry 100 at t1=3, stop 90, target 110, ATR 5
    n = 30
    o, h, lo, c, v = bars(n, seed=3)
    o[:] = 100.0; h[:] = 100.0; lo[:] = 100.0; c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 110.0, "atr": 5.0, "month": "2020-01"}
    # day 4 gaps through BOTH stop and target -> stop first, at the open
    o[4], h[4], lo[4], c[4] = 112.0, 113.0, 85.0, 86.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X1", P, {})
    assert oc["reason"] == "stop" and oc["exit_idx"] == 4 and oc["exit_px"] == 90.0


def test_stop_intraday_at_stop_price():
    n = 30
    o, h, lo, c, v = bars(n, seed=4)
    o[:] = 100.0; h[:] = 100.0; lo[:] = 100.0; c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 110.0, "atr": 5.0, "month": "2020-01"}
    o[5], h[5], lo[5], c[5] = 100.0, 101.0, 89.0, 95.0   # low pierces 90, open above
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X1", P, {})
    assert oc["reason"] == "stop" and oc["exit_px"] == 90.0


def test_target_fills_at_limit_and_gap_up_at_open():
    n = 30
    o, h, lo, c, v = bars(n, seed=5)
    o[:] = 100.0; h[:] = 100.0; lo[:] = 100.0; c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 110.0, "atr": 5.0, "month": "2020-01"}
    h[4], o[4], c[4], lo[4] = 110.5, 109.0, 110.0, 108.0   # touch 110 -> at the limit
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X1", P, {})
    assert oc["reason"] == "target" and oc["exit_px"] == 110.0
    h[4], o[4], c[4], lo[4] = 115.0, 114.0, 114.5, 113.0   # gap through -> at the open
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X1", P, {})
    assert oc["reason"] == "target" and oc["exit_px"] == 114.0


def test_x0_holds_exactly_20_sessions():
    n = 40
    o, h, lo, c, v = bars(n, seed=6)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 200.0, "atr": 5.0, "month": "2020-01"}
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X0", P, {})
    assert oc["hold"] == 20 and oc["reason"] == "hold20" and oc["exit_idx"] == 23


def test_x5_time_stop_at_session_10():
    n = 40
    o, h, lo, c, v = bars(n, seed=7)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 200.0, "atr": 5.0, "month": "2020-01"}
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X5", P, {})
    assert oc["reason"] == "time10" and oc["exit_idx"] == 13   # 3 + 10, flat close 100 < 105
    # profitable case: close >= entry + 1 ATR at session 10 -> continues as X1
    o[:] = h[:] = lo[:] = c[:] = 100.0
    c[13] = o[13] = h[13] = lo[13] = 106.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X5", P, {})
    assert oc["reason"] == "max60" or oc["reason"] == "eos"


def test_x4_exits_on_first_close_below_ma20():
    n = 60
    o, h, lo, c, v = bars(n, seed=8)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 96.0, "stop": 90.0, "target": 200.0, "atr": 5.0, "month": "2020-01"}
    c[20] = 94.0; o[20] = 99.0; h[20] = 99.5; lo[20] = 93.5   # first close < MA20 (100)
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X4", P, {})
    assert oc["reason"] == "ma20" and oc["exit_idx"] == 20 and oc["exit_px"] == 94.0


def test_x3_chandelier_trail_uses_prior_closes():
    n = 40
    o, h, lo, c, v = bars(n, seed=9)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    tr = {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
          "zone_low": 90.0, "stop": 86.25, "target": 500.0, "atr": 5.0, "month": "2020-01"}
    # run up to close 120 by day 10 -> trail = 120-15 = 105; day 11 low 104 stops
    for k in range(4, 11):
        c[k] = o[k] = h[k] = lo[k] = 100.0 + 3.0 * (k - 3)
    o[11], h[11], lo[11], c[11] = 106.0, 107.0, 104.0, 105.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X3", P, {})
    assert oc["reason"] == "stop" and oc["exit_idx"] == 11
    assert oc["exit_px"] == pytest.approx(106.0)   # trail 121-15, gap-fill at open


# ── position arms ─────────────────────────────────────────────────────────────

def _flat_trade(target=200.0, zone_low=96.0, stop=90.0):
    return {"ticker": "T", "s": 2, "t1": 3, "entry": 100.0, "zone_top": 100.0,
            "zone_low": zone_low, "stop": stop, "target": target, "atr": 5.0,
            "month": "2020-01"}


def test_p1_second_half_fills_at_zone_low():
    n = 30
    o, h, lo, c, v = bars(n, seed=10)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    lo[5] = 96.0; c[5] = 99.0; o[5] = 99.5; h[5] = 100.0     # touches zone low
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(_flat_trade(), "P1", P, {})
    assert oc["n_legs"] == 3                                  # 2 buys + final sell
    assert oc["buy_notional"] == pytest.approx(100.0 * 0.5 + 96.0 * 0.5)


def test_p2_average_down_adds_half_at_entry_minus_1atr():
    n = 30
    o, h, lo, c, v = bars(n, seed=11)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    lo[5] = 94.5; o[5] = 95.5; c[5] = 99.0; h[5] = 100.0      # touches 95 = entry-1ATR
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(_flat_trade(), "P2", P, {})
    assert oc["n_legs"] == 3
    assert oc["buy_notional"] == pytest.approx(100.0 + 95.0 * 0.5)


def test_p3_pyramid_adds_on_close_at_entry_plus_1atr():
    n = 30
    o, h, lo, c, v = bars(n, seed=12)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    c[4] = 105.5; o[4] = 101.0; h[4] = 106.0; lo[4] = 100.5   # first close >= 105
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(_flat_trade(), "P3", P, {})
    assert oc["n_legs"] == 3
    assert oc["buy_notional"] == pytest.approx(100.0 + 105.5 * 0.5)


def test_p4_swing_lot_topup_and_own_target():
    n = 40
    o, h, lo, c, v = bars(n, seed=13)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    c[4] = 105.5; o[4] = 101.0; h[4] = 106.0; lo[4] = 100.5   # arm on day-4 close
    lo[6] = 97.5; o[6] = 99.0; h[6] = 100.0; c[6] = 99.5      # top-up fills at 97.5 (entry-0.5ATR)
    h[8] = 105.5; o[8] = 100.0; c[8] = 105.0; lo[8] = 100.0   # top-up sells at 97.5+7.5=105.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(_flat_trade(), "P4", P, {})
    assert oc["n_legs"] == 4                                  # core buy, top-up buy+sell, core sell
    assert oc["buy_notional"] == pytest.approx(100.0 + 97.5 * 0.5)


# ── cost / R arithmetic ───────────────────────────────────────────────────────

def test_cost_and_r_arithmetic_hand_computed():
    n = 30
    o, h, lo, c, v = bars(n, seed=14)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    h[4] = 110.5; o[4] = 100.0; c[4] = 110.0; lo[4] = 100.0   # target 110 at the limit
    tr = _flat_trade(target=110.0)
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    oc = E.simulate_trade(tr, "X1", P, {})
    gross = 110.0 - 100.0
    costs = (E.COST_BUY + E.SLIP_RT) * 100.0 + E.COST_SELL * 110.0
    net = gross - costs
    assert oc["net"] == pytest.approx(net)
    assert oc["net_pct"] == pytest.approx(net / 100.0)
    assert oc["R"] == pytest.approx(net / 10.0)               # init risk (100-90)*1


# ── entry state machine ───────────────────────────────────────────────────────

def test_entry_machine_supersede_and_lock(monkeypatch):
    """A newer setup supersedes a pending unfilled order; a fill locks the stock
    for MAX_HOLD; setups while locked are never tradable."""
    n = 520
    o, h, lo, c, v = bars(n, seed=15)
    o[:] = h[:] = lo[:] = c[:] = 101.0          # above the 100 limit: no accidental fills
    lo[266] = 99.0; o[266] = 99.5               # day 266: fills the pending
    lo[466] = 99.0; o[466] = 99.5               # day 466: fills the later pending
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    sig = {"zone_low": 96.0, "zone_top": 100.0, "stop": 90.0, "target": 120.0,
           "atr": 5.0}
    seq = {260: dict(sig), 264: dict(sig), 305: dict(sig), 310: dict(sig), 460: dict(sig)}

    def fake_signal(k, O, H, L, C, I):
        return dict(sig) if k in seq else None

    monkeypatch.setattr(E, "sniper_signal_at", fake_signal)
    uni = pd.DataFrame(True, index=P["close"].index, columns=["T"])
    I_by_stock = {"T": E.stock_indicators(o, h, lo, c, v)}
    pop = E.entry_population(P, I_by_stock, uni)
    events = [e["kind"] for e in pop["events"]]
    # setup@260 superseded by setup@264; @264 fills day 266 -> lock to 326;
    # @305/@310 while locked; @460 pending fills day 466.
    assert events.count("setup") == 5
    assert events.count("superseded") == 1
    assert events.count("setup_while_locked") == 2            # @305, @310 (lock to 326)
    assert events.count("fill") == 2
    assert len(pop["sniper"]) == 2
    assert [t["t1"] for t in pop["sniper"]] == [266, 466]


def test_random_controls_seeded_and_matched():
    n = 400
    o, h, lo, c, v = bars(n, seed=16)
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = E.stock_indicators(o, h, lo, c, v)
    snipes = [{"ticker": "T", "s": 50, "t1": 51, "entry": 100.0, "zone_top": 100.0,
               "zone_low": 96.0, "stop": 90.0, "target": 115.0, "atr": 5.0,
               "month": "2020-03"}]
    r1, u1 = E.random_controls(P, {"T": I}, snipes, np.random.default_rng(SEED))
    r2, u2 = E.random_controls(P, {"T": I}, snipes, np.random.default_rng(SEED))
    assert u1 == 0 and len(r1) == 1
    assert r1[0]["s"] == r2[0]["s"]                       # seeded: identical picks
    assert E.month_to_era(r1[0]["month"]) == E.month_to_era("2020-03")
    assert r1[0]["t1"] == r1[0]["s"] + 1                  # next-open entry
    d_stop = (100.0 - 90.0) / 5.0
    d_tgt = (115.0 - 100.0) / 5.0
    assert r1[0]["stop"] == pytest.approx(r1[0]["entry"] - d_stop * r1[0]["atr"])
    assert r1[0]["target"] == pytest.approx(r1[0]["entry"] + d_tgt * r1[0]["atr"])
    # no liquid day available -> unmatched
    I_dry = dict(I)
    I_dry["adv20"] = np.zeros(n)
    r3, u3 = E.random_controls(P, {"T": I_dry}, snipes, np.random.default_rng(SEED))
    assert r3 == [] and u3 == 1


def test_month_to_era_split():
    assert E.month_to_era("2021-09") == "E1"
    assert E.month_to_era("2021-10") == "E2"
    assert E.month_to_era("2001-01") == "E1"


# ── portfolio + G1 assembly smoke (synthetic only) ────────────────────────────

def test_portfolio_sizing_cap_and_outputs():
    n = 300
    o, h, lo, c, v = bars(n, seed=17)
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    dates = P["close"].index
    trades = [{"ticker": "T", "s": 30 + 5 * i, "t1": 31 + 5 * i, "entry": 100.0,
               "zone_top": 100.0, "zone_low": 96.0, "stop": 90.0, "target": 110.0,
               "atr": 5.0, "month": str(dates[30 + 5 * i])[:7]}
              for i in range(20) if 31 + 5 * i < n - 25]
    Ic = {}
    outcomes = E.run_arm(trades, "X1", P, Ic)
    pf = E.assemble_portfolio(outcomes, trades, dates, lambda tk: P["close"]["T"].values)
    assert set(pf) >= {"cagr", "max_dd", "worst_12m", "n_taken", "final_equity"}
    assert pf["n_signals"] == len(trades)
    assert 0 < pf["n_taken"] <= len(trades)
    assert pf["max_dd"] <= 0.0 and pf["final_equity"] > 0


def test_g1_gate_refuses_without_approval():
    with pytest.raises(SystemExit):
        E.run_g1()


def test_evaluate_smoke_on_synthetic_panel():
    """The frozen G1 assembly runs end-to-end on a synthetic two-stock panel
    (no real outcomes, nothing written)."""
    n = 700
    rng = np.random.default_rng(21)
    fields = {}
    for tk in ("AAA", "BBB"):
        drift = np.concatenate([np.full(300, -0.003), np.full(n - 300, 0.002)])
        c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.02)))
        o = c * (1 + rng.normal(0, 0.005, n))
        h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.008, n)))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.008, n)))
        v = np.full(n, 2.0e8)
        fields.setdefault("open", {})[tk] = o
        fields.setdefault("high", {})[tk] = h
        fields.setdefault("low", {})[tk] = lo
        fields.setdefault("close", {})[tk] = c
        fields.setdefault("volume", {})[tk] = v
    P = mk_panel(fields, n)
    I_by_stock = {tk: E.stock_indicators(
        fields["open"][tk], fields["high"][tk], fields["low"][tk],
        fields["close"][tk], fields["volume"][tk]) for tk in ("AAA", "BBB")}
    universes = {"owner_adv20_10bn": pd.DataFrame(True, index=P["close"].index,
                                                  columns=["AAA", "BBB"])}
    result = E.evaluate(P, I_by_stock, universes)
    assert set(result["arms"]) == {"E_SN", "E_RND", "E_BRK"}
    for era in ("E1", "E2"):
        assert set(result["arms"]["E_SN"][era]["metrics"]) >= set(E.EXIT_ARMS)
        assert set(result["arms"]["E_SN"][era]["portfolio"]) >= set(E.POS_ARMS)
    assert "P2" in result["p2_tail"]["E_SN"]
