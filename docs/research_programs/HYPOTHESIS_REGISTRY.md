# Hypothesis Registry

> The operating index of hypotheses across active programs. A hypothesis is **counted in its program's multiplicity family from G1/REGISTERED and never leaves** (PG-3, OS-10). This registry is append-only in spirit: status advances by adding a superseding record, never by silent edit ([[HYPOTHESIS_LIFECYCLE]] HL-1/HL-2).

**Owner:** Research Director / CRO · **Last updated:** 2026-09-17 · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] · [[RESEARCH_PROGRAM]]

## Registered & in-flight

| ID | Program · Family | Mechanism | Status | Frozen record | Family slot |
|---|---|---|---|---|---|
| **HYP-PM-0001** | P-M · {I5,I6,I7,I12} | M1.1 inventory-imbalance mean reversion (I5), tested vs M2.1 (I7) | **FAILED** (F2) 2026-07-18 · was REGISTERED 2026-07-17T07:15:03Z | [[HYP-PM-0001_REGISTERED]] · sha256 `540c2d52…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-M member) |
| **HYP-PM-0003** | P-M · {I5,I6,I7,I12} | M2.1 adverse-selection permanence (I7), `broker_flow`/Dataset A instrument (distinct from HYP-PM-0002's `stockbit_flow_bars`) | **FAILED** (F2) 2026-09-09 · was REGISTERED 2026-09-09T09:22:00Z | [[HYP-PM-0003_REGISTERED]] · sha256 `a2db9204…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (2nd P-M member, independent — Option B/OS-10) |
| **HYP-PM-0004** | P-M · C-family · **C2** conduit disagreement | foreign/locally-owned brokerage net-flow disagreement → forward-return resolution (unconditional daily contrast form) | **INVALID (governance)** — executed in G1 Run 1 2026-09-11, NOT CONFIRMED (Holm p = 1.0); registered species-mix control unimplementable (freq-dependent) | `docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md` · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` · DECISION_LOG D-048 | **C-family consumed** (1st member) |
| **HYP-PM-0005** | P-M · C-family · **C3** breadth surprise | breadth-surprise state (±0.30 vs trailing median) → forward-return continuation (daily state contrast) | **NOT CONFIRMED (VALID, bounded)** — executed G1 Run 1 2026-09-11, primary k=5 Holm p = 1.0; determinate null, 329 daily observations | same registration · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` | **C-family consumed** (2nd member) |
| **HYP-PM-0006** | P-M · C-family · **C7** intensity-state | gross/ADV20 ≥ 2.0 state → registered outcome (directional forward return; high vs non-high daily contrast) | **REGISTERED** 2026-09-11 (`C7_REGISTRATION_v1_2026-09-11.md`) · pending execution (gated) | `C7_REGISTRATION_v1_2026-09-11.md` · `C7_REGISTRATION_READINESS_2026-09-11.md` | **C-family registered** (3rd member — not yet executed) |
| **HYP-PM-0009** | P-M · {I5,I6,I7,I12} | **I7 intraday execution timing** — informed/size-constrained execution back-loads within the session; conditional on a net-buying day, back-loaded net buying is followed by higher subsequent return than front-loaded net buying of the same sign (M2 · adverse selection) | **FAILED** (F2) 2026-09-15 · was REGISTERED 2026-09-14 · executed once (EXP-PM-0009/R2) | [[HYP-PM-0009_REGISTERED]] · sha256 `d19dfd0f…` · [[FAILURE_ENTRY]] · DECISION_LOG **D-050**/D-051 · cohort v004 `e1375264…` | **consumed** (3rd P-M member) |
| **HYP-PA-0001** | P-A · {I2,I3,I8} | reconstitution closing-auction dislocation (I8→I2) | **FAILED** (F2) 2026-08-19 · was REGISTERED 2026-07-19T00:19:47Z | [[HYP-PA-0001_REGISTERED]] · sha256 `3692e69a…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-A member) |
| **HYP-PM-0010** | P-M · **Price-Trend {T1}** (NEW family) | time-series momentum: trend-state onset (EMA20 slope>+2%, Kaufman ER(20)>=0.30, >=70% closes above EMA20, all at t-1) entered at close, exited on a 3xATR14 trailing stop, 60-session cap | **REGISTERED → IN_TESTING** 2026-09-17T06:35:57Z · forward test FWD-PM-REGIME-001 OPEN, ledger empty, first eligible entry 2026-09-18 | [[HYP-PM-0010_REGISTERED]] · protocol sha256 `4d3d27da…` · `P-M/forward_regime/PROTOCOL.md` | **Price-Trend {T1} opened** (1st member) |

## Status legend

`DRAFT` free-era candidate (unlimited refinement; nothing risked) · `REGISTERED` frozen, risked, in the family · then `IN_TESTING → VALIDATED | FAILED → …` per [[HYPOTHESIS_LIFECYCLE]] §3.

## Family-slot ledger

| Program | Family (append-only) | Members registered | Notes |
|---|---|---|---|
| **P-M · Microstructure Flow** | {I5, I6, I7, I12} | **3** — HYP-PM-0001 (FAILED F2), HYP-PM-0003 (FAILED F2→INVALID-DATA), HYP-PM-0009 (FAILED F2) | family opened at first registration (D-028, PG-3); HYP-PM-0003 registered 2026-09-09 as the 2nd member, counted independently of unregistered HYP-PM-0002 (Option B/OS-10, CRO-adopted) — HYP-PM-0002 remains DRAFT and consumes no slot; HYP-PM-0009 executed once 2026-09-15, FAILED F2 (no power claim per D-050 — non-rejection is not evidence of absence) |
| **P-M · C-family** | {C2, C3, C7} | **3** — HYP-PM-0004 (C2, INVALID), HYP-PM-0005 (C3, NOT CONFIRMED), HYP-PM-0006 (C7, pending execution) | family opened per **D-048** (2026-09-11, Owner Option B): separately-denominated from {I5,I6,I7,I12} — no I-taxonomy assignment made or inferred; C1a/C1b WITHDRAWN pre-execution and not counted; C2's INVALID is governance (controls unimplementable), not an empirical refutation; C7 execution gated (`c7_registered=false` + runs/<run_id> provenance wrapper per D-048) |
| **P-A · Auction Dislocation** | {I2, I3, I8} | **1** — HYP-PA-0001 | family opened at first registration (D-028, PG-3); registered 2026-07-19 on realized WP-D N=210/K=13 window |
| **P-M · Price-Trend** | {T1} | **1** — HYP-PM-0010 (REGISTERED, in forward test) | family opened at this registration (D-028, PG-3), owner decision 2026-09-17. Scope: directional trend features derived from OHLCV (MA slope, Kaufman efficiency ratio, participation above a MA, ATR-based exits), liquid IDX, epoch 2021-07-05→2026-09-16. Separately denominated from {I5,I6,I7,I12} and from the C-family: uses **no** broker/flow instrument. No family was split — FWD-PM-VOLEX-001 (Parkinson-60 volatility exclusion) is an **unregistered** prospective record holding no slot. Widening {T1} to absorb volatility/dispersion features is permitted; narrowing or splitting is not. |

## Notes

- **HYP-PM-0001** — registered under a **friction-anchored MDE** (round-trip ≈ 0.60% from the cost authority) and a **history-maturity gate** (validation in-sample until the ~1yr flow history lengthens). Terminal reachable tier **C2** (EV-9, N=1). **EXP-PM-0001 executed 2026-07-18T01:09:37Z (in-sample) → FAILED, mode F2 · Prediction failure**: primary k=15 gross signed reversal −0.0008%/trade (t=−0.35), net −0.6008%; robustness signs inconsistent ⇒ M1.1 refuted per the frozen falsification rule. Receipts: T5 custody + T7 [[FAILURE_ENTRY]]; product [[EVIDENCE_PACKAGE]] (C2 refutation, R12). **Terminal** — continuation only via T12 supersession (a new registration); stays counted in the P-M family (X8). See [[FAILURE_REGISTRY]].
- **HYP-PM-0003** — registered under a **friction-anchored MDE** (round-trip ≈ 0.60% from the cost
  authority, `engine/exits/costs.py`), primary test `bootstrap_ci` (`research/statistics.py`,
  clustered inference recorded as a future robustness extension, not implemented), α=0.05/power=0.80
  (hypothesis-specific convention), and a **history-maturity gate** (D-046/D-047 — Dataset A's
  backfilled span eligible for span-based maturity, no numeric N exists or is invented; validation
  is in-sample only). Bound to `DS-broker_flow-idx80-nonpit-2025_2026v1` (FROZEN, D-043),
  `provenance_hash 329b22e49f0e…`. Tests M2.1/I7 — the same taxonomy entry HYP-PM-0002 (unregistered
  draft, `stockbit_flow_bars` instrument) also targets; multiplicity counted **independently** per
  OS-10 (CRO-adopted, Option B), with an explicit, preserved caveat that observation-level
  independence between the two datasets (both describing the same underlying executed IDX trades)
  is unresolved — a scientific/evidential limitation, not a multiplicity blocker.
  **EXP-PM-0003 executed 2026-09-09T09:44:17Z (in-sample) → FAILED, mode F2 · Prediction failure**:
  primary k=7 gross signed continuation +0.0538% (CI95 [−0.0656%, +0.1768%], includes zero); net of
  0.60% friction −0.5462%. Robustness signs across k∈{3,7,15} = {−,+,−}. Receipts: T5 custody + T7
  [[FAILURE_ENTRY]]; product [[EVIDENCE_PACKAGE]] (C2 refutation, R12). Preserved caveat carried into
  the failure record: this result is not, by itself, independent evidence separable from
  HYP-PM-0002's own eventual (not-yet-executed) result. **Terminal** — continuation only via T12
  supersession (a new registration); stays counted in the P-M family (X8). See
  [[HYP-PM-0003_REGISTERED]], [[HYP-PM-0003_DRAFT]], [[HYP-PM-0003_POWER]], [[FAILURE_REGISTRY]].
- **HYP-PM-0004/0005/0006 (C-family, opened per D-048, 2026-09-11)** — the {C2, C3, C7} arms were
  registered 2026-09-11 under the Owner-authorized replacement registration
  (`docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md`; the original
  `BROKER_FLOW_PREREGISTRATION.md` was searched for exhaustively and NOT FOUND — the replacement is a NEW
  dated registration, not a reconstruction) and executed once as **G1 Run 1** on frozen Dataset B (store
  sha256 `21661f03…`, FINGERPRINT_v2 `1a68ab1c…`). Outcomes, preserved exactly: **C2 = INVALID
  (governance)** — executed but its registered species-mix control was unimplementable (freq-dependent), so
  the executed unconditional contrast does not test the designed conditional estimand; **C3 = VALID → NOT
  CONFIRMED, bounded** — primary k=5 θ = +5.8 bp, NW t = +0.323, Holm p = 1.0, signs +/+/−, determinate at
  329 daily observations; **C1a/C1b = WITHDRAWN_FREQ_DEPENDENT** — no numbers, never executed. **G1 overall
  = SPLIT / governance-invalidated.** No rescue, re-run, or re-specification is authorized. C7
  (`HYP-PM-0006`) is REGISTERED and execution-gated. Full receipts: DECISION_LOG **D-048** ·
  `docs/research_programs/P-M/g1_harness/G1_FINAL_EXECUTION_REPORT_2026-09-11.md` ·
  `G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md`.
- **HYP-PM-0009** — **REGISTERED 2026-09-14** per Owner/CRO ruling [[DECISION_LOG]] **D-050**. Mechanism
  **M2 / I7 · intraday execution timing**: informed and size-constrained participants back-load execution
  within the session, so conditional on a net-buying day, back-loaded net buying should be followed by
  higher subsequent return than front-loaded net buying of the same sign. **H₀ : `theta_primary ≤ 0`**
  against **H₁ : `theta_primary > 0`** — one-sided; a negative `theta_primary` is a NON-REJECTION, never a
  reversed finding. Population is the **v004 PIT-valid cohort**, bound by fingerprint
  `e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba` — 76 sessions (2026-04-28 →
  2026-09-11), 61,335 admissible ticker-days, 868 tickers, 19,793,865 bar rows — accepted under D-1 and
  **disjoint** from the ~277-session historical window the candidate specification described, which is
  excluded wholesale under E-PIT-1 (99.41% of its cells written >120 days after their session, median lag
  364 days; bias **B3 / F7**). **Ex-ante criterion: the 0.60% round-trip friction floor only.** Per D-050
  the Owner authorized I7 to proceed **without an ex-ante statistical power/MDE claim**, accepting the
  absence of an authoritative I7-specific σ and feasibility gate as a **governance limitation** — not
  filled by estimation, analogy, or invented methodology. **Consequently I7 carries no power claim: a
  non-rejection is not evidence of absence and must never be reported as one.** Declared limitations: **R7
  provenance** (PIT rests on a same-commit `updated_at` write timestamp; the vendor's original payload is
  not preserved — a *verification*, not an availability, limitation; `custody_partition: in-sample`) and
  **B4** (Papan Pemantauan Khusus / board membership unidentifiable). Pre-registration verification: 27/27
  tests, 8/8 executable validation gates, ledger exact and MECE. **EXP-PM-0009/R2 executed 2026-09-15T01:41:30Z (in-sample, v004 cohort) → FAILED, mode F2 · Prediction failure**: primary k=1 (entry close(t+1), outcome close(t+2)/close(t+1) − 1) θ_primary = **+0.0337%** per formation-day, Newey-West HAC t (lag 5) = **0.1102**, two-sided p = **0.912223** (Holm = identity), **64 daily observations** (6 dates skipped and counted); θ_net sensitivity = **−0.5663%** (sensitivity only). Kill rule met ⇒ M2/I7 back-loading prediction refuted at this specification. **Carried verbatim: I7 has NO power claim (D-050) — this non-rejection is NOT evidence of absence and must never be reported or used as one.** R7 PIT provenance limitation retained. R1 the same day was INVALID (implementation-only exit-index defect, estimand never evaluated; artifacts preserved; frozen block `d19dfd0f…` verified unchanged). Terminal reachable tier **C2** (EV-9, N=1). **Terminal (HL-3)** — continuation only via T12 supersession; counted in the family (X8). See [[HYP-PM-0009_REGISTERED]] (frozen, sha256 `d19dfd0f…`) · `experiments/EXP-PM-0009/{MANIFEST,CLOSE_OUT_REPORT}.md` · [[FAILURE_REGISTRY]] FAIL-PM-0009.
- **HYP-PA-0001** — **EXP-PA-0001 executed 2026-08-19 → FAILED, mode F2 · Prediction failure.** Test 1 (primary, gross, both directions, n=180, G=13): mean signed reversal +0.7261%, SE(CR1) 0.5026%, t=1.445, CI95 [−0.3691%, +1.8212%] — CI includes zero. Test 2 (capturable, DELETE-only, n=98): gross −0.2488% → net of 0.60% friction −0.8488%. Both failed ⇒ refuted per the frozen rule. Exact wild cluster bootstrap (all 2^13 sign vectors) agrees with the asymptotic test on every sample. **Substantive finding: the mechanism is directional, not symmetric** — ADD-side +1.8911% (CI95 [+0.6677%, +3.1144%], WCB p=0.0132, robust to all 13 leave-one-cluster-out refits, positive in 11/13 review dates) versus DELETE-side −0.2488%. Pre-registered gross-only and **not capturable** (shorting-constrained on IDX, C-4); it does not rescue the hypothesis. Realised power was ~4× better than the pre-registered MDE assumed, so the pooled null is informative, not underpowered. Terminal (HL-3); continuation only via T12. Receipts: [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]]. See [[FAILURE_REGISTRY]].
- **HYP-PM-0010 (Price-Trend {T1}, opened 2026-09-17)** — registered under the same
  **friction-anchored** convention as the P-M flow arms (round-trip from the cost authority,
  `engine/exits/costs.py`), with the operator's stated all-in round trip of **0.50%** recorded
  separately in PROTOCOL.md §2.1 alongside a sensitivity table and a **1.47% breakeven**. Primary
  endpoint is per-trade excess over IHSG with **one-way entry-date-clustered** standard errors
  (clustered inference implemented, unlike HYP-PM-0003's deferred extension). Powered at **n ≈ 514
  trading days (~24 months)** against the **ex-2025** planning effect of +1.106%/trade (SE 0.330%,
  t 3.35); the full-sample +2.260% is 2025-inflated and is **not** the planning basis. Interim read
  at 12 months is report-only. **Disclosed prior search:** a 48-cell threshold grid was run before
  registration (PROTOCOL.md limitation 8); a tighter cell nearly doubles the ex-2025 effect but
  inverts in 2026 and is deliberately not adopted — adopting it requires a new spec id and inherits
  that count. **Three policy overlays were tested and rejected pre-registration** (wider trailing
  stops, SIDEWAYS support/resistance mean reversion, IHSG-downtrend gating) and are recorded in
  PROTOCOL.md §4.1 so they cannot re-enter mid-test. Carried limitations: survivorship (the corpus
  holds only names still listed as of 2026-09 — bias optimistic, **unmeasured**), optimistic
  close-to-close fills, effective breadth ~10 from ~131 nominal positions, and sector neutrality
  **untested and unenforceable** (no ticker→sector map exists for 77% of the universe;
  `engine/sector_rotation.py` maps 82 of 959 tickers and returns a permissive `"sector unknown"`
  for the rest).
