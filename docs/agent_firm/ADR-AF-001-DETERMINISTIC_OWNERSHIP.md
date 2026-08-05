# ADR-AF-001 — Deterministic Ownership (Resolves Blocker B1)

**Date:** 2026-07-29
**Status:** DECIDED. Permanent, per `AGENT_FIRM_GOVERNANCE.md`'s decision-record discipline — amended
only by a superseding, dated ADR, never a silent edit.
**Resolves:** `AF2_IMPLEMENTATION_READINESS.md` Blocker B1.

---

## Evidence From Code (verified this pass)

| Module | Function | What it computes | Verified behavior |
|---|---|---|---|
| `engine/regime_filter.py` | `detect_regime(df)` | Market-wide regime (BULL/BEAR/SIDEWAYS) from a price DataFrame | Canonical, single implementation |
| `engine/edge_enrich.py` | `market_regime(conn)` | Fetches IHSG OHLCV, calls `detect_regime()` | **Adapter, not a competing implementation** — no independent classification logic |
| `scheduler/scanner.py` | `_safe_regime(df)` | Calls `detect_regime()`, fail-soft to `'UNKNOWN'` | **Adapter, not a competing implementation** |
| `engine/technicals.py` | `tech_direction(closes, short=20, long=50)` | Directional label (BULLISH/BEARISH/NEUTRAL) from an MA(20)/MA(50) crossover rule it computes internally | Canonical, single implementation — verified by direct read of its body: `ma_s = sum(closes[-short:])/short`, `ma_l = sum(closes[-long:])/long`, then a fixed comparison rule |
| `engine/edge_enrich.py` | `enrich_candidate()` | Calls `tech_direction(closes)`, packages the result alongside flow/wf-edge/catalyst fields | **Consumer, not a competing implementation** |
| `engine/catalyst.py` | `has_catalyst(conn, ticker, date)` | Deterministic boolean: does a dated catalyst exist for this ticker | Canonical, single implementation |
| `engine/indicators.py` | `calc_sma`, `calc_adx`, `calc_atr`, etc. | Individual indicator *values* (not a directional classification) | Canonical for indicator values — a different concern from `tech_direction()`'s classification |
| `engine/chart_indicators.py` | `support_resistance`, `detect_patterns` | Price-level and pattern facts | Canonical, no competing implementation found anywhere in the codebase |

**Prior-pass finding this ADR corrects:** `AF1_REQUIRED_CONTEXT_OBJECTS.md`'s `RegimeContext.regime_call`
was specified as a *new* pure function implementing thresholds copied from the LLM prompt's own prose
(`consistency_pct >= 55%` etc.) — an independent, third definition of "regime," never checked against
`detect_regime()`. This ADR closes that gap by making `detect_regime()`'s output the *only* value the
word "regime" refers to in Agent Firm's context — everything else becomes a differently-named,
per-ticker confirmation signal.

---

## Decision

### Regime

**Canonical producer: `engine/regime_filter.py::detect_regime()`.** `RegimeContext.regime_call` is a
**direct passthrough** of this function's output (via the existing adapters, `market_regime()`/
`_safe_regime()`) — never independently re-derived. The per-ticker facts previously folded into
`regime_call`'s definition (`wf_scores.consistency_pct`, `daily_screen` signals) become their own,
separately-named fields — `ticker_consistency_pct`, `sector_tailwind`, `macro_risk` — whose job is to
**confirm or challenge** the canonical `regime_call`, matching the Regime agent's own already-stated task
description ("confirm or challenge the quant pipeline's regime reading"), now finally grounded correctly:
the agent reasons about whether per-ticker evidence agrees with the one canonical market regime, rather
than computing a second, competing regime itself.

### Technical Direction

