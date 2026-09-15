# Failure Entry — FAIL-PM-0009 (immutable)

> The mandatory T7 receipt for the transition **REGISTERED (executed) → FAILED** of HYP-PM-0009
> ([[HYPOTHESIS_LIFECYCLE]] T7, HL-1). Per [[FAILURE_LIBRARY_SCHEMA]] this record is **append-only,
> immutable, and never deleted**. A falsification is a first-class institutional product (R12).

| Schema field | Value |
|---|---|
| **failure_id** | `FAIL-PM-0009` |
| **hypothesis_ref** | HYP-PM-0009 (registration sha256 `d19dfd0f6b059a4b4c564361087bf9aa59e327c8105c5229e166afa64f76b75a`, registered 2026-09-14 per DECISION_LOG **D-050**) |
| **mechanism_ref** | M2 · information / adverse selection — taxonomy entry **I7 · intraday execution timing** |
| **experiment_ref** | `EXP-PM-0009/R2` (`run_utc` 2026-09-15T01:41:30Z · script sha256 `d2e7a9a21f7939a73e2ecf36c3e667bb29b5d69d716faeff1f5346abd5905e3e` · receipt `experiments/EXP-PM-0009/MANIFEST.md`) |
| **failure_reason** | **F2 · Prediction failure** — the registered kill rule (`theta_primary > 0` with two-sided p < 0.05) was not met. Primary (k=1, entry close(t+1), outcome close(t+2)/close(t+1) − 1): **θ_primary = +0.0337%** per formation-day, Newey-West HAC t (lag 5) = **0.1102**, two-sided p = **0.912223** (Holm = identity, single cell), on **64 daily observations** (6 dates skipped and counted). θ_net sensitivity = **−0.5663%** (sensitivity only, never a verdict). **Exactly one mode**, F2; no auxiliary attribution investigated (prohibited by the closeout instruction — see Attribution below). |
| **invalid_assumptions** | The directional prediction — conditional on a net-buying day, back-loaded net buying is followed by higher subsequent return than front-loaded net buying of the same sign — is not supported at the registered specification on the v004 cohort (76 sessions, 2026-04-28..2026-09-11). No other assumption is adjudicated by this entry. |
| **lessons_learned** | Recorded facts only, no post-hoc investigation: the registered effect at the primary horizon is statistically indistinguishable from zero (p = 0.9122), and even the point estimate sits far below the 0.60% round-trip friction floor as the registered θ_net sensitivity (−0.5663%). **I7 carries NO power claim (D-050): this non-rejection is NOT evidence of absence and must never be reported or used as one.** The **R7 PIT provenance limitation** is retained in the result (custody verifiable; original vendor payload not independently re-verifiable — 200/200 source spot-check matches). Estimation-layer accounting (MECE): population 24,187 net-buying cells → X6 475, X5 17,684 (CA 256, RAJA 19, missing close 3,036, price floor 4,528, liquidity floor 9,845), surviving 6,028. Robustness horizons k=2 (θ −0.0362%, p 0.928) and k=3 (θ +0.2138%, p 0.615) — non-confirmatory, no sign consistency. |
| **related_features** | `nbuy(seg) = SUM(buy_lot) − SUM(sell_lot)` per segment (OPEN 09:00–09:59; LATE 14:50–15:49); `LATE_TILTED` if nbuy(LATE)/daily_net ≥ 0.50; daily-series-first aggregation (BFI-001 §G/§I); NW HAC lag 5, two-sided p (erfc). Semantic gate D-049 compliant: no all-broker net constructed anywhere (buy/sell sides separate aggressor quantities) — `identity_affected: false`. |
| **archived_date** | 2026-09-15 (governance closeout commit) |

## Attribution defense (R1 · Duhem–Quine) — limited to recorded facts

Per the closeout instruction **no explanation-seeking, subgroup, re-windowing, or post-hoc power
analysis was performed**; the hypothesis is terminal regardless. Facts already sealed in the receipt:

- **R1 (2026-09-15T01:39:02Z) was INVALID — implementation defect, estimand not evaluated** (exit-index
  bug made `fwd_return ≡ 0`). Artifacts preserved verbatim (`execution_r1_INVALID_defect.log`,
  `results_r1_INVALID_defect.json`). The correction was **implementation-only**; the frozen specification
  block hash `d19dfd0f…` was verified unchanged after execution and closeout. R2 is the single valid
  registered execution; R2's k=1 arm reproduces R1's accidentally-shifted arm exactly (deterministic
  cross-check).
- **Cost (F4):** not adjudicated as cause — no gross effect existed for friction to destroy (θ indistinguishable
  from zero); the registered θ_net sensitivity (−0.5663%) is reported, not interpreted further.
- **Power:** none claimed ex ante (D-050); none computed post hoc. The null is **not** an evidence-of-absence
  finding.

## Terminality (HL-3)

FAILED is terminal. There is **no path** back for HYP-PM-0009 (X2–X5). The only legitimate continuation is
**T12 → SUPERSEDED**: a *new* hypothesis, new G1, counted afresh in the P-M family {I5, I6, I7, I12},
citing this one. HYP-PM-0009 remains **counted in the family denominator permanently** (X8). Per the
registered `no_rescue` rule and the closeout STOP condition: no rerun, no alternative windows, no subgroup
analysis, no post-hoc power, no new threshold, no cohort modification, no rescue hypothesis.

## Lineage

[[HYP-PM-0009_REGISTERED]] (frozen, sha256 `d19dfd0f…`) · `experiments/EXP-PM-0009/MANIFEST.md` ·
`experiments/EXP-PM-0009/results.json` · `experiments/EXP-PM-0009/CLOSE_OUT_REPORT.md` ·
[[HYPOTHESIS_REGISTRY]] · [[FAILURE_REGISTRY]] · [[DECISION_LOG]] D-050 · D-051 · [[HYPOTHESIS_LIFECYCLE]]
