# AF-2 WP3 — Prompt Simplification Report

Companion to `Audit/AF2_WP3_IMPLEMENTATION_REPORT.md`. Every prompt in `engine/agent_firm/prompts/`
that backs a Tier-1-context specialist was reviewed; `bull_v1.md`/`bear_v1.md` were reviewed and left
unchanged (they never asked for computation — see Implementation Report's "Bull/Bear/Guardrails"
section).

For each prompt below: what computation instruction was removed, and what interpretation instruction
replaced it. Output JSON schemas are unchanged in all five — verified by `git diff` scoped to each
prompt's fenced JSON block, and by every existing test that asserts on `result.output["<field>"]`
still passing unchanged.

## `technical_v1.md`

**Removed:** "Recent OHLCV data for the ticker (up to 60 daily bars)" as the sole input, with no
guidance distinguishing "read the facts" from "compute the facts" — the original prompt's only
guardrail against re-derivation was implicit.

**Added:** An explicit `technical_context` object (11 named fields) plus the sentence "These facts
are already computed — do not recompute moving averages, RSI, MACD, ATR, or support/resistance
levels yourself, and do not build a second directional classifier from ohlcv_recent_10d." Conviction
guidance now points at confirming/contradicting `mechanical_direction` using the supplied
`pattern_flags`/`adx`/`vol_ratio`, not deriving a fresh read from price bars. `key_levels` are now
explicitly sourced from `support_levels`/`resistance_levels`, not re-derived.

## `flow_v1.md`

**Removed:** `"net_foreign_14d: sum of net_lot values from broker_flow rows where
investor_type='Asing'"` — a literal aggregation instruction, i.e. asking the LLM to perform lot
summation.

**Added:** `flow_context` object naming `net_foreign_14d` as already summed, plus "These facts are
already computed. Do not re-sum lots, recompute net_foreign_14d, or re-derive trend_7d... yourself."
The output field `net_foreign_14d` is now explicitly a passthrough ("passed through unchanged").

## `regime_v1.md`

**Removed:** Four literal threshold rules that amounted to a second regime classifier written in
prompt prose: `"BULL: ... consistency >= 55%"`, `"VOLATILE: vpin_label is EXTREME... OR avg
vol_ratio > 3.0"`, `"SIDEWAYS: signal neutral across most bars"`, `"macro_risk HIGH: if vol_ratio
spikes coincide with negative signal labels"` — every one of these was already independently
implemented as real code in `engine.agent_firm_context.build_regime_context()` (WP1/WP2), making the
prompt version a duplicate, drift-prone definition of "regime" (exactly the risk `ADR-AF-001`
documents).

**Added:** `regime_context` object naming `regime_call`/`sector_tailwind`/`macro_risk` as already
computed, plus "Default to regime_context's own... values — treat them as the pipeline's canonical
reading, not a first draft for you to recompute" and "Only deviate... if recent_screen_signals
clearly contradicts them... say so explicitly." This converts the agent's job from *classification*
to *confirm-or-challenge*, matching what the original prompt's task description already claimed to
do ("confirm or challenge the quant pipeline's regime reading") but never actually implemented.

## `news_v1.md`

**Removed:** Nothing computational — the News prompt never asked for derivation of a deterministic
fact (sentiment/catalyst assessment is genuine NLU by design). The only change is input shape.

**Added:** `news_context` object naming `has_catalyst` as "a precomputed bool from the quant
pipeline's catalyst detector — a fact to weigh, not a call for you to re-derive," disambiguating it
from the model's own `catalyst` sentiment-direction output field (same fields, same names as before;
the disambiguation is in the guidance text, not a schema change — see Implementation Report's Known
Limitation #4 on the still-pending `catalyst`→`catalyst_sentiment` rename from `ADR-AF-001`).

## `risk_v2.md`

**Removed:** Nothing computational was present to remove (the Risk Manager already only synthesized
analyst outputs) — but the prompt's own claim ("You will receive: ... Current open paper trades")
was previously undeliverable (see Implementation Report). The instruction "Veto if ticker already
has an open paper trade" existed with no data behind it.

**Added:** `portfolio_context`/`risk_context` objects, both stated as "already-computed facts. Do not
calculate volatility, exposure, position sizing, leverage, or drawdown yourself — weigh these facts
qualitatively." The veto rule now reads `"Veto if portfolio_context.already_open_position is true"`
(previously the same rule, but pointed at data that never arrived) plus a new, equally
qualitative rule for `risk_context.entries_blocked` (the drawdown circuit breaker) and
`risk_context.drawdown_pct` ("a qualitative caution signal, not a number to recompute").

---

## Payload Size, Qualitatively

Every specialist's user-message payload now contains exactly the fields that specialist's own prompt
references, plus a slimmed candidate identity summary — no specialist receives another specialist's
Tier-1 context object, and Risk's payload no longer implicitly carries the full `SignalCandidate`
(all 8 context fields via `model_dump()`) when only 2 of them were ever referenced in its prompt.
Technical's payload dropped from 60 raw OHLCV bars to a fixed ~11-field object plus 10 bars of color;
Flow's dropped from three separate raw-row lists (14 days of stockbit_flow + 14 days of broker_flow +
7 days of intraday bars) to one 7-field object; Regime's dropped from two raw-row lists to one 6-field
object. This is a structural, not merely incremental, reduction — the payload no longer scales with
lookback window length, only with the (fixed) number of typed context fields.
