"""
engine/edge_score.py — Composite edge score (validated WF expectancy dominant).

Pure functions, no DB / no side effects. Fixed (not cross-sectional) anchors so
the score is comparable across tickers and a weak universe cannot manufacture a
1.0 — "better no pick than bad pick."

The score is exactly five weighted terms. win_rate and sharpe are deliberately
NOT inputs here: they are deterministic vetoes (engine/veto.py), not score
contributors, and were removed to avoid dead/unused parameters.
"""

# ── Weights (config-driven) ─────────────────────────────────────────
W_EXPECTANCY  = 0.40    # validated OOS per-trade expectancy — dominant
W_CONSISTENCY = 0.20    # % of walk-forward windows profitable
W_FLOW        = 0.20    # smart-money / foreign flow strength
W_REGIME      = 0.10    # per-ticker regime fit
W_TECHNICAL   = 0.10    # technical setup (momentum votes)

# ── Expectancy anchor (per-trade PERCENT, capital-invariant) ────────
# norm = clip(expectancy_pct, 0, MAX) / MAX. Fixed anchor, not min-max:
# 3.0%/trade is "as good as it gets" for IDX single-stock 2-5d holds.
# Negative expectancy normalizes to 0.
MAX_EXPECTANCY_PCT = 3.0

# ── Consistency anchor (natural [0, 100]) ───────────────────────────
MIN_CONSISTENCY = 30.0
MAX_CONSISTENCY = 100.0

# ── Flow anchor (stockbit_flow.composite_score is integer [-8, +8]) ─
MIN_FLOW_SCORE = -8.0
MAX_FLOW_SCORE =  8.0

# ── Per-ticker regime fit ───────────────────────────────────────────
REGIME_FIT = {'BULL': 1.0, 'SIDEWAYS': 0.5, 'BEAR': 0.0}
DEFAULT_REGIME_FIT = 0.3    # unknown / missing regime string

# ── Technical anchor (calc_votes returns 1..4) ──────────────────────
MIN_VOTES = 1.0
MAX_VOTES = 4.0


def _clip_norm(value: float, lo: float, hi: float) -> float:
    """Normalize to [0, 1] with hard clipping at the boundaries."""
    if value <= lo:
        return 0.0
    if value >= hi:
        return 1.0
    return (value - lo) / (hi - lo)


def norm_expectancy(expectancy_pct: float | None) -> float:
    if expectancy_pct is None:
        return 0.0
    return _clip_norm(expectancy_pct, 0.0, MAX_EXPECTANCY_PCT)


def norm_consistency(consistency_pct: float | None) -> float:
    if consistency_pct is None:
        return 0.0
    return _clip_norm(consistency_pct, MIN_CONSISTENCY, MAX_CONSISTENCY)


def norm_flow(composite_score: int | None) -> float:
    """composite_score 0 → 0.5 (neutral); +8 → 1.0; -8 → 0.0."""
    if composite_score is None:
        return 0.0
    return _clip_norm(float(composite_score), MIN_FLOW_SCORE, MAX_FLOW_SCORE)


def norm_regime(regime: str | None) -> float:
    """Per-ticker regime (BULL/SIDEWAYS/BEAR). Unknown/None → default fit."""
    if regime is None:
        return DEFAULT_REGIME_FIT
    return REGIME_FIT.get(regime, DEFAULT_REGIME_FIT)


def norm_technical(votes: float | None) -> float:
    """calc_votes returns 1..4; below 1 or missing → 0."""
    if votes is None or votes < 1:
        return 0.0
    return _clip_norm(float(votes), MIN_VOTES, MAX_VOTES)


def _contributions(expectancy_pct, consistency_pct, flow_score,
                   regime, technical_votes) -> dict:
    """Each term's weighted contribution (unrounded)."""
    return {
        'expectancy':  W_EXPECTANCY  * norm_expectancy(expectancy_pct),
        'consistency': W_CONSISTENCY * norm_consistency(consistency_pct),
        'flow':        W_FLOW        * norm_flow(flow_score),
        'regime':      W_REGIME      * norm_regime(regime),
        'technical':   W_TECHNICAL   * norm_technical(technical_votes),
    }


def compute_edge(
    expectancy_pct: float | None = None,
    consistency_pct: float | None = None,
    flow_score: int | None = None,
    regime: str | None = None,
    technical_votes: float | None = None,
) -> float:
    """Composite edge score in [0.0, 1.0]. Missing inputs contribute 0
    (except regime, which falls back to DEFAULT_REGIME_FIT)."""
    return round(sum(_contributions(
        expectancy_pct, consistency_pct, flow_score, regime, technical_votes
    ).values()), 4)


def edge_breakdown(
    expectancy_pct: float | None = None,
    consistency_pct: float | None = None,
    flow_score: int | None = None,
    regime: str | None = None,
    technical_votes: float | None = None,
) -> dict:
    """Per-term weighted contributions plus the total `edge`, for the ranking
    dump so each name's score is fully explainable."""
    contribs = _contributions(
        expectancy_pct, consistency_pct, flow_score, regime, technical_votes)
    out = {k: round(v, 4) for k, v in contribs.items()}
    out['edge'] = round(sum(contribs.values()), 4)
    return out
