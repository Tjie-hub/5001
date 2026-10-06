# VERDICT — HYP-PM-0015 G1 (single run, 2026-10-06)

**Verdict: NULL — no model passes. The learned models do not beat the simple rule, and the
simple rule itself does not clear the program bar.** Per the predeclared null handling
(PREDECLARATION §10, REGISTRATION_DRAFT §1): the learned-rank question closes at G1. The
"only M0 passes" clause is NOT triggered (M0 fails condition 1).

- **Run:** one run, `run_id 167749f2791f4dd9bab8b3b19273b1db` (append-only `research_runs`),
  git commit `f4a84df9ba26aa3944f862204c856a10b5303e2f` (D-067 approval commit), driver
  sha256 `47752c25fcea51525ba44730934d87bf30cdb03a25eea900ffe9cc687c074efe` (verified before
  and at run time), PREDECLARATION sha256 `5d4dd3d81563…` (sidecar-matched).
- **Environment:** project venv (Python 3.12.3, numpy 2.4.4, pandas 3.0.2, sklearn 1.8.0 — the
  G0 freeze environment); all data access read-only; seeds 20261006 only.
- **Dataset fingerprint at run time:** `f3fc2ccf74906365…` (max_date 2026-10-05, 1,101,001
  final rows) vs G0 `1f5e85d5…` (1,100,914 rows): **+87 final rows, same max_date** — consistent
  with the 2026-10-05 session's bars finalizing between the G0 check (15:33) and the run
  (16:09; 912 final rows exist for 10-05 now). **Immaterial by construction:** every feature,
  label, and book return ends at the 2026-09-30 feature cutoff or the 2026-10-01 open (last
  test month's exit); no 10-05 bar enters any computation. Disclosed per PREDECLARATION §2.
- **Chosen configurations** (validation mean monthly rank IC): M1 = `m1_ridge_a10.0` (IC
  0.0489), M2 = `m2_hgbr_d3_lr0.05_i200` (IC 0.0543). No re-runs; any post-hoc change is a new,
  disclosed, re-frozen run.

## Report (PREDECLARATION §10 formats)

### Validation (2016-01 → 2021-09, 69 months) and Test (2021-10 → 2026-09, 60 months)

| model | period | mean rank IC | IC t | net excess vs base (%/mo) | Newey-West t (lag 3) | hit rate | turnover (%/mo) |
|---|---|---|---|---|---|---|---|
| M0 | val | 0.0405 | 1.63 | −0.458 | −1.01 | 50.7% | 30.1 |
| M0 | **test** | 0.0931 | 4.50 | **+0.451** | **1.20** | 53.3% | 26.5 |
| M1 (ridge α10) | val | 0.0489 | 2.14 | −0.508 | −1.02 | 46.4% | 30.4 |
| M1 | **test** | 0.1128 | 4.44 | **+0.204** | **0.42** | 55.0% | 24.8 |
| M2 (hgbr d3) | val | 0.0543 | 2.72 | +0.028 | 0.07 | 52.2% | 47.2 |
| M2 | **test** | 0.1086 | 4.81 | **+0.809** | **1.71** | 65.0% | 47.5 |

### Pass/fail on the TEST period (bar: Newey-West t ≥ 3.06 frozen; exact E[max|Z|] @ N=266 = 3.0558)

| condition | M0 | M1 (ridge α10) | M2 (hgbr d3 lr.05) |
|---|---|---|---|
| 1. net excess > 0 and NW t ≥ 3.06 | **FAIL** (t 1.20) | **FAIL** (t 0.42) | **FAIL** (t 1.71) |
| 2. beats M0, paired t ≥ 2 | — | **FAIL** (mean −0.247%/mo, t −0.59) | **FAIL** (mean +0.358%/mo, t 0.78) |
| 3. PBO < 0.5 | — | **FAIL** (PBO 0.5106) | **FAIL** (PBO 0.5106) |
| 4. leave-one-year-out > 0 | **PASS** (min +0.158%/mo) | **FAIL** (2022 −0.197%, 2026 −0.055%) | **PASS** (min +0.398%/mo) |
| **VERDICT** | **FAIL** | **FAIL** | **FAIL** |

### Year-by-year net excess vs the equal-weight base book, test period (%/mo, net of costs) — mandatory table

| year | M0 | M1 | M2 |
|---|---|---|---|
| 2021 (Oct–Dec) | +0.44 | +0.41 | +0.21 |
| 2022 | +1.62 | +1.81 | +2.45 |
| 2023 | +0.24 | +0.52 | +1.11 |
| 2024 | +0.64 | +0.03 | +0.54 |
| 2025 | **−1.03** | **−2.70** | **−1.30** |
| 2026 (Jan–Sep) | +0.89 | +1.67 | +1.58 |

2025 is the one common losing year (all three models negative; M1's worst month −9.17%/mo,
M2's −10.46%/mo in 2025-04/2025-09). M2's edge, such as it is, concentrates in 2022–2023.

### Overfitting statistics

- **PBO (CSCV-16, 6-configuration grid, validation monthly net returns): 0.5106** (> 0.5) —
  configuration selection was no better than chance out-of-sample; 64 of 69 months used,
  12,870 combinations. Condition 3 fails for both learned models.
- **DSR** (N = 266, sr_trials_std = 0.0466 across the grid's validation Sharpes 0.081–0.194):
  M1 0.280, M2 0.733 — reported, not gating; M2's test Sharpe (0.218/mo units) sits above the
  expected-max benchmark (0.133) but the PBO and the NW-t bar already dispose of the claim.

### Versus IHSG (reported, not gating; 60 test months, book net excess + base gross − IHSG)

M0 **+0.07%/mo**, M1 **−0.17%/mo**, M2 **+0.43%/mo**.

## Interpretation (honest reading, per the brief's stated purpose)

- The cross-section IS rankable on the test period — every model's monthly rank IC is positive
  with t 4.4–4.8 (M0's simple rule included, t 4.50). But the learned models do not rank better
  than the simple rule (M1's test IC 0.113 vs M0's 0.093; paired portfolio differences t ≤
  0.78), and no model converts ranking into top-quintile net excess at the program bar
  (best NW t 1.71 vs 3.06 required; the predeclared power statement anticipated exactly this —
  MDE 0.8–1.6%/mo vs observed 0.2–0.8%/mo).
- PBO 0.51 says the 6-configuration grid's validation ranking carried no out-of-sample
  information — the honest prior ("ends up close to low volatility plus momentum") is
  confirmed: nothing here beats M0, and M0 itself is not a tradeable edge over the base book
  at the deflation bar.
- **Filing consequence (owner acts):** per the predeclared null handling, the learned-model
  question closes; Price-Learning {L1} closes at G1 with HYP-PM-0015 NULL (both learned
  configurations) — the registry/DECISION_LOG/FAILURE_REGISTRY filing acts remain the owner's;
  the executor files nothing.

## Disclosures

1. **Fingerprint delta** (+87 final rows, same max_date 2026-10-05): late finalization of the
   newest session between the G0 check and the run; post-period by construction; disclosed
   above. G0's PIT evidence (bit-identity, embargo) was computed on the 15:33 panel state; the
   frozen loader is deterministic and the delta cannot touch any used price point.
2. **RESULT integrity:** `RESULT_20261006T090908Z.json` is exactly as written by the frozen
   driver — not post-edited. The instruction's "record git commit + driver sha256 in the
   RESULT" is satisfied by the run record itself (git commit IS in the RESULT; the driver
   sha256 was verified and printed at run start and is recorded here and in HANDOFF_G1.md,
   because editing the frozen driver to embed its own hash — or editing the RESULT after the
   fact — would both violate the freeze).
3. **Benign runtime warning:** one pandas `divide-by-zero in log` from `log_adv20` on
   zero-turnover bars (suspended names) → those cells are NaN and excluded by the
   feature-complete rule, as predeclared.
4. **Run audit:** fallback exits 52, full losses 0, no-entry 5 (of ~310 rebalance months ×
   ~150 names); base book never below 128 names.
