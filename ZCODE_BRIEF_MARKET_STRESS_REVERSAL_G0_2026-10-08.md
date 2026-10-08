# ZCode brief: market-stress reversal (liquidity provision). G0 for HYP-PM-0019 (2026-10-08)

**Category:** Research (P-M), family **Price-Reversal {R1, R2} → {R1, R2, R3}**, widened at this
registration by formal amendment (D-028, PG-3/PG-6).
**Authority:** D-075 (mechanism accepted, owner 2026-10-08). Where this brief and D-075 disagree, D-075
wins. Raise any conflict at G0; don't resolve it silently.
**Order:** D-075 says this G0 comes **after D-073's** (dividends). You may build the G0 now, but don't push
it for approval until the D-073 G0 is approved. The census ledger then decides the bar (below).
**Branch:** create `research/market-stress-reversal-2026-10` from `origin/ops/hardening-2026-07-10` at or
after `85b5703`. Use a new worktree, and push only that branch.

## Why

Every price-only reversal on IDX has been tested and found null or negative:
- S1-PM-0006: after a ≥10% fall, the next day is down
- the 2026-09-17 pattern scan
- the exhaustion and confirmed-bottom grids
- the chart-bottom studies
- the factor-zoo short-horizon reversal
- HYP-PM-0001 and HYP-PA-0001

The literature places reversal profit in **liquidity provision to forced sellers**, largest when liquidity
is scarce (Nagel 2012). D-075 admits one direct test: on market-wide stress days, do the liquid names that
fell most outperform over the next 5 sessions, after beta and cost?

**Honest prior:**
- On IDX, falls usually continue, and ARB limits drag forced selling out over days. A NULL is likely.
- A pass in 2007–2020 only reads as decayed.
- The one related survivor is HYP-PM-0014 (big-4 bank climax low), and it is excluded as a control.

## Mode: two gates

- **G0:** predeclaration, drivers, PIT tests, census counts, registration draft. Freeze with a sha256
  sidecar, push, then **STOP**. **Before G0 approval, no return after any stress day's close may be
  computed, printed or stored**: not for the basket, the market or any control.
  - Pre-event data is allowed: day-t returns (they define the event), ADV, β, Parkinson deciles, counts.
- **G1:** after approval, one run, then RESULT, VERDICT and HANDOFF. STOP. Any fix after G1 is a new,
  disclosed, re-frozen run.

## Data (frozen at G0)

- **E1 panel** (events from 2007-01-01 to 2021-06-30): `data/history_long.db::ohlcv_long`, read-only.
  - Columns: `ticker, date, open, high, low, close, adj_close, volume`.
  - **Before using it, establish and write down in HANDOFF_G0:**
    - the source (expected yfinance)
    - whether `close` is split-adjusted and whether `adj_close` includes dividends
    - survivorship: are names delisted before 2026 present? Count them.
    - the date coverage per year
  - Returns use `adj_close`, which is total return, if dividends are included. If not, apply the same
    dividend add-back as E2. Say which.
- **E2 panel** (events from 2021-07-01): 5001 `data/walkforward.db::ohlcv` (`is_final = 1`, raw bars).
  - Returns are total return. On each ex-date, add the dividend back from `corporate_action_events`
    (IDR cash dividends).
  - Exclude a name from an event if a split, bonus, reverse split or rights ex-date falls in t−1..t+5.
    These bars are raw, so the adjustment can't be trusted.
- **Overlap check (pre-event):** for 2021-07..2026-09, compute the stress flag on both panels and report
  how often they agree. Events always come from the panel for their era. If the two panels disagree on more
  than 20% of flagged days, STOP and report before going further.
- **Snapshot:** pin both DB files, recording sha256 and the `research/tracking.py` dataset fingerprint. G1
  verifies both before any outcome.
- **Guards:**
  - Daily |return| > 35% counts as a bad print; drop that name-day.
  - FORU is excluded from 2026-09-14 (D-063).
  - Names whose 5-session window lacks a bar (suspension or delisting): use the last available close and
    count them. Don't drop them silently.

## Event (fixed by D-075)

- **Liquid set on day t:** ADV20 ≥ Rp 10bn, where ADV20 is the mean of close × volume over t−20..t−1. At
  least 30 liquid names are required, otherwise there is no event.
- **Market return:** r_m(t) = the equal-weight mean of day-t returns across the liquid set.
- **σ(t):** the standard deviation of r_m over t−250..t−1 (at least 120 observations).
- **Stress day:** r_m(t) ≤ **−2.5 × σ(t)**.
- **Episode:** a stress day starts a new episode if no stress day occurred in the previous 5 sessions.
  **Only the first day of each episode is an event.** Later stress days are report-only.
- **Planner pre-event counts** (2026-10-08). Reproduce these; don't trust them.
  - 105 days / **63 episodes** 2007–2026 on `history_long`
  - 32 days / 21 episodes on the 5001 panel since 2021-07
  - liquid names per day: median 70 (long panel) and 137 (5001)

## The arm (exactly one, S1)

- **Basket:** the liquid names in the **bottom quintile of day-t return**, equal weight.
  - Excluded: zero volume on t, which includes ARB-locked names that can't be bought, and the exclusions
    under Data.
  - Report the basket size per event.
- **Entry:** the close of t. **Exit:** the close of t+5.
- **β:** for each name, the OLS slope of its daily returns on r_m over t−250..t−1 (at least 120
  observations). The basket β is the average of the names' β. Names without enough history take the
  average β of the other basket names. Count them.
