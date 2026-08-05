"""engine/position_sizing.py — Production-Engine-owned, sole authority for `agent_size_hint`.

Ownership (docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md): exactly one function in the entire
codebase is permitted to write a final numeric value for `agent_size_hint`. Before this module
existed, `scheduler/scanner.py` had two independent, unconditional write sites (the edge-veto
stage's deterministic `size_mult`, and the Agent Firm gate's LLM-derived `size_hint`/blind
default) with no precedence rule between them — the second always silently clobbered the first
whenever both were active, discarding a computed, validated edge score in favor of a value that
carries no information. `resolve_size_hint()` below replaces both write sites: each stage now only
*contributes an input* (`edge_score`, `size_tier`); this function combines them exactly once per
candidate, per the ADR's own stated precedence, so there is never a second write to silently
clobber a first.
"""

from __future__ import annotations

from typing import Optional

# The same numeric bands `risk_v2.md` used to hardcode into the LLM's own output, now living in
# code instead (ADR-AF-003) — the LLM recommends a qualitative tier; this module owns the number.
_TIER_MODULATION = {"reduce": 0.7, "normal": 1.0, "increase": 1.15}
_TIER_BASE_VALUE = {"reduce": 0.5, "normal": 1.0, "increase": 1.2}

DEFAULT_SIZE_HINT = 1.0  # preserved, pre-existing default — never silently changed
MIN_SIZE_HINT = 0.0
MAX_SIZE_HINT = 1.5


def _clamp(value: float) -> float:
    return max(MIN_SIZE_HINT, min(MAX_SIZE_HINT, value))


def resolve_size_hint(
    edge_score: Optional[float] = None,
    size_tier: Optional[str] = None,
    consensus: Optional[object] = None,
    execution: Optional[object] = None,
) -> float:
    """The sole writer of `agent_size_hint`, per ADR-AF-003. Bounded to [0.0, 1.5] by construction.

    `consensus`/`execution` are accepted because ADR-AF-003's declared signature names them, but
    the ADR's own precedence rule ("The Rule" section) never references either in any of its four
    cases below — they are not combined into the returned value here. Using them would be a new,
    undecided behavior this function does not silently invent; a future ADR amendment would need
    to state how they participate before this function's precedence rule changes.

    Precedence (ADR-AF-003, exact, in order):
      1. `edge_score` and `size_tier` both present — `edge_score` is the base; `size_tier`
         modulates it within a bounded band (reduce x0.7, normal x1.0, increase x1.15), clamped.
         Neither signal discards the other; both are inputs to this one function, never two
         competing writers.
      2. Only `edge_score` present (Agent Firm inactive, degraded, or the candidate was vetoed) —
         returned directly, rounded and clamped.
      3. Only `size_tier` present (`EDGE_SCORE_MODE=off`) — mapped to a fixed base value
         (reduce=0.5, normal=1.0, increase=1.2), clamped.
      4. Neither present — `DEFAULT_SIZE_HINT` (1.0), the pre-existing default, preserved as the
         fallback rather than silently changed.

    An unrecognized `size_tier` string is treated the same as `"normal"` (fail-soft, matching this
    repository's existing convention of treating an unrecognized enum value as the neutral case
    rather than raising).
    """
    if edge_score is not None and size_tier is not None:
        return round(_clamp(edge_score * _TIER_MODULATION.get(size_tier, 1.0)), 2)
    if edge_score is not None:
        return round(_clamp(edge_score), 2)
    if size_tier is not None:
        return round(_clamp(_TIER_BASE_VALUE.get(size_tier, DEFAULT_SIZE_HINT)), 2)
    return DEFAULT_SIZE_HINT
