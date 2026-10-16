# DRAFT — Mechanism memo: sector (industry) momentum on IDX

**Status:** DRAFT, not accepted · **Date:** 2026-10-16 · **Type:** Mechanism proposal (D-070 §1), input to a
D-entry · **Requested by:** owner, 2026-10-16 ("untuk index sectoral apakah sudah masuk research" → "DRAFT").
**Nothing here is registered.** No census arm is spent, no HYPOTHESIS_REGISTRY row is added, and no return of
any sector portfolio has been computed or read in preparing this memo.

---

## 0. Where sector research stands today (facts, checked 2026-10-16)

| item | state |
|---|---|
| Official IDX sectoral indices (IDX-IC: IDXFINANCE, IDXENERGY, …) | **not in any table**; `ohlcv` holds IDX equities + IHSG (from 2021-07-05) only |
| Ticker → sector labels | `ticker_sector`: 780 tickers, 11 sectors + 11 blank, 109 industries; source yfinance, fetched 2026-09-19 (GAP1). **One snapshot, no membership history** |
| Sector as a *control* | used once: sector-neutral construction in GAP1 (VOLEX survived, t 4.24 → 3.22; dividend yield collapsed, t 2.29 → 1.03) |
| Sector as a *signal* | **never tested.** Not in the factor zoo (2026-09-18 said untestable, no labels), not in the registry, not in the failure registry |
| Family map v2 (2026-09-29), item E `{S}` | **parked**: "trend-family-correlated by construction … negative-expected-value. Re-offer only after REGIME-002's first read." |
| Production | `engine/sector_rotation.py` (82 hand-mapped names, momentum score → OVERWEIGHT/UNDERWEIGHT) feeds two scanner filters. **Unvalidated heuristic** |

The last row is the practical reason to test it: a sector-momentum rule already shapes live candidates
without evidence. A determinate result either way has a use.

**The parking note is binding until the owner overrides it.** Section 7 states the override case and its cost.

## 1. Mechanism (not price prediction)

**Industry momentum: slow diffusion of industry-wide news.** Information that affects a whole sector (commodity
prices, regulation, rates, sector-wide flows) is absorbed into prices gradually, so sectors that rose over the
past months keep outperforming those that fell over the next month (Moskowitz and Grinblatt 1999; Hong, Torous
and Valkanov 2007 on industries leading the market; Hou 2007 on intra-industry lead-lag).

- **Pre-declared sign:** past-winner sectors outperform past-loser sectors. A reversal result is **not** a
  rescue and is not tested.
- **IDX-specific reason to expect it:** IDX sectors are dominated by commodity (coal, nickel, CPO) and
  regulation exposure (2026: MSCI consultation, export rules), both slow-moving themes. The macro-watch
  regulation categories built on 2026-10-16 are this mechanism's information channel.
- **IDX-specific reason to doubt it:** a sector is often 3–10 liquid names, so a "sector return" is close to a
  few stocks' returns. Stock-level momentum (12-1, 6-1, 3-1, 1m) **died** on the median test in the factor zoo
  (lottery tail); only 52-week-high proximity survived. If sector momentum is just aggregated stock momentum it
  will die the same way.

## 2. Distinct from what already failed or is in flight

| prior | why this is different | control required |
|---|---|---|
| Factor zoo stock momentum (died on median) | ranks **sectors**, holds every liquid member; not the extreme stocks | Fama-MacBeth: sector signal incremental over the stock's own 6-1 return and hi52 |
| HYP-PM-0010 {T1} trend onset (in forward test) | time-series, per stock, entry on a trend state; this is **cross-sectional across sectors**, monthly | report the signal's overlap with {T1} onset days pre-outcome (share of top-sector members in a {T1} state) |
| D-079 market-stress reversal (FAILED) | market-wide, after a shock; this is relative, every month | none |
| FWD-PM-VOLEX-001 (unregistered record) | volatility exclusion is a **required control**, not the mechanism | FM incremental over Parkinson-60 vol |

## 3. Family

**Proposed: open `{S}` Industry-Cross-Section** (the label the family map reserved). Slot 1 = A1 below.
Rationale for a separate family: it uses a sector-membership instrument that no existing family uses, and
widening {T1} to absorb it would be an irreversible widening of a family with a live forward test
(PG-3/PG-6/R7.5). **Owner decision.**

## 4. Proposed design (frozen at G0, not now)

One arm, literature parameters, **no grid** — every extra arm raises the bar for all.

- **A1 — long-only top sectors vs the liquid universe.**
  - Formation: equal-weight return of each sector's liquid members over months t−6 … t−2 (skip the most recent
    month: the one-month reversal is a separate effect).
  - Hold: month t. Buy every liquid member of the **top 3 of 11** sectors, equal weight.
  - Benchmark: equal weight of all liquid names. Long-only because IDX short-selling is not practically
    available to the owner; a long-short spread is reported, not tested.
