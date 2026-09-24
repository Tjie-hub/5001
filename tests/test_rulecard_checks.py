"""Every mandatory Rule Card check must catch the incident it encodes (D-055).

One test per row of the incident register in research/rulecard/checks.py. Each
incident is reproduced on a synthetic panel; the check must FAIL on the defect and
PASS on the clean version. Hermetic: no DB, no real data.
"""
import numpy as np
import pandas as pd
import pytest

from research.rulecard import checks, engine, synthetic

CARD = {"tier": "R", "portfolio": {"bucketing": "decile", "use": "avoid", "use_end": "high"},
        "estimand": {"primary_kind": "bucket_minus_rest", "predicted_sign": "negative", "nw_lag": 3},
        "deployment": {"predicted_sign": "negative"}, "costs": {"round_trip_pct": 0.60},
        "windows": {"split": "2017-01-01"}, "fingerprints": []}


@pytest.fixture(scope="module")
def clean():
    pan = engine.Panel(synthetic.make_panel(n_tickers=80, years=4, seed=21))
    cal = engine.calendar(pan.P)
    return pan, cal, list(cal["formation"])


@pytest.fixture(scope="module")
def sparse_volume():
    """~3% of sessions untraded per name — the raw material of LA-1 and ZV-1."""
    raw = synthetic.make_panel(n_tickers=80, years=4, seed=22)
    rng = np.random.default_rng(5)
    raw.loc[rng.random(len(raw)) < 0.03, "volume"] = 0.0
    pan = engine.Panel(raw)
    cal = engine.calendar(pan.P)
    return pan, cal, list(cal["formation"])


# ── LA-1: look-ahead (VOLEX +/-20 suspension mask, VOLEX-SN z_fwd) ─────────────────────

def test_la1_clean_trailing_signal_passes(clean):
    pan, _, forms = clean
    s = synthetic.z_signal(pan.P)
    assert checks.prefix_invariance(pan, synthetic.z_signal, s, forms)["status"] == "PASS"


def _future_zero_volume_mask(p):
    """The VOLEX-SN z_fwd defect: drop names untraded in the NEXT 20 sessions."""
    z = (p["volume"] <= 0).astype(float)
    fwd = z.groupby(p["ticker"]).transform(lambda x: x[::-1].rolling(20, min_periods=1).max()[::-1].shift(-1))
    return p["z"].where(fwd.fillna(0) == 0)


def _symmetric_window_mask(p):
    """The VOLEX-001 defect: exclude names within +/-20 sessions of an untraded session."""
    z = (p["volume"] <= 0).astype(float)
    near = z.groupby(p["ticker"]).transform(lambda x: x.rolling(41, center=True, min_periods=1).max())
    return p["z"].where(near == 0)


@pytest.mark.parametrize("bad", [_future_zero_volume_mask, _symmetric_window_mask])
def test_la1_holding_period_filters_fail(sparse_volume, bad):
    pan, _, forms = sparse_volume
    r = checks.prefix_invariance(pan, bad, bad(pan.P), forms)
    assert r["status"] == "FAIL" and r["detail"]["violations"]


def test_la1_full_sample_normalisation_fails(clean):
    pan, _, forms = clean

    def demeaned(p):
        return p["close"] - p.groupby("ticker")["close"].transform("mean")
    assert checks.prefix_invariance(pan, demeaned, demeaned(pan.P), forms)["status"] == "FAIL"


def test_la1_centred_rolling_fails(clean):
    pan, _, forms = clean

    def centred(p):
        return p.groupby("ticker")["close"].transform(lambda x: x.rolling(5, center=True).mean())
    assert checks.prefix_invariance(pan, centred, centred(pan.P), forms)["status"] == "FAIL"


def test_la1_signal_on_wrong_index_fails(clean):
    pan, _, forms = clean

    def reindexed(p):
        return p["z"].reset_index(drop=True).set_axis(range(1, len(p) + 1))
    assert checks.prefix_invariance(pan, reindexed, synthetic.z_signal(pan.P), forms)["status"] == "FAIL"


# ── ZV-1: zero-volume carry-forward bars (FWD-PM-REGIME-001, LIFE) ───────────────────

def test_zv1_engine_universe_excludes_carry_forward_bars():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=23)
    dates = list(pd.to_datetime(sorted(raw.date.unique())))
    d = engine.calendar(engine.prepare(raw))["formation"].iloc[20]
    k = dates.index(d)
    # 8 consecutive untraded sessions ending on a month-end, each re-printing the same OHLC
    rows = raw.index[(raw.ticker == "S000") & raw.date.isin(dates[k - 7:k + 1])]
    raw.loc[rows, ["open", "high", "low", "close"]] = raw.loc[rows[0], "close"]
    raw.loc[rows, "volume"] = 0.0
    pan = engine.Panel(raw)
    at_d = pan.P.index[(pan.P.ticker == "S000") & (pan.P.date == d)]
    assert not bool(pan.eligible.loc[at_d].iloc[0])


