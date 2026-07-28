"""The eight gate stages (spec §5 stage-contract table).

Each stage takes the precomputed `ctx` (built once by the pipeline from the
candidate) and the frozen `GateConfig`, and returns a StageResult carrying the
verdict, the statistic evidence, and the thresholds applied. Every number comes
from research.statistics or research.nr7_study — NO statistics are reimplemented
here. Stages are pure: no DB, no filesystem.
"""
from __future__ import annotations

import numpy as np

from research import statistics as st
from research.gatekeeper.models import StageResult, Verdict


def stage_min_sample(ctx, config) -> StageResult:
    """① N-floor on the overall trade set AND the governing regime cell."""
    n_overall = ctx["n_overall"]
    gov = ctx["governing_cell"]
    cell_n = ctx.get("cell_n", {}).get(gov, 0)
    ok = n_overall >= config.min_n_overall and cell_n >= config.min_n_cell
    return StageResult(
        stage="min_sample",
        verdict=Verdict.PASS if ok else Verdict.FAIL,
        statistic={"n_overall": n_overall, "governing_cell": gov, "cell_n": cell_n},
        threshold={"min_n_overall": config.min_n_overall, "min_n_cell": config.min_n_cell},
    )


def stage_confidence_interval(ctx, config) -> StageResult:
    """② Bootstrap CI on the claim's per-trade net %. The LOWER bound (not the
    point estimate) is tested against the promotion bar."""
    bar = config.promotion_bar_pct
    r = st.bootstrap_ci(ctx["claim_net"], n_boot=config.ci["n_boot"],
                        ci=config.ci["level"], seed=config.seed)
    if r["hi"] < bar:
        verdict = Verdict.FAIL
    elif r["lo"] >= bar:
        verdict = Verdict.PASS
    else:
        verdict = Verdict.WATCH        # interval straddles the bar — magnitude uncertain
    return StageResult(stage="confidence_interval", verdict=verdict,
                       statistic=r, threshold={"promotion_bar_pct": bar})


def stage_multiplicity(ctx, config) -> StageResult:
    """③ BH + Bonferroni across the FULL pre-registered family; the governing cell
    must survive correction (both, if require_both)."""
    alpha = config.multiplicity["alpha"]
    pvals = ctx["family_pvalues"]
    gi = ctx["governing_index"]
    bh = st.benjamini_hochberg(pvals, alpha=alpha)
    bonf = st.bonferroni(pvals, alpha=alpha)
    bh_p = bh["adjusted"][gi]
    bonf_p = bonf["adjusted"][gi]
    if config.multiplicity.get("require_both", True):
        ok = bh_p <= alpha and bonf_p <= alpha
    else:
        ok = bh_p <= alpha
    return StageResult(
        stage="multiplicity",
        verdict=Verdict.PASS if ok else Verdict.FAIL,
        statistic={"governing_label": ctx.get("family_labels", [None] * (gi + 1))[gi],
                   "raw_p": pvals[gi], "bh_p": bh_p, "bonferroni_p": bonf_p,
                   "family_size": len(pvals)},
        threshold={"alpha": alpha, "require_both": config.multiplicity.get("require_both", True)},
    )


def stage_psr(ctx, config) -> StageResult:
    """④ Probabilistic Sharpe Ratio vs benchmark 0."""
    psr = st.probabilistic_sharpe_ratio(ctx["claim_net"], sr_benchmark=0.0)
    ok = psr >= config.psr["min"]
    return StageResult(stage="psr",
                       verdict=Verdict.PASS if ok else Verdict.FAIL,
                       statistic={"psr": psr, "sr": st.sharpe(ctx["claim_net"])},
                       threshold={"min": config.psr["min"]})


def stage_deflated_sharpe(ctx, config) -> StageResult:
    """⑤ Deflated Sharpe against E[max SR] over the REAL scan-Sharpe distribution.

    n_trials = number of scan cells; sr_trials_std = std of the ACTUAL scan Sharpes.
    This is the institutional replacement for the Phase B 3-cell proxy (spec §8)."""
    scan = np.asarray(ctx["scan_sharpes"], dtype=float)
    n_trials = int(scan.size)
    sr_trials_std = float(scan.std()) if scan.size else 0.0
    d = st.deflated_sharpe_ratio(ctx["claim_net"], n_trials=n_trials,
                                 sr_trials_std=sr_trials_std)
    # DSR is a multiplicity-risk flag: PASS if it clears the bar, else WATCH. It
    # never hard-FAILs alone — a collapse with otherwise-positive expectancy evidence
    # warrants watchlist + the pre-registered forward test, not an outright REJECT
    # (spec §5 refinement; keeps the frozen master-plan posture that the forward test
    # is decisive on NR7-like claims).
    verdict = Verdict.PASS if d["dsr"] >= config.deflated_sharpe["min"] else Verdict.WATCH
    return StageResult(stage="deflated_sharpe", verdict=verdict, statistic=d,
                       threshold={"min": config.deflated_sharpe["min"]})


def stage_walk_forward(ctx, config) -> StageResult:
    """⑥ Walk-forward: OOS consistency AND pooled OOS expectancy above the bar."""
    wf = ctx["wf"]
    cfg = config.walk_forward
    ok = (wf["consistency_pct"] >= cfg["min_consistency_pct"]
          and wf["pooled_oos_exp"] >= config.promotion_bar_pct)
    return StageResult(stage="walk_forward",
                       verdict=Verdict.PASS if ok else Verdict.FAIL,
                       statistic=wf,
                       threshold={"min_consistency_pct": cfg["min_consistency_pct"],
                                  "promotion_bar_pct": config.promotion_bar_pct})


def stage_out_of_sample(ctx, config) -> StageResult:
    """⑦ Held-out out-of-sample: retention AND held-out expectancy above the bar."""
    oos = ctx["oos"]
    cfg = config.out_of_sample
    ok = (oos["retention"] >= cfg["min_retention"]
          and oos["late_exp"] >= config.promotion_bar_pct)
    return StageResult(stage="out_of_sample",
                       verdict=Verdict.PASS if ok else Verdict.FAIL,
                       statistic=oos,
                       threshold={"min_retention": cfg["min_retention"],
                                  "promotion_bar_pct": config.promotion_bar_pct})


def stage_ft_eligibility(ctx, config) -> StageResult:
    """⑧ Forward-test eligibility: never fails alone — attaches the frozen
    pre-registered forward-test rule that a PROMOTE carries."""
    return StageResult(stage="ft_eligibility", verdict=Verdict.PASS,
                       statistic={"forward_test_rule": dict(config.forward_test_rule)},
                       threshold={})


# ordered pipeline (spec §5 data-flow)
PIPELINE = (
    stage_min_sample,
    stage_confidence_interval,
    stage_multiplicity,
    stage_psr,
    stage_deflated_sharpe,
    stage_walk_forward,
    stage_out_of_sample,
    stage_ft_eligibility,
)
