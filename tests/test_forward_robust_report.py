"""Tests for docs/research_programs/P-M/forward_robust/robust_report.py (observability only, D-057).

The report reads the frozen REGIME-002 / FADE-001 ledgers; these tests use synthetic ledgers in the
ledgers' own schemas, so they never depend on (or touch) live forward-test state."""
import importlib.util
import os

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "research_programs", "P-M", "forward_robust", "robust_report.py")


@pytest.fixture(scope="module")
def RR():
    spec = importlib.util.spec_from_file_location("robust_report", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CAL = pd.bdate_range("2026-09-18", periods=400)


def _fade_ledger(n=120, seed=1, censored_every=10):
    rng = np.random.default_rng(seed)
    trades = []
    for k in range(n):
        i = int(rng.integers(0, 300))
        g, ih, ew = rng.normal(-0.005, 0.08), rng.normal(0.0, 0.04), rng.normal(0.0, 0.03)
        net = g - 0.006
        leg = {"exit_date": str(CAL[i + 21].date()), "exit_close": 1.0, "gross_return": g,
               "net_return": net, "ihsg_return": ih, "excess_ihsg": net - ih,
               "ewbook_return": ew, "excess_ewbook": net - ew}
        trades.append({"ticker": f"T{k % 40:02d}", "signal_date": str(CAL[i].date()),
                       "entry_date": str(CAL[i + 1].date()), "entry_open": 1.0,
                       "horizons": {"5": leg, "10": leg, "20": leg},
                       "censored": (k % censored_every == 0)})
    trades.append({"ticker": "X", "signal_date": "2026-09-18", "entry_date": "2026-09-21",
                   "entry_open": 1.0, "horizons": {"5": {}}, "censored": False})   # no h20 leg yet
    return {"spec_id": "FWD-PM-FADE-001", "trades": trades}


def _regime_ledger(n=80, seed=2):
    rng = np.random.default_rng(seed)
    trades = []
    for k in range(n):
        i = int(rng.integers(0, 300))
        hold = int(rng.integers(3, 60))
        net, mkt = rng.normal(0.01, 0.1), rng.normal(0.0, 0.05)
        trades.append({"ticker": f"R{k % 30:02d}", "entry_date": str(CAL[i].date()),
                       "exit_date": str(CAL[i + hold].date()), "sessions_held": hold,
                       "net_return": net, "market_return": mkt, "excess": net - mkt})
    return {"spec_id": "FWD-PM-REGIME-002", "trades": trades}


def test_fade_frame_drops_censored_and_open_legs(RR):
    F = RR.fade_frame(_fade_ledger())
    assert len(F) == 120 - 12            # every 10th censored; the open-leg row is skipped
    assert F.signal_date.lt(F.entry_date).all()


def test_frozen_column_is_the_protocol_cluster_t(RR):
    oa = RR.OA()
    T = RR.regime_frame(_regime_ledger())
    e = RR.estimators(T.excess, T.entry_date, CAL, RR.REGIME_L, oa)
    assert e["t_frozen"] == pytest.approx(oa.cluster_t(T.excess.values, T.entry_date.values)[1])
    months = T.entry_date.dt.to_period("M").astype(str).values
    assert e["t_month"] == pytest.approx(oa.cluster_t(T.excess.values, months)[1])
    assert "t_dk_L60" in e and np.isfinite(e["t_dk_L60"])


def test_too_few_rows_report_no_t(RR):
    T = RR.regime_frame(_regime_ledger(n=12))
    e = RR.estimators(T.excess, T.entry_date, CAL, RR.REGIME_L)
    assert "note" in e and "t_frozen" not in e


def test_fade_gross_differs_from_frozen_net_by_exactly_the_one_leg_cost(RR):
    rep = RR.report_fade(_fade_ledger(), CAL)
    for b in ("IHSG", "EW-book"):
        gross, net = rep[f"{b} GROSS (no-information null = 0)"], rep[f"{b} net (frozen endpoint)"]
        assert gross["mean_pct"] - net["mean_pct"] == pytest.approx(0.6, abs=1e-9)
        assert gross["N"] == net["N"] == 108


def test_empty_ledgers_report_nothing(RR):
    assert RR.report_regime({"trades": []}, CAL)["trades"] == 0
    assert RR.report_fade({"trades": []}, CAL)["signals_h20"] == 0


def test_calendar_positions_use_the_right_windows(RR):
    n_days, n_names = 30, 3
    rng = np.random.default_rng(4)
    cal = pd.bdate_range("2026-10-01", periods=n_days)
    M = {"cal": cal, "cpos": {t: i for i, t in enumerate(cal)}, "tcol": {"A": 0, "B": 1, "C": 2},
         "CC": rng.normal(0, .01, (n_days, n_names)), "CO": rng.normal(0, .01, (n_days, n_names)),
         "ih_cc": rng.normal(0, .005, n_days), "ih_co": rng.normal(0, .005, n_days),
         "ew_cc": rng.normal(0, .005, n_days), "ew_co": rng.normal(0, .005, n_days)}
    T = pd.DataFrame({"ticker": ["A"], "entry_date": [cal[2]], "exit_date": [cal[7]]})
    (s, r, b), = RR.regime_positions(T, M)
    assert s == 3 and len(r) == 5 and r[0] == M["CC"][3, 0] and b[-1] == M["ih_cc"][7]
    F = pd.DataFrame({"ticker": ["B"], "entry_date": [cal[5]]})
    (s, r, b), = RR.fade_positions(F, M, "EW-book", h=20)
    assert s == 5 and len(r) == 20 and r[0] == M["CO"][5, 1] and b[0] == M["ew_co"][5]
    assert r[1] == M["CC"][6, 1] and b[19] == M["ew_cc"][24]


def test_modeled_cost_column_is_gross_minus_model_minus_market(RR):
    """DEV-002 (D-059): the modeled-cost excess is gross - (fees + 1/2 s_in + 1/2 s_out
    + 2 sigma sqrt(Q/adv20)) - market; it sits beside the frozen column and never replaces it."""
    led = _regime_ledger(n=40)
    for t in led["trades"]:
        t["gross_return"] = t["net_return"] + 0.006
    T = RR.regime_frame(led)
    rows = []
    for t in T.itertuples():
        rows.append({"ticker": t.ticker, "date": t.entry_date, "s": 0.011, "sig_d": 0.02, "adv20": 4e9})
        rows.append({"ticker": t.ticker, "date": t.exit_date, "s": 0.011, "sig_d": 0.02, "adv20": 4e9})
    L = pd.DataFrame(rows).drop_duplicates(["ticker", "date"])
    cost = RR.modeled_cost(T, L)
    want = 0.005 + 0.011 + 2 * 0.02 * np.sqrt(100e6 / 4e9)
    assert np.allclose(cost.dropna(), want)
    rep = RR.report_regime(led, CAL, L=L)
    k = "excess (modeled cost D-059, vs IHSG) - observability"
    assert k in rep and "excess (net, vs IHSG) - frozen endpoint" in rep
    x = (T.gross_return - cost - T.market_return).dropna()
    assert rep[k]["mean_pct"] == pytest.approx(100 * x.mean())
