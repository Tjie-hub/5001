"""Tests for the PEAD G0 scripts in docs/research_programs/P-M/pead/ (synthetic inputs only).

g0_pead_power.py must never read a return inside [E-11, E+60]; test_placebo_never_reads_event_window poisons
that span and checks the placebo values are unchanged. pead_data_checks.py works on EPS and dates only."""
import importlib.util
import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "docs", "research_programs", "P-M", "pead")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(DIR, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def G():
    return _load("g0_pead_power")


@pytest.fixture(scope="module")
def DC():
    return _load("pead_data_checks")


CAL = pd.bdate_range("2019-01-01", periods=900)


# ---------------------------------------------------------------- g0_pead_power

def test_event_index_cutoff(G):
    d = CAL[10]
    assert G.event_index(CAL, d + pd.Timedelta(hours=11)) == 10        # morning -> same session
    assert G.event_index(CAL, d + pd.Timedelta(hours=16)) == 11        # 16:00 -> next session
    sat = pd.Timestamp("2019-01-05 10:00")                              # weekend -> next session
    assert CAL[G.event_index(CAL, sat)] == pd.Timestamp("2019-01-07")
    assert G.event_index(CAL, CAL[-1] + pd.Timedelta(days=3)) is None


def test_to_wib(G):
    assert G.to_wib("2026-04-30 05:00:00-04:00") == pd.Timestamp("2026-04-30 16:00")


def test_era_bounds(G):
    assert G.era_of(pd.Timestamp("2009-03-31")) is None
    assert G.era_of(pd.Timestamp("2009-04-01")) == "holdout"
    assert G.era_of(pd.Timestamp("2021-07-02")) == "holdout"
    assert G.era_of(pd.Timestamp("2021-07-05")) == "recent"
    assert G.era_of(G.CUT + pd.Timedelta(days=1)) is None


def test_sue(G):
    assert G.sue(12.0, 10.0, 1000.0) == pytest.approx(0.002)
    assert G.sue(1.0, 1.0, 0.0) is None
    assert G.sue(1.0, 1.0, float("nan")) is None


def test_dedupe_keeps_first(G):
    ev = pd.DataFrame({"ticker": ["A", "A", "A", "B"],
                       "ann_wib": pd.to_datetime(["2020-01-01", "2020-01-10", "2020-03-01", "2020-01-05"]),
                       "est": 1.0, "rep": 1.0})
    out, n = G.dedupe(ev)
    assert n == 1
    assert list(out["ann_wib"].dt.strftime("%m-%d")[out["ticker"] == "A"]) == ["01-01", "03-01"]


def test_top_quintile_within_quarter(G):
    E = pd.to_datetime(["2020-01-15"] * 10 + ["2020-04-15"] * 5)
    ev = pd.DataFrame({"E": E, "sue": list(range(10)) + [1, 2, 3, 4, 5]})
    flag, audit = G.top_quintile(ev)
    assert flag.iloc[:10].sum() == 2 and flag.iloc[8] == 1 and flag.iloc[9] == 1
    assert flag.iloc[10:].isna().all() and audit["events_in_small_quarters"] == 5


def test_power_and_mde(G):
    assert G.power_one_sided(0.02, 0.02, 3.3001) == pytest.approx(G.norm_cdf(1 - 3.3001))
    assert G.mde80(0.01, 3.3001) == pytest.approx(0.041417, rel=1e-4)


def test_cluster_se(G):
    v = pd.Series([1.0, 3.0, 2.0, 4.0, 6.0])
    m = pd.Series(["a", "a", "b", "c", "c"])
    se, k = G.cluster_se(v, m)          # month means 2, 2, 5
    assert k == 3 and se == pytest.approx(np.std([2, 2, 5], ddof=1) / np.sqrt(3))


def test_window_excess_coverage(G):
    d = CAL[:10]
    r = pd.Series(0.01, index=d)
    b = pd.Series(0.0, index=d)
    assert G.window_excess(r, b, d) == pytest.approx(1.01 ** 10 - 1)
    assert G.window_excess(r.iloc[:7], b, d) is None


def test_ksei_rank_asof_strictly_before(G):
    k = pd.DataFrame({"ticker": ["A", "A"], "date": pd.to_datetime(["2020-01-31", "2020-02-28"]),
                      "rk": [5.0, 7.0], "mcap": [1e12, 2e12]})
    assert G.ksei_rank_asof(k, "A", pd.Timestamp("2020-02-28")) == (5.0, 1e12)
    assert G.ksei_rank_asof(k, "A", pd.Timestamp("2020-03-02")) == (7.0, 2e12)
    assert G.ksei_rank_asof(k, "A", pd.Timestamp("2020-01-31")) == (None, None)


def test_trailing_features_are_prefix_invariant(G):
    rng = np.random.default_rng(0)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400))))
    h, lo = c * 1.01, c * 0.99
    full = pd.DataFrame({"t1": G.t1_state(c), "pk": G.parkinson60(h, lo), "hi": G.hi52(c, h)})
    part = pd.DataFrame({"t1": G.t1_state(c[:300]), "pk": G.parkinson60(h[:300], lo[:300]),
                         "hi": G.hi52(c[:300], h[:300])})
    pd.testing.assert_frame_equal(full.iloc[:300], part)
    assert G.parkinson60(h, lo).dropna().iloc[-1] == pytest.approx(np.log(1.01 / 0.99) / np.sqrt(4 * np.log(2)))


