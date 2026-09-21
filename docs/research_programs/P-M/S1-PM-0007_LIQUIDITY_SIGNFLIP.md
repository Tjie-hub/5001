# LIQUIDITY SIGN-FLIP — DISCOVERY RESULT

**Doc:** S1-PM-0007 · **Date:** 2026-08-25 · **Owner:** Claude · **DISCOVERY ONLY**
**Lead source:** residual recorded in `S1-PM-0006_C2C_REVERSAL_DISCOVERY.md`
**Cohort:** unchanged from `S1-PM-0005` (sha256 `c6dfd438…`) — `|r_t| >= 0.10`, consecutive
`t-1/t/t+1`, session **S2** primary. **Buckets not redefined after seeing results.**
`open` not used · no flow bars · no OFI · no `cont_k` · no registry change · `HYP-PM-0002` untouched.

---

# DECISION: **C — REJECTED**

**The sign-flip is an artifact of the exactly-zero return mass, and it does not survive the
liquidity-boundary or minimum-observation checks.**

The single number that settles it:

| UP cohort, S2 | 100k–1M | 1M–10M | >10M |
|---|---:|---:|---:|
| **P(next day > 0)** | **0.347** | **0.307** | **0.326** |
| P(next day = 0) | **0.258** | 0.257 | **0.105** |
| P(next day < 0) | 0.395 | 0.436 | **0.569** |
| mean | **+1.321%** | −0.286% | **−0.780%** |

> **The probability of going up is flat across the whole liquidity range.** What changes is that a
> quarter of low-volume next-days print **no change at all**, and that mass migrates into the
> negative column as volume rises. **Nothing reverses. Illiquid stocks stop moving.**

---

## Step 1–2 · Reconstruction and bucket detail (S2, primary)

### UP cohort (`r_t >= +0.10`), n = 8,658

| Bucket | n | tickers | mean | median | sd | P+ | P0 | P− | ticker-mean median | same-sign frac | med close | med turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1–10k | 89 | 48 | +0.734% | 0.000% | 0.102 | 0.337 | 0.247 | 0.416 | 0.000% | 0.375 | 1,595 | ~0 |
| 10k–100k | 386 | 115 | +0.787% | 0.000% | 0.105 | 0.334 | 0.218 | 0.448 | −0.489% | 0.417 | 900 | 0.04bn |
| **100k–1M** | 1,191 | 231 | **+1.321%** | 0.000% | 0.114 | 0.347 | 0.258 | 0.395 | −0.170% | 0.437 | **545** | 0.19bn |
| 1M–10M | 1,990 | 384 | −0.286% | 0.000% | 0.119 | 0.307 | 0.257 | 0.436 | −0.806% | 0.552 | 216 | 0.69bn |
| **>10M** | 5,002 | 583 | **−0.780%** | −1.818% | 0.114 | 0.326 | 0.105 | 0.569 | −1.175% | 0.630 | **182** | 17.49bn |

### DOWN cohort (`r_t <= −0.10`), n = 8,262

| Bucket | n | tickers | mean | median | sd | P+ | P0 | P− | ticker-mean median | same-sign frac | med close |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1–10k | 378 | 118 | −2.860% | −2.935% | 0.079 | 0.180 | 0.262 | 0.558 | −3.974% | 0.669 | 408 |
| 10k–100k | 692 | 226 | −1.592% | −2.840% | 0.094 | 0.324 | 0.101 | 0.575 | −2.338% | 0.646 | 266 |
| **100k–1M** | 1,610 | 368 | **−0.764%** | −0.331% | 0.103 | 0.357 | 0.142 | 0.502 | −1.435% | 0.584 | 160 |
| 1M–10M | 2,392 | 500 | −0.021% | 0.000% | 0.116 | 0.350 | 0.216 | 0.434 | −1.286% | 0.600 | 87 |
| **>10M** | 3,187 | 575 | **−0.928%** | 0.000% | 0.110 | 0.370 | 0.139 | 0.491 | −0.976% | 0.583 | 126 |

**There is no sign-flip in the DOWN cohort at all** — every bucket is negative, and the pattern is
U-shaped (−0.76%, −0.02%, −0.93%), not monotone. **The two cohorts do not share a liquidity story.**
Whatever is happening on the UP side is not a general property of liquidity.

## Step 3 · Falsification

### 3.1 · Liquidity boundaries — **FAILS, decisively**

Volume deciles *within* the liquid stratum. Boundary-free, reported in full; monotonicity is the test.

**UP, S2:**

