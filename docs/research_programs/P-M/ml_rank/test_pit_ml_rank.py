"""PIT (point-in-time) tests for the HYP-PM-0015 driver — G0 gate.

They read NO outcomes: synthetic panels only, no DB, no real returns, no model
fitting. Each test pins one predeclared causality claim from
PREDECLARATION.md §7:

  (a) every feature at rebalance cutoff t is bit-identical when the panel is
      truncated at t (no forward peeking in any feature window);
  (b) training label windows never overlap a prediction month (the embargo:
      December's return is never a training label of the January refit);
  (c) the universe at entry date D uses only data up to the prior session
      (a name that becomes eligible only ON D is not in the D universe).

Run:  pytest docs/research_programs/P-M/ml_rank/test_pit_ml_rank.py -v
(the repo pytest.ini restricts default discovery to tests/; this file is run
explicitly per the brief).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ml_rank_model as M  # noqa: E402

PIT_SEED = 20261006  # fixed: tests are deterministic


def make_panel(n_names=60, n_sessions=520, seed=PIT_SEED, hi_price=8):
    """Synthetic date×ticker pivots with realistic structure: per-name random
    walk (some names priced ≥ 50, most below), volume lognormal, H/L consistent
    with O/C, occasional suspensions (NaN stretches)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-02", periods=n_sessions)
    tickers = [f"TK{i:03d}" for i in range(n_names)]
    drift = rng.normal(0.0002, 0.0004, size=n_names)
    vol = rng.uniform(0.01, 0.04, size=n_names)
    scale = np.concatenate([rng.uniform(60.0, 400.0, size=hi_price),
                            rng.uniform(5.0, 48.0, size=n_names - hi_price)])
    logp = np.cumsum(rng.normal(0, 1, size=(n_sessions, n_names))
                     * vol[None, :] + drift[None, :], axis=0)
    close = np.exp(logp) * scale[None, :]
    open_ = close * np.exp(rng.normal(0, 0.004, size=close.shape))
    hi = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.008, close.shape)))
    lo = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.008, close.shape)))
    volume = np.exp(rng.normal(15, 1.0, size=close.shape))
    C = pd.DataFrame(close, index=dates, columns=tickers)
    # suspensions: a few names miss a few stretches entirely
    for tk in tickers[:5]:
        s = int(rng.integers(60, n_sessions - 40))
        C.loc[dates[s:s + int(rng.integers(3, 15))], tk] = np.nan
    na = C.isna()                      # a suspended name has NO bar: all fields NaN
    O = pd.DataFrame(open_, index=dates, columns=tickers).mask(na)
    H = pd.DataFrame(hi, index=dates, columns=tickers).mask(na)
    L = pd.DataFrame(lo, index=dates, columns=tickers).mask(na)
    V = pd.DataFrame(volume, index=dates, columns=tickers).mask(na)
    return {"open": O, "high": H, "low": L, "close": C, "volume": V}


# ── (a) feature bit-identity under panel truncation ───────────────────────────

@pytest.mark.parametrize("cutoff_frac", [0.45, 0.60, 0.75, 0.90])
def test_a_features_bit_identical_under_truncation(cutoff_frac):
    P = make_panel()
    T = len(P["close"])
    t = int(T * cutoff_frac)
    F_full = M.compute_features(P)
    elig_full = M.eligibility_mask(P["close"], P["volume"])
    P_trunc = {k: v.iloc[: t + 1] for k, v in P.items()}
    F_trunc = M.compute_features(P_trunc)
    elig_trunc = M.eligibility_mask(P_trunc["close"], P_trunc["volume"])
    for f in M.FEATURES:
        a = F_full[f].iloc[: t + 1].values
        b = F_trunc[f].values
        assert a.shape == b.shape, f
        assert np.array_equal(a, b, equal_nan=True), f"feature {f} not PIT at t={t}"
    assert np.array_equal(elig_full.iloc[: t + 1].values, elig_trunc.values), \
        "eligibility not PIT at t"


def test_a_features_deterministic_rerun():
    P = make_panel(seed=11)
    F1 = M.compute_features(P)
    F2 = M.compute_features(P)
    for f in M.FEATURES:
        assert np.array_equal(F1[f].values, F2[f].values, equal_nan=True), f


# ── (b) embargo: label windows never overlap prediction months ────────────────

def _month_add(m: str, k: int) -> str:
    y, mo = int(m[:4]), int(m[5:7])
    tot = y * 12 + (mo - 1) + k
    return f"{tot // 12:04d}-{tot % 12 + 1:02d}"


