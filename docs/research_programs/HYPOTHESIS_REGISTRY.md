# Hypothesis Registry

> The operating index of hypotheses across active programs. A hypothesis is **counted in its program's multiplicity family from G1/REGISTERED and never leaves** (PG-3, OS-10). This registry is append-only in spirit: status advances by adding a superseding record, never by silent edit ([[HYPOTHESIS_LIFECYCLE]] HL-1/HL-2).

**Owner:** Research Director / CRO · **Last updated:** 2026-08-19 · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] · [[RESEARCH_PROGRAM]]

## Registered & in-flight

| ID | Program · Family | Mechanism | Status | Frozen record | Family slot |
|---|---|---|---|---|---|
| **HYP-PM-0001** | P-M · {I5,I6,I7,I12} | M1.1 inventory-imbalance mean reversion (I5), tested vs M2.1 (I7) | **FAILED** (F2) 2026-07-18 · was REGISTERED 2026-07-17T07:15:03Z | [[HYP-PM-0001_REGISTERED]] · sha256 `540c2d52…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-M member) |
| **HYP-PA-0001** | P-A · {I2,I3,I8} | reconstitution closing-auction dislocation (I8→I2) | **FAILED** (F2) 2026-08-19 · was REGISTERED 2026-07-19T00:19:47Z | [[HYP-PA-0001_REGISTERED]] · sha256 `3692e69a…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-A member) |

## Status legend

`DRAFT` free-era candidate (unlimited refinement; nothing risked) · `REGISTERED` frozen, risked, in the family · then `IN_TESTING → VALIDATED | FAILED → …` per [[HYPOTHESIS_LIFECYCLE]] §3.

## Family-slot ledger

| Program | Family (append-only) | Members registered | Notes |
|---|---|---|---|
| **P-M · Microstructure Flow** | {I5, I6, I7, I12} | **1** — HYP-PM-0001 | family opened at first registration (D-028, PG-3) |
| **P-A · Auction Dislocation** | {I2, I3, I8} | **1** — HYP-PA-0001 | family opened at first registration (D-028, PG-3); registered 2026-07-19 on realized WP-D N=210/K=13 window |

## Notes

- **HYP-PM-0001** — registered under a **friction-anchored MDE** (round-trip ≈ 0.60% from the cost authority) and a **history-maturity gate** (validation in-sample until the ~1yr flow history lengthens). Terminal reachable tier **C2** (EV-9, N=1). **EXP-PM-0001 executed 2026-07-18T01:09:37Z (in-sample) → FAILED, mode F2 · Prediction failure**: primary k=15 gross signed reversal −0.0008%/trade (t=−0.35), net −0.6008%; robustness signs inconsistent ⇒ M1.1 refuted per the frozen falsification rule. Receipts: T5 custody + T7 [[FAILURE_ENTRY]]; product [[EVIDENCE_PACKAGE]] (C2 refutation, R12). **Terminal** — continuation only via T12 supersession (a new registration); stays counted in the P-M family (X8). See [[FAILURE_REGISTRY]].
- **HYP-PA-0001** — **EXP-PA-0001 executed 2026-08-19 → FAILED, mode F2 · Prediction failure.** Test 1 (primary, gross, both directions, n=180, G=13): mean signed reversal +0.7261%, SE(CR1) 0.5026%, t=1.445, CI95 [−0.3691%, +1.8212%] — CI includes zero. Test 2 (capturable, DELETE-only, n=98): gross −0.2488% → net of 0.60% friction −0.8488%. Both failed ⇒ refuted per the frozen rule. Exact wild cluster bootstrap (all 2^13 sign vectors) agrees with the asymptotic test on every sample. **Substantive finding: the mechanism is directional, not symmetric** — ADD-side +1.8911% (CI95 [+0.6677%, +3.1144%], WCB p=0.0132, robust to all 13 leave-one-cluster-out refits, positive in 11/13 review dates) versus DELETE-side −0.2488%. Pre-registered gross-only and **not capturable** (shorting-constrained on IDX, C-4); it does not rescue the hypothesis. Realised power was ~4× better than the pre-registered MDE assumed, so the pooled null is informative, not underpowered. Terminal (HL-3); continuation only via T12. Receipts: [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]]. See [[FAILURE_REGISTRY]].