def test_zv1_guard_catches_a_broken_universe(sparse_volume):
    pan, _, forms = sparse_volume
    assert checks.traded_days_guard(pan, forms)["status"] == "PASS"
    broken = engine.Panel.__new__(engine.Panel)
    broken.__dict__.update(pan.__dict__)
    broken.eligible = pd.Series(True, index=pan.P.index)      # a regression that admits everything
    assert checks.traded_days_guard(broken, forms)["status"] == "FAIL"


# ── ID-1: degenerate predictor (HYP-PM-0003 / BROKER-001 SUM(lot) identity) ──────────

def test_id1_identity_like_predictor_fails(clean):
    pan, cal, forms = clean
    rng = np.random.default_rng(3)
    s = pd.Series(np.where(rng.random(len(pan.P)) < 0.7, 0.0, rng.normal(size=len(pan.P))),
                  index=pan.P.index)                          # zero on ~70% of ticker-days
    months = engine.run_months(pan, s, CARD, cal, with_returns=False)
    assert checks.predictor_nondegenerate(months, pan, s, forms, "decile")["status"] == "FAIL"


def test_id1_sparse_coverage_fails(clean):
    pan, cal, forms = clean
    s = synthetic.z_signal(pan.P).where(pan.P["ticker"] < "S040")   # half the names unscored
    months = engine.run_months(pan, s, CARD, cal, with_returns=False)
    assert checks.predictor_nondegenerate(months, pan, s, forms, "decile")["status"] == "FAIL"


def test_id1_real_characteristic_passes(clean):
    pan, cal, forms = clean
    s = synthetic.z_signal(pan.P)
    months = engine.run_months(pan, s, CARD, cal, with_returns=False)
    assert checks.predictor_nondegenerate(months, pan, s, forms, "decile")["status"] == "PASS"


# ── EX-1 / FILL-1: exit-index defect and close fill ─────────────────────────────────

def test_ex1_zeroed_outcome_fails():
    months = [{"valid": True, "univ": 100, "zero_returns": 100, "primary": 0.0,
               "month": f"2020-{i:02d}"} for i in range(1, 13)]
    assert checks.forward_returns_nontrivial(months)["status"] == "FAIL"


def test_fill1_entry_on_formation_day_fails():
    ok = {"month": "2020-01", "formation": "2020-01-31", "entry": "2020-02-03", "exit": "2020-03-02"}
    bad = dict(ok, month="2020-02", entry="2020-01-31")
    assert checks.entry_exit_order([ok])["status"] == "PASS"
    assert checks.entry_exit_order([ok, bad])["status"] == "FAIL"


def test_fill1_engine_fills_at_next_session_open(clean):
    pan, cal, _ = clean
    s = synthetic.z_signal(pan.P)
    months = engine.run_months(pan, s, CARD, cal)
    m = next(x for x in months if x.get("valid"))
    E, X = pd.Timestamp(m["entry"]), pd.Timestamp(m["exit"])
    assert E > pd.Timestamp(m["formation"])
    t = pd.Timestamp(m["formation"])
    idx = pan.P.index[(pan.P.date == t) & pan.eligible]
    tk = pan.P.loc[idx, "ticker"].values
    expect = ((pan.open_w.loc[X, tk] / pan.open_w.loc[E, tk] - 1) * 100).mean()
    assert m["univ_mean"] == pytest.approx(float(expect), rel=1e-9)


# ── BM-1: benchmark machinery (IHSG bias) ────────────────────────────────────────────

def test_bm1_placebo(clean):
    pan, cal, _ = clean
    s = synthetic.z_signal(pan.P)
    plac = engine.run_months(pan, engine.placebo_scores(pan, s, cal), CARD, cal)
    series = [m["primary"] for m in plac if m.get("valid")]
    assert checks.placebo(series)["status"] == "PASS"
    assert checks.placebo([1.0 + 0.1 * np.sin(i) for i in range(40)])["status"] == "FAIL"


# ── SPL-1: unadjusted corporate actions ──────────────────────────────────────────────

def _unadjusted_split(raw, ticker, from_date, ratio=5.0):
    """A split the data vendor never adjusted: price /ratio, volume *ratio (value unchanged)."""
    m = (raw.ticker == ticker) & (raw.date >= from_date)
    raw.loc[m, ["open", "high", "low", "close"]] /= ratio
    raw.loc[m, "volume"] *= ratio


def test_spl1_unadjusted_splits_in_holding_windows_invalidate():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=24)
    rng = np.random.default_rng(9)
    dates = list(pd.to_datetime(sorted(raw.date.unique())))
    for tk in [f"S{i:03d}" for i in range(60)]:
        _unadjusted_split(raw, tk, dates[int(rng.integers(60, len(dates) - 30))])
    pan = engine.Panel(raw)
    cal = engine.calendar(pan.P)
    months = engine.run_months(pan, synthetic.z_signal(pan.P), CARD, cal)
    r = checks.split_band(months)
    assert r["detail"]["holdings"] > 0 and r["status"] == "FAIL"


