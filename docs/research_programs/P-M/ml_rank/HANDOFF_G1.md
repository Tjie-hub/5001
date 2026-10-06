# HANDOFF_G1 — HYP-PM-0015 single run complete; NULL; stopped for review

**Date:** 2026-10-06 · **Branch:** `research/ml-rank-2026-10` @ `f4a84df9ba26aa3944f862204c856a10b5303e2f`
(D-067 approval commit on top of the G0 freeze `f16aa9e749b122dd1383e7758874f718190a62fc`).
**One run was executed, as approved. No re-runs. Executor stops here.**

## 1. Run record

| field | value |
|---|---|
| run_id (research_runs, append-only) | `167749f2791f4dd9bab8b3b19273b1db` |
| git commit at run | `f4a84df9ba26aa3944f862204c856a10b5303e2f` (= HEAD, in RESULT) |
| driver sha256 (verified pre-run AND printed at run start) | `47752c25fcea51525ba44730934d87bf30cdb03a25eea900ffe9cc687c074efe` |
| PREDECLARATION.md sha256 | `5d4dd3d81563339372d00e2428fb24d5eb8c4267934188e60fe98a54f33a9ccd` (sidecar-matched) |
| interpreter | project venv `…/idx-walkforward-5001/venv` (Python 3.12.3, numpy 2.4.4, pandas 3.0.2, sklearn 1.8.0 — the G0 freeze environment) |
| data access | read-only (`DB_PATH`/`RESEARCH_DB_PATH`/`ML_RANK_*_PKL` pointed at the main tree; `mode=ro` DB handles) |
| RESULT | `RESULT_20261006T090908Z.json` — exactly as written by the frozen driver, not post-edited |
| exit | 0; one benign pandas log(0) RuntimeWarning (disclosed in VERDICT §Disclosures 3) |

The instruction's "record git commit + driver sha256 in the RESULT": the git commit IS in the
RESULT (driver-written field); the driver sha256 is recorded here and in VERDICT.md because
embedding it would have required editing the frozen driver and post-editing the RESULT would
violate run integrity. The run-start stdout carries the verified hash as extra evidence.

## 2. Outcome (full detail in VERDICT.md)

**NULL — no model passes; M0 does not pass either.**

- Test-period net excess vs base book: M0 +0.451%/mo (NW t 1.20), M1 +0.204%/mo (t 0.42),
  M2 +0.809%/mo (t 1.71) — all below the frozen bar 3.06.
- Learned vs M0 paired: M1 −0.247%/mo (t −0.59), M2 +0.358%/mo (t 0.78) — the learning adds
  nothing detectable over the simple rule.
- PBO 0.5106 (> 0.5) — configuration selection carried no OOS information.
- LOYO: M0 and M2 positive in every leave-one-year-out cut; M1 negative in 2022 and 2026.
- vs IHSG (reported): M0 +0.07%/mo, M1 −0.17%/mo, M2 +0.43%/mo.
- Rank IC on test is genuinely positive for all models (t 4.4–4.8) — the cross-section is
  rankable, but not convertible into bar-clearing net excess, and not better ranked by learning
  than by the pre-declared two-rank rule. The brief's honest prior is confirmed.

## 3. Dataset fingerprint delta (disclosed, per PREDECLARATION §2)

G1 fingerprint `f3fc2ccf…` (1,101,001 final rows, max_date 2026-10-05) vs G0 `1f5e85d5…`
(1,100,914 rows, same max_date): **+87 final rows** — consistent with the 2026-10-05 session
finalizing between 15:33 (G0 check) and 16:09 (run); 912 final 10-05 rows exist now. Every
feature, label, and book return ends at the 2026-09-30 cutoff or the 2026-10-01 open, so no
10-05 bar enters any computation — immaterial by construction, recorded for the ledger.

## 4. What the owner may want to do next (executor files nothing)

- File the NULL per the predeclared handling: Price-Learning {L1} closes at G1 with
  HYP-PM-0015 NULL (both learned configurations); FAILURE_REGISTRY row draft is in
  REGISTRATION_DRAFT.md §4; DECISION_LOG amendment text is the owner's act.
- The 6 grid arms enter the program census at filing (raises the next gate's bar; bar
  recomputation is the owner's, per the D-062/CENSUS_UPDATE convention).
- No follow-up runs, variants, or refinements are permitted off this run (brief: any fix after
  G1 is a new, disclosed, re-frozen run that counts as a new trial).

## 5. Governance state at stop

- Registries/DECISION_LOG untouched by the executor (D-067 was the owner's commit).
- Production untouched; ~/jurnal26 and research/broad-search-v2-zcode untouched; no secrets
  printed; the only write was the sanctioned append-only `research_runs` row + this branch's
  RESULT/VERDICT/HANDOFF files.
- Branch state to be pushed: RESULT_20261006T090908Z.json + VERDICT.md + this file, nothing
  else; driver/tests/PREDECLARATION byte-identical to the G0 freeze (hashes re-verified
  pre-run).
