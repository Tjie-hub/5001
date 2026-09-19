# Gap 2 Closed: Pre-2021 Price History — and the survivorship fear was overstated

**Date:** 2026-09-19 · **Script:** `scripts/fetch_history.py` ·
**Metadata:** `data/hist_meta.pkl` (first/last/count per ticker)
**Bulk data not committed:** 1,414,611 rows, 73MB raw / 12.6MB gzipped. The script
is deterministic against a public source, so the panel is regenerable; committing
a 12MB binary to carry it is the wrong trade.

## 1. What was acquired

780 tickers queried, **8 failures**, **1,414,611 daily bars before 2021-07-05**
across **541 tickers**. Depth reaches 2005 for the oldest names.

## 2. The survivorship measurement — and a correction

The raw "visible vs listed" ratio conflates two different things, because the
research panel is itself a **liquidity subset** of all listed firms. Decomposing:
the panel covers **80.6%** of today's listed universe by construction, so true
survivorship is `visible(Y) / (0.806 x listed(Y))`.

| cohort | visible | IDX listed | **survivorship to today** | implied attrition/yr |
|---|---|---|---|---|
| 2018 | 436 | 619 | **87.3%** | 1.68% |
| 2019 | 480 | 668 | 89.1% | 1.64% |
| 2020 | 523 | 713 | 91.0% | 1.57% |
| 2021 | 572 | 766 | 92.6% | 1.53% |
| 2023 | 706 | 903 | 96.9% | 1.03% |

**Attrition is ~1.0–1.7%/yr**, far milder than assumed. IDX grew 619 → 956 between
2018 and 2025 overwhelmingly by IPO, not by churn.

### The direction of the bias was stated backwards, and is corrected here

`POWER_CEILING_2026-09-19.md` §3 claims a survivor-only backfill "would likely
make the volatility overlay look **better** than it is, which is the worst
possible failure mode". **That is wrong.**

The overlay's edge is `kept − universe`. Dead names are disproportionately
high-volatility and poor-performing, so they sit mostly in the **excluded** decile
and in the universe mean. Removing them **raises** the universe mean while leaving
the kept book largely intact, which **shrinks** the measured edge. Survivorship is
therefore **conservative** for this construction, not inflationary.

The empirical check agrees: on 2021–26, where dead names *are* observable, the
overlay reads +0.226%/mo on the full panel against +0.223%/mo survivors-only —
a 0.003pp difference on 2.14% dead names.

## 3. What extending the sample would buy

`t = Sharpe × √years`, at the best measured Sharpe of 0.94:

| panel | years | names | t | vs bar 3.57 |
|---|---|---|---|---|
| current | 4.8 | 780 | 2.06 | short 1.51 |
| to 2018 | 8.7 | 436 | 2.77 | short 0.80 |
| to 2015 | 11.7 | 350 | 3.22 | short 0.35 |
| **to 2010** | **16.7** | **260** | **3.84** | **CLEARS** |
| to 2005 | 21.7 | 193 | 4.38 | CLEARS |

**A 2010 start clears the multiplicity-corrected bar.** 260 names is above the
~125 breadth floor established in the volatility work, though well below current.

**These are not results.** They assume the same Sharpe holds in older data, which
is an assumption and precisely what the extended panel exists to test. The 2008
crisis, the 2013 taper tantrum and the 2015 commodity collapse are all regimes
this program has never seen.

## 4. Consequence

The in-sample search was closed on the grounds that no specification could reach
significance and the only remaining path was a multi-year forward test. **That
conclusion needs revising:** extending the panel to 2010 is a third path, it is
now shown to be feasible, and its principal objection — survivorship — is both
smaller than assumed and pointed in the conservative direction.

Next step is not another search. It is to **rebuild the factor panel on the
extended history and re-run the surviving candidates**: the volatility overlay
(sector-neutral, per Gap 1) and the dividend book (which Gap 1 showed is ~61%
sector composition and must be re-tested sector-neutral before it is trusted).
