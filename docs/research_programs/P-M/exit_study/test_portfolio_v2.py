"""Tests for the G1-bis portfolio layer (PORTFOLIO_FIX.md, 2026-10-07).

Covers: the parity gate (canonical legs vs the frozen simulate_trade, net_pct
within 1e-9 plus exit anchors), cash never negative, the 20% entry and 30% add
caps, P1–P4 leg sizing, and the skip rules. Synthetic data only; no DB.

Run:  pytest docs/research_programs/P-M/exit_study/test_portfolio_v2.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import exit_study as E                    # noqa: E402  (frozen driver)
import portfolio_v2 as PV                 # noqa: E402

ARMS = ["X0", "X1", "X2", "X3", "X4", "X5", "X6", "P0", "P1", "P2", "P3", "P4"]


def bars(n, price=100.0, seed=1, vol=0.01):
    rng = np.random.default_rng(seed)
    c = price * np.exp(np.cumsum(rng.normal(0, vol, n)))
    o = c * (1 + rng.normal(0, vol / 2, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    v = np.full(n, 2.0e8)
    return o, h, lo, c, v


def mk_panel(fields, n_days, start="2020-01-02"):
    P = {}
    for field, cols in fields.items():
        P[field] = pd.DataFrame(cols, index=pd.bdate_range(start, periods=n_days))
    return P


def _trade(tk, s, t1, entry, zone_low=96.0, stop=90.0, target=130.0, atr=5.0,
           month="2020-02"):
    return {"ticker": tk, "s": s, "t1": t1, "entry": entry, "zone_top": entry,
            "zone_low": zone_low, "stop": stop, "target": target, "atr": atr,
            "month": month}


# ── parity: canonical legs vs the frozen simulation ──────────────────────────

def test_parity_legs_vs_frozen_all_arms():
    """For hand-built trades across every arm, the reconstructed legs imply
    the same net % as the frozen simulate_trade (<= 1e-9) and the same exit
    day/reason."""
    n = 200
    o, h, lo, c, v = bars(n, seed=42, vol=0.015)
    # a rich price path: run-up, sharp drawdown, recovery, late rally
    c[:] = 100.0
    o[:] = 100.0
    h[:] = 101.0
    lo[:] = 99.0
    for k in range(60, 90):                 # run-up
        c[k] = o[k] = 100.0 + 1.2 * (k - 60)
        h[k], lo[k] = c[k] + 0.8, c[k] - 0.8
    for k in range(90, 110):                # drawdown to below the zone
        c[k] = o[k] = 172.0 - 1.5 * (k - 90)
        h[k], lo[k] = c[k] + 1.2, c[k] - 1.5
    for k in range(110, 140):               # recovery
        c[k] = o[k] = 142.0 + 0.9 * (k - 110)
        h[k], lo[k] = c[k] + 0.7, c[k] - 0.9
    c[150] = o[150] = 180.0                 # late spike
    h[150], lo[150] = 182.0, 178.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    trades = [
        _trade("T", 50, 51, o[51], zone_low=95.0, stop=90.0, target=150.0, atr=5.0),
        _trade("T", 100, 101, o[101], zone_low=140.0, stop=135.0, target=175.0, atr=5.0),
        _trade("T", 130, 131, o[131], zone_low=150.0, stop=145.0, target=190.0, atr=5.0),
    ]
    checked = 0
    for tr in trades:
        for arm in ARMS:
            oc = E.simulate_trade(tr, arm, P, I)
            lg = PV.simulate_legs(tr, arm, P, I)
            assert lg["exit_idx"] == oc["exit_idx"], (tr["s"], arm, "exit_idx")
            assert lg["exit_reason"] == oc["reason"], (tr["s"], arm, "reason")
            diff = abs(lg["net_pct"] - oc["net_pct"])
            assert diff <= 1e-9, (tr["s"], arm, diff)
            checked += 1
    assert checked == 36


def test_parity_legs_vs_frozen_population_trades():
    """Parity also on sniper trades produced by the frozen entry machinery on
    a synthetic uptrend-with-pullbacks panel (integration)."""
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
        for f, arr in zip(("open", "high", "low", "close", "volume"),
                          (o, h, lo, c, v)):
            fields.setdefault(f, {})[tk] = arr
    P = mk_panel(fields, n)
    I_by = {tk: E.stock_indicators(fields["open"][tk], fields["high"][tk],
                                   fields["low"][tk], fields["close"][tk],
                                   fields["volume"][tk]) for tk in ("AAA", "BBB")}
    uni = pd.DataFrame(True, index=P["close"].index, columns=["AAA", "BBB"])
    pop = E.entry_population(P, I_by, uni)
    assert len(pop["sniper"]) >= 5, "fixture produced too few fills"
    max_diff, checked = 0.0, 0
    for tr in pop["sniper"]:
        for arm in ARMS:
            oc = E.simulate_trade(tr, arm, P, I_by)
            lg = PV.simulate_legs(tr, arm, P, I_by)
            assert lg["exit_idx"] == oc["exit_idx"]
            assert lg["exit_reason"] == oc["reason"]
            max_diff = max(max_diff, abs(lg["net_pct"] - oc["net_pct"]))
            checked += 1
    assert max_diff <= 1e-9, max_diff
    assert checked == len(pop["sniper"]) * 12


# ── engine mechanics ──────────────────────────────────────────────────────────

def _legs_for(trades, arm, P, I):
    return {(t["ticker"], t["s"]): PV.simulate_legs(t, arm, P, I)["legs"]
            for t in trades}


def test_cash_never_negative_and_min_cash_tracked():
    n = 400
    o, h, lo, c, v = bars(n, seed=7)
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    trades = [_trade("T", s, s + 1, o[s + 1], atr=5.0) for s in range(60, 340, 25)]
    for arm in ("X0", "X1", "P2", "P4"):
        legs = _legs_for(trades, arm, P, I)
        st = PV.run_portfolio_v2(trades, legs, {"T": c}, P["close"].index, "E1",
                                 record_fills=True)
        assert st["min_cash"] >= -1e-12, (arm, st["min_cash"])
        assert st["final_equity"] > 0


def test_entry_cap_20pct_of_equity():
    n = 120
    o, h, lo, c, v = bars(n, seed=8)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    # tight stop -> the 1%-risk leg is enormous; the 20% cap must bind
    tr = [_trade("T", 50, 51, 100.0, zone_low=99.5, stop=99.0, target=130.0, atr=1.0)]
    legs = _legs_for(tr, "X1", P, I)
    st = PV.run_portfolio_v2(tr, legs, {"T": c}, P["close"].index, "E1",
                             record_fills=True)
    assert st["taken"] == 1
    f = st["fills"][0]
    assert f["role"] == "entry"
    assert f["qty"] * f["px"] <= 0.20 * f["equity_ref"] + 1e-12
    assert f["qty"] * f["px"] == pytest.approx(0.20 * f["equity_ref"], rel=1e-9)


def test_add_cap_30pct_of_equity_p2():
    n = 120
    o, h, lo, c, v = bars(n, seed=9)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    lo[60] = 94.5                            # fills the P2 add at entry-1ATR (95)
    o[60] = 95.5
    c[60] = 99.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    tr = [_trade("T", 50, 51, 100.0, zone_low=96.0, stop=90.0, target=160.0, atr=5.0)]
    legs = _legs_for(tr, "P2", P, I)
    st = PV.run_portfolio_v2(tr, legs, {"T": c}, P["close"].index, "E1",
                             record_fills=True)
    entry = next(f for f in st["fills"] if f["role"] == "entry")
    add = next(f for f in st["fills"] if f["role"] == "add")
    # unconstrained: the add is exactly 50% of the base qty
    assert add["qty"] == pytest.approx(0.5 * entry["qty"], rel=1e-9)
    # total position notional at the add <= 30% of equity at the add
    held_before = entry["qty"]
    total = held_before * add["px"] + add["qty"] * add["px"]
    assert total <= 0.30 * add["equity_ref"] + 1e-9


def test_p1_half_legs_are_half_the_base():
    n = 120
    o, h, lo, c, v = bars(n, seed=10)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    lo[55] = 96.0                            # the zone-low half fills
    o[55] = 96.5
    c[55] = 99.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    tr = [_trade("T", 50, 51, 100.0, zone_low=96.0, stop=90.0, target=160.0, atr=5.0)]
    legs = _legs_for(tr, "P1", P, I)
    st = PV.run_portfolio_v2(tr, legs, {"T": c}, P["close"].index, "E1",
                             record_fills=True)
    entry = next(f for f in st["fills"] if f["role"] == "entry")
    half2 = next(f for f in st["fills"] if f["role"] == "half2")
    # each half is 0.5 x the base size -> the two fills are equal (cash unconstrained)
    assert entry["qty"] == pytest.approx(half2["qty"], rel=1e-9)


def test_skip_rules_full_tiny_cash():
    n = 400
    fields = {}
    for i in range(12):
        tk = f"S{i:02d}"
        o, h, lo, c, v = bars(n, seed=20 + i, vol=0.008)
        o[:] = h[:] = lo[:] = c[:] = 100.0 + i * 0.0    # flat, distinct tickers
        for f, arr in zip(("open", "high", "low", "close", "volume"),
                          (o, h, lo, c, v)):
            fields.setdefault(f, {})[tk] = arr
    P = mk_panel(fields, n)
    I = {tk: E.stock_indicators(fields["open"][tk], fields["high"][tk],
                                fields["low"][tk], fields["close"][tk],
                                fields["volume"][tk]) for tk in fields["close"]}
    closes = {tk: fields["close"][tk] for tk in fields["close"]}
    # 11 overlapping signals with long holds -> 10 taken, 1 skipped_full
    trades = [_trade(f"S{i:02d}", 60, 61, 100.0, zone_low=90.0, stop=80.0,
                     target=200.0, atr=5.0) for i in range(11)]
    legs = _legs_for(trades, "X1", P, I)
    st = PV.run_portfolio_v2(trades, legs, closes, P["close"].index, "E1")
    assert st["taken"] == 10 and st["skipped_full"] == 1

    # deep stop -> the 1%-risk notional itself is under 2% of equity -> tiny
    tr = [_trade("T2", 60, 61, 100.0, zone_low=60.0, stop=40.0, target=200.0, atr=5.0)]
    fields2 = {"open": {"T2": fields["open"]["S00"]}, "high": {"T2": fields["high"]["S00"]},
               "low": {"T2": fields["low"]["S00"]}, "close": {"T2": fields["close"]["S00"]},
               "volume": {"T2": fields["volume"]["S00"]}}
    P2 = mk_panel(fields2, n)
    I2 = {"T2": I["S00"]}
    legs2 = _legs_for(tr, "X1", P2, I2)
    st2 = PV.run_portfolio_v2(tr, legs2, {"T2": fields["close"]["S00"]},
                              P2["close"].index, "E1")
    assert st2["taken"] == 0 and st2["skipped_tiny"] == 1

    # cash-drained book -> the cash leg is binding and sub-2% -> cash skip
    trades3 = [_trade(f"S{i:02d}", 60, 61, 100.0, zone_low=99.0, stop=98.0,
                      target=101.5, atr=0.5) for i in range(6)]
    legs3 = _legs_for(trades3, "X1", P, I)
    st3 = PV.run_portfolio_v2(trades3, legs3, closes, P["close"].index, "E1",
                              record_fills=True)
    # first five entries take 20% each (cap binds: stops are tight) -> cash ~0
    # -> the sixth cannot raise even 2% -> skipped as cash
    assert st3["taken"] == 5 and st3["skipped_cash"] == 1
    assert st3["min_cash"] >= -1e-12


def test_p4_topup_sells_on_its_own_day():
    n = 200
    o, h, lo, c, v = bars(n, seed=13)
    o[:] = h[:] = lo[:] = c[:] = 100.0
    c[70] = 105.5                            # arm the swing lot (close >= +1ATR)
    o[70] = 101.0; h[70] = 106.0; lo[70] = 100.5
    lo[75] = 97.5                            # top-up fills at entry-0.5ATR
    o[75] = 99.0; h[75] = 100.0; c[75] = 99.5
    h[85] = 105.5                            # top-up sells at 97.5+1.5ATR = 105
    o[85] = 100.0; c[85] = 105.0; lo[85] = 100.0
    P = mk_panel({"open": {"T": o}, "high": {"T": h}, "low": {"T": lo},
                  "close": {"T": c}, "volume": {"T": v}}, n)
    I = {"T": E.stock_indicators(o, h, lo, c, v)}
    tr = [_trade("T", 65, 66, 100.0, zone_low=96.0, stop=90.0, target=160.0, atr=5.0)]
    legs = _legs_for(tr, "P4", P, I)
    st = PV.run_portfolio_v2(tr, legs, {"T": c}, P["close"].index, "E1",
                             record_fills=True)
    roles = [f["role"] for f in st["fills"]]
    assert "topup_buy" in roles
    # the engine must not go negative around the top-up sale and the final exit
    assert st["min_cash"] >= -1e-12
    assert st["final_equity"] > 0
