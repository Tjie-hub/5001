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
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

# flow_verdict values that mean institutions are selling into the move
BEARISH_FLOW = {"BEARISH", "DISTRIBUTING", "DISTRIBUTION", "MORNING_TRAP"}
# per-candidate regime calls that warrant the confidence floor
WEAK_REGIMES = {"SIDEWAYS", "BEAR"}
DEFAULT_CONF_FLOOR = 0.55
# callers whose score is a 0-100 magnitude; everything else is the -5..+5 flow scale
MAGNITUDE_STRATEGIES = {"premarket", "eod"}


def _output(analyst_results: Sequence[Any], role: str) -> dict[str, Any]:
    """Extract the `.output` dict from the analyst result with the given role.
    Returns an empty dict when the role is missing or its status is not 'ok'.
    Works with any object that has role/status/output attributes (AgentResult,
    mocks, etc.)."""
    for r in analyst_results:
        if getattr(r, "role", None) == role:
            return (getattr(r, "output", None) or {}) if getattr(r, "status", None) == "ok" else {}
    return {}


def apply_guardrails(
    decision: str,
    confidence: Optional[float],
    analyst_results: Sequence[Any],
    conf_floor: float = DEFAULT_CONF_FLOOR,
) -> tuple[str, Optional[str]]:
    """Return (decision, override_reason). Only downgrades approve→veto.

    analyst_results must be a sequence of objects with .role, .status, .output
    attributes (AgentResult or compatible). The guardrails key on the Flow,
    Technical, and Regime analyst verdicts — they are consistent enum values
    regardless of which caller built the candidate."""
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

    return decision, None


def normalize_quant(score, strategy: str) -> float:
    """Rescale a caller's raw score to a common 0-1 strength for the Risk prompt."""
    s = float(score or 0.0)
    n = s / 100.0 if strategy in MAGNITUDE_STRATEGIES else (s + 5.0) / 10.0
    return max(0.0, min(1.0, n))
