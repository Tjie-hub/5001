# EXP-PM-0001 — Evidence Package (terminal)

> The terminal evidence product for the confirmatory experiment of **HYP-PM-0001**. This package binds the frozen registration, the frozen manifest, the immutable results, and the lifecycle transition receipts into one auditable record. **No experimental result is restated with any modification** — every number below is quoted verbatim from `results.json` / `execution.log`. Authored at close-out; the underlying results are immutable.

**Owner:** Research Director / CRO · **Authored:** 2026-07-18 · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] (T5/T7, HL-1) · [[EVIDENCE_MODEL]] (EV-9, C2) · [[FAILURE_LIBRARY_SCHEMA]] (O8)

---

## 1. Identity

| Field | Value | Source |
|---|---|---|
| Experiment ID | **EXP-PM-0001** | MANIFEST |
| Hypothesis ID | **HYP-PM-0001** | REGISTERED |
| Registration timestamp | 2026-07-17T07:15:03Z | REGISTERED §receipt |
| Registration hash (seal) | `540c2d52dd8751dbda2a6b39ea7935860e12078c666a81e2156ff199ee885199` | REGISTERED = MANIFEST = results.json |
| Code commit | `b970224738b218ccdd08cc99cc7b8fd375d39a8c` | MANIFEST; == current HEAD |
| Pipeline / script | `run_exp_pm_0001.py` · sha256 `8cba58b6932837abf8d28c110132fa2df98cba8b38bd6842f267224a8caa2e96` | MANIFEST; == on-disk |
| Execution timestamp (`run_utc`) | **2026-07-18T01:09:37Z** | results.json = execution.log line 1 |
| **Experiment status** | **COMPLETED** | this package |
| **Hypothesis terminal status** | **FAILED** (F2 · Prediction failure) | [[FAILURE_ENTRY]] · [[HYPOTHESIS_REGISTRY]] |
| Evidence tier reached | **C2** (EV-9, N=1, in-sample per maturity gate) — competent refutation | REGISTERED §expected_evidence_product |

## 2. Lifecycle transition receipts (HL-1 — no receipt, no transition)

The experiment moves the hypothesis through the frozen-era state machine ([[HYPOTHESIS_LIFECYCLE]] §4). Two transitions occurred; each carries its mandatory receipt.

### T5 — REGISTERED → IN_TESTING (custody receipt)

| Field | Value |
|---|---|
| Guard | Experiment approved (frozen MANIFEST, 12/12 pre-execution consistency PASS); custody enforced; partition opened once |
| **When** | 2026-07-18T01:09:37Z (`run_utc`) |
| **By whom** | Research Director / CRO (this close-out task) |
| **Once** | Single confirmatory run; no re-run, no parameter change (any re-run with a changed parameter is a *new* experiment — MANIFEST §Immutability) |
| Partition | **IN-SAMPLE** — no OOS partition released. Per the registered HISTORY-MATURITY GATE (DFS §5.3), the ~1yr / one-regime flow history makes the confirmatory test in-sample until the history lengthens; regime-stratified & walk-forward validation remain DEFERRED (REGISTERED §declared_limitations) |

### T7 — IN_TESTING → FAILED (failure receipt)

| Field | Value |
|---|---|
| Guard | One F-mode, attribution defended against auxiliaries (R1) |
| Receipt | **[[FAILURE_ENTRY]]** (O8) — mandatory, immutable, never deleted ([[FAILURE_LIBRARY_SCHEMA]]) |
| F-mode | **F2 · Prediction failure** — the pre-registered criterion was not met |

## 3. Result (verbatim from `results.json` / `execution.log` — not modified)

**Leg 1 — displacement** (expect β>0): β(r_t ~ OFI) = `1.737092e-04`, corr = `0.0158`.

**Leg 2 — signed reversal** (predicted **> 0**), daily-clustered t-test, N = 233 days:

| k (min) | gross reversal %/trade | t | CI95 % | net-of-cost %/trade | sign |
|---|---|---|---|---|---|
| 5 | +0.0007 | 0.92 | [−0.0008, +0.0023] | −0.5993 | + |
| **15 (PRIMARY)** | **−0.0008** | **−0.35** | **[−0.0052, +0.0036]** | **−0.6008** | **−** |
| 30 | −0.0072 | −1.67 | [−0.0157, +0.0012] | −0.6072 | − |

**Robustness gradient** signs across k∈{5,15,30} = {+, −, −} → **consistent = false** (the frozen record declared the gradient a consistency check requiring agreement).

**Decile sort** (k=15): low-minus-high OFI forward-return spread = **+0.0983%** gross (vs 0.60% round-trip friction).

## 4. Decision against the preregistered rule (verbatim)

