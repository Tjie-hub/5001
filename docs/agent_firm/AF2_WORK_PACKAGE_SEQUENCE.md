# AF-2 — Work Package Sequence (Verified)

**Date:** 2026-07-29
**Basis:** `AF2_IMPLEMENTATION_READINESS.md`'s Blockers B1-B4, `AF1_REMEDIATION_PLAN.md`,
`AF1_IMPLEMENTATION_BACKLOG.md`.
**Purpose:** the dependency-verified execution order, including the four blocker-resolution items
(`WP0a`-`WP0d`) and two new work packages (`WP8`, `WP9`) this certification pass found missing from the
original backlog (Gap G2). This document supersedes `AF1_IMPLEMENTATION_BACKLOG.md`'s ordering for
sequencing purposes only — that document's per-package Objective/Affected files/Acceptance criteria
content is unchanged and still applies; only the ordering and the two new packages are new here.

---

## Dependency Graph

```
WP0c (decide: SignalCandidate extension vs evaluate() param — B4)
  └──> WP0a (decide: which side assembles Tier 1 objects — B3)
         └──> WP0b (decide: reuse engine/edge_enrich.py's functions vs new ones — B1)
                ├──> WP1  (TechnicalContext)
                ├──> WP3  (RegimeContext)
                ├──> WP2  (FlowContext)            [does not need WP0b — no B1 overlap found for Flow]
                ├──> WP4  (ConsensusContext + guardrail vetoes)
                └──> WP8  (MarketContext.ihsg_trend + market_risk_score)  [needs WP0b for ihsg_trend's producer]

WP0d (decide: size_mult vs resolve_size_hint precedence — B2)
  └──> WP9  (ExecutionContext)  [also needs WP0a, and its own hidden prerequisite below]
         └──> WP5  (deterministic size_hint, needs WP4 + WP9)
                └──> WP6  (schema hardening)
                       └──> WP7  (documentation reconciliation — now also closes G1, G2)
```

**No circular dependency was found.** The graph is a clean DAG. The four `WP0*` items are decisions
(each a short, explicit written amendment per `AF2_IMPLEMENTATION_READINESS.md` Parts 2-5), not
implementation work — they can be resolved in a single short session before any code-bearing work
package starts, and should be, since WP1/WP3/WP4/WP8/WP9/WP5 all transitively depend on at least one of
them.

---

## WP0a-WP0d — Blocker Resolutions (prerequisite to everything else)

| # | Resolves | Deliverable | Blocks |
|---|---|---|---|
| WP0c | B4 | One sentence in `AF1_CONTEXT_API_V2_SPEC.md`: batch-level objects attach as optional `SignalCandidate` fields (recommended) or `evaluate()` gains an optional defaulted parameter + a `AGENT_FIRM_GOVERNANCE.md` carve-out | WP0a |
| WP0a | B3 | One sentence in `AF1_CONTEXT_API_V2_SPEC.md`: assembly lives in Production Engine (recommended) or in `engine/agent_firm/` with the new forward dependencies explicitly added to `AGENT_FIRM_DEPENDENCY_AUDIT.md` | WP0b, WP1, WP2, WP3, WP4, WP8, WP9 |
| WP0b | B1 | Amend `AF1_CONTEXT_OBJECT_CATALOG.md`'s `TechnicalContext`/`RegimeContext`/`ExecutionContext` rows to name their actual producer, resolving the overlap with `engine/technicals.py`/`engine/regime_filter.py`/`engine/edge_score.py` | WP1, WP3, WP8, WP9 |
| WP0d | B2 | One paragraph, one test: the documented precedence rule between `EDGE_SCORE_MODE`'s `size_mult` and Agent Firm's `resolve_size_hint()` output when both modes are active | WP9, WP5 |

