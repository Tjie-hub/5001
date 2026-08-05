"""Deterministic post-LLM guardrails for the Risk Manager decision.

Root cause this addresses: the Risk prompt's veto gate keys on `quant_score`, but
that number is supplied on inconsistent scales by different callers (flow composite
-5..+5, premarket strength 0-100, EOD conviction 0-100/0.0). So the LLM gate is
unreliable and the firm could approve a candidate whose own analysts are bearish.

These guardrails run AFTER the LLM on the analyst VERDICTS (which are consistently
enumerated, unlike the raw number) and can only ever downgrade approve→veto — never
the reverse. They are pure/data-only so they unit-test without the LLM.

`normalize_quant` rescales each caller's score to a common 0-1 strength so the
prompt's (now 0-1) quant thresholds work again.

WP4 (AF-3): `build_consensus_summary()` assembles Tier 2 `ConsensusContext` from the
four analysts' already-produced verdicts plus `PortfolioContext`/`RiskContext` (ADR-AF-002)
— pure/side-effect-free, same as everything else in this module. `apply_guardrails()`
consumes it for two additional deterministic vetoes: K1 (≥3 negative analyst verdicts)
and K2 (candidate already has an open position). The `consensus` argument is optional
and defaults to `None`, so existing callers are unaffected — K1/K2 simply don't fire
without it.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from .schemas import ConsensusContext, PortfolioContext, RiskContext

# flow_verdict values that mean institutions are selling into the move
BEARISH_FLOW = {"BEARISH", "DISTRIBUTING", "DISTRIBUTION", "MORNING_TRAP"}
# per-candidate regime calls that warrant the confidence floor
WEAK_REGIMES = {"SIDEWAYS", "BEAR"}
DEFAULT_CONF_FLOOR = 0.55
# callers whose score is a 0-100 magnitude; everything else is the -5..+5 flow scale
MAGNITUDE_STRATEGIES = {"premarket", "eod"}

# K1 consensus counting: each analyst's own verdict field + the enum value(s) that
# count as negative/positive for that role, per its prompt's declared schema
# (technical_v1.md, flow_v1.md, regime_v1.md, news_v1.md).
_VERDICT_FIELD = {"technical": "verdict", "flow": "flow_verdict",
                   "regime": "regime_call", "news": "sentiment"}
_NEGATIVE_VERDICTS = {"technical": {"BEARISH"}, "flow": {"DISTRIBUTING"},
                       "regime": {"BEAR"}, "news": {"BEARISH"}}
_POSITIVE_VERDICTS = {"technical": {"BULLISH"}, "flow": {"ACCUMULATING"},
                       "regime": {"BULL"}, "news": {"BULLISH"}}
# K1 threshold: 3+ negative analyst verdicts auto-vetoes.
NEGATIVE_CONSENSUS_THRESHOLD = 3


def _output(analyst_results: Sequence[Any], role: str) -> dict[str, Any]:
    """Extract the `.output` dict from the analyst result with the given role.
    Returns an empty dict when the role is missing or its status is not 'ok'.
    Works with any object that has role/status/output attributes (AgentResult,
    mocks, etc.)."""
    for r in analyst_results:
        if getattr(r, "role", None) == role:
            return (getattr(r, "output", None) or {}) if getattr(r, "status", None) == "ok" else {}
    return {}


def build_consensus_summary(
    analyst_results: Sequence[Any],
    ticker: str,
    portfolio_ctx: Optional[PortfolioContext] = None,
    risk_ctx: Optional[RiskContext] = None,
) -> ConsensusContext:
    """Assemble Tier 2 `ConsensusContext` from the four analysts' already-produced
    verdicts (technical/flow/regime/news) plus Tier 1 `PortfolioContext`/`RiskContext`
    (ADR-AF-002). Pure and side-effect free — no I/O, no LLM call; `analyst_results`
    is read, never mutated.

    `positive_count`/`negative_count` key on each analyst's own verdict field and enum
    (see `_VERDICT_FIELD`/`_NEGATIVE_VERDICTS`/`_POSITIVE_VERDICTS`, above) — an analyst
    that is missing, failed, or NEUTRAL counts toward neither. `aligned_bullish` mirrors
    `positive_count`: how many analysts are aligned on a bullish/positive reading.
    """
    negative_count = 0
    positive_count = 0
    for role, field in _VERDICT_FIELD.items():
        value = (_output(analyst_results, role).get(field) or "").upper()
        if value in _NEGATIVE_VERDICTS[role]:
            negative_count += 1
        elif value in _POSITIVE_VERDICTS[role]:
            positive_count += 1

    already_open_position = bool(
        portfolio_ctx.has_open_position(ticker) if portfolio_ctx is not None else False
    )
    entries_blocked = bool(risk_ctx.entries_blocked if risk_ctx is not None else False)

    return ConsensusContext(
        negative_count=negative_count,
        positive_count=positive_count,
        aligned_bullish=positive_count,
        already_open_position=already_open_position,
        entries_blocked=entries_blocked,
    )


def apply_guardrails(
    decision: str,
    confidence: Optional[float],
    analyst_results: Sequence[Any],
    conf_floor: float = DEFAULT_CONF_FLOOR,
    consensus: Optional[ConsensusContext] = None,
) -> tuple[str, Optional[str]]:
    """Return (decision, override_reason). Only downgrades approve→veto.

    analyst_results must be a sequence of objects with .role, .status, .output
    attributes (AgentResult or compatible). The guardrails key on the Flow,
    Technical, and Regime analyst verdicts — they are consistent enum values
    regardless of which caller built the candidate.

    `consensus` (WP4, optional): when supplied, adds two further deterministic
    vetoes — K1 (≥3 negative analyst verdicts) and K2 (candidate already has an open
    position). Omitting it (the default) preserves pre-WP4 behavior exactly."""
    if decision != "approve":
        return decision, None

    flow_v = (_output(analyst_results, "flow").get("flow_verdict") or "").upper()
    tech_v = (_output(analyst_results, "technical").get("verdict") or "").upper()
    regime_call = (_output(analyst_results, "regime").get("regime_call") or "").upper()

    # 1. Hard contradiction: bearish flow not offset by a bullish technical read.
    if flow_v in BEARISH_FLOW and tech_v != "BULLISH":
        return "veto", (f"guardrail: flow {flow_v} not offset by bullish technical "
                        f"({tech_v or 'n/a'})")

    # 2. Confidence floor in weak regimes — kills fail-open approve-with-warning.
    if regime_call in WEAK_REGIMES and (confidence or 0.0) < conf_floor:
        return "veto", (f"guardrail: confidence {confidence or 0.0:.2f} < {conf_floor:.2f} "
                        f"in {regime_call} regime")

    if consensus is not None:
        # 3. K1: three or more analyst verdicts are negative.
        if consensus.negative_count >= NEGATIVE_CONSENSUS_THRESHOLD:
            return "veto", (f"guardrail: {consensus.negative_count} analyst verdicts "
                            f"negative (K1, threshold {NEGATIVE_CONSENSUS_THRESHOLD})")

        # 4. K2: candidate already has an open position — no doubling up.
        if consensus.already_open_position:
            return "veto", "guardrail: candidate already has an open position (K2)"

    return decision, None


def normalize_quant(score, strategy: str) -> float:
    """Rescale a caller's raw score to a common 0-1 strength for the Risk prompt."""
    s = float(score or 0.0)
    n = s / 100.0 if strategy in MAGNITUDE_STRATEGIES else (s + 5.0) / 10.0
    return max(0.0, min(1.0, n))
