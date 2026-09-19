# The Binding Constraint Is the Sample, Not the Search

**Date:** 2026-09-19 · **Scripts:** `scripts/composite_*.py`
**Conclusion:** no strategy of the effect size available on IDX can be established
at conventional significance with 5 years of monthly data. Further searching has
**negative** expected value.

## 1. The composite attempt, and why it failed

Standard practice when single factors are weak is to combine independent ones.
Rank correlations among the survivors were encouraging (0.11–0.48), so a
composite was built. It made things **worse at every step**:

| book | NET %/yr | t |
|---|---|---|
| dividend yield only | **+6.26** | 1.09 |
| + low-vol | +3.92 | 0.83 |
| + hi52 | +2.66 | 0.61 |
| all four | +2.06 | 0.50 |

The cause was already on record and I failed to apply it: **low volatility works
as an exclusion, not as a ranking signal.** As a standalone selection it returns
+0.32%/yr (t 0.19), reproducing the earlier "concentrated low-vol selection does
NOT work; only tail-exclusion works". Compositing a working signal with a
non-working one dilutes it. The correct construction remains rank-by-yield,
exclude-the-vol-tail.

Concentration and holding-period sweeps did not rescue it (top-10% +5.12%,
3-month hold +3.63% at t 0.96, though the 3-month hold does halve drawdown to
−11.1%).

## 2. The arithmetic that ends the search

Best book (dividend top-20% + vol-exclusion), monthly net series:

```
n = 57 months      mean +0.766%/mo      sd 4.246      t = 1.36
annualised Sharpe 0.63
```

| requirement | value |
|---|---|
| multiplicity-corrected bar (~140 trials) | **t = 3.57** |
| months needed at the observed effect size | **391 (32.6 years)** |
| months available | **57 (4.8 years)** |
| shortfall | 334 months |
| effect size needed instead, at n=57 | +2.01%/mo = **+24.1%/yr net** |
| months needed even at an *uncorrected* t = 2.0 | 123 (10.2 years) |

Nothing tested in this program produced anything within range of +24%/yr net.
**The sample cannot support the claim, regardless of which strategy is tested.**

This also means further search is not neutral but harmful: each new spec raises
the multiplicity bar while leaving the evidence unchanged.

## 3. Can the sample be extended? Partly — at a cost that may be worse

Price history is available far beyond the database's 2021-07 start: BBCA to 2004,
ASII and INDF to 2000, IHSG to 1990. On a 30-ticker stratified probe of current
names, **50% have history to ≤2010** and the median first year is **2011**. A
backfill would roughly triple the sample and bring the uncorrected bar within reach.

**But the source can only be queried for tickers that exist today.** Every IDX
name delisted between 2005 and 2021 is invisible. Extending history this way
trades a sample-size problem for a **survivorship problem**, and over a 20-year
window that bias is large and one-directional: dead names are disproportionately
high-volatility, low-priced and poor-performing — precisely the cohort that every
result in this program turns on (the volatility overlay *is* a bet on that cohort
underperforming).

A survivorship-contaminated 20-year panel would likely make the volatility
overlay look **better** than it is, which is the worst possible failure mode here.

## 4. What this leaves

Three honest options, in order of evidentiary quality:

1. **Forward test the dividend book.** The only clean path. It has the right
   shape — +7.07%/yr net, turnover 0.16/mo, maxDD −18.6%, 80 names, passes the
   median test, size-neutral, ex-date verified, economically sensible. Accruing
   out-of-sample months is the only way its t rises without inflating the trial
   count. Cost: years.
2. **Buy a point-in-time vendor panel** with delisted names included. This is the
   only way to extend history without survivorship contamination. Cost: money.
3. **Deploy at a lower evidentiary standard**, explicitly, with the statistics
   stated: a Sharpe-0.63 strategy whose t is 1.36 and whose ex-2025 return is
   +2.45%. That is a judgement call about risk appetite, not a research finding,
   and it should be recorded as such.

**What should not happen is more backtesting on this panel.** That is the one
option with negative expected value, and this document exists to close it off.