**Recommended resolutions** (stated in `AF2_IMPLEMENTATION_READINESS.md`, repeated here since they
determine the rest of this sequence): WP0c → option (a), extend `SignalCandidate`. WP0a → option (a),
assembly in Production Engine. WP0b → wrap the existing `engine/edge_enrich.py`/`engine/technicals.py`/
`engine/regime_filter.py` functions rather than building parallel ones. WP0d → Agent Firm's decision
supersedes the edge gate's when both are enforce, since it runs strictly later and has already seen the
edge gate's survivors as input (simplest rule, no new clamping logic required, matches the pipeline's
existing sequential-refinement shape).

---

## WP1 — `TechnicalContext` (revised)

**Sequencing:** after WP0a, WP0b. **Hidden prerequisite found this pass:** none beyond WP0a/WP0b — the
producer functions (whichever WP0b selects) already exist and are already callable.

**Runtime risk:** Low if WP0b resolves to reusing `engine/technicals.py::tech_direction()` (already
production-proven). **Elevated to Medium if WP0b is skipped or resolved as "build new functions
anyway"** — in that case, two independently-defined technical-direction reads exist in production
simultaneously, which is exactly Blocker B1's risk realized rather than closed.

## WP2 — `FlowContext`

**Sequencing:** after WP0a only — no B1 overlap was found for Flow specifically (the existing
`engine/edge_enrich.py::_latest_flow()` reads the same columns this object passthroughs, not a
conflicting parallel computation). **Hidden prerequisite:** the `analytics.py:109` taxonomy-alignment fix
(`AF1_IMPLEMENTATION_BACKLOG.md` WP2) must land in the same change, not after — a taxonomy mismatch left
live for even one deploy silently breaks the audit dashboard's agreement metric.

**Runtime risk:** Low-Medium, unchanged from the original assessment.

## WP3 — `RegimeContext` (revised)

**Sequencing:** after WP0a, WP0b. **Same elevated-risk note as WP1** applies if WP0b is skipped.

**Runtime risk:** Medium if WP0b resolves to "wrap `detect_regime()`" (low implementation risk, but a
*behavior* change from today's Agent Firm regime prompt, which is currently ungrounded and effectively
decorative — grounding it may change `regime_call` outputs it produces today, which is a desired
correction, not a regression, but should be observed, not assumed silent).

## WP4 — `ConsensusContext` + Open-Position/`entries_blocked` Guardrails

**Sequencing:** after WP0a only.

**Hidden prerequisite found this pass, not in the original backlog:** `agents/risk.py::run()`'s function
signature must change to accept a context parameter (today it only takes `candidate`, `analyst_results`,
`client` — confirmed by direct read, this is the root cause of the wiring bug
`AF1_CONTEXT_API_V2_SPEC.md` Part 1 found). This signature change breaks every test that calls
`risk.run()` directly or constructs its fixtures: `tests/agent_firm/test_firm.py`,
`test_firm_v2.py`, `test_risk.py`, `test_risk_v2.py` (all four confirmed by grep). **These four files
must be updated in the same change as the signature change, not as follow-up work** — a partially-updated
signature leaves the test suite red with no informative signal about which callers are stale.

**Runtime risk:** Medium-High, unchanged from the original assessment — this is the first package that
changes actual veto outcomes. Shadow-mode discipline (per `AF1_REMEDIATION_PLAN.md`) still applies.

## WP8 — `MarketContext.ihsg_trend` + `market_risk_score` Wiring (new — closes Gap G2)

