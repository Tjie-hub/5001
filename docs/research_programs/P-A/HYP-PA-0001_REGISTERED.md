# HYP-PA-0001 — REGISTERED (frozen, immutable)

> **This is the frozen registration record.** Per explicit Human Owner authorization, HYP-PA-0001 passed **G1** and underwent the irreversible **DRAFT → REGISTERED** transition ([[HYPOTHESIS_LIFECYCLE]] T4/G1, HL-2). The claim is now **risked** and has **joined the P-A family {I2,I3,I8} permanently** (PG-3, OS-10). The bytes between the FROZEN markers are sealed by the SHA-256 in the receipt (§Registration receipt); **any change is a new hypothesis (supersession T12), never an edit** (R15). Content below is transcribed verbatim from `HYP-PA-0001_DRAFT.md` §S1–§S3 as ratified (CRO ex-ante criteria + Owner GO, 2026-07-19); no methodology, value, or criterion was altered in the transcription.

<!--FROZEN-START-->
```
hypothesis_id:          HYP-PA-0001
status:                 REGISTERED
program:                P-A · Auction Dislocation
family:                 P-A {I2, I3, I8}   # DECISION_LOG D-028 — append-only; joined permanently (PG-3); first member
preregistered_at:       2026-07-19T00:19:47Z

mechanism_ref:          MECH-recon-dislocation
structural_barrier:     M6 — Market Design (index-methodology rule). The flow is a MANDATE, not
                        a mispricing. No quantity of arbitrage capital removes it — arbs shift
                        its timing, but the mandated flow must still clear. The barrier is the
                        index-tracking obligation itself (M6 structural).
participant_class:      passive/index-tracking funds (FORCED) vs. arbitrageurs/LPs (voluntary)

prediction:             ADDED names: abnormal return UP into the effective-date close, then
                        REVERSING DOWN over t+1..t+k. DELETED names: the mirror.
                        => event-level SIGNED reversal return (signed against event direction) > 0.
                        This is a MECHANISM claim (gross, both directions) — distinct from the
                        CAPTURABILITY claim below (net-of-cost, direction-restricted).
                        [readiness-review C-1/C-4: split from a single conflated claim]

null_hypothesis:        H0: mean signed reversal (gross) over t+1..t+k = 0

alternative_hypothesis: Two-part, pre-registered separately (resolves readiness-review C-1):
                        H1_mechanism (PRIMARY, gross, both directions, N=210):
                           mean signed reversal > MDE_stat, cluster-robust (review-date) SE.
                           Tests whether the M6 mechanism produces displacement+reversal at all.
                        H1_capturable (SECONDARY, net-of-cost, DELETE-only, N=105):
                           mean signed reversal - 0.60% round-trip friction > 0.
                           DELETE-side reversal capture is LONG-only (buy the depressed close,
                           sell into the reversal) — executable without shorting. ADD-side
                           reversal capture requires SHORTING the inflated close, which is
                           execution-constrained on IDX for most names (readiness-review C-4) —
                           ADD-side is therefore reported gross-only, NEVER claimed as a
                           net/capturable edge.

scope:                  LQ45 / IDX30 / IDX80 reconstitution add & delete events; liquid universe;
                        daily frequency; effective dates per published IDX reviews.
                        REALIZED coverage (WP-D, [[COVERAGE_REPORT]]): 2022-08-01 → 2026-05-04,
                        210 ticker-events (105 ADD / 105 DELETE; 192 distinct economic events),
                        13 review-date clusters. Two clusters (2021-H2, 2022-H1) remain unsourced;
                        the pre-2022-08 window is OUT OF SCOPE for this registration, not silently
                        included in it. [readiness-review R-3]

refutation_condition:   "If the mean signed post-effective reversal (gross) is not statistically
                         distinguishable from zero at the cluster-robust MDE_stat, OR is net-of-
                         cost negative on the DELETE-only capturable subsample, the mechanism is
                         refuted for IDX at this fidelity."   # one sentence, R14

multiplicity_family:    P_A_AUCTION_DISLOCATION {I2, I3, I8}   # first member; append-only (PG-3)

assumptions:            A-PA1  announcement/effective dates as published in secondary media are
                               accurate (53% of events are SECONDARY_SINGLE-sourced — the
                               crosschecked-only robustness leg below guards this, R-4)
                        A-PA2  the `ohlcv` close print equals, or closely proxies, the closing-
                               auction print used by index funds to rebalance
                        A-PA3  passive/index-tracking AUM tracking these indices is large enough,
                               relative to the name's liquidity, to move the close — theory-first
                               (Shleifer 1986), NOT IDX-calibrated; untested until the experiment runs
                        A-PA4  market-model parameters (vs IHSG) are stable over the pre-event
                               estimation window (no confounding corporate action in-window)
                        A-PA5  EXECUTION — the single cost authority (`engine/exits/costs.py`,
                               0.60% round-trip) is assumed to apply to closing-auction execution;
                               UNVERIFIED for auction prints specifically (readiness-review C-4).
                               This is why the net/capturable claim (H1_capturable) is scoped to
                               DELETE-only, not asserted for the full sample
                        A-PA6  multi-index duplicate rows (a ticker added to >1 index on the same
                               effective date) are ONE economic event, not independent draws; the
                               192-distinct-event dedup key is (ticker, effective_date, direction)
                               [readiness-review R-1]

validation_criteria:    { estimator: event-study CAR, market-model abnormal returns (vs IHSG);
                          run_up_window: [announcement .. effective]; reversal_window: [t+1 .. t+k];
                          estimation_window: 230 td ending ~20 td before announcement
                             (CRO-fixed 2026-07-19);
                          k: 5 td (CRO-ratified 2026-07-19 — fixed, not re-tunable post-hoc, X1);
                          aggregation: cross-event mean, CLUSTER-ROBUST (CR1) by review date —
                             the single pre-committed inference method, not a post-hoc choice
                             among {pooled-iid, cluster-robust} [readiness-review C-2];
                          alpha: 0.05;
                          MDE_stat (PRIMARY, gross, statistical detection floor):
                             fixed ex ante at the CONSERVATIVE cluster-robust bound —
                             ~4.97% raw / ~4.22% market-model-haircut (k=5d, N=210, K=13
                             clusters) — see [[HYP-PA-0001_POWER]] §4 for derivation. The pooled
                             iid-basis figure (~1.24%/1.05%) is reported as a SECONDARY
                             sensitivity check only, per PM-0001's lesson that a robustness
                             gradient is a consistency check, never a selection scan (R7.4);
                          net_of_cost: applied AFTER the statistical test, to the DELETE-only
                             subsample only (see alternative_hypothesis) — NOT part of MDE_stat;
                          robustness_leg: repeat the primary test on the SECONDARY_CROSSCHECKED-
                             only subsample (N=98) as a declared consistency check, not a
                             selection scan [readiness-review R-4];
                          confirmatory_harness: standalone script, pattern-matched to
                             EXP-PM-0001's manifest/seal/consistency-audit discipline — see
                             [[HYP-PA-0001_HARNESS_SPEC]] [readiness-review C-3]. `research/
                             gatekeeper` / family-adjusted DSR DEFERRED (CRO-ratified
                             disposition 2026-07-19), consistent with EXP-PM-0001's precedent of
                             a single confirmatory in-sample test bypassing the gatekeeper
                             pipeline }

required_data:           [ ohlcv                          # Available Today, 5 yr
                          reconstitution_event_calendar ]  # WP-D DELIVERED 2026-07-17 (210
                                                             # events, 13 clusters, window
                                                             # 2022-08-01 → 2026-05-04)

mechanism_blind_to:      all IDX reconstitution outcomes   # theory-first (Shleifer 1986), §7.3

expected_evidence_product:
                        Terminal tier C2 (EV-9, N=1, single-researcher ceiling — the same wall
                        as every hypothesis in this institution, [[HYPOTHESIS_LIFECYCLE]] §4.2).
                        Outcome is either a C2 provisional reconstitution-reversal edge (DELETE-
                        side, net-of-cost positive) or a competent refutation; both first-class
                        (R12, PG-11). [readiness-review R-5]

declared_limitations:   DATA PROVENANCE — 112/210 events (53%) are SECONDARY_SINGLE-sourced; one
                           source misattribution was already caught and corrected during WP-D
                           assembly ([[COVERAGE_REPORT]] §5). Mitigated, not eliminated, by the
                           crosschecked-only robustness leg above.
                        COVERAGE GAP — 2021-H2 and 2022-H1 unsourced; registration is scoped to
                           the realized 2022-08→2026-05 window only.
                        CLUSTER FRAGILITY — the review-date-common component means the
                           conservative MDE_stat (~5.0%) may exceed plausible literature effect
                           sizes (~1.5–2% gross); the test may be honestly underpowered for a
                           real, modest effect. This is a stated risk, not a resolved one — it is
                           a declared limitation the Owner accepted when lifting the HOLD to GO
                           (2026-07-19; [[HYP-PA-0001_POWER]] §4a).
                        EXECUTION ASYMMETRY — the net/capturable claim covers DELETE-side only
                           (A-PA5); ADD-side reversal is a gross/mechanism-only reading.
                        DECAY — the mechanism is expected to weaken as passive AUM and arbitrage
                           capacity grow (P7); no regime split is pre-registered given the single
                           ~3.75yr window (F9 risk noted, not tested).
                        [readiness-review R-5]
```
<!--FROZEN-END-->

