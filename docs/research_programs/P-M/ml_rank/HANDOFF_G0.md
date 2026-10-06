# HANDOFF_G0 — HYP-PM-0015 (draft) price-learning cross-sectional ranking model

**Date:** 2026-10-06 · **Branch:** `research/ml-rank-2026-10` (from
`origin/research/new-order-2026-09-30` @ 062999d) · **Executor:** ZCode, per
`ZCODE_BRIEF_ML_PRICE_RANK_2026-10-06.md`. **G0 is complete. No model was fit on returns. The
executor stops here; G1 runs only after owner approval.**

## 1. What is frozen (sha256, verified by two independent methods at freeze time)

| artifact | sha256 |
|---|---|
| `PREDECLARATION.md` | `5d4dd3d81563339372d00e2428fb24d5eb8c4267934188e60fe98a54f33a9ccd` |
| `ml_rank_model.py` (driver) | `47752c25fcea51525ba44730934d87bf30cdb03a25eea900ffe9cc687c074efe` |
| `test_pit_ml_rank.py` (PIT tests) | `16fb536a9e86f5d659fd8e0a2a015892a2e79328cdc16610cf18e428d46fa01a` |
| `pit_check_real.py` (real-corpus check) | `46b64432f0a22e9143a3292109298a5bcb501680e5c5fd3f0508103a414dab00` |
| `REGISTRATION_DRAFT.md` (HYP-PM-0015 + family + D-0xx draft) | `59f44a6f7661d3624db15180659c491f0c98a9a7433f312c4811bc68503161da` |
| `PIT_CHECK_G0.json` (real-corpus PIT evidence) | `f450e24f9af0f82d6cabcb138659f84785bed71ad891ea5996aae57fe9ff87ed` |
| `PREDECLARATION.sha256` sidecar | hash of PREDECLARATION.md (above) |

The freeze is also the git commit on this branch (record the commit sha at approval). Any change
to these files after approval invalidates the freeze and re-opens G0.

## 2. Deflation bar (frozen at G0 with the repo's method)

- Method: exact **E[max|Z|]** over N iid standard normals, ∫₀^∞ [1 − (2Φ(x)−1)^N] dx — the
  D-062/CHECKER_REVIEW/D-064 convention (the `(1−γ)Φ⁻¹+γΦ⁻¹` closed form in
  `deflation_audit.py::e_max_z` is the one-sided max variant; the program's |t| bar is the
  two-sided integral, CHECKER_REVIEW 2026-09-29: "3.04 at N=252, 3.06 at N=266" — reproduced
  exactly at G0).
- Computed at G0: **N=252 → 3.0395 · N=266 → 3.0558 · N=270 → 3.0603.**
- Census: 252 (D-062) + 14 (CENSUS_UPDATE 2026-09-29) = 266 = the brief-pinned N; +4 XP-001
  arms (recorded 2026-09-30, POWER_BENCHMARK_MEMO §5) → 270.
- **Frozen bar: 3.06** (the brief's declared value and the D-064 program bar — stricter than
  the exact 3.0558 @ N=266; the brief forbids loosening). Correct to 2 dp at both census depths.
- This registration's own 6 grid arms enter the census at the owner's filing act and raise the
  bar for the NEXT gate.

## 3. Configuration grid (frozen)

- **M0** (baseline, no learning): `0.5·(1 − rank(park60)) + 0.5·rank(mom12_1)`.
- **M1** — sklearn `Ridge(fit_intercept=True)` on the 14 feature ranks, target = next-month
  return's cross-sectional rank:
  | name | alpha |
  |---|---|
  | m1_ridge_a0.1 | 0.1 |
  | m1_ridge_a1.0 | 1.0 |
  | m1_ridge_a10.0 | 10.0 |
- **M2** — sklearn 1.8.0 `HistGradientBoostingRegressor(early_stopping=False,
  random_state=20261006)`:
  | name | max_depth | learning_rate | max_iter |
  |---|---|---|---|
  | m2_hgbr_d2_lr0.05_i200 | 2 | 0.05 | 200 |
  | m2_hgbr_d3_lr0.05_i200 | 3 | 0.05 | 200 |
  | m2_hgbr_d3_lr0.10_i100 | 3 | 0.10 | 100 |
- Selection: highest validation mean monthly rank IC per family; ties → earlier slot.
- SEED = 20261006 (the only RNG seed in the system; inside sklearn HGBR only).

## 4. Verification state at freeze

