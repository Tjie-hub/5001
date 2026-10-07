# PREDECLARATION — HYP-PM-0015 (draft): price-learning cross-sectional ranking model

**Status:** frozen before any outcome is computed · **Date:** 2026-10-06 ·
**Authority:** brief `ZCODE_BRIEF_ML_PRICE_RANK_2026-10-06.md` (fix/telegram-curation @ 0f7e627).
**Branch:** `research/ml-rank-2026-10` from `origin/research/new-order-2026-09-30` (062999d).
Two gates: **G0 = this freeze** (no model is fit on returns); **G1 = one single run** after the
owner, via the planner, approves this file — one run, one RESULT, one VERDICT, then stop for
review. Re-running with changed settings after seeing results is forbidden; any post-G1 fix is a
new, disclosed, re-frozen run that counts as a new trial. **Separate from Broad search v2** (own
reviewer, own branch `research/broad-search-v2-zcode`): untouched, not counted here.

## 1. Hypothesis (mechanism)

No existing P-M family covers a **learned combination of price/volume features** used to rank
stocks cross-sectionally. HYP-PM-0015 (draft; owner files it at G0): a small, fixed model family
(ridge / shallow gradient boosting) trained on cross-sectional feature ranks can rank the
next month's returns better than the pre-declared simple rule M0 (low Parkinson-60 volatility +
12-1 momentum). Honest prior: it ends up close to "low volatility plus momentum"; the value is
finding that out cleanly under program governance. Proposed family: **Price-Learning {L1}**
(REGISTRATION_DRAFT.md).

## 2. Data (frozen)

- `research.rulecard.data.load_extended_ohlcv(issuance=True)`: the pre-2021 yfinance backfill
  (regenerated 2026-09-23, D-053) + the settled DB corpus (is_final=1, from 2021-07-05), with the
  gap-verified split repair (D-053 machinery) and the rights/bonus/reverse-split holder-wealth
  correction (D-064). 2000-03-30 → latest final bar.
- Observed at G0 (pit_check_real.py, 2026-10-06): panel 6,595 sessions × 958 tickers,
  2000-03-30 → 2026-10-05; dataset fingerprint sha256 `1f5e85d50c183e7206c0b8b8f89ed61100a2051f814cfb59bbfab39b29aa2d96`
  (max_date 2026-10-05, 1,100,914 corpus rows; full structured fingerprint in PIT_CHECK_G0.json).
  G1 re-records the fingerprint via `research.tracking.track_run` — if it differs from the G0
  value beyond the max_date roll-forward, that is disclosed in the RESULT.
- **IHSG exists in the corpus only from 2021-07-05** (verified: no IHSG/^JKSE in the backfill;
  1,262 DB bars 2021-07-05 → 2026-10-05). Consequences are predeclared in §5 (D-1) and §6.

## 3. Universe at each rebalance (frozen; pattern-study parity)

At each monthly rebalance, evaluated on data through the **prior session's close only** (cutoff
row t = the panel row before the entry session):

- top **150** by 60-session mean turnover `C×V` (rolling mean, min_periods 40, cross-sectional
  rank ascending=False);
