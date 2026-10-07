# ZCode brief — which sniper setups work? A predeclared setup filter, HYP-PM-0016 draft (2026-10-07)

**Category:** Research (P-M). **Owner-requested 2026-10-07** ("yes, do both").
**Branch:** create `research/sniper-filter-2026-10` from `origin/research/exit-study-2026-10` (`0b30e49`,
which has the frozen, fixed sniper driver). New worktree. Push only that branch.

## Why

The owner's sniper rule, reconstructed point-in-time in the exit study (E-SN, 3,682 setups
2001–2026), beat random entries before 2021 (t 4.3) but not since (t 1.05). No exit or position rule
improved it. The open question is whether **a filter fixed on the setup day** separates the setups
that work from the ones that don't. This is meta-labelling: the entry rule stays, and a score
decides which setups to take.

Honest prior:
- HYP-PM-0015 showed that price-only learning ends up as "low volatility plus momentum".
- The test period has about 1,429 setups.
- A NULL, or "skip the volatile names", is the likely answer, and both are useful.

## Mode: two gates, as before

- **G0:** predeclaration, drivers, PIT tests, registration draft. Freeze them with a sha256 sidecar,
  push, **STOP**. No outcome may be read before G0 is approved.
- **G1:** after approval, one run, then RESULT, VERDICT and HANDOFF. STOP. Any fix after G1 is a new,
  disclosed, re-frozen run.

## Data and population (frozen)

- **Population:** exactly the exit study's E-SN setups and X1/P0 outcomes. Get them **only by calling**
  the frozen `exit_study.py` functions (`simulate_trade` and the population builder) at `0b30e49`.
  Don't copy or modify them.
- **The frozen sidecars must verify before and after:** `PREDECLARATION.sha256` and
  `PORTFOLIO_FIX.sha256`.
- **Dataset:** the same pinned panel and fingerprint as G1FIX (`f42275e3…`); disclose any drift.
- **Unit:** one **filled** setup.
- **Outcome:** X1 net R, the exit study's figure. Unfilled setups are excluded and their count is
  reported.

## Features (frozen; ≤ 10; all known at the close of setup day s, never at the fill)

1. zone touches
2. planned R:R from the zone mid
3. zone width / ATR14
4. (zone top − stop) / ATR14
5. (close − MA20) / ATR14
6. (close − MA50) / ATR14
7. MA200 slope over 20 sessions
8. Parkinson-60 volatility (the VOLEX measure)
9. 126-session return
10. IHSG above its MA200 (0/1)

Each is a cross-sectional percentile rank among all E-SN setups in the trailing 250 sessions before
s. Use raw values where a rank is undefined; write the rule down. ADV is the population floor, so it
isn't a feature.

## Models (≤ 4 configurations in total, all listed at G0)

- **M0, no learning:** the equal-weight mean of rank(low Parkinson-60) and rank(126-session return).
  This is the HYP-PM-0015 lesson, pre-registered as the baseline.
- **M1:** logistic regression on "R > 0", L2, with 2 C values.
- **M2:** one shallow `HistGradientBoostingClassifier` (max_depth 3, fixed settings).
- **Selection rule:** take a setup if its score is in the **top 40%** of scores among the trailing 250
  sessions' setups. This rule is the same for every model and is fixed now.

## Splits

- **Train:** 2001 → 2015-12.
- **Validation:** 2016-01 → 2021-09. Choose one M1 configuration here, on mean R of the selected
  setups. M0 and M2 have nothing to choose.
- **Test:** 2021-10 → the latest complete setup, read once at G1.
- **Refit:** yearly, on an expanding window.
- **Embargo:** training labels must be resolved (exit day) at least 20 sessions before the first
  prediction in the refit year.

## Pass bar (fixed at G0; on TEST)

A model passes only if all five hold:

1. **Selected minus all filled setups:** mean R difference > 0. Compute the monthly mean difference
   and its Newey-West t (lag 3), which must be ≥ the deflation bar at the new census N. Compute the
   bar at G0 with the repo's method and freeze it. It's about 3.06 at N=276; N rises with these
   configurations.
2. **The selected setups' own mean net R is > 0**, so they're tradeable, not just less bad.
3. **It holds in both halves** of the test period (2021-10..2023-12 and 2024-01..end). The
   difference must be > 0 in each.
4. **For M1/M2 to count as "learning adds value":** beats M0 with paired monthly t ≥ 2. Otherwise
   report M0's result as the finding.
5. **PBO < 0.5** over the grid, via `research/statistics.py::pbo_cscv`.

**Also report:**
- n selected
- win rate
- the year-by-year table (mandatory)
- R quintile spreads per feature, as univariate diagnostics
- the result with fill-bar exits (`days == 0`) dropped, as a robustness row

## Governance (draft, do not file)

- **Family:** Price-Learning **{L1}** (D-067), "learned combination of price/volume features". The
  family stays as it is. HYP-PM-0016 is a new member and inherits the {L1} multiplicity.
- **Census:** 276 + the number of configurations.
- **Files:** draft `REGISTRATION_DRAFT.md` and the D-entry text. The next free number is **D-070**,
  since D-069 is reserved by the consolidation brief. Don't edit HYPOTHESIS_REGISTRY,
  FAILURE_REGISTRY or DECISION_LOG.
- **PIT tests at G0:**
  - (a) every feature at s is bit-identical when the panel is truncated at s
  - (b) the embargo holds
  - (c) the selection threshold uses only setups before s

## Forward test (record only; nothing to build)

If a model passes, its frozen score becomes a forward test on the owner's live setups.

- jurnal26 now records every candidate and Watch sniper in its `setup_outcomes` table (from
  2026-10-07). It uses the same X1/P0 rules and the same 0.60% cost, outcomes in R.
- **Caveat for the handoff:** jurnal26 candidates come from 5001's feeds, not a full-market sniper
  scan. Only the `watchlist`-sourced rows match E-SN's selection. State which subset the forward test
  should use.

## Deliverables

**G0:**
- `docs/research_programs/P-M/sniper_filter/` containing:
  - `PREDECLARATION.md` and its `.sha256` (covering the predeclaration, the drivers and the tests)
  - the drivers
  - the PIT tests
  - `REGISTRATION_DRAFT.md`
  - `CENSUS_G0.json`: counts only
  - `HANDOFF_G0.md`: the deflation bar, the grid, the runtime estimate

  Push and STOP.

**G1:** `RESULT_<utc>.json`, `VERDICT.md`, `HANDOFF_G1.md`. Push and STOP.

## Hard constraints

- Research-side only (boundary tests). Read-only data. Never print secrets.
- No changes to the exit study's frozen files.
- Don't touch `~/jurnal26`, production, `ops/hardening`, or the consolidation work.
- `logs/TELEGRAM_OFF` stays.
