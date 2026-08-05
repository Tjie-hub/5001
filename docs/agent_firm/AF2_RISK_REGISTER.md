# AF-2 — Risk Register

**Date:** 2026-07-29
**Basis:** `AF2_IMPLEMENTATION_READINESS.md`, `AF2_WORK_PACKAGE_SEQUENCE.md`, `AF2_TEST_STRATEGY.md`.
**Scope calibration:** `paper_trade.py` manages **paper** positions only — no live broker execution
exists anywhere in this codebase (confirmed against `CLAUDE.md`'s own architecture description and the
absence of any order-placement API in the modules reviewed across this entire audit). No item below puts
real money at risk today. The actual stakes are: (1) **evidentiary integrity** — `agent_decisions`/
`paper_trades` performance data feeds `analytics.py::cohort_summary()`, which is exactly the kind of
audit trail this repository's research-governance culture (`CLAUDE.md`'s evidence-first philosophy)
treats as load-bearing for real future decisions, including eventual promotion of any Agent-Firm-gated
strategy toward real capital; and (2) **signal throughput** — a bad guardrail rollout that over-vetoes
loses opportunities, not money. Both are named precisely as such below, not inflated to "capital at
risk."

---

## Severity Legend

**Likelihood:** Low / Medium / High — probability of the risk materializing if the item ships as
currently designed, without the named mitigation. **Impact:** Low / Medium / High — consequence if it
does, scoped per the calibration above.

---

## Blocker-Level Risks (from `AF2_IMPLEMENTATION_READINESS.md`)

| ID | Risk | Likelihood | Impact | Mitigation | Rollback trigger | Rollback mechanism |
|---|---|---|---|---|---|---|
| R-B1 | `RegimeContext`/`TechnicalContext` ship as newly-invented parallel computations, disagreeing with `engine/regime_filter.py::detect_regime()`/`engine/technicals.py::tech_direction()` on the same ticker/date, with no reconciliation | Medium (this exact pattern already happened once — the original `flow_verdict` duplication — before it was caught) | Medium — corrupts the audit trail's internal consistency (two "regime" columns in the same evaluation disagreeing), erodes trust in Agent Firm's narrative output, no immediate throughput or paper-capital effect | WP0b resolved before WP1/WP3 start (`AF2_WORK_PACKAGE_SEQUENCE.md`); the B1 regression test (`AF2_TEST_STRATEGY.md`) run in CI, not just at review time | Regression test fails, or a manual audit finds a disagreement in production `agent_decisions`/`agent_traces` rows | Revert WP1/WP3 to raw-context passthrough (the pre-migration state) via git revert of the specific commit; no data migration needed since these are ephemeral, non-persisted objects |
| R-B2 | WP5 ships `resolve_size_hint()` without a documented precedence rule against `EDGE_SCORE_MODE`'s existing `size_mult`, adding a third unreconciled sizing signal to an already-live two-way collision | High if WP0d is skipped (the collision already exists unresolved today — adding a third signal without fixing the underlying last-write-wins bug only compounds it) | Medium — mis-sized paper positions corrupt `pnl_pct`/Sharpe figures in `paper_trades`, which `cohort_summary()` uses for approve-vs-veto performance comparison; a systematically biased sizing signal could make a genuinely bad strategy look better or worse than it is in the evidentiary record | WP0d resolved and its precedence rule enforced by the B2 regression test (`AF2_TEST_STRATEGY.md`) *before* WP5 starts, not after | B2 regression test fails, or shadow-mode comparison shows `resolve_size_hint()` and `size_mult` disagreeing beyond a reasonable band on a live-replayed candidate set | `AGENT_FIRM_GUARDRAILS_MODE=off` (or reverting just the `size_hint` consumption line at `scanner.py:1609` to `r.get("agent_size_hint", 1.0)` pre-WP5 behavior) — instant, single-line revert, no data migration |
| R-B3 | Assembly location left ambiguous; WP1-3/WP8/WP9 land with Agent Firm importing `engine/indicators.py`/`engine/technicals.py`/`engine/chart_indicators.py` directly, creating new forward dependencies `AGENT_FIRM_DEPENDENCY_AUDIT.md` never catalogued | Medium — likely by default if WP0a isn't explicitly decided, since "just call the function from inside `_build_context()`" is the path of least resistance during implementation | Low near-term (nothing breaks today), Medium long-term (works directly against the stated eventual repository-split goal in `AGENT_FIRM_GOVERNANCE.md`'s Independent Repository Timing section) | WP0a resolved explicitly before WP1 starts; if resolved as option (b) (accept the coupling), the Dependency Audit table is updated in the same change, not silently | A future `AGENT_FIRM_DEPENDENCY_AUDIT.md` re-verification (already scheduled for AF-7 per `AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`) finds undocumented "Tight coupling" entries | No code rollback needed if caught early — the fix at that point is documentation (add the entries) or a later refactor to move assembly, both non-urgent since nothing is functionally broken |
| R-B4 | Batch-level context objects (`MarketContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`) reach `evaluate()` via an undocumented signature change, silently triggering a MAJOR version event under `AGENT_FIRM_GOVERNANCE.md`'s own rule without the required "explicit owner sign-off" | Low-Medium — depends entirely on whether WP0c is actually decided before implementation, or discovered as a governance violation after the fact | Low — process/governance impact only, no runtime effect | WP0c resolved explicitly (recommend: extend `SignalCandidate`, avoiding the question entirely) | A governance review (or this document's own re-verification) finds `evaluate()`'s signature changed without a recorded MAJOR-version sign-off | Revert the signature change; re-implement via the `SignalCandidate`-extension path instead — no data impact, pure code-structure fix |

