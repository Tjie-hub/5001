# ZCode brief: online-retail broker imbalance. G0 (2026-10-09)

**Status:** staged. **Do not start until the owner accepts the mechanism D-entry** (D-070 rule 1). The
draft is in `data_acquisition/08_RETAIL_PATHS_1_4_FEASIBILITY_2026-10-09.md`, item 1. The accepting
D-number goes here: D-___.
**Category:** Research (P-M).
- **Family:** decide at G0. The candidates are a new family, or the P-M {I5,I6,I7,I12} family if the
  mechanism is judged I5 (inventory / liquidity provision).
- **This must be argued:** FAIL-PM-0001 (I5) and FAIL-PM-0003 (I7, same dataset) are in that family.
  - Show the retail-group signal differs from both constructions: give the correlation with their
    signals, pre-outcome.
  - Show it is not FAIL-PM-0007's identity-attenuated market net.
**Branch:** `research/retail-broker-imbalance-2026-10` from `origin/ops/hardening-2026-07-10`. Use a new
worktree.

## Frozen classification (do not re-optimise)

- **Retail group R = {XL, XC, YP, PD, KK}.** Rule: BUY-side value per trade ≤ Rp 6M over the
  formation window 2025-01-02 → 2025-03-31.
  - Measured: XL 2.27M, XC 2.45M, YP 4.99M, PD 5.13M, KK 5.81M. Next is YB at 6.88M.
- **The formation window is excluded from every test.** The test starts 2025-04-01.
- **Caveat:** bank-owned retail brokers (CC, NI, …) aren't in R. The signal is *online*-retail imbalance.

## Data

- **Sources:**
  - `broker_flow` in a pinned snapshot: ~96 names before 2026-04, ~830 after.
  - The research-side breadth backfill `~/idx_external/broker_flow/data/*.jsonl`: 764 tickers,
    2025-01-02 → 2026-03-31.
    - Built by `backfill.py` (read-only Stockbit, `fetch_broker_flow(date=…)`).
    - Error lines (`fetch_failed`, `date_mismatch`) are gaps. Never fill them.
- **Vendor limit:** the vendor returns the **top 25 brokers per side**. A retail broker outside the top 25
  is missing, not zero.
  - Report the share of stock-days where each R broker is absent. Freeze how absence is treated.
- **Signal:** `RI(i,w)` = Σ R net value / Σ all-broker gross value, for stock i in week w.
- **Volume basis:** broker lots are regular-market only, so the 2026-07-06 break doesn't apply.
  Liquidity floors use adv_regular (pending D-081).

## Arm (pre-declare the sign)

- **One primary arm:** weekly Fama-MacBeth sort on RI.
  - Score: next 1-week and 4-week excess return of the top vs bottom quintile, net of `cost_realised`.
- **Predicted sign (D-entry):** negative (liquidity-provision reward). A positive result is not a rescue:
  the D-entry names one sign.
- **Controls:** size, Parkinson-60, 1-week reversal, the foreign net (Asing) imbalance.
- **Bar:** N = the census at G0 + 1.
- **Power:** about 76 test weeks in the liquid panel and ~26 weeks broad. Report the MDE honestly.
  If power is below 50% at the bar, apply a stop rule: record only, with no G1.

## G0 deliverables

- `PREDECLARATION.md` + sha256
- `CENSUS_G0.json`: R coverage by week, absence rates, distinctness correlations
- power, `REGISTRATION_DRAFT.md`, `HANDOFF_G0.md`

No returns read. Push and STOP.
