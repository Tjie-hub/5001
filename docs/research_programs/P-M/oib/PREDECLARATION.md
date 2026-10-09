# PREDECLARATION: daily order-flow imbalance (OIB) continuation. P-M {I5,I6,I7,I12}, I7. G0 freeze

**Status:** frozen before any outcome is read · **Date:** 2026-10-09
**Authority:** **D-088** (owner: "accept OIB"). The study is run by the planner.
**Branch:** `research/oib-continuation-2026-10` from hardening `d14b3c6`.
**Gates:** G0 = this freeze, a counts-only census and PIT tests, then STOP. G1 = one run, gated on
`OIB_G1_APPROVED=1`, after owner approval.
**Sidecar:** `PREDECLARATION.sha256` covers this file, `oib.py`, `outcomes.py`, `g0_census.py`,
`g1_run.py`, `extract_daily.py`, `test_pit_oib.py`, and the verbatim copies `ownership.py`
(856afe18…) and `cost_realised.py` (65051253…).

## 1. Signal and prediction

- **OIB(i, t) = (B − S) / (B + S)**, where B and S are the session's final cumulative buy- and
  sell-aggressor lots: MAX over the day's minute bars, since the counters are cumulative (fix
  `47ff225`).
- A ticker-day counts only with ≥ 200 bars.
- **Prediction (I7, order-splitting continuation):** `S = EW(Q5, highest OIB) − EW(Q1) > 0` over the
  next day.

## 2. Data (frozen)

- **Daily totals:** `extract_daily.py` over the walkforward snapshot `a2d7e675…`, giving 318,398
  ticker-days (2025-01 → 2026-10).
  - Cache `~/scratch/oib_daily_2026-10-08.json`, sha256 `73a06abf…`.
- **Prices:** `history_long` `7d298068…`. Its last session is **2026-09-24**, which bounds the outcomes.
  - Total return by dividend add-back.
  - Opens are taken from the same table.
- **Universe at close t:**
  - an OIB row (≥ 200 bars)
  - ADV20 ≥ Rp 1bn on the D-081 basis
  - close ≥ 50
  - ≥ 61 bars of history
  - a Parkinson-60 value
- **Test days:** a test day needs ≥ 100 eligible names. Thin data-gap days are excluded (listed in the
  census).

## 3. Pass conditions (G1; all must hold)

1. **Strength:** mean S_cc (close t → close t+1) > 0 and NW t (5 lags) ≥ **3.2991**.
   - N = 612: the census of 611 (D-087 withdrew before registration) + 1.
2. **Both halves > 0:** formations ≤ 2025-12-31 (230 days) and later (154).
3. **Incremental:** a daily Fama-MacBeth regression with z(OIB), z(same-day return), z(log ADV) and
   z(Parkinson-60). The OIB coefficient must have mean > 0 and NW t ≥ 2.0.
   - The same-day Spearman between OIB and the return is +0.42, so continuation must not be the
     return's own momentum.
4. **Next-open entry:** mean S_oc (open t+1 → close t+1) > 0. OIB is only complete after the close, so
   the close-to-close test is the literature's mechanism test, and this condition is its tradeable
   counterpart.
5. **Tradeable block:** 5-session OIB, entry at the next open, exit at the open after the next block,
   net of `cost_realised` × turnover per leg. Mean net > 0 (76 block spreads).

**Report only:** block gross and costs, monthly means, counts. A failed condition cannot be rescued.

## 4. Stop rule (frozen before power)

- **Rule:** if power at **0.10% a day** at the bar is below **20%**, G1 does not run.
- **Power:** the pre-sample (2023–2024) random daily spread has σ 0.643% at k = 57. Scaled to k = 75,
  that is σ 0.560%.
- **Result:** MDE **0.118% a day**; **power at 0.10% a day 57.8%** (40.1% unscaled). **NOT FIRED.**

## 5. Census (CENSUS_G0.json)

- 384 testable days (2025-01-02 → 2026-09-23).
- Median universe 377 names (min 102, max 520), with 75 per quintile.
- OIB quantiles: p5 −0.59, median −0.11, p95 +0.53.
- Drops are mostly the ADV floor (166,133 name-days).

## 6. Disclosures

- **HYP-PM-0001 (FAILED F2) built its 1-minute OFI from the same cumulative counters**, so its
  instrument measured running totals. That is flagged to the owner separately and is not acted on
  here.
- This study is a different cell and horizon: I7 next-day continuation, not I5 1-minute reversal.
