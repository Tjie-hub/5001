"""Tests for docs/research_programs/P-M/validity_audit/validity_audit.py (descriptive audit).

The audit runs on the Owner's 14 GB DB, which the authoring session cannot reach, so every
section is exercised end-to-end here on a synthetic corpus with planted defects."""
import importlib.util
import json
import os

import numpy as np
import pandas as pd
import pytest

from research.rulecard import synthetic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "research_programs", "P-M", "validity_audit", "validity_audit.py")


@pytest.fixture(scope="module")
def VA():
    spec = importlib.util.spec_from_file_location("validity_audit", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rolling_slope_matches_polyfit(VA):
    rng = np.random.default_rng(3)
    y = pd.Series(np.cumsum(rng.normal(size=80)) + 100)
    got = VA.rolling_slope(y, 20)
    for end in (19, 40, 79):
        want = np.polyfit(np.arange(20), y.iloc[end - 19:end + 1].values, 1)[0]
        assert got.iloc[end] == pytest.approx(want, rel=1e-9, abs=1e-12)
    assert got.iloc[:19].isna().all()


def test_window_has_event_start_exclusive_end_inclusive(VA):
    d = pd.to_datetime
    starts = d(["2024-01-02", "2024-01-02", "2024-01-05", "2024-01-10"])
    ends = d(["2024-01-05", "2024-01-04", "2024-01-09", "2024-01-20"])
    ev = d(["2024-01-02", "2024-01-05"])
    # event on the entry date is not inside (price already on the new basis); on exit it is
    assert VA.window_has_event(starts, ends, ev).tolist() == [True, False, False, False]
    assert not VA.window_has_event(starts, ends, []).any()


def test_calendar_time_vec_matches_reference_loop(VA):
    OA = VA._oa()
    rng = np.random.default_rng(5)
    n_days, n_names, h = 120, 15, 5
    CO, CC = rng.normal(0, .01, (n_days, n_names)), rng.normal(0, .01, (n_days, n_names))
    CC[rng.random(CC.shape) < 0.03] = np.nan
    bco, bcc = rng.normal(0, .005, n_days), rng.normal(0, .005, n_days)
    e, c = rng.integers(0, n_days - 2, 60), rng.integers(0, n_names, 60)
    pos = []
    for ei, ci in zip(e, c):
        k = min(h, n_days - ei)
        pos.append((ei, np.r_[CO[ei, ci], CC[ei + 1:ei + k, ci]], np.r_[bco[ei], bcc[ei + 1:ei + k]]))
    want = OA.calendar_time(None, pos, n_days)
    got = VA.calendar_time_vec(n_days, e, c, h, CO, CC, bco, bcc)
    assert got[0] == pytest.approx(want[0]) and got[1] == pytest.approx(want[1]) and got[2] == want[2]


def _corpus(VA):
    raw = synthetic.make_panel(n_tickers=40, years=2, seed=11, start="2024-01-01").drop(columns="z")
    dates = pd.DatetimeIndex(sorted(raw.date.unique()))
    # planted: an unadjusted 1.6:1 split on S001, a -20% rights-issue ex-date on S002,
    # a >35% jump on S003 with no recorded cause, a zero-volume day on S004
    split_d, rights_d, jump_d = dates[200], dates[260], dates[300]
    m = (raw.ticker == "S001") & (raw.date >= split_d)
    raw.loc[m, ["open", "high", "low", "close"]] /= 1.6
    m = (raw.ticker == "S002") & (raw.date >= rights_d)
    raw.loc[m, ["open", "high", "low", "close"]] *= 0.8
    m = (raw.ticker == "S003") & (raw.date >= jump_d)
    raw.loc[m, ["open", "high", "low", "close"]] *= 1.5
    raw.loc[(raw.ticker == "S004") & (raw.date == dates[150]), "volume"] = 0
    ih = raw.groupby("date")[["open", "high", "low", "close"]].mean().reset_index()
    ih["ticker"], ih["volume"] = "IHSG", 1e12
    D = pd.concat([raw, ih[raw.columns]], ignore_index=True).sort_values(["ticker", "date"]).reset_index(drop=True)
    x = {"is_final": pd.DataFrame({"is_final": [1], "n": [len(D)]}),
         "ca": pd.DataFrame({"ticker": ["S001"], "date": [str(split_d.date())], "action": ["split"], "value": [1.6]}),
         "cae": pd.DataFrame({"ticker": ["S002", "S002"], "action_type": ["rightissue", "dividend"],
                              "event_id": ["1", "2"], "event_date": [str(rights_d.date()), str(dates[100].date())],
                              "raw_json": [json.dumps({"rightissue_ratio": "1:4", "rightissue_price": 500}),
                                           json.dumps({"dividend_value": 10})]}),
         "su": pd.DataFrame(columns=["ticker", "last_normal_date", "resume_date"])}
    return D, x, (split_d, rights_d, jump_d)


def test_classify_big_moves_labels_planted_causes(VA):
    D, x, (split_d, rights_d, jump_d) = _corpus(VA)
    P = D[D.ticker != "IHSG"][["ticker", "date", "close", "volume"]]
    B = VA.classify_big_moves(P, VA.event_frames(x), 0.15)
    lab = {(r.ticker, r.date): r.cls for r in B.itertuples()}
    assert lab[("S001", split_d)] == "split"
    assert lab[("S002", rights_d)] == "rightissue"
    assert lab[("S003", jump_d)] == "unmatched"


def test_every_section_runs_on_a_synthetic_corpus(VA):
    """Smoke: A-F end to end, including the T1 replication assert against overlap_audit."""
    D, x, _ = _corpus(VA)
    OA = VA._oa()
    A = VA.section_a(D, x)
    assert A["tickers"] == 40 and A["n_sessions_missing_ihsg"] == 0
    B = VA.section_b(D)
    assert B["stopped_more_than_60_sessions_before_end"] == 0
    C = VA.section_c(D, x)
    assert C["all"]["by_class"].get("split") == 1 and C["all"]["by_class"].get("unmatched") == 1
    assert C["split_continuity"]["gapped_in_db"] == 1
    Dd = VA.section_d(D, x)
    assert Dd["rightissue"]["matched_bars"] == 1 and Dd["rightissue"]["median"] < -0.15
    assert "rightissue_ratio" in Dd["rightissue"]["raw_json_keys"]
    M = VA.fade_panel(D, x, OA)
    E = VA.section_e(D, x, OA, M)
    assert set(E["fade"]) == {"h5", "h20"} and "kept" in E["t1"]
    F = VA.section_f(D, x, OA, M)
    assert {r["arm"] for r in F} >= {"P2 resistance breakout", "P3a failed breakdown"}
    for r in F:
        # the registered endpoint is the gross contrast minus the 0.60% round trip
        assert r["net%_registered_endpoint"] == pytest.approx(r["gross%"] - 0.6, abs=2e-3)
