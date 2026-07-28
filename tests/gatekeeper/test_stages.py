"""Phase C stages (spec §5 stage-contract table). Each stage delegates all math to
research.statistics; here we pin the PASS/WATCH/FAIL banding with deterministic
fixtures. No exact CI/DSR magic numbers — we assert the qualitative band the verdict
keys on (robust to numpy version), plus the proxy-retirement invariant on DSR."""
import numpy as np

from research.gatekeeper import stages
from research.gatekeeper.config import load_config
from research.gatekeeper.models import Verdict

CFG = load_config()


def _returns(mean, sd, n, seed=0):
    return list(np.random.default_rng(seed).normal(mean, sd, n))


# ── Stage 1 — minimum sample ─────────────────────────────────────────────────

def test_min_sample_pass_when_both_floors_met():
    ctx = {"n_overall": 500, "governing_cell": "BULL", "cell_n": {"BULL": 300}}
    r = stages.stage_min_sample(ctx, CFG)
    assert r.verdict == Verdict.PASS


def test_min_sample_fail_when_overall_below_floor():
    ctx = {"n_overall": 100, "governing_cell": "BULL", "cell_n": {"BULL": 300}}
    assert stages.stage_min_sample(ctx, CFG).verdict == Verdict.FAIL


def test_min_sample_fail_when_governing_cell_below_floor():
    ctx = {"n_overall": 500, "governing_cell": "BULL", "cell_n": {"BULL": 40}}
    assert stages.stage_min_sample(ctx, CFG).verdict == Verdict.FAIL


# ── Stage 2 — confidence interval (test the LOWER bound vs bar) ───────────────

def test_ci_pass_when_lower_bound_above_bar():
    ctx = {"claim_net": _returns(2.0, 3.0, 400)}
    r = stages.stage_confidence_interval(ctx, CFG)
    assert r.verdict == Verdict.PASS
    assert r.statistic["lo"] >= CFG.promotion_bar_pct


def test_ci_watch_when_interval_straddles_bar():
    # mean ~0.9, wide spread -> lo < 0.50 < hi  (the NR7 situation)
    ctx = {"claim_net": _returns(0.9, 5.0, 333)}
    r = stages.stage_confidence_interval(ctx, CFG)
    assert r.verdict == Verdict.WATCH
    assert r.statistic["lo"] < CFG.promotion_bar_pct <= r.statistic["hi"]


def test_ci_fail_when_upper_bound_below_bar():
    ctx = {"claim_net": _returns(-0.9, 3.0, 400)}
    r = stages.stage_confidence_interval(ctx, CFG)
    assert r.verdict == Verdict.FAIL
    assert r.statistic["hi"] < CFG.promotion_bar_pct


# ── Stage 3 — multiple-testing correction (governing cell) ───────────────────

def test_multiplicity_pass_when_governing_survives_both():
    ctx = {"family_pvalues": [0.001, 0.5, 0.99], "family_labels": ["BULL", "BEAR", "SW"],
           "governing_index": 0}
    r = stages.stage_multiplicity(ctx, CFG)
    assert r.verdict == Verdict.PASS
    assert r.statistic["bonferroni_p"] <= CFG.multiplicity["alpha"]


def test_multiplicity_fail_when_governing_not_significant_after_correction():
    ctx = {"family_pvalues": [0.04, 0.5, 0.99], "family_labels": ["BULL", "BEAR", "SW"],
           "governing_index": 0}
    assert stages.stage_multiplicity(ctx, CFG).verdict == Verdict.FAIL


# ── Stage 4 — PSR ────────────────────────────────────────────────────────────

def test_psr_pass_for_strong_positive_series():
    ctx = {"claim_net": _returns(2.0, 2.0, 400)}
    r = stages.stage_psr(ctx, CFG)
    assert r.verdict == Verdict.PASS and r.statistic["psr"] >= CFG.psr["min"]


def test_psr_fail_for_near_zero_series():
    ctx = {"claim_net": _returns(0.0, 3.0, 400)}
    assert stages.stage_psr(ctx, CFG).verdict == Verdict.FAIL


# ── Stage 5 — Deflated Sharpe from the REAL scan distribution ─────────────────

def test_deflated_sharpe_uses_real_scan_distribution_not_a_proxy():
    scan = [0.05, 0.10, 0.15, 0.12, 0.08]          # 5 real scan-cell Sharpes
    ctx = {"claim_net": _returns(2.0, 2.0, 400), "scan_sharpes": scan}
    r = stages.stage_deflated_sharpe(ctx, CFG)
    # the correction must use the TRUE trial count and the std of the ACTUAL Sharpes
    assert r.statistic["n_trials"] == len(scan)
    assert abs(r.statistic["sr_trials_std"] - float(np.std(scan))) < 1e-12


def test_deflated_sharpe_pass_for_strong_edge_small_family():
    ctx = {"claim_net": _returns(2.5, 1.5, 400), "scan_sharpes": [0.05, 0.06, 0.07]}
    assert stages.stage_deflated_sharpe(ctx, CFG).verdict == Verdict.PASS


def test_deflated_sharpe_never_hard_fails_collapse_is_watch_not_reject():
    # DSR measures multiplicity-risk; a collapse with otherwise-positive evidence
    # must WATCHLIST (forward test decides), never REJECT on its own (spec §5 refinement).
    scan = list(np.random.default_rng(1).normal(0.1, 0.15, 42))   # large dispersed family
    ctx = {"claim_net": _returns(0.6, 3.0, 333), "scan_sharpes": scan}
    r = stages.stage_deflated_sharpe(ctx, CFG)
    assert r.verdict == Verdict.WATCH        # NOT FAIL, even when DSR collapses toward 0
    assert r.statistic["dsr"] < CFG.deflated_sharpe["min"]


# ── Stage 6 — walk-forward ───────────────────────────────────────────────────

def test_walk_forward_pass_when_consistent_and_profitable():
    ctx = {"wf": {"consistency_pct": 75, "pooled_oos_exp": 1.2, "n_windows": 16}}
    assert stages.stage_walk_forward(ctx, CFG).verdict == Verdict.PASS


def test_walk_forward_fail_when_inconsistent():
    ctx = {"wf": {"consistency_pct": 40, "pooled_oos_exp": 1.2, "n_windows": 16}}
    assert stages.stage_walk_forward(ctx, CFG).verdict == Verdict.FAIL


def test_walk_forward_fail_when_below_bar():
    ctx = {"wf": {"consistency_pct": 80, "pooled_oos_exp": 0.1, "n_windows": 16}}
    assert stages.stage_walk_forward(ctx, CFG).verdict == Verdict.FAIL


# ── Stage 7 — out-of-sample ──────────────────────────────────────────────────

def test_out_of_sample_pass_when_retention_and_exp_hold():
    ctx = {"oos": {"retention": 0.8, "late_exp": 1.0, "late_n": 200}}
    assert stages.stage_out_of_sample(ctx, CFG).verdict == Verdict.PASS


def test_out_of_sample_fail_when_retention_collapses():
    ctx = {"oos": {"retention": 0.2, "late_exp": 1.0, "late_n": 200}}
    assert stages.stage_out_of_sample(ctx, CFG).verdict == Verdict.FAIL


# ── Stage 8 — forward-test eligibility ───────────────────────────────────────

def test_ft_eligibility_always_passes_and_attaches_frozen_rule():
    r = stages.stage_ft_eligibility({}, CFG)
    assert r.verdict == Verdict.PASS
    assert r.statistic["forward_test_rule"]["min_n"] == 15
    assert r.statistic["forward_test_rule"]["go_exp"] == 0.50
