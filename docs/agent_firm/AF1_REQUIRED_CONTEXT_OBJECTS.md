# AF-1 — Required Context Objects

**Date:** 2026-07-29
**Basis:** `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`, `AF1_COMPUTATION_BOUNDARY_POLICY.md`.
**Relationship to `AF1_CONTEXT_API.md`:** that document defines six typed objects
(`MarketContext`, `Opportunity`, `RecentHistory`, `PortfolioState`, `RiskLimits`, `SessionState`) that
replace `_build_context()`'s raw SQL with typed data, and states explicitly: "this design does not
invent new data sources, it types and relocates existing ones." This document is the amendment that
was implicitly out of that scope: for the five fields below, typing and relocating the *raw* row isn't
enough — per the Computation Boundary Policy, the prompt must receive the *derived* fact, not the rows
it would otherwise have to derive that fact from itself. Every object below is designed to nest inside
`AF1_CONTEXT_API.md`'s existing `RecentHistory` type (or, for one case, the pre-existing
`SignalCandidate.indicators` field) — none of them require a new top-level context type or touch the
six-type structure, `MarketContext`, `PortfolioState`, `SessionState`, or the interface's stable shape.

---

## 1. Instead of raw OHLCV, provide `TrendContext`

**Instead of:** `ohlcv_recent_60d` — 60 raw daily bars handed to the Technical Analyst with no computed
indicator values (Audit T1, T2).

**Provide:** `TrendContext`

```
sma20: float | None
sma50: float | None
close_vs_sma50_pct: float          # calc_close_vs_ma
ma_slope_20: float                 # calc_ma_slope
adx: float                         # calc_adx
atr: float                         # calc_atr
vol_ratio: float                   # calc_vol_ratio
support_levels: list[float]        # chart_indicators.support_resistance()
resistance_levels: list[float]     # chart_indicators.support_resistance()
pattern_flags: list[str]           # chart_indicators.detect_patterns()
ohlcv_recent_10d: list[OhlcvBar]   # kept — small window, for qualitative "does this look right" color
```

**Producer:** `engine/indicators.py` (`calc_sma`, `calc_close_vs_ma`, `calc_ma_slope`, `calc_adx`,
`calc_atr`, `calc_vol_ratio`) + `engine/chart_indicators.py` (`support_resistance`, `detect_patterns`)
— all already exist, already tested, currently unused by this path. No new indicator math is invented;
this object is a call to functions the repository already has.

**Transport:** either (a) nest inside `RecentHistory` as `RecentHistory.trend_context`, replacing the
full `ohlcv: list[OhlcvBar]` field with the 10-day window plus this derived block, or (b) populate the
already-existing, already-optional `SignalCandidate.indicators: dict[str, Any]` field (`schemas.py:23`)
— which is the lower-friction path since it requires no change to `AF1_CONTEXT_API.md`'s type
definitions at all, only wiring the two real call sites (`scanner.py:1000,1092`) that currently hardcode
`indicators={}` to actually populate it. Recommend (b) for the first migration pass; (a) if/when
`AF1_CONTEXT_API.md`'s six-type bundle is actually implemented in AF-2's step 6.

**Prompt change:** `technical_v1.md` stops asking the model to infer MA position from raw closes; it
receives `sma20`/`sma50`/`close_vs_sma50_pct` directly and is asked to synthesize a verdict from them —
a strictly smaller, more grounded prompt.

---

## 2. Instead of raw flow tables, provide `FlowSummary`

**Instead of:** raw `stockbit_flow_14d`, `broker_flow_14d` rows, with the LLM asked to re-derive
`flow_verdict`, `smart_money_signal`, and `net_foreign_14d` from them (Audit F1, F2, F3) — despite
`verdict`/`smart_money` already being present, precomputed, in the same rows.

**Provide:** `FlowSummary`

