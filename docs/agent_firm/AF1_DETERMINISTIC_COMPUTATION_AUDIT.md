# AF-1 — Deterministic Computation Audit

**Date:** 2026-07-29
**Status:** COMPLETE. Basis for `AF1_COMPUTATION_BOUNDARY_POLICY.md`.
**Scope note — how this relates to the existing AF-1 corpus:** the six documents dated 2026-07-28
(`AGENT_FIRM_ARCHITECTURE.md` through `AF1_IMPLEMENTATION_SPEC.md`) resolved the **access boundary** —
who queries what, who owns which schema, which process/runtime concerns belong to which side. That
work is final; nothing below reopens it. This document audits a different, previously unexamined
boundary: the **computation boundary** — for every value an LLM is asked to produce, whether producing
it requires reasoning (an LLM's actual value-add) or deterministic computation (arithmetic, indicator
math, threshold comparison, lookup) that should be code. `AF1_CONTEXT_API.md` fixed *where the query
executes*; this document is about *what shape the answer takes* once it arrives at the prompt —
`AF1_CONTEXT_API.md`'s own `RecentHistory` type is currently specified as raw row lists (verified
below), which is exactly the gap this audit closes.
**Method:** every finding below is verified by direct reading of the prompt file, the agent module that
calls it, `firm.py`'s context assembly, and (where relevant) the Production Engine module that already
computes the equivalent value. Nothing here is inferred from naming.

---

## Classification Key

| Category | Meaning |
|---|---|
| Arithmetic | Sum, mean, ratio, or other numeric aggregation over structured rows |
| Technical Indicator | Moving averages, ATR, support/resistance, volume profile, pattern detection |
| Statistical Calculation | Win rate, Sharpe, distribution stats |
| Risk Calculation | Anything feeding a real risk/exposure decision |
| Position Sizing | A multiplier or quantity that changes real (paper) capital allocation |
| Threshold Evaluation | A comparison against a fixed numeric constant stated as a rule |
| Lookup Table | A discrete mapping from a condition to a value, expressible as `if/elif` |
| Aggregation | Counting/grouping categorical values across multiple inputs |
| Classification | A categorical judgment synthesized from already-known facts |
| Reasoning | Weighing evidence, constructing an argument, calibrating uncertainty |
| Narrative | Human-readable explanation of a conclusion already reached |
| Explanation | Same as Narrative — kept as a distinct row only where a prompt asks for it separately |

---

## Full Inventory

### Technical Analyst (`prompts/technical_v1.md`, `agents/technical.py`)

Input today: `ohlcv_recent_60d` — 60 raw daily bars, nothing else (`technical.py:28-37`). No indicator
values, no S/R levels, are ever computed before the prompt runs.

| # | Value | Category | Currently produced by | Should be produced by | Evidence |
|---|---|---|---|---|---|
| T1 | `key_levels.support`/`resistance` | Technical Indicator | LLM, eyeballing 60 raw bars | Production Engine | `engine/chart_indicators.py::support_resistance(df, lookback=5, max_levels=6)` already exists and computes this exact value — never called on this path |
| T2 | "price above key MAs" input to `verdict`/`conviction` | Technical Indicator | LLM, inferring MA position from raw closes (no MA values given) | Production Engine | `engine/indicators.py::calc_sma/calc_close_vs_ma/calc_ma_slope/calc_adx` already exist, unused here |
| T3 | `verdict` (BULLISH/NEUTRAL/BEARISH) | Classification | LLM | **Agent Firm — correct owner, wrong inputs** | Legitimate synthesis task; currently miscategorized as a violation only because its inputs (T1, T2) are raw instead of derived |
| T4 | `conviction` (0.0-1.0, banded to conditions like "volume support", "no divergence") | Threshold Evaluation + calibration | LLM | Split — bands should ground in computed facts; the confidence expression itself may stay LLM | `technical_v1.md:18-21` |

### Flow Specialist (`prompts/flow_v1.md`, `agents/flow.py`)

Input today: raw `stockbit_flow_14d`, `broker_flow_14d`, `stockbit_flow_bars_7d` rows (`flow.py:27-32`).

