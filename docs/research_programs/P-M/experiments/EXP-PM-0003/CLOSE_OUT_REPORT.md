# EXP-PM-0003 — Close-Out Report

**Date:** 2026-09-09 · **Author:** Research Director / CRO · **Scope:** post-execution close-out of the confirmatory experiment for HYP-PM-0003. **No experimental result was modified; the experiment was not re-run.**

## 1. Outcome

| | |
|---|---|
| Experiment status | **COMPLETED** |
| Hypothesis terminal status | **FAILED** — mode **F2 · Prediction failure** (canonical term for "falsified", [[HYPOTHESIS_LIFECYCLE]] §3) |
| Decision basis | Frozen preregistered rule: *bootstrap CI on net-of-cost signed continuation does not exclude zero, or point estimate < 0.60% floor ⇒ M2.1 REFUTED*. Primary k=7 gross = `+0.0538%`, CI95 `[-0.0656%, +0.1768%]` (includes zero); net-of-cost = `-0.5462%` ⇒ **refuted on CI alone and again net of cost** |
| Evidence product | **C2 competent refutation** (EV-9, N=1, in-sample per D-046/D-047) — a first-class product (R12/PG-11) |

## 2. Verification performed (no results altered)

1. **Artifacts exist & internally consistent** — MANIFEST, results.json, execution.log, script present; registration/manifest/results all carry the same registration hash (`a2db9204…`).
2. **Registration seal intact** — SHA-256 of the frozen bytes recomputed this session = `a2db9204…` (matches receipt) → the frozen hypothesis object is untampered.
3. **Anchors cross-checked** — script sha `b32fde97…` unchanged since G2 review; `run_utc 2026-09-09T09:44:17Z` identical in results.json and execution.log; Dataset A fingerprint, roster hash, row count, k, friction identical across REGISTERED / MANIFEST / results.json / execution.log. Full table in [[EVIDENCE_PACKAGE]] §6 → **PASS**.
4. **Decision rule applied verbatim** from the frozen record; single F-mode (F2) determined and defended against F3/F4/F5/F7 (R1).
5. **Multiplicity and observation-dependence caveats preserved** — [[FAILURE_ENTRY]] `lessons_learned` and [[EVIDENCE_PACKAGE]] §7 both explicitly carry forward that this result is not independent evidence separable from `HYP-PM-0002`'s own, not-yet-executed I7 test (A-PM3.3), and that Option B/OS-10 independent multiplicity counting (CRO-adopted 2026-09-09) is unaffected by this outcome.

## 3. Files created / modified by this close-out

**Created (governance):**
- `docs/research_programs/P-M/experiments/EXP-PM-0003/FAILURE_ENTRY.md` — O8 failure receipt (mandatory T7 receipt, immutable)
- `docs/research_programs/P-M/experiments/EXP-PM-0003/EVIDENCE_PACKAGE.md` — terminal evidence product; T5/T7 receipts; consistency audit
- `docs/research_programs/P-M/experiments/EXP-PM-0003/CLOSE_OUT_REPORT.md` — this report

**Modified (governance):**
- `docs/research_programs/FAILURE_REGISTRY.md` — new entry `FAIL-PM-0003` appended; failure-mode distribution table updated (F2 count 2→3); Notes entry added
- `docs/research_programs/HYPOTHESIS_REGISTRY.md` — HYP-PM-0003 status advanced REGISTERED → FAILED; Family-slot ledger and Notes updated

**NOT modified (immutable — frozen artifacts, untouched by this close-out):**
- `EXP-PM-0003/results.json`, `EXP-PM-0003/execution.log` — experimental results, untouched
- `EXP-PM-0003/MANIFEST.md`, `EXP-PM-0003/run_exp_pm_0003.py` — frozen pre-execution artifacts, untouched
- `HYP-PM-0003_REGISTERED.md` — the frozen hypothesis specification, **not modified** by this close-out (status advancement is tracked in `HYPOTHESIS_REGISTRY.md` and this package, per the same precedent `HYP-PM-0001_REGISTERED.md` set — the sealed record itself never changes after registration)
- `data/walkforward.db` (Dataset A) — untouched; remains FROZEN (D-043)

## 4. Next legitimate step

FAILED is terminal (HL-3). No re-run, no parameter/k/instrument change (X2–X5, R15). Continuation, if any, is **T12 → SUPERSEDED**: a *new* hypothesis (new G1, counted afresh in the P-M family), e.g. re-examining I7 under a different instrument, horizon, or conditioning (subject to its own G1/G2 process). HYP-PM-0003 remains counted in the family denominator (X8). Separately and unaffected by this outcome: `HYP-PM-0002` remains an open, unregistered draft targeting the same I7 entry via `stockbit_flow_bars` — its own eventual G1/G2/execution path is untouched by this close-out.

## 5. Proposed commit (not yet made)

One commit sealing the close-out and the previously-uncommitted experiment artifacts together — **not executed by this task**:

```
docs(P-M/EXP-PM-0003): close-out — HYP-PM-0003 FAILED (F2), C2 refutation

Experiment COMPLETED; hypothesis REGISTERED->IN_TESTING->FAILED per frozen rule
(primary k=7 signed continuation +0.0538%, CI includes zero; net -0.5462% vs
0.60% friction floor). Adds Evidence Package, Failure Entry (O8/T7 receipt);
appends Failure Registry; advances Hypothesis Registry. Results/manifest/script/
registered hypothesis/Dataset A untouched; sealed by this commit.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```
