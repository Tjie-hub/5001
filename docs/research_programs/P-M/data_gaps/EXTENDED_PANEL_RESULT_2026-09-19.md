# Extended Panel: the volatility overlay clears the bar, out-of-sample

**Date:** 2026-09-19 · **Scripts:** `scripts/{ext_panel,ext_test}.py`
**Panel:** 43,136 name-months, 295 months, 780 tickers, 2000-07 → 2026-07

## 0. Result

The volatility tail-exclusion overlay, **sector-neutral** and tradeability-
conditioned, is **statistically significant out-of-sample** on 16 years of data
that were used in none of the ~140 in-sample trials.

| tradeability filter | FULL t | mo | **PRE-2021 t** | mo | effect %/mo |
|---|---|---|---|---|---|
| clean: 0 zero-vol in 60 | 4.70 | 143 | **3.48** | 76 | +0.254 |
| ≤3 zero-vol in 60 | 5.34 | 177 | **4.07** | 110 | +0.276 |
| ≤6 zero-vol in 60 | 5.37 | 181 | **3.95** | 114 | +0.286 |
| forward-only | 5.80 | 186 | **4.22** | 119 | +0.310 |
| no filter | 4.24 | 230 | **4.14** | 163 | +0.236 |

Multiplicity bar: **t = 3.57** at 140 trials, 3.66 at 200. Every full-panel
specification clears it; four of five clear it on pre-2021 alone.

**Why the out-of-sample column is the one that counts.** The multiplicity penalty
exists because ~140 specifications were searched *on 2021-2026 data*. Pre-2021
data entered none of them. It is therefore a genuinely unpenalised test, and it
returns an effect size (+0.274 to +0.308%/mo) statistically indistinguishable
from in-sample (+0.201 to +0.275).

## 1. Era stability

| window | pooled | t | sector-neutral | t | months |
|---|---|---|---|---|---|
| FULL 2000-2026 | +0.289 | 3.73 | **+0.254** | **4.70** | 143 |
| 2010-2026 | +0.303 | 4.15 | +0.263 | 4.81 | 134 |
| **PRE-2021 (unseen)** | +0.301 | 2.22 | **+0.300** | **3.48** | 76 |
| 2010-2020 (unseen) | +0.331 | 2.49 | +0.325 | 3.58 | 67 |
| 2021-2026 (known) | +0.275 | 4.42 | +0.201 | 3.31 | 67 |

Positive in every 5-year block: 2010-14 +0.457 (t 3.53), 2015-19 +0.335 (t 1.28),
2020-24 +0.205 (t 1.84), 2025+ +0.288 (t 2.29). **Sector-neutrality raises t in
the old data** (2.22 → 3.48), i.e. sector composition was adding noise, not signal.

## 2. How the panel was built, and three bugs caught building it

- 1,414,611 pre-2021 bars merged with the settled corpus → 2,501,806 bars.
- **Splits:** 279 events on 202 tickers. Applied to the **pre-2021 rows only** —
  the DB corpus is already back-adjusted (verified: no price jump at BBCA/HEAL/
  GOOD split dates), so adjusting the whole series would have double-counted
  every post-2021 split.
- **Dividends NOT re-adjusted.** Verified on 54 splits with dividends either
  side: observed pre/post DPS ratio median 0.70 against a median split ratio of
  3.66, correlation −0.099. The source already adjusts them; adjusting again
  would have inflated pre-split yields precisely on the oldest data.
- **A phantom `pgrep` match** stalled the split fetch for 37 minutes: the shell
  that *wrote* the script matched `pgrep -f fetch_div_hist` from its own heredoc.
  Third instance of this class in this session.

## 3. What this does NOT establish

1. **Economic sufficiency.** This is an **overlay increment** of ~+3.0 to
   +3.7%/yr, not a standalone strategy return. It improves a book; it is not one.
2. **The hedged Sharpe-0.94 construction is not validated.** That book leaned on
   dividend yield, which Gap 1 showed is ~61% sector composition. Only the
   volatility component is confirmed here.
3. **Pre-2021 data is materially thinner and dirtier.** Zero-volume rates run
   24-43% in 2003-09 and 17-22% in 2014-18 against ~5% post-2021; median volume
   reads 400 in 2006. The strict filter therefore admits only 76 of ~200 pre-2021
   months, and that subset is more liquid and more continuously traded than the
   modern panel. The result is robust to relaxing the filter (t 3.48 → 4.22), but
   the samples are not the same population.
4. **Survivorship** remains (~1.0-1.7%/yr attrition) though it is conservative
   in direction for this construction.
5. **Capacity** at the mid-ADV band where the edge concentrates is unmeasured
   for the sector-neutral variant.

## 4. Dividend yield on the extended panel — unresolved

Sector-neutral it reads +1.49%/mo (t 3.36) full-panel and +1.92%/mo (t 2.53)
pre-2021 — much stronger than the +0.353%/mo (t 1.03) measured on the 5-year
panel in Gap 1. The two panels use different dividend sources (`div_hist` vs
`corporate_actions`) and differ by 7 months of coverage. **That discrepancy is
not explained and the dividend result should not be relied on until it is.**
Outlier capping is not the cause: capping yields at 50% raises t to 3.73.

## 5. Consequence

`POWER_CEILING_2026-09-19.md` concluded that no route to significance existed on
available data and only a multi-year forward test remained. **That conclusion is
now superseded.** Extending the sample was the third path, it worked, and the
volatility overlay is the first result in this program to clear a
multiplicity-corrected bar on data it was not fitted to.

The candidate for forward testing should therefore be the **volatility overlay,
sector-neutral** — not the dividend book in `forward_dividend/PROTOCOL_DRAFT.md`,
whose signal is substantially sector composition and whose extended-panel
behaviour is unexplained.
