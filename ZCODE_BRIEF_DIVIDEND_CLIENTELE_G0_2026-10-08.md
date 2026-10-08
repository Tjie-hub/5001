# ZCode brief: dividend clientele, D1 pre-cum demand and D2 ex-day capture. G0 for HYP-PM-0017 (2026-10-08)

**Category:** Research (P-M), new family **{SE} Structural-event forced flow**.
**Authority:** D-073 (mechanism accepted, owner 2026-10-08: "D first", "2%"). Where this brief and
D-073 disagree, D-073 wins. Raise any conflict at G0; don't resolve it silently.
**Branch:** create `research/dividend-clientele-2026-10` from `origin/ops/hardening-2026-07-10` at
or after the commit that carries D-073/D-074. Use a new worktree, and push only that branch.

## Why

D-070 closed the price-pattern search. D-073 accepts one scheduled, mechanism-backed event, the cash
dividend, with two declared directions:

- **D1 (pre-cum demand).** Yield and capture buyers push the price up in the sessions before the cum
  date.
- **D2 (ex-day tax clientele).** The marginal holder values a rupiah of dividend at less than a
  rupiah of price: dividends are taxed at 10–20%, gains at 0.1%. So the ex-date drop should be
  smaller than the dividend, and buying the cum close and selling the ex open should earn the gap.

**Honest prior.**
- D1 is probably null. It is underpowered, and the anchor shortens its window (see below).
- D2 is the real test, but a positive gap can still sit inside the 0.60% cost on mid-yield names.
- A NULL is useful: it closes dividends as a source of flow edge.

## Mode: two gates

- **G0:** predeclaration, drivers, PIT tests, census counts, registration draft. Freeze with a
  sha256 sidecar, push, then **STOP**. **No return after any event's entry may be computed,
  printed or stored before G0 is approved.** Pre-entry prices (ADV, yield, volatility deciles) are
  allowed.
- **G1:** after approval, one run, then RESULT, VERDICT and HANDOFF. STOP. Any fix after G1 is a
  new, disclosed, re-frozen run.

## Data (frozen at G0)

- **Source and snapshot.**
  - Read-only `data/walkforward.db`, using `ohlcv` (raw bars, `is_final = 1`) and
    `corporate_action_events`.
  - Pin a snapshot and record its sha256 and the `research/tracking.py` dataset fingerprint. G1
    must verify both before reading any outcome.
- **Events.**
  - `action_type = 'dividend'`, `dividend_currency = 'CURRENCY_IDR'`, `dividend_value > 0`, with
    stored `dividend_cumdate` and `dividend_exdate`.
  - Several dividends on the same (ticker, cum date) are summed into one event.
  - Drop exact duplicates by `dividend_id`.
  - Report how many events the data-quality rules removed, and why.
- **Session mapping.**
  - cum = the trading session on `dividend_cumdate`.
  - ex = the first trading session after cum. Check that it equals `dividend_exdate`, and report
    mismatches. A mismatch is excluded, not repaired.
- **Liquidity.** ADV20 (mean close × volume over the 20 sessions before cum) ≥ Rp 10bn.
- **Exclusions.**
  - a split, bonus, reverse split or rights ex-date from cum−10 to ex+1
  - a missing bar at entry, cum or ex
  - FORU from 2026-09-14 (D-063)
- **Planner pre-event counts** (2026-10-08, metadata and ADV only). Reproduce these; don't trust them.
  - **575** liquid events, all with cum ≥ 2021.
  - 333 events with yield ≥ 2% (D-073 count, on a 576 base).
  - An AGM (`rups_date`) 1–90 calendar days before cum exists for **445** events.
  - The gap from AGM to cum: p25/p50/p75 = **8 / 10 / 12 calendar days**.
  - `rups` rows start in 2020.

## Arms (exactly two; directions fixed by D-073)

### D1: pre-cum run-up

- **Anchor** (the date the dividend is public). It is the earlier of these two:
  - **(a)** the latest `rups_date` for the ticker 1–90 calendar days before cum
  - **(b)** `dividend_created`, if it is before cum **and** isn't a backfill artefact

  An artefact is `dividend_created` ≥ `dividend_exdate`, or a created date shared by more than 50
  events, which suggests a bulk load. ZCode shows the `dividend_created` distribution at G0 and
  freezes this test before any outcome. If the artefact test can't be made reliable, D1 uses (a)
  only. State which one applies.
- **Entry:** the close of the later of cum−10 and the first session after the anchor.
- **Exit:** the cum close.
- **Window:** 3 to 10 sessions. Events with a window of fewer than 3 sessions are dropped from D1.
- **Events with no anchor are dropped from D1** and stay in D2.
- **Outcome:** the stock's return minus the total-return EW liquid book over the same sessions.
  - The stock is held through cum only, so it collects no dividend inside the window.
  - Both legs are measured close to close.
  - D1's cost is 0.60%, applied once per event, since it is a round trip.

### D2: ex-day capture

- **Population:** yield = dividend / close at cum−1, and yield ≥ **2%**.
- **Outcome:** (open_ex + 0.9 × dividend − close_cum) / close_cum − 0.60%, minus the book's return
  from the cum close to the ex open.
  - The book's return includes dividends: book members going ex that morning add their dividends
    back.
  - The 0.9 is the 10% resident final tax.