> **Frozen falsification rule** (REGISTERED §falsification): *"Displacement conditional on OFI does NOT revert net of cost (signed reversal ≤ 0 or < MDE) ⇒ M1.1 REFUTED."*
> **Frozen alternative** (REGISTERED): *"H1: mean signed reversal, NET OF COST, > 0."*
> **Frozen MDE** (friction-anchored): gross reversal that must be cleared = **0.60%** round-trip.

**Applying the rule to the frozen primary estimator (k=15):**
- Gross signed reversal = **−0.0008%/trade** ⇒ `signed reversal ≤ 0` — **the refutation condition is met on sign alone**, before cost.
- Net-of-cost signed reversal = **−0.6008%/trade** ⇒ `≤ 0` and `< MDE` — refutation condition met a second, independent way.
- Robustness gradient sign-inconsistent; decile spread (+0.098%) is itself an order of magnitude below the 0.60% MDE.

**⇒ M1.1 (inventory-imbalance mean reversion, I5) is REFUTED for IDX proxy flow.** The hypothesis transitions to **FAILED**.

## 5. Failure-mode determination (exactly one, defended — R1)

**Filed: F2 · Prediction failure** — "the pre-registered out-of-sample criterion was not met." The pre-registered primary estimator (signed_reversal at k=15) did not show the predicted positive sign (point estimate −0.0008%, t=−0.35, CI95 straddling zero), and the declared consistency gradient disagreed in sign.

**Defense against the auxiliary explanation (F4 · Cost destruction):** F4 requires a *real* gross effect destroyed by friction. The frozen primary estimator shows **no real gross effect** — the signed reversal at k=15 is negative and statistically indistinguishable from zero, and the robustness signs are inconsistent. The only weakly-positive gross quantity, the decile spread (+0.098%), is (a) not the pre-registered primary estimator and (b) itself ~6× below the 0.60% friction, so it cannot rescue the claim to "real but uncapturable." The failure is therefore that the prediction was wrong (F2), **not** that a real edge was eaten by cost (F4).

**Not F3** (multiplicity collapse): the claim did not survive even at gross/unadjusted primary, so no family denominator was needed to kill it. **Not F5** (regime artifact): the in-sample/one-regime scope is a *declared limitation*, not the cause of the null. **Not F7** (look-ahead): the estimator uses only forward returns after the signing bar; the bid-ask-bounce guard (1-bar skip) was run and is likewise null (t=−0.47). Exactly one mode: **F2**.

## 6. Internal-consistency audit

| Anchor | Cross-checked across | Result |
|---|---|---|
| Registration hash `540c2d52…` | REGISTERED §receipt · MANIFEST §Identity · results.json `registration_sha256` | **MATCH (3/3)** |
| Registration seal | SHA-256 of frozen bytes recomputed | **MATCH** — seal intact, frozen object untampered |
| Execution timestamp `2026-07-18T01:09:37Z` | results.json `run_utc` · execution.log line 1 | **MATCH** |
| Code commit `b970224…` | MANIFEST · `git rev-parse HEAD` | **MATCH** |
| Script sha256 `8cba58b6…` | MANIFEST · on-disk `sha256sum` | **MATCH** |
| Dataset (12,956,970 rows · 867 tickers · 2025-07-07→2026-07-17) | MANIFEST · results.json · execution.log | **MATCH** |
| Analysis rows 12,642,224 | results.json `n_analysis_rows` · execution.log | **MATCH** |
| k_primary = 15 · friction = 0.60% (0.006) | REGISTERED · MANIFEST · results.json · execution.log | **MATCH** |
| Primary result −0.0008% (t=−0.35) / net −0.6008% | results.json k15 · execution.log lines 15–16 | **MATCH** |

**Audit verdict: PASS — every document references the same execution timestamp (`2026-07-18T01:09:37Z`), commit (`b970224…`), and result (k=15 gross −0.0008%, net −0.6008%).**

## 7. Institutional value (R12 — negative evidence is evidence)

A competent refutation is a first-class product (PG-11, R12). EXP-PM-0001 maps a boundary on the D2 identification problem for IDX proxy flow: at 1-min OFI / k=15-min horizon, inventory mean-reversion (M1.1/I5) does not produce a capturable — or even a sign-stable gross — reversal, consistent with adverse-selection permanence (M2.1/I7) dominating, or with the proxy's fidelity ceiling (LIM2). The only legitimate continuation is a **new** registration under T12 (supersession); there is no path back for this object (HL-3, §5).

## 8. Lineage

[[HYP-PM-0001_REGISTERED]] · [[HYP-PM-0001_POWER]] · [[MANIFEST]] · [[FAILURE_ENTRY]] · [[HYPOTHESIS_REGISTRY]] · [[FAILURE_REGISTRY]] · [[HYPOTHESIS_LIFECYCLE]] · [[EVIDENCE_MODEL]]
