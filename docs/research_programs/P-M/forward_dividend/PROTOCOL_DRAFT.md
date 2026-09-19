# FWD-PM-DIVYIELD-001 — PROTOCOL (DRAFT, **SUPERSEDED 2026-09-19**)

> **SUPERSEDED — do not register.** Two findings later the same day disqualified
> this candidate. Gap 1 showed the signal is ~61% sector composition: its pooled
> +0.909%/mo falls to +0.353%/mo (t 1.03) under sector neutrality. The extended
> 26-year panel then put it at t 1.79 (2021-26), t 2.53 (pre-2021) and t 3.36
> (full) sector-neutral — below the 3.57 bar throughout.
> The replacement candidate is `../forward_volex/PROTOCOL_DRAFT.md`
> (FWD-PM-VOLEX-SN-001), which clears the bar out-of-sample.
> This file is preserved unedited below as the record of what was drafted.

# FWD-PM-DIVYIELD-001 — PROTOCOL (DRAFT, NOT REGISTERED)

**Status:** DRAFT. **Not registered. No family slot consumed. Not open.**
Registration requires an owner decision (PG-3 / D-028): it would either widen an
existing family or open a new one, and that act is irreversible. This document is
the frozen *candidate* spec so that registration, if chosen, needs no further
design work — and so that no design choice can be made after seeing forward data.

**Drafted:** 2026-09-19 · **Evidence:** `../alpha_search_v2/` (FINDINGS, POWER_CEILING)

## 0. Why this exists

The in-sample search is closed and its conclusion is negative: on 4.8 years of
IDX data, `t ≈ Sharpe × √years`, the best achievable Sharpe is 0.94, and the
multiplicity-corrected bar of t = 3.57 needs ~14–33 years. **No specification can
close that gap**, which was verified on five axes (return, risk-adjusted,
rebalancing frequency, composite, sample).

Out-of-sample time is therefore the *only* input that raises evidence without
raising the bar. This spec exists to start accruing it.

## 1. Frozen specification

**Universe**, evaluated at each month-end on settled data (`is_final=1`):
- `ADV60 >= Rp 1,000,000,000`
- `close >= Rp 50`
- >= 60 sessions of price history
- `volume > 0` on the formation date
- **zero zero-volume sessions in the trailing 60** (tradeability conditioning —
  see `../vol_exclusion/TRADEABILITY_RERUN_2026-09-18.md`; without this the
  measured edge is inflated by suspended names)

**Signal**, in this order:
1. Compute Parkinson-60 volatility; **drop the top decile** (exclusion, not ranking
   — low-vol *selection* does not work: +0.32%/yr, t 0.19)
2. Compute trailing-12-month cash dividends per share from `corporate_actions`
   using **ex-dates strictly before** the formation date; divide by close
3. Hold the **top quintile** by that yield, **equal weighted**

**Rebalance:** monthly, at the first session after month-end. Execution **not at
the open** — the opening window carries ~78% wider effective spread and 2.4x the
dispersion (`../factor_zoo/FUNDAMENTALS_ADDENDUM`, §6.3).

**Hedge (the primary arm):** short IHSG exposure at a **fixed β = 0.70**,
re-estimated never. Vol-targeting is deliberately **excluded** from the primary
arm — it helped in-sample only after hedging and is a second free parameter.

**Costs:** 0.60% round trip (`engine/exits/costs.py`), applied to realised
turnover each period.

## 2. Endpoint and decision rule

**Primary endpoint:** monthly excess return of the hedged book over the 6.25%
annualised deposit rate, recorded per month, never pooled across amendments.

**Pre-committed decision points** — no earlier readout is a decision:
- **24 months:** interim only. No promote/reject.
- **36 months:** first decision. PROMOTE requires the accumulated t on the hedged
  series to exceed **2.5** *and* the cumulative return to exceed deposit.
- **60 months:** final. PROMOTE requires **t > 3.0**.

These thresholds are below the in-sample bar of 3.57 deliberately: forward
evidence carries no multiplicity penalty because the spec is frozen before
observation. That is the entire point of doing it this way.

**REJECT** at any decision point if the cumulative hedged return is below zero.

## 3. Expectations, stated in advance

From in-sample evidence (which is *not* a prediction, but the benchmark to
falsify): +10.75%/yr net, Sharpe 0.94, maxDD −10.4%, ~80 names, turnover
0.02–0.16/mo. If forward Sharpe lands materially below ~0.5, the in-sample result
was a 2025 artefact and this should be rejected early.

## 4. Forbidden

- Changing universe, signal, weighting, hedge ratio, rebalance date or cost model
  after opening. Any change closes this spec and opens a successor; results either
  side are never pooled (the 001→002 precedent).
- Reading the ledger to decide anything before 36 months.
- Adding vol-targeting, changing the exclusion decile, or tuning the quintile.
- Treating the in-sample numbers in §3 as evidence *for* the strategy.

## 5. Known limitations, disclosed at draft time

1. **2025 dependence.** Ex-2025 the unhedged book returns +2.45%, below deposit.
   Forward data must cover at least one full non-2025-like regime to be informative.
2. **Dividend data is yfinance-sourced**, ex-dates verified empirically
   (corr(return, −yield) = +0.607 on 1,856 observations) but not vendor-grade.
3. **IDX80 inapplicability.** Every edge here lives *outside* the index; inside
   IDX80 the volatility overlay is −0.32%/mo. This spec is not investable by an
   IDX80-mandated book.
4. **Breadth.** ~80 names. Below ~50 the volatility component degrades sharply
   (IR 0.39 at N=10 vs 1.14 at N=200).
5. **Capacity untested** for the hedged variant; the unhedged mid-ADV estimate
   breaks even near Rp 136bn AUM.
6. **The hedge assumes a shortable IHSG instrument exists** at reasonable cost.
   **Unverified — this is a precondition, not an assumption.**

## 6. What registration would require (owner decision)

- A family determination under PG-3/D-028: does this widen `Price-Trend {T1}`, or
  open a new family? Dividend yield is not a price-trend feature, which argues for
  a new family — and that is a one-way door.
- A multiplicity declaration covering the ~140 trials already spent in-sample.
- A `HYPOTHESIS_REGISTRY` entry and an evidence receipt.

None of that has been done. **This document is inert until it is.**
