# Failure Entry — FAIL-PM-0003 (immutable)

> The mandatory T7 receipt for the transition **IN_TESTING → FAILED** of HYP-PM-0003 ([[HYPOTHESIS_LIFECYCLE]] T7, HL-1). Per [[FAILURE_LIBRARY_SCHEMA]] this record is **append-only, immutable, and never deleted**. A falsification is a first-class institutional product (R12).

| Schema field | Value |
|---|---|
| **failure_id** | `FAIL-PM-0003` |
| **hypothesis_ref** | HYP-PM-0003 (registration sha256 `a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5`) |
| **mechanism_ref** | M2.1 · Adverse-selection spread component (I7, M2/D2) |
| **experiment_ref** | EXP-PM-0003 (`run_utc` 2026-09-09T09:44:17Z · script sha256 `b32fde97ca1666d8166738f9250d78b446697f22f0a31a173fa73fd05283c55b`) |
| **failure_reason** | **F2 · Prediction failure** — the pre-registered criterion (net-of-cost signed continuation at k=7 `> 0`) was not met. Primary (k=7) gross signed continuation = `+0.0538%`, CI95 `[-0.0656%, +0.1768%]` — includes zero. Net-of-cost = `-0.5462%`, far below the `+0.60%` friction floor. **Exactly one mode**, defended against F3/F4/F5/F7 below (R1). |
| **invalid_assumptions** | A-PM3.2 (*the 3–15 trading-day horizon separates permanence from later, unrelated information*) is not supported at the tested horizons: no sign-stable continuation is measurable across k∈{3,7,15} (gross signs: k3 −0.0287%, k7 +0.0538%, k15 −0.0044% — not consistent). The directional prediction — positive net flow → subsequent same-direction (continuing) return, ⇒ signed continuation > 0 — is not supported at the primary horizon. A-PM3.1 (signed-lot correctly signs aggressor direction) is not contradicted by this result; a null is consistent with either correct signing and no real permanence effect, or (unverified) mis-signing — this entry does not distinguish the two, per instruction against inventing interpretation. |
| **lessons_learned** | At Dataset A's daily broker-summary fidelity, net signed `lot` carries no capturable adverse-selection-permanence signal at the 3–15 trading-day horizon against the 0.60% round-trip friction floor; the primary (k=7) gross point estimate is small and statistically indistinguishable from zero. **This is a separate, independent experimental result from HYP-PM-0002's own (not-yet-executed) test of the same I7 entry on `stockbit_flow_bars`.** Per the preserved multiplicity caveat (A-PM3.3, `HYP-PM-0003_REGISTERED.md` `multiplicity_family`), observation-level independence between the two datasets remains unresolved — this result should not, by itself, be read as fully independent confirmation-or-refutation evidence separable from whatever HYP-PM-0002 eventually finds; any future joint reading of both results must carry that caveat forward. |
| **related_features** | `net_flow(ticker,date) = SUM(lot)` — non-predictive for k-ahead continuation at the tested horizons; `signed_continuation_k`; dependence-sensitivity diagnostic (N/N-10/N-100, reported per `HYP-PM-0003_POWER.md` §5 — a labeled sensitivity diagnostic, not a correction, and not itself part of the refutation decision). |
| **archived_date** | 2026-09-09 (institutional close-out; not yet sealed by git commit — see CLOSE_OUT_REPORT §5) |

## Attribution defense (R1 · Duhem–Quine)

The rejected prediction is attributed to the **mechanism** (M2.1), not to an auxiliary. Defended:
- **Cost model (F4):** not the cause — the frozen primary estimator (k=7 gross `+0.0538%`, CI including zero) shows no real gross effect for friction to destroy; even taken at face value the point estimate is ~11× below the 0.60% floor, not a "real edge, killed by cost."
- **Multiplicity (F3):** not the cause — the claim did not survive even at gross/unadjusted primary (CI already includes zero), so no family-denominator or multiplicity adjustment was needed to kill it.
- **Regime (F5):** the in-sample-only scope is a **declared limitation** (history-maturity gate, D-046/D-047), disclosed ex ante at registration — it does not manufacture the null.
- **Look-ahead (F7):** `fwd_ret_k = close_{t+k}/close_t - 1` is computed strictly forward (positive `k`-bar shift) from the formation date; no future information enters the signal.
- **Observation-dependence caveat (A-PM3.3):** not an auxiliary explanation for *this* result — `HYP-PM-0002` has not executed, so no shared-observation contamination between the two experiments is possible here. The caveat bears on how this result and any future `HYP-PM-0002` result should be read **jointly**, not on the validity of this experiment standing alone.

## Terminality (HL-3)

FAILED is terminal. There is **no path** back to IN_TESTING/REGISTERED/REFINING/DRAFT for HYP-PM-0003 (X2–X5). The only legitimate continuation is **T12 → SUPERSEDED**: a *new* hypothesis, new G1, counted afresh in the P-M family {I5,I6,I7,I12}, citing this one. HYP-PM-0003 remains counted in the family denominator permanently (X8) — this failure does not reduce it.

## Lineage

[[HYP-PM-0003_REGISTERED]] · [[HYP-PM-0003_DRAFT]] · [[HYP-PM-0003_POWER]] · [[EVIDENCE_PACKAGE]] · [[MANIFEST]] · [[HYPOTHESIS_REGISTRY]] · [[FAILURE_REGISTRY]] · [[HYPOTHESIS_LIFECYCLE]]
