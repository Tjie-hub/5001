# NR7 Edge-Generalization Study — Design Spec

**Date:** 2026-07-07
**Phase:** 4 (Alpha Optimization) — first increment
**Status:** design approved, pending spec review

## Objective

Decide, with pre-registered OOS rigor, whether NR7 Breakout's measured edge
(+1.75%/trade net, 44 tickers) is a **generalizable** strategy edge worth
widening live — or **selection bias** confined to the 44 names that happened to
clear the ≥20-trades reporting bar. The study produces evidence + a binary
decision that gates a *separate, later* increment (the SHADOW widening rollout).

This increment ships **no production behavior change.** It is a reproducible
research script plus a results document. The whole point is that its verdict can
be "do NOT widen" — and that is a valid, valuable outcome.

## Why this is the first Phase-4 increment

Spike findings (2026-07-07, recorded in the audit memory):
- NR7 is the only strategy with positive pooled OOS expectancy (+1.75%/trade net).
- On liquid names (ADV ≥ Rp 5bn) the edge *holds*: +1.92%/trade, 243 trades, 11 names.
- **But** across all 943 scored tickers the per-ticker OOS return is ~0 (mean
  −0.01%, median −0.05%, 34% positive), and ~0 on the 178-name liquid subset too.
- Live selection (`_edge_selectable`, scanner.py:642) requires a **per-ticker**
  `wf_edge` row with positive expectancy → NR7 is effectively restricted to ~8
  liquid positive-edge names, BULL-regime-gated. Hence 0 live paper trades.

So the edge is real on the 44 but invisible on the universe. Widening hinges on
one unanswered question — does it generalize? — which must be tested before any
live change. Portfolio/ranker work (4.1/4.3/4.4) is premature on one thin edge;
gate-softening (4.2) and second-edge hunting (4.5) are fallbacks if this fails.

## Pre-registered pass criteria (set BEFORE running — no post-hoc tuning)

All expectancy figures are **net of the full round-trip cost model** (buy 0.15% +
sell 0.25% + slippage 0.10%/leg = 0.60% round trip; `engine/exits/costs.py`).

| Test | PASS threshold |
|---|---|
| **T1 Universe** | Trade-weighted pooled OOS expectancy across the full liquid universe (ADV ≥ Rp 5bn) ≥ **+0.50%/trade net**, with **N ≥ 300** pooled trades. |
| **T2 Selection/CV** | Tickers selected as positive on the EARLY half of OOS windows retain, on the held-out LATE half, pooled expectancy ≥ **+0.50%/trade net** with **N ≥ 150**, AND ≥ **50%** of their early-period edge (late_exp ≥ 0.5 × early_exp). |
| **T3 Regime** | Per entry-regime stratum (BULL / SIDEWAYS / BEAR): pooled expectancy ≥ **+0.50%/trade net** with **N ≥ 100** to call that regime "tradeable". |

**Decision rules (also pre-registered):**
- **WIDEN-UNIVERSE** is justified only if **T1 AND T2 both pass** (edge is broad
  and persists out-of-sample → the per-ticker gate is an unnecessary restrictor).
- **WIDEN-REGIME to include SIDEWAYS** is justified only if the SIDEWAYS stratum
  passes T3 (currently all liquid names sit in SIDEWAYS, so this is the lever with
  the most live upside).
- If **T1 or T2 fails** → do NOT widen the universe; the 44-name edge is treated as
  selection bias. Recommendation flips to Phase-4 fallback (hunt a second edge).
- The study reports each test's numbers regardless; the thresholds decide, not us.

## Architecture

One research script + one pure aggregation module (so the statistics are
unit-testable without a 5-year backtest), writing a results doc. No scheduler
wiring, no live-path edits.

