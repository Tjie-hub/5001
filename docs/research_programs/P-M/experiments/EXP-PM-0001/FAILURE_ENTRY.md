# Failure Entry — FAIL-PM-0001 (immutable)

> The mandatory T7 receipt for the transition **IN_TESTING → FAILED** of HYP-PM-0001 ([[HYPOTHESIS_LIFECYCLE]] T7, HL-1). Per [[FAILURE_LIBRARY_SCHEMA]] this record is **append-only, immutable, and never deleted**. A falsification is a first-class institutional product (R12).

| Schema field | Value |
|---|---|
| **failure_id** | `FAIL-PM-0001` (uuid `f2a1-pm0001-540c2d52-20260718T010937Z`) |
| **hypothesis_ref** | HYP-PM-0001 (registration sha256 `540c2d52dd8751dbda2a6b39ea7935860e12078c666a81e2156ff199ee885199`) |
| **mechanism_ref** | M1.1 · Inventory-imbalance mean reversion (I5, M1/D2) |
| **experiment_ref** | EXP-PM-0001 (`run_utc` 2026-07-18T01:09:37Z · commit `b970224…` · script `8cba58b6…`) |
| **failure_reason** | **F2 · Prediction failure** — the pre-registered criterion (net-of-cost signed reversal > 0) was not met; the frozen primary estimator (signed_reversal, k=15) did not even show the predicted positive gross sign (−0.0008%/trade, t=−0.35, CI95 [−0.0052, +0.0036]%), and the declared robustness gradient {k5:+, k15:−, k30:−} was sign-inconsistent. Net-of-cost primary = −0.6008%/trade. **Exactly one mode**, defended against F4 in [[EVIDENCE_PACKAGE]] §5. |
| **invalid_assumptions** | A-PM2 (*the 1-min/k horizon spans inventory build-and-offload*) is not supported at the tested horizons: no sign-stable reversal is measurable at k∈{5,15,30}. The directional prediction — positive OFI → subsequent reversing (negative) return, ⇒ signed reversal > 0 — is contradicted at the primary horizon. A-PM5 (*proxy flow representative of total imbalance*) and LIM2 (proxy fidelity, no LOB) remain the unresolved confound bounding the I5-vs-I7 read (causal argument, not identification). |
| **lessons_learned** | At IDX proxy fidelity, 1-min OFI carries no capturable inventory-reversal signal at the 5–30 min horizon; the displacement β is positive but tiny (corr 0.016) and does not reverse net of the 0.60% round-trip. Future P-M work should either (a) test M2.1 adverse-selection **permanence** (I7) as the competing read, or (b) await higher-fidelity (LOB) flow before re-opening inventory mean-reversion under a new registration (T12). Do **not** re-run this object with an adjusted k or an added liquidity filter — that is X2/X3/X4 (R15). |
| **related_features** | OFI_t (signed net imbalance, normalized) — non-predictive for k-ahead reversal at proxy fidelity; rev_{t+1..t+k}; decile-sorted OFI forward-return spread (+0.098% gross, below MDE). |
| **archived_date** | 2026-07-18 (institutional close-out; sealed by git commit) |

## Attribution defense (R1 · Duhem–Quine)

The rejected prediction is attributed to the **mechanism** (M1.1), not to an auxiliary. Defended:
- **Cost model (F4):** not the cause — the frozen primary estimator shows no real gross effect to destroy (see [[EVIDENCE_PACKAGE]] §5).
- **Data/proxy (F6/void):** the run is fully reproducible from the frozen spec (script `8cba58b6…`, deterministic, no seeds); it is a refutation, not a void.
- **Regime (F5):** the in-sample/one-regime scope is a *declared* limitation (history-maturity gate), disclosed ex ante — it does not manufacture the null.
- **Look-ahead (F7):** forward-only estimator; bid-ask-bounce guard (1-bar skip) run and likewise null (t=−0.47).

## Terminality (HL-3)

FAILED is terminal. There is **no path** back to IN_TESTING/REGISTERED/REFINING/DRAFT for HYP-PM-0001 (X2–X5). The only legitimate continuation is **T12 → SUPERSEDED**: a *new* hypothesis, new G1, counted afresh in the P-M family {I5,I6,I7,I12}, citing this one.

## Lineage

[[HYP-PM-0001_REGISTERED]] · [[EVIDENCE_PACKAGE]] · [[MANIFEST]] · [[HYPOTHESIS_REGISTRY]] · [[FAILURE_REGISTRY]] · [[FAILURE_LIBRARY_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]]
