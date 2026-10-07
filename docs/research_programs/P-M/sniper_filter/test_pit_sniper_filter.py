"""PIT and mechanics tests for the sniper setup filter — G0 gate.

Synthetic panels and hand-built trades only; no DB, no real data, no outcomes
(X1 R is never computed here). Each test pins one predeclared claim from
PREDECLARATION.md:

  (a) every feature at s is bit-identical when the panel is truncated at s;
  (b) the embargo holds (a training label must have exited >= 20 sessions
      before the refit year's first prediction);
  (c) the selection threshold uses only setups strictly before s;
  plus the rank fallback rule (C-2), the M0 definition (C-3), the 60%
  threshold arithmetic and fallbacks (§5), the zone-group consistency check
  (§3.1) and the frozen deflation bar (§7).

Run:  pytest docs/research_programs/P-M/sniper_filter/test_pit_sniper_filter.py -v
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "exit_study"))

import sniper_filter as SF  # noqa: E402


def _panel(n=400, price=100.0, dip_at=None, seed=7):
    """Flat OHLCV panel with an optional dip (a pivot low) at `dip_at`."""
    rng = np.random.default_rng(seed)
    c = np.full(n, float(price))
    o = np.full(n, float(price))
    h = np.full(n, float(price))
    l = np.full(n, float(price))
    v = np.full(n, 2.0e8)
    if dip_at is not None:
        l[dip_at] = 96.0
        o[dip_at] = 99.0
        c[dip_at] = 97.0
        h[dip_at] = 99.5
    P = {}
    idx = pd.bdate_range("2019-01-02", periods=n)
    for f, arr in (("open", o), ("high", h), ("low", l), ("close", c), ("volume", v)):
        P[f] = pd.DataFrame({"T": arr}, index=idx)
    return P, idx


def _trade(s):
    return {"ticker": "T", "s": s, "t1": s + 1, "entry": 100.0, "zone_top": 100.0,
            "zone_low": 96.0, "stop": 90.0, "target": 115.0, "atr": 5.0,
            "month": "2019-11"}


def _indicators(P):
    return {"T": SF.E.stock_indicators(
        P["open"]["T"].values.astype(float), P["high"]["T"].values.astype(float),
        P["low"]["T"].values.astype(float), P["close"]["T"].values.astype(float),
        P["volume"]["T"].values.astype(float))}


# ── (a) truncation identity ──────────────────────────────────────────────────

def test_features_bit_identical_on_truncated_panel():
    """Every raw feature at s is bit-identical when the panel (and IHSG) is
    truncated at the setup day: nothing looks past s."""
    s = 300
    P, idx = _panel(400, dip_at=s - 10)
    I = _indicators(P)
    ihsg = pd.Series(7000.0, index=idx)
    tr = _trade(s)
    full = SF.raw_features(tr, P, I, ihsg, ihsg.rolling(200, min_periods=200).mean())
    cut = idx[s]                                          # keep bars 0..s
    P2 = {k: v.loc[:cut] for k, v in P.items()}
    I2 = _indicators(P2)
    ihsg2 = ihsg.loc[:cut]
    tr2 = dict(tr, s=P2["close"].index.get_loc(cut))
    trunc = SF.raw_features(tr2, P2, I2, ihsg2, ihsg2.rolling(200, min_periods=200).mean())
    for f in SF.FEATURES:
        assert full[f] == trunc[f], f


def test_parkinson_is_pre_event_only_and_matches_hand_calc():
    H = np.array([10.0, 11.0, 12.0, 10.0, 9.0] * 12 + [10.0] * 0)  # 60 bars
    L = H * 0.9
    s = len(H) - 1
    expect = float(np.sqrt(np.mean(np.log(H / L) ** 2) / (4.0 * np.log(2.0))))
    assert SF.parkinson60(H, L, s) == pytest.approx(expect)
    # window is the 60 sessions ENDING at s: shifting s changes the value
    assert SF.parkinson60(np.append(H, 10.0), np.append(L, 9.0), s) == SF.parkinson60(H, L, s)


# ── zone-group consistency (§3.1) ────────────────────────────────────────────

def test_zone_group_matches_signal_zone_low_and_count():
    s = 300
    P, _ = _panel(400, dip_at=s - 10)
    I = _indicators(P)
    tr = _trade(s)
    grp = SF.zone_group_at(tr, P, I)
    assert grp["min"] == pytest.approx(tr["zone_low"])
    assert grp["count"] >= 1                       # the dip pivot is a touch
    with pytest.raises(ValueError):
        SF.zone_group_at(dict(tr, zone_low=50.0), P, I)


# ── rank fallback / strictly-past window (C-1, C-2) ─────────────────────────

def test_rank_uses_strictly_prior_setups_and_falls_back():
    ft = pd.DataFrame(
        {"pos": [100, 101, 300], "month": ["2019-01"] * 3, "park60": [0.2, 0.4, 0.3],
         "ret126": [0.1, 0.2, np.nan], 'zone_touches': 1.0, 'planned_rr': 1.0, 'zone_width_atr': 1.0, 'zone_stop_atr': 1.0, 'close_ma20_atr': 1.0, 'close_ma50_atr': 1.0, 'ma200_slope': 1.0, 'ihsg_above_ma200': 1.0},
        index=pd.MultiIndex.from_tuples([(0, 100), (0, 101), (0, 300)]))
    ranked = SF.add_ranks(ft)
    # pos=100: no prior setup -> fallback to the raw value (C-2)
    assert ranked.loc[(0, 100), "park60_r"] == 0.2
    # pos=101: one prior value 0.2 < 0.4 -> rank 1.0
    assert ranked.loc[(0, 101), "park60_r"] == 1.0
    # pos=300: two prior values 0.2,0.4; x=0.3 -> (1 + 0.5*0)/2 = 0.5
    assert ranked.loc[(0, 300), "park60_r"] == 0.5
    # NaN own value stays NaN even with priors (C-2)
    assert not np.isfinite(ranked.loc[(0, 300), "ret126_r"])
    # pos=101 sees only pos=100 (strictly prior, in-window): rank of 0.2 vs 0.1 = 1.0
    assert ranked.loc[(0, 101), "ret126_r"] == 1.0


def test_rank_window_excludes_beyond_250_sessions():
    ft = pd.DataFrame(
        {"pos": [0, 300], "month": ["2019-01"] * 2, "park60": [0.2, 0.4],
         "ret126": [0.1, 0.2], 'zone_touches': 1.0, 'planned_rr': 1.0, 'zone_width_atr': 1.0, 'zone_stop_atr': 1.0, 'close_ma20_atr': 1.0, 'close_ma50_atr': 1.0, 'ma200_slope': 1.0, 'ihsg_above_ma200': 1.0},
        index=pd.MultiIndex.from_tuples([(0, 0), (0, 300)]))
    ranked = SF.add_ranks(ft)
    # pos=300 vs prior at pos=0: 300 - 0 = 300 > 250 -> outside the window
    assert ranked.loc[(0, 300), "park60_r"] == 0.4


# ── (c) selection threshold uses only strictly-prior setups ─────────────────

def _score_frame(scores, poss):
    idx = pd.MultiIndex.from_tuples([(0, p) for p in poss])
    return (pd.Series(scores, index=idx), pd.Series(poss, index=idx))


def test_selection_threshold_mutates_only_forward():
    scores, pos = _score_frame([0.5] * 20, list(range(1000, 1020)))
    base = SF.select_mask(scores, pos)
    # give the LAST setup an extreme score: earlier selections must not move
    scores2 = scores.copy()
    scores2.iloc[-1] = 9.9
    after = SF.select_mask(scores2, pos)
    assert (base.iloc[:-1] == after.iloc[:-1]).all()


def test_selection_60pct_arithmetic_and_fallbacks():
    # strictly increasing scores: each setup's threshold is the 60th pct of
    # [0..i-1], always below its own score -> the first is unscored, rest select
    scores, pos = _score_frame([float(i) for i in range(10)], list(range(1000, 1010)))
    sel = SF.select_mask(scores, pos)
    assert bool(sel.iloc[0]) is False             # no priors at all -> not selected
    assert bool(sel.iloc[1]) is True              # 1.0 >= quantile([0.0], .6) = 0.0
    assert bool(sel.iloc[-1]) == (9.0 >= np.quantile(np.arange(9.0), 0.60))
    # fallback: 4 prior setups (< 5) -> threshold over ALL prior setups
    scores3, pos3 = _score_frame([1.0, 2.0, 3.0, 4.0, 5.0], [1000, 1001, 1002, 1003, 1004])
    sel3 = SF.select_mask(scores3, pos3)
    assert bool(sel3.iloc[-1]) == (5.0 >= np.quantile([1.0, 2.0, 3.0, 4.0], 0.60))


# ── (b) the embargo ──────────────────────────────────────────────────────────

def test_embargo_excludes_labels_within_20_sessions():
    frame = pd.DataFrame({
        "month": ["2015-06", "2015-06", "2015-06", "2015-06"],
        "exit_pos": [900, 979, 980, 981],       # first_pos = 1000
    })
    m = SF.train_mask_for(frame, 2016, 1000)
    # exit <= 1000-20 = 980 is the frozen rule: 979 and 980 pass, 981 does not
    assert list(m) == [True, True, True, False]


def test_embargo_uses_previous_year_month_bound():
    frame = pd.DataFrame({"month": ["2016-01", "2015-12"], "exit_pos": [0, 0]})
    m = SF.train_mask_for(frame, 2016, 1000)
    assert list(m) == [False, True]             # 2016-01 is not in the train window


# ── M0 (C-3) and the frozen bar ──────────────────────────────────────────────

def test_m0_is_mean_of_inverted_park_and_ret_rank_and_nan_safe():
    ft = pd.DataFrame({"park60_r": [0.9, 0.2, np.nan], "ret126_r": [0.1, 0.6, 0.5]},
                      index=pd.MultiIndex.from_tuples([(0, 1), (0, 2), (0, 3)]))
    s = SF.m0_score(ft)
    assert s.loc[(0, 1)] == pytest.approx(0.5 * (1 - 0.9 + 0.1))
    assert s.loc[(0, 2)] == pytest.approx(0.5 * (1 - 0.2 + 0.6))
    assert not np.isfinite(s.loc[(0, 3)])       # undefined component -> unscored


def test_emax_abs_z_reproduces_the_repo_values():
    assert SF.emax_abs_z(252, steps=200_000) == pytest.approx(3.0395, abs=5e-4)
    assert SF.emax_abs_z(266, steps=200_000) == pytest.approx(3.0558, abs=5e-4)
    assert SF.emax_abs_z(270, steps=200_000) == pytest.approx(3.0603, abs=5e-4)
    assert SF.emax_abs_z(SF.CENSUS_N, steps=200_000) == pytest.approx(3.0713, abs=5e-4)
    assert SF.DEFLECTION_BAR == 3.07 and SF.CENSUS_N == 280


# ── the G1 gate ──────────────────────────────────────────────────────────────

def test_g1_gate_refuses_without_approval(monkeypatch):
    monkeypatch.delenv(SF.G1_ENV, raising=False)
    with pytest.raises(SystemExit):
        SF.run_g1()