---

## Work-Package-Level Risks

| ID | Risk | Likelihood | Impact | Mitigation | Rollback trigger | Rollback mechanism |
|---|---|---|---|---|---|---|
| R-WP4a | New guardrail vetoes (`negative_count`, `already_open_position`, `entries_blocked`) over-veto relative to today's LLM-only behavior, reducing signal throughput more than intended | Medium — this is a real behavior change by design, not a bug; the risk is in the *degree*, not the existence | Low-Medium — fewer paper trades opened, a throughput/opportunity-cost effect, not a correctness one; recoverable next cycle | Shadow-mode comparison (`replay_firm_offline_run.py` extension) reviewed by a human before `enforce`; `AGENT_FIRM_GUARDRAILS_MODE` starts at `shadow` by default | Shadow-mode veto rate deviates significantly from the pre-WP4 approve rate on the same replayed candidate set | `AGENT_FIRM_GUARDRAILS_MODE=off` reverts to pure-LLM decisioning instantly; no data migration, no code revert needed |
| R-WP4b | `risk.run()`'s signature change (adding a context parameter) ships without all four dependent test files updated in the same commit, leaving the suite red or, worse, silently skipped | Low if `AF2_TEST_STRATEGY.md`'s "same commit" requirement is followed; Medium if WP4 is split across multiple PRs | Low — CI-catchable, not a production risk if caught before merge | Explicit acceptance criterion: `pytest tests/agent_firm/ -q` fully green in the same PR as the signature change | CI red on the WP4 PR | Standard git revert of the WP4 commit; no production exposure if CI gate is respected |
| R-WP5 | `resolve_size_hint()` systematically mis-sizes paper positions relative to what a well-calibrated LLM `size_hint` would have produced, biasing the paper-trading performance record | Medium — any new deterministic function replacing a previously-unconstrained LLM output carries calibration risk in its first deployment, regardless of how carefully bounded it is | Medium — same evidentiary-integrity concern as R-B2, sustained over time rather than a one-off collision | Mandatory shadow-mode period (`AF1_REMEDIATION_PLAN.md`) with human review of the logged comparison before `enforce`; boundary-case unit tests per `AF2_TEST_STRATEGY.md` | Shadow-mode comparison shows `resolve_size_hint()` diverging from the historical LLM-derived distribution in a way that isn't explained by the new, better-grounded inputs | Single-line revert at `scanner.py:1609` to consume the pre-WP5 `AgentDecision.size_hint` source; `resolve_size_hint()` itself stays in the codebase, unused, for later re-attempt |
| R-WP9 | The `open_trade()` extraction refactor (pulling capital/exposure computation into `get_execution_context()`) introduces a transcription error that subtly changes real sizing/cap behavior for every trade, not just the new `ExecutionContext` consumers | Low if the before/after regression test (`AF2_TEST_STRATEGY.md`) is run and passes; **Medium if that test is skipped or only spot-checked** | **High if it materializes** — this is the one refactor in the entire program that touches code already governing every paper trade opened today, not just new functionality; an error here has blast radius across the whole system, not just Agent Firm | Byte-for-byte before/after regression test on a representative historical trade set, required before merge, not optional | Regression test fails, or a post-deploy audit finds `open_trade()`'s lot/cap computation differs from the pre-refactor baseline on any input | Git revert of the extraction commit — `ExecutionContext`'s consumers (WP5) would need to fall back to their pre-WP9 state simultaneously, so this revert should be treated as reverting WP9+WP5 together if WP5 has already shipped on top of it |
| R-WP2 | `analytics.py::_is_aligned`'s taxonomy check silently breaks (matches nothing, or matches everything) if the flow-verdict taxonomy passthrough ships without the paired update | Medium if treated as a follow-up rather than same-change work (explicitly warned against in `AF1_IMPLEMENTATION_BACKLOG.md` and `AF2_TEST_STRATEGY.md`) | Low-Medium — the audit dashboard's agreement metric silently goes to 0% or 100% for the `flow` role, a data-quality issue in a reporting surface, not a decision-path issue | Required regression test asserting `agent_agreement()` end-to-end, in the same change as the taxonomy passthrough | The regression test fails, or the `/api/agent/audit` dashboard's flow-agreement figure is visibly degenerate post-deploy | Revert the taxonomy passthrough change alone; `FlowContext`'s other fields (`net_foreign_14d`, `trend_7d`) are unaffected and can stay |