| dec | volume range | mean | median | P+ | **P0** |
|---|---|---:|---:|---:|---:|
| 0 | 0.10–0.59M | **+1.509%** | 0.000% | 0.350 | **0.267** |
| 1 | 0.59–1.88M | +0.237% | 0.000% | 0.309 | 0.263 |
| 2 | 1.88–4.68M | −0.685% | 0.000% | 0.296 | 0.259 |
| 3 | 4.68–11.07M | **+0.144%** | 0.000% | 0.340 | 0.236 |
| 4 | 11.08–22.73M | −1.017% | −0.760% | 0.331 | 0.155 |
| 5 | 22.76–44.60M | −0.318% | −1.592% | 0.320 | 0.112 |
| 6 | 44.62–80.31M | −0.772% | −2.060% | 0.314 | 0.103 |
| 7 | 80.32–156.89M | −1.847% | −2.658% | 0.286 | 0.098 |
| 8 | 156.98–359.71M | −0.972% | −2.765% | 0.314 | 0.072 |
| **9** | **359.98M–66,011M** | **+0.177%** | −1.205% | 0.382 | **0.079** |

**The most liquid decile of all flips back positive.** The means are non-monotone throughout —
negative at dec2, positive at dec3, most negative at dec7, positive at dec9. **The "flip at >10M" is
a property of where the boundary was drawn, not of liquidity.** Had the lead been generated with a
100M boundary instead of 10M, the reported sign would have been the other way.

The **medians** are monotone (0, 0, 0, 0, −0.76%, −1.59%, −2.06%, −2.66%, −2.77%, −1.21%) — but
**P0 falls monotonically 0.267 → 0.079 across the same deciles.** The median trend *is* the zero
mass draining away. It is arithmetic, not behaviour.

**DOWN, S2:** means −1.622, −0.135, **+0.372**, −0.213, **+0.132**, −0.491, −0.042, −0.788, −1.237,
−1.850. Also non-monotone, and the **lowest**-volume decile is among the most negative — the
opposite of the UP pattern.

### 3.2 · Minimum ticker observation count — **FAILS on the UP side**

**UP / >10M** (the leg the lead was built on):

| min obs | tickers | median of ticker means | frac > 0 |
|---|---:|---:|---:|
| ≥5 | 362 | −0.850% | 0.395 |
| ≥10 | 198 | −0.528% | 0.439 |
| **≥20** | **54** | **−0.154%** | **0.481** |

**The effect decays monotonically to nothing as you require more observations per ticker.** Among
tickers that land in this cohort twenty or more times, the median effect is −0.15% and 48% are
positive. **It lives in names that appear rarely, not in names that repeatedly behave this way** —
the signature of a composition effect rather than a stable characteristic.

**UP / 100k–1M** is worse: only 86 tickers have ≥5 observations, median ticker mean +0.607%,
**frac>0 = 0.535** — a coin flip.

**DOWN / >10M is the one leg that strengthens** (≥5 → −1.636%/0.313; ≥20 → −2.999%/0.263). But that
is **down-continuation** — the short side, unexecutable on IDX — and its median close is **Rp126**,
placing it squarely in the cheap, band-adjacent population that S1-PM-0006 already flagged as
ARB-driven. **DOWN / 100k–1M inverts** under the same check (≥20 obs: **+3.010%**, frac>0 = 0.700,
n = 10 tickers).

### 3.3 · Ticker concentration — **mixed, and worst where the lead was strongest**

UP/100k–1M: **top 10 tickers = 24.3%** of observations across 231 tickers.
UP/>10M: top 10 = 7.9% across 583 · DOWN/100k–1M: 16.6% · DOWN/>10M: 11.4%.
**The positive leg of the flip is the most concentrated one.**

### 3.4 · Corporate actions — passes (not the driver)
Removing CA dates at `t` and `t+1` removes 5 / 12 / 21 / 26 rows respectively and moves every mean
by under 4 basis points.

### 3.5 · Winsorisation and outlier removal — **the positive leg is fragile**

| Cell | baseline | winsor 0.5/99.5 | trim 1/99 | drop top-5 \|r1\| |
|---|---:|---:|---:|---:|
| **UP / 100k–1M** | **+1.321%** | +1.315% | **+0.833%** | +1.251% |
| UP / >10M | −0.780% | −0.642% | −0.673% | −0.684% |
| DOWN / 100k–1M | −0.764% | −0.827% | −0.895% | −0.922% |
| DOWN / >10M | −0.928% | −1.009% | −1.082% | −0.995% |

