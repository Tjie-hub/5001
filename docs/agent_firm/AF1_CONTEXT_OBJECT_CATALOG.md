# AF-1 — Context Object Catalog (Field-Level)

**Date:** 2026-07-29
**Basis:** `AF1_CONTEXT_API_V2_SPEC.md`. This document is that spec's field-level detail — Part 3 of the
Context API redesign.
**Column definitions:**
- **Producer** — the Production Engine module/function that computes the value.
- **Consumer** — which agent(s) receive it.
- **Deterministic source** — the underlying table/computation the value traces back to.
- **Update frequency** — how often the value is recomputed.
- **Replaces prompt computation** — the specific Audit finding (from `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`)
  this field eliminates, or "—" if the field is new/unchanged and replaces nothing.

---

## MarketContext (Tier 1, per scan cycle)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `regime` | `str` | Quant scan pipeline | `RegimeContext` assembly, Risk agent | Existing quant regime classifier | Per scan cycle | — (unchanged from V1) |
| `ihsg_trend` | `TechnicalContext` (reused type) | `engine/indicators.py` + `engine/chart_indicators.py`, applied to IHSG's own OHLCV | `RegimeContext` assembly | Same indicator functions as per-ticker `TechnicalContext` | Per scan cycle | Closes a previously-undiscovered gap: IHSG bars were computed (`firm.py:94-98`) but delivered to no agent |
| `market_risk_score` | `float \| None` | Existing `/metrics` computation | Risk agent (via `ConsensusContext`/`RiskContext` assembly) | Already-computed for the Prometheus endpoint | Per scan cycle | — (V1 already named this gap; unresolved until now) |

## OpportunityContext (Tier 1, per candidate — renamed `SignalCandidate`)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `ticker`, `strategy`, `score`, `scan_time` | existing types | Quant scan pipeline | All agents | Unchanged | Per candidate | — |
| `regime`, `flow_verdict`, `foreign_score` | existing types | Quant scan pipeline | All agents | Unchanged | Per candidate | — |
| `indicators` | `TechnicalContext` (now typed, was opaque `dict[str, Any]`) | `engine/indicators.py`/`chart_indicators.py` | Technical agent | See `TechnicalContext` below | Per candidate | Closes the gap where `scanner.py:1000,1092` hardcode `indicators={}` at both real call sites |

## TechnicalContext (Tier 1, per candidate)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `sma20` | `float \| None` | `engine/indicators.py::calc_sma` | Technical agent | `ohlcv` table | Per candidate, daily | T2 |
| `sma50` | `float \| None` | `calc_sma` | Technical agent | `ohlcv` | Per candidate, daily | T2 |
| `close_vs_sma50_pct` | `float` | `calc_close_vs_ma` | Technical agent | `ohlcv` | Per candidate, daily | T2 |
| `ma_slope_20` | `float` | `calc_ma_slope` | Technical agent | `ohlcv` | Per candidate, daily | T2 |
| `adx` | `float` | `calc_adx` | Technical agent | `ohlcv` | Per candidate, daily | T2 |
| `atr` | `float` | `calc_atr` | Technical agent | `ohlcv` | Per candidate, daily | T2 (also informs conviction banding) |
| `vol_ratio` | `float` | `calc_vol_ratio` | Technical agent | `ohlcv` | Per candidate, daily | T2 |
| `support_levels` | `list[float]` | `engine/chart_indicators.py::support_resistance` | Technical agent | `ohlcv` | Per candidate, daily | T1 |
| `resistance_levels` | `list[float]` | `support_resistance` | Technical agent | `ohlcv` | Per candidate, daily | T1 |
| `pattern_flags` | `list[str]` | `chart_indicators.py::detect_patterns` | Technical agent | `ohlcv` | Per candidate, daily | — (new — was never computed for this path) |
| `ohlcv_recent_10d` | `list[OhlcvBar]` | Existing `ohlcv` query, trimmed | Technical agent | `ohlcv` | Per candidate, daily | Kept — qualitative color only, not the full 60-bar history the LLM previously had to derive everything from |

**Reuse note:** this exact type, applied to IHSG's own OHLCV, is `MarketContext.ihsg_trend`. One
producer function set, two consumers.

