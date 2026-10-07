# VERDICT — sniper setup filter (HYP-PM-0016 draft): G1, the single run

**Run:** `RESULT_20261007T090305Z.json` · 2026-10-07 09:03:05 UTC · runtime 200.2 s ·
branch `research/sniper-filter-2026-10` @ Revision 2 (`d261260`) · gate
`SNIPER_FILTER_G1_APPROVED=1` (owner approval of Revision 2). **Executed exactly once.**
Freeze sidecar verified at run time (all five files OK); snapshot gate passed BEFORE any
outcome was computed — snapshot sha256 `c42c151e…` and dataset fingerprint **`f42275e3…`
(matches G1FIX exactly, zero drift)**.
**Population:** 3,682 filled E-SN setups (validation 934, test 1,429) via the frozen
`exit_study` functions; outcome = the frozen X1 net R.

## Verdict: NULL — no configuration passes

**Every pass flag below is copied from the RESULT's computed `pass_conditions`; this verdict
does not re-judge them.**

| config | passes | c1 NW t ≥ 3.2931 | c1 NW t (value) | c2 selR > 0 | c3 both halves > 0 | c4 beats M0 (t ≥ 2) | c5 PBO < 0.5 |
|---|---|---|---:|---:|---|---|---|
| M0 | **False** | False | −0.573 | False | False | — (baseline) | True |
| M1a (not chosen) | **False** | False | −0.047 | False | False | **False** (cannot pass: not the validation-chosen M1) | True |
| M1b (chosen, C=10) | **False** | False | +0.194 | False | False | True (t +2.43) | True |
| M2 | **False** | False | +0.226 | False | False | True (t +2.12) | True |

Underlying numbers (test period 2021-10..2026-09, n = 1,429; all-setups mean R = **−0.0434**):

| config | n selected | selected mean R | selected win rate | h1 diff (≤2023-12) | h2 diff (≥2024-01) | would pass under secondary bar (report-only) |
|---|---:|---:|---:|---:|---:|---|
| M0 | 578 | −0.1243 | 49.5% | −0.1113 | +0.0090 | False |
| M1a | 584 | −0.0146 | 73.1% | −0.0723 | +0.0521 | False |
| M1b | 585 | −0.0098 | 73.3% | −0.0551 | +0.0630 | False |
| M2 | 581 | −0.0285 | 71.3% | −0.0202 | +0.0426 | False |

- **Condition 1 fails everywhere by a wide margin**: the best monthly-difference Newey-West t is
  +0.23 (M2) against the frozen primary bar **3.2931** (census N = 599). The secondary line
  (3.07, report-only) would not have passed either.
- **Condition 2 fails everywhere**: no configuration's selected setups have positive mean net R
  on test (the selected are "less bad" than the average setup, not profitable).
- **Condition 3 fails everywhere** (each half must be > 0; every configuration is negative in
  the first half).
- **Condition 4**: M1b (the validation-chosen M1; validation means M1a −0.0161 vs M1b +0.0019)
  and M2 beat M0 with paired monthly t +2.43 / +2.12 — **learning beat the pre-registered
  baseline, but everything it learned to select still loses money** on test.
- **Condition 5 passes**: PBO = **0.461** (< 0.5; 60 validation months, 8 dropped for no
  selection, 48 used, 16 splits) — the grid's selection is not pure overfitting noise; there is
  simply no positive effect to overfit.

## Reading (factual, no re-judgement of the flags)

- **The pre-registered honest prior is confirmed: the answer is a NULL.** No setup filter — the
  low-vol+momentum baseline or either learned model — separates profitable setups from
  unprofitable ones on the sniper entry in 2021-10..2026-09.
- **The HYP-PM-0015 lesson did not transfer.** M0 (low-vol + momentum ranks, the pre-registered
  baseline) was the WORST test performer (−0.124R selected vs −0.043R all): ranking sniper
  setups by low Parkinson-60 volatility and high 126-session momentum selected *worse*-than-
  average trades in the confirmation era. The test quintile diagnostic agrees (M0's park60
  q5−q1 spread −0.208, ret126 −0.240 — the ranked extremes run the wrong way).
- **The learned models moved in a consistent direction** (M1b/M2 beat M0 at t ≥ 2; their
  selected win rates are 71–73% vs ~53% overall) but with negative mean R — many small wins,
  fewer larger losses. Under the frozen rule that is reported, not chased: `passes` is False.
- **Robustness row (fill-bar exits dropped):** zero test trades exited on the fill bar, so the
  robustness row is identical to the headline (`n_dropped_fillbar = 0`).
- **Selection tiers (Revision 2 V2 reporting):** per configuration — window tier 2,358, all-known
  tier 4, unselected 1,320, unscored 1,319 (scores exist for prediction years ≥ 2016 only).
- **Forward test: not built.** §8 of the predeclaration builds a forward test only "if a model
  passes"; none passed, so there is nothing to forward-test and the jurnal26 `setup_outcomes`
  subset caveat stays dormant.

## Filing (owner acts; this study files nothing)

Per the predeclared null handling: HYP-PM-0016 → **FAILED (F2-class NULL — no configured filter
clears the bar)**; the {L1} family slot is consumed by this registration and the 4
configurations enter the census at the owner's filing act (the census arithmetic lives in the
ratification draft @ 2937488). The D-entry draft is `REGISTRATION_DRAFT.md` (numbered D-0xx;
the next free number at filing applies). FAILURE_REGISTRY / HYPOTHESIS_REGISTRY / DECISION_LOG
were not edited by this study.

## Disclosures

1. Benign sklearn `FutureWarning`s on `penalty="l2"` (deprecated spelling in sklearn 1.8) — the
   frozen configuration ran as written.
2. The snapshot gate verified `c42c151e…` / `f42275e3…` before any outcome was computed; the
   run read the frozen snapshot, not the live DB.
3. The year-by-year table, quintile spreads (validation and test, per feature) and full flag
   blocks are in `RESULT_20261007T090305Z.json` (keys: `year_by_year`,
   `feature_quintile_spreads`, `configs[*].pass_conditions`).
4. Practice-style registration in {L1} (D-067): consumes no new family; inherits its
   multiplicity; the study files nothing itself.

**G1 is terminal for this study. Any fix after this run is a new, disclosed, re-frozen run.**

*— ZCode, 2026-10-07*