- **Universe and liquidity:** the D-081 basis (regular-market volume); ADV and price floors as in D-084 G0
  practice, frozen at G0. Sector needs ≥ 3 liquid members in the formation month or it is not ranked.
- **Sector return weighting:** equal weight (no historical market cap in the panel). Turnover weight reported.
- **Cost:** D-082 `cost_realised` where ticks exist; the mapping for earlier years must be frozen at G0 (open
  item — the 0.60% round trip is the fallback, stated before any run).
- **Data:** the extended panel (2000-07 → 2026-07, 43,136 name-months, 780 tickers; `data_gaps/`), split-adjusted
  as built 2026-09-19, labels from `ticker_sector`.
- **Pass (all required):**
  1. Net-of-cost NW t ≥ the bar at registration (next id HYP-PM-0022 at N = 613 → bar 3.2996).
  2. Both halves (2001–2013, 2014–2026) positive net.
  3. FM incremental over own 6-1 return, hi52 and Parkinson-60 vol: sector coefficient t ≥ 2.
  4. Median-based check: the top-sector book's **median** month excess > 0 (the factor-zoo lesson).
- **Descriptive only, not part of pass:** official IDX-IC indices (from 2021-01) if they can be fetched; the
  2021–2026 window is the most-searched era in this repo and too short.

## 5. Stop rule (frozen before power is computed)

- **Placebo noise:** assign tickers at random to 11 pseudo-sectors of the real sizes, recompute the A1 spread
  (no real sector returns read), 1,000 draws → σ of the monthly spread.
- **Design effect:** 0.25% a month net (half the US long-short literature; long-only vs universe).
- **Stop if power < 20%** at that effect and the bar. Then WITHDRAWN before registration, uncounted
  (the D-087/D-094/D-097 pattern).

## 6. Stated limits (before any number)

1. **Survivorship.** The panel's 780 tickers are names with labels today; delisted names are missing. The bias
   is not uniform across sectors (mining and property lost more names), so it can manufacture a sector spread.
   G0 must report members per sector per year and the delisting count it can establish; if it cannot bound the
   bias, that is a stop reason.
2. **Labels are not point-in-time.** A company's sector today is applied to 2000. Mostly stable, but
   conglomerates and pivots (e.g. coal → nickel) are misclassified historically.
3. **yfinance sectors ≠ IDX-IC.** Eleven GICS-like sectors, not IDX's official classification.
4. **Thin sectors.** Utilities has 13 names in total; in early years several sectors will have < 3 liquid names
   and drop out of the ranking, which changes "top 3 of 11" into top 3 of fewer.
5. **Prior is weak.** Every IDX price-pattern search since D-070 has been NULL; stock momentum died; the family
   map called this negative-EV. A NULL is the likely outcome and would still be useful (§0, production rule).

## 7. The override decision the owner must make

The family map parked `{S}` until REGIME-002's first read. Running this now:
- **Costs** one census arm (612 → 613; bar 3.2991 → 3.2996 for every later test) if it passes G0.
- **Buys** a determinate answer on a rule that production already applies unvalidated
  (`engine/sector_rotation.py`).
- **Does not** read or touch REGIME-002 (separate instrument, separate family).

Options: (a) override and accept `{S}` now; (b) keep it parked, and instead switch the production
sector-rotation filter to observe-only until tested; (c) both.

## 8. Draft D-entry text (for the owner to accept, edit or reject)

> ### D-101 · Mechanism accepted: industry momentum — new family Industry-Cross-Section {S}
> **Status:** DRAFT · **Date:** — · **Type:** Mechanism acceptance (D-070 §1) · **Approval authority:** Owner, —.
> Overrides the family-map v2 parking of `{S}` (2026-09-29, item E) for one arm.
> - Mechanism: slow diffusion of industry-wide news (Moskowitz-Grinblatt 1999; Hong-Torous-Valkanov 2007).
>   Pre-declared sign: past-winner sectors outperform. Reversal is not a rescue.
> - Family: new `{S}`, slot 1 = A1 (6-2 formation, 1-month hold, top 3 of 11 sectors, long-only vs the EW liquid
>   universe). Incremental over own-stock 6-1, hi52 and Parkinson-60 vol is a pass condition.
> - Data: extended panel 2000-07 → 2026-07 + `ticker_sector` snapshot, hash-pinned in the G0.
> - G0 before any outcome: survivorship bound, label caveat, placebo σ, stop rule at 20% power.
> - The bar at the census + 1. Both halves must carry the sign. Net of cost.
>
> **Amendment.** Only by a superseding D-entry.

## 9. Next step after acceptance

A G0 branch `research/sector-momentum-2026-10` with: predeclaration + sha256 sidecar, panel and label hashes,
survivorship report, placebo σ and power — **no G1 runner shipped** until the owner approves G1 (the D-084 pattern).
