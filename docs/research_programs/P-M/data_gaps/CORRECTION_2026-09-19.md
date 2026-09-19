# Correction: `corporate_actions` is NOT missing 2.8% of dividends

**Date:** 2026-09-19 · Corrects commit `c5469ec` and the claim repeated in
session summary.

## The claim that was wrong

Commit `c5469ec` states:

> "corporate_actions is MISSING 496 dividend events (2.8%) that the yfinance
> history has, strictly one-directional... The production table is incomplete."

**That is false.** Within the table's own coverage window (2021-07-05 onward)
`corporate_actions` holds **2,070** dividend events against yfinance's **1,803**
— the DB has *more*, not fewer. Only **52** events are genuinely absent, all
dated 2026, consistent with ordinary fetch lag rather than a defect.

## What actually caused the discrepancy

The 496 "missing" rows were **name-months**, not dividend events, and they were an
artefact of my own feature construction.

`corporate_actions` begins 2021-07-05. A trailing-12-month dividend computed from
it is **truncated** for every formation date in the panel's first year, because
the lookback window reaches back before the table exists. `div_hist` reaches to
2000 and therefore sees those dividends.

Evidence:

| check | result |
|---|---|
| disagreements in the first 12 months (≤ 2022-07) | **518 of 541 (96%)** |
| restricted to formation dates ≥ 2022-07 | **23 of 16,345 (0.14%)** |
| correlation of the two yield series, ≥ 2022-07 | **+0.9992** |

The two sources agree almost exactly once both have a full lookback available.

## Consequence for the dividend result

The Gap 1 sector-neutral dividend figure (+0.353%/mo, t 1.03) was computed on a
panel whose **first 12 months carried a truncated dividend lookback**, which
understated yield for those months. The extended panel, which has full lookback
throughout, gives t 1.79 for the same 2021-26 window.

**The verdict is unchanged** — sector-neutral dividend yield reads t 1.79
(2021-26), 2.53 (pre-2021) and 3.36 (full 26y), all below the 3.57 bar. But the
*reason* the two panels disagreed is now correctly attributed to my window
handling rather than to production data quality.

## Two real, smaller issues that remain

1. **52 dividend events from 2026 are absent** from `corporate_actions`. Minor
   and consistent with fetch lag, but worth a backfill.
2. **`data/fetcher.py::_save_actions` swallows every exception** (`except:
   pass`) and can only capture dividends that land on a fetched OHLCV row. Any
   dividend whose ex-date has no saved bar is silently lost — 4 of the 52 fit
   that pattern. The silence is the defect more than the gap.

## Lesson

A trailing-window feature computed at the left edge of a data source is truncated,
not zero. Any panel built this way needs either a warm-up exclusion or a source
whose history predates the panel. I did not apply that check, and it produced a
false accusation against a production table.