| # | Value | Category | Currently produced by | Should be produced by | Evidence |
|---|---|---|---|---|---|
| F1 | `flow_verdict` (ACCUMULATING/DISTRIBUTING/NEUTRAL) | Classification — **duplication** | LLM, re-derived from raw rows | Production Engine — **already computed** | `flow_filter.py:219` computes an equivalent `verdict` (BULLISH/BEARISH/NEUTRAL) from the same 14-day window and persists it as `stockbit_flow.verdict` — a column already present in the exact payload handed to this prompt (`firm.py:115`, field `verdict`). The LLM is asked to recompute a value sitting unused in its own input. |
| F2 | `smart_money_signal` (STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL) | Classification — **duplication** | LLM | Production Engine — **already computed** | `flow_filter.py:169-199` computes `smart_money` (STRONG_BUY/STRONG_SELL/ACCUMULATION/MORNING_TRAP/NEUTRAL), persisted in `stockbit_flow.smart_money`, same payload |
| F3 | `net_foreign_14d` | Arithmetic | LLM, instructed to manually sum `net_lot` over rows | Production Engine | `flow_v1.md:24`: "sum of net_lot values from broker_flow rows where investor_type='Asing'" — a one-line `SUM()`/`sum()` |

### Regime Analyst (`prompts/regime_v1.md`, `agents/regime.py`)

Input today: raw `wf_scores`, `sector_data_10d` (last 10 `daily_screen` rows) (`regime.py:23-27`).

| # | Value | Category | Currently produced by | Should be produced by | Evidence |
|---|---|---|---|---|---|
| R1 | `regime_call` (BULL/BEAR/SIDEWAYS/VOLATILE/UNKNOWN) | Threshold Evaluation | LLM, applying prose thresholds by hand | Production Engine | `regime_v1.md:20-24` states the rule as literal numeric thresholds: `consistency_pct >= 55%`, `vol_ratio > 3.0` — this is `if/elif`, written in English |
| R2 | `sector_tailwind` (bool) | Threshold Evaluation | LLM | Production Engine | `regime_v1.md:25`: "true if the ticker's best strategy shows avg_sharpe > 0.8" — a single boolean comparison |
| R3 | `macro_risk` (LOW/MEDIUM/HIGH) | Threshold Evaluation / co-occurrence rule | LLM | Production Engine | `regime_v1.md:26`: "HIGH if vol_ratio spikes coincide with negative signal labels" — a computable correlation check over the same 10 rows already in context |

### News/Sentiment Analyst (`prompts/news_v1.md`, `agents/news.py`) — **no finding**

| # | Value | Category | Assessment |
|---|---|---|---|
| N1 | `sentiment`, `catalyst`, `key_headline`, `summary` | Classification / Reasoning | Genuinely NLU-dependent — headline text and web-search snippets are unstructured; interpreting them is exactly what an LLM is for. No raw-vs-derived confusion exists here because there is no deterministic computation being bypassed. **Cite as the pattern the other agents should resemble.** |

### Bull / Bear Researchers (`prompts/bull_v1.md`, `bear_v1.md`) — **no finding**

| # | Value | Category | Assessment |
|---|---|---|---|
| B1 | `bull_case`/`key_strength`, `bear_case`/`key_risk` | Narrative / Reasoning | Pure argumentative synthesis over already-produced analyst outputs. Correctly scoped; no computation is being asked of either agent. |

### Risk Manager (`prompts/risk_v2.md`, `agents/risk.py`, `guardrails.py`)

Input today: candidate + all 6 upstream `AgentResult`s, raw, as a JSON dump (`risk.py:31-37`).

| # | Value | Category | Currently produced by | Should be produced by | Evidence |
|---|---|---|---|---|---|
| K1 | `decision`'s "≥3 of 4 analysts negative" rule | Aggregation / Threshold | LLM, counting categorical fields across 4 outputs | Production Engine | `risk_v2.md:23` |
| K2 | "Veto if ticker already has an open paper trade" | Lookup Table (deterministic gate) | LLM, trusted to check `open_trades` in context and comply with a prose instruction | Production Engine | `risk_v2.md:26`. **Highest real-world risk of any finding not already flagged**: a prompt-compliance failure here directly doubles up a live position, not merely mislabels a narrative. |
| K3 | `size_hint` (0.0-1.5, explicit numeric lookup table) | Position Sizing / Lookup Table | LLM | Production Engine | `risk_v2.md:16,28-30` gives literal `if/elif` bands (0.5 / 1.0 / 1.2). Flows unmodified into `paper_trade.py:413`'s `lots_multiplier` — i.e., a real (paper) capital-allocation input. `schemas.py:50` (`size_hint: Optional[float] = None`) enforces no bound despite every prompt version declaring the contract as `0.0-1.5`. Mitigated only by `paper_trade.py:410,426`'s downstream `max_lots`/aggregate-exposure caps, which bound blast radius but do not validate the value itself. **Flagship finding.** |
| K4 | `confidence` bands ("clear consensus across all analysts" etc.) | Threshold Evaluation dressed as calibration | LLM | Split — same counting problem as K1 | `risk_v2.md:36-39` |
| K5 | `quant_score` normalization | Arithmetic | **Production Engine — already correct** | — | `guardrails.py:71-75::normalize_quant`, computed in Python, injected pre-formatted into the prompt (`risk.py:30`). **Cite as the template to replicate for K1-K3.** |
| K6 | Guardrail overrides (bearish-flow-not-offset, confidence-floor-in-weak-regime) | Threshold Evaluation | **Production Engine — already correct** | — | `guardrails.py:39-68::apply_guardrails`, deterministic, post-LLM, downgrade-only. **Cite as the template**, but note it currently covers only 2 of the prompt's several deterministic rules — K1, K2, and K3 are not yet guarded. |

