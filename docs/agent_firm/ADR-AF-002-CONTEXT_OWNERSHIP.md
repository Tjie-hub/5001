# ADR-AF-002 — Context Ownership (Resolves Blocker B3)

**Date:** 2026-07-29
**Status:** DECIDED. Permanent, per `AGENT_FIRM_GOVERNANCE.md`'s decision-record discipline.
**Resolves:** `AF2_IMPLEMENTATION_READINESS.md` Blocker B3 — the contradiction between
`AF1_CONTEXT_API.md`'s own text ("Production Engine assembles these six objects... and passes them into
`evaluate`/`evaluate_staged`") and `AF1_REMEDIATION_PLAN.md`/`AF1_IMPLEMENTATION_BACKLOG.md`'s affected-file
lists (`engine/agent_firm/firm.py::_build_context()`), which placed assembly on the opposite side.

---

## The Contradiction, Restated

Two prior documents disagree about which side of the Agent-Firm/Production-Engine boundary builds the
typed context objects an evaluation consumes. This matters concretely: if assembly stays inside
`engine/agent_firm/`, implementing it requires Agent Firm to import Production Engine's internal compute
modules directly (`engine/indicators.py`, `engine/technicals.py`, `engine/regime_filter.py`,
`flow_filter.py`) — new forward dependencies `AGENT_FIRM_DEPENDENCY_AUDIT.md` never catalogued, working
against `AGENT_FIRM_GOVERNANCE.md`'s stated eventual repository-split goal.

## Decision

**Context assembly is split by tier, not assigned a single blanket owner — this split is itself the
resolution, not a hedge:**

### Tier 1 (pre-evaluation, input to `evaluate`/`evaluate_staged`) — **Production Engine assembles**

