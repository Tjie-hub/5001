# Failure Registry

> The institutional repository of falsified hypotheses and failed experiments ([[FAILURE_LIBRARY_SCHEMA]]). **Append-only and immutable** — a failure entry is never edited or deleted (HL-1, R12). Preserving negative results maps the boundaries of market efficiency and keeps the family denominator honest (OS-10). A refutation is a first-class product (PG-11), not a defect.

**Owner:** Chief Research Officer · **Last updated:** 2026-09-29 · **Governed by:** [[FAILURE_LIBRARY_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]]

## Entries

| failure_id | hypothesis_ref | mechanism | experiment_ref | mode | archived | record |
|---|---|---|---|---|---|---|
| **FAIL-PM-0001** | HYP-PM-0001 | M1.1 inventory-imbalance mean reversion (I5) | EXP-PM-0001 (`run_utc` 2026-07-18T01:09:37Z) | **F2 · Prediction failure** | 2026-07-18 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PM-0003** | HYP-PM-0003 | M2.1 adverse-selection permanence (I7), `broker_flow`/Dataset A instrument | EXP-PM-0003 (`run_utc` 2026-09-09T09:44:17Z) | **F2 · Prediction failure** | 2026-09-09 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PA-0001** | HYP-PA-0001 | MECH-recon-dislocation · reconstitution closing-auction dislocation (I8→I2) | EXP-PA-0001 (`results.json` sha256 `27dac1ec…`) | **F2 · Prediction failure** | 2026-08-19 | [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] |
| **FAIL-PM-0004-G1** | HYP-PM-0004 | C2 conduit disagreement (C-family) | G1 Run 1 (`G1_REAL_OUTPUT_RUN1_2026-09-11.json` sha256 `74883c04…`) | **INVALID · governance** — registered species-mix control unimplementable (freq-dependent); executed unconditional contrast is not the designed conditional estimand; NOT CONFIRMED (Holm p = 1.0) | 2026-09-11 | DECISION_LOG D-048 · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` |
| **FAIL-PM-0005-G1** | HYP-PM-0005 | C3 breadth surprise (C-family) | G1 Run 1 (same output) | **NOT CONFIRMED (VALID, bounded)** — primary k=5 θ = +5.8 bp, NW t = +0.323, Holm p = 1.0; determinate null at 329 daily observations; signs +/+/−; net of 0.60% floor ≈ −54 bp | 2026-09-11 | DECISION_LOG D-048 · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` |
| **FAIL-PM-0009** | HYP-PM-0009 | M2 · information / adverse selection — **I7 intraday execution timing** (v004 PIT cohort, `stockbit_flow_bars`) | EXP-PM-0009/R2 (`run_utc` 2026-09-15T01:41:30Z · script sha256 `d2e7a9a2…`) | **F2 · Prediction failure** — kill rule not met: primary k=1 θ_primary = +0.0337%/day, NW HAC t (lag 5) = 0.1102, two-sided p = 0.912223, 64 daily observations; θ_net sensitivity −0.5663% (sensitivity only). **NO POWER CLAIM (D-050): non-rejection is NOT evidence of absence.** R7 PIT provenance limitation retained | 2026-09-15 | [[FAILURE_ENTRY]] (in `experiments/EXP-PM-0009/`) · `MANIFEST.md` · DECISION_LOG D-050/D-051 |
| **FAIL-PM-0007** | HYP-PM-0007 | Broker-flow imbalance baseline (BFI-001 / research.db `BROKER-001`) | `10_execute_bfi001` (run 2026-09-03 · `90_results.json`) | **INVALID · data** — primary BFI_broad = NV/GV identity-attenuated (\|NV/GV\| p90 0.00201, p99 0.0146, max 0.060, P(≥0.2)=0); structure secondaries VALID → NOT CONFIRMED (CONC t −2.65 Holm 0.097; BREADTH t +2.41, LOKAL t +2.43, Holm 0.164) | 2026-09-29 (alias ratified; outcome owner-ratified 2026-09-11) | DECISION_LOG D-063 · EXPERIMENT_LEDGER `BROKER-001` |
| **FAIL-PM-0015** | HYP-PM-0015 | Price-Learning {L1} · learned cross-sectional rank of 14 OHLCV/volume feature ranks (ridge / shallow HistGBR) vs baseline M0 (low Parkinson-60 + 12-1 momentum) | G1 single run `run_id 167749f2…` (`RESULT_20261006T090908Z.json`, commit `f4a84df`, driver sha256 `47752c25…`) | **F2 · Prediction failure** | 2026-10-06 | [[ml_rank/VERDICT]] · [[ml_rank/PREDECLARATION]] |

## Failure-mode distribution (institutional self-diagnostic — §5.3)

