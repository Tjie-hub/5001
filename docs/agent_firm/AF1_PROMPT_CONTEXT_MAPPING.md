# AF-1 — Prompt / Context Mapping

**Date:** 2026-07-29
**Basis:** `AF1_CONTEXT_API_V2_SPEC.md`, `AF1_CONTEXT_OBJECT_CATALOG.md`.
**Scope:** every prompt file in `engine/agent_firm/prompts/` (7 total), reviewed against the V2 object
set. This is prompt-*content* impact only — no prompt file is edited by this document; line references
are to the current files as of this review.

---

## `technical_v1.md` — Technical Analyst

**Current deterministic computations asked of the LLM:**
- Infer moving-average position ("price above key MAs") from 60 raw daily bars (line 19) — Audit T2.
- Derive `key_levels.support`/`resistance` from the same raw bars (line 14) — Audit T1.

**Replacement context fields:** `TechnicalContext` (all fields) — see Catalog.

**Prompt sections to remove:**
- Line 4-6's input description ("Recent OHLCV data for the ticker (up to 60 daily bars)") — replaced by
  a `TechnicalContext` description.
- The `key_levels` output field (line 14) — no downstream consumer was found for this LLM-produced value
  (verified: nothing reads `technical.output.key_levels` beyond storage/display), and
  `TechnicalContext.support_levels`/`.resistance_levels` already carries the computed answer. Removing it
  from the *output* schema (it remains available as an *input* the model may reference in `reasoning`)
  eliminates an entire field the model previously had to compute with no verification path.

**Prompt sections to rewrite:**
- Conviction guidance (lines 18-21) — currently keyed to vague conditions ("volume support", "no
  divergence") the model has no computed values to check against. Rewrite to reference
  `TechnicalContext.adx`, `.close_vs_sma50_pct`, `.pattern_flags` directly, so a conviction band is a
  judgment about *already-known* numbers, not a proxy for computing them first.

**Expected simplification:** the prompt shrinks from "here are raw bars, compute indicators, then judge"
to "here are the indicators, judge." Removes one full output field (`key_levels`); the input section
gets *more* structured (more named fields) but the reasoning burden the model carries gets strictly
smaller. Net: prompt is not necessarily shorter in character count, but the computational burden it
implicitly assigns the model drops to zero.

---

## `flow_v1.md` — Flow Specialist

**Current deterministic computations asked of the LLM:**
- Classify `flow_verdict` (ACCUMULATING/DISTRIBUTING/NEUTRAL) from raw 14d rows (lines 14, 21-23) —
  Audit F1, a duplication of `stockbit_flow.verdict` already present in the same payload.
- Classify `smart_money_signal` from the same raw rows (line 15) — Audit F2, duplication of
  `stockbit_flow.smart_money`.
- Sum `net_lot` over `broker_flow` rows for `net_foreign_14d` (lines 16, 24) — Audit F3.

**Replacement context fields:** `FlowContext.verdict`, `.smart_money`, `.net_foreign_14d` (all
passthrough/precomputed), `.trend_7d` (new deterministic early-divergence tag).

**Prompt sections to remove:**
- Lines 21-23 (the ACCUMULATING/DISTRIBUTING/NEUTRAL classification criteria) — the classification no
  longer happens in the prompt.
- Line 24 (`net_foreign_14d` sum instruction) — removed entirely; the value is now a passthrough input.
- `flow_verdict`, `smart_money_signal`, `net_foreign_14d` all move from the **output** schema (lines
  14-16) to the **input** payload.

**Prompt sections to rewrite:**
- The output schema narrows to `reasoning` (and, if retained, a qualitative cross-check field — see open
  question below).

**Expected simplification:** output schema shrinks from 4 fields to 1-2. **Open design question, flagged
rather than resolved here:** once `verdict`/`smart_money`/`net_foreign_14d` are all passthrough, what
residual task justifies a full LLM call for this agent? The one genuine candidate is cross-referencing
the daily `verdict` against `FlowContext.flow_bars_recent` (intraday) for early divergence the daily
figure hasn't caught yet — e.g., "the daily verdict says ACCUMULATING but this morning's bars show
selling starting." This is real, bounded, interpretive work (comparing two already-computed signals for
disagreement), not a computation the audit flags — but whether it's *valuable enough* to keep a full
agent call versus collapsing Flow's contribution into a precomputed field consumed directly by
`ConsensusContext` is a product decision for AF-2, not an architecture decision this document makes
unilaterally.

