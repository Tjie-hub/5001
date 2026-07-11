"""Tests for research/statistics.py (audit R-6). Hand-verified expected values;
determinism (seed) is asserted explicitly."""
import math

import numpy as np
import pytest

from research import statistics as st


# ─── bootstrap_ci ─────────────────────────────────────────────────────────────

def test_bootstrap_ci_constant_series_is_degenerate():
    r = st.bootstrap_ci([5.0] * 50)
    assert r["point"] == 5.0 and r["lo"] == 5.0 and r["hi"] == 5.0 and r["se"] == 0.0


def test_bootstrap_ci_brackets_mean_and_orders():
    x = list(range(100))
    r = st.bootstrap_ci(x)
    assert r["lo"] < r["point"] < r["hi"]
    assert r["point"] == pytest.approx(np.mean(x))
    assert r["n"] == 100


def test_bootstrap_ci_is_deterministic_for_seed():
    x = np.sin(np.arange(200)).tolist()
    a = st.bootstrap_ci(x, seed=123)
    b = st.bootstrap_ci(x, seed=123)
    assert a == b                      # byte-identical
    c = st.bootstrap_ci(x, seed=456)
    assert (a["lo"], a["hi"]) != (c["lo"], c["hi"])   # different seed => different draw


def test_bootstrap_ci_empty_and_singleton():
    e = st.bootstrap_ci([])
    assert math.isnan(e["point"]) and e["n"] == 0
    s = st.bootstrap_ci([3.3])
    assert s["point"] == 3.3 and s["lo"] == 3.3 and s["hi"] == 3.3 and s["n"] == 1


def test_bootstrap_ci_width_narrows_with_n():
    rng = np.random.default_rng(0)
    small = st.bootstrap_ci(rng.normal(0, 1, 30).tolist(), seed=7)
    large = st.bootstrap_ci(rng.normal(0, 1, 3000).tolist(), seed=7)
    assert (large["hi"] - large["lo"]) < (small["hi"] - small["lo"])


# ─── t_test_greater ───────────────────────────────────────────────────────────

def test_t_test_mean_equals_mu0_is_half():
    # symmetric around 0 => t == 0 => p == 0.5
    r = st.t_test_greater([-2, -1, 0, 1, 2], mu0=0.0)
    assert r["t"] == pytest.approx(0.0, abs=1e-12)
    assert r["p"] == pytest.approx(0.5, abs=1e-9)


def test_t_test_strong_positive_tiny_p():
    r = st.t_test_greater([1.0] * 3 + [1.01, 0.99] * 50, mu0=0.0)  # mean ~1, tiny se
    assert r["p"] < 1e-6 and r["t"] > 5


def test_t_test_strong_negative_high_p():
    r = st.t_test_greater([-1.0, -1.1, -0.9] * 40, mu0=0.0)
    assert r["p"] > 0.99


def test_t_test_zero_variance():
    assert st.t_test_greater([2.0] * 10, mu0=0.0)["p"] == 0.0    # 2>0 certain
    assert st.t_test_greater([2.0] * 10, mu0=5.0)["p"] == 1.0    # 2>5 impossible


# ─── benjamini_hochberg ───────────────────────────────────────────────────────

def test_bh_all_reject_boundary():
    # p(k) == (k/m)*alpha for all k => all adjusted == alpha, all reject at <=
    r = st.benjamini_hochberg([0.01, 0.02, 0.03, 0.04, 0.05], alpha=0.05)
    assert r["n_reject"] == 5
    assert all(a == pytest.approx(0.05) for a in r["adjusted"])


def test_bh_partial_and_order_preserved():
    # shuffled input; adjusted must map back to input order
    r = st.benjamini_hochberg([0.5, 0.001, 0.9], alpha=0.05)
    assert r["adjusted"][1] == pytest.approx(0.003)   # 0.001*3/1
    assert r["adjusted"][0] == pytest.approx(0.75)    # 0.5*3/2
    assert r["adjusted"][2] == pytest.approx(0.9)
    assert r["reject"] == [False, True, False]
    assert r["n_reject"] == 1


def test_bh_empty():
    r = st.benjamini_hochberg([])
    assert r["n_reject"] == 0 and r["adjusted"] == []


# ─── bonferroni ───────────────────────────────────────────────────────────────

def test_bonferroni_known_and_clip():
    r = st.bonferroni([0.01, 0.02, 0.2], alpha=0.05)
    assert r["adjusted"] == pytest.approx([0.03, 0.06, 0.6])
    assert r["reject"] == [True, False, False]
    assert r["n_reject"] == 1
    assert st.bonferroni([0.5, 0.9], alpha=0.05)["adjusted"] == [1.0, 1.0]


# ─── sharpe / PSR / DSR ───────────────────────────────────────────────────────

def test_sharpe_known():
    assert st.sharpe([0, 1, 2]) == pytest.approx(1.0)   # mean 1, std(ddof1) 1


def test_psr_half_at_own_sr_and_monotone():
    x = [0.01 * i for i in range(-20, 80)]              # positive-mean sample
    sr = st.sharpe(x)
    assert st.probabilistic_sharpe_ratio(x, sr_benchmark=sr) == pytest.approx(0.5, abs=1e-6)
    hi = st.probabilistic_sharpe_ratio(x, sr_benchmark=0.0)
    lo = st.probabilistic_sharpe_ratio(x, sr_benchmark=sr * 2)
    assert hi > 0.5 > lo                                # higher bar => lower PSR


def test_expected_max_sharpe_grows_with_trials_and_scales():
    assert st.expected_max_sharpe(1, 0.5) == 0.0
    assert st.expected_max_sharpe(50, 0.5) < st.expected_max_sharpe(500, 0.5)
    assert st.expected_max_sharpe(100, 1.0) == pytest.approx(
        2 * st.expected_max_sharpe(100, 0.5))


def test_dsr_harder_with_more_trials():
    x = [0.02 * i for i in range(-30, 90)]
    d1 = st.deflated_sharpe_ratio(x, n_trials=2, sr_trials_std=0.1)
    d2 = st.deflated_sharpe_ratio(x, n_trials=200, sr_trials_std=0.1)
    assert 0.0 <= d2["dsr"] <= 1.0
    assert d2["dsr"] < d1["dsr"]                        # more trials => tougher benchmark
    assert d2["sr_benchmark"] > d1["sr_benchmark"]