def test_spl1_data1_scale_contamination_now_fails():
    """Regression (validity audit 2026-09-24): DATA-1 left 0.38% of holdings with a >35%
    session and passed the old 0.5% bar. A comparable trace must now be INVALID."""
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=31)
    dates = list(pd.to_datetime(sorted(raw.date.unique())))
    for k, tk in enumerate(["S003", "S017", "S041"]):
        _unadjusted_split(raw, tk, dates[200 + 150 * k], ratio=1.6)   # -37.5% print, < 100%
    pan = engine.Panel(raw)
    months = engine.run_months(pan, synthetic.z_signal(pan.P), CARD, engine.calendar(pan.P))
    r = checks.split_band(months)
    d = r["detail"]
    assert d["holdings_with_big_move"] >= 1
    assert d["share"] <= 0.005, "fixture must be a trace the OLD threshold would have passed"
    assert d["max_abs_move"] < checks.IMPOSSIBLE_MOVE
    assert r["status"] == "FAIL"


def test_spl1_single_impossible_move_fails():
    """One +200% print (a split adjusted twice) in one holding invalidates the run even
    though the share of affected holdings is far below the bar."""
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=32)
    dates = list(pd.to_datetime(sorted(raw.date.unique())))
    _unadjusted_split(raw, "S010", dates[400], ratio=1.0 / 3.0)       # x3 jump = +200%
    pan = engine.Panel(raw)
    months = engine.run_months(pan, synthetic.z_signal(pan.P), CARD, engine.calendar(pan.P))
    r = checks.split_band(months)
    assert r["detail"]["share"] < checks.MAX_BIG_MOVE_SHARE
    assert r["detail"]["max_abs_move"] >= checks.IMPOSSIBLE_MOVE
    assert r["status"] == "FAIL"


def test_spl1_lookback_big_move_is_excluded_ex_ante():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=25)
    dates = list(pd.to_datetime(sorted(raw.date.unique())))
    d = engine.calendar(engine.prepare(raw))["formation"].iloc[15]
    _unadjusted_split(raw, "S001", dates[dates.index(d) - 5])
    pan = engine.Panel(raw)
    at_d = pan.P.index[(pan.P.ticker == "S001") & (pan.P.date == d)]
    assert not bool(pan.eligible.loc[at_d].iloc[0])


def test_clean_panel_passes_every_return_check(clean):
    pan, cal, _ = clean
    months = engine.run_months(pan, synthetic.z_signal(pan.P), CARD, cal)
    assert checks.forward_returns_nontrivial(months)["status"] == "PASS"
    assert checks.split_band(months)["status"] == "PASS"
    assert checks.entry_exit_order(months)["status"] == "PASS"


# ── ZV-2: market-wide carry-forward rows (pre-2021 backfill holidays) ────────────────

def _with_holidays(raw, holiday_dates):
    """Vendor-style holiday rows: every ticker prints the prior close with zero volume."""
    extra = []
    for d in holiday_dates:
        prev = raw[raw.date < d].groupby("ticker").tail(1).copy()
        prev["date"] = d
        for c in ("open", "high", "low"):
            prev[c] = prev["close"]
        prev["volume"] = 0.0
        extra.append(prev)
    return pd.concat([raw] + extra, ignore_index=True)


def test_zv2_holiday_rows_are_not_sessions():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=26)
    cal0 = engine.calendar(engine.prepare(raw))
    # a holiday on the calendar month-end and a 5-day holiday block mid-month
    me = pd.Timestamp("2016-06-30")
    block = list(pd.bdate_range("2016-09-12", "2016-09-16"))
    raw = raw[~raw.date.isin([me] + block)]              # the market was closed on those days
    hol = _with_holidays(raw, [me] + block)
    pan = engine.Panel(hol)
    assert set(pd.to_datetime(pan.non_sessions_dropped)) == {me, *block}
    cal = engine.calendar(pan.P)
    assert pd.Timestamp(cal.loc["2016-06", "formation"]) < me     # month-end moves to the last real session
    m = [x for x in engine.run_months(pan, synthetic.z_signal(pan.P), CARD, cal, with_returns=False)
         if x["month"] in ("2016-06", "2016-09")]
    assert all(x["valid"] for x in m)                              # universe not emptied
    assert len(cal0) >= len(cal) - 1


def test_zv2_real_session_with_a_volume_hole_is_kept():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=27)
    d = pd.Timestamp("2016-05-11")
    raw.loc[raw.date == d, "volume"] = 0.0                           # volume lost, prices still moved
    assert d not in set(engine.non_session_dates(engine.prepare(raw)))


def test_zv2_detection_is_prefix_invariant():
    raw = synthetic.make_panel(n_tickers=60, years=3, seed=28)
    block = list(pd.bdate_range("2016-09-12", "2016-09-16"))
    hol = _with_holidays(raw[~raw.date.isin(block)], block)
    full = set(engine.non_session_dates(engine.prepare(hol)))
    for cut in ("2016-09-14", "2016-09-16", "2017-03-01"):
        part = set(engine.non_session_dates(engine.prepare(hol[hol.date <= cut])))
        assert part == {d for d in full if d <= pd.Timestamp(cut)}
