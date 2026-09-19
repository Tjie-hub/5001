# FWD-PM-VOLEX-SN-001 — PROTOCOL (DRAFT, NOT REGISTERED)

**Status:** DRAFT. **Not registered. No family slot consumed. Not open.**
Supersedes `../forward_dividend/PROTOCOL_DRAFT.md` as the forward-test candidate.

**Drafted:** 2026-09-19 · **Evidence:** `../data_gaps/EXTENDED_PANEL_RESULT_2026-09-19.md`

## 0. Why this replaces the dividend draft

The dividend book was drafted as the candidate on 2026-09-19 morning. Two later
findings disqualified it:

- **Gap 1 (sector labels):** its pooled edge of +0.909%/mo falls to +0.353%/mo
  (t 1.03) under sector neutrality. It was ~61% sector composition.
- **Extended panel:** sector-neutral it reads t 1.79 (2021-26), t 2.53 (pre-2021),
  t 3.36 (full 26 years) — **below the 3.57 multiplicity bar throughout**.

The volatility overlay clears that bar, out-of-sample, under every tradeability
filter tested. It is the better candidate and this spec targets it instead.

## 1. The evidence being forward-tested

Sector-neutral volatility tail-exclusion, on a 26-year panel of which 16 years
were used in none of the ~140 in-sample trials:

| filter | FULL t | mo | **PRE-2021 t** | mo | effect %/mo |
|---|---|---|---|---|---|
| clean (0 zero-vol in 60) | 4.70 | 143 | **3.48** | 76 | +0.254 |
| ≤3 zero-vol in 60 | 5.34 | 177 | **4.07** | 110 | +0.276 |
| forward-only | 5.80 | 186 | **4.22** | 119 | +0.310 |
| no filter | 4.24 | 230 | **4.14** | 163 | +0.236 |

Positive in every five-year block. Sector-neutrality *raises* t in old data
(2.22 → 3.48), so composition was noise, not signal.

## 2. Frozen specification

**Universe**, at each month-end on settled data (`is_final=1`):
- `ADV60 >= Rp 1,000,000,000`, `close >= Rp 50`, >= 60 sessions of history,
  `volume > 0` on the formation date
- **zero zero-volume sessions in the trailing 60** (strict filter — the
  conservative choice; relaxing it strengthened the result in-sample, so the
  strict version is the harder test)

**Signal:** within **each sector**, drop the top decile by Parkinson-60 volatility.
Hold everything else, equal weighted. Sectors with fewer than 10 eligible names
are held whole.

**Rebalance:** monthly, first session after month-end, **not at the open** (that
window carries ~78% wider effective spread and 2.4x the dispersion).

**Costs:** 0.60% round trip on realised turnover. In-sample overlay turnover is
~9.1%/mo one-way.

**Measured as an OVERLAY**, not a standalone book: the endpoint is the return of
the excluded-tail book minus the return of the same universe unexcluded. This is
what the evidence measures and what the forward test must measure.

## 3. Endpoint and decision rule

**Primary endpoint:** monthly overlay increment, recorded per month, never pooled
across amendments.

- **24 months:** interim only, no decision.
- **36 months:** PROMOTE requires accumulated t > 2.5 **and** a positive
  cumulative increment.
- **60 months:** final. PROMOTE requires t > 3.0.

Thresholds sit below the in-sample 3.57 deliberately: forward evidence carries no
multiplicity penalty because the spec is frozen before observation.

**REJECT** at any decision point if the cumulative increment is below zero.

## 4. Expectations, stated in advance

In-sample and out-of-sample both give **+0.24 to +0.31%/mo** (~+3.0 to +3.7%/yr).
If the forward increment runs materially below ~+0.10%/mo over 36 months, the
effect has decayed or the in-sample estimate was optimistic, and this should be
rejected.

## 5. Forbidden

- Changing universe, sector definition, exclusion decile, rebalance date or cost
  model after opening. Any change closes this spec and opens a successor; results
  either side are never pooled (the 001→002 precedent).
- Reading the ledger to decide anything before 36 months.
- Converting the overlay into a standalone long book and judging it on absolute
  return — that is a different claim with different evidence.

## 6. Limitations

1. **This is an overlay increment (~+3.0-3.7%/yr), not a strategy.** It improves
   a book; it is not one. Absolute performance depends entirely on the underlying
   book, which over 2021-2026 lost money.
2. **Not investable by an IDX80 mandate.** Inside the index the overlay is
   −0.32%/mo; the edge lives outside it, concentrated in the mid-ADV tercile.
3. **Pre-2021 evidence rests on a thinner, cleaner subset.** Zero-volume rates run
   24-43% in 2003-09 against ~5% now, so the strict filter admits 76 of ~200
   pre-2021 months, and that subset is more liquid than the modern panel.
4. **Survivorship** ~1.0-1.7%/yr attrition, conservative in direction for this
   construction but not zero.
5. **Capacity unmeasured** for the sector-neutral variant at the mid-ADV band.
6. **Breadth:** needs ~100+ names. IR falls from 1.14 at N=200 to 0.39 at N=10.

## 7. What registration would require (owner decision)

- A family determination under PG-3/D-028. Volatility exclusion is not a
  price-trend feature, so this likely opens a **new family** rather than widening
  `Price-Trend {T1}` — a one-way door.
- A multiplicity declaration covering the ~140 in-sample trials, **with the
  argument that pre-2021 evidence is unpenalised** recorded explicitly.
- A `HYPOTHESIS_REGISTRY` entry and an evidence receipt.

**Inert until then.**