- `pytest docs/research_programs/P-M/ml_rank/test_pit_ml_rank.py` → **17/17 PASS** (synthetic
  PIT a/b/c, regression guards incl. the first-month `iloc[-1]` wraparound found and fixed by
  these tests, machinery smoke: full walk-forward + evaluate() on a synthetic panel, G1 gate
  refusal).
- `pytest tests/test_architecture_boundary.py` → **3/3 PASS** (no production↔research violations).
- `pit_check_real.py` on the real corpus (reads NO outcomes) → **ALL PASS** (PIT_CHECK_G0.json):
  features bit-identical under truncation at 10 cutoffs 2003–2025 (all eras), universe identity,
  embargo clean on the real calendar (27 refits, 0 violations, December never a January label).
- Panel observed: 6,595 sessions × 958 tickers, 2000-03-30 → 2026-10-05; dataset fingerprint
  sha256 `1f5e85d50c183e7206c0b8b8f89ed61100a2051f814cfb59bbfab39b29aa2d96` (max_date
  2026-10-05, 1,100,914 rows).

## 5. Estimated runtime

| step | estimate |
|---|---|
| PIT real check (measured) | 220 s (panel load dominates) |
| G1: panel load + features | ≈ 3–4 min |
| G1: walk-forward (11 refit years × 6 models; HGBR ≤ ~30k×14 rows) | ≈ 1–2 min |
| G1: books, NW t, PBO, DSR, tables | seconds |
| **G1 total** | **≈ 5–8 min** |

## 6. How G1 runs (after approval — owner/planner only)

```bash
cd <repo worktree on research/ml-rank-2026-10>
DB_PATH="<abs>/data/walkforward.db" \
ML_RANK_HIST_PKL="<abs>/docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl" \
ML_RANK_SPLITS_PKL="<abs>/docs/research_programs/P-M/data_gaps/data/split_hist.pkl" \
ML_RANK_G1_APPROVED=1 python3 -c \
  "import sys; sys.path.insert(0,'docs/research_programs/P-M/ml_rank'); \
   import ml_rank_model as M; M.run_g1()"
```

- The env overrides exist because the code-only worktree does not carry the gitignored data
  artifacts (73 MB backfill pickle; 14.7 GB production DB, opened **read-only**; splits pickle).
  In the main tree the defaults resolve and only `ML_RANK_G1_APPROVED=1` is needed.
- `run_g1()` refuses without `ML_RANK_G1_APPROVED=1`; records one append-only `research_runs`
  row (kind `HYP-PM-0015-G1`, git commit + dataset fingerprint + environment via
  `research.tracking`) and writes `RESULT_<utc>.json` next to the driver. Nothing else is
  written.
- If the G1 fingerprint differs from the G0 fingerprint beyond the max-date roll-forward, the
  RESULT must disclose it (predeclared, PREDECLARATION §2).
- After the single run: VERDICT.md + HANDOFF_G1.md, then STOP for review.

## 7. Decision points for the owner at G0 approval

1. **D-1 (needs explicit acknowledgment):** beta252/idio_vol use the equal-weight panel market
   proxy for the full sample because the frozen corpus has **no pre-2021-07 IHSG** (verified:
   backfill lacks IHSG/^JKSE; DB has 1,262 bars from 2021-07-05). Alternatives were rejected at
   G0 (dropping the features changes the hypothesis; splicing IHSG seams the feature mid-test).
   IHSG remains the reported non-gating benchmark.
2. **D-2..D-5** (adjusted-panel close≥50 parity; first-month full-RT cost; suspended-exit
   fallback; bar 3.06 vs exact 3.0558) — declared in PREDECLARATION §13, believed
   non-controversial; object at approval if not.
3. **Filing acts (owner, at approval):** file HYP-PM-0015 + Price-Learning {L1} in
   HYPOTHESIS_REGISTRY.md, the D-0xx entry in DECISION_LOG.md (draft text in
   REGISTRATION_DRAFT.md), and add the 6 grid arms to the trial census.
4. **Bar sensitivity:** at N=270 the exact bar is 3.0603 → still 3.06 at 2 dp; no action needed.

## 8. Governance state

- Production untouched; no service restarts; `logs/TELEGRAM_OFF` untouched; ~/jurnal26 and
  research/broad-search-v2-zcode untouched; HYPOTHESIS_REGISTRY / FAILURE_REGISTRY /
  DECISION_LOG untouched by the executor.
- The only writes made by this task: the files under `docs/research_programs/P-M/ml_rank/` on
  the new branch, and read-only DB opens. The G1 ledger row is the single sanctioned write at
  the next gate.
