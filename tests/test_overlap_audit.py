"""Overlap-inference audit (docs/research_programs/P-M/overlap_audit/overlap_audit.py).

Two properties the audit relies on, shown on synthetic data (no DB):
1. With 20-session holds entered daily, a one-way ENTRY-DATE cluster t rejects a true null far
   more often than its nominal 5%; the calendar-time portfolio stays close to nominal.
2. FADE-001's registered endpoint subtracts the 0.60% round trip from the signal leg only, so a
   pattern carrying no information at all scores a strongly "significant" negative excess.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "research_programs" / "P-M" / "overlap_audit" / "overlap_audit.py"
FADE = ROOT / "docs" / "research_programs" / "P-M" / "forward_fade" / "scripts" / "fade_failed_breakdown.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def oa():
    return _load(AUDIT, "overlap_audit")


def test_dk_lag0_is_the_registered_estimator(oa):
    x, dates, cal, _ = oa.simulate_null(n_days=300, seed=3)
    G = pd.Series(dates).nunique()
    assert oa.dk_t(x, dates, cal, 0)[1] / np.sqrt(G / (G - 1)) == pytest.approx(oa.cluster_t(x, dates)[1])


def test_entry_date_clustering_overrejects_a_true_null(oa):
    reg = cal = 0
    for seed in range(20):
        x, dates, c, pos = oa.simulate_null(n_days=600, seed=seed)
        reg += abs(oa.cluster_t(x, dates)[1]) > 1.96
        cal += abs(oa.calendar_time(c, pos, len(c))[1]) > 1.96
    assert reg >= 5 and cal <= 3          # 200-seed calibration: 41% vs 7% at nominal 5%


@pytest.mark.skipif(not FADE.exists(), reason="frozen FADE script not present")
def test_net_of_cost_endpoint_scores_a_no_information_pattern_as_an_anti_edge(oa):
    from research.rulecard import synthetic
    F = _load(FADE, "fade_frozen")
    d = synthetic.make_panel(n_tickers=80, years=3, seed=5).drop(columns="z")
    d["volume"] *= 5                                           # every name clears the Rp 1 bn floor
    d = F.build(d.sort_values(["ticker", "date"]).reset_index(drop=True),
                pd.DataFrame(columns=["ticker", "date", "is_split"]))
    sig = d[d.liq & (d.low < d.lo20) & (d.close > d.lo20) & d.entry_open.notna()]
    s = sig[sig.exit_close_5.notna() & (sig.bad_5.fillna(1) == 0)]
    ewb = d[d.liq].groupby("date")["fwd_open_5"].mean()
    stock = s.exit_close_5 / s.entry_open - 1
    bench = s.date.map(ewb)
    net = F.cluster_t((stock - F.COST - bench).values, s.date.values)
    gross = F.cluster_t((stock - bench).values, s.date.values)
    assert net[0] == pytest.approx(-F.COST, abs=0.002) and net[1] < -5     # "anti-edge" from noise
    assert abs(gross[1]) < 3                                                # the real null
