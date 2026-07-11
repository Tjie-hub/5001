"""Research statistics utilities (audit R-6): uncertainty quantification and
multiple-testing control for edge claims.

The research engine had no way to attach a confidence interval to an expectancy
or to discount a "winning" cell for the many cells that were tested. This module
supplies both, as pure, deterministic functions (numpy + stdlib only — no scipy,
no global RNG). Every stochastic routine takes an explicit integer `seed` and
defaults to SEED, so results are byte-reproducible.

Contents
--------
- bootstrap_ci        : percentile bootstrap CI for the mean (expectancy).
- t_test_greater      : one-sided H1: mean > mu0 (normal approx, large-N).
- benjamini_hochberg  : BH false-discovery-rate control across a test family.
- bonferroni          : family-wise Bonferroni correction.
- sharpe              : per-observation Sharpe (mean / std).
- probabilistic_sharpe_ratio : PSR — P(true SR > benchmark) (Bailey & Lopez de
                        Prado 2012), skew/kurtosis-aware.
- expected_max_sharpe : E[max SR] under N independent trials (Gaussian EVT).
- deflated_sharpe_ratio : DSR — PSR against the multiple-testing-inflated
                        benchmark (Bailey & Lopez de Prado 2014).

All p-values / probabilities use statistics.NormalDist for Phi and Phi^-1.
The normal approximation for t_test_greater is accurate for the N>=100 samples
this engine gates on; it is documented, not hidden.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

SEED = 20260711  # fixed default so bootstrap results are reproducible
_PHI = NormalDist()
_EULER_MASCHERONI = 0.5772156649015329


# ─── Confidence intervals ─────────────────────────────────────────────────────

def bootstrap_ci(values, n_boot: int = 10000, ci: float = 0.95,
                 seed: int = SEED) -> dict:
    """Percentile-bootstrap CI for the MEAN of `values` (e.g. per-trade returns).

    Resamples `values` with replacement `n_boot` times using a seeded numpy
    Generator, so the interval is deterministic for a given (values, n_boot, ci,
    seed). Returns point estimate, CI bounds, bootstrap standard error and n.
    """
    x = np.asarray(values, dtype=float)
    n = x.size
    if n == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "se": float("nan"), "n": 0, "n_boot": n_boot, "ci": ci, "seed": seed}
    if n == 1:
        v = float(x[0])
        return {"point": v, "lo": v, "hi": v, "se": 0.0,
                "n": 1, "n_boot": n_boot, "ci": ci, "seed": seed}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = x[idx].mean(axis=1)
    alpha = (1.0 - ci) / 2.0
    lo, hi = np.quantile(boot_means, [alpha, 1.0 - alpha])
    return {"point": float(x.mean()), "lo": float(lo), "hi": float(hi),
            "se": float(boot_means.std(ddof=1)), "n": int(n),
            "n_boot": n_boot, "ci": ci, "seed": seed}


# ─── Hypothesis test ──────────────────────────────────────────────────────────

def t_test_greater(values, mu0: float = 0.0) -> dict:
    """One-sided test of H1: mean(values) > mu0.

    Uses the normal approximation to Student-t (valid at the N>=100 sample sizes
    this engine gates edge claims on). Returns t statistic, one-sided p, n, mean,
    standard error.
    """
    x = np.asarray(values, dtype=float)
    n = x.size
    if n < 2:
        return {"t": float("nan"), "p": float("nan"), "n": int(n),
                "mean": float(x.mean()) if n else float("nan"), "se": float("nan")}
    m = float(x.mean())
    se = float(x.std(ddof=1) / math.sqrt(n))
    if se == 0.0:
        # zero variance: mean>mu0 is certain / impossible
        return {"t": float("inf") if m > mu0 else float("-inf"),
                "p": 0.0 if m > mu0 else 1.0, "n": int(n), "mean": m, "se": 0.0}
    t = (m - mu0) / se
    p = 1.0 - _PHI.cdf(t)   # upper tail
    return {"t": float(t), "p": float(p), "n": int(n), "mean": m, "se": se}


# ─── Multiple-testing correction ──────────────────────────────────────────────

def benjamini_hochberg(pvalues, alpha: float = 0.05) -> dict:
    """Benjamini-Hochberg FDR control. Returns BH-adjusted p-values (same order
    as input), a boolean reject mask at level `alpha`, and the number rejected."""
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    if m == 0:
        return {"adjusted": [], "reject": [], "n_reject": 0, "alpha": alpha}
    order = np.argsort(p)
    ranked = p[order]
    factor = m / np.arange(1, m + 1)
    adj_sorted = ranked * factor
    # enforce monotonic non-decreasing from the largest p downward
    adj_sorted = np.minimum.accumulate(adj_sorted[::-1])[::-1]
    adj_sorted = np.clip(adj_sorted, 0.0, 1.0)
    adjusted = np.empty(m)
    adjusted[order] = adj_sorted
    reject = adjusted <= alpha
    return {"adjusted": adjusted.tolist(), "reject": reject.tolist(),
            "n_reject": int(reject.sum()), "alpha": alpha}


def bonferroni(pvalues, alpha: float = 0.05) -> dict:
    """Family-wise Bonferroni correction over `m = len(pvalues)` tests."""
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    if m == 0:
        return {"adjusted": [], "reject": [], "n_reject": 0, "alpha": alpha, "m": 0}
    adjusted = np.clip(p * m, 0.0, 1.0)
    reject = adjusted <= alpha
    return {"adjusted": adjusted.tolist(), "reject": reject.tolist(),
            "n_reject": int(reject.sum()), "alpha": alpha, "m": int(m)}


# ─── Sharpe-ratio statistics ──────────────────────────────────────────────────

def _std_moments(x: np.ndarray):
    """Population std, skew, and (non-excess) kurtosis of x."""
    m = x.mean()
    s = x.std(ddof=0)
    if s == 0.0:
        return s, 0.0, 3.0
    z = (x - m) / s
    skew = float((z ** 3).mean())
    kurt = float((z ** 4).mean())   # normal == 3.0
    return float(s), skew, kurt


def sharpe(values) -> float:
    """Per-observation Sharpe = mean / std (ddof=1). Not annualized — the caller
    controls the observation unit (here: per-trade)."""
    x = np.asarray(values, dtype=float)
    if x.size < 2:
        return float("nan")
    s = x.std(ddof=1)
    return float(x.mean() / s) if s > 0 else float("nan")


def probabilistic_sharpe_ratio(values, sr_benchmark: float = 0.0) -> float:
    """PSR = P(true SR > sr_benchmark) given the observed (non-normal) sample
    (Bailey & Lopez de Prado 2012). Skew/kurtosis-adjusted."""
    x = np.asarray(values, dtype=float)
    n = x.size
    if n < 2:
        return float("nan")
    sr = sharpe(x)
    _, skew, kurt = _std_moments(x)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2))
    z = (sr - sr_benchmark) * math.sqrt(n - 1) / denom
    return float(_PHI.cdf(z))


def expected_max_sharpe(n_trials: int, sr_trials_std: float) -> float:
    """E[max of N i.i.d. standard-normal-ish Sharpe estimates] (Bailey & Lopez de
    Prado 2014, Gaussian extreme-value approximation). `sr_trials_std` is the
    cross-trial standard deviation of the estimated Sharpe ratios."""
    if n_trials < 2 or sr_trials_std <= 0:
        return 0.0
    g = _EULER_MASCHERONI
    z1 = _PHI.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = _PHI.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return float(sr_trials_std * ((1.0 - g) * z1 + g * z2))


def deflated_sharpe_ratio(values, n_trials: int, sr_trials_std: float) -> dict:
    """DSR: PSR evaluated against the multiple-testing-inflated benchmark
    E[max SR] over `n_trials` (Bailey & Lopez de Prado 2014). A DSR near 1 means
    the strategy's Sharpe survives the fact that many strategies were tried;
    near 0.5 or below means the result is consistent with luck-of-the-max.

    `sr_trials_std` = std of the estimated Sharpe ratios across the tested family
    (must be supplied — it is what makes the correction honest)."""
    sr_star = expected_max_sharpe(n_trials, sr_trials_std)
    dsr = probabilistic_sharpe_ratio(values, sr_benchmark=sr_star)
    return {"dsr": float(dsr), "sr": sharpe(values), "sr_benchmark": float(sr_star),
            "n_trials": int(n_trials), "sr_trials_std": float(sr_trials_std)}
