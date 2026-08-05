# ADR-AF-005 — Provider Router Layer: Formalization and Multi-Provider Expansion

**Date:** 2026-07-29
**Status:** DECIDED. Permanent, per `AGENT_FIRM_GOVERNANCE.md`'s decision-record discipline.
**Extends:** `docs/superpowers/specs/2026-07-08-firm-provider-abstraction-design.md` ("Status:
Approved — locked, pending implementation plan"; implemented under
`Audit/PROVIDER_RESILIENCE_COMPLETION_2026-07-10.md` and the 2026-07-13 RCA hardening referenced
throughout `engine/agent_firm/providers/`). This ADR does not reopen or re-decide that design — it
extends its scope and formalizes a piece of it (§4a "Future providers") that was approved but never
exercised.
**Companion document:** `docs/agent_firm/AGENT_FIRM_PROVIDER_LAYER_ARCHITECTURE.md` — component
diagram, sequence diagram, responsibility matrix, failure-mode analysis, deployment
recommendations, repository structure, and migration strategy.

---

## The Question

Operational planning for provider expansion (adding OpenAI and Gemini as additional Agent Firm
LLM providers) asked for an "architecture update" introducing a Provider Layer that separates
investment-review logic from provider infrastructure concerns — selection, failover, retry,
timeout, quota, health, response normalization, caching — behind a stable interface, with new
providers addable as adapters only.

Read literally, this describes doing something that does not yet exist. Read against the actual
repository (`engine/agent_firm/providers/`), nearly all of it already exists, decided and
implemented on 2026-07-08 through 2026-07-13: `router.py` (selection + failover), `registry.py` +
`factory.py` (construction, provider-name-driven, zero hardcoded provider set), `circuit_breaker.py`
(per-provider health/circuit state), `governor.py` (adaptive quota-rate pacing, R-7 Tier 1),
`classification.py` + `errors.py` (uniform failure taxonomy across SDK and subprocess-CLI
providers), `events.py` + `alerts.py` + `metrics.py` (observability). `firm.py` already depends only
on the `FirmLLMProvider` protocol (`providers/base.py`) — it has never called `ClaudeProvider` or
`ZAIProvider` directly.

The real, open question is narrower: **what is actually missing, or actually undecided**, relative
to the requested target architecture — and does closing that gap require a new architectural
decision, or just execution of a decision already on record?

## Decision

**Three things are net-new and are decided by this ADR. Everything else the request describes is
already-decided prior work, reaffirmed here without change.**

### 1. A Cache component is added to the Provider Router layer (net new)

No caching layer exists today — every `generate()` call reaches a live provider. This ADR adds a
**disabled-by-default, per-(provider, prompt-hash) response cache** sitting inside the Router,
between provider selection and the adapter call, keyed on a hash of `(provider name, model,
messages)` with a short TTL. It exists to blunt duplicate-candidate bursts (the same ticker
re-scored by more than one strategy in the same cycle) and to give a standalone-service deployment
(§4 below) a cheap first line of defense against upstream cost/rate pressure — not as a correctness
mechanism the Agent Firm may rely on. Agent Firm business logic must not assume caching is active;
disabling it must never change a decision, only its cost and latency.

### 2. The Agent Firm's four internal responsibilities are named and are a documentation
   decomposition, not a code restructuring

The requested layering — Prompt Builder, Evidence Aggregator, Consensus Engine, Review Policy —
is adopted as the **canonical vocabulary** for what already exists inside `engine/agent_firm/`
(excluding `providers/`), mapped as follows:

| Requested layer | Existing implementation |
|---|---|
| Prompt Builder | `prompts/*.md` (one template per role) + each `agents/*.py`'s prompt-loading + JSON-envelope construction |
| Evidence Aggregator | `firm.py::_run_analysts` — the technical/flow/regime/news LangGraph node, each consuming its own typed Tier 1 context field off `SignalCandidate` (ADR-AF-002) |
| Consensus Engine | `firm.py::_run_bull` / `_run_bear` — the bull/bear debate nodes, each conditioned on the prior nodes' `AgentResult`s |
| Review Policy | `firm.py::_run_risk` + `guardrails.py` (`apply_guardrails`, `normalize_quant`) — the Risk agent's LLM decision plus the deterministic, LLM-cannot-override-only-downgrade guardrail pass |

