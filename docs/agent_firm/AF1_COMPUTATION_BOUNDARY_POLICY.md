# AF-1 — Computation Boundary Policy

**Date:** 2026-07-29
**Status:** PROPOSED — architectural policy, pending owner sign-off before AF-2 implementation begins,
same governance weight as the six 2026-07-28 AF-1 documents.
**Basis:** `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`.
**Relationship to the existing AF-1 corpus:** `AF1_RESPONSIBILITY_MATRIX.md`'s Primary Principle is
"Production Engine owns operations. Agent Firm owns decisions." That principle answers *who runs the
system*. This document answers a narrower, previously unstated question inside "Agent Firm owns
decisions": **which parts of a decision are computation, and which are judgment** — because "Agent Firm
owns decisions" was being read, in practice, as "Agent Firm's prompts may compute anything needed to
reach a decision," which is how `size_hint`, `flow_verdict`, and three regime thresholds ended up as
prose arithmetic. This document closes that reading.

---

## The Governing Test

Before any value in a prompt or an agent's output is accepted as-is, apply this test:

> **If the rule that produces this value can be written as a pure function with no LLM call — the same
> function today's prose is implicitly asking the model to simulate — it is not a reasoning task. Write
> the function.**

A corollary, verified repeatedly in the Audit: **if a value already exists, computed, in the same
context payload the prompt receives, asking the LLM to reproduce it is never correct** — it can only
match (wasted tokens, wasted latency) or drift (a second, uncontrolled definition of the same fact).
`flow_verdict`/`smart_money_signal` (Audit F1, F2) are the clearest instances: `flow_filter.py` already
computed and persisted the answer; the prompt asks for it again anyway.

---

## Production Engine SHALL Compute

- **All technical indicators** — moving averages, ATR, ADX, VWAP, support/resistance, volume profile,
  pattern detection. *Rationale:* these are closed-form numeric functions with one correct answer per
  input; an LLM asked to eyeball them from raw bars produces a plausible-sounding approximation with no
  reproducibility guarantee, in a domain (`engine/indicators.py`, `engine/chart_indicators.py`) where the
  exact functions already exist and are already tested.
- **All flow/smart-money classifications and their component scores** — verdict, smart-money tier,
  composite score, foreign score. *Rationale:* `flow_filter.py` already computes these deterministically
  from the same 14-day window; a second, LLM-derived definition of "accumulating" that disagrees with
  the first is not a second opinion, it is data corruption of the firm's own audit trail.
- **All threshold-defined regime/risk classifications** — any categorical output whose defining rule is
  stated in the prompt as a numeric comparison (`consistency_pct >= 55%`, `vol_ratio > 3.0`,
  `avg_sharpe > 0.8`). *Rationale:* a rule expressible as `if x >= 0.55` is code that happens to be
  written in English inside a system prompt. Writing it as a prompt instead of a function buys nothing
  and costs determinism, testability, and auditability.
- **All arithmetic aggregation over structured rows** — sums, means, ratios, counts. *Rationale:*
  arithmetic has exactly one correct answer; an LLM computing `SUM(net_lot)` over a JSON array is strictly
  worse than `sum()` on every axis (cost, latency, correctness risk) with zero compensating benefit.
- **All position-sizing multipliers and any other value that changes real capital allocation** — lots,
  `capital_used`, exposure caps, `size_hint`'s final numeric value. *Rationale:* this is the one category
  where an ungrounded LLM output has a direct, unmediated path to money at risk (`paper_trade.py:413`).
  The severity asymmetry between "wrong narrative" and "wrong position size" means this category gets
  the strictest rule in this policy, stricter than plain threshold evaluation: **no LLM output may reach
  a sizing function as anything other than one bounded, qualitative input among several** (see
  Position Sizing exception below).