## FlowContext (Tier 1, per candidate)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `verdict` | `str` | `flow_filter.py` (existing) | Flow agent | `stockbit_flow.verdict` | Per candidate, daily | F1 |
| `smart_money` | `str` | `flow_filter.py` (existing) | Flow agent | `stockbit_flow.smart_money` | Per candidate, daily | F2 |
| `composite_score` | `int` | `flow_filter.py` (existing) | Flow agent | `stockbit_flow.composite_score` | Per candidate, daily | — (already passthrough today, unchanged) |
| `foreign_score` | `float \| None` | `flow_filter.py` (existing) | Flow agent | `stockbit_flow.foreign_score` | Per candidate, daily | — (already passthrough today, unchanged) |
| `net_foreign_14d` | `int` | New: `SUM(net_lot) WHERE investor_type='Asing'` | Flow agent | `broker_flow` | Per candidate, daily | F3 |
| `trend_7d` | `Literal["accumulating","distributing","flat"]` | New: rolling-sign function over `stockbit_flow_bars` | Flow agent | `stockbit_flow_bars` | Per candidate, intraday | — (new — gives the agent a deterministic early-divergence signal instead of raw bars) |
| `flow_bars_recent` | `list[FlowBar]` | Existing `stockbit_flow_bars` query, trimmed | Flow agent | `stockbit_flow_bars` | Per candidate, intraday | Kept — qualitative color window, not the full derivation task |

## RegimeContext (Tier 1, per candidate)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `regime_call` | `Literal["BULL","BEAR","SIDEWAYS","VOLATILE","UNKNOWN"]` | New pure function (`regime_rules.py` or `guardrails.py`) | Regime agent | `wf_scores`, `daily_screen` | Per candidate, per evaluation | R1 |
| `sector_tailwind` | `bool` | Same new function | Regime agent | `wf_scores.avg_sharpe` | Per candidate, per evaluation | R2 |
| `macro_risk` | `Literal["LOW","MEDIUM","HIGH"]` | Same new function | Regime agent | `daily_screen.vol_ratio`/`signal` | Per candidate, per evaluation | R3 |
| `best_strategy` | `str \| None` | Same new function | Regime agent | `wf_scores`, ordered by `weighted_score` | Per candidate, per evaluation | — (new — surfaces which strategy the call is based on) |
| `consistency_pct` | `float \| None` | Same new function | Regime agent | `wf_scores.consistency_pct` | Per candidate, per evaluation | — (grounding detail for R1) |
| `recent_screen_signals` | `list[ScreenRow]` (10d, small window) | Existing `daily_screen` query, trimmed | Regime agent | `daily_screen` | Per candidate, per evaluation | Kept — qualitative color only |

## NewsContext (Tier 1, per candidate)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `mentions_7d` | `list[NewsMention]` | `tools/news_lookup.py` (existing, unchanged) | News agent | `news_mentions` | Per candidate, per evaluation | — (already clean — Audit N1) |
| `mentions_count_7d` | `int` | New trivial `len()`/`COUNT()` | News agent | `news_mentions` | Per candidate, per evaluation | — (new, minor convenience, not a violation fix) |
| `web_search_results` | `list[SearchResult]` | `tools/web_search.py` (existing, unchanged) | News agent | Tavily API | Per candidate, per evaluation, live | — (already clean) |