| Mode | Count | Note |
|---|---|---|
| F1 Mechanistic incoherence | 0 | |
| **F2 Prediction failure** | **5** | FAIL-PM-0001, FAIL-PM-0003, FAIL-PA-0001, FAIL-PM-0009, FAIL-PM-0015 |
| F3 Multiplicity collapse | 0 | |
| F4 Cost destruction | 0 | |
| F5 Regime artifact | 0 | |
| F6 Provenance failure (VOID) | 0 | |
| F7 Look-ahead contamination | 0 | |
| F8 Capacity extinction | 0 | |
| F9 Decay (not an error) | 0 | |
| INVALID · governance (outside F1–F9) | **1** | FAIL-PM-0004-G1 — governance-invalidated arm, recorded for denominator honesty; not an F-mode |
| INVALID · data (outside F1–F9) | **1** | FAIL-PM-0007 — primary unmeasurable on the instrument (identity attenuation); filed on alias ratification (D-063) for denominator honesty; not an F-mode |
| NOT CONFIRMED (registered no-rescue vocabulary) | **1** | FAIL-PM-0005-G1 — valid bounded null at the registered inference |

> N=7 (4 F2 + 1 governance-invalidated + 1 data-invalidated + 1 valid bounded null; FAIL-PM-0007 added 2026-09-29 per D-063). All F2 entries died at short-to-swing horizons against the same 0.60% round-trip friction — a program-level pattern (horizon/friction mismatch) that no single F-code expresses. Recorded here because the distribution alone will not surface it. The two 2026-09-11 G1-family rows (FAIL-PM-0004-G1, FAIL-PM-0005-G1) receipt the first C-family empirical outcome per DECISION_LOG D-048: C2 governance-invalidated, C3 a valid bounded null — neither is a rescue of the other, and the withdrawn C1a/C1b produced no numbers.

## Notes

- **FAIL-PM-0001** — first entry in the P-M program. HYP-PM-0001 remains **counted in the P-M family {I5,I6,I7,I12}** (X8: a failure never reduces the denominator). Terminal; continuation only via T12 supersession — a *new* registration.
- **FAIL-PM-0003** — second REGISTERED member of the P-M family (Option B, OS-10, CRO-adopted 2026-09-09 — independent counting; `HYP-PM-0002` remains unregistered and consumes no slot). Tested M2.1 (I7) via `broker_flow`/Dataset A (FROZEN, D-043, `provenance_hash 329b22e49f0e…`), the **same taxonomy entry** `HYP-PM-0002`'s own (unregistered, unexecuted) draft targets via a different instrument (`stockbit_flow_bars`). **Preserved caveat:** observation-level independence between the two datasets is unresolved (A-PM3.3) — this result is not, by itself, separable evidence from `HYP-PM-0002`'s eventual result; any future joint reading must carry the caveat forward. HYP-PM-0003 remains **counted in the P-M family** (X8). Terminal; continuation only via T12 supersession.
- **FAIL-PA-0001** — first entry in the P-A program. HYP-PA-0001 remains **counted in the P-A family {I2,I3,I8}** (X8). Terminal; continuation only via T12 supersession. Note the family is more consumed than a 1-of-3 member count implies: the taxonomy records I8 as causally upstream of I2 (LIM3 — shared observations, not independent evidence) and I3 as competing with I2 for the same session-boundary observations.
- **FAIL-PM-0009** — third REGISTERED member of the P-M family {I5,I6,I7,I12} (D-028, slot permanent PG-3/OS-10), registered 2026-09-14 per D-050 and executed **once** 2026-09-15 (`EXP-PM-0009/R2`, in-sample, v004 PIT cohort fingerprint-bound `e1375264…fba`). Killed by the frozen kill rule: θ_primary = +0.0337% is nominally positive but statistically indistinguishable from zero (two-sided p = 0.912223, NW HAC lag 5, 64 daily m(d) observations). **The registered interpretation constraint is carried forward verbatim: I7 has no ex-ante power claim (D-050), so this non-rejection is NOT evidence of absence and must never be reported or used as one.** R7 PIT provenance limitation (verification, not availability) retained in the result. An initial invocation R1 the same day was INVALID — an implementation-only exit-index defect (estimand never evaluated); artifacts preserved verbatim; the frozen specification block (sha `d19dfd0f…`) verified unchanged before, during, and after. HYP-PM-0009 remains counted in the family (X8). Terminal; continuation only via T12 supersession. See `experiments/EXP-PM-0009/{MANIFEST,CLOSE_OUT_REPORT}.md`.
- **FAIL-PM-0015** — first and only REGISTERED member of P-M · Price-Learning {L1} (D-067; slot permanent, X8). Executed **once** 2026-10-06 (test 2021-10..2026-09, 60 months, read once). Test net top-quintile excess vs the EW base book: M0 +0.45%/mo NW t 1.20, M1 ridge +0.20% t 0.42, M2 HistGBR +0.81% t 1.71, all below the frozen bar 3.06; neither learned model beats M0 (paired t −0.59 / 0.78); PBO 0.51 (configuration selection no better than chance). Rank IC is positive (t 4.4–4.8) but does not convert into top-quintile net excess; validation-period excess was negative or flat. Classified F2 (the registered prediction failed at its own gate), not F3: the learned models miss even an undeflated t 2 and do not beat the uncounted baseline. Per the predeclared null handling the family question closes at G1 (D-068); any future price-learning work is a NEW registration by formal amendment, inheriting this family's multiplicity.
