# PREDECLARATION — sniper setup filter (HYP-PM-0016 draft), G0 freeze

**Status:** frozen before any outcome is read · **Date:** 2026-10-07 ·
**Authority:** brief `ZCODE_BRIEF_SNIPER_FILTER_2026-10-07.md` (04d412b) as overridden by
`ZCODE_NEXT_TASKS_2026-10-07.md` (7ccb15d); **D-070** (a28ec7e) admits HYP-PM-0016 as the LAST
price-feature study (D-070 §Decision 2) and closes everything after it.
**Branch:** `research/sniper-filter-2026-10` from the post-Task-0 hardening tip (`a28ec7e`).
**This is a PRACTICE-STYLE registration draft in the {L1} family (D-067):** it filters the owner's
existing sniper entry (meta-labelling) and inherits {L1}'s multiplicity. Two gates: **G0 = this
freeze + a counts-only census + PIT tests**, then STOP; **G1 = one run** after owner/planner
approval (machine-gated on `SNIPER_FILTER_G1_APPROVED=1`), then RESULT/VERDICT/HANDOFF, STOP.
No outcome may be read before G1 approval. The sha256 sidecar (`PREDECLARATION.sha256`) covers
THIS file, `sniper_filter.py`, `g0_census.py`, `g1_run.py` and `test_pit_sniper_filter.py`.

## 1. Question

The owner's sniper entry (E-SN: 3,682 filled setups 2001–2026, PIT-reconstructed) beat random
entries before 2021 (t ≈ +4.2) but not since (t ≈ +1.05). Does a **setup-day filter** separate the
setups that work from the ones that don't? The entry rule itself stays; a score decides which
setups to take (meta-labelling). Honest prior: a NULL, or "skip the volatile names" (the HYP-PM-0015
lesson), is the likely answer, and both are useful.

## 2. Data and population (frozen)

- **Dataset:** the frozen `exit_study.py` loader (`E.load_panel(issuance=True)` via
  `research.rulecard.data`), **pinned to `2026-10-06`** — G1FIX's exact panel horizon. The DB
  fingerprint must equal G1FIX's `f42275e3…`; any drift is disclosed and stops the run.
- **Population:** exactly the exit study's E-SN fills, obtained ONLY by calling the frozen
  `E.entry_population(P, I_by_stock, owner)` with the owner screen
  (`adv20 = mean(C·V, 20 sessions) ≥ E.ADV20_MIN`) — the identical construction as G1FIX. Do not
  copy or modify the frozen functions. **Unit: one filled setup.** Unfilled setups are excluded;
  their count is reported in the census.
- **Outcome (G1 only):** X1 net R from the frozen `E.simulate_trade(tr, "X1", P, I_cache)` — the
  exit study's own figure, one R per filled setup.