---

## Product/Scope Risks (not safety risks — named for completeness)

| ID | Risk | Likelihood | Impact | Note |
|---|---|---|---|---|
| R-P1 | Once Flow/Regime agents' outputs become mostly passthrough (per `AF1_PROMPT_CONTEXT_MAPPING.md`'s open question), the cost/latency of a full LLM call per candidate may no longer be justified by the residual reasoning task | Medium — a natural consequence of successfully closing the duplication findings, not a defect | Low — a cost/latency optimization opportunity, not a correctness risk | Not assigned a rollback mechanism since it isn't a regression risk; flagged for an explicit AF-2-or-later product decision on whether to collapse these two agents' contribution into a precomputed field feeding `ConsensusContext` directly |

---

## Rollback Strategy — General Principles

1. **Every Tier 1/2/3 context object is ephemeral** (per `AF2_IMPLEMENTATION_READINESS.md` Gap G4's
   resolution) — no rollback of any context-object change requires a data migration, only a code revert.
   This bounds every rollback in this register to "revert the commit," never "restore from backup."
2. **Every behavior-changing package (WP4, WP5) ships behind a mode flag defaulting to `shadow`**,
   consistent with this repository's own established pattern. The fastest rollback for either is flipping
   that flag, not reverting code — code revert is the second line of defense, not the first.
3. **The one item in this register with a blast radius beyond Agent Firm itself is R-WP9** (the
   `open_trade()` extraction). It is the only item in this backlog recommended for its own isolated,
   specifically-reviewed change, sequenced apart from `ExecutionContext`'s consumers, precisely so its
   rollback (if ever needed) does not entangle with WP5's.
4. **No item in this register requires a schema migration to roll back** — `AF1_REMEDIATION_PLAN.md`
   WP6's `size_hint` bound is the only schema-level change in the entire program, and it is additive
   (a validation constraint on an existing optional field), trivially reversible by relaxing the bound
   again if ever needed.
