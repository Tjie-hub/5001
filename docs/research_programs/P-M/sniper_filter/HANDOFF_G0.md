# HANDOFF_G0 — sniper setup filter (HYP-PM-0016 draft): G0 frozen, STOP

**Revision 1 (2026-10-07): G0 was NOT approved as originally frozen (planner review of
`72b4bd5`). The fixes below (R1–R8, per `ZCODE_BRIEF_SNIPER_G0_REVISION_2026-10-07.md` +
owner ruling `560522a`) are applied in place, re-frozen with a new sidecar, and recorded in
`PREDECLARATION.md` §11. Still read NO outcomes; still gated on
`SNIPER_FILTER_G1_APPROVED=1`; STOP for approval.**

## Revision 1: what changed

- **R1 selection on the full series:** the selection mask is computed ONCE per configuration on
  every scored setup (2016 onward) and indexed into validation/test/PBO — the old per-subset
  calls started every subset's trailing-250 windows cold (the first test months fell back or went
  unselected). PIT test added (full-series vs subset).
- **R2 PBO on validation months only:** the old matrix was ~180 all-NaN rows (scores exist only
  for prediction years ≥ 2016) — meaningless PBO. Now: the 4 configurations' monthly
  selected-mean-R over 2016-01..2021-09, months without selections dropped and counted,
  `n_splits` 16 (≥2 rows/split), NaN asserted away. §7.5 amended.
- **R3 computed pass flags:** the RESULT carries per-configuration booleans for conditions 1–5
  and `passes`; condition 4 uses the validation-chosen M1 only (the unchosen M1 is reported,
  cannot pass); h1/h2 each > 0; PBO is one grid-level value; the VERDICT copies the flags.
- **R4 "also report" implemented (was mandatory, was missing):** year-by-year table per
  configuration, per-feature R-quintile spreads (validation/test separately), the no-fill-bar
  robustness row, win rate. Proven by a synthetic dry run with fake R
  (`RESULT_SYNTHETIC_20261007T082258Z.json` — schema proof only; the real panel was not touched).