def test_b_embargo_no_label_window_overlap():
    P = make_panel(n_sessions=900)
    schedule = M.build_schedule(P)
    years = sorted({r["year"] for r in schedule})
    for year in years[1:]:
        train, pred = M.refit_split(schedule, year)
        assert pred, year
        assert all(m >= M.TRAIN_FIRST_MONTH for m in train)
        first_pred = min(pred)
        # every label window [m, next(m)] ends strictly before the first
        # prediction month → no overlap with any prediction month
        for m in train:
            assert M.month_key_next(m) < first_pred, (year, m, first_pred)
        assert not (set(train) & set(pred))
        # the month immediately before the first prediction month is never a
        # training label (its return window reaches into the prediction month)
        assert _month_add(first_pred, -1) not in train
        # December is embargoed for a January refit
        if first_pred.endswith("-01"):
            assert max(train).endswith("-11"), (year, max(train))


def test_b_embargo_december_label_never_used():
    P = make_panel(n_sessions=400)
    schedule = M.build_schedule(P)
    train, pred = M.refit_split(schedule, max({r["year"] for r in schedule}))
    first_pred = min(pred)
    # the label month whose return window touches the first prediction month
    # is exactly the one excluded: next(m) == first_pred must not be in train
    assert _month_add(first_pred, -1) not in train
    assert _month_add(first_pred, -2) in train  # one month earlier is fine


# ── (c) universe at D uses only data up to the prior session ──────────────────

def test_c_universe_excludes_names_turning_eligible_on_entry_date():
    """A name whose price/turnover only qualifies ON the entry session D must
    not be in the D universe (features and eligibility stop at the prior
    session t)."""
    n_sessions = 160
    n_fill = 155          # filler names with huge turnover keep the rank gate real
    dates = pd.bdate_range("2024-01-02", periods=n_sessions)
    # entry month = 2024-06; entry session = its first bdate; t = the row before
    entry_ts = pd.Timestamp("2024-06-03")
    e = dates.get_loc(entry_ts)
    t = e - 1
    tickers = [f"FL{i:03d}" for i in range(n_fill)] + ["CTRL", "LATE", "VOLJ"]
    close = pd.DataFrame(300.0, index=dates, columns=tickers)
    volume = pd.DataFrame(1.0e6, index=dates, columns=tickers)
    # LATE: priced 40 (below floor) through t, 300 on the entry session
    close.loc[dates[:e], "LATE"] = 40.0
    # VOLJ: price fine but turnover tiny through t, 1e12 on the entry session
    volume.loc[dates[:e], "VOLJ"] = 1.0
    P = {"open": close.copy(), "high": close * 1.01, "low": close * 0.99,
         "close": close, "volume": volume}
    elig = M.eligibility_mask(P["close"], P["volume"])
    uni_t = set(elig.columns[elig.iloc[t].values])       # universe at entry date D
    assert "CTRL" in uni_t                                # control: eligible from prior data
    assert "LATE" not in uni_t, "LATE used its entry-session price"
    assert "VOLJ" not in uni_t, "VOLJ used its entry-session turnover"
    # and truncating the panel at t gives the identical universe
    P_trunc = {k: v.iloc[: t + 1] for k, v in P.items()}
    elig_trunc = M.eligibility_mask(P_trunc["close"], P_trunc["volume"])
    assert set(elig_trunc.columns[elig_trunc.iloc[-1].values]) == uni_t


def test_c_universe_truncation_identity_multi_month():
    P = make_panel(n_names=80, n_sessions=420)
    schedule = M.build_schedule(P)
    elig_full = M.eligibility_mask(P["close"], P["volume"])
    for rec in schedule[::7]:
        t = rec["t"]
        P_trunc = {k: v.iloc[: t + 1] for k, v in P.items()}
        elig_trunc = M.eligibility_mask(P_trunc["close"], P_trunc["volume"])
        assert np.array_equal(elig_full.iloc[t].values, elig_trunc.iloc[-1].values), \
            rec["month"]


# ── machinery sanity (books, IC, schedule shape) ──────────────────────────────

def test_book_skips_non_enterable_and_sizes_quintile():
    idx = [f"N{i:02d}" for i in range(20)]
    scored = pd.Series(np.linspace(0, 1, 20), index=idx)
    ret = pd.Series(0.01, index=idx)
    entry_open = pd.Series(10.0, index=idx)
    entry_open.loc["N19"] = np.nan          # cannot enter
    bk = M.month_book(scored, ret, entry_open, pd.Series(dtype=float))
    assert bk["k"] == 4
    assert "N19" not in bk["members"] and len(bk["members"]) == 4
    assert bk["turnover"] == pytest.approx(0.5)          # τ = 0.5·Σw = 0.5·(4·0.25)
    bk2 = M.month_book(scored, ret, entry_open,
                       pd.Series(1.0 / 4.0, index=bk["members"]))
    assert bk2["turnover"] == pytest.approx(0.0)         # identical book → no turnover


