# Failure Registry

> The institutional repository of falsified hypotheses and failed experiments ([[FAILURE_LIBRARY_SCHEMA]]). **Append-only and immutable** — a failure entry is never edited or deleted (HL-1, R12). Preserving negative results maps the boundaries of market efficiency and keeps the family denominator honest (OS-10). A refutation is a first-class product (PG-11), not a defect.

**Owner:** Chief Research Officer · **Last updated:** 2026-09-11 · **Governed by:** [[FAILURE_LIBRARY_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]]

## Entries

| failure_id | hypothesis_ref | mechanism | experiment_ref | mode | archived | record |
|---|---|---|---|---|---|---|
| **FAIL-PM-0001** | HYP-PM-0001 | M1.1 inventory-imbalance mean reversion (I5) | EXP-PM-0001 (`run_utc` 2026-07-18T01:09:37Z) | **F2 · Prediction failure** | 2026-07-18 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PM-0003** | HYP-PM-0003 | M2.1 adverse-selection permanence (I7), `broker_flow`/Dataset A instrument | EXP-PM-0003 (`run_utc` 2026-09-09T09:44:17Z) | **F2 · Prediction failure** | 2026-09-09 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PA-0001** | HYP-PA-0001 | MECH-recon-dislocation · reconstitution closing-auction dislocation (I8→I2) | EXP-PA-0001 (`results.json` sha256 `27dac1ec…`) | **F2 · Prediction failure** | 2026-08-19 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PM-0004-G1** | HYP-PM-0004 | C2 conduit disagreement (C-family) | G1 Run 1 (`G1_REAL_OUTPUT_RUN1_2026-09-11.json` sha256 `74883c04…`) | **INVALID · governance** — registered species-mix control unimplementable (freq-dependent); executed unconditional contrast is not the designed conditional estimand; NOT CONFIRMED (Holm p = 1.0) | 2026-09-11 | DECISION_LOG D-048 · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` |
| **FAIL-PM-0005-G1** | HYP-PM-0005 | C3 breadth surprise (C-family) | G1 Run 1 (same output) | **NOT CONFIRMED (VALID, bounded)** — primary k=5 θ = +5.8 bp, NW t = +0.323, Holm p = 1.0; determinate null at 329 daily observations; signs +/+/−; net of 0.60% floor ≈ −54 bp | 2026-09-11 | DECISION_LOG D-048 · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` |

## Failure-mode distribution (institutional self-diagnostic — §5.3)

| Mode | Count | Note |
|---|---|---|
| F1 Mechanistic incoherence | 0 | |
| **F2 Prediction failure** | **3** | FAIL-PM-0001, FAIL-PM-0003, FAIL-PA-0001 |
| F3 Multiplicity collapse | 0 | |
| F4 Cost destruction | 0 | |
| F5 Regime artifact | 0 | |
| F6 Provenance failure (VOID) | 0 | |
| F7 Look-ahead contamination | 0 | |
| F8 Capacity extinction | 0 | |
| F9 Decay (not an error) | 0 | |
| INVALID · governance (outside F1–F9) | **1** | FAIL-PM-0004-G1 — governance-invalidated arm, recorded for denominator honesty; not an F-mode |
| NOT CONFIRMED (registered no-rescue vocabulary) | **1** | FAIL-PM-0005-G1 — valid bounded null at the registered inference |

> N=5 (4 failure-classified + 1 governance-invalidated + 1 valid bounded null). All F2 entries died at short-to-swing horizons against the same 0.60% round-trip friction — a program-level pattern (horizon/friction mismatch) that no single F-code expresses. Recorded here because the distribution alone will not surface it. The two 2026-09-11 G1-family rows (FAIL-PM-0004-G1, FAIL-PM-0005-G1) receipt the first C-family empirical outcome per DECISION_LOG D-048: C2 governance-invalidated, C3 a valid bounded null — neither is a rescue of the other, and the withdrawn C1a/C1b produced no numbers.

## Notes

- **FAIL-PM-0001** — first entry in the P-M program. HYP-PM-0001 remains **counted in the P-M family {I5,I6,I7,I12}** (X8: a failure never reduces the denominator). Terminal; continuation only via T12 supersession — a *new* registration.
- **FAIL-PM-0003** — second REGISTERED member of the P-M family (Option B, OS-10, CRO-adopted 2026-09-09 — independent counting; `HYP-PM-0002` remains unregistered and consumes no slot). Tested M2.1 (I7) via `broker_flow`/Dataset A (FROZEN, D-043, `provenance_hash 329b22e49f0e…`), the **same taxonomy entry** `HYP-PM-0002`'s own (unregistered, unexecuted) draft targets via a different instrument (`stockbit_flow_bars`). **Preserved caveat:** observation-level independence between the two datasets is unresolved (A-PM3.3) — this result is not, by itself, separable evidence from `HYP-PM-0002`'s eventual result; any future joint reading must carry the caveat forward. HYP-PM-0003 remains **counted in the P-M family** (X8). Terminal; continuation only via T12 supersession.
- **FAIL-PA-0001** — first entry in the P-A program. HYP-PA-0001 remains **counted in the P-A family {I2,I3,I8}** (X8). Terminal; continuation only via T12 supersession. Note the family is more consumed than a 1-of-3 member count implies: the taxonomy records I8 as causally upstream of I2 (LIM3 — shared observations, not independent evidence) and I3 as competing with I2 for the same session-boundary observations.
