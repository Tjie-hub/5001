# AF-1 — Implementation Backlog

**Date:** 2026-07-29
**Basis:** `AF1_REMEDIATION_PLAN.md`.
**Constraint:** planning only — no code is implemented as part of producing this document, matching the
same constraint every prior AF-1 document (`AGENT_FIRM_IMPLEMENTATION_ROADMAP.md:5`) was written under.
**Sequencing:** this backlog is the detailed breakdown of `AF1_REMEDIATION_PLAN.md`'s WP1-WP7, intended
to execute inside `AF1_IMPLEMENTATION_SPEC.md` Part 3's steps 6-7 — it does not introduce a parallel
implementation track.

---

## WP1 — `TrendContext` (Technical Analyst)

**Objective:** replace raw 60-bar OHLCV + LLM-inferred MA/S-R reads with precomputed indicator facts.

**Affected files:**
- `engine/indicators.py` — reused, no change (`calc_sma`, `calc_close_vs_ma`, `calc_ma_slope`, `calc_adx`, `calc_atr`, `calc_vol_ratio`)
- `engine/chart_indicators.py` — reused, no change (`support_resistance`, `detect_patterns`)
- `engine/agent_firm/firm.py::_build_context` (or its AF-2 Context API replacement) — compute `TrendContext`, attach to the candidate
- `engine/agent_firm/agents/technical.py` — pass `TrendContext` instead of (or alongside a 10-day trim of) raw OHLCV
- `engine/agent_firm/prompts/technical_v1.md` — remove the "infer MA position/S-R from raw bars" instructions; consume the supplied fields
- `engine/agent_firm/schemas.py` — no schema change required (`SignalCandidate.indicators` already exists)
- `scheduler/scanner.py:1000,1092` — replace hardcoded `indicators={}` with real `TrendContext` construction
- `tests/agent_firm/test_technical.py`, `engine/agent_firm/smoke.py` — update fixtures to the new input shape

**Dependencies:** none — every producing function already exists and is already tested.

**Risk:** Low. The only behavior-relevant change is that the Technical Analyst's `verdict`/`conviction`
now has real inputs instead of raw bars — this should improve grounding, not change the interface shape
or the decision-lifecycle contract.

**Acceptance criteria:**
- `technical_v1.md` no longer instructs the model to derive MA position or support/resistance levels
  from bar data.
- `TrendContext` is populated at both real production call sites, not only in `smoke.py`.
- `tests/agent_firm/test_technical.py` covers at least one case where `TrendContext` fields directly
  contradict what raw OHLCV alone would suggest, verifying the agent is actually consuming the derived
  fields, not falling back to eyeballing the trimmed bar window.

---

## WP2 — `FlowSummary` (Flow Specialist)

**Objective:** stop re-deriving `flow_verdict`/`smart_money_signal`/`net_foreign_14d` when
`flow_filter.py` already computes equivalents.

**Affected files:**
- `flow_filter.py` — expose the existing verdict/smart_money computation as a reusable function if not
  already cleanly separable (verify before assuming a change is needed here — it may already be)
- `engine/agent_firm/firm.py::_build_context` — assemble `FlowSummary` (passthrough fields + one new
  `SUM()` for `net_foreign_14d` + one new rolling-sign function for `trend_7d`)
- `engine/agent_firm/agents/flow.py` — pass `FlowSummary`
- `engine/agent_firm/prompts/flow_v1.md` — remove `flow_verdict`/`smart_money_signal`/`net_foreign_14d`
  as LLM-derived outputs; they become orchestrator-attached passthrough fields on the `AgentResult`
- `engine/agent_firm/analytics.py:109` — **must change in lockstep**: `_is_aligned`'s hardcoded
  `output.get("flow_verdict") == "ACCUMULATING"` check needs to track whatever taxonomy the passthrough
  field actually carries (`flow_filter.py`'s `BULLISH`/`BEARISH`/`NEUTRAL`, not the prompt's current
  `ACCUMULATING`/`DISTRIBUTING`/`NEUTRAL`) — flagged explicitly so this isn't discovered as a silent
  analytics-dashboard regression after the fact
- `tests/agent_firm/test_flow.py`, `tests/agent_firm/test_analytics.py` — update fixtures/assertions

**Dependencies:** none for the passthrough fields; `net_foreign_14d`/`trend_7d` are small new
computations with no upstream dependency.

