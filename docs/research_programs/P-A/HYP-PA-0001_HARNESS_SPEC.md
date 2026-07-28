# HYP-PA-0001 — Confirmatory Harness Specification (pre-registration, free era)

> **This is a specification, not code.** No script, notebook, or executable exists for this
> hypothesis. Nothing here runs, and nothing here is a frozen MANIFEST — MANIFEST creation is a
> post-registration act (T5, [[HYPOTHESIS_LIFECYCLE]]), mirroring EXP-PM-0001's pattern, and is
> out of scope until `DRAFT → REGISTERED` (T4) fires. This document exists so that, at
> registration time, there is **no daylight** between what `HYP-PA-0001_DRAFT.md`'s
> `validation_criteria` promises and what the eventual harness will implement — the exact gap
> that HYP-PM-0001's post-mortem flagged (§8.3: an informed-flow discriminator was registered
> and never executed). Closes readiness-review **C-3**.

**Date:** 2026-07-18 (criteria CRO-ratified 2026-07-19) · **Status:** free-era planning artifact — criteria now frozen-ready · **Governs:** the future
confirmatory script for EXP-PA-0001 (not yet created; naming and structure TBD at registration,
following `run_exp_pm_0001.py`'s structural precedent for manifest/seal discipline only — the
estimator itself is unrelated and must not be copied).

---

## 1. One-to-one mapping to `validation_criteria`

Every field below corresponds verbatim to a field in `HYP-PA-0001_DRAFT.md` §S3
`validation_criteria`. **Nothing is specified here that is not already promised there; nothing
is promised there that is not specified here.**

| `validation_criteria` field | Harness behavior at execution |
|---|---|
| `estimator: event-study CAR, market-model abnormal returns (vs IHSG)` | For each event, compute abnormal return = raw return − (α̂ + β̂·r_IHSG,t), with α̂/β̂ estimated on a pre-announcement estimation window **fixed by the CRO (2026-07-19) at 230 trading days ending ~20 trading days before announcement** |
| `run_up_window: [announcement .. effective]` | Cumulative abnormal return (CAR) from `announcement_date` to `effective_date`, inclusive — descriptive only, not the tested quantity |
| `reversal_window: [t+1 .. t+k]` | CAR from the trading day after `effective_date` through `effective_date + k` trading days — **this is the tested quantity** |
| `k: 5 td` | Reversal window length in trading days; **CRO-fixed at 5 td (ratified 2026-07-19)**, not re-tunable post-hoc (X1 — moving k after seeing a near-miss is prohibited) |
| `aggregation: cluster-robust (CR1) by review date` | Standard errors computed via a cluster-robust (Liang–Zeger sandwich, CR1 small-sample correction) estimator, clusters = the 13 (or updated) distinct `effective_date` review dates. This is the **only** inference method run — no parallel pooled-iid run is used for the decision (it appears only as the pre-registered secondary sensitivity figure, computed and reported, never substituted as the decision basis) |
| `alpha: 0.05` | Two-sided test, α = 0.05, against H0: mean signed reversal (gross) = 0 |
| `MDE_stat: ~4.97% raw / ~4.22% haircut` | Not computed at run time — this is the *pre-registered* detection floor from `HYP-PA-0001_POWER.md` §4, reported alongside the realized point estimate and cluster-robust CI for comparison. The decision rule (§2 below) does not require recomputing it |
| `net_of_cost: DELETE-only, N=105` | A second, restricted analysis: same estimator, restricted to `event_type = DELETE`, gross point estimate minus the round-trip friction constant imported from `engine/exits/costs.py` (COMMISSION_BUY 0.15% + COMMISSION_SELL 0.25% + SLIPPAGE 0.10%×2 legs ≈ 0.60%) — **imported, not re-derived**, so PA and PM share one cost authority |
| `robustness_leg: SECONDARY_CROSSCHECKED-only, N=98` | Same estimator (Test 1 form) restricted to `verification_status = SECONDARY_CROSSCHECKED`; reported as a consistency check per the robustness-gradient pattern established in EXP-PM-0001 (k∈{5,15,30}: agreement expected, not a scan for a survivor) |
| dedup rule (A-PA6) | Rows are grouped by `(ticker, effective_date, event_type)` before analysis; a ticker entering/leaving multiple indices on the same effective date contributes **one** economic-event observation, not one per index row |
| `confirmatory_harness: standalone script` | No `research/gatekeeper` invocation; no family-adjusted DSR computed at this stage — deferred (CRO-ratified disposition 2026-07-19), matching EXP-PM-0001's documented precedent (`MANIFEST.md`: *"no gatekeeper pipeline invoked — in-sample confirmatory test per the registered history-maturity gate"*). If this deferral changes before registration, this spec must be revised to match, not silently diverge |

## 2. Decision rule (verbatim form for the eventual `falsification` field)

Restated identically to `HYP-PA-0001_DRAFT.md` §S3 `refutation_condition`, in operational form:

1. Run Test 1 (primary, gross, N=210, cluster-robust). If the CR1 CI excludes zero **and** the
   sign matches the predicted direction → mechanism claim survives Test 1.
2. Run Test 2 (secondary, net, DELETE-only, N=105). If gross − 0.60% > 0 → capturable claim
   survives Test 2.
3. Run the robustness leg (N=98, crosschecked-only). Report agreement/disagreement with Test 1;
   **disagreement does not license re-running Test 1 with a filter** (R15/X4 — the crosschecked
   subsample is a consistency check, not a rescue mechanism).
4. **Refuted** (FAILED) if Test 1 fails (CI includes zero, or wrong sign) **or** Test 2 fails
   (net-of-cost ≤ 0) — mirroring EXP-PM-0001's dual gross/net refutation logic exactly (its
   `falsification` field: *"signed reversal ≤ 0 or < MDE ⇒ REFUTED"*), adapted to PA's
   two-population (mechanism vs. capturable) split.
5. Exactly one F-mode is attributed at close-out (R1), following the F1–F9 taxonomy — e.g., a
   Test-1 miss with a real Test-2-eligible point estimate would file **F2** (prediction
   failure); a Test-1 pass with a Test-2 miss would file **F4** (cost destruction), per the
   same logic used in `FAILURE_ENTRY.md` for FAIL-PM-0001.

## 3. Output artifacts (planned, not created)

Mirroring EXP-PM-0001's sealed pattern — `results.json`, `execution.log`, a frozen
`MANIFEST.md` (created at T5, not now), and an `EVIDENCE_PACKAGE.md` at close-out. No file
listed in this section exists yet; this section is a naming reservation, not a deliverable.

## 4. What this document does NOT do

- Does not execute anything. No code was written to produce this document.
- Does not compute a reversal effect, a t-statistic, or a p-value on real data.
- Does not touch return data for any event — only the field mapping and decision logic are
  specified, using nuisance parameters (σ, N, K) already computed in `HYP-PA-0001_POWER.md`
  from data that does not condition on the outcome.
- Does not register HYP-PA-0001 or create a MANIFEST.

## 5. Lineage

[[HYP-PA-0001_DRAFT]] §S3 `validation_criteria` (source of truth — this document must never
diverge from it) · [[HYP-PA-0001_POWER]] §4 (MDE_stat derivation) · EXP-PM-0001
`MANIFEST.md`/`EVIDENCE_PACKAGE.md` (structural precedent) · [[HYPOTHESIS_LIFECYCLE]] T5
(MANIFEST creation, deferred).
