# C7 INTENSITY-STATE — REGISTRATION v1 (2026-09-11)

**NEW DATED REGISTRATION — NOT PREVIOUSLY REGISTERED.**
**Status (updated 2026-09-11, later): REGISTERED — owner-approved.** The six decisions in §3 were supplied by the owner and are incorporated verbatim; §3 now records the resolution of each former NOT SET item. C7 has never been preregistered: it exists in the record only as descriptive evidence (family map D+H; custody-handoff primary survivor) and as harness machinery. This document registers it for execution after the owner's approval of this registration.

**Spec sources:** `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` rows D, H, K, I/L (sha `e07dc07f…`); descriptive evidence `ZCodeProject/pm_data_audit/family_passD_states.json` + generator `17_family_passD.py`; custody handoff `PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md` ("C7 flow intensity/state (freq-free, cap-robust; next-day high-intensity persistence 48%/46% vs 11% base)"); program execution conventions (BFI-001 frozen prereg §C/§D/§G/§I, sha `91c0eb9a…`); Dataset B freeze manifest v1.

---

## 1. Mechanism (as documented)

High broker-flow intensity states — gross traded value far above the name's own baseline — persist into the next session (measured P(next-day high | high) = 45.7–48.1% vs 11.3% base) and coincide with execution/liquidity structure (intensity ≥ 2× ADV on 18.11% of name-days; flat baselines across liquidity terciles). Family map classifies D/H as **execution-type**: the registered question is whether the intensity state carries **executable information** (next-session flow, liquidity, or price behavior), distinct from the closed disagreement/surprise mechanisms.

## 2. ESTABLISHED parameters (cited to existing material)

| Parameter | Registered value | Source |
|---|---|---|
| Intensity | `intensity(i,t) = gross(i,t) / ADV20(i,t)` where gross = Σ\|value\| over the ticker-session's full-population frozen flow rows; ADV20 = **median traded value (close × volume) over the prior 20 sessions, shift(1)** — BFI-001/program convention | map H ("gross/ADV20: p50 0.82, p90 3.12"); descriptive generator `17_family_passD.py` (used a trailing 21-value median — recorded; execution pins the program 20-value convention; prevalence may shift marginally from the descriptive 18.11%) |
| High-intensity state | `intensity ≥ 2.0` | map H ("intensity ≥2× on 18.1% of name-days"); `family_passD_states.json: high_intensity_prevalence = 0.18109` |
| Inputs | frozen store `broker_flow_b` (values), production `ohlcv` (close, volume), session calendar, PIT roster | Dataset B freeze manifest v1; store sha `21661f03…` |
| Freq | **never read** — C7 is freq-free by construction | SEMANTIC_REGISTER_v1; triage |
| Exclusions (inherited conventions) | price < 100; \|ret1\| ≥ 0.15; suspension at t; corporate action in (t, t+k]; gross ≤ 0; quarantine (RAJA); missing ADV20 history | BFI-001 §D conventions; G1 registration §6 |
| PIT | roster membership at t from sha-verified artifacts; no future roster; flow `trade_date == t` only | foundation.py; G1 parity test |
| Availability | session-t flow and intensity are economically known at close t; no T+1-materialized file is consumed for formation | BFI-001 §C convention |
| Missing/zero-volume treatment | zero-volume sessions produce gross = 0 → state = not-high; zero/negative ADV20 ⇒ observation excluded (counted); no imputation, no forward-fill | family pass behavior; conventions |
| Inference | daily state-contrast series → Newey-West t with lag = horizon; two-sided p; **direction read afterwards, never prejudged** (BFI-001 §G convention) | BFI-001 §G/§I |
| Cost convention | 0.60% round-trip floor reported as `theta_net = theta_mean − 0.006` (reported sensitivity, never a statistical verdict) | BFI-002 memo §8; estate cost authority |
| Outcome data | Dataset B frozen forward returns (close(t)→close(t+k), strict contiguity) — IF the owner selects a return-based outcome (§3 item 1) | foundation.py; freeze manifest v1 |
| Multiplicity default | C7 registered as a **single-cell family** (Holm n = 1 at primary horizon) unless the owner packages C6/C8 with it (§3 item 4) | — |

## 3. Formerly NOT SET — RESOLVED by owner decisions (2026-09-11, incorporated verbatim)

| # | Parameter | Owner decision (verbatim intent) | Registered implementation |
|---|---|---|---|
| 1 | Outcome | "Use directional forward return as the C7 outcome." | Dataset B calendar-indexed close(t)→close(t+k), strict contiguity |
| 2 | Contrast | "Compare the pre-specified high-intensity state against the pre-specified normal/non-high-intensity state." Frozen before execution. | Per formation date: mean fwd-return of high cells (intensity ≥ 2.0) − mean fwd-return of non-high cells (< 2.0); dates lacking either side are skipped and counted |
| 3 | Horizons | "k ∈ {3,5,10}; primary k = 5", using the program's registered forward-return and session-contiguity conventions | Dataset B close→close, strict contiguity (foundation-convention) |
| 4 | Multiplicity | "C7 is its own independent family; do NOT pool with C6 or C8." | Single-cell family: Holm at primary k is the identity (holm_p = raw two-sided p) |
| 5 | MDE/power | "No MDE or formal power claim is authorized unless already supported by an existing authoritative methodology." None exists. | **Registered: "MDE/power not used as a confirmation criterion."** No power claim may be attached to C7 outputs |
| 6 | Descriptive persistence | 45.7–48.1% vs 11.3% figures are CONTEXT ONLY — must not determine thresholds, horizons, contrast, or the decision rule | Registered: context-only; the 2.0 threshold, horizons, contrast, and rule derive from the family-map/descriptive state definition and program conventions, not from those figures |

## 4. What this registration does NOT do

Does not execute C7; does not compute any return; does not tune the 2.0 threshold or state windows from outcomes; does not modify Dataset B, the G1 result, or the withdrawn C1a/C1b status; does not claim C7 was previously preregistered.

## 5. Implementation and verification notes (mechanical, post-approval)

- Executed-form: `g1_harness.py` `c7_build_panel` / `cell_c7` / `run_c7` (fail-closed on the `c7_registered` gate). Freq is **never read**: the C7 panel consumes only flow `value` signs/magnitudes and ohlcv close×volume; a poison test (freq set to garbage on every row) leaves the output byte-identical.
- No breadth-floor exclusion is registered for C7 (its registration §2 lists the exclusions without one) — formation dates are used as they validly form; this absence is part of the registered specification, not an omission.
- Deterministic tests: `test_c7_registration.py` (7/7) — intensity/threshold/boundary, ADV20 window+shift(1) structural check, freq-poison identity, exclusion counts, k-set/primary/contrast exactness, cost sensitivity, fail-closed, determinism. G1 suite unaffected: 16/16.
- CA-window exclusion (corporate action strictly inside (t, t+k]) reuses the G1-registered machinery and is counted per horizon in the output.
