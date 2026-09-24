"""Statistics the Rule Card verdict depends on (D-055).

Kept here, not in research/statistics.py, so the verdict path is covered by the
framework hash that FREEZE.json pins: a change to any function below after a card
is frozen makes that card's run refuse. Deterministic: every stochastic routine
takes an explicit seed.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_PHI = NormalDist()
Z_POWER_80 = _PHI.inv_cdf(0.80)   # 0.8416 — the "+0.84" in RULE_FIRST_PROTOCOL R5


def nw_t(values, lag: int = 3) -> float:
    """Newey-West (Bartlett kernel) t-statistic of the mean.

    Same estimator as remeasure_v2.py::nw_t (the D-053 re-measurement), so a
    Rule Card run and that record are directly comparable.
    """
    a = np.asarray(values, dtype=float)
    a = a[~np.isnan(a)]
    n = a.size
    if n < 3:
        return float("nan")
    d = a - a.mean()
    v = d @ d / n
    for k in range(1, min(lag, n - 1) + 1):
        v += 2.0 * (1.0 - k / (lag + 1.0)) * (d[k:] @ d[:-k]) / n
    if v <= 0:
        return float("nan")
    return float(a.mean() / math.sqrt(v / n))


def needed_effect(t_star: float, sigma: float, n: int) -> float:
    """True mean needed for 80% power at one-sided threshold t_star (R5)."""
    return float((t_star + Z_POWER_80) * sigma / math.sqrt(n))


def minimum_bayes_factor_p_null(t: float, prior_true: float) -> float:
    """Lower bound on P(null | data) from MBF = exp(-t^2/2) (Harvey 2017)."""
    mbf = math.exp(-t * t / 2.0)
    odds_null = (1.0 - prior_true) / prior_true * mbf
    return float(odds_null / (1.0 + odds_null))


def _stationary_bootstrap_idx(T: int, block: float, rng) -> np.ndarray:
    """Politis-Romano stationary bootstrap index path of length T."""
    idx = np.empty(T, dtype=int)
    idx[0] = rng.integers(0, T)
    new_block = rng.random(T) < 1.0 / block
    starts = rng.integers(0, T, size=T)
    for i in range(1, T):
        idx[i] = starts[i] if new_block[i] else (idx[i - 1] + 1) % T
    return idx


def mr_test(bucket_returns, direction: str = "increasing", n_boot: int = 1000,
            block: float = 6.0, seed: int = 20260924) -> dict:
    """Patton-Timmermann (2010) monotonic-relationship test.

    bucket_returns: T x K array, columns ordered from lowest to highest score.
    H0: returns are NOT monotone in the stated direction (min adjacent
    difference <= 0). H1: every adjacent difference has the stated sign.
    Small p = evidence of a graded dose-response (RULE_FIRST_PROTOCOL R6).
    """
    R = np.asarray(bucket_returns, dtype=float)
    R = R[~np.isnan(R).any(axis=1)]
    if direction == "decreasing":
        R = -R
    elif direction != "increasing":
        raise ValueError("direction must be 'increasing' or 'decreasing'")
    T, K = R.shape
    if T < 12 or K < 3:
        return {"J": float("nan"), "p": float("nan"), "T": int(T), "K": int(K)}
    D = R[:, 1:] - R[:, :-1]
    mu = D.mean(axis=0)
    J = float(mu.min())
    rng = np.random.default_rng(seed)
    Jb = np.empty(n_boot)
    for b in range(n_boot):
        ii = _stationary_bootstrap_idx(T, block, rng)
        Jb[b] = (D[ii].mean(axis=0) - mu).min()
    p = float((Jb >= J).mean())
    return {"J": J, "p": p, "T": int(T), "K": int(K), "n_boot": n_boot,
            "block": block, "seed": seed, "adjacent_means": mu.tolist()}
