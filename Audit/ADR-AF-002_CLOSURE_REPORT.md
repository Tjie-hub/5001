# ADR-AF-002 — Closure Report

**Date:** 2026-07-29
**Status:** ADR-AF-002 is **COMPLETE**. This report closes the work package sequence (WP1–WP4),
the independent architecture audit, and the production validation exercise, and hands the migration
off to normal operational maintenance.

---

## Executive Summary

ADR-AF-002 (`docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`) decided that Tier 1 context objects
(technical, flow, regime, news, market, portfolio, risk, execution facts) for the Agent Firm would be
assembled once, by Production Engine, from canonical existing compute functions, and attached to
`SignalCandidate` before evaluation — replacing an ad hoc, per-agent raw-SQL context path
(`firm.py::_build_context()`) with a single, typed, fail-soft producer
(`engine/agent_firm_context.py`) and migrating every specialist to consume it.

That decision is now fully realized in production code, independently audited, and validated under
simulated realistic conditions:

- **WP1 (Foundation)** built the nine typed context objects and their canonical-producer-wrapping
  builder functions, unit-tested but not yet wired into any live path.
- **WP2 (Producer Migration)** wired those builders into `scheduler/scanner.py`'s two
  `SignalCandidate` construction sites — context populated, but nothing consumed it yet.
- **WP3 (Consumption Migration)** migrated every specialist (Technical, Flow, Regime, News, Risk) to
  read its typed context directly off the candidate, deleted the legacy `_build_context()`, and
  closed a real pre-existing gap (the Risk Manager could not previously see open positions to enforce
  its own "no doubling up" rule).
- **WP4 (Integration Completion)** found and closed a second, larger gap an audit surfaced: two
  scheduled daily jobs (`run_premarket_firm_scan()`, `run_eod_trade_plan()`) and one intraday exit
  gate (`monitor.py::_agent_confirms_exit()`) were constructing candidates with **no** Tier 1 context
  at all — every one of their evaluations had been running on empty defaults since WP3 shipped. All
  three are now wired to the same producer, using the same already-approved pattern.
- **Final Architecture Audit** independently re-verified (fresh greps, fresh reads, fresh test runs,
  not reused from prior sessions) that all five live construction sites are correctly wired, no
  duplicate builder or legacy `_build_context()` remnant exists anywhere, and the research/production
  boundary is intact. It found and corrected three stale code comments as the one genuine defect this
  pass surfaced.
- **Production Validation** exercised the completed pipeline against 8 realistic scenarios (real
  seeded data, real `build_candidate_context()`, real committee wiring, a scripted zero-cost LLM
  stand-in per an explicit user scope decision), measured orchestration/context-building performance,
  and confirmed every tested failure mode degrades to a typed default rather than raising.

**No architecture, schema, or research-boundary change was needed at any point in this closure.**

---

## Timeline: WP1 → WP4

| Work Package | Scope | Key deliverable | Report |
|---|---|---|---|
| WP1 — Foundation | Nine Tier 1/2 context types + canonical-producer-wrapping builders, unit-tested, unwired | `engine/agent_firm_context.py` (builders), `engine/agent_firm/schemas.py` (types) | `Audit/AF2_WP1_IMPLEMENTATION_REPORT.md` |
| WP2 — Producer Migration | Wire builders into `scanner.py`'s two construction sites | `run_agent_firm_gate()`/`rank_bear_watchlist_and_notify()` populate context | `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md` |
| WP3 — Consumption Migration | Migrate 5 specialists to consume typed context; delete `_build_context()`; close Risk Manager portfolio-visibility gap | `engine/agent_firm/agents/*.py`, prompts rewritten to "interpret, don't recompute" | `Audit/AF2_WP3_IMPLEMENTATION_REPORT.md` + `AF2_WP3_CONTEXT_CONSUMPTION_MATRIX.md` + `AF2_WP3_PROMPT_SIMPLIFICATION_REPORT.md` + `AF2_WP3_REGRESSION_REPORT.md` |
| WP4 — Integration Completion | Audit found 3 unwired call sites (`jobs.py` x2, `monitor.py` x1); wired all three; confirmed `reset_market_ctx()` blocked-not-removable | `scheduler/jobs.py`, `monitor.py` | `Audit/AF2_WP4_IMPLEMENTATION_REPORT.md` + `AF2_WP4_TECHNICAL_DEBT_REPORT.md` + `AF2_WP4_CALL_GRAPH_REPORT.md` + `AF2_WP4_FINAL_CERTIFICATION.md` |
| Final Architecture Audit | Independent re-verification of WP1-4; fixed 3 stale docstrings | `scheduler/scanner.py`, `engine/agent_firm_context.py` (comments only) | `Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md` |
| Production Validation | 8 simulated scenarios, performance measurement, failure-mode confirmation, before/after regression evidence | No code change | `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md` + `AF2_RUNTIME_PERFORMANCE_REPORT.md` + `AF2_BEHAVIORAL_REGRESSION_REPORT.md` + `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md` |

