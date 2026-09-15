# EXP-PM-0009 — Execution Receipt (HL-1) · HYP-PM-0009 / I7

> Single registered execution of **HYP-PM-0009** (I7 · intraday execution timing), performed under the
> frozen registration `docs/research_programs/P-M/HYP-PM-0009_REGISTERED.md`
> (preregistration_sha256 `d19dfd0f…`), on Owner authorization conveyed 2026-09-15 after independent
> registration confirmation. No substantive registered field was modified before, during, or after
> execution. **This experiment is terminal: no rerun, rescue, variant, or re-cut is authorized.**

## 1 · Pre-execution integrity gate — 19/19 PASS

| Binding | Registered | Verified |
|---|---|---|
| Registry entry | HYP-PM-0009, REGISTERED | ✓ (`HYP-PM-0009_REGISTERED.md`, clean at commit `e0e3f91`) |
| Preregistration hash | `d19dfd0f6b05…f76b75a` over FROZEN block | ✓ recomputed, exact match |
| Cohort fingerprint (v004) | `e1375264133b42f4…8784fba` | ✓ `I7_V004_ADMISSIBLE_v1.sqlite`, exact match |
| Registered I7 spec | candidate sha `76a96545…` | ✓ `BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md`, exact match |
| Session calendars | base `5012be23…` (sidecar + embedded + in-store manifest), ext `a7a4eedf…` | ✓ |
| No post-registration change | none permitted | ✓ ledger exact/MECE in-store; X3 sessions match; all files clean vs `e0e3f91` |

## 2 · Run record

| Field | Value |
|---|---|
| **Run ID** | `EXP-PM-0009/R2` (the single valid registered execution) |
| **Execution timestamp** | 2026-09-15T01:41:30Z (in-script UTC) |
| **Code/commit provenance** | Repository at registration commit `e0e3f915cbcd80c06caa87f00cf2f7611d82f6e9`; executor `run_exp_pm_0009.py` (self-hashed into `results.json`); Python stdlib-only statistics (sqlite3/math/json) |
| **Registered-spec fingerprint** | preregistration_sha256 `d19dfd0f6b059a4b4c564361087bf9aa59e327c8105c5229e166afa64f76b75a` |
| **Input fingerprints** | cohort store `e1375264…fba`; candidate spec `76a96545…`; calendar base `5012be23…`, extension `a7a4eedf…`; outcome leg `data/walkforward.db` (ohlcv, corporate_actions; read-only URI + `PRAGMA query_only`) |

### R1 defect disclosure (retained, immutable)

A first invocation (`EXP-PM-0009/R1`, 2026-09-15T01:39:02Z) was **INVALID — implementation defect,
estimand not evaluated**: the exit-leg index was computed as `eff[i+k]`, which for k=1 equals the
*entry* session, so `fwd_return = close(t+1)/close(t+1) − 1 ≡ 0` for every cell (θ exactly 0.000000,
NW_t = NaN, p = NaN). The registered estimand was never computed; this is a mechanical code defect,
not a specification element (the frozen outcome `close(t+2)/close(t+1) − 1` was never altered).
R1's artifacts are preserved verbatim as `execution_r1_INVALID_defect.log` /
`results_r1_INVALID_defect.json`. The index was corrected to the registered formula
(exit `eff[i+1+k]`; X6 guard and CA window extended accordingly) and **R2 is the single valid
registered execution**. Determinism cross-check: R2's k=1 arm reproduces R1's accidental k=2 arm
exactly (θ 0.0337%, t 0.1102, p 0.912223), confirming the one-session-shift diagnosis. **No
specification, cohort, exclusion, estimator, threshold, or timing field changed between R1 and R2.**

## 3 · Admissibility and exclusion counts

**Accrual layer (registered ledger, verified in-store):** 82,814 candidate cells = 61,335 admitted
+ 7,038 X3 + 2,044 E-PIT-2 + 1,507 E-PIT-3 + 10,890 E-PIT-4 (exact, MECE, duplicate-free).

**Effective sample:** 76 sessions (2026-04-28..2026-09-11), 868 tickers, 19,793,865 bar rows.

**Signal layer:** population = net-buying days (daily_net > 0, 09:00..15:49 continuous session):
**24,187 cells** of 61,335.

**Estimation layer (k=1 primary; per-cell MECE, applied and counted as registered):**