## Registration receipt (HL-1)

> One transition, one receipt. This receipt binds the transition; the SHA-256 seals the frozen object above.

| Field | Value |
|---|---|
| **Hypothesis ID** | HYP-PA-0001 |
| **Transition** | `DRAFT → REGISTERED` (T4 / G1) |
| **Registered at** | 2026-07-19T00:19:47Z |
| **Registered by** | Human Owner — explicit authorization for irreversible T4 registration (this task, 2026-07-19); CRO ex-ante criteria ratified 2026-07-19; Owner HOLD lifted to GO 2026-07-19 (register on realized N=210/K=13) |
| **G1 gate** | Satisfied — six §5.2 elements + guards present (mechanism M6, directional prediction, null, scope, family, blind_to); ex-ante criterion incl. effect size CRO-ratified (R5); power/MDE shows the test can fail, marginal-power risk accepted by Owner (R2); refutation condition in one sentence (R14); required_data Available Today (D-002) |
| **preregistration_sha256** | `3692e69a8e1cbf6d0a978c5e9c0dc7d34bfb1f95d81807abc1d18a6e8e31b825` (SHA-256 of the bytes between the FROZEN markers, trailing newline stripped — same convention as HYP-PM-0001_REGISTERED.md) |
| **Immutability** | This record is immutable. A revision is a **new** hypothesis (supersession, T12/HL), never an edit (R15, HL-2). Sealed additionally by git commit. |
| **Family effect** | HYP-PA-0001 is now the **first member of the P-A family {I2,I3,I8}**; the family is append-only from this point (PG-3). |
| **Next** | Experiment execution (S4–S8) under custody, per [[HYP-PA-0001_HARNESS_SPEC]] — **not performed here**; OOS partition released once at run time (CU-5). |

## Lineage

Free-era draft: [[HYP-PA-0001_DRAFT]] (retained as history) · Power analysis: [[HYP-PA-0001_POWER]] · Confirmatory harness spec: [[HYP-PA-0001_HARNESS_SPEC]] · Family decision: [[DECISION_LOG]] D-028 · Program: [[RESEARCH_PROGRAM]] · Objectives: [[OBJECTIVES_2026H2]] O1 · Mechanism: [[ECONOMIC_MECHANISM_TAXONOMY]] · Data: [[DATA_FEASIBILITY_STUDY]] §3–§4 · Tier: [[EVIDENCE_MODEL]] EV-9 · Registry: [[HYPOTHESIS_REGISTRY]].
