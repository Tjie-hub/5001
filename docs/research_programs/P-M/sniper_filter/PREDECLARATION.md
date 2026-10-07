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
| 10 | `ihsg_above_ma200` | 1.0 if IHSG close at s > its 200-session MA at s, else 0.0; **where the corpus has no IHSG bar at s (pre-2021-07) the raw value is 0.0** (declared fallback; the D-1-style limitation is disclosed — the feature is degenerate for early E1) |

**Cross-sectional rank:** each raw feature becomes a percentile rank among ALL filled E-SN setups
whose setup day falls in the **trailing 250 sessions before s** (positional window
[p(s)−250, p(s)−1] on the panel index; strictly before s — no same-day or future setups).
Percentile = (#{prior values < x} + 0.5·#{== x}) / n_prior, computed on the prior values that are
defined. **Fallback (declared):** where the rank is undefined — no prior setup in the window, or
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

## 5. Selection rule (frozen; identical for every model)

Take a setup if its score is in the **top 40%** of the scores of the filled E-SN setups in the
**trailing 250 sessions before s** (same positional window as §3; the threshold is the 60th
percentile of those prior scores, strictly before s — PIT-tested). If fewer than 5 prior setups
have scores in the window, the threshold falls back to the 60th percentile over ALL scored setups
with setup day strictly before s (declared). If no prior scored setup exists at all, the setup is
not selected (counted).

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

## 7. Pass bar (fixed now; evaluated on TEST only)

1. **Selected minus all filled:** mean R difference > 0, computed as the monthly mean difference
   with a **Newey-West t (lag 3) ≥ the deflation bar 3.07** (frozen: exact E[max|Z|] at the new
   census N = 276 + 4 configurations = **280** is 3.0713; N=279 under the D-067 M0-uncounted
   convention gives 3.0702 — both round to **3.07**; the stricter reading governs).
2. **The selected setups' own mean net R > 0.**
3. **Both halves:** the difference is > 0 in 2021-10..2023-12 AND in 2024-01..end.
4. **"Learning adds value" (M1/M2 only):** paired monthly t ≥ 2 vs M0 (selected-vs-selected
   monthly mean R). Otherwise M0's result is the finding.
5. **PBO < 0.5** over the grid via `research/statistics.py::pbo_cscv(matrix, n_splits=16)`, where
   the matrix is the 4 configurations' monthly selected-mean-R series over the TRAIN+VAL months.

**Also reported:** n selected; win rate; the year-by-year table (mandatory); R-quintile spreads
per feature (univariate diagnostics); and the headline recomputed with fill-bar exits
(hold == 0) dropped, as a robustness row.

## 8. Governance (draft, do not file)

- **Family:** Price-Learning **{L1}** (D-067). HYP-PM-0016 is a new member and inherits the {L1}
  multiplicity. **Census: 276 + 4 configurations = 280** (D-070 adds no trials). Note: D-067's
  convention excluded the M0 baseline from the census; this brief's literal "276 + the number of
  configurations" counts all four listed configurations. The bar is 3.07 either way; the owner
  resolves the convention at filing.
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
| C-5 | `ihsg_above_ma200` uses the DB IHSG series only (no proxy); pre-2021-07 → 0.0 (declared) |
| C-6 | monthly aggregations (the Newey-West series, the halves, PBO matrix, year-by-year) key on the SETUP month (`tr["month"]`, the signal month — identical to the exit study's era keying) |
| C-7 | the pinned panel ends 2026-10-06; test period = 2021-10..latest complete setup on that panel |
| C-8 | census N = 280 counts all 4 listed configurations (stricter bar governs; D-067's M0-uncounted convention noted) |

Nothing else deviates from the brief. Any change to the frozen files after approval is a new,
disclosed, re-frozen run.
