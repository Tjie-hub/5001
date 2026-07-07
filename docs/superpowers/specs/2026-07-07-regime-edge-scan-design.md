# Regime-Conditional Edge Scan — Design Spec

**Date:** 2026-07-07
**Phase:** 4 (Alpha Optimization) — second increment
**Status:** design approved, pending spec review

## Objective

For every strategy in the roster, measure whether it has a positive, *persistent*
out-of-sample edge in a specific market regime — surfacing any ready second edge
(especially for SIDEWAYS, where NR7 loses and all liquid names currently sit)
that is hiding in the disabled roster and would need only a regime gate to
deploy. Ships **no production behavior change**: a research script + a results
doc whose verdict is a ranked list of confirmed-candidate `(strategy, regime)`
edges, or "none — invent a new strategy".

## Why this is the next Phase-4 increment

The NR7 generalization study (2026-07-07, [[project-phase4-nr7-generalization]])
proved a reusable lesson: **a strategy that is negative overall can carry a strong
regime-conditional edge** — NR7 pooled ~0 universe-wide but +1.18%/trade net in
BULL and −0.82% in SIDEWAYS. The 8 disabled strategies were disabled on their
*all-regime* pooled expectancy; none has been tested per-regime. The
mean-reversion-flavored ones (`vwap_reversion`, `conservative`, `Panic Rebound`,
`Crash Recovery`, `Liquidity Sweep`) are prime SIDEWAYS candidates. Scanning the
roster first is cheap (reuses the NR7 harness), data-driven, and decisive either
way — a found edge is a near-free second strategy; no edge justifies inventing one.

## Pre-registered criteria (set BEFORE running)

Reuse `engine.nr7_study.THRESHOLDS` unchanged. Each `(strategy, regime)` **cell**
is classified into one of THREE states (net of the 0.60% round-trip):

1. **Regime bar (T3):** cell pooled expectancy ≥ **+0.50%/trade net**, **N ≥ 100**.
2. **CV persistence (T2):** within that cell's trades, tickers positive on the
   early half retain, on the held-out late half, pooled expectancy ≥ **+0.50% net**
   with ≥ **50%** edge retention. Sample sufficiency uses a **cell-scaled** count
   `t2_min_n = 60` (a single regime cell is much smaller than the whole universe —
   the universe T2 bar of 150 would reject real edges for lack of late sample).

**Three-state outcome (avoids forcing binary on thin samples):**
- **CONFIRMED** — T3 passes AND T2 passes (bar + retention + late N ≥ 60).
- **PROMISING** — T3 passes AND CV retention ≥ 0.50 with positive late expectancy,
  but late N < 60 (edge looks real and persistent but the sample is too thin to
  confirm → recommend SHADOW to accumulate live evidence, do NOT enforce).
- **REJECTED** — T3 fails, OR CV shows negative/decayed late expectancy.

The universe pool (T1, all regimes) is reported per strategy for context but is
**not** a gate here — the whole point is that regime-conditional edges hide behind
a ~0 universe number (that is exactly the NR7 shape). `t2_min_n=60` is the one
scan-local parameter; it is pre-registered here and not tuned after seeing results.

### Multiple-comparisons discipline (mandatory)

14 strategies × 3 regimes = **42 cells**; at a +0.50% bar some will clear by luck.
Defenses, all required:
- The **two-hurdle rule** (regime bar AND CV persistence) — two largely independent
  tests sharply cut false positives.
- The results doc reports **all 42 cells** (full distribution), never only winners.
- Any confirmed candidate is a *SHADOW* candidate only — it must earn a live SHADOW
  period before any enforce (that wiring is a separate, later increment).
- No parameter tuning to make a cell pass. The scan runs each strategy at its
  existing defaults; thresholds are fixed in advance.

## Architecture

Reuse the pure NR7 statistics module untouched; add one orchestration script that
generalizes the NR7 trade collector from a single strategy to all of them.