| Rule | Cells |
|---|---|
| X6 — t, t+1, t+2 not strictly consecutive admitted sessions | 475 |
| X5 — corporate action in [t, t+2] | 256 |
| X5 — ticker RAJA | 19 |
| X5 — ohlcv close missing/unusable at t, t+1 or t+2 | 3,036 |
| X5 — close(t) < Rp 100 | 4,528 |
| X5 — PIT liquidity floor unmet (trailing-60-session median traded value, shift(1), < Rp 1e9 or insufficient history) | 9,845 |
| **X5 total** | **17,684** |
| **Surviving cells entering the estimator** | **6,028** |

Check: 24,187 = 475 + 17,684 + 6,028 (exact, MECE).

## 4 · Primary estimator output (k = 1, the ONE registered test)

| Quantity | Value |
|---|---|
| Daily series m(d) — formation dates with ≥ 1 LATE_TILTED and ≥ 1 EARLY_TILTED surviving cell | **64** |
| Dates skipped and counted (never zero-filled; includes 2026-09-08's single admissible cell, disposed by step_1) | **6** |
| **θ_primary** | **+0.000337 (+0.0337% per formation-day)** |
| Newey-West HAC t (lag = 5) | 0.1102 |
| Two-sided p (erfc convention) | **0.912223** |
| Holm-adjusted p (single cell — Holm at the primary is the identity) | 0.912223 |
| θ_net sensitivity = θ_primary − 0.006 (**sensitivity only, never a verdict**) | −0.5663% |

**Robustness horizons (non-confirmatory; may never become primary):**
k=2: θ = −0.0362%, t = −0.0905, p = 0.927881 (65 m-dates, 6,013 cells). k=3: θ = +0.2138%,
t = 0.5033, p = 0.614777 (63 m-dates, 5,923 cells). All far from significance; no sign consistency.

## 5 · Decision and classification (made exactly once)

Registered kill rule: *if θ_primary is not positive with two-sided p < 0.05, the hypothesis is
REFUTED and terminates as FAILED (mode F2 · prediction failure).*

θ_primary is nominally positive (+0.0337%) but two-sided p = 0.9122 ≥ 0.05. The kill condition is met.

## **CLASSIFICATION: FAIL (F2 · prediction failure)**

H0 : θ_primary ≤ 0 is not rejected at the registered one-sided decision (two-sided p = 0.9122;
nominal one-sided size 0.025). The prediction that within-session back-loading of net buying carries
information beyond the daily total is refuted at this specification on the v004 cohort. Per the
registered `no_rescue` rule this null is **terminal**; continuation only via T12 supersession (a new
registration consuming its own slot).

**Interpretation constraints (frozen, binding):**
- I7 carries **NO ex-ante power claim** (Owner ruling D-050). This non-rejection is **NOT evidence
  of absence** and must never be reported or used as one.
- θ is composite-H0-consistent: a negative θ would fall inside H0 as a non-rejection, never a
  reversed finding; here θ > 0 but statistically indistinguishable from zero.
- **R7 PIT provenance limitation remains disclosed**: PIT status rests on `stockbit_flow.updated_at`
  (this system's own writer, same-commit write timestamps, naive Asia/Jakarta). It supports
  contemporaneous custody and no-later-rewrite, **not** independent re-verification of the original
  vendor response — a VERIFICATION limitation, not an availability one (200/200 source spot-check
  matches, `I7_V004_SOURCE_PROVENANCE_v1.json`). Byte-for-byte reproduction from recorded inputs is
  impossible.
- custody_partition: in-sample · oos_partition: NONE · B4 (PPK/board) unidentifiable, liquidity floor
  is a mitigation not a solution.

## 6 · Reproducibility

Executor: `run_exp_pm_0009.py` (sha256 recorded inside `results.json.provenance.script_sha256`).
In-script integrity gate: 19/19 PASS at run time. Both databases opened read-only (URI `mode=ro` +
`PRAGMA query_only`); no DB writes. Full daily series, accounting, and decision inputs in
`results.json`; run transcript in `execution.log`. Determinism: pure stdlib arithmetic, no RNG, no
parallelism — re-execution of this script against the same fingerprint-bound inputs reproduces
`results.json` exactly.

**Status: EXECUTED ONCE (valid run R2). CLASSIFICATION FINAL: FAIL (F2). STOPPED — no investigation,
modification, rerun, rescue, or variants authorized.**
