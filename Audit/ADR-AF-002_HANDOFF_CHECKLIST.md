# ADR-AF-002 — Handoff Checklist

**Date:** 2026-07-29
**Companion to:** `Audit/ADR-AF-002_CLOSURE_REPORT.md`.
**Purpose:** a single-page, checkbox-shaped confirmation that this migration is ready to hand off to
normal operational maintenance, with no open implementation questions remaining.

---

## Handoff Status

- [x] **Implementation complete** — WP1 (Foundation), WP2 (Producer Migration), WP3 (Consumption
      Migration), WP4 (Integration Completion) all delivered. Five live `SignalCandidate`
      construction sites, all context-aware. Zero remaining `_build_context()` legacy implementation.
      Reports: `Audit/AF2_WP1_IMPLEMENTATION_REPORT.md` → `Audit/AF2_WP4_FINAL_CERTIFICATION.md`.
- [x] **Independent audit complete** — a fresh, non-reused-context verification pass re-derived every
      finding from the current repository state (new greps, new reads, new test runs), confirmed no
      bypass/duplicate/legacy remnant, and found + fixed one class of genuine defect (three stale
      code docstrings). Report: `Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md`.
- [x] **Production validation complete** — 8 realistic scenarios exercised against the real pipeline
      (real context builders, real committee wiring, scripted zero-cost LLM per an explicit,
      user-authorized scope decision), performance measured, all tested failure modes confirmed
      fail-soft, a concrete before/after comparison documented the migration's actual behavioral
      effect. Reports: `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md`,
      `Audit/AF2_RUNTIME_PERFORMANCE_REPORT.md`, `Audit/AF2_BEHAVIORAL_REGRESSION_REPORT.md`.
- [x] **Monitoring plan available** — nine tracked metrics (candidate throughput, context
      completeness, decision distribution, specialist failure rate, cache hit rate, decision
      latency, risk veto rate by reason, paper-trade acceptance rate, unexpected fail-soft
      activations), each with a concrete SQL query building on existing
      `agent_decisions`/`agent_traces`/`provider_events` persistence — no new infrastructure
      required to start. Report: `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`.
- [x] **Roadmap updated** — `CLAUDE.md`'s 2026-07-29 Amended entry marks ADR-AF-002 COMPLETE and
      cross-references the closure report and this checklist (per explicit user selection — see
      `Audit/ADR-AF-002_CLOSURE_REPORT.md`'s "Update Roadmap" reasoning for why `CLAUDE.md` rather
      than one of the three stale, mutually-inconsistent `docs/agent_firm/*.md` planning documents
      was chosen as the update target).
- [x] **Certification recorded** — three independent passes (WP4, Final Audit, Production
      Validation) all concur: ship, with the same single, well-understood monitoring condition.

**No open item on this list blocks declaring ADR-AF-002 closed.**

---

## Remaining Maintenance Items (not blockers — tracked, not urgent)

| Item | Why it's maintenance, not a blocker |
|---|---|
| `reset_market_ctx()` compatibility shim removal | Function is already an inert no-op; removal is a small, mechanical follow-up blocked only by two developer scripts (`scripts/probe_actual_http_concurrency.py`, `scripts/replay_firm_offline_run.py`) needing a one-line edit each |
| `tests/test_agent_firm_context_wiring.py`'s line-9 stale docstring claim (found during this closure's own repository readiness check) | Comment-only; asserts `_build_context()`/`_market_ctx` "is untouched," which became false when WP3 deleted `_build_context()` — zero functional impact |
| Instrumenting batch-context cache hit/miss as a structured, queryable signal (currently validated structurally, not continuously monitored) | Proposed, not yet built — a future, separately-reviewed instrumentation addition, per the monitoring plan |
| Promoting "unexpected fail-soft" log lines to a structured event table (mirroring `provider_events`'s shape) | Same — proposed future enhancement, currently interim-covered by grep-based log monitoring |
| `docs/agent_firm/*.md` planning-corpus reconciliation (23 files, at least 3 mutually-inconsistent roadmap/sequence documents predating the actual WP1-4 delivery) | Explicitly deferred since WP2's own report; large, separately-scoped effort, never absorbed into any of WP1-4 or this closure |

## Deliberately Out-of-Scope (future enhancements, not maintenance)

- `ConsensusContext` (Tier 2) — no builder, no attach point, would require its own ADR amendment.
- `SessionContext`/`OpportunityContext` — same category, no attach point exists in the frozen
  `SignalCandidate` field set.
- Any Agent Firm capability expansion beyond Tier 1 context ownership — explicitly out of every
  work package's mandate in this sequence, and out of this closure's mandate too.

---

## Next Roadmap Milestone

**Operations Dashboard / Job History phase**, per the standing sequencing already agreed in
`Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md` and reaffirmed in `Audit/FINAL_RELEASE_DECISION.md`
(both 2026-07-28, pre-dating ADR-AF-002) — **not** a new milestone this closure invented. Full entry
criteria, risks, and readiness assessment: `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`.

**Milestone after that** (unchanged, same standing sequence): **Agent Firm repository split** —
`docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`'s AF-1 through AF-7 sequence is the existing,
detailed execution plan for that milestone specifically, once reached.
