# AF-2 — Behavioral Regression Report

**Date:** 2026-07-29
**Companion to:** `Audit/AF2_PRODUCTION_VALIDATION_REPORT.md`.
**Purpose:** distinguish, with concrete evidence, between defects, expected behavioral changes,
technical debt, and future enhancements — per this validation's explicit rule not to flag expected
changes as regressions.

No literal pre-migration/post-migration historical decision log exists to diff against (the
migration changed how candidates are *constructed*, not a retained, replayable historical dataset) —
"pre-migration baseline" is therefore reconstructed directly, in this session, by running the
identical candidate through the identical real pipeline **with and without** Tier-1 context attached,
which is exactly the difference the migration introduces. This is a more precise comparison than a
historical-log diff would give, because it isolates the one variable that changed (context presence)
while holding the strategy, score, and LLM behavior (the scripted provider) fixed.

---

## 1. Direct Before/After Comparison — `major_news` Scenario

Same candidate (ticker `NEWS`, strategy `momentum_following`, score 4.5), same real seeded data, same
scripted provider, evaluated twice — once with every Tier-1 field left at its pre-WP2/pre-WP4
default (`None`, the exact shape a candidate from `run_premarket_firm_scan()`/`run_eod_trade_plan()`/
`_agent_confirms_exit()` had before WP4), once with real context attached:

| | Decision | Confidence | Size hint | Rationale |
|---|---|---|---|---|
| **Before** (no Tier-1 context) | veto | 0.7 | 0.0 | "Risk: only 0/4 bullish, quant=0.95.\nBull/Bear: bear dominates" |
| **After** (real Tier-1 context) | **approve** | 0.8 | 1.2 | "Risk: 3/4 bullish, quant=0.95.\nBull/Bear: bull dominates" |

**Classification: expected behavioral change, not a defect.** This is the single clearest,
concretely-demonstrated illustration of what the WP2→WP3→WP4 migration was built to fix: before
Tier-1 context existed (or before it reached a given call site, per WP4's finding), every analyst
node had nothing concrete to evaluate — `quant_score` alone, without analyst corroboration, rarely
clears the Risk Manager's approval bar (`risk_v2.md`'s own decision framework requires analyst
alignment, not just a raw score). A genuinely bullish candidate — real uptrending technicals, a real
`BULL` regime reading, real positive news headlines — was being **silently vetoed for the wrong
reason** (analysts uninformed, not because the trade was actually bad) at any call site missing
context. Post-migration, the same real signal is correctly recognized and approved. This is the
intended, designed effect of ADR-AF-002, not a side effect.

## 2. Direct Before/After Comparison — `normal_trading_day` Scenario

Same method, ticker `NORM` (which has a real, seeded open paper-trade position):

| | Decision | Confidence | Rationale |
|---|---|---|---|
| **Before** | veto | 0.7 | "Risk: only 0/4 bullish, quant=0.9.\nBull/Bear: bear dominates" |
| **After** | veto | **0.9** | "Risk: already open position.\nBull/Bear: n/a" |

**Classification: expected behavioral change, same top-level outcome, different (and now correct)
reasoning.** The final decision (veto) coincidentally matches in this case, but the *reason*
changes fundamentally: before, the veto happened because no analyst had signal to offer (an
uninformed default); after, the veto happens because of a real, correct, load-bearing fact — an
open position already exists on this ticker — exactly the "no doubling up" rule `risk_v2.md` has
always stated but which `Audit/AF2_WP3_REGRESSION_REPORT.md` documented as structurally
undeliverable before WP3 wired `PortfolioContext` into `risk.py`. The higher confidence (0.9 vs. 0.7)
reflects that the post-migration veto rests on a certain fact, not a guess — also expected, not a
regression.

## 3. Reachable Value Space of `RegimeContext.regime_call`/`MarketContext.regime`

**Observation, not a defect:** `RegimeContext.regime_call`/`MarketContext.regime` are typed as
`Literal["BULL", "BEAR", "SIDEWAYS", "VOLATILE", "UNKNOWN"]`, but the canonical producer,
`engine.regime_filter.detect_regime()`, only ever returns `"BULL"`, `"BEAR"`, or `"SIDEWAYS"` (by
direct read of its source — confirmed this session). `"VOLATILE"` is therefore **schema-reachable
but never actually produced** by the current implementation; the `high_volatility` scenario in the
Production Validation Report confirms this empirically — its regime came out `SIDEWAYS`, not
`VOLATILE`, with the volatility signal correctly carried instead by `macro_risk="HIGH"` (a
genuinely separate, ticker-level field derived from VPIN/volume-ratio spikes, per
`engine/agent_firm_context.py::build_regime_context()`).

**Classification: pre-existing characteristic, not a WP1-4-introduced regression.** This predates
the ADR-AF-002 migration entirely (`detect_regime()` is an unmodified, pre-existing canonical
function per `ADR-AF-001`) — the migration correctly wired a passthrough to whatever this function
already produced, and never claimed to add a `VOLATILE` classification. Flagged here as a
**documentation/technical-debt observation** for whoever wrote the `regime_v1.md` prompt's own
`"VOLATILE"` guidance line (it describes a value the model will structurally never receive from
`regime_context.regime_call`) — a minor prompt-clarity item, not a functional defect, and explicitly
**not corrected in this session** per the rule "do not change prompts unless a genuine production
defect requires it." The model can still legitimately output `"VOLATILE"` in its own `regime_call`
response field (the Risk/committee reads the model's output, not only the passthrough value) — this
observation concerns only what `regime_context.regime_call` (the *input* the model receives) can
ever contain, not what the model's own output field can contain.

## 4. Test-Suite Non-Regression (Re-Confirmed, Not Re-Litigated)

`Audit/AF2_WP4_FINAL_CERTIFICATION.md` and `Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md`
already established, across two independent full-suite runs, that the full repository test suite
(1564 passed / 44 failed / 9 errors) is byte-for-byte identical in its failure/error set to the
pre-WP4 baseline. This validation session made no code changes, so this fact is unchanged and is not
re-verified from scratch here — re-litigating an already-confirmed, unchanged fact would not
constitute new evidence.

## 5. Summary Classification

| Change | Classification |
|---|---|
| Candidates at previously-unwired call sites (premarket/EOD/exit-review) now receive real context and can be approved/vetoed on real signal instead of defaulting toward "insufficient analyst support" | **Expected behavioral change** (the entire point of ADR-AF-002) |
| Risk Manager's open-position veto now actually fires (previously undeliverable) | **Expected behavioral change** (WP3, re-confirmed here with a live example) |
| `regime_call`'s `"VOLATILE"` enum value is unreachable from the real producer | **Technical debt / documentation observation**, pre-existing, not introduced by WP1-4 |
| `reset_market_ctx()` compatibility shim | **Technical debt**, already documented, blocked by 2 non-production scripts |
| `ConsensusContext`/`SessionContext`/`OpportunityContext` unbuilt | **Deliberately deferred future enhancement**, not a defect |

**No unexpected regression was found in this validation pass.** Every behavioral difference observed
traces directly to the documented, intended effect of attaching real Tier-1 context where none
existed before.
