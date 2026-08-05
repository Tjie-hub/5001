# Final Production Readiness Certification — Agent Firm / Production Engine Workstream

**Date:** 2026-07-29
**Scope certified:** ADR-AF-002 (Context Ownership), ADR-AF-003 (Sizing Ownership), ADR-AF-004
(Versioning Contract), the Agent Firm Integration Validation, and Production Operational Validation
Phases 1–2 — the complete arc from architecture decision through implementation, independent
validation, and operational readiness review, as scoped by this task's own "Completed" list.
**Nature of this task:** a certification review synthesizing nine prior reports plus this session's
own fresh re-verification of the invariants they claim — not a new investigation, and not a new
round of fixes. Per this task's own rule ("only fix a defect if it directly invalidates
certification"), **zero code changes were made this session.**

---

## Executive Summary

Every prior certification in this sequence reached **GO WITH CONDITIONS**, and every one of those
conditions was, on inspection, either (a) an explicit monitoring/observation request rather than a
blocking defect, (b) an inert or explicitly-out-of-scope architectural gap, or (c) a documentation-
only loose end with zero functional impact. Re-running the tests that back every load-bearing claim
— research/production boundary, DB centralization, route policy, the sizing single-writer
invariant, the versioning-contract signature freeze — confirms all of them still hold, unchanged,
right now, with zero code drift since Production Operational Validation Phase 2's own certified
state.

No condition surviving this review rises to "blocking." The two genuinely open items with real
operational weight — real Ubuntu-host resource/latency measurements, and confirmation of two
specific live production `.env` values (`EDGE_SCORE_MODE`, `TELEGRAM_WEBHOOK_SECRET`) — require
live-box access this session did not have (declined by the user in Phase 2, not re-requested here
since nothing about this task changes that fact), and are categorized below as **Operational**
conditions to close before or shortly after the next deploy, not as reasons to withhold
certification of the code that has already been built, tested, and independently validated four
times over.

**Final decision: GO WITH CONDITIONS.**

---

## 1. Certification Evidence Reviewed

| Report | Date | Verdict |
|---|---|---|
| `Audit/AF2_WP4_FINAL_CERTIFICATION.md` | 07-29 | GO WITH CONDITIONS |
| `Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md` | 07-29 | GO WITH CONDITIONS (re-affirmed, no new condition) |
| `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md` (+ companions: `AF2_RUNTIME_PERFORMANCE_REPORT.md`, `AF2_BEHAVIORAL_REGRESSION_REPORT.md`, `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`) | 07-29 | PRODUCTION VALIDATED WITH MONITORING |
| `Audit/ADR-AF-002_CLOSURE_REPORT.md` + `Audit/ADR-AF-002_HANDOFF_CHECKLIST.md` | 07-29 | Closed; next milestone named (Operations Dashboard / Job History) |
| `Audit/PRODUCTION_ENGINE_ROADMAP_RECONCILIATION.md` + `Audit/PRODUCTION_ENGINE_BACKLOG.md` + `Audit/PRODUCTION_ENGINE_NEXT_EXECUTION_PLAN.md` | 07-29 | Identified ADR-AF-003 as the pre-empting P0 item (now resolved — see below) |
| `Audit/ADR-AF-003_IMPLEMENTATION_REPORT.md` | 07-29 | Implemented per spec; one documented, justified deviation (deferred `size_hint` audit-trail completeness) |
| `Audit/ADR-AF-004_IMPLEMENTATION_REPORT.md` | 07-29 | Implemented (no code change required); two documented, non-blocking prose-vs-schema deviations |
| `Audit/AGENT_FIRM_INTEGRATION_VALIDATION_REPORT.md` | 07-29 | GO WITH CONDITIONS — found and fixed the `size_tier` persistence gap |
| `Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE1.md` | 07-29 | GO WITH CONDITIONS — historical-replay/restart-safety validated, zero defects |
| `Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE2.md` | 07-29 | GO WITH CONDITIONS — found and fixed the `close_trade()` duplicate-close gap |

