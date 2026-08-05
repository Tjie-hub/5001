# AF-1 — Remediation Plan

**Date:** 2026-07-29
**Basis:** `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`, `AF1_COMPUTATION_BOUNDARY_POLICY.md`,
`AF1_REQUIRED_CONTEXT_OBJECTS.md`.
**Scope:** planning only, per this review's own constraint — no code is changed by this document.
**Sequencing note:** this plan is written to slot into `AF1_IMPLEMENTATION_SPEC.md` Part 3's existing,
already-decided AF-2 implementation order — specifically step 6 ("Build the Context API's six typed
objects and redirect `_build_context()` to consume them... the largest single implementation item") and
step 7 ("Wire `RiskLimits.entries_blocked` into the guardrail layer"). Nothing below proposes a
competing sequence; it names where each item lands inside the sequence already fixed there.

---

## Part 4 — Per-Violation Migration Plan

| # | Violation (Audit ref) | Current implementation | Target implementation | Owner | Breaking change risk | Backward compat | Migration order | Complexity | Priority |
|---|---|---|---|---|---|---|---|---|---|
| WP1 | T1, T2 — Technical indicators/S-R from raw bars | `technical_v1.md` + 60 raw OHLCV bars, LLM infers | `TrendContext` populated from `engine/indicators.py`/`chart_indicators.py`, fed via `SignalCandidate.indicators` | Production Engine | Low — additive optional field, no interface signature change | Full — `indicators` is already optional per `AGENT_FIRM_INTERFACE_SPEC.md` | Alongside AF-2 step 6 | Low (functions already exist) | P1 |
| WP2 | F1, F2, F3 — Flow verdict/smart-money/sum duplication | `flow_v1.md` + raw 14d rows, LLM re-derives verdict/smart_money/net_foreign_14d | `FlowSummary` — verdict/smart_money passthrough from `flow_filter.py`, `net_foreign_14d` computed once | Production Engine | Medium — taxonomy passthrough may change the exact string values `analytics.py::_is_aligned` (line 109) hardcodes | Requires a lockstep update to `analytics.py`'s alignment check | Alongside AF-2 step 6 | Low-Medium | P1 |
| WP3 | R1, R2, R3 — Regime thresholds | `regime_v1.md` prose `if/elif` over raw `wf_scores`/`daily_screen` | `RegimeAssessment` from a new pure function | Production Engine | Low — pure extraction, no data source change | Full | Alongside AF-2 step 6 | Low | P1 |
| WP4 | K1, K2 — Consensus counting + open-position dedup + `entries_blocked` gap | Prose rules in `risk_v2.md`; `entries_blocked` not visible to Agent Firm at all today (`AF1_FAILURE_CONTRACT.md` §6) | `ConsensusSummary` + guardrail vetoes in `apply_guardrails` | Production Engine (guardrails.py) | **Medium-High — changes actual veto behavior**, not just internal wiring: previously-approved candidates may now be vetoed | Must ship shadow-mode first (log the new guardrail's would-be verdict without enforcing it), per this repo's own `off/shadow/enforce` convention | AF-2 step 7 (explicitly where `RiskLimits.entries_blocked` wiring was already scheduled) | Medium | **P0** |
| WP5 | K3 — `size_hint` lookup table | Prose numeric table in `risk_v2.md`, unclamped, flows to `paper_trade.py:413` | `SizingInput`/`SizingResult` via `guardrails.py::resolve_size_hint()` | Production Engine (guardrails.py) | **High — this is the one item that changes real position-sizing numbers in production** | Must ship shadow-mode: log both the old LLM-derived and new deterministic `size_hint` side by side before switching the scanner to consume the deterministic one | After WP4 (needs `ConsensusSummary` as an input); sequenced immediately after AF-2 step 7 | Medium | **P0** |
| WP6 | S2 — missing `size_hint` bound | `schemas.py:50`, no `ge`/`le` | Add bound (or rely on WP5's own clamp, whichever lands first makes the other redundant but not harmful) | Production Engine (schemas.py) | Low | Full — only rejects values already outside the documented contract | After WP5 | Trivial | P2 |
| WP7 | O2 — `AF1_CONTEXT_API.md`'s `RecentHistory` still specified as raw rows | Doc says `ohlcv`/`stockbit_flow`/`broker_flow`/`strategy_edge`/`recent_screen_signals` are raw lists | Dated amendment referencing `TrendContext`/`FlowSummary`/`RegimeAssessment` as the actual field shapes | Documentation only | None | N/A | After WP1-3 designs are implemented, so the amendment describes what actually shipped | Trivial | P2 |

**Reading the table:** WP4 and WP5 are marked P0 because they are the only two items with a real
behavior-change / capital-at-risk dimension — everything else is a quality/reliability improvement to
already-fail-open-safe narrative generation. This matches the Audit's own severity ranking (K2 and K3
were named as carrying the highest real-world risk of any finding).

---

## Part 5 — Decision Integrity

**Claim to demonstrate:** after WP1-WP7 land, Agent Firm performs zero technical analysis calculations,
zero arithmetic, zero statistical calculations, zero position sizing, and zero deterministic lookups —
only reasoning, synthesis, critique, confidence calibration, and recommendation.

| Category | Pre-migration LLM-side occurrence | Post-migration state |
|---|---|---|
| Technical analysis calculations | T1 (S/R), T2 (MA position) | **Zero.** `TrendContext` supplies both; `technical_v1.md` no longer asks for either. |
| Arithmetic | F3 (`net_foreign_14d` sum), K1 (analyst-negative count) | **Zero.** `FlowSummary.net_foreign_14d` and `ConsensusSummary.negative_count` are both computed once, in code, before the relevant prompt runs. |
| Statistical calculations | None found in a prompt (Audit A1 confirms `analytics.py` already owns this category correctly) | **Zero — no change needed**, already compliant. |
| Position sizing | K3 (`size_hint` 0.0-1.5 lookup table) | **Zero.** The LLM emits `size_tier` (a qualitative label); `resolve_size_hint()` computes the number. |
| Deterministic lookups | R1-R3 (regime thresholds), K2 (open-position dedup) | **Zero.** `RegimeAssessment` and the `already_open_position`/`entries_blocked` guardrail vetoes replace all four. |

### Explicit Exceptions

Two residual LLM outputs remain adjacent to "computation" after migration. Both are named explicitly,
per the Definition of Done's own requirement that "any remaining exception is justified, not silently
allowed":

1. **`confidence` (0.0-1.0).** The LLM still emits a numeric confidence score. This is **not** an
   exception to "zero threshold evaluation" in the sense that matters: per the Computation Boundary
   Policy's "LLMs MAY compute" section, a confidence score is permitted specifically because, post-WP4,
   no fixed numeric band gating real behavior is restated in the same prompt as the reason for that
   score — the *bands* (`SIDEWAYS/BEAR regime confidence floor`, already in `apply_guardrails` today)
   live in code, not in the number's own definition. The number itself is a calibration, consumed by
   guardrails that were already deterministic before this remediation and remain so after.
2. **`size_tier` (`reduce`/`normal`/`increase`).** A three-way qualitative choice, not a number. Justified
   under the Policy's Position Sizing exception: it is consumed as one bounded input to
   `resolve_size_hint()`, never becomes a multiplier itself, and cannot by construction produce a
   `size_hint` outside `[0.0, 1.5]` regardless of what the LLM emits — the arithmetic that has real
   capital consequence stays entirely in code.

No other exception is required. Every other numeric or categorical output an LLM produces post-migration
(`verdict`, `sentiment`, `regime` narrative color, `bull_case`/`bear_case`, `rationale`) is synthesis
over already-computed facts or natural-language interpretation of unstructured text — the two categories
`AF1_COMPUTATION_BOUNDARY_POLICY.md` reserves for Agent Firm.