- **IHSG:** read read-only from the same DB (`SELECT date, open, close FROM ohlcv WHERE
  ticker='IHSG'`, the ml-rank loader's exact pattern), pinned to the panel horizon.

## 3. Features (frozen; 10; all known at the close of setup day s, never at the fill)

Raw definitions (ATR = the signal's `atr` = ATR14 at s; MA20/MA50/MA200 from the frozen
`E.stock_indicators` at s; `zone_low/zone_top/stop/target` from the trade's own signal):

| # | name | raw definition |
|---|---|---|
| 1 | `zone_touches` | the pivot count of the support zone group — the SAME group `E.sniper_signal_at` picked (highest-mean pooled group below C[s]); obtained by calling the frozen `E.zone_context(L, H, I, s)` and re-selecting that group (consistency-checked against `tr["zone_low"] == group["min"]`) |
| 2 | `planned_rr` | (target − zone_mid) / (zone_mid − stop), zone_mid = (zone_low + zone_top)/2 |
| 3 | `zone_width_atr` | (zone_top − zone_low) / atr |
| 4 | `zone_stop_atr` | (zone_top − stop) / atr |
| 5 | `close_ma20_atr` | (C[s] − ma20[s]) / atr |
| 6 | `close_ma50_atr` | (C[s] − ma50[s]) / atr |
| 7 | `ma200_slope` | (ma200[s] − ma200[s−20]) / atr |
| 8 | `park60` | Parkinson-60 range volatility, the VOLEX measure: `sqrt( mean_60( ln(H/L)^2 ) / (4·ln 2) )` over the 60 sessions ending s (the forward_exclusion PROTOCOL §universe signal formula) |
| 9 | `ret126` | C[s]/C[s−126] − 1 |
| 10 | `mkt_above_ma200` | **(Revision 1 R7 — replaces the IHSG feature, which has no corpus bar before 2021-07 and was constant for all of training):** 1.0 if the equal-weight market index at s is above its 200-session MA at s, else 0.0. The index = the daily mean close-to-close return of the owner-screen-eligible universe, cumulated from 1.0 — point in time, full history |

**Cross-sectional rank (reference set as amended by Revision 1 R5):** each raw feature becomes a
percentile rank among the filled E-SN setups whose **setup day falls in the trailing 250 sessions
before s AND whose fill bar index is < p(s)** — strictly earlier DAYS (never the same day), and
only setups whose fill had already happened by s (a fill is watched for 20 sessions, so a
setup's filled/unfilled status at s′ < s is not knowable at s until the fill occurs; the fill
index is the trade's `t1`, known by the close of s′+1 at the latest). Percentile =
(#{prior values < x} + 0.5·#{== x}) / n_prior, on the prior values that are defined.
**Fallback (declared):** where the rank is undefined — no prior known setup in the window, or
the setup's own raw value is undefined — the **raw value** is used instead of the rank; a NaN raw
value stays NaN. ADV is the population floor, so it is not a feature.

## 4. Models (frozen; 4 configurations; the grid)

- **M0 (no learning, the pre-registered baseline):** the equal-weight mean of
  `1 − rank(park60)` and `rank(ret126)` (low volatility and momentum rank HIGH — the HYP-PM-0015
  lesson). A setup with either rank component undefined is not scored by M0 (counted).
- **M1:** sklearn `LogisticRegression(penalty="l2", solver="lbfgs", max_iter=1000,
  random_state=SEED)` on the 10 ranked features, label = "X1 net R > 0" (training labels only).
  **Two C values: C ∈ {0.1, 10.0}** (M1a, M1b). NaN inputs are imputed with the median of each
  feature over the model's current training set (declared; train-window only — PIT-safe).
- **M2:** one shallow `HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1,
  max_iter=200, early_stopping=False, random_state=SEED)` on the same 10 inputs (native NaN
  handling; no imputation).
- SEED = 20261007.

## 5. Selection rule (frozen; identical for every model; computed per Revision 1 R1)

Take a setup if its score is in the **top 40%** of the scores of the filled E-SN setups in the
**trailing 250 sessions before s whose fill was already known by s** (the §3 reference set; the
threshold is the 60th percentile of those prior scores). If fewer than 5 prior scored setups are
known in the window, the threshold falls back to the 60th percentile over ALL known scored setups
with setup day strictly before s (declared). If no prior scored setup exists at all, the setup is
not selected (counted). **R1: the mask is computed ONCE per configuration on the FULL score
series (every scored setup, 2016 onward) and then indexed into validation, test and PBO — never
on a split subset, whose trailing windows would start cold and violate this section.** PIT-tested
(mutation + full-series-equality tests).

## 6. Splits, refit and embargo (frozen)

- **Train:** setup months 2001-01..2015-12. **Validation:** 2016-01..2021-09. **Test:**
  2021-10..latest complete setup, read ONCE at G1.
- **Refit:** yearly, on an expanding window — the model predicting calendar year Y is fit on all
  setups with setup month ≤ Y−1 whose **trade has already exited at least 20 sessions before the
  first session of Y** (EMBARGO = 20 sessions on the exit day; PIT-tested). Fits exist for
  Y = 2016..latest; validation predictions use their years' fits, test predictions use
  2021..latest's fits. M1's C is chosen ONCE on validation (mean R of selected val setups) and
  then frozen for the test refits; M0 and M2 have nothing to choose.
- Scores, thresholds and predictions at any setup s use only information available at s plus
  models fit under the embargo rule — PIT-tested (a)/(b)/(c).

## 7. Pass bar (fixed now; evaluated on TEST only; as amended by Revision 1 R8 + owner ruling 560522a)

1. **Selected minus all filled:** mean R difference > 0, computed as the monthly mean difference
   with a **Newey-West t (lag 3) ≥ the PRIMARY deflation bar 3.2765** (R8, owner-ruled: census
   N = 561 + 4 configurations = **565**, exact `emax_abs_z(565)` = 3.2765; the stricter count
   governs by default). The 280-count bar (**3.07**, exact 3.0713 — the hardening D-070-context
   count) is a **secondary reporting line only and can never pass a configuration** (owner
   ruling 560522a); the RESULT reports `would_pass_under_secondary_bar_report_only` beside each
   verdict. Ratifying the 561 census in DECISION_LOG is a separate owner filing.
2. **The selected setups' own mean net R > 0.**
3. **Both halves:** the difference is > 0 in 2021-10..2023-12 AND in 2024-01..end (each half > 0).
4. **"Learning adds value" (the validation-chosen M1 and M2 only):** paired monthly t ≥ 2 vs M0
   (selected-vs-selected monthly mean R). The unchosen M1 is reported but cannot pass.
   Otherwise M0's result is the finding.
5. **PBO < 0.5**, one grid-level value applied to every configuration, via
   `research/statistics.py::pbo_cscv`. **(Revision 1 R2:)** the matrix is the 4 configurations'
   monthly selected-mean-R over the **VALIDATION months only** (2016-01..2021-09, where all four
   have out-of-sample scores); months where any configuration has no selection are dropped and
   the drop count recorded; `n_splits` is frozen at 16 (≥ 2 rows per split at ~69 months; the
   runner lowers it only for degenerate synthetic runs); no NaN may remain (asserted).

The five conditions are **computed booleans in the RESULT** (`pass_conditions` + `passes` per
configuration — Revision 1 R3); the VERDICT copies them, it does not re-judge them.

**Also reported (mandatory, Revision 1 R4):** n selected; win rate; the year-by-year table per
configuration (2016 → latest: n all, n selected, mean R selected, mean R all); per-feature
R-quintile spreads on the validation and test periods reported separately (univariate
diagnostics); and the headline (condition-1/2 numbers) recomputed with fill-bar exits
(hold == 0) dropped, as a robustness row.

## 8. Governance (draft, do not file)

- **Family:** Price-Learning **{L1}** (D-067). HYP-PM-0016 is a new member and inherits the {L1}
  multiplicity. **Census (R8):** the depth is unresolved — hardening carries 276 (D-070 context;
  D-070 adds no trials), the unratified recount (`broad_search_v2/recount/RECOUNT_W0` +
  `CENSUS_NOTE`) carries 561. **The primary pass bar freezes at the stricter count: 561 + 4 =
  565 → 3.2765**; the 280-count bar (3.07) is the secondary line. Ratifying the 561 census is a
  separate owner filing (not this study's act).
- **Why HYP-PM-0016 is admitted at all: D-070** (§Decision 2) — the last admitted price-feature
  study, because it filters an existing owner entry rule and its pre-registered baseline is a risk
  measure (low volatility).
- **Files:** `REGISTRATION_DRAFT.md` drafts the D-entry as **D-0xx**; the next free number at the
  time of writing is **D-071**; the owner assigns it at filing. HYPOTHESIS_REGISTRY,
  FAILURE_REGISTRY and DECISION_LOG are not edited by this study.
- **Forward test (record only, nothing built):** if a model passes, its frozen score becomes a
  forward test on the owner's live setups via jurnal26's `setup_outcomes` table (same X1/P0 rules,
  0.60% RT cost, outcomes in R). **Caveat to carry into any such handoff:** jurnal26 candidates
  come from 5001's feeds, not a full-market sniper scan — only the `watchlist`-sourced rows match
  E-SN's selection; the forward test should use that subset.

## 9. PIT tests (G0 gate; read no outcomes)

`test_pit_sniper_filter.py`: (a) every feature at s is **bit-identical** when the panel is
truncated at s; (b) the **embargo** holds (no training label's exit day within 20 sessions of the
refit year's first prediction); (c) the **selection threshold uses only setups strictly before s**
(mutation test: a future setup's extreme score cannot move a past selection); plus the rank
fallback rule, the M0 definition, the 60%-threshold arithmetic, and the zone-group consistency
check, on synthetic panels and hand-built trades. Run:
`pytest docs/research_programs/P-M/sniper_filter/test_pit_sniper_filter.py -v`.

## 10. Conventions beyond the brief's silence (declared; object at approval if not)

| id | convention |
|----|------------|
| C-1 | percentile = mid-rank (#{<x} + 0.5·#{==x})/n on the trailing-250 window's defined values |
| C-2 | rank fallback to the raw value only when the window has no prior setup or the own raw value is undefined; NaN stays NaN |
| C-3 | M0 excludes setups with an undefined rank component (counted in the RESULT); M1 imputes NaN with the train-window median; M2 uses NaN natively |
| C-4 | M1 probabilities from `predict_proba`; M2 from `predict_proba`; M0 is its declared rank mean |
| C-5 | **(superseded by Revision 1 R7)** feature 10 is `mkt_above_ma200` — the equal-weight market index cumulated from the owner-screen universe's mean daily close-to-close return (no IHSG dependence; full history) |
| C-6 | monthly aggregations (the Newey-West series, the halves, PBO matrix, year-by-year) key on the SETUP month (`tr["month"]`, the signal month — identical to the exit study's era keying) |
| C-7 | the pinned panel ends 2026-10-06; test period = 2021-10..latest complete setup on that panel |
| C-8 | **(superseded by Revision 1 R8)** primary census N = 565 (561 + 4), bar 3.2765; the 280 count (3.07) is the secondary report-only line |

Nothing else deviates from the brief. Any change to the frozen files after approval is a new,
disclosed, re-frozen run.

## 11. Revision 1 (2026-10-07, disclosed pre-approval revision — planner review of G0 `72b4bd5`)

**Status: NOT APPROVED as originally frozen; still read no outcomes.** The planner found the G1
runner defective (unreadable or discretion-opening) and ordered fixes in place on this branch, a
new sidecar, and this record. This is not a re-run and no outcome was touched. **The superseded
G0 sidecar is `PREDECLARATION.sha256` @ `72b4bd5`, file sha256
`fafaf4c97abfb8db3edc9aea6cf94657716752eb1d2d0f7e74cd776e2bbbcf89`** (kept in git history).

- **R1 — full-series selection.** `select_mask` was being called on split subsets, so every
  subset's trailing-250 windows started cold (the first test months got no validation history).
  Fixed: the mask is computed once per configuration on the FULL score series and indexed into
  val/test/PBO (§5). New test: full-series vs subset selections differ exactly as the cold-window
  bug predicts, and the pipeline uses the full-series value.
- **R2 — PBO matrix.** The old TRAIN+VAL matrix was ~180 all-NaN rows (scores exist only for
  prediction years ≥ 2016) — PBO meaningless. Fixed (§7.5): validation-months matrix only, months
  with no selection dropped and counted, `n_splits` frozen at 16 (≥ 2 rows/split), NaN asserted
  away before the call.
- **R3 — computed pass flags.** The RESULT now carries per-configuration booleans for conditions
  1–5 and `passes`; condition 4 uses the validation-chosen M1 only; h1/h2 must each be > 0;
  condition 5 is one grid-level PBO; the VERDICT copies the flags.
- **R4 — the "also report" list implemented.** Year-by-year table per configuration, per-feature
  R-quintile spreads (validation and test separately), the no-fill-bar robustness row, win rate.
  Proven on a synthetic dry run (`RESULT_SYNTHETIC_20261007T082258Z.json`, fake R — no real
  outcome touched).
- **R5 — fill-aware, strictly-earlier reference sets.** Ranks and thresholds now use setups with
  setup pos < p(s) AND fill bar index < p(s) (a fill watched for 20 sessions is not knowable at s
  until it happens; same-day setups no longer rank against each other in row order). New tests:
  a late-filling setup is excluded from a prior day's rank and threshold (the naive threshold
  would flip the selection); same-day setups get identical reference sets under both row orders.
- **R6 — the fingerprint gate runs BEFORE any outcome and cannot drift.** A read-only SQLite
  backup snapshot of the DB was taken into the scratch area (outside the repo):
  `/home/tjiesar/scratch/sniper_filter_g1/walkforward_snapshot_2026-10-07.db`, file sha256
  `c42c151e4a825f622349e42891b0083c5579f6816228e1452d9c5869de68d177`, whose dataset fingerprint
  equals **`f42275e3…` exactly** (max_date 2026-10-06, 1,101,826 rows — the backup captured
  G1FIX's data state). Both hashes are frozen in `sniper_filter.py` and verified (SystemExit)
  before any outcome is computed.
- **R7 — feature 10 replaced.** `ihsg_above_ma200` (constant 0.0 for all of training — no IHSG
  bar before 2021-07) is replaced by `mkt_above_ma200`: the equal-weight market index built from
  the panel (mean daily close-to-close return of the owner-screen universe, cumulated), 1.0 if
  above its 200-session MA at s. Feature count stays 10; the truncation test covers it.
- **R8 — the deflation bar, owner-ruled.** Primary pass bar: census **N = 561 + 4 = 565**, exact
  `emax_abs_z` = **3.2765** (561 → 3.2745 reproduced from the recount). The 280-count bar (3.07)
  is a secondary report-only line that can never pass a configuration (**owner ruling 560522a**).
  Ratifying the 561 census in DECISION_LOG is a separate owner filing.

Census re-run under the R5 reference-set definition (counts only — the filled-setup count is
unchanged at 3,682; the per-feature fallback/NaN counts are refreshed). Tests: 17 (all pass).
**Still gated on `SNIPER_FILTER_G1_APPROVED=1`; STOP for approval.**