- **R5 fill-aware reference sets:** ranks and thresholds use setups with setup pos < p(s) AND
  fill index < p(s) (a fill watched 20 sessions isn't knowable at s until it happens); same-day
  setups no longer rank against each other in row order. Two new tests: late-filling exclusion
  (the naive threshold would flip a selection) and same-day order-independence. Census re-run
  under the new definition: **3,682 filled setups unchanged** (E1 2,253 / E2 1,429), fingerprint
  still `f42275e3…` exactly; per-feature fallback counts refreshed in `CENSUS_G0.json`.
- **R6 fingerprint gate before outcomes, drift-proof:** a read-only SQLite backup snapshot of the
  production DB lives at `/home/tjiesar/scratch/sniper_filter_g1/walkforward_snapshot_2026-10-07.db`
  (outside the repo), file sha256 `c42c151e…d177`, dataset fingerprint **= `f42275e3…` exactly**
  (max_date 2026-10-06 — the backup captured G1FIX's data state). Both frozen and verified with
  SystemExit BEFORE any outcome is computed.
- **R7 feature 10 replaced:** `mkt_above_ma200` (equal-weight market index from the panel:
  mean daily close-to-close return of the owner-screen universe, cumulated; 1.0 if above its
  200-session MA) replaces the IHSG feature, which was constant for all of training (no corpus
  IHSG before 2021-07). Feature count stays 10; truncation test covers it.
- **R8 bar settled by the owner (ruling `560522a`):** PRIMARY pass bar = census **561 + 4 = 565**,
  exact `emax_abs_z(565)` = **3.2765** (561 → 3.2745 reproduced from the recount). The 280-count
  bar (3.07) is a **secondary report-only line** and can never pass a configuration. Ratifying
  the 561 census in DECISION_LOG is a separate owner filing (not this study's act). The
  predeclaration freezes exactly this (§7, §8, §11).
- **Tests:** 17 (was 12), all pass. **Old sidecar:** `PREDECLARATION.sha256` @ `72b4bd5`, file
  sha256 `fafaf4c97abfb8db3edc9aea6cf94657716752eb1d2d0f7e74cd776e2bbbcf89` (git history).

---

**Original G0 record (2026-10-07, pre-Revision-1) follows — sections 1–6 below describe the
first freeze; where Revision 1 supersedes them (bar, feature 10, reference sets, PBO, snapshot
gate, RESULT schema), §Revision 1 above and PREDECLARATION §11 govern.**

**Date:** 2026-10-07 · **Branch:** `research/sniper-filter-2026-10` (from the post-Task-0
hardening tip `a28ec7e`) · **Authority:** `ZCODE_BRIEF_SNIPER_FILTER_2026-10-07.md` as overridden
by `ZCODE_NEXT_TASKS_2026-10-07.md` (Task 1). **No outcome has been read.** G1 is machine-gated
(`SNIPER_FILTER_G1_APPROVED=1`) and was not run.

## 1. What is frozen

`docs/research_programs/P-M/sniper_filter/` — `PREDECLARATION.md` (the full spec: population,
10 features + rank rule, 4 model configurations, selection rule, splits/embargo, pass bar,
conventions C-1..C-8), the drivers (`sniper_filter.py` library, `g0_census.py`, the gated
`g1_run.py`), the PIT tests (`test_pit_sniper_filter.py`, 12 — all pass), `REGISTRATION_DRAFT.md`
(D-entry text, numbered **D-0xx** for the owner's filing) and `CENSUS_G0.json` (counts only).
`PREDECLARATION.sha256` covers the predeclaration, the drivers and the tests. The exit study's
frozen files were verified (`PREDECLARATION.sha256` + `PORTFOLIO_FIX.sha256`, all OK) before any
work and are called, never modified.

## 2. Deflation bar (frozen at G0 with the repo's method)

- Method: exact **E[max|Z|]** over N iid standard normals, ∫₀^∞ [1 − (2Φ(x)−1)^N] dx (the
  D-062/CHECKER_REVIEW/D-064 two-sided convention; ml-rank HANDOFF_G0 §2). Reproduced at G0:
  **N=252 → 3.0394 · N=266 → 3.0558 · N=270 → 3.0603** (the recorded values).
- Census: **276** (D-070's own context line; D-070 adds no trials) + **4 configurations**
  (M0, M1-C1, M1-C2, M2 — this brief's literal "276 + the number of configurations") =
  **N = 280** → exact **3.0713**. The D-067 convention (M0 uncounted) would give N=279 →
  3.0702 — **both round to the frozen bar 3.07**, so the convention choice does not move it;
  the stricter reading governs (owner resolves at filing).
- **Frozen bar: 3.07** (Newey-West t, lag 3, on the monthly selected-minus-all differences,
  TEST only). Bar sensitivity: at N=300 the exact value is 3.092 — the census must not grow
  silently.

## 3. Configuration grid (frozen)

- **M0** (no learning): `0.5·(1 − rank(park60)) + 0.5·rank(ret126)` — the HYP-PM-0015 lesson as
  the pre-registered baseline.
- **M1a / M1b:** sklearn `LogisticRegression(l2, solver=lbfgs, max_iter=1000)` on the 10 ranked
  features, label "X1 net R > 0", **C ∈ {0.1, 10.0}**; the single C is chosen on validation
  (mean R of selected val setups) and frozen for the test refits.
- **M2:** one `HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=200,
  early_stopping=False, random_state=20261007)`.
- **Selection (all models):** top 40% — score ≥ the 60th percentile of the trailing-250-session
  setups' scores, strictly before s; <5 prior scored setups → the percentile over all prior
  scored setups; none → not selected.
- **Splits:** train 2001-01..2015-12 · validation 2016-01..2021-09 · test 2021-10.. (read once);
  yearly expanding refits with the **20-session exit embargo** (PIT-tested).

## 4. Census (counts only — no outcomes)

`CENSUS_G0.json` (generated by `g0_census.py` from the frozen functions): dataset fingerprint
`f42275e3…` (matches G1FIX exactly — zero drift, panel pinned to 2026-10-06), filled-setup counts
total/by-era/by-year, the entry state machine's event counters (fills, expired, superseded,
setups-while-locked, out-of-window — the unfilled accounting the brief requires), per-feature NaN
and rank-fallback counts. **No R, no net %, no return of any kind appears anywhere.**

## 5. Runtime estimate (for the G1 approval decision)

- G0 (this freeze): population + features on 3,682 fills ≈ 6–9 min (panel + indicators dominate;
  measured census runtime is in CENSUS_G0.json).
- **G1 estimate: ~12–20 min single run** — population + features (~7 min), X1 outcomes for all
  fills via `E.simulate_trade` (~1–2 min), 11 embargoed refits × 3 learned configurations (small
  matrices, seconds each), the selection rule (vectorizable, minutes), PBO (deterministic,
  seconds). Well inside one session; no parallelism, no network.

## 6. Governance

- Practice-style registration in {L1} (D-067); inherits the family's multiplicity; **D-070** is
  the admission authority (last price-feature study). Registries/DECISION_LOG not edited; the
  registration draft carries **D-0xx** for the owner's filing (next free number D-071).
- Read-only data throughout; ~/jurnal26 untouched (its `setup_outcomes` table is only referenced
  as the future forward-test surface, with the watchlist-subset caveat); production, crontab,
  service, `logs/TELEGRAM_OFF` untouched.
- **Task 1 STOPS here per the next-tasks note: no outcome read, no G1.** G1 needs the owner's
  approval flag and is one run (RESULT → VERDICT → HANDOFF → stop).

*— ZCode, 2026-10-07*
