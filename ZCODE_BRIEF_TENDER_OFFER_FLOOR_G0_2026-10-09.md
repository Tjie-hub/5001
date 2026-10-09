# ZCode brief: tender-offer price floor. G0 for HYP-PM-0018 (2026-10-09)

**Category:** Research (P-M), family **Structural-Event {SE}**, slot 2. The family was opened by D-076 and
holds HYP-PM-0017, which FAILED (D-077).
**Authority:** D-074 (mechanism accepted, owner 2026-10-08; "G1 + stop rule"). Owner go-ahead: 2026-10-09,
"go for D-074". Where this brief and D-074 disagree, D-074 wins. Raise any conflict at G0; don't resolve it
silently.
**Branch:** create `research/tender-offer-floor-2026-10` from `origin/ops/hardening-2026-07-10` at or after
the commit that adds this brief. Use a new worktree, and push only that branch.

## Why

A tender offer is a contractual promise to buy at a fixed price until `tender_end`, paid on
`tender_paydate`. If the market trades below the offer, the gap is an arbitrage spread bounded by deal
risk and time. It isn't a forecast. This is the one {SE} mechanism whose payoff is written in a contract.

**Honest prior (D-074):** with n ≈ 26, expect a small positive mean below the bar, or a stop. The forward
recorder is the durable output.

## Mode: two gates, plus the stop rule

- **G0:** predeclaration, drivers, PIT tests, census counts, registration draft. Freeze with a sha256
  sidecar, push, then **STOP**.
  - **Before G0 approval, no return after the entry close may be computed, printed or stored.** That covers
    the tender window, `tender_end` and the EW book.
  - Pre-event data is allowed: the spread at the entry close, ADV20, counts and window lengths.
- **Stop rule (owner, D-074):** if the frozen population has **fewer than 20** eligible events, there is
  **no G1**.
  - In that case the G0 instead delivers a descriptive **spread ledger**: per event, the pre-entry facts
    only, with no outcomes.
  - The arm still counts in the census from registration (X8).
  - State clearly in HANDOFF_G0 which branch applies.
- **G1** (only if n ≥ 20, after approval): one run, then RESULT, VERDICT and HANDOFF. STOP.

## Data (frozen at G0)

- **Source:** 5001 `corporate_action_events` with `action_type = 'tenderoffer'` (165 rows).
  - Fields from `raw_json`: `tender_price`, `tender_start`, `tender_end`, `tender_paydate`,
    `tender_percentage`, `tender_shares`, `tender_created`, `event_note`.
  - Prices: 5001 `ohlcv` (`is_final = 1`).
- **Snapshot:** pin a fresh walkforward snapshot (sqlite backup API), recording its sha256 and the
  `research/tracking.py` fingerprint. G1 verifies both before any outcome. Re-using the 2026-10-08 pair is
  fine if `corporate_action_events` has no tender rows newer than it. Check, and say which.
- **Basis check (required):** the 2026-10-08 G0s found that stored prices are split-adjusted to fetch time,
  and `dividend_value` is pre-scaled to the same basis.
  - Establish whether `tender_price` is on the stored-price basis or as-announced.
  - Test: for every event with a split, bonus or reverse split after `tender_start`, compare tender_price
    against the stored closes around the window. Use pre-entry closes only, and report the ratio.
  - If tender_price is as-announced, rescale it by the cumulative later split factor, and freeze that rule.
- **Guards:**
  - Daily |return| > 35% counts as a bad print.
  - FORU is excluded from 2026-09-14 (D-063).
  - Exclude an event if a split, bonus, reverse split or rights ex-date falls inside entry..`tender_end`.
    Count these.

## Point-in-time: when was the offer known? (must be settled at G0)

`tender_created` is a vendor stamp and can't be trusted on its own. For example, ZBRA was created on
2021-09-23 for a window of 2021-04-30 → 05-29.

- **Rule to freeze:** the offer is treated as public at the **close before `tender_start`**.
  - Rationale: the offer statement (*pernyataan penawaran tender*) is published before the window opens
    (POJK 9/2018).
  - Run the artefact test from the dividend G0 on `tender_created` (created on or after `tender_end`, or a
    created date shared by more than 50 rows).
  - Report how many events have `tender_created` ≤ `tender_start` against later.
  - Use `tender_created` for nothing except that report.
- **PIT test (a):** the spread, ADV20 and the eligibility flag use only bars at or before the entry close.

## Population (fixed by D-074)

All of these must hold:
1. tender_price, tender_start and tender_end are stored, with start < end, and the window has at least 2
   sessions.
2. **ADV20 ≥ Rp 1bn** on the entry session, using true-rupiah ADV (stored close × cumulative split factor ×
   volume, as in the stress G0), known by that session.
3. **Spread** = tender_price / close(entry) − 1 ≥ **0.60% + the D-059 modelled round-trip cost** at the
   name's ADV20.
   - Cite the D-059 function's path and commit (the stress G0 used `7e039ee`), and freeze it.
4. Entry = the close of the session **before `tender_start`**.
   - If that session has zero volume, the event is ineligible. Count these.

**Planner pre-event counts** (2026-10-08). Reproduce these; don't trust them:
- 165 events; 129 with 20 pre-bars
- 67 of those 129 priced below the market
- eligible at ≥ Rp 1bn: **26** (median spread 3.6%); at ≥ Rp 10bn: 8 (7.4%); with no floor: 61 (5.0%)
- median window 22 sessions (range 4–25)
- eligible events 2021 → 2026

