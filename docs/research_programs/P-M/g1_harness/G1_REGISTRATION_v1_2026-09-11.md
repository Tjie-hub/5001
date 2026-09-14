# G1 REPLACEMENT REGISTRATION — v1 (2026-09-11)

**Identity:** NEW, dated, owner-authorized replacement registration for the G1 experiment. It is **NOT** the recovered original `BROKER_FLOW_PREREGISTRATION.md` — that artifact remains NOT FOUND (exhaustive retrieval 2026-09-11) and nothing in this document claims or reconstructs it. This registration is created under the owner's explicit authorization ("dated replacement registration for the G1 work") after the original was confirmed unavailable.

**Status:** REGISTERED (replacement) · **Date:** 2026-09-11 · **Supersedes:** nothing (there was no recoverable prior registration on this side) · **Governing design record:** `pm_data_audit/PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md` (DESIGN memo — adopted here as the specification source per owner authorization) + inherited BFI-001 execution conventions (`ZCodeProject/bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md` §C/§D/§I) + owner directives of 2026-09-11.

**Every parameter below was inventoried against the harness implementation (`g1_harness.py`) and the design record. Parameters that could not be established from the authoritative record are explicitly registered as NOT SET (§9) — none was silently resolved.**

---

## 1. Family and arms

| Arm | Status | Notes |
|---|---|---|
| C1a (primary, freq-dependent) | **WITHDRAWN** | Owner decision 2026-09-11: freq probe did not establish orders-vs-fills; ~124× cross-vendor inconsistency unresolved. Per BFI-002 memo §9's pre-declared fallback ("the design is withdrawn, not re-cut"). Never executes while the withdrawal is in force (`freq_resolution="withdrawn"` → `WITHDRAWN_FREQ_DEPENDENT`, no numbers). |
| C1b (robustness, freq-dependent) | **WITHDRAWN** | Same basis, same moment. |
| C2 (conditional conduit disagreement) | **RETAINED** | Freq-free. Memo §7 C2. |
| C3 (breadth surprise) | **RETAINED — LEAD** | Freq-free, cap-robust. Memo §7 C3 and §9 fallback ordering ("C3 as lead, C2 as secondary"). |

Retained family for multiplicity = **{C2, C3}** (Holm across both at the primary horizon).

## 2. Unit of observation and timing

- One observation per (ticker i, formation session t), t on the PIT roster (`DATASET_B_PIT_ROSTER`, sha `f7e2fec0…` v1 / content-identical v2), 386 admitted sessions 2025-01-02→2026-08-27.
- Formation consumes ONLY information dated ≤ t: broker-flow rows with `trade_date == t`; ADV20 shifted; trailing breadth median strictly past. No future-data path (synthetic-tested: T+1 dumps, excluded sessions, forward-dated rows cannot leak).

## 3. Data sources

| Input | Source | Pin |
|---|---|---|
| Broker flow (limit=150, full population) | frozen store `broker_flow_b` | FINGERPRINT_v2 `1a68ab1c…` reproduced at freeze; store file sha256 `21661f03…` |
| Broker-flow population counters | store `bandar_detector_b` | equality with returned counts verified 30,877/30,877 |
| OHLCV (outcome + volume) | production `ohlcv`, `is_final=1`, read-only | pinned inside FINGERPRINT_v2 fold |
| Suspensions | production `suspension_events`, expanded over the declared calendar | — |
| Corporate actions | `corporate_action_events` (primary) + basis/quarantine detectors | RAJA quarantined |
| **NF control** | production `stockbit_flow`, `NF = (buy_lot − sell_lot)/(buy_lot + sell_lot)` | window digest `60f5f91c…` — **re-verify immediately before execution; halt + re-pin on drift** |
| Session calendar | `DATASET_B_SESSION_CALENDAR_v2.json` (sha `5012be23…`) | strict contiguity enforced |

## 4. Retained arm definitions (frozen)

**C3 — breadth surprise (lead).**
- breadth(i,t) = (n_buy − n_sell)/(n_buy + n_sell) from the full-population store rows of (i, t).
- surprise(i,t) = breadth(i,t) − per-ticker trailing median of breadth over ALL prior valid panel rows (strictly past; minimum history 30 observations).
- States: surprise ≥ +0.30 (broad) vs ≤ −0.30 (narrow) (threshold frozen from measured incidence, memo §7).
- Daily spread: mean fwd-return of broad states − mean fwd-return of narrow states on each formation date.

**C2 — conduit disagreement (secondary).**
- Shares from full-population store values: for_net = (Σ Asing buy − Σ Asing sell)/gross; loc_net symmetric; for_gross = (Σ Asing |value|)/gross; loc_gross symmetric.
- Disagreement state: for_gross ≥ 0.15 AND loc_gross ≥ 0.15 AND sign(for_net) ≠ sign(loc_net).
- Daily spread: mean fwd-return of long-foreign (for_net>0, loc_net<0) − mean fwd-return of short-foreign (for_net<0, loc_net>0).