def test_rank_ic_monotone():
    s = pd.Series(np.arange(10, dtype=float))
    assert M.rank_ic(s, s * 2 + 1) == pytest.approx(1.0)
    assert M.rank_ic(s, -s) == pytest.approx(-1.0)
    assert np.isnan(M.rank_ic(s.head(2), s.head(2)))     # < 3 names → NaN


def test_m0_score_uses_low_vol_and_momentum():
    X = pd.DataFrame({"park60": [0.1, 0.9], "mom12_1": [0.9, 0.1]},
                     index=["A", "B"])
    cs = {"X": X}
    s = M.m0_scores(cs)
    assert s["A"] == pytest.approx(0.9)   # low vol + high momentum ranks first
    assert s["B"] == pytest.approx(0.1)


def test_newey_west_t_matches_naive_at_lag0_white_noise():
    rng = np.random.default_rng(3)
    x = rng.normal(0.05, 0.04, size=400)
    t_nw = M.newey_west_t(x, lag=0)
    t_naive = x.mean() / (x.std(ddof=0) / np.sqrt(400))
    assert t_nw == pytest.approx(t_naive, rel=1e-12)
    assert abs(M.newey_west_t(x, lag=3)) > 0


def test_refit_split_train_uses_expanding_window():
    P = make_panel(n_sessions=900)
    schedule = M.build_schedule(P)
    years = sorted({r["year"] for r in schedule})
    y0, y1 = years[len(years) // 3], years[-1]
    t0, _ = M.refit_split(schedule, y0)
    t1, _ = M.refit_split(schedule, y1)
    assert set(t0) < set(t1) and len(t1) > len(t0)


def test_schedule_never_emits_first_panel_month():
    """Regression guard: the panel's first month has no prior session — t must
    never be negative (iloc[-1] would silently wrap to the LAST row)."""
    P = make_panel(n_sessions=400)
    schedule = M.build_schedule(P)
    assert all(r["t"] >= 0 for r in schedule)
    assert all(r["t"] < r["entry"] < r["exit"] for r in schedule)
    first_month_key = M.month_key(P["close"].index[0])
    assert first_month_key not in {r["month"] for r in schedule}


# ── end-to-end machinery smoke test (synthetic only — no real returns) ────────

def test_g1_gate_refuses_without_approval():
    with pytest.raises(SystemExit):
        M.run_g1()


def test_full_pipeline_smoke(monkeypatch):
    """run_walkforward + evaluate() on a synthetic panel: the frozen reporting
    path must execute and return a well-formed result. Fits only on SYNTHETIC
    labels — reads no real outcomes, writes nothing."""
    monkeypatch.setattr(M, "VAL_MONTHS", ("2021-01", "2023-09"))
    P = make_panel(n_names=60, n_sessions=2000, seed=5)
    F = M.compute_features(P)
    elig = M.eligibility_mask(P["close"], P["volume"])
    schedule = M.build_schedule(P)
    ret_m = M.monthly_returns(P, schedule)
    cs_by_month, scores = M.run_walkforward(F, elig, ret_m, schedule)
    val = [r["month"] for r in schedule
           if "2021-01" <= r["month"] <= "2023-09" and r["month"] in cs_by_month]
    assert len(val) >= 32, "smoke panel must cover the PBO split requirement"
    assert all(any(m in s for m in val) for s in scores.values())
    result = M.evaluate(P, pd.DataFrame({"open": [], "close": []}), elig, ret_m,
                        schedule, cs_by_month, scores, fingerprint={"sha256": "smoke"})
    assert set(result["chosen"]) == {"m1", "m2"}
    assert result["chosen"]["m1"] in {n for n, f, _ in M.MODEL_GRID if f == "m1"}
    for key in ("m0", "m1", "m2"):
        st = result["stats"][key]
        assert {"validation", "test"} <= set(st)
        assert "nw_t" in st["test"] and "by_year" in st["test"]
        assert result["verdict"][key]["pass"] in (True, False)
    assert result["pbo"] is None or {"pbo", "n_trials"} <= set(result["pbo"])
    assert set(result["dsr"]) == {"m1", "m2"}
    assert all(len(v) <= 30 for v in result["top30_last_month"].values())
    assert result["verdict"]["m1"]["pass"] in (True, False)
