# AF-2 Architecture Certification

**Date:** 2026-07-29
**Basis:** `ADR-AF-001-DETERMINISTIC_OWNERSHIP.md`, `ADR-AF-002-CONTEXT_OWNERSHIP.md`,
`ADR-AF-003-SIZING_OWNERSHIP.md`, `ADR-AF-004-VERSIONING_CONTRACT.md`, and the full document trail those
four ADRs resolve (`AF2_IMPLEMENTATION_READINESS.md` Blockers B1-B4).
**Note on document status:** consistent with this repository's append-only-decision convention (the same
discipline `docs/roadmap/DECISION_LOG.md` uses elsewhere), the four ADRs **supersede** the specific
sections of `AF1_REQUIRED_CONTEXT_OBJECTS.md`, `AF1_CONTEXT_API_V2_SPEC.md`,
`AF1_CONTEXT_OBJECT_CATALOG.md`, `AF1_REMEDIATION_PLAN.md`, `AF1_IMPLEMENTATION_BACKLOG.md`, and
`AF2_WORK_PACKAGE_SEQUENCE.md` that conflicted with their decisions — those documents are not edited by
this certification; each ADR's "Required Documentation Updates" section is the authoritative record of
what changed and why. Applying those edits is AF-2 implementation work, not an architecture decision, and
is correctly out of scope here.

---

## Consolidated Ownership Table

Every responsibility named in the Definition of Done, one owner each.