**Fresh re-verification this session** (not reused from any prior report's own numbers):

| Check | Result |
|---|---|
| `tests/test_architecture_boundary.py` + `tests/test_research_data_fence.py` + `tests/test_db_centralization.py` + `tests/security/test_route_policy.py` | **13 passed, 0 failed** |
| `tests/agent_firm/test_firm.py` + `tests/test_sizing_single_writer_invariant.py` + `tests/agent_firm/test_versioning_contract.py` + `tests/test_position_sizing.py` | **53 passed, 0 failed** |
| `git status` vs. Phase 2's recorded state | **Unchanged** — no code drift since the last certified full-suite run (1635 passed / 44 failed / 9 errors, Phase 2) |

---

## 2. Confirmations Required by This Task's Objective 4

| Requirement | Status | Evidence |
|---|---|---|
| Production architecture is internally consistent | **Confirmed** | ADR-AF-002 (context ownership), ADR-AF-003 (sizing ownership), ADR-AF-004 (versioning) were implemented in dependency order, each verified not to conflict with the others (ADR-AF-004's own deviations §ADR-AF-004 explicitly checked for, and found none, contradicting the MINOR classification or `evaluate()`'s frozen signature). Sizing has exactly one writer (`resolve_agent_size_hints()`), re-confirmed today. |
| Research/Production separation remains intact | **Confirmed** | `test_architecture_boundary.py`/`test_research_data_fence.py` re-run fresh this session: 13/13 passed. Zero files under `research/` were touched by any report in this sequence — every session in the chain states this explicitly and none contradicts it. |
| Operational procedures are complete | **Complete, with one caveat** | Startup/shutdown/daily-checklist/log-rotation/DB-maintenance/recovery-after-reboot procedures are documented in `Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE2.md` §7, extending (not duplicating) `docs/OPERATIONS.md`. Caveat: none of these procedures have been exercised against the live host this session — see Operational Conditions below. |
| Failure recovery procedures are documented | **Confirmed** | Restart-safety (Phase 1: DB-backed open-position guard, idempotent `ft_signal` insert), graceful shutdown (`gunicorn.conf.py::worker_exit`, `wait=True`), and reboot recovery (`systemd Restart=always` + daily-checklist verification) are all documented with their actual mechanism named, not just asserted. |
| Audit trail is complete | **Confirmed, after two now-closed gaps** | `agent_decisions`/`agent_traces` persist `size_tier` (fixed in the Integration Validation session — was silently dropped before that fix); `paper_trades` exit data can no longer be silently overwritten by a duplicate close (fixed in Phase 2). The one remaining, explicitly-deferred gap — `agent_decisions.size_hint` not reflecting the final resolved value — is a documented, justified, non-blocking deviation (ADR-AF-003's own report), not an incomplete audit trail for the data it does claim to carry. |
| Determinism guarantees remain valid | **Confirmed** | `resolve_size_hint()` is a pure function (re-verified: no caching, no global mutation) — proven deterministic across repeated identical inputs by Phase 1's `test_full_chain_deterministic_across_repeated_runs` and the multi-day replay test. `evaluate`/`evaluate_staged`/`reset_market_ctx` signatures are frozen and snapshot-tested (`test_versioning_contract.py`, 11 tests, re-run clean today). |

---

## 3. Outstanding Conditions — Categorized

### Blocking
**None.** No item surviving review requires a code or configuration change before the next deploy
can proceed.

### Non-Blocking (technical debt, safe to carry)
| Item | Why it's non-blocking |
|---|---|
| `reset_market_ctx()` compatibility shim | Inert no-op; blocked only by two non-production developer scripts needing a one-line edit each |
| `ConsensusContext` (Tier 2), `SessionContext`/`OpportunityContext` | Explicitly out of every work package's mandate (Tier 1 only); would need a dated ADR amendment to build |
| `AgentDecision.size_hint` always `None` at construction (final resolved value not retroactively written back) | Documented, justified deviation (ADR-AF-003 report); `size_tier` — the qualitative signal that matters for the audit trail — is fully captured; existing consumers (`trade_plan.py`, premarket message builder) already handle `None` gracefully |
| Stale docstring, `tests/test_agent_firm_context_wiring.py` line 9 (claims `_build_context()` "is untouched"; deleted in WP3) | Comment-only; zero functional impact; found and explicitly not fixed by the ADR-AF-002 closure session per its own "report, don't expand scope" instruction — re-confirmed here as still comment-only, still not certification-invalidating |
| `docs/agent_firm/*.md` planning-corpus reconciliation (23 files, ≥3 mutually-inconsistent roadmap documents) | Documentation debt predating the actual delivered WP1-4 structure; repeatedly, deliberately deferred across every session in this sequence; does not affect the correctness of the shipped code |
| Two unrelated pre-existing unused imports (`scheduler/jobs.py`, `scheduler/scanner.py`) | Cosmetic, pre-dates this entire workstream |

### Operational (requires live-host access or live conditions, not a code change)
| Item | Status |
|---|---|
| Real Ubuntu CPU/RSS/disk/DB-growth/log-growth measurements | **Not collected across two operational-validation phases** — SSH access was attempted and declined by the user both times access was relevant (Phase 2). This is the single largest genuinely open item in the entire sequence. Recommend capturing before or immediately after the next live deploy, not as a pre-deploy gate (the code correctness this measures does not depend on the number itself). |
| Confirm live `.env`'s `EDGE_SCORE_MODE` value | Carried from `Audit/PRODUCTION_ENGINE_BACKLOG.md` P0-2 (predates ADR-AF-003's implementation) — determines whether the sizing-collision defect ADR-AF-003 fixed was actually firing in production before the fix. Academic now that the fix has shipped either way, but worth confirming for the historical record. |
| Confirm live `.env`'s `TELEGRAM_WEBHOOK_SECRET` is still set | Carried from `Audit/PRODUCTION_ENGINE_BACKLOG.md` P0-3 — a general production-security config item, not specific to the Agent Firm workstream this certification scopes; flagged here for completeness since it appeared in the same backlog review, not treated as part of this certification's own gate |
| Monitor `agent_decisions` decision-distribution shift for `strategy IN ('premarket','eod')` and exit-review, post-deploy | The one condition every certification in this sequence has consistently named — the three newly-context-wired call sites are expected to shift approve/veto/confidence distributions, by design; this should be watched against real traffic, not merely assumed correct |
| Real-provider (Z.ai/Claude) latency/behavior at production scale | Validated only by the existing manual smoke probe (`engine/agent_firm/smoke.py`) across every session in this sequence; simulated-provider methodology was consistently and deliberately used elsewhere to avoid consuming the shared Claude-provider quota |
| Provider (Stockbit) latency instrumentation | Genuinely missing (no timing/duration logging in `flow_filter.py`/`stockbit_fetcher.py`); a real gap, but building instrumentation is new capability, correctly out of scope for every validation session in this sequence |
| Live provider-disconnect recovery, observed against a real outage | Not tested against a real endpoint (Phase 2); recommend treating the next real Stockbit outage as the actual validation event rather than manufacturing one against production |

### Future Enhancements (explicitly deferred, no timeline pressure)
| Item |
|---|
| Operations Dashboard / Job History — the standing next roadmap milestone (`Audit/ADR-AF-002_HANDOFF_CHECKLIST.md`, `Audit/PRODUCTION_ENGINE_NEXT_MILESTONE.md`); should incorporate `AF2_POST_DEPLOYMENT_MONITORING_PLAN.md`'s nine tracked metrics into its first version |
| Agent Firm repository split (AF-1 through AF-7, `docs/agent_firm/AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`) — sequenced after the dashboard milestone, zero milestones started |
| Instrumenting batch-context cache hit/miss and "unexpected fail-soft" activations as structured, queryable events (currently interim-covered by grep-based log monitoring) |
| `PRAGMA integrity_check` at application startup (partially mitigated today by the nightly backup's own verify step) |
| Targeted `UPDATE agent_decisions SET size_hint = ...` mechanism, if the deferred audit-trail-completeness item is ever prioritized |

---

## 4. Risk Assessment

The one class of risk every certification in this sequence has consistently, honestly named is not
a defect: **wiring real Tier 1 context into the three previously-empty-context call sites
(premarket, EOD, exit-review) will shift the Agent Firm's decision distribution at those sites** —
this is the intended, designed effect of ADR-AF-002's completion, not a side effect to be
mitigated. Every report from `AF2_WP4_FINAL_CERTIFICATION.md` onward has flagged this as the
single highest-priority thing to watch post-deploy, and this certification does not discover
anything that changes that framing.

Beyond that, the two fixes made across the sequence (`size_tier` persistence, `close_trade()`
duplicate-close guard) were both narrow, single-function, regression-tested changes with zero
observed side effects across a 1635-test full-suite run — neither introduces a new risk surface.

The largest residual uncertainty is not architectural but observational: **this entire validation
sequence has never been exercised against the real production host or real live market data.**
Every test, every replay, every resource measurement in Phases 1–2 ran on a Windows dev checkout
against seeded/mocked data. This is a real, acknowledged limit on how much confidence any of these
reports can honestly claim about production behavior specifically — appropriately reflected in the
"GO WITH CONDITIONS" tier rather than an unconditional "GO," across every report in this sequence,
including this one.

---

## 5. Repository Health

- **Outstanding failures:** the full repository suite runs at 1635 passed / 44 failed / 9 errors
  (Phase 2's certified state, unchanged as of this session). Every failure/error is a pre-existing,
  previously-documented Windows-local-tooling artifact (`test_value_format.py`'s Node.js module
  resolution, `test_auto_token.py`/`test_config_validation.py`/`test_cron_contract.py`/
  `test_logging_config.py`/`test_news_filter.py`/`test_stockbit_fetcher_ensure_valid_token.py`'s
  environment-specific issues, `security/test_release_scripts.py`/`test_secret_hygiene.py`, and one
  known-flaky test in `tests/regime/test_storage.py` that alternates pass/fail across runs
  independent of any change in this sequence). None touch Agent Firm, scanner, paper_trade, sizing,
  or monitor code.
- **Outstanding technical debt:** fully enumerated in §3 above (Non-Blocking table) — nothing new
  found this session; every item traces to an already-existing report.
- **Deferred ADR items:** `ConsensusContext`/`SessionContext`/`OpportunityContext` (Tier 2, ADR-AF-002),
  `agent_decisions.size_hint` audit-trail completeness (ADR-AF-003) — both are documented,
  justified, and require either a new ADR amendment or a small separately-scoped follow-up, not a
  correction to what's already shipped.
- **Known limitations:** no live-Ubuntu-host validation has occurred (§3 Operational); provider
  latency is uninstrumented; real-provider LLM behavior is validated only by manual smoke-testing,
  never at production scale, across this entire sequence.

---

## 6. Recommendation

# GO WITH CONDITIONS

**This is not a new tier — it is the same recommendation every report in this sequence has
independently reached, re-confirmed rather than re-derived from scratch.** The code is complete,
internally consistent, independently tested four times over (implementation → integration
validation → operational Phase 1 → operational Phase 2), and free of any defect that has survived
scrutiny across that many independent passes. The conditions that remain are monitoring
obligations and live-environment confirmations, not code deficiencies — categorized precisely as
such in §3 so a future reader (or future certification) does not have to re-derive which is which.

**Before the next deploy:** nothing blocks it.
**Within the first 1–2 weeks after deploy:** monitor the premarket/EOD/exit-review decision-
distribution shift (the one condition every report in this sequence has named); capture real
Ubuntu resource numbers as soon as access is available (now overdue across two phases).
**No fix was required to reach this decision** — per this task's own rule, and consistent with a
codebase whose last four independent validation passes each found at most one narrow, already-fixed
defect and nothing else.
