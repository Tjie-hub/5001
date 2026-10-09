# PREDECLARATION: online-retail broker imbalance {RF}, B1 on the liquid panel. G0 freeze (stop rule FIRED)

**Status:** frozen before any outcome is read · **Date:** 2026-10-09
**Authority:** **D-086** (owner: "accept path 1, run it on the 96-name panel"). The study is run by the
planner.
**Branch:** `research/retail-broker-imbalance-2026-10` from hardening `f434f4b`.
**Sidecar:** `PREDECLARATION.sha256` covers this file, `flow.py`, `outcomes.py`, `g0_census.py`,
`test_pit_flow.py`, and the verbatim copies `ownership.py` (856afe18…, from b7f84ac) and
`cost_realised.py` (65051253…).

## 1. Question and sign

Is online-retail net order flow absorbed at a profit? The prediction is that retail net buying in week
w is followed by lower returns in week w+1:
`S1 = EW(Q1, lowest RI) − EW(Q5) > 0`.

## 2. Data (frozen)

- **Panel:** the 98 names with `broker_flow` rows on or before 2025-03-31 (the continuous liquid
  panel). Snapshots: walkforward `a2d7e675…`, history_long `7d298068…`.
- **Retail group:** R = {XL, XC, YP, PD, KK}, by value per trade ≤ Rp 6M over 2025-01-02 → 03-31. That
  formation window feeds no signal.
- **Signal:** `RI = Σ_R net value / Σ |net value|` over all reported brokers in the formation week,
  with ≥ min(3, week length) sessions of data.
  - The vendor lists the top 25 per side, and an absent R broker counts as 0.
  - The mean R presence is 99.3%, so the cap barely binds.
- **Universe at the week's last session:**
  - has a price bar and broker data
  - ADV20 ≥ Rp 1bn on the D-081 basis
  - close ≥ 50
  - has a Parkinson-60 value

## 3. Tests (would apply at G1)

1. **Strength:** mean weekly gross S1 > 0 and NW t (4 lags) ≥ **3.2991**.
   - N = 612: the census of 611 after D-085, + 1.
2. **Both halves > 0:** formations ≤ 2025-12-31 (38 weeks) and later (38).
3. **Incremental:** a weekly Fama-MacBeth regression with z(RI), z(foreign imbalance), z(formation-week
   return), z(log ADV) and z(Parkinson-60). The RI coefficient must have mean < 0 and NW t ≤ −2.
4. **Tradeability:** non-overlapping 4-week blocks (18 spreads), net of `cost_realised` × turnover.
   Mean net > 0.

## 4. Stop rule (frozen before power was computed)

If the power to detect a **0.30% a week** gross spread at the bar is below **20%**, G1 does not run.

## 5. Census result (CENSUS_G0.json)

- 76 testable weeks (2025-04-11 → 2026-09-18). The median universe is 91 names, with 18 per quintile.
- **Data gap:** in week 2026-07-24 no panel name has a price bar on its last session (a gap in
  `history_long`). That week's universe is 0.
- **Pre-outcome distinctness:**

  | RI against | Spearman |
  |---|---|
  | foreign imbalance | −0.369 |
  | formation-week return | −0.358 |

  Retail buys losers and takes the other side of foreigners. That is why both are controls.
- **Power:** the pre-sample random weekly spread (2023–2024, 102 weeks, the same names) has σ 1.819%.
  - MDE 0.86% a week.
  - **Power at 0.30% a week: 3.1%.**
- **STOP RULE FIRED. No G1.** `outcomes.py` is frozen but has never been run. No G1 runner is shipped.

## 6. Owner options

- **(a) Recommended:** leave the study **unregistered**. A G0 that stopped before registration is
  WITHDRAWN (pre-registration, uncounted), so the census stays at 611.
  - Re-run the design on the breadth panel once the backfill (764 names, 2025-01 → 2026-03) completes.
  - Legs of about 160 names should cut σ by about 3×, which puts a 0.30% a week effect within reach.
  - That is a new G0 under D-086's mechanism.
- **(b)** Register B1 as dormant (the D-080 precedent): counted, census 612, with no G1.
- **(c)** Override and run G1 anyway. A NULL at 3% power is zero evidence (rule R2), so this is not
  recommended.
