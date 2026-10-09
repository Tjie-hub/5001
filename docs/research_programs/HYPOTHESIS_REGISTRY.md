# Hypothesis Registry

> The operating index of hypotheses across active programs. A hypothesis is **counted in its program's multiplicity family from G1/REGISTERED and never leaves** (PG-3, OS-10). This registry is append-only in spirit: status advances by adding a superseding record, never by silent edit ([[HYPOTHESIS_LIFECYCLE]] HL-1/HL-2).

**Owner:** Research Director / CRO · **Last updated:** 2026-10-09 · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] · [[RESEARCH_PROGRAM]]

## Registered & in-flight

| ID | Program · Family | Mechanism | Status | Frozen record | Family slot |
|---|---|---|---|---|---|
| **HYP-PM-0001** | P-M · {I5,I6,I7,I12} | M1.1 inventory-imbalance mean reversion (I5), tested vs M2.1 (I7) | **FAILED** (F2) 2026-07-18 · was REGISTERED 2026-07-17T07:15:03Z | [[HYP-PM-0001_REGISTERED]] · sha256 `540c2d52…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-M member) |
| **HYP-PM-0003** | P-M · {I5,I6,I7,I12} | M2.1 adverse-selection permanence (I7), `broker_flow`/Dataset A instrument (distinct from HYP-PM-0002's `stockbit_flow_bars`) | **FAILED** (F2) 2026-09-09 · was REGISTERED 2026-09-09T09:22:00Z | [[HYP-PM-0003_REGISTERED]] · sha256 `a2db9204…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (2nd P-M member, independent — Option B/OS-10) |
| **HYP-PM-0004** | P-M · C-family · **C2** conduit disagreement | foreign/locally-owned brokerage net-flow disagreement → forward-return resolution (unconditional daily contrast form) | **INVALID (governance)** — executed in G1 Run 1 2026-09-11, NOT CONFIRMED (Holm p = 1.0); registered species-mix control unimplementable (freq-dependent) | `docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md` · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` · DECISION_LOG D-048 | **C-family consumed** (1st member) |
| **HYP-PM-0005** | P-M · C-family · **C3** breadth surprise | breadth-surprise state (±0.30 vs trailing median) → forward-return continuation (daily state contrast) | **NOT CONFIRMED (VALID, bounded)** — executed G1 Run 1 2026-09-11, primary k=5 Holm p = 1.0; determinate null, 329 daily observations | same registration · `G1_FINAL_EXECUTION_REPORT_2026-09-11.md` | **C-family consumed** (2nd member) |
| **HYP-PM-0006** | P-M · C-family · **C7** intensity-state | gross/ADV20 ≥ 2.0 state → registered outcome (directional forward return; high vs non-high daily contrast) | **NOT CONFIRMED (VALID, determinate null)** — executed 2026-09-14 under D-049 R-6 (`run_id RUN-20260914T015335Z-41bea166a025`); was REGISTERED 2026-09-11 | `C7_REGISTRATION_v1_2026-09-11.md` · `C7_REGISTRATION_READINESS_2026-09-11.md` · [[C7_EXECUTION_REPORT_2026-09-14]] | **C-family consumed** (3rd member) |
| **HYP-PM-0007** | P-M · {I5,I6,I7,I12} | Broker-flow imbalance baseline (BFI-001; research.db `BROKER-001`, IDX80 PIT `broker_flow` top-25) | **INVALID (data)** primary; structure secondaries NOT CONFIRMED (VALID) — executed 2026-09-03 · PREREGISTERED 2026-09-03T10:58:54Z · **alias ratified 2026-09-29 (D-063)** | prereg sha `91c0eb9a…` (`ZCodeProject/bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md`) · `90_results.json` · [[FAILURE_REGISTRY]] FAIL-PM-0007 · DECISION_LOG D-063 | **consumed** (4th P-M member, counted on ratification — conservative denominator, X8/OS-10) |
| **HYP-PM-0009** | P-M · {I5,I6,I7,I12} | **I7 intraday execution timing** — informed/size-constrained execution back-loads within the session; conditional on a net-buying day, back-loaded net buying is followed by higher subsequent return than front-loaded net buying of the same sign (M2 · adverse selection) | **FAILED** (F2) 2026-09-15 · was REGISTERED 2026-09-14 · executed once (EXP-PM-0009/R2) | [[HYP-PM-0009_REGISTERED]] · sha256 `d19dfd0f…` · [[FAILURE_ENTRY]] · DECISION_LOG **D-050**/D-051 · cohort v004 `e1375264…` | **consumed** (3rd P-M member) |
| **HYP-PA-0001** | P-A · {I2,I3,I8} | reconstitution closing-auction dislocation (I8→I2) | **FAILED** (F2) 2026-08-19 · was REGISTERED 2026-07-19T00:19:47Z | [[HYP-PA-0001_REGISTERED]] · sha256 `3692e69a…` · [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] | **consumed** (1st P-A member) |
| **HYP-PM-0010** | P-M · **Price-Trend {T1}** (NEW family) | time-series momentum: trend-state onset (EMA20 slope>+2%, Kaufman ER(20)>=0.30, >=70% closes above EMA20, all at t-1) entered at close, exited on a 3xATR14 trailing stop, 60-session cap | **REGISTERED → IN_TESTING** 2026-09-17T06:35:57Z · forward test **FWD-PM-REGIME-002 OPEN**, ledger empty (0 trades), first eligible entry 2026-09-18 · was FWD-PM-REGIME-001, closed 2026-09-17T06:53:39Z with zero recorded trades and superseded (zero-volume carry-forward guard; see the supersession record below) | [[HYP-PM-0010_REGISTERED]] · `P-M/forward_regime/PROTOCOL.md` — 002 protocol sha256 at open `6e7e1a7b…`, current `4063752e…` (three post-opening amendments, each recorded as observability-only: limitations 9–10, then the daily and weekly IHSG regime fields; cumulative diff +88/−0) · was 001 sha256 `4d3d27da…` | **Price-Trend {T1} opened** (1st member) |
| **HYP-PM-0012** | P-M · **Price-Reversal {R1}** (NEW family) | failed-breakdown anti-edge: sweep below the trailing 20-session low then close back above → **negative** forward excess (avoidance/anti-edge; no entry, never a short) | **REGISTERED → IN_TESTING** 2026-09-21 · forward test **FWD-PM-FADE-001 OPEN**, ledger empty (0 signals), first eligible entry 2026-09-22 | [[HYP-PM-0012_REGISTERED]] · `P-M/forward_fade/PROTOCOL.md` — registration sha256 `e1959672…` · spec frozen 2026-09-20 v1 (`scripts/fade_failed_breakdown.py`, SHA256SUMS) | **Price-Reversal {R1} opened** (1st member) |
| **HYP-PM-0014** | P-M · **Price-Reversal {R1,R2}** (R2; family widened, **D-066**) | big-4 bank 2-ATR climax low (20-session closing low and close <= SMA20 - 2xATR14) -> next-open entry, 10-session excess vs EW liquid book net 0.60% RT; BBCA primary, big-4 pooled secondary | **REGISTERED -> IN_TESTING** 2026-10-05T16:09:16Z | [[forward_bank/PROTOCOL]] · sha256 `2371cc48…` · FWD-PM-BANK-001 | Price-Reversal slot **2** |
| **HYP-PM-0015** | P-M · **Price-Learning {L1}** (NEW family, **D-067**) | learned cross-sectional rank of 14 OHLCV/volume feature ranks (ridge / shallow HistGBR, 6-config grid) vs baseline M0 (low Parkinson-60 + 12-1 momentum); monthly open-to-open, long-only top quintile, top-150 ADV60, net 0.60% RT on turnover; gate vs EW base book | **FAILED** (F2) 2026-10-06 · G1 single run NULL, **D-068** · was REGISTERED 2026-10-06 (D-067) | [[P-M/ml_rank/PREDECLARATION]] · sha256 `5d4dd3d8…` · branch `research/ml-rank-2026-10` @ `f16aa9e` | Price-Learning slot **1** |
| **HYP-PM-0016** | P-M · **Price-Learning {L1}** (D-067) | sniper setup filter (meta-label on the owner's E-SN support-zone entry): 10 setup-day feature ranks; M0 low Parkinson-60 + 126-session momentum, M1 L2 logistic, M2 shallow HistGBR; top-40% selection vs all filled setups, outcome X1 net R; bar 3.2931 at census N=599 (D-071) | **FAILED** (F2) 2026-10-08 · G1 single run NULL, **D-072** · registered + G0 frozen in the same entry (G0 `72b4bd5`, Rev 1 `b3dd0bc`, Rev 2 `d261260`) | [[P-M/sniper_filter/PREDECLARATION]] · sha256 `aa68e12e…` · branch `research/sniper-filter-2026-10` @ `b9e5e5b` | Price-Learning slot **2** |
| **HYP-PM-0017** | P-M · **Structural-Event {SE}** (NEW family, **D-076**) | dividend clientele (D-073): D1 pre-cum demand (anchored run-up into cum, n 547) and D2 ex-day tax-clientele capture (yield ≥ 2%, n 324); total-return EW liquid book net 0.60% RT; Parkinson-60 control; t = min(month, two-way cluster); bar 3.2968 at census N=607 | **FAILED** (F2) 2026-10-09 · G1 single run NULL, **D-077** (`89c3af9`) · was REGISTERED 2026-10-08 (D-076) | [[P-M/dividend_clientele/PREDECLARATION]] · sha256 `50c91491…` · branch `research/dividend-clientele-2026-10` @ `0309cc6` | Structural-Event slot **1** |
| **HYP-PM-0019** | P-M · **Price-Reversal {R1,R2,R3}** (R3; family widened, **D-078**) | market-stress reversal (D-075, liquidity provision): first −2.5σ EW-liquid stress day per episode → bottom-quintile day-t basket, close t → close t+5, minus β × EW liquid market, net D-059 cost; 63 episodes (E1 history_long 2007–2020: 46, E2 5001 2021-07→: 17); bar 3.2973 at census N=608 | **REGISTERED** 2026-10-09 (D-078) · G0 frozen, G1 approved, not yet run | [[P-M/stress_reversal/PREDECLARATION]] · sha256 `23979b75…` · branch `research/market-stress-reversal-2026-10` @ `fa78700` | Price-Reversal slot **3** |

## Status legend

`DRAFT` free-era candidate (unlimited refinement; nothing risked) · `REGISTERED` frozen, risked, in the family · then `IN_TESTING → VALIDATED | FAILED → …` per [[HYPOTHESIS_LIFECYCLE]] §3.

## Family-slot ledger

| Program | Family (append-only) | Members registered | Notes |
|---|---|---|---|
| **P-M · Microstructure Flow** | {I5, I6, I7, I12} | **4** — HYP-PM-0001 (FAILED F2), HYP-PM-0003 (FAILED F2→INVALID-DATA), HYP-PM-0009 (FAILED F2), HYP-PM-0007 (INVALID-DATA; alias of BROKER-001 ratified 2026-09-29, D-063) | family opened at first registration (D-028, PG-3); HYP-PM-0003 registered 2026-09-09 as the 2nd member, counted independently of unregistered HYP-PM-0002 (Option B/OS-10, CRO-adopted) — HYP-PM-0002 remains DRAFT and consumes no slot; HYP-PM-0009 executed once 2026-09-15, FAILED F2 (no power claim per D-050 — non-rejection is not evidence of absence) |
| **P-M · C-family** | {C2, C3, C7} | **3** — HYP-PM-0004 (C2, INVALID), HYP-PM-0005 (C3, NOT CONFIRMED), HYP-PM-0006 (C7, NOT CONFIRMED) | family opened per **D-048** (2026-09-11, Owner Option B): separately-denominated from {I5,I6,I7,I12} — no I-taxonomy assignment made or inferred; C1a/C1b WITHDRAWN pre-execution and not counted; C2's INVALID is governance (controls unimplementable), not an empirical refutation; C7 executed 2026-09-14 under D-049 R-6 authorization, NOT CONFIRMED (Holm p=0.6128 at primary k=5) — see C7_EXECUTION_REPORT_2026-09-14.md |
| **P-A · Auction Dislocation** | {I2, I3, I8} | **1** — HYP-PA-0001 | family opened at first registration (D-028, PG-3); registered 2026-07-19 on realized WP-D N=210/K=13 window |
| **P-M · Price-Trend** | {T1} | **1** — HYP-PM-0010 (REGISTERED, in forward test) | family opened at this registration (D-028, PG-3), owner decision 2026-09-17. Scope: directional trend features derived from OHLCV (MA slope, Kaufman efficiency ratio, participation above a MA, ATR-based exits), liquid IDX, epoch 2021-07-05→2026-09-16. Separately denominated from {I5,I6,I7,I12} and from the C-family: uses **no** broker/flow instrument. No family was split — FWD-PM-VOLEX-001 (Parkinson-60 volatility exclusion) is an **unregistered** prospective record holding no slot. Widening {T1} to absorb volatility/dispersion features is permitted; narrowing or splitting is not. |
| **P-M · Price-Reversal** | {R1} -> {R1, R2} (widened D-066, 2026-10-05) -> **{R1, R2, R3}** (widened D-078, 2026-10-09) | **3** — HYP-PM-0012 (R1, REGISTERED, in forward test), HYP-PM-0014 (R2, REGISTERED, in forward test), HYP-PM-0019 (R3, REGISTERED, G1 approved) | family opened at this registration (D-028, PG-3), owner decision 2026-09-21 (**D-052**). Scope: OHLCV-only short-horizon reversal anti-edges (negative forward excess), liquid IDX. Separately denominated from {I5,I6,I7,I12}, the C-family, and {T1}. Discovered in the 2026-09-17 ~12-arm pattern scan; the scan's multiplicity is carried by this registration (Bonferroni-18 cleared in-sample) and inherited by any future arm registered from it. Widening {R1} permitted; narrowing or splitting not. HYP-PM-0011 reserved-retired, never assigned (D-052). |
| **P-M · Price-Learning** | {L1} | **2** — HYP-PM-0015 (FAILED F2, D-068; question closed at G1 per predeclared null handling), HYP-PM-0016 (FAILED F2, D-072; sniper setup filter, last admitted price-feature study per D-070) | family opened at this registration (D-028, PG-3), owner approval 2026-10-06 (**D-067**). Scope: fitted models combining OHLCV/volume features to rank the liquid cross-section monthly; top-150 ADV60. Separately denominated from {V}, {R1,R2}, C and {T1} (fixed rules vs a fitted model family); multiplicity is carried at program level (6 grid arms enter the census), so the separate family does not loosen any bar. Widening permitted by formal amendment; narrowing or splitting not. |
| **P-M · Structural-Event** | {SE} | **1** — HYP-PM-0017 (FAILED F2, D-077) | family opened at this registration (D-028, PG-3), owner approval 2026-10-08 (**D-076**). Scope: contractual or calendar corporate events that force or attract flow (dividends D-073, tender offers D-074; index and lock-up events only if admitted by their own mechanism entries). Separately denominated from the price families; multiplicity is carried at program level in the census, so the separate family does not loosen any bar. Widening permitted by formal amendment; narrowing or splitting not. |

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
- **HYP-PM-0006 (C7)** — **executed 2026-09-14** under **D-049 R-6** authorization (`g1_config.json`
  `c7_registered: false → true`, the only parameter change; spec fixed verbatim by
  `C7_REGISTRATION_v1_2026-09-11.md` §2/§3). Preflight: 13/13 gates PASS, Dataset B store sha256
  `21661f03…` re-verified unchanged, PIT-aligned, production DB isolation confirmed (ro + query_only).
  Deterministic suites 31/31 (C7 7/7, G1 16/16, provenance 8/8). **Primary k=5: θ = +13.38bp, NW t =
  +0.5061, n=338 days, Holm p = 0.6128 — NOT CONFIRMED.** Secondary k∈{3,10} also non-significant
  (p=0.768, 0.392). Cost-adjusted net −31.34bp to −54.08bp across horizons (sensitivity only, not the
  verdict). Sealed: `run_id RUN-20260914T015335Z-41bea166a025`, output sha256 `c1cc10a2…`,
  `valid_provenance=true`, `drifted_files=[]`. **Terminal per registered-run discipline — no rescue, no
  C8 testing, no parameter changes authorized.** Receipts: DECISION_LOG **D-049** R-6 ·
  `docs/research_programs/P-M/g1_harness/C7_EXECUTION_REPORT_2026-09-14.md`.
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
- **HYP-PM-0010 spec supersession, 2026-09-17T06:53:39+00:00** — FWD-PM-REGIME-001 closed with **zero recorded trades**
  and was superseded by **FWD-PM-REGIME-002**. 001's universe filter admitted zero-volume
  carry-forward bars (IDX suspensions print a repeated-OHLC session, not a calendar gap; 001's audit
  checked only gaps and wrongly recorded "suspension contamination is absent"). A frozen price drives
  the Kaufman efficiency ratio toward 1.0 because its denominator stops growing, so a non-trading
  stock scores as a pristine trend — zero-volume bars are 0.951% of liquid ticker-days but **4.778%**
  of regime-UP liquid ticker-days. Found via **LIFE** (8 consecutive zero-volume sessions at 12725,
  ER 0.95; excluded by 001 only because ADV20 peaked at Rp 976m vs the Rp 1e9 floor). 002 adds a
  traded-days guard (`volume > 0` at entry, >= 18 of trailing 20 sessions traded); mechanism and all
  thresholds unchanged. Removing the artifact **lowers** the effect — ex-2025 +1.106% → **+0.928%**
  /trade, t 3.35 → 2.83 — so the decision point moves **24 → 36 months** and 24 becomes a second
  interim. **HYP-PM-0010 and its {T1} family slot are retained, not re-registered** (no forward
  observation existed; mechanism unchanged), **flagged for owner override** — the conservative
  reading would register HYP-PM-0011 and advance {T1} to 2 members.
- **Book-level overlay declared 2026-09-17** (`BOOK_OVERLAY_POLICY.md`) — volatility exclusion is
  applied at **allocation**, outside every frozen spec. It is **not a hypothesis and consumes no
  family slot**: its evidential home is FWD-PM-VOLEX-001. Owner chose this over widening
  `Price-Trend {T1}` to cover volatility/dispersion features, which would have been irreversible
  (families widen, never narrow). **FWD-PM-REGIME-002's endpoint remains computed on the unfiltered
  signal set** — the overlay never touches the ledger, and combined book performance is not evidence
  for either test. Five other entry filters (slope-Q5, slope-Q4+Q5, extension-Q5, and combinations)
  were measured and rejected; none changed the win rate, which stayed 32-34% across all six — the
  losses are the mechanism, not a removable subset.
- **Exploratory pattern scan, 2026-09-17** (`P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md`) —
  ~12 unregistered arms measured on one corpus: liquidity sweep (production `engine/smc.py`, N=36,739,
  ex-2025 **-1.33%**, t **-7.16**), failed breakdown (**-1.94%**, t **-7.15**), failed breakout,
  resistance breakout, falling wedge (x2), Wedge Pop (Kell, **-1.89%**, t -4.01), Episodic Pivot
  (Qullamaggie). **Every mean-reversion pattern is significantly NEGATIVE** — anti-edges, not nulls.
  Only continuation is positive and it collapses outside 2025. Flow confirmation does not rescue the
  sweep. **Consumes no family slot** and is deliberately NOT filed in `FAILURE_REGISTRY.md`, whose
  counts feed family denominators and which records only *registered* hypotheses. Any future
  registration drawn from this scan inherits its ~12-arm multiplicity. Two findings worth carrying:
  (a) `stockbit_flow.composite_score` is **unpopulated**, so the engine's composite flow score has
  never been testable; (b) **single-ticker validation is worthless here** — every refuted pattern
  looks profitable on BRPT, which sits at the **91st percentile** of a per-ticker distribution where
  only **35%** of tickers are positive (median -1.59%, 10th/90th -9.23%/+4.15%). A randomly chosen
  ticker has a ~35% chance of appearing to confirm a genuinely negative effect.
- **HYP-PM-0012 (Price-Reversal {R1}, opened 2026-09-21)** — registered under **D-052** per Owner
  instruction (decision package `P-M/forward_fade/OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md`,
  Option A). Failed-breakdown anti-edge: sweep below the trailing 20-session low, close back above
  → forward excess NEGATIVE vs both benchmarks, net of 0.60% RT. In-sample: h=20 −1.46%/t −5.64
  (IHSG), −1.47%/t −8.20 (EW-book), ex-2025 −1.88%/t −6.80; 12,131 signals, 757 tickers, top name
  0.6%; three independent builds agree within 0.3pp; Bonferroni-18 cleared. Endpoint: 12-month
  t < −2.5 BOTH benchmarks, 18-month t < −3.0 both; REJECT if cumulative excess >= 0 on either or
  <100 signal-dates by month 12; decay haircut −0.5% at month 12. Anti-edge only — no entry, never
  a short; any overlay use requires a §3 checkpoint first (BOOK_OVERLAY_POLICY §4) and FWD-PM-
  REGIME-002 is untouched. HYP-PM-0011 reserved-retired, never assigned (D-052).