### Orchestrator / Context Builder (`firm.py::_build_context`)

| # | Finding | Evidence |
|---|---|---|
| O1 | Root cause for T1, T2, F1-F3, R1-R3: `_build_context()` (`firm.py:81-144`) runs 7 raw SQL queries and hands rows straight into every prompt with zero derivation step in between. | Verified by direct read — no aggregation, no indicator computation, no threshold pre-check anywhere in this function. |
| O2 | `AF1_CONTEXT_API.md` (2026-07-28) already schedules `_build_context()` for replacement by six typed objects, but as specified, `RecentHistory` still carries `ohlcv: list[OhlcvBar]`, `stockbit_flow: list[StockbitFlowRow]`, `broker_flow: list[BrokerFlowRow]`, `strategy_edge: list[WfScoreRow]`, `recent_screen_signals: list[ScreenRow]` — typed, but still raw (`AF1_CONTEXT_API.md:38-49`). That design closes the access boundary (who runs the query) without closing the computation boundary (what shape the answer takes). This audit's Part 3 (`AF1_REQUIRED_CONTEXT_OBJECTS.md`) is written as an amendment to that document, not a competing design. |

### Schema-Level Findings

| # | Finding | Evidence |
|---|---|---|
| S1 | `SignalCandidate.indicators: dict[str, Any] = {}` already exists as an optional, versioned (MINOR-safe per `AGENT_FIRM_GOVERNANCE.md`) extension point for exactly this purpose, but is populated only in `smoke.py:36` (a demo script). Both real production call sites hardcode it empty. | `scheduler/scanner.py:1000`, `scheduler/scanner.py:1092` both read `indicators={}` |
| S2 | `AgentDecision.size_hint: Optional[float] = None` has no `ge`/`le` bound despite every prompt version declaring the contract as `0.0-1.5`. | `schemas.py:50` |

### Tools — out of this review's scope, already resolved elsewhere

| # | Finding | Disposition |
|---|---|---|
| X1 | `tools/sqlite_query.py`'s free-form SQL capability | Already decided **REPLACE** in `AF1_IMPLEMENTATION_SPEC.md` Decision B (AF-4 scope) — a data-access-boundary concern, not a computation-boundary one. Not re-litigated here. |
| X2 | `tools/news_lookup.py`, `tools/web_search.py` | Clean — pure structured/external reads, no computation asked of the LLM in either. |

### Analytics — correctly-scoped existing example

| # | Finding | Disposition |
|---|---|---|
| A1 | `analytics.py::cohort_summary/_stats/agent_agreement` (win rate, Sharpe, cohort comparison) | Statistical Calculation, correctly implemented as pure Python/SQL post-hoc analytics — never in a prompt, never on the decision path. Proof the codebase already knows how to own this category correctly; extend this pattern rather than inventing a new one. |

---

## Summary

| Area | Violations found | Clean |
|---|---|---|
| Technical Analyst | 2 (T1, T2) — indicator/S-R math done by LLM from raw bars | `verdict` classification itself is fine once grounded |
| Flow Specialist | 3 (F1, F2, F3) — 2 of which are outright duplication of an already-computed, already-in-payload value | — |
| Regime Analyst | 3 (R1, R2, R3) — all three are prose-encoded `if/elif` | — |
| News/Sentiment | 0 | Fully clean — the model for the other agents |
| Bull/Bear | 0 | Fully clean |
| Risk Manager | 3 primary (K1, K2, K3) + 1 secondary (K4) | K5, K6 are the existing correct pattern |
| Orchestrator | 1 root cause (O1) covering 8 of the above findings | — |
| Schema | 2 gaps (S1 unused extension point, S2 missing bound) | — |

**Verdict on the user's framing question:** yes — these are symptoms of one architectural flaw, not
isolated bugs. Every violation above traces back to the same root cause (O1): `_build_context()` hands
every analyst raw database rows and lets the prompt's English prose serve as the specification for
computations that belong in code. The fix is not seven separate patches; it is one category of fix
(derive-before-prompting) applied at the one wiring point, which `AF1_CONTEXT_API.md`'s already-planned
replacement of `_build_context()` is the natural place to carry it — see
`AF1_REQUIRED_CONTEXT_OBJECTS.md`.
