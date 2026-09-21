# Dataset A — `regime_classification` Characterization (F-5, D-042 Option B)

**Status:** Descriptive characterization only. **Not an O15 Regime object** (no `DEFINED→DECLARED→APPLIED`
lifecycle entered; nothing written to `regime_profiles`; no strategy/trade evaluation performed). Produced
under [[DECISION_LOG]] D-042 (Option B) authorization, scoped **only** to satisfying F-5 for Dataset A's FROZEN
gate.
**Date:** 2026-09-09 · **Program:** P-M · **Object:** `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A)

---

## 1. Methodology (reused, not invented)

Per D-042's scope ("use only appropriate existing canonical market evidence... keep the result descriptive
rather than trade-conditioned"), this characterization reuses the **existing, already-canonical** rule-based
classifier `engine/regime_filter.py::detect_regime()` **verbatim** — no new threshold or logic invented:

```
BULL:     ADX(14) > 25  AND  MA-slope(20,5) > +1.0%
BEAR:     ADX(14) > 25  AND  MA-slope(20,5) < -1.0%
SIDEWAYS: everything else (including NaN warmup days)
```

`detect_regime()` itself only labels a single latest bar; this characterization applies the **identical rule**,
using the **identical indicator functions** (`engine.indicators.calc_adx`, `calc_ma_slope`), to **every trading
day** in Dataset A's exact window — a direct, faithful extension, not a new methodology. This is explicitly
**not** the trade-conditioned `research/regime/` machinery (`collect_tagged_trades`/`tag_trade`, which labels
regime at individual strategy-trade entry points and writes to `regime_profiles`) — that pipeline was not
invoked, per instruction.

**Evidence source:** `ohlcv WHERE ticker='IHSG'` — the same canonical market-index series used throughout this
governance work as the trading-calendar confirmation source (`canonical_trading_dates()`,
`tools/broker_flow_idx80_gap.py`). 470 daily bars loaded, `2024-09-02 → 2026-08-27` (includes a
~4-month warmup buffer before Dataset A's window start for ADX(14)/MA(20)+slope(5) to settle; only bars within
`[2025-01-02, 2026-08-27]` are classified/reported).

## 2. Result

| Regime | Trading days | % of window |
|---|---|---|
| SIDEWAYS | 239 | 61.6% |
| BEAR | 103 | 26.5% |
| BULL | 46 | 11.9% |
| **Total** | **388** | **100%** — matches Dataset A's exact date count (F-2 receipt) exactly |

**21 distinct regime runs** (20 label transitions) across the window — not a single static regime, and not
noise-level flip-flopping either (runs range from single days to multi-month spans; the two BEAR runs alone
span 2026-02-03→2026-03-04 and 2026-03-06→2026-04-13, plus 2026-05-12→2026-06-25).

**Price-level context [DB-VERIFIED, IHSG close]:**
- Window start (2025-01-02): 7,163.21. Window end (2026-08-27): 6,423.61. **Overall window return: −10.32%.**
- **Peak within window: 9,134.70 (2026-01-20).** Trough within window: 5,342.14 (2026-06-08).
- **Maximum peak-to-trough drawdown: −41.52%**, from the January 2026 peak to the June 2026 trough. Verified
  against the raw daily close series (`2026-05-25 → 2026-06-19`): a gradual, multi-day decline (6,206 → 6,130 →
  6,195 → 5,941 → 5,839 → 5,595 → 5,342 → recovery to 5,747…), **not a single-bar data glitch.**

## 3. Populated field value

```
regime_classification: mixed — SIDEWAYS 61.6% / BEAR 26.5% / BULL 11.9% of trading days (rule-based,
  ADX(14)>25 & MA-slope(20,5) thresholds, reusing engine/regime_filter.py::detect_regime()'s existing
  definition, applied daily to IHSG); includes a documented ~41.5% peak-to-trough IHSG drawdown
  (2026-01-20 peak 9,134.70 -> 2026-06-08 trough 5,342.14), followed by partial recovery. Overall window
  return -10.32%. Descriptive characterization only — not an O15 Regime object; not trade-conditioned;
  not applied to any strategy.
```

## 4. Limitations (stated, not glossed over)

1. **Index-level, not stock-level.** This characterizes IHSG's own regime path, not the 79 individual Dataset A
   tickers' idiosyncratic behavior — a ticker can move against the index regime. `regime_classification`'s ROM
   definition ("market conditions during the sample period") is satisfied at the market/index level, consistent
   with the `WORKED_EXAMPLE_END_TO_END.md` §S4 precedent, which is also index/universe-level, not per-ticker.
2. **A different classifier could yield different boundaries.** `detect_regime()`'s thresholds (ADX>25, slope
   ±1.0%) are the existing production convention, reused for consistency — not independently validated here as
   "the" correct regime definition. A different, equally reasonable rule could shift the exact day-counts.
3. **Not a claim, not evidence for any hypothesis.** This is descriptive dataset metadata, produced for
   governance completeness (F-5) — it carries **no evidence tier**, is not an Observation (O11) or Result (O12),
   and must not be cited as support for any future hypothesis without that hypothesis independently defining its
   own regime-conditioning per [[RESEARCH_OBJECT_SCHEMA]] §5.1 (O15).
4. **No O15 Regime object was created.** `regime_profiles` still does not exist as a table in this database
   (confirmed unchanged from the F-5 investigation) — nothing was written to it, and this artifact does not
   create it. This satisfies D-042 Option B's explicit scope ("do not create a formal O15 Regime object").

## 5. Worktree note

This artifact and the DECISION_LOG entries (D-042, and the `regime_classification` field-population records) are
the only outputs of this step. No production code was modified (only read). No `regime_profiles` row was
written. No hypothesis registered, no empirical test run.