No file is renamed, split, or moved by this ADR. The mapping exists so that "Agent Firm never
contains provider-specific code" (constraint 6 of the request) has a checkable meaning: none of the
four responsibilities above, nor their combined orchestration in `firm.py`'s `StateGraph`, may name
a provider, import a `providers.*` submodule other than `providers.base.FirmLLMProvider` (the
protocol) and `providers.factory.build_router` (the default-construction entry point), or branch on
`provider ==`. `firm.py` today already satisfies this; it is the standing bar future changes are
held to.

### 3. OpenAI and Gemini adapters are in-scope, additive work — not a design decision

The 2026-07-08 design doc's §4a ("Future providers") already specifies the entire adapter-addition
contract: implement `FirmLLMProvider`, `@register("openai")` / `@register("gemini")`, add env vars,
add the name to `AGENT_FIRM_PROVIDER_ORDER`. It states explicitly that this requires **no change**
to `router.py`, `factory.py`, config validation, `firm.py`, any `agents/*.py` module, prompts, or
schemas. This ADR reaffirms that contract as still correct and adds only the operational detail the
original design left open because it had no multi-vendor precedent yet at the time: response
normalization variance and health-check cost, both addressed in the companion architecture
document's Responsibility Matrix and Failure-Mode Analysis.

## Why Not a Bigger Change

The request's premise — "the current Agent Firm communicates directly with individual LLM
providers" — is not true of this repository and has not been true since the 2026-07-08 design was
implemented. Treating the request as license to rebuild `providers/` would violate this
repository's own governance stance (`docs/roadmap/DECISION_LOG.md`'s pattern, applied here):
a canonical, already-decided design is corrected only by a superseding record when its *content*
is wrong, not rewritten because a later request assumed it didn't exist. Nothing in the router,
registry, factory, circuit breaker, governor, classification, or event/alert/metrics modules is
found to be wrong; this ADR closes the one real gap (Cache), formalizes one already-approved but
unexercised extension point (adapters), and gives the Agent Firm's internal layering a name it did
not previously have in writing.

## Consequences

- `docs/agent_firm/AGENT_FIRM_PROVIDER_LAYER_ARCHITECTURE.md` (companion doc) is the authoritative
  reference for the diagrams, responsibility matrix, failure-mode table, deployment
  recommendation, repository structure, and migration steps this ADR's three decisions require.
- `engine/agent_firm/providers/cache.py` does not exist yet; its introduction is **the only code
  change this ADR requires**, and is additive (new module + a router constructor parameter
  defaulting to disabled) — no existing provider, router, or firm code path changes behavior when
  the cache is left at its default-off setting.
- `engine/agent_firm/providers/openai.py` and `.../gemini.py` do not exist yet; their introduction
  is deferred until a provider is actually contracted for production use — this ADR removes any
  architectural blocker to adding them but does not itself add them.
- The Production Engine (`scheduler/`, `engine/` outside `agent_firm/`, `monitor.py`,
  `paper_trade.py`, `data/`, `routes/`) is untouched by this ADR, consistent with the request's
  explicit constraint; nothing in `engine/agent_firm_context.py` (the ADR-AF-002 context-ownership
  boundary between Production Engine and Agent Firm) changes.
- `docs/superpowers/specs/2026-07-08-firm-provider-abstraction-design.md` is not edited (this
  repository's convention: superseded/extended by a new dated record, not a silent edit); this ADR
  is that record for the "Future providers" section specifically.

## Required Documentation Updates

- None to existing canonical documents beyond this ADR and its companion — the 2026-07-08 design
  doc's content remains correct as written.

## Required Implementation Changes (future work, not performed by this ADR)

- Add `engine/agent_firm/providers/cache.py` (see companion doc §"Cache") — new module, Router
  constructor gains an optional `cache: ResponseCache | None = None` parameter, default `None`
  (disabled). No existing call site changes.
- Add `engine/agent_firm/providers/openai.py` / `.../gemini.py` when a provider is actually
  contracted — each a self-contained `@register(...)` adapter, per the existing "Future providers"
  contract. No router, factory, firm, or schema change required per provider added.
