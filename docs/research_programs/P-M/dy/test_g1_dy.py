"""Synthetic tests for g1_dy.py (HYP-PM-0024 G1). All data is synthetic; no real return is ever computed.

  venv/bin/python3 -m pytest -q docs/research_programs/P-M/dy/test_g1_dy.py
"""
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1_dy as g


def _month_ends(n, start=(2015, 1)):
    out, (y, m) = [], start
    for _ in range(n):
        nm = date(y + (m == 12), m % 12 + 1, 1)
        out.append(nm - timedelta(days=1))
        y, m = nm.year, nm.month
    return out


# ---- refusal: nothing is computed before the registration is pinned ----

def _boom(*a, **k):
    raise AssertionError("data was loaded before the pin check")


def test_refuses_unpinned(monkeypatch, capsys):
    monkeypatch.setattr(g, "REG_SHA256", None)
    monkeypatch.setattr(g.g0dy, "monthly_panel", _boom)
    monkeypatch.setattr(g, "load_daily", _boom)
    assert g.main() == 2
    assert capsys.readouterr().out.startswith("Registration not pinned or changed; refusing to run")


def test_refuses_changed_registration(monkeypatch):
    monkeypatch.setattr(g, "REG_SHA256", "0" * 64)
    monkeypatch.setattr(g.g0dy, "monthly_panel", _boom)
    assert g.main() == 2


# ---- building blocks ----

def test_book_weights_top_quintile_ew_and_floor():
    valid = [(f"T{i:02d}", float(i)) for i in range(50)]
    w = g.book_weights(valid)
    assert sorted(w) == [f"T{i:02d}" for i in range(40, 50)] and all(abs(v - 0.1) < 1e-12 for v in w.values())
    assert g.book_weights(valid[:29]) is None
    tie = [(f"T{i:02d}", 1.0) for i in range(30)]          # all tied: ticker order decides, deterministically
    assert sorted(g.book_weights(tie)) == [f"T{i:02d}" for i in range(24, 30)]
    vw = g.book_weights(valid, mcap={t: (2.0 if t == "T49" else 1.0) for t, _ in valid})
    assert abs(vw["T49"] - 2 / 11) < 1e-12


def test_park60_value_window_and_gaps():
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(70)]
    k = math.exp(0.02)
    bars = [(d, 100 * k, 100.0) for d in days] + [(date(2019, 12, 1), 0.0, 1.0), (date(2019, 12, 2), 1.0, 2.0)]
    idx = g.park60_index(bars)
    assert len(idx[0]) == 70                                   # the two invalid bars are skipped
    assert g.park60_at(idx, days[-1]) == pytest.approx(math.sqrt(0.0004 / (4 * math.log(2))))
    assert g.park60_at(idx, days[58]) is None                  # only 59 bars by then
    assert g.park60_at(idx, days[-1] + timedelta(days=11)) is None   # newest bar too stale
    assert g.park60_at(idx, days[-1] + timedelta(days=10)) is not None


def test_pct_ranks_average_ties():
    assert list(g.pct_ranks([3, 1, 1, 2])) == [1.0, 0.375, 0.375, 0.75]


# ---- known spread -> known t, end to end through run() ----

def test_known_spread_gives_known_t(monkeypatch):
    months = _month_ends(41)
    names = [f"T{i:02d}" for i in range(50)]
    a = [0.02 + 0.01 * math.cos(t) for t in range(40)]        # top-quintile excess per month
    c = [0.01 * math.sin(3 * t) for t in range(40)]           # common shock, cancels in the spread
    px = {n: 100.0 for n in names}
    ksei = {}
    for t, D in enumerate(months):
        ksei[D] = {n: (1000.0, px[n]) for n in names}
        if t < 40:
            for i, n in enumerate(names):
                px[n] *= 1 + c[t] + (a[t] if i >= 40 else 0.0)
    panel = {D: ksei[D] for D in months[:-1]}
    # TTM scaled by the month's market cap so each name's yield stays i + 1: book = T40..T49 every month
    monkeypatch.setattr(g.ex, "ttm_at", lambda s, D: s[D] if s else None)
    series = {n: {D: (i + 1) * ksei[D][n][0] * ksei[D][n][1] for D in months} for i, n in enumerate(names)}
    recs = g.run(panel, ksei, series, lambda t, D, m: 0.05, lambda t, D: 0.02)
    expected = [0.8 * a[t] - g.COST_RT * (1.0 if t == 0 else 0.0) for t in range(40)]
    got = [r["net"] for r in recs]
    assert len(got) == 40 and np.allclose(got, expected, atol=1e-12)
    out = g.summarise(recs)
    m, se, tt = g.g1fq.newey_west(expected, g.NW_LAGS)
    assert out["t"] == pytest.approx(tt) and out["mean_net_monthly"] == pytest.approx(m)
    assert recs[0]["turnover"] == 1.0 and all(r["turnover"] == 0 for r in recs[1:])
    assert out["half1_mean"] == pytest.approx(np.mean(expected[:20]))