```
scripts/nr7_generalization_study.py   # orchestration: load corpus → run NR7 WF
                                       #   per liquid ticker → collect labelled trades
                                       #   → call the pure aggregators → write results
engine/nr7_study.py                    # PURE, unit-tested: pooling, CV split,
                                       #   regime stratification, cost application,
                                       #   pass/fail evaluation against thresholds
docs/superpowers/results/2026-07-07-nr7-generalization-study.md   # written output
```

### Components & data flow

1. **Universe** — all tickers with `get_adv_value_30d(conn, ticker, as_of) ≥
   VALUE_LIQ_MIN_IDR` (`engine/liquidity.py`), measured as-of the study date.
   *Known limitation (documented in results): ADV is current, not at-trade-time;
   a ticker's liquidity can drift. This biases toward names liquid today.*
2. **Trade generation** — for each liquid ticker, walk the 5y corpus with the
   Phase-2 window scheme (12mo train / 3mo test rolling), and inside each **OOS
   test window** run `strategy_nr7_breakout(df_window)` collecting each `Trade`'s
   `entry_date`, `exit_reason`, and raw entry/exit prices. Only OOS-window trades
   count (no train-window trades in the pool).
3. **Cost normalization** — recompute each trade's net pnl_pct with the FULL
   round-trip model via `engine/exits/costs.apply_costs` on BOTH legs (do not
   trust the strategy fn's SELL-only deduction; memory note 4338). This is done in
   the pure module so it is tested.
4. **Regime labelling** — for each trade, `detect_regime(df[:entry_idx])`
   (`engine/regime_filter.py`) → BULL / SIDEWAYS / BEAR at entry (trailing data
   only, no look-ahead).
5. **Aggregation (pure)** — `engine/nr7_study.py`:
   - `pool(trades) -> {exp_pct, n, win_rate}` (trade-weighted).
   - `cv_split(trades, boundary_date) -> (early, late)`; `select_positive_tickers(
     early, min_trades)`; evaluate late-period pooled expectancy on that ticker set.
   - `stratify_by_regime(trades) -> {regime: pooled}`.
   - `evaluate(results, thresholds) -> {T1, T2, T3, widen_universe, widen_regime}`.
6. **Output** — `scripts/…` renders the results doc: the pooled table, the CV
   table, the regime table, each PASS/FAIL vs threshold, and the final decision
   with the exact numbers. Also emits a machine-readable JSON block for the record.

## Testing (TDD)

`engine/nr7_study.py` is pure and fully unit-tested on **synthetic trade lists**
(no DB, no 5y run):
- `pool` trade-weights correctly; empty → n=0.
- `apply_round_trip_cost` reduces a known gross trade by exactly 0.60%.
- `cv_split` partitions by date boundary; `select_positive_tickers` picks only
  early-positive names with ≥ min_trades; the CV evaluation on a hand-built set
  where early-positive tickers go negative late → correctly reports "does not
  persist".
- `stratify_by_regime` buckets and pools per label.
- `evaluate` returns the right PASS/FAIL and decision for fixtures crafted to sit
  just above/below each threshold (boundary tests).

The orchestration script gets a thin smoke test (runs on a 2–3 ticker slice with a
tiny window to prove the wiring, not the statistics).

## Out of scope (explicitly)

- Any change to `_edge_selectable`, `_REGIME_STRATEGY_MAP`, or the live scan path.
- SHADOW routing / measurement of a widened NR7 — that is the **next** increment,
  specced only after this study's verdict is known.
- Portfolio construction, ranker/sizer, adaptive weighting (4.1/4.3/4.4).
- Re-running the full multi-strategy WF refresh (NR7-only here).

## Deliverable & definition of done

- `engine/nr7_study.py` + full unit tests (green).
- `scripts/nr7_generalization_study.py` runs end-to-end on the prod corpus.
- `docs/superpowers/results/2026-07-07-nr7-generalization-study.md` written with
  the three test tables, PASS/FAIL against pre-registered thresholds, and the
  binary WIDEN / DO-NOT-WIDEN decision.
- A one-paragraph recommendation for the next increment based on the verdict.