**Objective:** compute and actually deliver IHSG trend context and the existing `/metrics` risk score to
the agents that need macro grounding — today both are either dead (`ihsg`, computed but never read by any
agent, confirmed by grep) or never captured at all (`market_risk_score`, per V1's own original note).

**Affected files:** wherever WP0a places assembly, `engine/agent_firm/firm.py::_build_context()`'s
`_market_ctx` cache (or its replacement), `MarketContext`'s type definition.

**Sequencing:** after WP0a, WP0b (since `ihsg_trend`'s producer is the same function WP0b selects for
`TechnicalContext`, applied to IHSG's own OHLCV).

**Runtime risk:** Low — purely additive; no agent currently consumes this data, so there is no existing
behavior to regress.

## WP9 — `ExecutionContext` (new — closes Gap G2)

**Objective:** give the sizing-resolution step visibility into current portfolio heat (capital,
aggregate exposure, config constants) — today `resolve_size_hint()` as originally designed
(`AF1_REQUIRED_CONTEXT_OBJECTS.md` §5) had no such visibility.

**Hidden prerequisite found this pass:** `paper_trade.py`'s capital/exposure computation
(`cost_per_lot`, `max_lots`, `open_capital`, the 30%-of-capital cap) is currently **inline inside
`open_trade()`** (`paper_trade.py:403-430`), not exposed as a separately callable function. Building
`ExecutionContext` requires extracting this into a reusable, read-only function (e.g.
`paper_trade.py::get_execution_context()`) **without changing `open_trade()`'s own behavior** — this is
a refactor of capital-sizing-adjacent code, which carries execution risk from the refactor itself
(risk of a transcription error while extracting the inline block), independent of `ExecutionContext`
being, by design, read-only and additive.

**Sequencing:** after WP0a, WP0b, **and WP0d** (the precedence decision should inform whether
`resolve_size_hint()` needs a `size_mult` input from the edge-veto pipeline as a reconciliation term, or
can ignore it because the precedence rule handles reconciliation elsewhere).

**Runtime risk:** Low for `ExecutionContext` itself (read-only, additive); **Medium for the
`open_trade()` extraction refactor** — recommend a dedicated, narrowly-scoped PR with before/after output
comparison on a representative set of historical trades (see `AF2_TEST_STRATEGY.md`), not bundled into
the same change as WP5.

## WP5 — Deterministic `size_hint`

**Sequencing:** after WP4 (needs `ConsensusContext`), WP9 (needs `ExecutionContext`), **and WP0d**
(needs the precedence rule against `EDGE_SCORE_MODE`'s `size_mult` — this is a hard gate, not a
nice-to-have: implementing `resolve_size_hint()` without first deciding B2 means shipping a third,
unreconciled sizing signal into an already-live two-way collision).

**Runtime risk:** High, unchanged from the original assessment — the one package in this entire sequence
that changes real position-sizing numbers in production. Mandatory shadow-mode rollout per
`AF1_REMEDIATION_PLAN.md`, **now additionally validated against `EDGE_SCORE_MODE=enforce` scenarios**,
since B2's resolution must be exercised, not just declared.

## WP6, WP7 — Unchanged

Sequencing and content as specified in `AF1_IMPLEMENTATION_BACKLOG.md`, with WP7's scope widened to also
close Gap G1 (the stale `AF1_IMPLEMENTATION_SPEC.md` step 6 reference to V1's six-object design).

---

## Revised Priority Summary

| Priority | Items | Why |
|---|---|---|
| **P0 — must resolve before any code** | WP0a, WP0b, WP0c, WP0d | Every downstream package transitively depends on at least one; each is a short written decision, not implementation work |
| **P0 — capital/behavior-affecting** | WP4, WP5 | Unchanged from `AF1_REMEDIATION_PLAN.md` — now additionally gated on WP0a/WP0d respectively |
| P1 | WP1, WP2, WP3, WP8 | Quality/grounding improvements; WP1/WP3 carry elevated risk specifically if WP0b is skipped |
| P1 — refactor risk, not behavior risk | WP9 | Low risk for the new object; Medium risk specifically for the `open_trade()` extraction sub-step — sequence as its own reviewed change |
| P2 | WP6, WP7 | Unchanged |

**Recommended execution order:** WP0c → WP0a → WP0b → WP0d → (WP2, WP8, WP1, WP3 in any order, all
independent of each other once WP0a/b are resolved) → WP4 → WP9 → WP5 → WP6 → WP7.