**C1a/C1b — WITHDRAWN (registered, not specified-for-execution).** Their former definitions (F-classifier species mix; ST = deskBuyShare − deskSellShare; θ(k) within signed-NF tercile buckets) remain documented in the design memo and harness code for provenance only.

## 5. Outcome and horizons

- Forward returns: Dataset B calendar-indexed close(t)→close(t+k), exactly k admitted sessions apart, strict contiguity (any excluded session inside (t, t+k] invalidates), no substitution; parity-tested against `foundation.forward_returns`.
- k ∈ {3, 5, 10}; **primary read k = 5**; no post-hoc horizon selection.

## 6. Exclusions (frozen)

1. Ticker quarantined (adjustment-basis; RAJA-class).
2. Suspended at t, or missing bar at t / t+k / any window cell checked by the contiguity rule.
3. gross ≤ 0 or no flow rows.
4. close(t) < 100.
5. |ret1| ≥ 0.15 (formation-day move proxy; no prior-session close ⇒ excluded).
6. No ratified NF value for (i, t).
7. Corporate action ex-date strictly inside (t, t+k] (k-specific).
8. Formation-date breadth floor: fewer than 40 valid names ⇒ date excluded (counted).
9. Species-classifier unclassified rows: not applicable (C1a/C1b withdrawn); freq is never read.

Every exclusion is counted per stage and emitted in the output accounting block.

## 7. Inference (frozen)

- Per cell: the daily spread/θ series IS the date clustering. Statistic: mean, Newey-West t with lag = k (BFI-001 convention), two-sided p via erfc. Constant/insufficient series → NaN t (never fabricated).
- Multiplicity: Holm step-down across the **retained arms {C2, C3} at k = 5**, α = 0.05. Non-computed arms are excluded from the family (and carry no p-value).
- Cost sensitivity: `theta_net_cost_floor = theta_mean − 0.006` reported per cell (estate cost authority; reported, never optimized).

## 8. Registered decision rules

- Per retained arm: **confirmed** iff Holm-adjusted p < 0.05 at the primary horizon AND sign consistency across k ∈ {3, 5, 10} is reported; otherwise **not confirmed** (recorded as such — no rescue, no re-specification, no secondary-arm promotion).
- **No KILL rule is pre-registered for C2/C3** — the design record contains none; this absence is registered explicitly rather than invented.
- Cost-floor figures are economic-relevance readings only; they never flip a statistical verdict.

## 9. Explicitly registered NOT-SET parameters and limitations

1. **MDE/power: NOT SET.** No ratified power/effective-N methodology exists (DEP-B row 6, diagnostic-only). No power claim may be attached to any G1 output.
2. **C3 falsification clause "adds nothing after NF and ST controls": NOT EXECUTABLE** — ST is withdrawn with C1a (freq-dependent). C3 runs as the unconditional state contrast above; the clause is registered as inapplicable, not silently dropped.
3. **C2 "species mix as control": NOT EXECUTABLE** for the same reason; C2 runs without species control. Limitation recorded.
4. **NF as a conditioning control for C2/C3:** the retained execution form is unconditional state contrasts; a control-conditioned regression variant is **not registered** (it would require new implementation, outside this authorization). NF remains a ratified covariate carried in the panel.
5. **ADV20 statistic and NW(k) inference binding:** inherited BFI-001 conventions (rolling-20-session median of traded value, shift(1); NW lag k), carried as-is under the owner's authorization of this replacement; not independently re-derived.
6. **Availability convention:** flow facts of session t (broker flow, NF, breadth) are formation inputs at t; `stockbit_flow` file materialization is T+1 morning (owner-declared); OHLCV `is_final=1`. The after-close convention otherwise inherits BFI-001 §C prose (DEP-B row 8 recorded).

## 10. Verification obligations at execution time

1. `check_gates` returns empty (all four gates true, `synthetic=false`).
2. Store sha256 == `21661f03…` (freeze manifest); FINGERPRINT_v2 `1a68ab1c…` and supplementary fold `13033786…` reproduce.
3. `stockbit_flow` window digest == `60f5f91c…` (halt + re-pin + record if drifted).
4. `capture_manifest` fully terminal (enforced inside the loader).
5. Output JSON written to `g1_real_output.json` and immediately preserved with the config snapshot, code sha256, freeze fingerprint, NF digest, and execution timestamp.

## 11. Provenance hashes at registration

| Artifact | sha256 (16…) |
|---|---|
| Freeze manifest v1 | `95f2c998760ba6f2` |
| Store file | `21661f033145ef90` |
| FINGERPRINT_v2 dataset fp | `1a68ab1c6c33409f` |
| Supplementary store fold | `1303378683819f17` |
| stockbit_flow window extract | `60f5f91c33b929cd` |
| PIT roster v1 | `f7e2fec030116a90` |
| Session calendar v2 | `5012be2315dc82cc` |
| BFI-002 design memo (spec source) | `9c87888f61bfdb51` |
| BFI-001 frozen prereg (conventions source) | `91c0eb9a4a42630f` |
| Owner decision packet | `G1_OWNER_DECISION_PACKET_2026-09-11.md` |
| Governance unblock record (NF) | `G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md` |