The stop rule applies to the number **you** reproduce under the rules above, not to the planner's 26.

## The arm (exactly one, T1)

- **Outcome per event:** R = close(tender_end) / close(entry) − 1 − the modelled round-trip cost.
  - This is a market exit at the `tender_end` close.
  - If `tender_end` is not a session, use the last session on or before it.
  - Add back any dividend with an ex-date inside the window. Count these.
- **Test:** the pooled mean of R, with **month-clustered t**, clustered on the entry month.
  - **Pass:** mean R > 0 **and** t ≥ the frozen bar.
- **Required:** the mean excess over the EW liquid book (ADV20 ≥ Rp 10bn, total return, same window) is
  > 0.
- **Report only (not tested):**
  - the acceptance upper bound: tender_price paid on tender_paydate, no proration, net of cost
  - the convergence ratio (close(end) − close(entry)) / (tender_price − close(entry))
  - the per-event table and the 5 worst events
  - splits by `tender_percentage` (full vs partial; freeze the cut, e.g. ≥ 99% = full) and by ADV tier
    (1–10bn vs ≥ 10bn)
- **Mandatory vs voluntary:** no stored field says which. Try to classify from `event_note` or
  `tender_percentage` pre-event, and freeze the rule. If no reliable rule exists, say so and leave the
  split unreported. Don't guess.
- **Falsification (D-074):** the pooled net is ≤ 0 or below the bar, **or** losses concentrate in withdrawn
  or prorated deals that the rule can't exclude in advance. Define at G0 how "withdrawn" is detected (for
  example, close(end) far below the offer with no payment) and report it at G1.

## Bar (fixed at G0)

- **Census:** the ledger is **608** after D-078 (605 + HYP-PM-0017's 2 arms + HYP-PM-0019's 1).
  - This arm makes **N = 609**, bar `bar_v2.e_max_abs_z(609)` = **3.2978** (exact 3.297758).
  - D-074's "602 / 3.2945" is stale.
  - Re-verify at G0 and again at G1. If another arm is counted in between, recompute and disclose.
- **Power (in HANDOFF_G0, pre-event):** use pre-entry daily σ over the 60 sessions before entry, scaled to
  each event's window length. Report the MDE at your n and the bar.
  - Volatility *inside* any tender window (even another event's) is not allowed, because those are
    outcomes.
  - So report the planner's pessimistic convention, plus a stated optimistic bound: the spread distribution
    itself, which is the maximum a fully converging event can earn.

## PIT tests (at G0, must pass)

- (a) The spread, ADV20 and eligibility use only bars at or before the entry close. Truncating the panel at
  the entry gives identical values.
- (b) Entry is the session before `tender_start`. If `tender_end` is not a session, the last session on or
  before it is used.
- (c) Basis rule: a synthetic split after `tender_start` rescales tender_price (or doesn't) exactly as frozen.
- (d) Synthetic event: entry 100, end close 103, cost 0.6%, so R = **+2.4%** exactly. EW book +1%, so the
  excess is +1.4%.
- (e) The dividend add-back uses the ex-date inside the window, never the cum date.
- (f) The G0 census script never reads a close after the entry. Prove it by grep or a test.

## Forward recorder (D-074 §3; record only, no census arm)

- Draft the recorder spec in HANDOFF_G0: every new tender offer is logged at `tender_start` (price, spread,
  ADV) and at `tender_end` (convergence).
- First case: **DOOH**, offer 148, window 2026-10-05 → 11-03.
- Name where it would live (next to the D-064 ex-date monitor lineage). Don't build it.

## Governance (draft, do not file)

- **Registration:** HYP-PM-0018 in {SE}, slot 2. The next free D-number at filing is expected to be
  **D-079**.
- Draft `REGISTRATION_DRAFT.md` with the D-entry text. If the stop rule fires, the D-entry records the
  stop instead of a G1.
- **Don't edit** HYPOTHESIS_REGISTRY, FAILURE_REGISTRY or DECISION_LOG.

## Deliverables

**G0:** `docs/research_programs/P-M/tender_offer/` containing:
- `PREDECLARATION.md` and `.sha256`
- the drivers and PIT tests
- `CENSUS_G0.json`: counts only, covering each population filter step, per year, the basis-check result,
  the tender_created audit, exclusions, and the stop-rule decision
- `REGISTRATION_DRAFT.md`
- `HANDOFF_G0.md`: provenance, PIT, power, the bar and its N, the D-059 source, the recorder spec, the
  runtime estimate
- if the stop rule fires: `SPREAD_LEDGER.md` (pre-entry facts per event)

Push and **STOP**.

**G1** (only if n ≥ 20 and approved): `RESULT_<utc>.json`, `VERDICT.md`, `HANDOFF_G1.md`. Push and STOP.

## Hard constraints

- Research-side only (`test_architecture_boundary.py`, `test_research_data_fence.py` must pass). Read-only
  data. Never print secrets.
- Don't touch `~/jurnal26`, production, the 5001 service, the registries, or `ops/hardening` beyond the
  branch point. `logs/TELEGRAM_OFF` stays.
- The stress-reversal G1 (`research/market-stress-reversal-2026-10`) is a separate task. Don't mix the
  branches.
- No outcome reads before G0 approval. Breaking this voids the study under D-070 rule 1.