# ---- kill rules ----

def _strong_fm(n=60, seed=1):
    return list(np.random.default_rng(seed).normal(0.01, 0.002, n))


def test_half_nonpositive_kills_even_with_a_high_t():
    rng = np.random.default_rng(7)
    net = list(rng.normal(-0.0005, 0.0001, 150)) + list(rng.normal(0.08, 0.001, 150))
    out = g.evaluate(net, _strong_fm(300))
    assert out["t"] >= g.BAR and out["fm_t"] >= 2
    assert out["passed"] is False and out["kill_reasons"] == ["half <= 0"]


def test_all_three_pass():
    rng = np.random.default_rng(3)
    out = g.evaluate(list(rng.normal(0.02, 0.01, 120)), _strong_fm(120))
    assert out["passed"] is True and out["kill_reasons"] == []


def _fm_rows(rng, n, driver):
    """One FM month. driver "ep": yield = E/P + a little noise (near-collinear) and the return loads on E/P's
    cross-sectional rank -- the exposure the registered FM controls for. driver "yield": yield independent of
    E/P and the return loads on yield's rank. (A return driven by RAW E/P levels is only partly absorbed by a
    rank control; that limitation of the registered rank FM is disclosed in the pin D-entry.)"""
    ep = rng.uniform(0.01, 0.2, n)
    y = ep + rng.normal(0, 0.002, n) if driver == "ep" else rng.uniform(0.01, 0.2, n)
    size = rng.normal(28, 1, n)
    park = rng.uniform(0.01, 0.05, n)
    volex = (park > np.quantile(park, 0.9)).astype(float)
    ret = 0.02 * g.pct_ranks(ep if driver == "ep" else y) + rng.normal(0, 0.01, n)
    return list(zip(ret, y, ep, size, park, volex))


def test_fm_collinear_with_ep_kills():
    rng = np.random.default_rng(11)
    coefs = [g.fm_coef(_fm_rows(rng, 60, "ep")) for _ in range(60)]
    rng2 = np.random.default_rng(12)
    out = g.evaluate(list(rng2.normal(0.02, 0.01, 60)), coefs)
    assert out["t"] >= g.BAR and out["half1_mean"] > 0 and out["half2_mean"] > 0
    assert out["fm_t"] < 2 and out["passed"] is False and out["kill_reasons"] == ["FM t < 2"]


def test_fm_exact_collinearity_gives_no_coefficient():
    rng = np.random.default_rng(5)
    rows = [(r, e, e, s, p, v) for r, _, e, s, p, v in _fm_rows(rng, 60, "ep")]   # yield == E/P exactly
    assert g.fm_coef(rows) is None


def test_fm_detects_a_real_increment_and_survives_a_constant_volex_column():
    rng = np.random.default_rng(13)
    coefs = []
    for _ in range(60):
        rows = [(r, y, e, s, p, 0.0) for r, y, e, s, p, _ in _fm_rows(rng, 60, "yield")]   # no VOLEX names
        coefs.append(g.fm_coef(rows))
    assert all(c is not None for c in coefs)
    m, se, t = g.g1fq.newey_west(coefs, g.NW_LAGS)
    assert t >= 2


def test_fm_too_few_names():
    rng = np.random.default_rng(2)
    assert g.fm_coef(_fm_rows(rng, 29, "yield")) is None
