"""Tests for the {FQ} E/P G1 script in docs/research_programs/P-M/fq/ (synthetic inputs only).

g1_fq_ep.py must refuse to run before registration; its split rule, delisting handling, mechanical-drop screen,
tercile formation and Newey-West statistic are checked on hand-built panels with known answers."""
import calendar
import importlib.util
import os
from datetime import date

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "research_programs", "P-M", "fq", "g1_fq_ep.py")


@pytest.fixture(scope="module")
def G1():
    spec = importlib.util.spec_from_file_location("g1_fq_ep", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("p0,s0,p1,s1,expected", [
    (1000, 100, 1100, 100, 0.10),          # plain move
    (1000, 100, 500, 200, 0.0),            # 2:1 split
    (1000, 100, 10000, 10, 0.0),           # 1:10 consolidation
    (1000, 100, 1000, 160, 0.0),           # issuance: share count up, price flat -> not a split
    (1000, 100, 650, 160, -0.35),          # issuance with a real fall: not treated as a split
    (0, 100, 1000, 100, None),
])
def test_split_adjusted_return(G1, p0, s0, p1, s1, expected):
    r = G1.split_adjusted_return(p0, s0, p1, s1)
    assert (r is None) if expected is None else r == pytest.approx(expected)


def test_newey_west_zero_lags_is_iid_se(G1):
    x = np.array([0.01, -0.02, 0.03, 0.00, 0.02])
    m, se, t = G1.newey_west(x, lags=0)
    assert m == pytest.approx(x.mean())
    assert se == pytest.approx(x.std() / np.sqrt(len(x)))
    assert t == pytest.approx(m / se)


def test_newey_west_positive_autocorrelation_widens_se(G1):
    x = np.concatenate([np.full(20, 0.02), np.full(20, -0.01)])   # long runs -> positive autocorrelation
    assert G1.newey_west(x, 6)[1] > G1.newey_west(x, 0)[1]


def test_leg_return_delisting_and_mechanical_drop(G1):
    w = {"AAAA": 0.5, "BBBB": 0.25, "CCCC": 0.25}
    d = {"AAAA": (100, 1000.0), "BBBB": (100, 1000.0), "CCCC": (100, 1000.0)}
    n = {"AAAA": (100, 1100.0), "CCCC": (100, 10.0)}           # BBBB delisted, CCCC -99%
    r, dropped = G1.leg_return(w, d, n)
    assert dropped == ["CCCC"]
    assert r == pytest.approx((0.5 * 0.10 + 0.25 * 0.0) / 0.75)
    r100, _ = G1.leg_return(w, d, n, delist_minus100=True)
    assert r100 == pytest.approx((0.5 * 0.10 + 0.25 * -1.0) / 0.75)


def test_leg_return_lists_split_adjusted_names(G1):
    sp = []
    r, _ = G1.leg_return({"AAAA": 1.0}, {"AAAA": (100, 1000.0)}, {"AAAA": (200, 520.0)}, splits=sp)
    assert sp == ["AAAA"] and r == pytest.approx(0.04)


def test_turnover(G1):
    assert G1.turnover({"A": 0.5, "B": 0.5}, {"A": 0.5, "C": 0.5}) == pytest.approx(0.5)
    assert G1.turnover({}, {"A": 1.0}) == pytest.approx(0.5)


# ---------------------------------------------------------------- end to end on a known panel

def _eom(y, m):
    return date(y, m, calendar.monthrange(y, m)[1])


NAMES = [f"{chr(65 + i // 26)}{chr(65 + i % 26)}AA" for i in range(30)]
HIGH = set(NAMES[:10])                                  # big earners: high E/P, +2%/month


def _panel():
    by, px = {}, {t: 100.0 for t in NAMES}
    for y in (2008, 2009, 2010):
        for m in range(1, 13):
            by[_eom(y, m)] = {t: (1000.0, px[t]) for t in NAMES}
            for t in HIGH:
                px[t] *= 1.02
            for t in NAMES:
                if t not in HIGH:
                    px[t] += 0.01 * (1 + NAMES.index(t))   # tiny drift so no name trips the stale filter
    return by


def _fin():
    fin = {}
    for t in NAMES:
        ni = 50.0 if t in HIGH else 1.0 + 0.1 * NAMES.index(t)
        qs = {}
        for y in (2007, 2008, 2009, 2010):
            for m in (3, 6, 9, 12):
                pe = _eom(y, m)
                qs[pe] = {"ni": ni, "ccy": "IDR", "rate": 1.0, "vendor_r": None, "equity": 1000.0,
                          "deadline": None if y == 2010 and m == 12 else
                          {3: date(y, 4, 30), 6: date(y, 9, 30), 9: date(y, 10, 31), 12: date(y + 1, 3, 31)}[m],
                          "withheld": False}
        fin[t] = qs
    return fin


def test_run_variant_recovers_known_premium(G1, monkeypatch):
    monkeypatch.setattr(G1.G0, "FIRST_D", (2009, 1))
    monkeypatch.setattr(G1.G0, "LAST_D", (2010, 11))
    res = G1.run_variant(_panel(), _fin())
    assert res["n_months"] >= 20
    assert res["mean_monthly"] == pytest.approx(0.02, abs=2e-3)   # high leg +2%, low leg ~0
    assert res["t"] > 10
    assert all(nh == 10 and nl == 10 for _, nh, nl in res["legs"])


def test_formation_ignores_next_month_prices(G1, monkeypatch):
    monkeypatch.setattr(G1.G0, "FIRST_D", (2009, 6))
    monkeypatch.setattr(G1.G0, "LAST_D", (2009, 6))
    by = _panel()
    D = date(2009, 6, 30)
    fin = _fin()
    dates = sorted(by)
    kdate = {(d.year, d.month): d for d in dates}
    for qs in fin.values():
        for q in qs.values():
            q["qual"] = G1.G0.first_qualifying(q["deadline"], kdate) if q["deadline"] else None
    i = dates.index(D)
    uni = G1.G0.universe_at(by[D], by[dates[i - 1]], by[dates[i - 2]])
    a = G1.form(D, uni, fin)
    by[dates[i + 1]] = {t: (s * 3, p * 50) for t, (s, p) in by[dates[i + 1]].items()}
    uni2 = G1.G0.universe_at(by[D], by[dates[i - 1]], by[dates[i - 2]])
    assert G1.form(D, uni2, fin) == a
    assert set(a[0]) == HIGH


def test_main_refuses_until_registered(G1):
    assert G1.REG_SHA256 is None
    assert G1.main([]) == 2