`MarketContext`, `OpportunityContext`, `TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext`,
`PortfolioContext`, `RiskContext`, `ExecutionContext`, `SessionContext` are all constructed **before**
Agent Firm's evaluation graph runs, from data and functions that already live in Production Engine. This
matches `AF1_CONTEXT_API.md`'s own original text and the Responsibility Matrix's Primary Principle ("if
it's about running the system that produces and acts on signals, it's Production Engine's").

**Location:** a new module, `engine/agent_firm_context.py` — deliberately placed at the top level of
`engine/`, **outside** `engine/agent_firm/`, so the ownership boundary is visible in the file tree, not
just in documentation. This module imports both Production Engine's compute functions (per ADR-AF-001)
and Agent Firm's type definitions (`engine/agent_firm/schemas.py`) — it is Production Engine code that
happens to produce Agent-Firm-shaped output, not Agent Firm reaching into Production Engine. This mirrors
`engine/edge_enrich.py`'s own existing shape exactly: a Production Engine module that assembles
veto-ready dicts for `engine/veto.py` to consume, without `engine/veto.py` ever importing the raw source
tables itself.

**Caller:** `scheduler/scanner.py`/`scheduler/jobs.py` call `engine/agent_firm_context.py`'s assembly
functions, attach the results to `SignalCandidate` instances (see ADR-AF-004 for exactly how), and only
then call `evaluate`/`evaluate_staged` — the same call sites that already exist today, unchanged in
number or position, just with an added assembly step before the call.

### Tier 2 (post-analyst, pre-risk) — **Agent Firm assembles**

`ConsensusContext` is the sole exception: it depends on the four analyst agents' *already-produced*
`AgentResult`s, which do not exist until Agent Firm's own evaluation graph has partially run. It cannot
be assembled before `evaluate`/`evaluate_staged` is called, by definition. **Location: unchanged from the
original design** — `engine/agent_firm/guardrails.py::build_consensus_summary()`, called from
`firm.py::_run_risk()` between the analyst nodes and the Risk agent node. This is not a violation of the
Tier 1 principle above; it is a different tier with a different, necessary owner, named as such rather
than forced into the same bucket.

## Who Owns Type Definitions (Schema/Shape)

**Agent Firm — `engine/agent_firm/schemas.py`.** Every Tier 1 and Tier 2 object's Pydantic class is
defined here, alongside the existing `SignalCandidate`/`AgentResult`/`AgentDecision`. Rationale: these
types are Agent Firm's *input contract* — the same reasoning `AGENT_FIRM_INTERFACE_SPEC.md` already
applies to `SignalCandidate` itself (Production Engine constructs instances of a type Agent Firm defines
and versions). This is not a new pattern; it is the existing `SignalCandidate` pattern extended to the
new objects, and it means `engine/agent_firm_context.py` (Tier 1's Production-Engine-owned assembler)
depends on Agent Firm's schema module for types — already an accepted, existing dependency direction per
`AGENT_FIRM_DEPENDENCY_AUDIT.md` §1 (Production Engine → Agent Firm, classified "Public API").

## Who Owns Serialization

**Agent Firm**, following from type-definition ownership — these are Pydantic models, serialized via the
same `model_dump()`/`json.dumps()` pattern every existing agent already uses for `SignalCandidate`. **No
new serialization mechanism is introduced.**

**Persistence, decided explicitly rather than left implicit:** Tier 1/Tier 2 context objects are
**ephemeral** — constructed fresh per evaluation (Tier 1: per scan cycle for batch-level objects, per
candidate for the rest; Tier 2: per candidate, post-analyst), consumed only in-memory by the LLM prompt
construction step, and **never persisted** to `agent_decisions`/`agent_traces` or any other table. This
closes Gap G4 from `AF2_IMPLEMENTATION_READINESS.md` with a permanent answer: if audit-reproducibility
(the ability to later ask "what indicators did the Technical agent actually see for this decision")
is judged valuable, that is a distinctly-scoped future decision for AF-3 or later, requiring its own ADR
— it is not silently assumed either way by this decision.

## Who Owns Lifecycle

Follows assembly ownership per tier:
- **Tier 1 batch-level objects** (`MarketContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`)
  — **Production Engine**, cached once per scan cycle by `engine/agent_firm_context.py`, matching
  `firm.py`'s existing `_market_ctx`/`reset_market_ctx()` cache lifecycle exactly (that cache's *location*
  moves to the new module; its *behavior* — reset once per scan batch — is unchanged).
- **Tier 1 per-candidate objects** (`TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext`,
  `OpportunityContext`, `SessionContext`) — **Production Engine**, constructed fresh per candidate by the
  same module.
- **Tier 2** (`ConsensusContext`) — **Agent Firm**, constructed fresh per candidate, per evaluation, by
  `firm.py`.

---

## Required Documentation Updates

- `AF1_CONTEXT_API_V2_SPEC.md` — add one sentence to Part 2 (already anticipated as an "open item"
  location) recording this tiered assembly-ownership decision; the "Compatibility Strategy" section's
  claim that "there is no code to migrate" is unaffected and remains accurate.
- `AF1_CONTEXT_OBJECT_CATALOG.md` — every object's "Producer" column is unaffected (already correctly
  attributed to Production Engine compute functions); this ADR clarifies *assembly location*, a
  previously-missing column, addressed by reference to this document rather than by rewriting the
  Catalog's table structure.
- `AGENT_FIRM_DEPENDENCY_AUDIT.md` — **no new entry required.** Because Tier 1 assembly lives in
  `engine/agent_firm_context.py` (Production Engine, outside `engine/agent_firm/`), no new Agent-Firm →
  Production-Engine forward dependency is created. This is the direct, intended consequence of choosing
  option (a) from `AF2_IMPLEMENTATION_READINESS.md` Part 4 over option (b).
- `AF2_IMPLEMENTATION_READINESS.md` Part 4 (Blocker B3) — marked resolved, referencing this ADR.
- `AF2_WORK_PACKAGE_SEQUENCE.md`'s `WP0a` — marked resolved; WP1/WP2/WP3/WP4/WP8/WP9's "affected files"
  lists should read `engine/agent_firm_context.py` (new) instead of
  `engine/agent_firm/firm.py::_build_context()` for their assembly-side changes.

## Required Implementation Changes (for AF-2, not performed by this ADR)

- Create `engine/agent_firm_context.py`.
- `engine/agent_firm/firm.py::_build_context()` is **deleted**, not "replaced in place" — its 7 raw SQL
  queries and the `_market_ctx` cache move to the new module in typed/derived form (per ADR-AF-001 and
  the Catalog).
- `evaluate`/`evaluate_staged`'s own internals stop calling `_build_context()`; they receive
  already-assembled context attached to the `SignalCandidate`s passed in (see ADR-AF-004).
- `scheduler/scanner.py`/`scheduler/jobs.py`'s candidate-construction call sites gain a call to
  `engine/agent_firm_context.py`'s assembly functions before constructing `SignalCandidate` instances.