- **Report only, not tested:**
  - the gross-of-tax row (dividend × 1.0)
  - the ex-close exit row
  - the drop ratio (close_cum − open_ex) / dividend, as median and IQR

### Benchmark (both arms)

- The book is an equal-weight portfolio of every stock with ADV20 ≥ Rp 10bn on each day,
  recomputed point-in-time.
- **Total return:** on each member's ex session, its dividend is added back into that day's
  return, using the same `corporate_action_events` rows. The event stock itself is excluded from its
  own book.
- The book is unadjusted for splits, but a member with a split, bonus or rights ex-date that day is
  dropped from the book on that day.

## Inference and pass bar (fixed at G0, for each arm on its own)

- **Primary t:** the smaller of two:
  - (i) the t of the mean of calendar-month means (events grouped by the cum date's month)
  - (ii) the two-way cluster-robust t, by cum month and by ticker
- **An arm passes only if all four hold:**
  1. **Strength:** pooled mean > 0 **and** primary t ≥ **3.2940** (census 601, `bar_v2.e_max_abs_z`,
     recomputed at G0; D-071 §2).
  2. **Both halves positive:** mean > 0 in each half.
     - The split dates are frozen: cum ≤ 2023-12-31, and cum ≥ 2024-01-01.
     - D-073's "2009 →" half is in effect 2021-23, because no liquid event is earlier. Say so.
  3. **Volatility control positive:** excess > 0 against a Parkinson-60-decile-matched book instead
     of the EW book.
     - Deciles are computed on the 60 sessions before entry, across the liquid universe.
     - This guards against overlap with VOLEX {V} (D-062).
  4. **D2 only:**
     - It must pass at the 0.9 tax factor, not only gross.
     - It must not be positive **only** in the top yield tercile. If the lower two terciles together
       have a mean ≤ 0, D2 fails as economically unusable (D-073).
- **Both arms are reported** whichever passes. There is no "best of", no horizon grid and no yield
  grid. The census counts 2 arms.

**Also report:**
- n per arm and per half
- win rate
- mean and median
- the year table (mandatory)
- the month split: AGM season May–Jul vs the rest
- yield terciles
- the D1 window-length distribution
- a foreign-ownership proxy split, **only if** a point-in-time proxy exists. Otherwise write "none
  PIT; not reported".

## Power (in HANDOFF_G0, pre-event σ only)

- **D1:** recompute the MDE at the actual anchored n (about 445 before the ≥3-session filter) and
  the actual median window. Expect about 1.3% clustered.
- **D2:** recompute at n ≈ 333. Use the pre-event overnight σ (open versus the prior close), not the
  close-to-close σ.

## PIT tests (at G0, must pass)

- (a) The anchor date is before the entry session for every D1 event. A unit test covers an AGM on
  cum−3, which gives a 2-session window and must be dropped.
- (b) Yield, ADV20 and the Parkinson decile use only bars before entry. Check this by truncating
  the panel at entry and getting identical values.
- (c) Book membership on each day uses only ADV computed on earlier days.
- (d) The total-return add-back uses an ex-date, never a cum date.
- (e) Synthetic event, D2:
  - inputs: cum close 1000, dividend 50, ex open 960, flat book
  - expected: (960 + 45 − 1000) / 1000 − 0.006 = −0.001
  - The driver must reproduce this exactly.
- (f) The G0 census script never computes a return after entry. Prove it by grep or a test, as
  Task 2 did.

## Governance (draft, do not file)

- **Family:** {SE}, opened at this registration (D-028, PG-3). HYP-PM-0017 = D1 + D2, 2 arms.
- **Census:** 599 + 2 = 601. The bar is frozen at G0.
- **Files:** draft `REGISTRATION_DRAFT.md` and the D-entry text, using the next free number at
  filing (expected **D-075**).
- **Don't edit** HYPOTHESIS_REGISTRY, FAILURE_REGISTRY or DECISION_LOG.
- D-074 (tender offers, HYP-PM-0018) comes after this G0. Leave it alone.

## Forward test (record only, nothing to build)

- **If an arm passes:** the forward test is on new liquid dividends after the G1 date, with the same
  frozen rules, recorded at cum and ex.
- **The D-064 ex-date monitor** stays detection-only. Name in HANDOFF which table or recorder would
  host the forward test.

## Deliverables

**G0:** `docs/research_programs/P-M/dividend_clientele/` containing:
- `PREDECLARATION.md` and `.sha256`, covering the predeclaration, the drivers and the tests
- the drivers
- the PIT tests
- `CENSUS_G0.json`: counts only, per arm and half, plus the exclusion reasons
- `REGISTRATION_DRAFT.md`
- `HANDOFF_G0.md`: the bar, the power numbers, the anchor rule as frozen, the `dividend_created`
  artefact finding, the runtime estimate

Push and **STOP**.

**G1:** `RESULT_<utc>.json`, `VERDICT.md`, `HANDOFF_G1.md`. Push and STOP.

## Hard constraints

- Research-side only (`test_architecture_boundary.py`, `test_research_data_fence.py` must pass).
  Read-only data. Never print secrets.
- Don't touch `~/jurnal26`, production, the 5001 service, or `ops/hardening` beyond the branch point.
- `logs/TELEGRAM_OFF` stays.
- No outcome reads before G0 approval. Breaking this voids the study under D-070 rule 1.