```
engine/nr7_study.py            # REUSED as-is: pool, cv_split, select_positive_tickers,
                               #   stratify_by_regime, round_trip_net_pct, THRESHOLDS
scripts/regime_edge_scan.py    # NEW: collect_trades_for_strategy(fn, name, ticker, df)
                               #   → loop STRATEGY_FUNCS × liquid universe → matrix +
                               #   per-cell CV → write results doc + JSON
docs/superpowers/results/2026-07-07-regime-edge-scan.md   # written output
```

### Components & data flow

1. **Universe** — liquid names via `engine.liquidity.get_adv_value_30d(conn, t,
   as_of) ≥ VALUE_LIQ_MIN_IDR`, as-of latest corpus date (same as the NR7 study;
   same documented caveat: current ADV, not at-trade-time).
2. **Generalized collector** — `collect_trades_for_strategy(strategy_fn, name,
   ticker, df)` is the NR7 collector parameterised by the strategy function:
   per rolling window (12mo train / 3mo test), prepend a 60-bar warmup tail, run
   the strategy on the extended frame, keep trades with `entry_date >= test_start`,
   recover `raw_exit` by inverting the SELL-leg cost, label entry regime from
   `detect_regime(df[date <= entry].tail(250))`. Emits study-trade dicts tagged
   with `strategy` name. Handles the `strategy_vwma_breakout_pullback` no-`filters`
   signature (call without `filters=`).
3. **Aggregation** — per strategy: `pool(all_its_trades)` (universe/T1 context);
   `stratify_by_regime(...)` (T3 cells). For each cell with `exp ≥ 0.50 and n ≥
   100`, run the CV test on that cell's trades (`cv_split` at the global boundary,
   `select_positive_tickers`, late-vs-early `pool`, retention) → T2 pass/fail.
4. **Verdict** — classify each `(strategy, regime)` into CONFIRMED / PROMISING /
   REJECTED per the three-state rule. Rank CONFIRMED then PROMISING by cell net
   expectancy.
5. **Output** — results doc: the full 14×3 matrix (exp / N / win per cell, with the
   regime-bar PASS/FAIL flag), the CV table for every cell that cleared the regime
   bar, the ranked CONFIRMED and PROMISING lists, and a recommendation. Plus a
   machine-readable JSON block.

## Testing (TDD)

The pure statistics are already covered by `tests/test_nr7_study.py`. New tests:
- **Generalized collector shape** — `collect_trades_for_strategy` on a synthetic df
  with a real roster strategy (e.g. `strategy_vwap_reversion`): every emitted trade
  has `{strategy, ticker, entry_date, raw_entry, raw_exit, regime}`, regime ∈
  {BULL,SIDEWAYS,BEAR}, prices > 0, and `strategy` equals the passed name.
- **VWMA special-case** — collector runs `strategy_vwma_breakout_pullback` without
  raising (proves the no-`filters` branch).
- **Smoke** — the scan runs end-to-end on a 2–3 ticker × 2 strategy slice and
  produces a matrix dict with the expected `(strategy, regime)` keys.

## Out of scope (explicitly)

- Wiring any found edge into the live scan / regime map — separate SHADOW-gated
  increment, specced only after a candidate is confirmed.
- Inventing a new strategy — only if the scan finds no confirmed candidate.
- Re-tuning any strategy's parameters; changing `THRESHOLDS`.
- Portfolio construction / ranker / adaptive weighting (4.1/4.3/4.4).

## Deliverable & definition of done

- `scripts/regime_edge_scan.py` runs end-to-end on the prod corpus.
- New collector unit tests + smoke green; full suite green.
- `docs/superpowers/results/2026-07-07-regime-edge-scan.md` written with the full
  14×3 matrix, per-cell CV for cleared cells, ranked CONFIRMED and PROMISING
  lists, and a one-paragraph recommendation: which `(strategy, regime)` (if any) to
  take to a SHADOW-wiring increment (CONFIRMED → wire; PROMISING → SHADOW to gather
  data), or — if all REJECTED — that the roster has no persistent regime-conditional
  edge and a new strategy is justified.
