# Failure Registry

> The institutional repository of falsified hypotheses and failed experiments ([[FAILURE_LIBRARY_SCHEMA]]). **Append-only and immutable** — a failure entry is never edited or deleted (HL-1, R12). Preserving negative results maps the boundaries of market efficiency and keeps the family denominator honest (OS-10). A refutation is a first-class product (PG-11), not a defect.

**Owner:** Chief Research Officer · **Last updated:** 2026-08-19 · **Governed by:** [[FAILURE_LIBRARY_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]]

## Entries

| failure_id | hypothesis_ref | mechanism | experiment_ref | mode | archived | record |
|---|---|---|---|---|---|---|
| **FAIL-PM-0001** | HYP-PM-0001 | M1.1 inventory-imbalance mean reversion (I5) | EXP-PM-0001 (`run_utc` 2026-07-18T01:09:37Z) | **F2 · Prediction failure** | 2026-07-18 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PA-0001** | HYP-PA-0001 | MECH-recon-dislocation · reconstitution closing-auction dislocation (I8→I2) | EXP-PA-0001 (`results.json` sha256 `27dac1ec…`) | **F2 · Prediction failure** | 2026-08-19 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |

## Failure-mode distribution (institutional self-diagnostic — §5.3)

| Mode | Count | Note |
|---|---|---|
| F1 Mechanistic incoherence | 0 | |
| **F2 Prediction failure** | **2** | FAIL-PM-0001, FAIL-PA-0001 |
| F3 Multiplicity collapse | 0 | |
| F4 Cost destruction | 0 | |
| F5 Regime artifact | 0 | |
| F6 Provenance failure (VOID) | 0 | |
| F7 Look-ahead contamination | 0 | |
| F8 Capacity extinction | 0 | |
| F9 Decay (not an error) | 0 | |

> N=2. Still too small to diagnose the institution's efficiency (§5.3). Both entries are F2, and both mechanisms died at short horizons against the same 0.60% round-trip friction — a program-level pattern (horizon/friction mismatch) that no single F-code expresses. Recorded here because the distribution alone will not surface it.

## Notes

- **FAIL-PM-0001** — first entry in the P-M program. HYP-PM-0001 remains **counted in the P-M family {I5,I6,I7,I12}** (X8: a failure never reduces the denominator). Terminal; continuation only via T12 supersession — a *new* registration.
- **FAIL-PA-0001** — first entry in the P-A program. HYP-PA-0001 remains **counted in the P-A family {I2,I3,I8}** (X8). Terminal; continuation only via T12 supersession. Note the family is more consumed than a 1-of-3 member count implies: the taxonomy records I8 as causally upstream of I2 (LIM3 — shared observations, not independent evidence) and I3 as competing with I2 for the same session-boundary observations.
