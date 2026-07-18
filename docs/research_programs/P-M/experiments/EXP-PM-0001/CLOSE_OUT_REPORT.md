# EXP-PM-0001 — Close-Out Report

**Date:** 2026-07-18 · **Author:** Research Director / CRO · **Scope:** post-execution close-out of the confirmatory experiment for HYP-PM-0001. **No experimental result was modified; the experiment was not re-run.**

## 1. Outcome

| | |
|---|---|
| Experiment status | **COMPLETED** |
| Hypothesis terminal status | **FAILED** — mode **F2 · Prediction failure** (canonical term for "falsified", [[HYPOTHESIS_LIFECYCLE]] §3) |
| Decision basis | Frozen preregistered rule: *signed reversal ≤ 0 or < MDE ⇒ M1.1 REFUTED*. Primary k=15 gross = −0.0008%/trade (t=−0.35); net-of-cost = −0.6008%; robustness signs inconsistent ⇒ **refuted on sign alone and again net of cost** |
| Evidence product | **C2 competent refutation** (EV-9, N=1, in-sample), a first-class product (R12/PG-11) |

## 2. Verification performed (no results altered)

1. **Artifacts exist & internally consistent** — MANIFEST, results.json, execution.log, script present; the pre-registration/manifest/results all carry the same registration hash.
2. **Registration seal intact** — SHA-256 of the frozen bytes recomputed = `540c2d52…` (matches receipt) → the frozen hypothesis object is untampered.
3. **Anchors cross-checked** — commit `b970224…` = current HEAD; script sha `8cba58b6…` = on-disk; `run_utc 2026-07-18T01:09:37Z` identical in results.json and execution.log; dataset / analysis-row counts / k / friction identical across all documents. Full table in [[EVIDENCE_PACKAGE]] §6 → **PASS**.
4. **Decision rule applied verbatim** from the frozen record; single F-mode (F2) determined and defended against F4/F3/F5/F7 (R1).

## 3. Files created / modified by this close-out

**Created (governance):**
- `docs/research_programs/P-M/experiments/EXP-PM-0001/EVIDENCE_PACKAGE.md` — terminal evidence product; T5/T7 receipts; consistency audit
- `docs/research_programs/P-M/experiments/EXP-PM-0001/FAILURE_ENTRY.md` — O8 failure receipt (mandatory T7 receipt, immutable)
- `docs/research_programs/P-M/experiments/EXP-PM-0001/CLOSE_OUT_REPORT.md` — this report
- `docs/research_programs/FAILURE_REGISTRY.md` — institutional append-only failure ledger (new)

**Modified (governance):**
- `docs/research_programs/HYPOTHESIS_REGISTRY.md` — HYP-PM-0001 status advanced REGISTERED → FAILED; execution note added

**NOT modified (immutable — added to git for the first time by this close-out, sealing them):**
- `EXP-PM-0001/results.json`, `EXP-PM-0001/execution.log` — experimental results, untouched
- `EXP-PM-0001/MANIFEST.md`, `EXP-PM-0001/run_exp_pm_0001.py` — frozen pre-execution artifacts, untouched

## 4. Next legitimate step

FAILED is terminal (HL-3). No re-run, no parameter/k/filter change (X2–X5, R15). Continuation, if any, is **T12 → SUPERSEDED**: a *new* hypothesis (new G1, counted afresh in the P-M family), e.g. testing M2.1 adverse-selection permanence (I7), or re-opening inventory mean-reversion under higher-fidelity (LOB) flow. HYP-PM-0001 remains counted in the family denominator (X8).

## 5. Proposed commit (not yet made)

One commit sealing the close-out and the previously-uncommitted experiment artifacts together:

```
docs(P-M/EXP-PM-0001): close-out — HYP-PM-0001 FAILED (F2), C2 refutation

Experiment COMPLETED; hypothesis REGISTERED→IN_TESTING→FAILED per frozen rule
(primary k=15 signed reversal -0.0008%/net -0.6008%; robustness sign-inconsistent).
Adds Evidence Package, Failure Entry (O8/T7 receipt), Failure Registry; advances
Hypothesis Registry. Results/manifest/script untouched; sealed by this commit.
```
