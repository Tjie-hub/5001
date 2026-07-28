# Agent Firm — Implementation Roadmap

**Date:** 2026-07-28
**Basis:** `AGENT_FIRM_ARCHITECTURE.md`'s blocker list, `AGENT_FIRM_DEPENDENCY_AUDIT.md`.
**Constraint:** this is a planning document only — no code is implemented as part of producing it.
Each milestone below closes specific, named blockers.

---

## AF-1 — Foundation

**Goal:** establish Agent Firm as a nameable, independently testable unit within the current
repository, without changing any behavior.
- Introduce the data-access layer for `agent_decisions`/`agent_traces`/`provider_events`
  (Blocker 1) — read functions only at this stage, no schema change.
- Redirect `scheduler/scanner.py:1070` and `routes/backtest.py:835`'s raw SQL through the new layer.
- Add Agent Firm's own logging setup module (Blocker 4).
- No interface behavior changes; existing tests must pass unmodified except where they directly
  asserted raw SQL shape (should be none).

## AF-2 — Interface Stabilization

**Goal:** make `AGENT_FIRM_INTERFACE_SPEC.md` enforceable, not just documented.
- Formalize `evaluate`/`evaluate_staged`/`reset_market_ctx` as the versioned public contract (see
  `AGENT_FIRM_GOVERNANCE.md`'s versioning policy).
- Add the three `/api/agent/*` operations (status, set-mode, audit) to the same formal contract
  (Blocker 3), backed by AF-1's data layer.
- Replace test-layer package-attribute monkeypatching with an official test double at the interface
  boundary (Blocker 5).
- Exit criterion: every Production Engine call site in the Dependency Audit's §1 table is either
  "Public API" against the now-versioned contract, or explicitly deprecated with a migration note.

## AF-3 — Provider Abstraction Hardening

**Goal:** make the provider layer (Z.ai/Claude, circuit breaker, governor, quota routing) something
that can be extended (a third provider) or replaced without touching the interface above it.
- Formalize `providers/base.py`'s `ProviderCapabilities`/`ProviderResponse` as Agent Firm's own
  internal-but-stable extension point.
- Close the redaction/atomic-write gaps already identified in this session's security review that
  are adjacent to this layer (`_write_token_atomic()` landing, per
  `Audit/OWNER_DECISION_PACKAGE.md` Decision 4) — cross-referenced here since it's the same code area,
  not duplicated as new Agent Firm work.
- No externally-visible change to `evaluate`/`evaluate_staged`.

## AF-4 — Execution Engine (Tooling Boundary)

**Goal:** close Blocker 2 — LLM tools stop opening the database file directly.
- Define the narrow, read-only data API `tools/news_lookup.py`/`tools/sqlite_query.py` should call
  instead of `data.db.connect` directly.
- Decide, explicitly, what query surface actually needs to remain available to agents (this is the
  one AF milestone with real product-scope risk — narrowing what agents can query may change actual
  agent behavior, not just internal wiring).

## AF-5 — Evaluation Pipeline Portability

**Goal:** verify the LangGraph evaluation pipeline (`firm.py`, `agents/`) has zero remaining
Production-Engine-specific assumptions beyond the AAF-1–AF-4 boundary layers.
- Audit `_build_context`, `_run_analysts`, and each agent module for any remaining direct coupling
  not already caught in the Dependency Audit.
- This milestone is primarily verification, not new construction — confirm AF-1 through AF-4 actually
  closed what they claimed to.

## AF-6 — Observability

**Goal:** Agent Firm can be operated and debugged without Production Engine's own monitoring stack.
- Agent Firm's own metrics/health surface (today's `providers/metrics.py::provider_stats()` is close
  but reachable only via Production Engine's routes — see Blocker 3, closed in AF-2).
- Decide whether Agent Firm needs its own alerting path independent of `utils.telegram.send_telegram`,
  or whether that shared utility (correctly classified as "acceptable to keep" in the Dependency
  Audit) remains the right long-term choice.

## AF-7 — Production Certification

**Goal:** Agent Firm passes its own version of the certification process this Production Engine v1
just completed — architecture review, dependency audit re-verification, security review, its own
CI-green gate — before being declared independently releasable.
- Re-run the Dependency Audit against AF-1–AF-6's actual implementation; confirm every "Tight
  coupling" entry from this document has been closed or explicitly re-classified as acceptable.
- Definition of Done for this milestone is the Definition of Done for Agent Firm v1 as a whole — see
  the closing summary.

---

## Sequencing Notes

- AF-1 and AF-6 (the shared logging/data-access foundation) should land before AF-2, since AF-2's
  formal contract is only meaningful once the internal reach-through it's replacing has somewhere
  correct to redirect to.
- AF-4 carries the only real product-scope decision in this roadmap (what agents may query) — flag
  this explicitly to the owner before starting it, not after.
- AF-3 can run in parallel with AF-1/AF-2 — it touches a different layer (provider internals) with no
  dependency on the data-access or interface work.
- Nothing in AF-1 through AF-6 requires or implies moving Agent Firm to a separate repository yet —
  that is a governance/timing decision (`AGENT_FIRM_GOVERNANCE.md`), not a prerequisite any of these
  milestones assume.
