# RC-0001-MAX — dry-run findings, 2026-09-24

**Authority:** point-in-time record, generated after the first D-055 dry run. It is superseded, not
edited. No MAX value and no signal-to-return relation was computed at any point. The diagnostics used
the pre-2021 backfill only: calendar structure, traded counts, price continuity at split dates, and
return dispersion under **random** bucket assignment.

## 1. What the dry run showed (Owner's machine, 03:49 UTC)

- **Headline counts:** 317 formations, 215 valid, median universe 134. All four no-return checks
  (LA-1, ZV-1, ID-1, FILL-1) passed.
- **Skipped months:**
  - 2000–2009: the universe is below 50 names. This is real — the Rp 1 bn nominal floor admits few
    names then, and none through the 2008-08..2009-03 crash, so those months are censored.
  - 2011–2019: a scattered set of months, not explained by the universe floor. They are the finding.

## 2. Three data defects, all in the pre-2021 backfill

| code | defect | evidence | fix (framework, tested) |
|---|---|---|---|
| **ZV-2** | yfinance prints IDX holidays and vendor gaps as rows for every ticker: zero volume, unchanged price. | 197 of 5,332 dates, e.g. Lebaran 2017-06-26..30, 2017-06-01, 2018-03-30, 2018-12-31, 2019-01-01, and 2016-04-13..19 (0 names traded). These became formation or entry "sessions" with no trading. They also filled every name's 20-day traded window, which emptied the universe for weeks: 2018-06 and 2019-04 had 0 eligible names. | `engine.non_session_dates`: a date is dropped only if traded names < 50% of the prior-60-date median **and** < 20% of prices moved. It is prefix-invariant. A real session with a volume hole is kept. |
| **DATA-1** | **Double split adjustment.** yfinance `history(auto_adjust=False)` already split-adjusts OHLC (`auto_adjust` only covers dividends). The D-053 loader (`remeasure_v2.split_adjust`, which the first `data.py` replicated) applied `split_hist.pkl` again. | Of the 197 pre-2021 events, all 165 with ratio ≥ 1.5 are continuous in the raw backfill. The second pass created fake jumps: HMSP 2016-06 +2,404%, ASII 2012-06 +989%, MYOR +2,277%, and more. The σ of holding returns fell from 76.4% to 16.6% after the DATA-1 and DATA-2 fixes. | `data.adjust_unadjusted_splits` adjusts an event only when the raw prices show the jump; the audit is attached to the panel. |
| **DATA-2** | Isolated vendor scale glitches: bars printed at about 1/10 or 10× their neighbours. | MAPI and TOWR, 2018-03..05. MAPI alternates 825 → 82.25 → 815 → 80.5, giving "monthly returns" of +924% and +322%. 55 bars in all. | `data.drop_scale_glitches`: drops a backfill bar that is more than 3× off its 5-bar median. No IDX price band allows a 3× move in one session. Backfill only; each dropped bar is listed. |

After the fixes, the backfill-only structure has more valid months: 183 pre-2021 months, against 170
before the glitch and split fixes.

## 3. Implication for existing records — descriptive only, not acted on

- **D-053 VOLEX-SN re-measurement.** It read the same backfill through the same double-adjusting
  loader. Its `RESULT.json` records 38 holdings with a > 35% session move, spread over 29 of the 88
  gating months. Those 29 months average +0.197%/mo, against +0.087%/mo for the other 59. The verdict
  (FAILS, t 1.39 vs 2.87) was not flattered in mean by the defect, but its input is defective.
  D-053 forbids a re-cut. Whether to record a data-defect correction against it is an **Owner call**.
- **Other pre-2021 work.** Any panel built with the same `split_adjust` over this backfill probably
  carries DATA-1. That includes `data_gaps/EXTENDED_PANEL_RESULT_2026-09-19.md` and the VOLEX-001
  backtest reference. **Not audited here.**

## 4. Power — the card is underpowered at haircut 0.5

The σ in the card (3.47%/mo) comes from a paper that sorted every IDX stock, roughly 40 names per
decile. Our liquid universe gives deciles of about 12–15 names. The **noise floor** is the σ of the
top-minus-bottom spread when buckets are assigned at random. It carries no signal information and is
a lower bound on the real σ. Measured on the corrected backfill (6 random draws):

| ADV floor | median universe | decile σ | quintile σ | pre-2021 months |
|---|---|---|---|---|
| Rp 1,000 m (card) | 125 | 6.58 | 4.63 | 183 |
| Rp 500 m | 140 | 6.32 | 4.36 | 193 |
| Rp 250 m | 154 | 6.13 | 4.32 | 201 |
| Rp 100 m | 172 | 6.03 | 4.11 | 208 |

**How much effect is needed:**
- With N ≈ 245 months (≈183 backfill + ≈61 DB), 80% power at t* = 2 needs a true decile spread of
  about **1.18%/mo**, or about 0.84%/mo for quintiles.
- The card plans 1.6 × 0.5 = **0.80**, so it is **underpowered**. It would need a haircut of ≥ 0.74,
  meaning almost no decay from the published figure.
- Lowering the liquidity floor barely helps. The backfill covers 772 tickers, so breadth is capped by
  the data, not by the floor.

**Structural reading.** A monthly cross-sectional sort on the liquid IDX universe can detect only
realised spreads of about 1.2%/mo (decile) or 0.85%/mo (quintile) and above. Most published anomalies
are smaller than that after decay. C2 (issuance) and C3 (52-week high) should get the same
noise-floor screen on paper before any card is written.

## 5. Proposed for the Owner (not recorded in DECISION_LOG yet)

**D-056 (draft)**, three parts:
1. Record ZV-2, DATA-1 and DATA-2 and the framework fixes.
2. Tighten R5: σ used = max(literature σ, noise floor measured by `cli power`). The noise floor is
   required at freeze.
3. Decide whether a data-defect correction is recorded against the D-053 re-measurement input,
   without reopening its spec.

**RC-0001 disposition options:**
- **(a) Record "underpowered, not tested."** No trial is consumed, and the card stays on file. This is
  the protocol's own answer.
- **(b) Owner accepts a haircut ≥ 0.74.** Not recommended: the IDX paper is a 5-year, all-stock,
  equal-weighted sample, the profile most exposed to decay.