```
verdict: str                 # passthrough of stockbit_flow.verdict — NOT recomputed
smart_money: str             # passthrough of stockbit_flow.smart_money — NOT recomputed
composite_score: int         # passthrough
foreign_score: float | None  # passthrough
net_foreign_14d: int         # SUM(net_lot) WHERE investor_type='Asing', computed once in SQL/Python
trend_7d: str                # "accumulating" | "distributing" | "flat" — deterministic sign-of-rolling-
                              # delta tag over the 7d intraday bars, not LLM-derived
flow_bars_recent: list[FlowBar]  # small recent window kept for qualitative color
```

**Producer:** `flow_filter.py`'s existing computation (already runs upstream of every evaluation, since
`stockbit_flow.verdict`/`.smart_money` are already populated before the Flow agent ever runs) — this
object requires no new computation for `verdict`/`smart_money`/`composite_score`/`foreign_score`, only a
thin read plus one new `SUM()` for `net_foreign_14d` and one small new rolling-sign function for
`trend_7d`.

**Transport:** `RecentHistory.flow_summary`, replacing the raw `stockbit_flow`/`broker_flow` fields (or
supplementing them with `flow_bars_recent`'s small window for color, per the pattern above).

**Prompt change:** `flow_v1.md` drops `flow_verdict`/`smart_money_signal`/`net_foreign_14d` as
LLM-derived outputs entirely — they become passthrough fields the orchestrator attaches to the analyst's
`AgentResult` directly, no LLM call needed to reproduce them. The Flow agent's remaining job — genuine
reasoning — is producing `reasoning` text that narrates the already-computed verdict, and any qualitative
color the raw `flow_bars_recent` window supports. **Downstream note:** `analytics.py::_is_aligned`
(line 109) currently checks `output.get("flow_verdict") == "ACCUMULATING"` — this hardcoded string check
must be updated in lockstep if the taxonomy changes to match `flow_filter.py`'s own
`BULLISH`/`BEARISH`/`NEUTRAL` vocabulary (see `AF1_REMEDIATION_PLAN.md` WP2).

---

## 3. Instead of raw wf_scores/screen rows, provide `RegimeAssessment`

**Instead of:** raw `wf_scores`, `sector_data_10d` rows plus a prose threshold table (Audit R1, R2, R3).

**Provide:** `RegimeAssessment`

```
regime_call: Literal["BULL","BEAR","SIDEWAYS","VOLATILE","UNKNOWN"]  # computed by fixed rule
sector_tailwind: bool                  # avg_sharpe > 0.8, computed
macro_risk: Literal["LOW","MEDIUM","HIGH"]  # computed co-occurrence rule
best_strategy: str | None
consistency_pct: float | None
```

**Producer:** a new small, pure function — e.g. `engine/agent_firm/regime_rules.py::assess_regime()` —
implementing exactly the three thresholds currently stated as prose in `regime_v1.md:20-26`
(`consistency_pct >= 55`, `vol_ratio > 3.0`, `avg_sharpe > 0.8`, plus the co-occurrence check for
`macro_risk`). Nothing here requires a new data source; every input is already queried by
`firm.py:128-139`.

**Transport:** `RecentHistory.regime_assessment`, replacing the raw `wf_scores`/`sector_data` fields (or
supplementing them with a small recent window if the agent should retain qualitative color from the raw
signal labels).

**Prompt change:** `regime_v1.md`'s three threshold rules are deleted from the prompt text entirely and
replaced by code. The prompt keeps only the genuinely interpretive part of the Regime Analyst's job —
contextualizing *why* a regime call matters for this trade, drawing on sector/macro narrative that isn't
reducible to the three thresholds — not recomputing the call itself.

---

## 4. Instead of raw analyst dicts + prose counting rule, provide `ConsensusSummary`

**Instead of:** four raw analyst-output dicts handed to the Risk prompt with an English instruction to
count how many are "clearly negative" (Audit K1), plus a separate prose instruction to check
`open_trades` for a dedup veto (Audit K2).

**Provide:** `ConsensusSummary`

```
negative_count: int          # count of {technical,flow,regime,news} verdicts classified negative
positive_count: int
aligned_bullish: int          # for confidence-banding, replaces "clear consensus across all analysts"
already_open_position: bool   # replaces "veto if ticker already has an open paper trade"
entries_blocked: bool         # RiskLimits.entries_blocked, per AF1_CONTEXT_API.md's RiskLimits type
```

**Producer:** a pure function over the four upstream `AgentResult`s and `PortfolioState`/`RiskLimits` —
e.g. `guardrails.py::build_consensus_summary()`, living in the same file and following the same
"pure/data-only, unit-testable without the LLM" discipline the module's own docstring already states as
its design principle (`guardrails.py:1-14`).

**Transport:** not a Context API input (it depends on analyst outputs that don't exist until after the
analyst nodes run) — assembled inside `firm.py::_run_risk`, between the analyst/bull/bear nodes and the
Risk agent call, exactly where `normalize_quant` is already invoked today (`risk.py:30`).

**Prompt change:** `risk_v2.md`'s "≥3 of 4 negative" and "already has an open paper trade" rules are
deleted from the prompt text; `negative_count`/`already_open_position`/`entries_blocked` are supplied
directly, and (per `AF1_REMEDIATION_PLAN.md` WP4) `already_open_position` and `entries_blocked` become
hard guardrail vetoes in `apply_guardrails`, not prompt-compliance-dependent LLM decisions — closing
`AF1_FAILURE_CONTRACT.md` §6's already-named `RiskLimits.entries_blocked` gap using the exact mechanism
that document already pointed at ("this is exactly where `AF1_CONTEXT_API.md`'s new
`RiskLimits.entries_blocked` check belongs").

---

## 5. Instead of an LLM-picked size_hint, provide `SizingInput` → `SizingResult`

**Instead of:** an LLM choosing a numeric `size_hint` from a prose lookup table (Audit K3) that then
flows unmodified into real position sizing.

**Provide two objects, one in each direction:**

`SizingInput` (LLM output — qualitative only):
```
size_tier: Literal["reduce","normal","increase"]
```

`SizingResult` (Production Engine output — the actual multiplier):
```
size_hint: float   # 0.0-1.5, computed, bounded by construction
```

**Producer:** `guardrails.py::resolve_size_hint(tier: str, consensus: ConsensusSummary, quant_score:
float) -> float` — a new pure function replacing `risk_v2.md:28-30`'s prose table with code. Bounded
(`0.0 <= x <= 1.5`) and unit-testable without any LLM call, the same testability property
`apply_guardrails` already has and that `guardrails.py`'s own docstring names as the reason the module is
"pure/data-only."

**Transport:** the Risk agent's LLM call returns `size_tier` instead of `size_hint`; `_run_risk` calls
`resolve_size_hint()` immediately after, and only the resolved, bounded value is ever written to
`AgentDecision.size_hint` or reaches `paper_trade.py`'s `lots_multiplier`.

**Prompt change:** `risk_v2.md`'s numeric size_hint table is removed entirely and replaced with a
three-way qualitative choice — the LLM's genuine signal ("this setup feels thinner than the quant score
alone suggests") is preserved, but the arithmetic that turns that signal into a capital-affecting number
never touches the model.

---

## Summary — Mapping to `AF1_CONTEXT_API.md`'s Six Types

| New object | Nests inside | Replaces |
|---|---|---|
| `TrendContext` | `SignalCandidate.indicators` (existing field) or `RecentHistory` | `ohlcv_recent_60d` full history |
| `FlowSummary` | `RecentHistory` | raw `stockbit_flow`/`broker_flow` |
| `RegimeAssessment` | `RecentHistory` | raw `wf_scores`/`sector_data` |
| `ConsensusSummary` | Not a Context API input — assembled in `firm.py::_run_risk` | prose counting/dedup rules |
| `SizingInput`/`SizingResult` | `SizingInput` replaces part of the Risk agent's output schema; `SizingResult` replaces `AgentDecision.size_hint`'s LLM-sourced value | prose size_hint lookup table |

No new top-level context type is introduced. `MarketContext`, `PortfolioState`, `SessionState`, and the
"one bundled parameter vs. five" open item in `AF1_CONTEXT_API.md` are unaffected and remain exactly as
already decided.