**Risk:** Medium — the taxonomy change is the one part of this work package with a real regression
surface (`analytics.py`'s agreement dashboard), not the flow logic itself. Treat the taxonomy alignment
as a required sub-task, not an afterthought.

**Acceptance criteria:**
- `flow_v1.md` no longer asks the model to classify accumulation/distribution or sum lots.
- `analytics.py::_is_aligned`'s flow check matches whatever taxonomy `FlowSummary.verdict` actually
  carries, verified by a test that exercises `agent_agreement()` end-to-end.
- `net_foreign_14d` is computed once, in code, and is bit-for-bit reproducible given the same rows.

---

## WP3 — `RegimeAssessment` (Regime Analyst)

**Objective:** move the three prose-encoded thresholds (`consistency_pct >= 55%`, `vol_ratio > 3.0`,
`avg_sharpe > 0.8`) into a pure function.

**Affected files:**
- New: `engine/agent_firm/regime_rules.py` (or a function added to `guardrails.py` if a separate module
  is judged unnecessary — implementation-level choice, not architectural)
- `engine/agent_firm/firm.py::_build_context` — compute `RegimeAssessment`
- `engine/agent_firm/agents/regime.py` — pass `RegimeAssessment`
- `engine/agent_firm/prompts/regime_v1.md` — remove the three threshold rules; keep only the
  macro/sector narrative reasoning task
- `tests/agent_firm/test_regime.py` — add unit tests for the new pure function directly (no LLM call
  needed to test threshold logic — this is the whole point)

**Dependencies:** none.

**Risk:** Low — pure extraction of already-stated rules into code; no new data source, no interface
change.

**Acceptance criteria:**
- `regime_v1.md`'s three numeric threshold rules no longer appear as prose instructions.
- The new pure function has direct unit test coverage independent of any LLM/provider mock.
- `regime_call`/`sector_tailwind`/`macro_risk` are bit-for-bit reproducible given the same `wf_scores`/
  `daily_screen` rows.

---

## WP4 — `ConsensusSummary` + Open-Position/`entries_blocked` Guardrails (Risk Manager)

**Objective:** replace the "≥3 of 4 negative" prose count and the "already has an open position" prose
dedup rule with deterministic guardrails, and close the already-named `RiskLimits.entries_blocked` gap
from `AF1_FAILURE_CONTRACT.md` §6 using the same mechanism.

**Affected files:**
- `engine/agent_firm/guardrails.py` — add `build_consensus_summary()`, extend `apply_guardrails()` with
  two new veto conditions (`already_open_position`, `entries_blocked`) and the negative-count rule
- `engine/agent_firm/firm.py::_run_risk` — assemble `ConsensusSummary` before the Risk agent call,
  attach `RiskLimits.entries_blocked` (requires `paper_trade.py::is_entries_blocked()` to be wired into
  the Context API per `AF1_CONTEXT_API.md`'s `RiskLimits` design — this work package should land
  together with or immediately after that wiring, not before)
- `engine/agent_firm/prompts/risk_v2.md` — remove the "≥3 negative" and "already open position" prose
  rules; the LLM's decision now only needs to reason about cases the deterministic gates don't already
  resolve
- `tests/agent_firm/test_risk_v2.py`, a new `tests/agent_firm/test_guardrails.py` (or extend the existing
  one if present) — unit test every new veto path without any LLM call

**Dependencies:** `AF1_CONTEXT_API.md`'s `RiskLimits.entries_blocked` field.

**Risk:** **Medium-High.** This is the first work package in this backlog that changes actual veto
outcomes, not just internal wiring — a candidate the LLM would have approved may now be deterministically
vetoed by the open-position or `entries_blocked` gate. Per this repository's own established pattern
(`AUTH_MODE`/`EDGE_SCORE_MODE`/`SECTORS_APP_MODE`, all `off`/`shadow`/`enforce`), **ship in shadow mode
first**: log what the new guardrail would have decided, without enforcing it, for at least one full
evaluation cycle before switching it to `enforce`.

**Acceptance criteria:**
- `apply_guardrails` vetoes on `already_open_position=True` and `entries_blocked=True` unconditionally,
  matching `AF1_FAILURE_CONTRACT.md` §6's stated contract ("the Risk agent MUST treat `entries_blocked`
  as at least as strong a signal as any of its own analysis").
- A shadow-mode logging path exists and has been observed for at least one cycle before `enforce` is
  flipped, with a recorded comparison of LLM-only vs. guardrail-adjusted decisions.
- `risk_v2.md` no longer contains the "already has an open paper trade" or "≥3 of 4 negative" prose
  rules.

---

## WP5 — Deterministic `size_hint` (Risk Manager / Position Sizing)

**Objective:** replace the LLM-picked numeric `size_hint` with a qualitative `size_tier` input to a
deterministic sizing function.

**Affected files:**
- `engine/agent_firm/guardrails.py` — add `resolve_size_hint(tier, consensus, quant_score) -> float`,
  bounded `[0.0, 1.5]` by construction
- `engine/agent_firm/prompts/risk_v2.md` — replace the numeric `size_hint` field/table with a
  `size_tier: "reduce"|"normal"|"increase"` field
- `engine/agent_firm/agents/risk.py`, `firm.py::_run_risk` — call `resolve_size_hint()` after the LLM
  response, write only the resolved value to `AgentDecision.size_hint`
- `engine/agent_firm/schemas.py` — `size_hint` bound becomes enforceable by construction (WP6 may still
  add a schema-level `ge`/`le` as defense in depth)
- `tests/test_agent_size_hint.py`, `tests/agent_firm/test_risk_v2.py` — update fixtures to the new
  `size_tier` shape; add direct unit tests for `resolve_size_hint()`

**Dependencies:** WP4 (`resolve_size_hint` takes `ConsensusSummary` as an input).

**Risk:** **High — the one item in this entire backlog that changes real position-sizing numbers in
production.** Mandatory shadow-mode rollout: compute and log both the old LLM-derived `size_hint` and
the new `resolve_size_hint()` output side by side, without switching `scheduler/scanner.py:1609`'s
`_size_mult` source, for at least one full evaluation cycle. Only switch the live multiplier source after
that comparison has been reviewed.

**Acceptance criteria:**
- `risk_v2.md`'s numeric `size_hint` lookup table (0.5/1.0/1.2) is removed from the prompt entirely.
- `resolve_size_hint()` is unit-tested without any LLM call and is provably bounded to `[0.0, 1.5]` for
  every possible `size_tier`/`ConsensusSummary`/`quant_score` combination (a property-style test, not
  just example cases, is appropriate here given the capital-affecting nature of this function).
- A shadow-mode comparison log exists and has been reviewed before `scanner.py` is switched to consume
  the deterministic value.

---

## WP6 — Schema Hardening

**Objective:** enforce the `size_hint` contract at the schema level as defense in depth.

**Affected files:**
- `engine/agent_firm/schemas.py` — add `ge=0.0, le=1.5` (or equivalent) to `AgentDecision.size_hint`
- `tests/agent_firm/test_schemas.py` — add a rejection test for an out-of-bound value

**Dependencies:** WP5 (by the time this lands, `resolve_size_hint()` should already make violation
impossible in practice — this is belt-and-suspenders, not the primary control).

**Risk:** Low — only rejects values already outside the documented, versioned contract every prompt
version has stated since `risk_v1.md`.

**Acceptance criteria:** constructing an `AgentDecision` with `size_hint` outside `[0.0, 1.5]` raises a
validation error.

---

## WP7 — Documentation Reconciliation

**Objective:** amend `AF1_CONTEXT_API.md` to reflect that `RecentHistory`'s relevant fields carry derived
facts (`TrendContext`, `FlowSummary`, `RegimeAssessment`), not raw rows, once WP1-3 have actually shipped.

**Affected files:**
- `docs/agent_firm/AF1_CONTEXT_API.md` — dated amendment (never a silent edit, per this repository's own
  documentation convention for point-in-time records)

**Dependencies:** WP1-3 design agreement (does not need to wait for full implementation — the amendment
can be written once the shapes are fixed, ahead of code landing, exactly as `AF1_CONTEXT_API.md` itself
was written ahead of AF-2 implementation).

**Risk:** None — documentation only.

**Acceptance criteria:** `AF1_CONTEXT_API.md`'s `RecentHistory` type definition no longer describes
`ohlcv`/`stockbit_flow`/`broker_flow`/`strategy_edge`/`recent_screen_signals` as plain raw-row lists
without qualification; it references this document set for the derived shapes those fields actually
carry post-migration.

---

## Priority Summary

| Priority | Work packages | Why |
|---|---|---|
| **P0** | WP4, WP5 | Only two items with real behavior-change / capital-at-risk dimension — everything else is narrative-quality improvement inside an already fail-open-safe system |
| P1 | WP1, WP2, WP3 | Materially improve verdict trustworthiness and audit-trail integrity (especially WP2's duplication fix), but do not change what happens to real capital on their own |
| P2 | WP6, WP7 | Defense in depth / documentation hygiene, low risk and low urgency |

**Recommended implementation order:** WP3 → WP1 → WP2 → WP4 → WP5 → WP6 → WP7 (lowest-risk,
no-dependency items first, building up to the two capital-affecting items last so the shadow-mode
rollout discipline in WP4/WP5 can be exercised on a codebase where the surrounding context objects
already exist and are already tested).