Trimming 2% of observations cuts the positive leg by **37%** (+1.321% → +0.833%). The negative legs
are stable. **The half of the "flip" that would have to be traded long-only is the half that does not
hold up.**

### 3.6 · Regimes — the **spread** is consistent, the **flip** is not

UP cohort, mean next-day return:

| | 100k–1M | >10M | flip present? |
|---|---:|---:|---|
| S0 | +2.948% | **+1.025%** | no — both positive |
| S1 | +0.749% | **+0.170%** | no — both positive |
| **S2** | +1.321% | **−0.780%** | yes |
| S3 | +0.482% | **−1.473%** | yes |

The **ordering** (low-volume > high-volume) holds in all four regimes. The **sign flip** appears only
in S2 and S3, because the high-volume leg's own sign is regime-dependent — **+1.025% in S0 versus
−1.473% in S3.** A spread that never changes sign can only be harvested long-short, and the short
leg is unavailable.

## Step 4 · Economic plausibility

| Candidate explanation | Verdict |
|---|---|
| **Stale / discrete pricing** | **SUPPORTED — this is the main driver.** P(next = 0) runs 0.258 → 0.105 across buckets and 0.267 → 0.079 across deciles, while P(up) stays flat at 0.31–0.35. The entire mean and median gradient is the zero mass draining away as trading gets denser. |
| **Composition effect** | **SUPPORTED.** Median close is **Rp545** in 100k–1M versus **Rp182** in >10M. A *share*-volume bucket is substantially a *price-level* bucket, and median turnover differs 92× (Rp0.19bn vs Rp17.49bn). The buckets sort on at least three correlated things at once. |
| **Price-limit mechanics** | **PLAUSIBLE, unresolved.** The DOWN/>10M leg — the only one that strengthens under falsification — sits at a median close of Rp126, in the 35%/25% ARA tiers and the band-adjacent population. Separating this needs the price *level*, which back-adjustment (B-0) has corrupted. **Cannot be tested here.** |
| **Liquidity / price impact** | **NOT SUPPORTED.** A genuine price-impact story predicts a monotone gradient. The means are non-monotone and the top decile flips back positive. |
| **Adjustment artifacts** | **NOT the driver.** CA exclusion moves every mean by <4bp. |
| **A small number of names** | **PARTIALLY SUPPORTED** for the positive leg: top 10 tickers = 24.3% of observations, only 86 tickers with ≥5 obs, 53.5% of them positive. |

**No mechanism is claimed.** The two explanations the data does support — discreteness and
composition — are both measurement properties of the bucketing, not descriptions of investor
behaviour.

## Step 5 · Decision

# C — REJECTED

**The sign-flip disappears under basic falsification and the residual is an artifact.**

1. **P(up) is flat across the entire liquidity range** (0.347 / 0.307 / 0.326). Only the zero mass
   moves. No behavioural reversal is present to explain.
2. **The liquidity boundary fails.** Decile means are non-monotone and the highest decile flips back
   positive. The flip is a property of the 10M cut, not of liquidity.
3. **Minimum-observation count fails.** UP/>10M decays from −0.850% to **−0.154%** with 48% of
   tickers positive at ≥20 observations.
4. **Regime-conditional.** The high-volume leg is **+1.025% in S0** and **−1.473% in S3**.
5. **Composition confound unresolved and unresolvable here** — share-volume buckets are also price
   buckets, and the price level is corrupted by B-0.
6. **The one leg that strengthens is the short side** (DOWN/>10M), unexecutable on IDX and
   band-adjacent.
7. **The only long-only-positive leg is the fragile one** — +1.321% baseline, **+0.833% trimmed**,
   24.3% of observations in ten tickers, against a **0.60% round-trip** floor.

**No hypothesis statement and no test design are provided**, per the decision.

**What this pass did establish, and it is worth keeping:** `P(r_{t+1} == 0)` is a first-order feature
of this corpus — 26% in the low-volume stratum, 10% in the high — and **any future work on daily IDX
returns must treat the zero mass explicitly.** A mean or median compared across strata that differ in
zero-mass is comparing two different mixtures, and will manufacture spreads that are not there. This
lead was such a spread.

## Confirmations

No hypothesis registered · registry unmodified · `HYP-PM-0002` untouched · **`open` not used** ·
`stockbit_flow_bars` not queried · no OFI, no `cont_k` · no profitability optimisation · **no
threshold search and no boundary tuning** — the pre-existing buckets were used unchanged and the
decile view is boundary-free and reported in full · database `mode=ro`, unmodified.

**File created:** `S1-PM-0007_LIQUIDITY_SIGNFLIP.md`.