---

## `regime_v1.md` — Regime Analyst

**Current deterministic computations asked of the LLM:**
- `regime_call` via `consistency_pct >= 55%` threshold (lines 13, 20) — Audit R1.
- `sector_tailwind` via `avg_sharpe > 0.8` threshold (lines 14, 25) — Audit R2.
- `macro_risk` via a vol_ratio/signal co-occurrence rule (lines 15, 26) — Audit R3.

**Replacement context fields:** `RegimeContext.regime_call`, `.sector_tailwind`, `.macro_risk`,
`.best_strategy`, `.consistency_pct` (all precomputed).

**Prompt sections to remove:**
- Lines 19-26 in full (the entire "Guidance" threshold block) — every rule there becomes code.
- `regime_call`, `sector_tailwind`, `macro_risk` move from output (lines 13-15) to input.

**Prompt sections to rewrite:**
- The task description (line 8: "confirm or challenge the quant pipeline's regime reading") no longer
  makes sense once the challenge itself is deterministic — rewrite to "explain the macro/sector context
  behind this regime call, drawing on qualitative signal beyond the three factors already computed"
  (e.g., sector-wide news, cross-ticker correlation the deterministic rule doesn't capture).

**Expected simplification:** same shape as Flow — output schema shrinks to essentially `reasoning`. Same
open question applies: once the three-field classification is deterministic, the Regime Analyst's
residual job is narrative color, not classification. Flag for the same AF-2 product decision as Flow —
whether that residual narrative task justifies its own LLM call or should be folded into the Risk agent's
own reasoning over `RegimeContext` directly.

---

## `news_v1.md` — News/Sentiment Analyst — **no change required**

**Current deterministic computations asked of the LLM:** none (Audit N1 — clean).

**Replacement context fields:** `NewsContext` (typed container for the same fields already passed;
`mentions_count_7d` added as a minor convenience, not a behavior change).

**Prompt sections to remove/rewrite:** none.

**Expected simplification:** none — this prompt is already the model the others are being brought in
line with. Cited here only for completeness (every prompt reviewed, per the task's own instruction), not
because it needs work.

---

## `bull_v1.md` — Bull Researcher — **no change required**

**Current deterministic computations asked of the LLM:** none (Audit B1 — clean).

**Replacement context fields:** none new — consumes the four analysts' `AgentResult`s, which are now
better-grounded (Technical/Flow/Regime verdicts derived from real computed facts instead of raw-row
guesses), but the Bull agent's own prompt and task are unaffected.

**Prompt sections to remove/rewrite:** none.

**Expected simplification:** none directly, but an indirect quality improvement — the "strongest possible
bull case" this agent constructs is only as good as the analyst outputs it's built from; grounding those
outputs (WP1-3) should make the bull case's `key_strength` field reference real, verifiable factors more
often than a plausible-sounding guess.

---

## `bear_v1.md` — Bear Researcher — **no change required**

Same assessment as `bull_v1.md`. No violation found (Audit B1), no prompt change required, same indirect
quality benefit from better-grounded upstream analyst outputs.

---

## `risk_v2.md` — Risk Manager

**Current deterministic computations asked of the LLM:**
- `quant_score` normalization — **already fixed**, done in `guardrails.py::normalize_quant` before the
  prompt runs (not a finding, cited for completeness).
- "Veto if ≥3 of [Technical, Flow, Regime, News] are clearly negative" (line 23) — Audit K1.
- "Veto if ticker already has an open paper trade" (line 26) — Audit K2, and the prompt claims data
  (`open_trades`, line 7) that is **never actually sent to this agent today** (verified: `agents/risk.py`'s
  `run()` signature has no `context` parameter).
- `size_hint` numeric lookup table (lines 16, 28-30) — Audit K3.
- Confidence bands keyed to "clear consensus across all analysts" (lines 36-39) — Audit K4, same
  counting problem as K1.

**Replacement context fields:** `ConsensusContext.negative_count`/`.positive_count`/`.aligned_bullish`/
`.already_open_position`/`.entries_blocked` (all precomputed); LLM output field `size_hint` replaced by
`size_tier` (qualitative), resolved to a number by `resolve_size_hint()` (Tier 3) after the LLM call
returns.

**Prompt sections to remove:**
- Line 23 ("Veto if >= 3... are clearly negative AND quant_score < 0.30") — becomes a hard guardrail in
  `apply_guardrails`, not a prompt rule.
- Line 26 ("Veto if ticker already has an open paper trade") — same, becomes a hard guardrail, and
  requires the `ConsensusContext`/`PortfolioContext` wiring fix (Part 1 of the V2 spec) to even be
  possible for the first time.
- Lines 28-30 (the `size_hint` numeric table) — replaced entirely by the `size_tier` three-way choice.

**Prompt sections to rewrite:**
- The output schema (lines 11-18): `size_hint: 0.0-1.5` becomes `size_tier:
  "reduce"|"normal"|"increase"`.
- The "Decision framework" section (lines 22-27) narrows to the rules that remain genuinely LLM
  judgment: line 24 ("Veto if technical conviction < 0.3 AND flow is DISTRIBUTING") and line 25 ("Veto if
  flow is BEARISH/DISTRIBUTING and technical is not BULLISH") are borderline — both are still fixed
  threshold/boolean rules per the Computation Boundary Policy's Governing Test, and should be evaluated
  for the same guardrail treatment as K1/K2 in AF-2, not assumed to survive as prompt text unchanged.
  This document flags them rather than resolving them, since they weren't in the original Audit's
  primary findings but read, on this closer pass, as the same category.
- Confidence guidance (lines 36-39) — rewrite band descriptions to reference `ConsensusContext.aligned_bullish`
  directly instead of "clear consensus," removing the implicit counting task.

**Expected simplification:** this is the largest single simplification in the set. The "Decision
framework" section — currently the bulk of the file — shrinks to only the rules that survive the
Governing Test as genuine judgment calls (plausibly none, per the note above, pending AF-2's review of
lines 24-25). The remaining LLM task is narrower and sharper: given a fixed set of deterministic gates
that have already run, does the bull/bear debate surface anything that should still tip a genuinely
close call, and what confidence/size_tier reflects that.

---

## Summary Table

| Prompt | Violations found | Output fields removed | Output fields added | Residual LLM task after migration |
|---|---|---|---|---|
| `technical_v1.md` | T1, T2 | `key_levels` | — | Verdict synthesis from grounded indicators |
| `flow_v1.md` | F1, F2, F3 | `flow_verdict`, `smart_money_signal`, `net_foreign_14d` | — | Open question: intraday-vs-daily divergence narrative, or fold into `ConsensusContext` directly |
| `regime_v1.md` | R1, R2, R3 | `regime_call`, `sector_tailwind`, `macro_risk` | — | Open question: macro/sector narrative color, or fold into Risk agent directly |
| `news_v1.md` | none | — | — | Unchanged — sentiment/catalyst NLU |
| `bull_v1.md` | none | — | — | Unchanged — argumentation |
| `bear_v1.md` | none | — | — | Unchanged — argumentation |
| `risk_v2.md` | K1, K2, K3, K4 (+2 newly-flagged borderline rules, lines 24-25) | `size_hint` (numeric) | `size_tier` (qualitative) | Judgment on genuinely close calls only, after deterministic gates have run |

**Net effect:** 3 of 7 prompts (News, Bull, Bear) require zero change — real evidence that the multi-agent
design itself is sound; the flaw was isolated to how four of the seven agents were fed data, not to the
architecture of having seven agents. 2 of 7 (Flow, Regime) shrink enough that AF-2 should explicitly
revisit whether they remain worth a dedicated LLM call. 1 of 7 (Risk) carries the largest simplification
and the two capital/behavior-affecting fixes (K2, K3) already flagged P0 in `AF1_REMEDIATION_PLAN.md`.