- adjusted-panel close **≥ 50** (identical semantics to the 2026-09/10 pattern studies, which
  gate the same loader's adjusted prices — disclosed, not a nominal-price gate);
- traded on **≥ 18 of the last 20 sessions** (count of finite closes, rolling 20, min_periods 20).

This is the same universe construction as `Claude outputs/bos_study_2026-10-06/bos_study.py`
(rank of rolling-60 mean of C·V ≤ 150, C ≥ 50, present ≥ 18/20), re-derived as pure functions.

## 4. Price handling (disclosed before any read)

- Split/issuance adjustments are **back-adjustments applied once at dataset-build time** (the
  loader's contract). A 2026-built panel rescales pre-event bars with factors from events after
  those bars; within any feature window a factor constant to the whole window leaves every
  feature invariant, and at ex-dates the correction makes returns wealth-true (the D-064
  estimand). The only non-invariant is the close ≥ 50 gate, which is therefore an
  adjusted-price gate by design (parity with the pattern studies, §3).
- The loader's vendor-error cleaning (centered glitch median, backfill only) runs at build time,
  outside the per-rebalance decision path. PIT test (a) truncates the **cleaned, frozen** panel;
  the cleaning is part of the dataset, not of the trading decision.
- Issuance correction is ON (`issuance=True`), per the brief and D-064 §D.

## 5. Features (all 14, frozen; each used as a cross-sectional rank in [0, 1])

Computed at the cutoff row t (last session before the entry month), causal windows only,
min_periods = full window. r = daily close-to-close simple return.

| # | name | definition at t |
|---|------|-----------------|
| 1 | ret5 | C_t / C_{t−5} − 1 |
| 2 | ret21 | C_t / C_{t−21} − 1 |
| 3 | ret63 | C_t / C_{t−63} − 1 |
| 4 | ret126 | C_t / C_{t−126} − 1 |
| 5 | mom12_1 | C_{t−21} / C_{t−252} − 1 (12-month minus 1-month momentum) |
| 6 | park60 | sqrt( mean over 60 sessions of ln(H/L)² / (4 ln 2) ) — Parkinson |
| 7 | rv20 | std (ddof=1) of ln returns over the last 20 sessions |
| 8 | maxret21 | max daily simple return over the last 21 sessions ("lottery") |
| 9 | dist52w | C_t / max(C over 252 sessions) − 1 (≤ 0) |
| 10 | log_adv20 | ln of the 20-session mean of C×V |
| 11 | adv_ratio | ADV20 / ADV120 (means of C×V, 20 and 120 sessions) |
| 12 | beta252 | 252-session rolling beta of r to the market series M (below) |
| 13 | idio_vol | sqrt( max( var252(r) − beta252²·var252(M), 0 ) ) |
| 14 | atr14_ratio | ATR14 / C_t; ATR14 = 14-session mean of TR, TR = max(H−L, |H−C_{t−1}|, |L−C_{t−1}|) |

**Deviation D-1 (disclosed, requires owner acknowledgment at G0 approval):** the brief specifies
"252-day beta to IHSG" and "idiosyncratic volatility relative to IHSG", but the frozen corpus
contains **no pre-2021-07 IHSG** (§2), so an IHSG-beta feature would be structurally NaN for the
entire 2001–2022 training era and cannot support "train from 2001". Frozen implementation: a
single market series **M = the equal-weight mean daily simple return of ALL panel names with a
finite return that session**, used for beta252/idio_vol over the whole sample (consistent across
validation and test; panel-native; PIT-causal: session s uses only session-s returns). The
actual IHSG series is used only for the reported (non-gating) IHSG benchmark (§6). Alternatives
considered and rejected at G0: dropping the two features (changes the hypothesis content);
splicing IHSG forward of 2021-07-05 (feature definition changes mid-test). At G1 the post-2021
IHSG-beta is reported beside the proxy-beta as observability (no gate).

Feature ranks: at each rebalance, percentile rank (average ties) **among the feature-complete
eligible set** (all 14 finite ∧ §3 eligible). A name missing any feature is out of that month's
model input (counted in the RESULT audit).

## 6. Target, rebalance, portfolio, costs, benchmarks (frozen)

- **Rebalance:** monthly, the first panel session of each month. Features/eligibility use data
  through the prior session's close only. **Entry:** that first session's open. **Hold one
  month; exit:** the next month's first session's open (open-to-open).
- **Target (label):** the cross-sectional percentile rank (average ties) of the next month's
  open-to-open return, ranked among that month's feature-complete eligible set.
- **Return validity:** a name with no open at entry cannot be entered (excluded, counted).
  Exit fallback (predeclared): a name not trading at the exit session exits at its **last
  finite close on or before the exit session**; a name with no bar at all after entry books
  **−100%** for the month. Both fallback classes are counted in the RESULT audit. Training
  labels use **organic** returns only (exit open printed); fallback exits feed book returns,
  never labels.
- **Books:** long-only, equal weight. k = max(1, floor(n_fc / 5)) where n_fc = feature-complete
  eligible count; members = top-k scored names that can enter (skipping non-enterable names).
  The top-30 names of each model are reported (RESULT).
- **Costs:** 0.60% round trip × one-sided monthly turnover τ = 0.5·Σ|w_new − w_old|, charged to
  the model book. First formation carries τ = 1 (0.60% — a slight overcharge vs buy-only;
  conservative, disclosed).
- **Benchmark 1 (gating):** the equal-weight liquid **base book** — every §3-eligible name that
  can enter, equal weight, **gross of costs** (conservative: charging the benchmark's own
  turnover would raise our excess; its net variant is reported as observability).
- **Benchmark 2 (reported, not gating):** IHSG open-to-open over the books' own entry/exit
  dates, requiring an IHSG bar on the exact date (available for all test months; pre-2021 not
  observable, §2).

## 7. PIT properties (tested at G0; tests read no outcomes)

1. **(a) Feature bit-identity under truncation** — every feature at cutoff t is bit-identical
   (float64, NaN-aware) when the frozen panel is truncated at t. `test_pit_ml_rank.py`
   (synthetic, 4 cutoffs) and `pit_check_real.py` (real corpus, 10 cutoffs 2003–2025, all
   eras): **PASS**, PIT_CHECK_G0.json frozen.
2. **(b) Embargo** — a training label month m's return window [open(m), open(m+1)] ends at the
   first session of m+1; the yearly refit is computed before its first prediction month, so
   labels require next(m) < first prediction month. For a January refit the last training label
   is November (the December return is never a training label). Verified on the real calendar:
   27 refits, 0 violations (PIT_CHECK_G0.json).
3. **(c) Universe at D uses only data up to D−1** — a name that becomes eligible only ON the
   entry session is not in that month's universe; universe identity under truncation verified
   (synthetic targeted test + real-corpus identity at 10 cutoffs).

## 8. Splits (frozen; walk-forward, yearly refit, expanding window)

- **Train:** label months from 2001-01, expanding (feature rows from ≈2002-01; names/features
  as §5–§6).
- **Validation: 2016-01 → 2021-09** (read only for configuration selection).
- **Test: 2021-10 → latest complete month** (60 months at the 2026-09-30 panel edge), **read
  once at G1**.
- **Refit schedule:** one refit per calendar year Y, trained on label months ≤ (the month two
  before Y's first prediction month) — i.e. labels ≤ November Y−1 for a January start; the same
  refit serves validation months Jan–Sep 2021 and test months Oct–Dec 2021 (frozen configs).
- Selection: the single M1 and the single M2 configuration with the highest **mean monthly
  rank IC on validation** (rank IC = Spearman between predicted scores and realized next-month
  open-to-open returns, by hand with average ties, over the month's feature-complete set);
  ties break to the earlier grid slot. Validation never gates pass/fail.

## 9. Models (frozen grid; ≤ 6 configurations across M1 and M2)

- **M0 (baseline, no learning):** score = 0.5·(1 − rank(park60)) + 0.5·rank(mom12_1).
- **M1:** sklearn `Ridge(alpha=α, fit_intercept=True)` on the 14 feature ranks; α ∈
  {0.1, 1.0, 10.0}.
- **M2:** sklearn 1.8.0 `HistGradientBoostingRegressor`, early_stopping=False,
  random_state=20261006, other parameters at defaults; configurations:
  (max_depth=2, lr=0.05, max_iter=200), (max_depth=3, lr=0.05, max_iter=200),
  (max_depth=3, lr=0.10, max_iter=100).
- No other model, no additional features, no re-tuning. Seeds fixed (SEED=20261006; no other
  RNG anywhere in the driver).

## 10. Statistics reported and pass bar (frozen)

Reported for M0, M1, M2 on validation and on test: mean monthly rank IC and its one-sided t;
top-quintile net-of-cost excess over the base book with **Newey-West t (Bartlett, lag 3**;
statsmodels is not installed — predeclared hand implementation, biased autocovariances);
hit rate; mean monthly turnover; the worst 12 months; the **year-by-year table**.

- **PBO** via `research.statistics.pbo_cscv` (CSCV, n_splits=16) over the full 6-configuration
  grid's monthly validation NET returns.
- **DSR** via `research.statistics.deflated_sharpe_ratio` at multiplicity N=266, with
  `sr_trials_std` = the cross-configuration std of the grid's own validation Sharpe (monthly
  net) — computed at G1, reported for M1/M2.

**A model PASSES only if all of these hold on the TEST period:**
1. Net top-quintile excess over the base book > 0 with Newey-West t ≥ **3.06** (frozen
   deflation bar, §10.1);
2. Beats M0 on paired monthly net-excess differences, one-sided t ≥ 2 (else the learning adds
   nothing);
3. PBO < 0.5;
4. Leave-one-year-out: dropping each test calendar year in turn leaves mean net excess > 0
   (not carried by one year);
5. Positive vs IHSG — **reported, not gating** (corollary of D-065 §3 and BM-1).

M0's verdict uses conditions 1 and 4 (2 and 3 are learning-specific). **If only M0 passes, that
is a valid finding**: the simple rule is the edge and is reported as such.

### 10.1 Deflation bar (computed at G0 with the repo's method, frozen)

- Repo method (D-062 `deflation_audit.py`, CHECKER_REVIEW_2026-09-29, D-064): the bar for a
  |t| statistic at multiplicity N is the **exact expected maximum E[max|Z|] of N iid standard
  normals**, E[M] = ∫₀^∞ [1 − (2Φ(x)−1)^N] dx (numerically integrated at G0):
  **N=252 → 3.0395; N=266 → 3.0558; N=270 → 3.0603.**
- Census: 252 (D-062, 2026-09-28) + 14 broad-search arms (CENSUS_UPDATE.md, 2026-09-29) =
  **266**, the brief-pinned N; +4 XP-001 arms recorded 2026-09-30 (POWER_BENCHMARK_MEMO) → 270.
- **Frozen bar: 3.06** — the brief's declared value and the D-064 program bar. It is the
  stricter of the brief's declaration vs the exact N=266 value (3.0558), and correct to 2 dp at
  both census depths. Freezing the exact 3.0558 would loosen the brief's bar; not permitted.
- Going forward: this predeclaration's own grid (6 arms; M0 uncounted as a baseline) enters the
  program census at the owner's filing act and raises the bar for the NEXT gate.

## 11. Honesty statements (before the run)

- **Survivorship:** the corpus backfill covers names still listed in 2026-09 (54/929 end
  early). For a LONG-only ranking book this biases levels UP (delisted names vanish rather than
  booking their final losses; mitigated but not eliminated by the §6 exit fallback). The
  primary gate is the **excess vs the equally-biased base book**, which is internally
  consistent; any absolute-level claim carries the caveat, and the forward test adjudicates.
- **Power (R5):** at 60 test months and a monthly excess σ of 2–4%/mo, the MDE at the frozen
  bar is ≈ 3.06·σ/√60 ≈ **0.8–1.6%/mo**. A real but modest learned tilt (the honest prior is
  "close to low-vol + momentum", ≈ 0.3–0.75%/mo) will most likely FAIL the bar even if genuine.
  Expected verdict on a true small effect is therefore NULL; this is the census-priced cost of
  the program bar, accepted here before the run.
- **Selection honesty:** validation is used only to pick one M1 and one M2 configuration; the
  grid's multiplicity is carried by PBO (over all 6) and DSR (N=266). Test is read once.
- **No outcome was read at G0:** no monthly return label was computed on real data before this
  freeze; `pit_check_real.py` computes features/eligibility only.

## 12. Governance

- Registration drafted as **HYP-PM-0015** with family proposal **Price-Learning {L1}** in
  `REGISTRATION_DRAFT.md` (draft only — HYPOTHESIS_REGISTRY.md / FAILURE_REGISTRY.md /
  DECISION_LOG.md are NOT edited by this task; the owner files them at G0 approval).
- Code: `docs/research_programs/P-M/ml_rank/` (driver `ml_rank_model.py`, PIT tests
  `test_pit_ml_rank.py`, real-corpus check `pit_check_real.py`). Research-side only; no
  production imports (tests/test_architecture_boundary.py: 3/3 PASS on the branch); the only DB
  access is read-only; the only write at G1 is the append-only `research_runs` ledger row.
- **G1 is machine-gated:** `run_g1()` refuses to run unless the environment carries
  `ML_RANK_G1_APPROVED=1` (set by the owner/planner at approval). One invocation, one
  RESULT_<utc>.json, one VERDICT.
- Production untouched; no service restarts; `logs/TELEGRAM_OFF` stays; ~/jurnal26 and
  research/broad-search-v2-zcode untouched.

## 13. Deviations from the brief (declared)

| id | deviation | why |
|----|-----------|-----|
| D-1 | beta252/idio_vol use the EW-panel market proxy M for the full sample instead of IHSG | no pre-2021-07 IHSG in the frozen corpus (§2); consistency across train/val/test preferred over a mid-test feature seam; IHSG kept for the reported benchmark |
| D-2 | close ≥ 50 gate operates on the adjusted panel | pattern-study parity (the brief's own universe definition); disclosed in §3/§4 |
| D-3 | first-formation month charged the full 0.60% RT | conservative rounding of the cost rule (§6) |
| D-4 | exit fallback (last close ≤ exit; −100% if never traded again) | the brief is silent on suspended exits; frozen before any read (§6) |
| D-5 | bar frozen at 3.06 (brief's value) rather than the exact 3.0558 @ N=266 | "may tighten, not loosen" (§10.1) |

Nothing else deviates. Any post-approval change to this file or the driver invalidates the
freeze and re-opens G0.