- **All deterministic gating rules expressible as a fixed predicate** — already-open-position dedup,
  the `entries_blocked` circuit breaker (`AF1_CONTEXT_API.md`'s `RiskLimits`), N-of-M analyst-negative
  counts. *Rationale:* these are boolean gates, not judgment calls; the existing `apply_guardrails`
  downgrade-only mechanism already proves this pattern works in this codebase — it just doesn't yet
  cover all of these rules (Audit K1, K2).
- **All statistical calculations** — win rate, Sharpe, cohort comparisons. *Rationale:* already
  correctly implemented in `analytics.py`, entirely outside any prompt. No change requested; stated here
  only to make the boundary explicit and prevent regression.

## Agent Firm SHALL Reason About

- **Synthesizing a directional verdict from already-computed facts.** Once `TrendContext`,
  `FlowSummary`, and `RegimeAssessment` (see `AF1_REQUIRED_CONTEXT_OBJECTS.md`) exist, deciding "is this
  BULLISH given SMA20 > SMA50, ADX 28, and an accumulating flow tag" is genuine synthesis — no single
  computed fact determines the verdict alone, and weighing several computed facts against each other is
  exactly the judgment an LLM is suited for. *Rationale:* this is the actual value-add of a multi-agent
  review layer; the goal of this policy is to re-ground that judgment in real inputs, not to eliminate
  it.
- **Natural-language interpretation of unstructured text** — news headlines, web-search snippets.
  *Rationale:* there is no deterministic function that extracts sentiment from Indonesian financial news
  prose; this is a genuine NLU task with no closed-form alternative (`prompts/news_v1.md`, Audit N1 —
  already correctly scoped today).
- **Constructing an argument that weighs already-produced analyst outputs against each other** — the
  Bull/Bear debate. *Rationale:* argumentation over a fixed evidence set is reasoning, not arithmetic;
  Audit B1 found no violation here and none is introduced by this policy.
- **Calibrating a qualitative confidence or conviction level**, provided the evidence set behind it is
  already computed and provided the calibration is not itself gated by a threshold restated in the
  prompt (see the Threshold Evaluation rule above — a confidence value used only for display/context is
  reasoning; a confidence value whose numeric bands are literally the veto rule is threshold evaluation
  wearing a confidence label).
- **Producing human-readable rationale** for every decision — this is required output, not optional
  narrative; every `AgentDecision.rationale` must remain LLM-authored prose, since a template-generated
  explanation would lose exactly the interpretive value this system exists to add.

## LLMs SHALL NEVER Compute

1. **A technical indicator value** (moving average, ATR, support/resistance level, VWAP, ADX) from raw
   price bars. *Rationale:* one correct answer, closed-form, already implemented in Production Engine.
2. **A sum, mean, ratio, or other arithmetic aggregate** over structured numeric rows handed to it in
   context. *Rationale:* strictly worse than code on cost, latency, and correctness, with no offsetting
   benefit — there is no interpretive judgment in `SUM(net_lot)`.
3. **A position-sizing multiplier, or any other numeric value consumed unmodified as a real
   capital-allocation input.** *Rationale:* the one category where a wrong output has direct financial
   consequence rather than a mislabeled narrative; the asymmetry justifies an absolute rule, not a
   judgment call about how much to trust the model this time.
4. **A threshold comparison against a numeric constant stated as a fixed rule in the prompt itself.**
   *Rationale:* per the Governing Test — if the rule is a fixed predicate, it is not a judgment call, it
   is code. Restating it as prose does not make it reasoning; it makes it an unauditable, untested,
   non-reproducible copy of a rule that belongs in a function signature.
5. **A count over categorical values across multiple structured inputs** (e.g., "how many of these 4
   analysts are negative"). *Rationale:* counting is arithmetic; the LLM's job starts after the count
   exists, when deciding *how much* a given count should matter is genuinely contextual — but the count
   itself has one correct value.
6. **A value that duplicates a field already computed and stored by Production Engine and handed to the
   same prompt.** *Rationale:* per the Governing Test's corollary — this can only match (waste) or drift
   (corrupt the firm's own audit trail with two disagreeing definitions of the same fact).

## LLMs MAY Compute

- **A calibrated confidence/conviction score**, as long as no fixed numeric threshold gating real
  behavior is restated in the same prompt as the reason for that score. *Rationale:* expressing
  uncertainty about a synthesis is reasoning; deciding what happens at 0.3 vs 0.8 confidence is a policy
  decision that belongs to Production Engine's guardrail layer, not to the number's author.
- **A qualitative categorical judgment synthesized from multiple already-computed facts** — a verdict,
  a sentiment label, a "which of these looks most compelling" ranking among a small already-identified
  set. *Rationale:* this is what a reasoning system is for; nothing in this policy restricts it, only
  the inputs it may be built from.
- **A qualitative sizing *preference* tier** (e.g., `"reduce"`/`"normal"`/`"increase"`), consumed as one
  bounded input among several by a Production Engine sizing function that computes the actual multiplier
  — never the multiplier itself. *Rationale:* this is the one narrow, explicitly bounded exception to
  the Position Sizing rule above; it preserves the LLM's ability to flag "this setup feels thinner than
  the quant score alone suggests" as a genuine synthesis signal, while keeping the arithmetic that turns
  that signal into lots entirely in code, testable without any LLM call — the same pattern
  `guardrails.py::normalize_quant` already proves works for `quant_score`.

---

## How This Interacts With Existing AF-1 Decisions

- **Does not reopen** `AF1_SCHEMA_OWNERSHIP_DECISION.md`, `AF1_DATA_ACCESS_LAYER.md`,
  `AF1_FAILURE_CONTRACT.md`, `AF1_RESPONSIBILITY_MATRIX.md`, or `AGENT_FIRM_GOVERNANCE.md` — none of
  those documents' decisions depend on where a value is computed, only on who owns the connection,
  schema, and process boundary.
- **Amends** `AF1_CONTEXT_API.md` only in the narrow sense of specifying what shape `RecentHistory`'s
  fields take (derived, not raw) — see `AF1_REQUIRED_CONTEXT_OBJECTS.md`. Does not change the six-type
  structure, the `MarketContext`/`PortfolioState`/`RiskLimits`/`SessionState` design, or the "one bundled
  vs. five separate parameters" open item, all of which remain exactly as decided.
- **Extends** `AF1_FAILURE_CONTRACT.md` §5's guardrail-permanence contract: the new deterministic gates
  this policy requires (open-position dedup, N-of-M consensus count, `size_hint` resolution) belong in
  `apply_guardrails`'s family, using the same "deterministic, post-LLM, unit-testable without the LLM"
  pattern already governed there — not a new mechanism.
- **Does not touch** `tools/sqlite_query.py`'s free-form-SQL question — already resolved as data-access
  scope in `AF1_IMPLEMENTATION_SPEC.md` Decision B.

## Compatibility Note

Per `AGENT_FIRM_GOVERNANCE.md`'s versioning policy, none of the changes this policy implies are MAJOR:
`SignalCandidate.indicators` is already an optional field (populating it is invisible to any caller not
reading it); `AgentDecision.size_hint` remains the same type, only gaining a bound that rejects values
already outside its documented contract; the decision-lifecycle enum is untouched. This is MINOR-at-most
under the existing policy, not a breaking change to the interface `AF1_IMPLEMENTATION_SPEC.md` finalized.