def test_placebo_never_reads_event_window(G):
    rng = np.random.default_rng(1)
    tick = ["A", "B", "C"]
    ret = pd.DataFrame(rng.normal(0, 0.02, (len(CAL), 3)), index=CAL, columns=tick)
    book = pd.Series(rng.normal(0, 0.01, len(CAL)), index=CAL)
    ev = pd.DataFrame({"ticker": tick, "e_i": [200, 400, 600], "top_q": [1.0, 1.0, 1.0],
                       "E": CAL[[200, 400, 600]], "era": ["holdout"] * 3})
    v1, *_ = G.placebo_values(ev, CAL, SimpleNamespace(ret_w=ret), book)
    poisoned = ret.copy()
    for t, e in zip(tick, ev["e_i"]):
        poisoned.iloc[e - 11:e + G.WIN_END + 1, poisoned.columns.get_loc(t)] = 10.0
    v2, *_ = G.placebo_values(ev, CAL, SimpleNamespace(ret_w=poisoned), book)
    pd.testing.assert_series_equal(v1, v2)
    assert G.PLACEBO[1] < -11 and G.PLACEBO[1] - G.PLACEBO[0] + 1 == G.WIN_END - G.WIN_START + 1


def test_pipeline_end_to_end_on_synthetic_panel(G):
    """characteristics -> build_events -> distinctness -> placebo -> g0_stats on the real engine.Panel."""
    import sys
    sys.path.insert(0, ROOT)
    from research.rulecard import engine, events
    rng = np.random.default_rng(7)
    cal = pd.bdate_range("2012-01-02", periods=700)
    tick = [f"T{i:02d}" for i in range(60)]
    rows = []
    for t in tick:
        c = 1000 * np.exp(np.cumsum(rng.normal(0, 0.015, len(cal))))
        rows.append(pd.DataFrame({"ticker": t, "date": cal, "open": c, "high": c * 1.01, "low": c * 0.99,
                                  "close": c, "volume": 5e6}))
    pan = engine.Panel(pd.concat(rows, ignore_index=True))
    book, _ = events._book(pan)
    book = pd.Series(np.asarray(book.values, dtype=float), index=pd.to_datetime(book.index))
    pcal = pd.DatetimeIndex(np.sort(pd.to_datetime(pan.P["date"]).unique()))
    C = G.characteristics(pan)
    assert {"hi52", "park60", "t1", "hi52_pct"} <= set(C.columns)
    # quarterly announcements from session 300 on, 11:00 WIB (= 00:00 New York)
    earn = {t: [{"ts": f"{d.date()} 00:00:00-04:00", "est": 10.0, "rep": float(10 + rng.normal(0, 2))}
                for d in pcal[300:680:63]] for t in tick}
    ksei = pd.DataFrame([{"date": d, "ticker": t, "sec_num": 1e9, "price": 1000.0 + i}
                         for d in pd.date_range("2012-01-31", periods=34, freq="ME") for i, t in enumerate(tick)])
    ksei["mcap"] = ksei["sec_num"] * ksei["price"]
    ksei["rk"] = ksei.groupby("date")["mcap"].rank(ascending=False, method="first")
    ev, counts = G.build_events(earn, ksei.sort_values(["ticker", "date"]), pcal, C)
    assert counts["eligible_events"] > 0 and counts["top_quintile_events"] > 0
    assert (ev["E"] - ev["ann_wib"].dt.normalize()).dt.days.max() <= 3
    d = G.distinctness(ev)
    assert set(d) >= {"hi52", "park60", "log_mcap", "t1"}
    vals, months, eras, short = G.placebo_values(ev, pcal, pan, book)
    s = G.g0_stats(vals, months)
    assert s["events_with_placebo"] == len(vals) > 0 and "power_at_floor" in s
    assert not any("mean" in k for k in s)                       # no window mean is ever reported


