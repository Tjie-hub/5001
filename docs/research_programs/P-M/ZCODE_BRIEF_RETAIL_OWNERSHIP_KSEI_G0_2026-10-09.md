# ZCode brief: retail ownership (KSEI). G0 (2026-10-09)

**Status:** staged. **Do not start until the owner accepts the mechanism D-entry** (D-070 rule 1). The
draft is in `data_acquisition/08_RETAIL_PATHS_1_4_FEASIBILITY_2026-10-09.md` §Draft mechanism D-entries,
item 2. The accepting D-number goes here: D-___.
**Category:** Research (P-M). New family, proposed name **Ownership-Clientele {OC}**, slot 1 (level) and
slot 2 (flow). Confirm the family at G0 and raise any conflict with {SE} or {LC}.
**Branch:** `research/retail-ownership-2026-10` from `origin/ops/hardening-2026-07-10`. Use a new worktree
and push only that branch.

## Mechanism (from the draft D-entry)

- **(a) Level:** stocks held mostly by individuals carry lottery demand and are overpriced, so they
  underperform next month.
  - References: Kumar 2009; Han and Kumar 2013; NBER w29543.
- **(b) Flow:** a monthly rise in the individual share (retail inflow) is followed by underperformance.
- **Incrementality is required:** both must add value over the surviving VOLEX risk premium
  (Parkinson-60 top-decile exclusion), size and 12-1 momentum. A result that is only VOLEX in disguise is
  a fail.

## Data (freeze at G0)

- **Source:** `~/idx_external/ksei/ksei_equity_holdings.csv`, built by `parse_ksei.py` from 211 KSEI zips
  (2009-03 → 2026-09).
  - Record each zip's sha256 and a manifest sha256.
  - Do not refetch. If a month is added, record that.
- **Prices:** 5001 `ohlcv` (`is_final = 1`) or history_long. State which, and pin a snapshot + fingerprint
  as in the stress G0. FORU is excluded from 2026-09-14 (D-063).
- **PIT rule (freeze):** month-end file M is known from the **5th trading session of month M+1**.
  - The zip stamp is about +3 days. The web publication date is unknown, so be conservative.
  - Portfolios form at that session's close.
- **Denominator (decide and justify at G0):**
  - Option 1: ID / custodied total (L_total + F_total).
  - Option 2: ID / sec_num (listed shares).
  - The custodied total is well below listed shares for controller-held names (TOWR 26.2B vs 59.1B).
    Report both distributions pre-outcome, then freeze one.
- **Individual** = `L_ID + F_ID`. Report the foreign-individual share separately, as a description only.
- **Liquidity floor:** ADV20 ≥ Rp 1bn using **adv_regular** (the volume-basis rule, pending D-081) from
  2026-07-06. Disclose the basis.

## Arms (pre-declare exactly)

- **A1 level:** monthly sort on the individual share, top vs bottom quintile, within the liquid
  universe.
  - Score: next-month return, net of `cost_realised` (pending D-082).
  - Test: Fama-MacBeth with Newey-West t.
- **A2 flow:** the 1-month change in individual share, sorted the same way.
- **Controls (in a Fama-MacBeth regression):** log size, Parkinson-60, 12-1 momentum, VOLEX flag.
- **Bar:** `bar_v2.e_max_abs_z(N)` with N = the census at G0 + 2. Re-verify at G1.
- **Halves:** 2009–2017 and 2018–2026. Both must have the predicted sign (the era-flip lesson, D-070).

## G0 deliverables (no returns read)

- `PREDECLARATION.md` + sha256
- `CENSUS_G0.json`: per-month counts after each filter, the denominator distributions, and the PIT
  calendar
- power at the bar from pre-period volatility only
- `REGISTRATION_DRAFT.md`, `HANDOFF_G0.md`

Push and STOP.

## Hard constraints

- Research-side only. `test_architecture_boundary.py` and `test_research_data_fence.py` must pass.
- No return after a formation date may be computed before G0 approval (this would void the study under
  D-070).
- Don't touch production, the registries, DECISION_LOG or `~/jurnal26`. TELEGRAM_OFF stays.