**Canonical producer, for the mechanical directional label: `engine/technicals.py::tech_direction()`.**
`TechnicalContext` gains a passthrough field, `mechanical_direction: Literal["BULLISH","BEARISH","NEUTRAL"]`,
populated by calling `tech_direction()` directly — not re-derived from a separate MA crossover
computation. `TechnicalContext`'s richer fields (`sma20`, `sma50`, `adx`, `atr`, `support_levels`,
`resistance_levels`, `pattern_flags` — from `engine/indicators.py`/`engine/chart_indicators.py`, unchanged
from the original design) are **not** a second directional classifier — they are supplementary grounding
facts for the Technical agent's own synthesis (`verdict`), which may legitimately differ from
`mechanical_direction` because it reasons over strictly more information (pattern flags, S/R proximity,
ADX trend strength) than the mechanical rule sees. This is the Computation Boundary Policy's own
distinction in practice: duplicating a classification with no new input is prohibited; synthesizing a
richer verdict from a mechanical fact plus additional grounded context is exactly what the multi-agent
design exists to do.

### Catalyst Status

**Canonical producer: `engine/catalyst.py::has_catalyst()`.** `NewsContext` gains a passthrough field,
`has_catalyst: bool`. The News agent's own LLM output field is **renamed from `catalyst` to
`catalyst_sentiment`** — this was a naming collision, not a computation duplication (`has_catalyst()`
answers "does a dated catalyst exist"; the News agent's field answers "is recent news bullish/bearish" —
a directional NLU read over headline text, not a presence check) — but the collision risked exactly the
kind of silent-disagreement confusion B1 was raised to prevent, so it is resolved by disambiguating the
name, not by removing either field.

---

## Consumers-Only (confirmed, no change required)

`engine/edge_enrich.py::enrich_candidate()`, `engine/edge_enrich.py::market_regime()`,
`scheduler/scanner.py::_safe_regime()` — all three call into the canonical producers above and package
results; none contain independent classification logic. No change is required to any of these three —
this ADR's implementation changes are scoped entirely to Agent Firm's context objects (below).

---

## Required Documentation Updates

- `AF1_CONTEXT_OBJECT_CATALOG.md` — `TechnicalContext` row gains `mechanical_direction`; `RegimeContext`
  row's `regime_call` field description changes from "computed by fixed rule" to "passthrough of
  `detect_regime()`"; `RegimeContext.consistency_pct` renamed `ticker_consistency_pct` to disambiguate
  from any market-level concept; `NewsContext` gains `has_catalyst`.
- `AF1_PROMPT_CONTEXT_MAPPING.md` — `regime_v1.md`'s replacement-fields entry updated to reflect the
  passthrough (not computed) nature of `regime_call`; `news_v1.md`'s output schema entry updated for the
  `catalyst` → `catalyst_sentiment` rename (this is the one prompt in that document's "no change
  required" list that now requires a one-field rename — corrected here).
- `AF2_IMPLEMENTATION_READINESS.md` Part 2 (Blocker B1) — marked resolved, referencing this ADR.

## Required Implementation Changes (for AF-2, not performed by this ADR)

- `TechnicalContext`'s assembly function calls `engine/technicals.py::tech_direction()` in addition to
  `engine/indicators.py`/`engine/chart_indicators.py`'s existing functions.
- `RegimeContext`'s assembly function calls `engine/regime_filter.py::detect_regime()` (via the existing
  `market_regime()`/`_safe_regime()` adapters, not a new independent call) for `regime_call`, and computes
  `ticker_consistency_pct`/`sector_tailwind`/`macro_risk` as before, renamed per the field-name change
  above.
- `NewsContext`'s assembly function calls `engine/catalyst.py::has_catalyst()`.
- `prompts/news_v1.md`'s output schema: `catalyst` → `catalyst_sentiment`.
- Two regression tests (already specified in `AF2_TEST_STRATEGY.md` WP1/WP3) asserting Agent Firm's
  `mechanical_direction`/`regime_call` agree with `engine/veto.py`'s own reads of the same underlying
  functions for the same ticker/date — now trivially true by construction (same function, same call),
  but retained as a regression guard against future drift if either call site is ever edited
  independently.
