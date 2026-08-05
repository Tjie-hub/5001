# ADR-AF-004 — Versioning Contract (Resolves Blocker B4)

**Date:** 2026-07-29
**Status:** DECIDED. Permanent, per `AGENT_FIRM_GOVERNANCE.md`'s decision-record discipline.
**Resolves:** `AF2_IMPLEMENTATION_READINESS.md` Blocker B4 — the tension between
`AGENT_FIRM_GOVERNANCE.md`'s literal versioning rule and `AF1_CONTEXT_API.md`'s framing of the
bundled-vs-separate-parameters question as "not architectural."

---

## The Question

`AGENT_FIRM_GOVERNANCE.md`: "**MAJOR** — any change to `evaluate`/`evaluate_staged`/`reset_market_ctx`'s
signature..." — stated without a carve-out for additive/optional parameters, unlike the adjacent rule for
`SignalCandidate`/`AgentDecision` field changes, which explicitly exempts additive changes ("a new
optional field... is MINOR"). Is adding a new parameter to `evaluate()` to carry Tier 1 context objects
(ADR-AF-002) MAJOR, MINOR, or PATCH — and is the existing rule correct as written, or does it need
amendment?

## Decision

**The existing rule is correct as written and is NOT amended. Any signature change to `evaluate`,
`evaluate_staged`, or `reset_market_ctx` — including an additive, optional, defaulted parameter — remains
MAJOR.**

### Why This Rule Is Kept Stricter Than the Data-Class Field Rule

A new optional field on `SignalCandidate`/`AgentDecision` is inert until a caller chooses to read or
write it — every existing call site continues to compile and behave identically with zero code changes.
A new parameter on `evaluate()` is different in kind, not just degree: **any caller that wants the new
behavior must edit its call site**, even if the parameter is optional and old call sites still compile
unchanged. The call surface itself changes shape. `AGENT_FIRM_GOVERNANCE.md`'s asymmetry between the two
rules is deliberate and correct, not an oversight — this ADR affirms it rather than smoothing it away.

### How This Migration Avoids Triggering the Rule

Per ADR-AF-002, Tier 1 context objects are assembled by `engine/agent_firm_context.py` and attached
directly to `SignalCandidate` instances as new optional fields — `SignalCandidate.technical:
TechnicalContext | None`, `.flow: FlowContext | None`, `.regime: RegimeContext | None`, `.news:
NewsContext | None`, and, for the four batch-level objects, `.market: MarketContext | None`, `.portfolio:
PortfolioContext | None`, `.risk_limits: RiskContext | None`, `.execution: ExecutionContext | None` —
the same batch-level object reference repeated across every candidate in a scan cycle's list (cheap: a
shared Python object reference, not a deep copy, since these are immutable Pydantic instances constructed
once per cycle).

**`evaluate(candidates: list[SignalCandidate]) -> list[AgentDecision]`'s signature does not change at
all.** This is not a workaround that dodges the spirit of the versioning rule — it is the same mechanism
`SignalCandidate.indicators` already used successfully (an optional field extension, MINOR per the
existing, unamended rule), applied to every new object this program introduces. The rule in
`AGENT_FIRM_GOVERNANCE.md` never needs to be invoked for this migration, because the migration is
designed not to need it.

### Classification of This Migration

**MINOR**, in full, under `AGENT_FIRM_GOVERNANCE.md`'s existing, unamended text: every change is a new
optional field on `SignalCandidate` (per the rule's own explicit MINOR carve-out) or a new optional field
on `AgentDecision` (`size_tier`, alongside the repurposed-but-type-unchanged `size_hint` per
ADR-AF-003). No existing field is removed or changes type; the decision-lifecycle enum is untouched;
`evaluate`/`evaluate_staged`/`reset_market_ctx`'s signatures are byte-for-byte unchanged.

---

## Consequences

- `AF1_CONTEXT_API.md`'s "Open Item for AF-2" ("bundled `EvaluationContext` parameter or five separate
  named parameters... left to AF-2") is **superseded, not merely resolved** — neither option in that
  framing is chosen; a third option (attach to `SignalCandidate`) avoids the question the open item posed.
  This is recorded here as a supersession, consistent with this repository's own append-only-decision
  convention (`docs/roadmap/DECISION_LOG.md`'s pattern, applied to the Agent Firm document set).
- Any future proposal to add a genuinely new parameter to `evaluate`/`evaluate_staged`/`reset_market_ctx`
  (for a reason this ADR's `SignalCandidate`-extension pattern cannot accommodate) must be evaluated as
  MAJOR under the unamended rule, with the explicit owner sign-off `AGENT_FIRM_GOVERNANCE.md`'s Release
  Policy already requires for MAJOR changes — this ADR does not weaken that requirement for anything
  outside the specific migration described above.

## Required Documentation Updates

- `AF1_CONTEXT_API.md` — its "Open Item for AF-2" section gains a one-line pointer to this ADR as the
  superseding resolution; the document itself is not edited otherwise (per this repository's
  never-delete convention, and per `AF1_CONTEXT_API_V2_SPEC.md`'s own stated plan to mark it superseded
  only once V2 is actually implemented).
- `AGENT_FIRM_GOVERNANCE.md` — **no amendment required.** This ADR's decision is to affirm the existing
  text, not change it; recorded here rather than as an edit to that document, consistent with governance
  documents being amended only by a superseding record when their *content* changes, not when a later
  decision merely confirms them.
- `AF2_IMPLEMENTATION_READINESS.md` Part 5 (Blocker B4) — marked resolved, referencing this ADR.

## Required Implementation Changes (for AF-2, not performed by this ADR)

- `engine/agent_firm/schemas.py::SignalCandidate` gains the eight new optional fields listed above.
- `engine/agent_firm/schemas.py::AgentDecision` gains `size_tier: Optional[str] = None`; `size_hint`'s
  docstring/comment updated to reflect its repurposed meaning per ADR-AF-003 (no type change).
- No change to `evaluate`, `evaluate_staged`, or `reset_market_ctx`'s function signatures anywhere in
  `engine/agent_firm/firm.py`.
