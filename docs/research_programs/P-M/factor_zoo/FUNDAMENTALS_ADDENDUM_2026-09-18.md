# Addendum — Fundamental Data Acquired, and It Does Not Help

**Date:** 2026-09-18 · Follows `FINDINGS_2026-09-18.md` (commit 26f1048)
**Scripts:** `scripts/{fetch_fund,fund_factors,fund_sweep,combo}.py` · **Raw:** `data/*.pkl`

The parent document named a historical fundamentals panel as "the single
highest-value data acquisition". It was acquired. **It does not produce an edge,
and it makes the best price/volume book worse.**

## 1. What was acquired

Yahoo Finance, 780 tickers, **0 failures**:

| artefact | rows | tickers | span |
|---|---|---|---|
| `fund_shares.pkl` — historical shares outstanding | 132,230 | 780 | 2020-06 → 2026-07 |
| `fund_annual.pkl` — annual balance sheet + income | 2,217 | 552 | FY2021 → FY2026-06 |

Merged onto the monthly panel: **size 99.9%** coverage (shares × close → market
cap), **value/quality ~52.6%**.

Nothing was written to the production database. New production data needs its own
table, fetcher and fence review; this is research scratch stored as files.

## 2. Point-in-time treatment, and its limit

IDX requires audited annuals within 90 days of year-end, so FY(Y) is public by
~31 March of Y+1. A deliberately conservative **6-month lag** is applied: FY(Y)
becomes usable only from **1 July of Y+1**. Merging on period-end dates would be
look-ahead and would manufacture a value factor out of nothing.

Resulting staleness: **median 363 days**, p90 514. With annual reporting plus the
lag, each factor is constant for ~12 months at a time, so decile membership barely
moves within a year. That is a real power limitation, not a bug.

**Unfixable limitation, stated rather than buried:** Yahoo serves **restated**
financials, not point-in-time originals. A company that restated FY2022 in 2024
shows the restated figure today. This biases toward cleaner numbers than anyone
could have traded on, and correcting it requires a vendor PIT database.

## 3. Result — every classic factor is null

Top/bottom decile excess over the equal-weight universe, monthly:

| factor | TOP mean | t | TOP median | t | BOT mean | t | BOT median | t |
|---|---|---|---|---|---|---|---|---|
| **btm** (value) | −0.42 | −0.57 | +0.45 | 0.91 | +0.92 | 1.07 | +0.49 | 0.75 |
| **roe** (quality) | +0.56 | 0.90 | +0.23 | 0.55 | +0.47 | 0.54 | −1.00 | −1.67 |
| **gp_assets** (profitability) | −0.55 | −0.62 | +0.20 | 0.30 | +1.02 | 1.00 | +0.10 | 0.13 |
| **earn_yield** | −0.32 | −0.49 | +0.85 | 1.64 | +0.26 | 0.28 | −1.03 | −1.82 |
| **ag** (investment) | +0.87 | 1.10 | −0.04 | −0.05 | +0.10 | 0.10 | −0.70 | −1.13 |
| sales_p | +0.25 | 0.39 | +0.09 | 0.28 | +1.58 | 1.69 | +1.31 | 1.66 |
| leverage | +0.04 | 0.07 | −0.13 | −0.41 | −0.13 | −0.25 | +0.03 | 0.08 |
| op_assets | −0.09 | −0.10 | +0.55 | 0.90 | +0.84 | 0.84 | −0.38 | −0.52 |
| **size** | −0.57 | −1.52 | **+0.67** | **2.21** | +0.57 | 0.86 | **−0.91** | **−2.04** |

**Value, quality, profitability and investment are all null on both mean and
median.** Not one clears |t| > 2 on either measure.

**Size is the only factor with a signal, and it is REVERSED.** Large caps beat
small caps on the median (+0.67, t 2.21; smallest decile −0.91, t −2.04) — the
opposite of the classic size premium. Note the sign flips between mean and median,
exactly the lottery pathology documented in the parent findings: small caps have
the better *mean* (tail-driven) and the worse *median*. It is also era-dependent:
2021-23 t 2.87 → 2024-26 t 0.57 (ex-2025 t 2.71).

## 4. Fundamentals make the best book worse

Applied as screens to hi52 top-20% + vol-exclusion (baseline **+13.67%/yr**,
t 1.44, ex-2025 +2.08%):

| screen | ALL %/yr | t | EX-2025 %/yr |
|---|---|---|---|
| *(baseline, no screen)* | **+13.67** | 1.44 | +2.08 |
| & btm above median | −1.17 | 0.11 | −11.78 |
| & btm top half + roe>0 | −0.37 | 0.17 | −8.63 |
| & roe above median | +1.41 | 0.31 | −13.15 |
| & gp/assets above median | +4.40 | 0.51 | −14.87 |
| & earn_yield above median | +1.38 | 0.30 | −6.47 |
| & size above median | +8.73 | 0.98 | −2.96 |
| & size below median | +20.46 | 1.78 | +8.58 |

Every value/quality screen **destroys** the book. The only improvement is *small*
size — which is re-admitting the lottery tail, not adding fundamental information,
and still fails at t 1.78.

Fundamental-only books (top 20% + vol-exclusion, ~46-51 names) are all negative:
btm **−6.70%/yr**, roe −3.85%, gp_assets −4.50%, earn_yield −5.67%, every Sharpe
below zero.

## 5. Caveats that cut both ways

- Coverage is 52.6%, so value/quality tests run on ~170 names per month and only
  **37 months** have usable breadth (size has 59).
- Annual granularity + 6-month lag means ~4-5 distinct observations per ticker
  across the sample. Power against a slow-moving factor is genuinely limited, and
  a null here is weaker evidence than a null on a monthly-varying signal.
- Restatement bias (§2) should, if anything, *flatter* value and quality. It does
  not.
- Screened books fall to 23-29 names, below the breadth threshold established in
  the volatility work (IR 0.39 at N=10 vs 1.14 at N=200), so those rows are
  directionally indicative rather than decisive. The fundamental-only books are
  not affected by this — they hold 46-51 names.

## 6. What this settles

The parent document's highest-priority data gap is **closed**. Fundamentals were
the main untested factor family, and on 5 years of IDX data they do not deliver.
The remaining gap is a ticker→sector map, which is cheap and unlocks a risk
control rather than a new alpha source.

**No revision to the parent conclusion.** The only surviving signal is still
52-week-high proximity with the volatility tail excluded, it still fails the
multiplicity bar, and its absolute return is still 2025-dependent. Acquiring
fundamentals did not change that — which is itself the most decision-relevant
result here, because it removes the main reason to keep searching.