| Responsibility | Owner | Concrete location | Resolved by |
|---|---|---|---|
| **Deterministic calculations** — indicators, market regime, technical direction, flow verdicts, catalyst presence, statistical calculations, edge scoring | **Production Engine** | `engine/indicators.py`, `engine/chart_indicators.py`, `engine/technicals.py`, `engine/regime_filter.py`, `flow_filter.py`, `engine/catalyst.py`, `engine/edge_score.py`, `engine/wf_edge.py`, `analytics.py` (post-hoc stats) | `AF1_COMPUTATION_BOUNDARY_POLICY.md`; canonical-producer disambiguation by `ADR-AF-001` |
| **Reasoning** — verdict synthesis, narrative, argumentation, confidence calibration, qualitative sizing recommendation | **Agent Firm** | `engine/agent_firm/agents/*.py`, `engine/agent_firm/prompts/*.md` | `AF1_COMPUTATION_BOUNDARY_POLICY.md`; `size_tier` (not `size_hint`) confirmed as the sizing-adjacent boundary by `ADR-AF-003` |
| **Context production** (computing the deterministic *values* that populate context objects) | **Production Engine** | Same modules as "Deterministic calculations," row above | `ADR-AF-001` |
| **Context assembly — Tier 1** (pre-evaluation: `MarketContext`, `OpportunityContext`, `TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`, `SessionContext`) | **Production Engine** | New module `engine/agent_firm_context.py` (outside `engine/agent_firm/` by design) | `ADR-AF-002` |
| **Context assembly — Tier 2** (post-analyst: `ConsensusContext`) | **Agent Firm** | `engine/agent_firm/guardrails.py::build_consensus_summary()`, called from `firm.py::_run_risk()` | `ADR-AF-002` — a principled exception, not a contradiction: this tier cannot exist before Agent Firm's own analyst calls run |
| **Context object type definitions (schema/shape)** | **Agent Firm** | `engine/agent_firm/schemas.py`, extending `SignalCandidate`/`AgentDecision` | `ADR-AF-002`, `ADR-AF-004` |
| **Context serialization** | **Agent Firm** | Pydantic `model_dump()`/`json.dumps()`, same mechanism as today's `SignalCandidate` | `ADR-AF-002` |
| **Context persistence** | **Neither — ephemeral by design** | Constructed in-memory per evaluation, never written to `agent_decisions`/`agent_traces` | `ADR-AF-002` (explicit decision, not a silent default) |
| **Sizing — executable multiplier** | **Production Engine** | New module `engine/position_sizing.py::resolve_size_hint()` — the **only** writer of `agent_size_hint`, called exactly once per candidate per scan cycle | `ADR-AF-003` |
| **Sizing — qualitative recommendation input** | **Agent Firm** | Risk agent's `size_tier` output (`"reduce"`/`"normal"`/`"increase"`) | `ADR-AF-003` |
| **Execution** — opening/closing paper trades, SL/TP, exit kernel | **Production Engine** | `paper_trade.py` (unchanged) | `AF1_RESPONSIBILITY_MATRIX.md`, not reopened by this review |
| **Persistence — infrastructure** (DB file, connection, `busy_timeout`/WAL, backup/restore) | **Production Engine** | `data/db.py::connect()` (unchanged) | `AF1_RESPONSIBILITY_MATRIX.md`, not reopened |
| **Persistence — schema** (`agent_decisions`/`agent_traces`/`provider_events`) | **Agent Firm** | Per `AF1_SCHEMA_OWNERSHIP_DECISION.md` (unchanged, not reopened by this review) | `AF1_SCHEMA_OWNERSHIP_DECISION.md` |
| **Scheduling** — cron timing, job registration | **Production Engine** | APScheduler, `scheduler/` (unchanged) | `AF1_RESPONSIBILITY_MATRIX.md`, not reopened |
| **Risk enforcement — deterministic veto rules** | **Production Engine** (as policy authorship; two pipeline-appropriate execution points) | `engine/veto.py` (pre-LLM, physically in Production Engine); `engine/agent_firm/guardrails.py` (post-LLM, physically colocated with Agent Firm because it depends on Agent Firm's own analyst output, per the Tier 2 principle above) | `AF1_COMPUTATION_BOUNDARY_POLICY.md`, `AF1_FAILURE_CONTRACT.md` §5; execution split explained, not left ambiguous |

**Every row has exactly one owner named.** Where a responsibility legitimately splits by pipeline stage
(Context assembly, Risk enforcement), the split is a principled tier distinction stated explicitly in the
relevant ADR, not two owners sharing one undifferentiated responsibility.

---

## Definition of Done — Verification

| Criterion | Status | Evidence |
|---|---|---|
| Every deterministic calculation has one owner | **Met** | `ADR-AF-001` names the canonical producer for regime, technical direction, and catalyst status — the three calculations where a second, competing implementation risk was found; every other deterministic calculation already had an unambiguous single owner per `AF1_CONTEXT_OBJECT_CATALOG.md` |
| Every context object has one producer | **Met** | Consolidated table above; `ADR-AF-001`'s passthrough design means `RegimeContext`/`TechnicalContext`/`NewsContext` each have exactly one producer function per field, not two disagreeing ones |
| Every runtime field has one writer | **Met** | `agent_size_hint` — the one field with a confirmed, live two-writer collision — now has exactly one writer, `resolve_size_hint()`, per `ADR-AF-003` |
| No silent overwrite exists | **Met** | `ADR-AF-003` removes both of the original two write sites and replaces them with one call site with an explicit, tested precedence rule for every input-presence combination |
| Agent Firm performs reasoning only | **Met** | Verified per-agent-output in `AF2_IMPLEMENTATION_READINESS.md` Part 7, unchanged by this review's decisions; `ADR-AF-003` closes the one remaining gap (`size_hint` → `size_tier`) that pre-existed this review's blocker set |
| Production Engine remains the sole operational engine | **Met** | Execution, scheduling, and infrastructure-persistence ownership were never in question and are not reopened here; `ADR-AF-003` additionally makes Production Engine the sole owner of executable sizing, closing the one place where "operational" and "LLM-influenced" had blurred together |

---

## Certification Statement

**The architecture is CERTIFIED.**

All four blockers identified in `AF2_IMPLEMENTATION_READINESS.md` (B1: duplicate deterministic context;
B2: sizing ownership collision; B3: context assembly ownership contradiction; B4: versioning-contract
ambiguity) have been resolved by explicit, permanent architecture decisions (`ADR-AF-001` through
`ADR-AF-004`). Every responsibility in the Definition of Done has exactly one owner. No responsibility
was found, in this pass, to still have an ambiguous or duplicated owner.

**AF-2 implementation may begin.**

Implementation should proceed against the decision set as it now stands: `AF1_COMPUTATION_BOUNDARY_POLICY.md`
for what may never be computed by an LLM, `AF1_CONTEXT_OBJECT_CATALOG.md` as amended by `ADR-AF-001`'s
corrections for what each context object contains, `ADR-AF-002` for where each object is assembled,
`ADR-AF-003` for how sizing is resolved, `ADR-AF-004` for how the new fields reach `evaluate()` without a
MAJOR version event, and `AF2_WORK_PACKAGE_SEQUENCE.md`/`AF2_TEST_STRATEGY.md`/`AF2_RISK_REGISTER.md` for
execution order, verification, and rollback discipline — each of those three documents' specific
`guardrails.py`-as-sizing-owner references superseded by `ADR-AF-003`, as recorded in that ADR's own
"Required Documentation Updates" section.

No further architecture decision is required before implementation starts. Any ambiguity discovered
during AF-2 implementation itself should be resolved the same way this review resolved B1-B4: a new,
dated, superseding ADR — never a silent implementation-time choice.