- **Outcome per event:**

  R = basket return (close t → close t+5) − β × EW liquid market return (same window) − cost

  - The EW liquid market uses day-t membership and is total return.
  - The cost is the **D-059 modelled round-trip cost** for each name at its ADV20, averaged over the basket.
    Locate the function D-059 used, cite its path and commit, and freeze it.
- **Test statistic:** the mean of R across events, with t = mean / sd × √n. Episodes are the independent
  unit, so there is no clustering.

## Pass bar (fixed at G0; all must hold)

1. **Strength:** mean R > 0 **and** t ≥ the frozen bar. The bar is `bar_v2.e_max_abs_z(N)`, with N = the
   census ledger at G0 plus 1.
   - The ledger is **601** as of D-075, plus D-073's 2 arms once registered = 603, plus D-074's 1 arm if it
     is registered before this one.
   - So N = 604 (3.2954) or 605 (3.2959). State which, and the ledger rows it counts.
2. **Both halves > 0:** E1 2007-01 → 2020-12 and E2 2021-07 →.
   - Events from 2021-01..06 are in the pooled test but in neither half. List them.
3. **Next-day entry > 0:** R with entry at the close of **t+1** and exit at the close of t+6 is > 0.
4. **Not volatility:** the basket's excess over a **Parkinson-60-decile-matched book** is > 0.
   - For each basket name, use the EW of liquid names in its Parkinson-60 decile (computed on t−60..t−1)
     over the same window.
   - This guards against VOLEX {V}, D-062.

**Required controls (reported; a sign flip is named in VERDICT but doesn't fail the arm by itself):**
- excluding the big-4 banks (BBCA, BBRI, BMRI, BBNI), against HYP-PM-0014
- excluding names with any ex-date (dividend included) in t−1..t+5

**Report only (not tested):**
- **S2:** the EW liquid market over close t → t+5, minus its trailing-250 mean 5-session return
- later-in-episode stress days, with the same S1 construction
- horizons 1, 10 and 20 sessions
- a per-event table (date, r_m, σ multiple, basket size, β, R) and a year table
- the 5 worst events
- the ARB-excluded count per event

## Entry-timing pre-check (at G0, pre-event)

- The stress flag uses day t's close. From 5001 `stockbit_flow_bars` (2025+), recompute r_m(t) with each
  liquid name's last price at or before **15:49**, against the prior close.
- Report how often the 15:49 flag matches the close flag on 2025+ stress days and near-misses (within
  ±0.5σ).
- Use price only. Known issue: minute-bar **volume** under-captures since 2026-07, but prices are fine.
- This answers whether a trader could know at the pre-close. Pass condition 3 covers the case where they
  can't.

## Power (in HANDOFF_G0, pre-event only)

Estimate the S1 standard deviation per event without outcomes:
- the cross-sectional dispersion of the basket names' daily returns over t−60..t−1
- scaled to 5 sessions
- with a stress multiplier taken from day-t dispersion relative to normal

Report the MDE at n = 63 and at the frozen bar. The planner's approximation is 0.8–1.3%.

## PIT tests (at G0, must pass)

- (a) Liquid membership, σ(t), β, Parkinson deciles and ADV use only bars before t. Truncating the panel at
  t−1 gives identical values. The day-t return is the only day-t input.
- (b) Episode rule: unit tests for two stress days 3 sessions apart (one event) and 6 sessions apart (two
  events).
- (c) The quintile uses only liquid names with a valid day-t return. A zero-volume ARB name is excluded.
- (d) A synthetic panel with known values: basket return +2%, market +1%, β 1.5, cost 0.6%.
  R = 2 − 1.5 × 1 − 0.6 = **−0.1%**, which the driver must reproduce exactly.
- (e) Total-return add-back uses the ex-date, never the cum date.
- (f) The G0 census script never computes a return after the close of t. Prove it by grep or a test.

## Governance (draft, do not file)

- **Registration:** HYP-PM-0019 (HYP-PM-0017 = D-073 dividends, HYP-PM-0018 = D-074 tender offers).
  Family Price-Reversal widened to {R1, R2, R3}, with R3 = market-stress liquidity provision.
- **Files:** draft `REGISTRATION_DRAFT.md` and the D-entry text, with the next free number at filing and
  the family-widening amendment wording.
- **Don't edit** HYPOTHESIS_REGISTRY, FAILURE_REGISTRY or DECISION_LOG.

## Forward test (record only, nothing to build)

If S1 passes, the forward test is every new first-day stress episode after the G1 date, with the same frozen
rules, recorded at t and t+5. Expect about 3–6 episodes a year, so a verdict takes years. Say so in HANDOFF.
Name where a recorder would live.

## Deliverables

**G0:** `docs/research_programs/P-M/stress_reversal/` containing:
- `PREDECLARATION.md` and `.sha256`, covering the predeclaration, the drivers and the tests
- the drivers
- the PIT tests
- `CENSUS_G0.json`: counts only, per year and per half, plus basket sizes, exclusions and the panel
  agreement rate
- `REGISTRATION_DRAFT.md`
- `HANDOFF_G0.md`: the `history_long` provenance findings, the pre-close agreement, power, the bar and its N,
  the D-059 cost source, the runtime estimate

Push and **STOP**.

**G1:** `RESULT_<utc>.json`, `VERDICT.md`, `HANDOFF_G1.md`. Push and STOP.

## Hard constraints

- Research-side only (`test_architecture_boundary.py`, `test_research_data_fence.py` must pass). Read-only
  data. Never print secrets.
- Don't touch `~/jurnal26`, production, the 5001 service, or `ops/hardening` beyond the branch point.
- `logs/TELEGRAM_OFF` stays.
- No outcome reads before G0 approval. Breaking this voids the study under D-070 rule 1.