def test_main_refuses_changed_freeze(G, capsys, monkeypatch, tmp_path):
    # never let the suite reach a real run: point at a scratch freeze whose hash cannot match
    f = tmp_path / "freeze.md"
    f.write_text("edited")
    monkeypatch.setattr(G, "FREEZE", f)
    assert G.main(["--force"]) == 2
    assert "REFUSED" in capsys.readouterr().out


# ---------------------------------------------------------------- pead_data_checks

def test_fiscal_period(DC):
    assert DC.fiscal_period(pd.Timestamp("2020-03-20")) == (2019, "FY")
    assert DC.fiscal_period(pd.Timestamp("2020-04-30")) == (2020, "Q1")
    assert DC.fiscal_period(pd.Timestamp("2020-07-30")) == (2020, "H1")
    assert DC.fiscal_period(pd.Timestamp("2020-10-30")) == (2020, "9M")


def _earn(rows):
    return {"A": [{"ts": ts, "est": e, "rep": r} for ts, e, r in rows]}


def test_basis_check_detects_ytd_mismatch(DC):
    # consensus single-quarter 10, reported cumulative 10/20/30/40
    E = DC.events_frame(_earn([("2020-04-28 10:00:00+07:00", 10, 10), ("2020-07-28 10:00:00+07:00", 10, 20),
                               ("2020-10-28 10:00:00+07:00", 10, 30), ("2021-03-20 10:00:00+07:00", 10, 40)]))
    b = DC.basis_check(E)
    assert b["median_rep_over_est"]["9M"] == pytest.approx(3.0)
    assert b["median_abs_rep_vs_same_year_Q1"]["H1"] == pytest.approx(2.0)


def test_split_check_restated_vs_not(DC):
    pre = [(f"2019-{m:02d}-15 10:00:00+07:00", 10, 10) for m in (2, 5, 8, 11)]
    post_restated = [(f"2020-{m:02d}-15 10:00:00+07:00", 10, 10) for m in (2, 5, 8, 11)]
    post_raw = [(f"2020-{m:02d}-15 10:00:00+07:00", 2, 2) for m in (2, 5, 8, 11)]
    spl = pd.DataFrame({"ticker": ["A"], "date": [pd.Timestamp("2020-01-01")], "ratio": [5.0]})
    a = DC.split_check(DC.events_frame(_earn(pre + post_restated)), spl)
    b = DC.split_check(DC.events_frame(_earn(pre + post_raw)), spl)
    assert a["share_factor_ge2_closer_to_1_than_factor"] == 1.0
    assert b["share_factor_ge2_closer_to_1_than_factor"] == 0.0


def test_duplicate_and_consensus_checks(DC):
    E = DC.events_frame(_earn([("2020-04-28 10:00:00+07:00", 10, 10), ("2020-05-05 10:00:00+07:00", None, 11),
                               ("2020-07-28 10:00:00+07:00", 10, 12)]))
    assert DC.duplicate_check(E)["rows_within_days_of_previous"] == 1
    c = DC.consensus_check(E)
    assert c["est_missing"] == 1 and c["usable"] == 2 and c["est_equals_rep"] == 1
