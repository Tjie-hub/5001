"""PIT and mechanics tests for the sniper setup filter — G0 gate (Revision 1).

Synthetic panels and hand-built trades only; no DB, no real data, no outcomes
(X1 R is never computed here). Each test pins one predeclared claim from
PREDECLARATION.md (as amended by §11 Revision 1):

  (a) every feature at s is bit-identical when the panel is truncated at s
      (including the R7 market-index feature);
  (b) the embargo holds (a training label must have exited >= 20 sessions
      before the refit year's first prediction);
  (c) the selection threshold uses only setups strictly before s, and — R1 —
      a setup's selection is IDENTICAL whether computed on the full series or
      any split subset (the subset computation is colder — that difference is
      exactly why the pipeline must use the full series);
  (R5) the rank/threshold reference sets are fill-aware: a setup that fills
      AFTER s is not in s's reference set, and same-day setups share one
      reference set regardless of row order;
  plus the rank fallback rule (C-2), the M0 definition (C-3), the 60%
  threshold arithmetic and fallbacks (§5), the zone-group consistency check
  (§3.1), and the frozen bars (R8).

Run:  pytest docs/research_programs/P-M/sniper_filter/test_pit_sniper_filter.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "exit_study"))

import sniper_filter as SF  # noqa: E402

DUMMY = {f: 1.0 for f in SF.FEATURES if f not in ("park60", "ret126")}


def _panel(n=400, price=100.0, dip_at=None, seed=7):
    """Flat OHLCV panel with an optional dip (a pivot low) at `dip_at`."""
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


def _trade(s, t1=None):
    return {"ticker": "T", "s": s, "t1": s + 1 if t1 is None else t1,
            "entry": 100.0, "zone_top": 100.0,
            "zone_low": 96.0, "stop": 90.0, "target": 115.0, "atr": 5.0,
            "month": "2019-11"}


def _indicators(P):
    return {"T": SF.E.stock_indicators(
        P["open"]["T"].values.astype(float), P["high"]["T"].values.astype(float),
        P["low"]["T"].values.astype(float), P["close"]["T"].values.astype(float),
        P["volume"]["T"].values.astype(float))}


# ── (a) truncation identity (incl. the R7 market index) ─────────────────────

def test_features_bit_identical_on_truncated_panel():
    """Every raw feature at s is bit-identical when the panel is truncated at
    the setup day: nothing looks past s (mkt_above_ma200 included)."""
    s = 300
    P, idx = _panel(400, dip_at=s - 10)
    I = _indicators(P)
    mask = pd.DataFrame(True, index=P["close"].index, columns=P["close"].columns)
    mkt = SF.market_index(P, mask)                        # all-eligible
    mkt_ma = mkt.rolling(200, min_periods=200).mean()
    tr = _trade(s)
    full = SF.raw_features(tr, P, I, mkt, mkt_ma)
    cut = idx[s]                                          # keep bars 0..s
    P2 = {k: v.loc[:cut] for k, v in P.items()}
    I2 = _indicators(P2)
    mkt2 = SF.market_index(P2, pd.DataFrame(True, index=P2["close"].index,
                                            columns=P2["close"].columns))
    mkt2_ma = mkt2.rolling(200, min_periods=200).mean()
    tr2 = dict(tr, s=P2["close"].index.get_loc(cut))
    trunc = SF.raw_features(tr2, P2, I2, mkt2, mkt2_ma)
    for f in SF.FEATURES:
        assert full[f] == trunc[f], f


def test_market_index_is_causal_cumprod_of_mean_returns():
    """R7: the index cumulates the daily mean close-to-close return of the
    eligible universe; a flat eligible universe keeps it at 1.0; a one-day
    +1% close move multiplies it by 1.01 from that day on, never before."""
    P, idx = _panel(10)
    mask = pd.DataFrame(True, index=P["close"].index, columns=P["close"].columns)
    mkt = SF.market_index(P, mask)
    assert (mkt == 1.0).all()
    P["close"].iloc[5, 0] = P["close"].iloc[4, 0] * 1.01
    P["high"].iloc[5, 0] = P["close"].iloc[5, 0] * 1.001
    mkt2 = SF.market_index(P, mask)
    assert mkt2.iloc[4] == pytest.approx(1.0)             # nothing before day 5
    assert mkt2.iloc[5] == pytest.approx(1.01)
    # day 6's return reverts (the fixture price stays at the jumped level), so
    # the cumprod follows the RETURNS: 1.01 * (100/101) = 1.0 — the index never
    # looks ahead and never smooths
    assert mkt2.iloc[6] == pytest.approx(1.01 * (P["close"].iloc[6, 0] / P["close"].iloc[5, 0]))


def test_parkinson_is_pre_event_only_and_matches_hand_calc():
    H = np.array([10.0, 11.0, 12.0, 10.0, 9.0] * 12)      # 60 bars
    L = H * 0.9
    s = len(H) - 1
    expect = float(np.sqrt(np.mean(np.log(H / L) ** 2) / (4.0 * np.log(2.0))))
    assert SF.parkinson60(H, L, s) == pytest.approx(expect)
    # window is the 60 sessions ENDING at s: appending a bar keeps s's value
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


# ── rank fallback / R5 reference sets (C-1, C-2, R5) ────────────────────────

def _rank_frame(rows):
    """rows: dicts with pos, fill_pos, park60, ret126."""
    cols = {"pos": [], "fill_pos": [], "park60": [], "ret126": [],
            "month": ["2019-01"] * len(rows), **DUMMY}
    for r in rows:
        for k in ("pos", "fill_pos", "park60", "ret126"):
            cols[k].append(r[k])
    ft = pd.DataFrame(cols,
                      index=pd.MultiIndex.from_tuples(
                          [(0, r["pos"]) for r in rows]))
    return SF.add_ranks(ft)


def test_rank_uses_strictly_prior_setups_and_falls_back():
    ranked = _rank_frame([
        {"pos": 100, "fill_pos": 101, "park60": 0.2, "ret126": 0.1},
        {"pos": 102, "fill_pos": 103, "park60": 0.4, "ret126": 0.2},
        {"pos": 300, "fill_pos": 301, "park60": 0.3, "ret126": np.nan},
    ])
    # pos=100: no prior setup -> fallback to the raw value (C-2)
    assert ranked.loc[(0, 100), "park60_r"] == 0.2
    # pos=102: one KNOWN prior (pos 100, filled 101 < 102), 0.2 < 0.4 -> rank 1.0
    assert ranked.loc[(0, 102), "park60_r"] == 1.0
    # pos=300: two prior values 0.2,0.4; x=0.3 -> (1 + 0.5*0)/2 = 0.5
    assert ranked.loc[(0, 300), "park60_r"] == 0.5
    # NaN own value stays NaN even with priors (C-2)
    assert not np.isfinite(ranked.loc[(0, 300), "ret126_r"])


def test_rank_window_is_250_sessions():
    ranked = _rank_frame([
        {"pos": 0, "fill_pos": 1, "park60": 0.2, "ret126": 0.1},
        {"pos": 300, "fill_pos": 301, "park60": 0.4, "ret126": 0.2},
    ])
    # 300 - 0 = 300 > 250 -> outside the window: fallback to the raw value
    assert ranked.loc[(0, 300), "park60_r"] == 0.4


def test_rank_excludes_setups_that_fill_after_s():
    """R5: a setup at s' < s whose FILL happens after s is NOT in s's
    reference set (the fill was not knowable at s)."""
    ranked = _rank_frame([
        {"pos": 100, "fill_pos": 200, "park60": 0.9, "ret126": 0.5},  # fills at 200
        {"pos": 150, "fill_pos": 151, "park60": 0.4, "ret126": 0.2},  # fills at 151
        {"pos": 160, "fill_pos": 161, "park60": 0.4, "ret126": 0.2},  # the probe
    ])
    # at pos=160 the pos-100 setup (fills 200 >= 160) is EXCLUDED; only the
    # pos-150 setup (fills 151 < 160) is prior: 0.4 vs 0.4 -> mid-rank 0.5.
    # Without the fill-awareness the rank would see {0.9, 0.4} -> 0.75.
    assert ranked.loc[(0, 160), "park60_r"] == 0.5


def test_same_day_setups_share_one_reference_set():
    """R5: two same-day setups get identical reference sets whatever their row
    order (same-day setups are never in one another's reference set)."""
    rows_a = [
        {"pos": 100, "fill_pos": 101, "park60": 0.2, "ret126": 0.1},
        {"pos": 100, "fill_pos": 102, "park60": 0.4, "ret126": 0.2},
        {"pos": 150, "fill_pos": 151, "park60": 0.3, "ret126": 0.15},
    ]
    rows_b = [rows_a[1], rows_a[0], rows_a[2]]          # reversed row order
    ra, rb = _rank_frame(rows_a), _rank_frame(rows_b)
    # day-150's rank of park60=0.3 sees {0.2, 0.4} -> (1 + 0.5*0)/2 = 0.5,
    # identical under both row orders
    # (duplicate index labels elsewhere make pandas return a Series here)
    assert ra.loc[(0, 150), "park60_r"].iloc[0] == 0.5
    assert rb.loc[(0, 150), "park60_r"].iloc[0] == 0.5
    # the two same-day setups (duplicate key (0,100)) both fall back to their
    # raw values (empty reference set) under both orders — order-dependence gone
    assert sorted(ra.loc[(0, 100), "park60_r"].values) == [0.2, 0.4]
    assert sorted(rb.loc[(0, 100), "park60_r"].values) == [0.2, 0.4]


# ── (c) + R1 selection ───────────────────────────────────────────────────────

def _score_frame(scores, poss, fills=None):
    idx = pd.MultiIndex.from_tuples([(0, p) for p in poss])
    if fills is None:
        fills = [p + 1 for p in poss]
    return (pd.Series(scores, index=idx),
            pd.Series(poss, index=idx, dtype=np.int64),
            pd.Series(fills, index=idx, dtype=np.int64))


def test_selection_threshold_mutates_only_forward():
    scores, pos, fill = _score_frame([0.5] * 20, list(range(1000, 1020)))
    base = SF.select_mask(scores, pos, fill)
    scores2 = scores.copy()
    scores2.iloc[-1] = 9.9
    after = SF.select_mask(scores2, pos, fill)
    assert (base.iloc[:-1] == after.iloc[:-1]).all()


def test_selection_60pct_arithmetic_and_fallbacks():
    scores, pos, fill = _score_frame([float(i) for i in range(10)],
                                     list(range(1000, 1010)))
    sel = SF.select_mask(scores, pos, fill)
    assert bool(sel.iloc[0]) is False             # no priors at all -> not selected
    assert bool(sel.iloc[1]) is True              # 1.0 >= quantile([0.0], .6) = 0.0
    assert bool(sel.iloc[-1]) == (9.0 >= np.quantile(np.arange(9.0), 0.60))
    # fallback: 4 prior setups (< 5) -> threshold over ALL prior setups
    scores3, pos3, fill3 = _score_frame([1.0, 2.0, 3.0, 4.0, 5.0],
                                        [1000, 1001, 1002, 1003, 1004])
    sel3 = SF.select_mask(scores3, pos3, fill3)
    assert bool(sel3.iloc[-1]) == (5.0 >= np.quantile([1.0, 2.0, 3.0, 4.0], 0.60))


def test_selection_excludes_late_filling_setups_from_the_threshold():
    """R5 at the threshold: a prior setup whose fill lands after s cannot set
    s's threshold."""
    scores, pos, fill = _score_frame([1.0, 2.0, 3.0, 4.0, 5.0, 9.0],
                                     [40, 50, 60, 70, 80, 85],
                                     fills=[41, 51, 61, 71, 81, 100])  # 9.0 fills at 100
    scores.loc[(0, 90)] = 3.7
    pos.loc[(0, 90)] = 90
    fill.loc[(0, 90)] = 91
    sel = SF.select_mask(scores, pos, fill)
    # prior KNOWN setups at 90: scores [1,2,3,4,5] (the 9.0 fills at 100 >= 90):
    # >= 5 priors -> the window threshold is q60([1,2,3,4,5]) = 3.4 -> selected
    assert bool(sel.loc[(0, 90)]) == (3.7 >= np.quantile([1.0, 2.0, 3.0, 4.0, 5.0], 0.60))
    assert bool(sel.loc[(0, 90)]) is True
    # WITHOUT the fill-awareness the 9.0 would sit in the window and move the
    # threshold to q60([1,2,3,4,5,9]) = 4.0 -> NOT selected: the bug is real
    assert np.quantile([1.0, 2.0, 3.0, 4.0, 5.0, 9.0], 0.60) == pytest.approx(4.0)
    assert (3.7 >= 4.0) is False


def test_selection_identical_on_full_series_and_split_subset():
    """R1: a setup in the FIRST test month gets its selection from the FULL
    series (warm trailing-250 history); computing the threshold on the test
    subset instead is colder and MUST NOT be used — the pipeline indexes the
    full-series result into the subset."""
    n = 300
    poss = list(range(1000, 1000 + n))
    rng = np.random.default_rng(11)
    scores, pos, fill = _score_frame(list(rng.uniform(0, 1, n)), poss)
    full_sel = SF.select_mask(scores, pos, fill)
    subset_sel = SF.select_mask(scores.iloc[-40:], pos.iloc[-40:], fill.iloc[-40:])
    # the subset's first row has no warm history inside the subset...
    assert bool(subset_sel.iloc[0]) is False
    # ...while the full-series computation selects it (its threshold comes
    # from the warm prior history) — and the pipeline uses exactly this value
    assert bool(full_sel.iloc[-40]) is True
    assert bool(full_sel.loc[full_sel.iloc[-40:].index[0]])


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


# ── M0 (C-3) and the frozen bars (R8) ────────────────────────────────────────

def test_m0_is_mean_of_inverted_park_and_ret_rank_and_nan_safe():
    ft = pd.DataFrame({"park60_r": [0.9, 0.2, np.nan], "ret126_r": [0.1, 0.6, 0.5]},
                      index=pd.MultiIndex.from_tuples([(0, 1), (0, 2), (0, 3)]))
    s = SF.m0_score(ft)
    assert s.loc[(0, 1)] == pytest.approx(0.5 * (1 - 0.9 + 0.1))
    assert s.loc[(0, 2)] == pytest.approx(0.5 * (1 - 0.2 + 0.6))
    assert not np.isfinite(s.loc[(0, 3)])       # undefined component -> unscored


def test_emax_abs_z_reproduces_the_repo_values_and_the_frozen_bars():
    assert SF.emax_abs_z(252, steps=200_000) == pytest.approx(3.0395, abs=5e-4)
    assert SF.emax_abs_z(266, steps=200_000) == pytest.approx(3.0558, abs=5e-4)
    assert SF.emax_abs_z(270, steps=200_000) == pytest.approx(3.0603, abs=5e-4)
    # R8 + owner ruling 560522a: the PRIMARY bar is the stricter census
    # (561 + 4 = 565); the exact 561 value reproduces the recount's 3.2745
    assert SF.emax_abs_z(561, steps=200_000) == pytest.approx(3.2745, abs=5e-4)
    assert SF.CENSUS_N_PRIMARY == 565
    assert SF.BAR_PRIMARY == 3.2765
    assert SF.emax_abs_z(SF.CENSUS_N_PRIMARY, steps=200_000) == pytest.approx(
        SF.BAR_PRIMARY, abs=5e-4)
    # the secondary line is report-only and can never pass a configuration
    assert SF.CENSUS_N_SECONDARY == 280
    assert SF.emax_abs_z(280, steps=200_000) == pytest.approx(3.0713, abs=5e-4)
    assert SF.BAR_SECONDARY == 3.07


# ── the G1 gate ──────────────────────────────────────────────────────────────

def test_g1_gate_refuses_without_approval(monkeypatch):
    monkeypatch.delenv(SF.G1_ENV, raising=False)
    with pytest.raises(SystemExit):
        SF.run_g1()