## PortfolioContext (Tier 1, account-wide, per scan cycle)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `open_trades` | `list[OpenTrade]` | Existing `paper_trades` query | `ConsensusContext` assembly | `paper_trades` | Per scan cycle | — (was already computed; the gap being closed is delivery, not computation) |
| `has_open_position_for_ticker` | `bool` (evaluated per-candidate at lookup time) | New: membership check over `open_trades` | `ConsensusContext` assembly | `paper_trades` | Per candidate, cheap lookup against the per-cycle cache | K2 — **and fixes the pre-existing wiring bug**: `open_trades` was computed but never reached `risk.run()` at all (verified: `agents/risk.py::run()`'s signature has no `context` parameter; `firm.py::_run_risk` never passes one) |
| `open_position_count` | `int` | New: `len(open_trades)` | `ConsensusContext` assembly, narrative color | `paper_trades` | Per scan cycle | — (new, supports narrative "how concentrated is the book" reasoning) |

## RiskContext (Tier 1, account-wide, per scan cycle — renamed `RiskLimits`)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `entries_blocked` | `bool` | `paper_trade.py::is_entries_blocked()` (existing) | `ConsensusContext` assembly, hard guardrail veto | Drawdown circuit breaker | Per scan cycle | — (V1-named gap, unresolved until WP4 lands) |
| `drawdown_pct` | `float \| None` | `paper_trade.py` (existing) | Risk agent narrative, guardrail | Same circuit breaker | Per scan cycle | — |
| `auth_mode` | `str` | `config.AUTH_MODE` (existing) | Risk agent audit trail (informational only) | Env config | Per scan cycle | — |

## ExecutionContext (Tier 1, account-wide, per scan cycle — new)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `capital` | `float` | `paper_trade.py`'s existing capital bookkeeping | `resolve_size_hint()` (Tier 3) | Account capital state | Per scan cycle | — (new) |
| `aggregate_open_exposure_pct` | `float` | New: `open_capital / capital` from `paper_trade.py:425` | `resolve_size_hint()` | `paper_trades` | Per scan cycle | — (new — closes the "sizing is blind to portfolio heat" gap found in Part 1 of the V2 spec) |
| `risk_pct_config` | `float` | Existing config value | `resolve_size_hint()` | Config | Per scan cycle | — (new, grounding detail) |
| `max_position_pct_config` | `float` | Existing constant (`paper_trade.py:410`'s 30% cap) | `resolve_size_hint()` | Config/constant | Per scan cycle | — (new, grounding detail) |

## SessionContext (Tier 1, per candidate — renamed `SessionState`)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `scan_time` | `str` | Existing, from `SignalCandidate.scan_time` | Any agent | Scan pipeline | Per candidate | — |
| `wib_session` | `Literal["premarket","regular","post-close"]` | New: derived from `scan_time` | Any agent that cares about timing | `scan_time` | Per candidate | — (V1-named, not yet implemented) |

## ConsensusContext (Tier 2 — assembled after analysts run, before Risk agent)

| Field | Type | Producer | Consumer | Deterministic source | Update frequency | Replaces |
|---|---|---|---|---|---|---|
| `negative_count` | `int` | New: `guardrails.py::build_consensus_summary()` | Risk agent, `apply_guardrails` | Technical/Flow/Regime/News `AgentResult`s | Per candidate, per evaluation | K1 |
| `positive_count` | `int` | Same function | Risk agent, `apply_guardrails` | Same | Per candidate, per evaluation | K1 |
| `aligned_bullish` | `int` | Same function | Risk agent confidence banding | Same | Per candidate, per evaluation | K4 (confidence-banding counting problem) |
| `already_open_position` | `bool` | Same function, sourced from `PortfolioContext.has_open_position_for_ticker` | `apply_guardrails` (hard veto) | `PortfolioContext` | Per candidate, per evaluation | K2 |
| `entries_blocked` | `bool` | Same function, sourced from `RiskContext.entries_blocked` | `apply_guardrails` (hard veto) | `RiskContext` | Per candidate, per evaluation | Closes `AF1_FAILURE_CONTRACT.md` §6's named gap |

---

## Tier 3 — Post-Decision Resolution (not an LLM input; documented for completeness)

| Function | Inputs | Output | Producer | Replaces |
|---|---|---|---|---|
| `resolve_size_hint()` | LLM's `size_tier` + `ConsensusContext` + `ExecutionContext` + `quant_score` | `size_hint: float`, bounded `[0.0, 1.5]` | New, in `guardrails.py` | K3 |

---

## Cross-Reference Index — Every Audit Finding's Resolution

| Audit finding | Resolved by |
|---|---|
| T1 (support/resistance from raw bars) | `TechnicalContext.support_levels`/`.resistance_levels` |
| T2 (MA position inferred from raw closes) | `TechnicalContext.sma20`/`.sma50`/`.close_vs_sma50_pct`/`.ma_slope_20` |
| F1 (`flow_verdict` duplication) | `FlowContext.verdict` |
| F2 (`smart_money_signal` duplication) | `FlowContext.smart_money` |
| F3 (`net_foreign_14d` LLM-computed sum) | `FlowContext.net_foreign_14d` |
| R1 (`regime_call` threshold) | `RegimeContext.regime_call` |
| R2 (`sector_tailwind` threshold) | `RegimeContext.sector_tailwind` |
| R3 (`macro_risk` threshold) | `RegimeContext.macro_risk` |
| K1 (≥3-negative count) | `ConsensusContext.negative_count`/`.positive_count` |
| K2 (open-position dedup) | `ConsensusContext.already_open_position`, sourced from `PortfolioContext` — plus the wiring fix |
| K3 (`size_hint` lookup table) | `resolve_size_hint()` (Tier 3), consuming `ConsensusContext` + `ExecutionContext` |
| K4 (confidence-band counting) | `ConsensusContext.aligned_bullish` |
| S1 (`indicators` unused extension point) | `OpportunityContext.indicators` now typed as `TechnicalContext`, actually wired at both call sites |
| S2 (`size_hint` missing bound) | `resolve_size_hint()`'s bounded-by-construction return, plus `AF1_REMEDIATION_PLAN.md` WP6's schema-level defense in depth |

Every finding in `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md` has exactly one resolving field or function
above. None are unresolved; none are resolved twice by conflicting mechanisms.