All dates: 2026-07-29 (all six phases were executed in adjacent sessions on the same working day).

---

## Key Architectural Changes

1. **Single canonical Tier 1 assembler**: `engine/agent_firm_context.py`, deliberately placed outside
   `engine/agent_firm/` so the Production-Engine/Agent-Firm ownership boundary is visible in the file
   tree (per `ADR-AF-002`). No duplicate builder exists anywhere else in the repository (re-verified).
2. **Five live production construction sites, all now context-aware**: `scheduler/scanner.py`'s
   `run_agent_firm_gate()`/`rank_bear_watchlist_and_notify()` (WP2), `scheduler/jobs.py`'s
   `run_premarket_firm_scan()`/`run_eod_trade_plan()` (WP4), and `monitor.py`'s
   `_agent_confirms_exit()` (WP4).
3. **Specialist consumption**: every analyst (`technical.py`, `flow.py`, `regime.py`, `news.py`) reads
   its own typed context field directly off `SignalCandidate`, with no raw SQL/data retrieval inside
   any specialist (re-verified this session's predecessor). `risk.py` additionally consumes
   `PortfolioContext`/`RiskContext`.
4. **Legacy path fully retired**: `firm.py::_build_context()` (7 raw SQL queries) is deleted, not
   replaced in place, per `ADR-AF-002`'s own explicit instruction — confirmed zero remnant anywhere
   in the repository.
5. **Fail-soft at two layers**: per-field (`_safe()` inside `build_candidate_context()`) and per-call-site
   (a coarser try/except around the whole context-population step) — both layers independently
   confirmed to degrade to typed defaults rather than raise, under both hermetic tests and the
   Production Validation exercise's live empty-DB probe.

---

## Defects Discovered and Resolved

| # | Defect | Found in | Resolved in | Nature |
|---|---|---|---|---|
| 1 | Risk Manager's prompt claimed to check "current open paper trades" for its no-doubling-up rule, but no open-trades data was ever passed to `risk.run()` | WP3 | WP3 | Structural — the rule was undeliverable since before this migration began; closed by wiring `PortfolioContext` into `risk.py` |
| 2 | Three live, scheduled production call sites (`run_premarket_firm_scan()`, `run_eod_trade_plan()`, `_agent_confirms_exit()`) constructed candidates with zero Tier 1 context — every evaluation from these sites ran on empty defaults since WP3 shipped | WP4 audit | WP4 | Functional correctness gap in production, not cosmetic — the most significant finding of the entire closure sequence |
| 3 | Three code docstrings (`scanner.py` x2, `agent_firm_context.py` module docstring) asserted a WP2-era claim ("nothing reads these fields yet, producer wiring only") that became false the moment WP3 shipped consumption | Final Architecture Audit | Final Architecture Audit | Documentation drift — comment-only fix, zero functional risk |
| 4 | A test-suite hermeticity gap: wiring real `build_candidate_context()` into `monitor.py`/`scheduler/jobs.py` meant their existing tests would silently open the real, gitignored production DB unless pinned | WP4 | WP4 | Test-infrastructure defect, fixed alongside the production code change it was a consequence of |
| 5 | A Windows-only `.winvenv` fragility: a first-ever `pandas`/`numpy` import performed after another test's `importlib.reload()` cycle fails with a numpy C-extension guard error | WP4 | WP4 | Environment/test-ordering artifact, fixed by a module-level pre-import; no production code path is affected (production never calls `importlib.reload()` at runtime) |

Defect #2 is the one this closure most wants a future reader to internalize: **the migration was not
complete when WP3 "finished migrating consumption"** — a real gap in producer-side coverage survived
an entire work package undetected until WP4's dedicated audit task went looking for it. This is the
concrete justification for why this closure sequence included an independent audit and a production
validation pass rather than stopping at WP4's own implementation report.

---

## Validation Summary

- **Independent Architecture Audit** (`Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md`):
  re-derived every finding fresh (not reused from WP4's own session) — confirmed no bypass, no
  duplicate builder, no legacy remnant, research boundary intact. Full suite: 1564 passed / 44 failed
  (pre-existing, unrelated Windows-local-tooling) / 9 errors (same), byte-for-byte identical to WP4's
  own baseline both before and after the audit's 3 comment fixes.
- **Production Validation** (`Audit/AF2_PRODUCTION_VALIDATION_REPORT.md` and its three companions):
  8 realistic scenarios (normal day, low-liquidity, high-volatility, no-news, major-news, bull/bear/
  sideways regime) run through the real pipeline with a scripted LLM stand-in — all produced sensible,
  context-driven, internally-consistent outcomes; a direct before/after comparison concretely showed
  a genuinely bullish candidate being silently mis-vetoed pre-fix (analysts uninformed) and correctly
  approved post-fix; every tested failure mode (empty DB, disabled firm, empty candidate list)
  confirmed fail-soft; orchestration/context-building overhead measured at single-digit-to-low-double-
  digit milliseconds per candidate, negligible against real LLM latency.
- **Test-count progression across the whole sequence** (a clean, fully-explained arithmetic trail,
  re-verified this session): 1549 (WP2 baseline) → 1560 (+11, WP3's new tests) → 1564 (+4, WP4's new
  tests) → 1564 (unchanged, Final Audit and Production Validation added no code and no tests). No
  regression anywhere in this progression.

---

## Final Certification

Three independent certification passes, using each task's own requested vocabulary, all point the
same direction:

| Pass | Verdict |
|---|---|
| WP4 Final Certification | GO WITH CONDITIONS |
| Final Architecture Audit | GO WITH CONDITIONS (re-affirmed, no new condition added) |
| Production Validation | PRODUCTION VALIDATED WITH MONITORING |

**This closure report's own certification: ADR-AF-002 is COMPLETE.** The "with conditions/monitoring"
qualifier carried through all three passes refers to the same, single, already-well-understood
condition — the migration changes real decision distributions at the three call sites WP4 fixed, and
this is the *intended*, designed effect, which should be watched against real production traffic (per
the monitoring plan below), not treated as an open implementation question. There is no unresolved
implementation work blocking this statement.

**Explicit statement: ADR-AF-002 is complete.** Every requirement in the ADR's own text has either
been implemented (the Tier 1 mandate, in full) or explicitly, permanently scoped out with a named
reason (Tier 2 `ConsensusContext`, never built, never claimed to be — see below). No further work
package in this sequence is planned or required to satisfy the ADR as written.

---

## Remaining Technical Debt

Carried forward, unchanged, from `Audit/AF2_WP4_TECHNICAL_DEBT_REPORT.md` and re-confirmed
still-accurate by this session's own repository readiness check (fresh greps, not reused):

| Item | Status | Blocking factor |
|---|---|---|
| `reset_market_ctx()` compatibility shim | Inert no-op, cannot be removed | Two non-production developer scripts (`scripts/probe_actual_http_concurrency.py`, `scripts/replay_firm_offline_run.py`) still call it directly |
| `ConsensusContext` (Tier 2) | Unbuilt — no builder, no attach point | Deliberately out of every work package's mandate (Tier 1 only); would need its own ADR amendment |
| `SessionContext`/`OpportunityContext` | Unbuilt/no attach point | Same — documented since WP1, never claimed as in-scope |
| `AgentState.db_path`/`.context` unused `TypedDict` keys | Dead but harmless | `schemas.py` out of every session's "no schema change" mandate |
| One test-file docstring (`tests/test_agent_firm_context_wiring.py` line 9) | Newly found this session — claims `_build_context()`/`_market_ctx` "is untouched," but `_build_context()` was deleted in WP3 | Same category as defect #3 above, not fixed this session per this closure task's own "report findings without expanding scope" instruction — see Repository Readiness below |
| Two unrelated pre-existing unused imports (`scheduler/jobs.py`, `scheduler/scanner.py`) | Pre-dates WP1-4, unrelated to Agent Firm | Out of mandate, general hygiene |
| `docs/agent_firm/*.md` planning corpus (23 files, at least 3 mutually-inconsistent roadmap/sequence documents) | Predates the actual delivered WP1-4 structure | Explicitly deferred since WP2's own report; reconciling it is its own, separately-scoped effort, not absorbed into this closure |

None of these items block the "ADR-AF-002 is complete" statement above — each is either fully inert,
explicitly out of the ADR's own scope, or a documentation-only loose end with zero functional impact.

---

## Operational Monitoring Requirements

Full detail in `Audit/AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`. Summary of the nine tracked metrics:
candidate throughput, context completeness, decision distribution, specialist failure rate, batch-
context cache hit rate, decision latency, risk-veto-rate breakdown by reason, paper-trade acceptance
rate, and unexpected (coarse, whole-call-site) fail-soft activations. All nine build on existing
`agent_decisions`/`agent_traces`/`provider_events` persistence and the existing
`docs/OPERATIONS.md` SQL-query convention — no new infrastructure is required to start tracking any
of them.

**Single highest-priority metric to watch first:** decision distribution (§3 of the monitoring
plan) for `strategy IN ('premarket', 'eod')` and the exit-review path, specifically comparing before
vs. after the WP4 deploy date — this is the one metric every certification pass in this sequence
named as the expected, intended behavioral shift that should be confirmed against real traffic.
