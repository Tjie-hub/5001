# HYP-PA-0001 — Index-Reconstitution Closing-Auction Dislocation (DRAFT)

> **Status: DRAFT — all G1 criteria ratified & recorded (2026-07-19); cleared for T4, NOT yet registered. No family slot consumed.**
> This is a free-era candidate ([[HYPOTHESIS_LIFECYCLE]] §2–§3): refinement is unlimited and nothing has been risked. It becomes a risked claim only at the irreversible `DRAFT → REGISTERED` transition (T4/G1), which is now deferred solely to explicit human authorization of that transition (§5 step 4); all G1 admissibility criteria are ratified and recorded.
>
> **Update 2026-07-17:** WP-D delivered (210 events, 13 clusters, [[COVERAGE_REPORT]]) and the power analysis is complete ([[HYP-PA-0001_POWER]]) — **MDE ≈ 1.3%/event at k=5d, pooled; fragile to review-date clustering.** The two §4 held items (R5 effect-size, R2 power) are now **computed**; registration awaits **CRO ex-ante ratification of k/MDE** and a register-now-vs-close-gaps decision. Family slot still unconsumed. *(Historical — superseded by the 2026-07-19 ratification update below.)*
>
> **Update 2026-07-18 (readiness-review resolution pass):** an independent Pre-Registration Readiness Review checked HYP-PA-0001 against the institutional lessons from HYP-PM-0001's completed lifecycle (FAILED, F2) and found 4 Critical + 5 Recommended deficiencies — chiefly, an unresolved gross-vs-net MDE ambiguity, an undetermined power basis (pooled vs. cluster), no confirmatory harness spec, and an unexamined ADD-side short-execution constraint. **All 9 are now resolved by specification** (this pass; free era, unlimited revision, no data collected, nothing registered, no code written). See the change log in the readiness-review report for the file-by-file mapping. **Still DRAFT. Still NOT registered.** What remains is (a) CRO ratification of the now-unambiguous-but-honestly-marginal criteria, and (b) the pre-existing owner HOLD on register-now-vs-close-two-more-clusters — both human/data decisions this pass does not and cannot resolve. *(Historical — both resolved by the 2026-07-19 ratification update below.)*
>
> **Update 2026-07-19 (governance ratification recorded):** the CRO ratified the ex-ante criteria exactly as recommended in [[HYP-PA-0001_POWER]] §4 (k=5 td; MDE_stat ~4.97% raw / ~4.22% haircut, cluster-robust CR1 by review date as the **sole** inference basis; Test 2 net-of-cost DELETE-only N=105; robustness leg N=98), **fixed the market-model estimation window at 230 trading days ending ~20 td before announcement**, and **ratified DEFERRAL** of the family-adjusted DSR (single confirmatory in-sample test, EXP-PM-0001 precedent). The Owner **lifted the HOLD to GO**, electing to register on the realized N=210 / K=13 (2022-08→2026-05) window with the 2021-H2 / 2022-H1 gaps carried as declared limitations. **All six §5.2 elements and every G1 guard are now satisfied and recorded. Still DRAFT — the irreversible T4 transition is deferred to explicit human authorization; nothing is registered and no family slot is consumed by this pass.** The 2026-07-17/18 update lines above are retained as history.

**Program:** P-A · Auction Dislocation · **Family:** P-A {I2, I3, I8} ([[DECISION_LOG]] D-028) — this would be the **first member**
**Mechanism (I8 → I2):** index-reconstitution forced flow → closing-auction price displacement
**Backlog rank:** #1 for P-A ([[OBJECTIVES_2026H2]] §3) · **Capability:** PROXY · **Date drafted:** 2026-07-17
**G1 decision path:** CRO ruled **Path A** (2026-07-17) — assemble the event calendar, power the test, *then* register.

---

## S1 · Literature Discovery → Literature Card

```
card_id:               LC-PA-0001
sources:               Shleifer (1986) "Do demand curves for stocks slope down?" J. Finance
                       Harris & Gurel (1986); Chen, Noronha & Singal (2004);
                       Greenwood (2005); Petajisto (2011) "The index premium and its costs"
identified_mechanisms: [ index_reconstitution_demand_shock ]
empirical_claims:      [ "Index additions earn abnormal returns around the effective date",
                         "Driven by price-inelastic index-fund demand, not information",
                         "Effect partially reverses after the rebalancing flow clears",
                         "Concentrated at the close, where funds trade to minimize tracking error" ]
limitations:           [ "US/developed samples; declining magnitude as passive AUM & arb evolve",
                         "Effect size regime- and liquidity-dependent" ]
```

## S2 · Mechanism Identification → Economic Mechanism

```
mechanism_id:      MECH-recon-dislocation
classification:    M6 — Market Design (index-methodology rule)
participant_class: passive/index-tracking funds (FORCED) vs. arbitrageurs/LPs (voluntary)
causal_graph:      [published index review adds/deletes a name at a fixed effective date]
                     → [passive funds MUST rebalance to the index at the effective close
                        to minimize tracking error]
                     → [large, price-inelastic, one-directional flow at the closing auction]
                     → [temporary displacement of the close from continuous-session value]
                     → [partial reversal once the mandated flow clears]
persistence_theory: The flow is a MANDATE, not a mispricing. No quantity of arbitrage capital
                    removes it — arbs shift its timing, but the mandated flow must still clear.
                    The barrier is the index-tracking obligation itself (M6 structural).
half_life_estimate: days (the reversal window) → suits DAILY data
decay_hypothesis:   step function on index-methodology rule change (monitor the RULEBOOK,
                    not a return series — EV-11); slow drift as passive AUM/arb capacity grows
```
*Passes the micro-economics gate: inelastic forced demand displacing price is first-principles sound. Barrier is M6 — the highest-durability class ([[RESEARCH_PROGRAM_PLAYBOOK]] PB-1).*

## S3 · Hypothesis Registration → Hypothesis Object (DRAFT, pre-G1)

```
hypothesis_id:         HYP-PA-0001
mechanism_ref:         MECH-recon-dislocation

prediction:            ADDED names: abnormal return UP into the effective-date close, then
                       REVERSING DOWN over t+1..t+k. DELETED names: the mirror.
                       => event-level SIGNED reversal return (signed against event direction) > 0.
                       This is a MECHANISM claim (gross, both directions) — distinct from the
                       CAPTURABILITY claim below (net-of-cost, direction-restricted).
                       [readiness-review C-1/C-4: split from a single conflated claim]

null_hypothesis:       H0: mean signed reversal (gross) over t+1..t+k = 0

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

scope:                 LQ45 / IDX30 / IDX80 reconstitution add & delete events; liquid universe;
                       daily frequency; effective dates per published IDX reviews.
                       REALIZED coverage (WP-D, [[COVERAGE_REPORT]]): **2022-08-01 → 2026-05-04**,
                       210 ticker-events (105 ADD / 105 DELETE; 192 distinct economic events),
                       13 review-date clusters. Two clusters (2021-H2, 2022-H1) remain unsourced;
                       the pre-2022-08 window is OUT OF SCOPE for this registration, not silently
                       included in it. [readiness-review R-3: draft previously overstated
                       coverage as "2021-07 → present"]

refutation_condition:  "If the mean signed post-effective reversal (gross) is not statistically
                        distinguishable from zero at the cluster-robust MDE_stat, OR is net-of-
                        cost negative on the DELETE-only capturable subsample, the mechanism is
                        refuted for IDX at this fidelity."   # one sentence, R14

multiplicity_family:   P_A_AUCTION_DISLOCATION {I2, I3, I8}   # first member; append-only (PG-3)

assumptions:           # readiness-review R-1: made explicit (PM-0001 lesson L4 — an
                       # attribution-defensible failure requires an enumerated assumption set)
                       A-PA1  announcement/effective dates as published in secondary media are
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
                              [readiness-review R-1: closes an undeclared event-count ambiguity]

validation_criteria:   { estimator: event-study CAR, market-model abnormal returns (vs IHSG);
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
                            disposition 2026-07-19), consistent with
                            EXP-PM-0001's precedent of a single confirmatory in-sample test
                            bypassing the gatekeeper pipeline }

required_data:         [ ohlcv                          # Available Today, 5 yr  ✅
                         reconstitution_event_calendar ]  # WP-D DELIVERED 2026-07-17 (210
                                                            # events, 13 clusters, window
                                                            # 2022-08-01 → 2026-05-04) — no
                                                            # longer "Obtainable Later"

mechanism_blind_to:    all IDX reconstitution outcomes   # theory-first (Shleifer 1986), §7.3 ✅
                       NOTE: WP-D's calendar assembly (event dates + membership only, no
                       returns) preserves blindness (§5 custody discipline below); this
                       readiness-review resolution pass likewise touched no return/effect data
                       (descriptive counts only) — blindness intact.

expected_evidence_product:
                       Terminal tier C2 (EV-9, N=1, single-researcher ceiling — the same wall
                       as every hypothesis in this institution, [[HYPOTHESIS_LIFECYCLE]] §4.2).
                       Outcome is either a C2 provisional reconstitution-reversal edge (DELETE-
                       side, net-of-cost positive) or a competent refutation; both first-class
                       (R12, PG-11). [readiness-review R-5]

declared_limitations:  DATA PROVENANCE — 112/210 events (53%) are SECONDARY_SINGLE-sourced; one
                          source misattribution was already caught and corrected during WP-D
                          assembly ([[COVERAGE_REPORT]] §5). Mitigated, not eliminated, by the
                          crosschecked-only robustness leg above.
                       COVERAGE GAP — 2021-H2 and 2022-H1 unsourced; registration (if it
                          proceeds) is scoped to the realized 2022-08→2026-05 window only.
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

status:                DRAFT   # all G1 criteria ratified 2026-07-19; cleared for T4
                                # (deferred to explicit human authorization) — see §4
```

---

## 4. G1 admissibility assessment

The six §5.2 elements plus the G1 guards ([[HYPOTHESIS_LIFECYCLE]] §4.1). **Verdict: all six §5.2 elements + guards satisfied and recorded; the two formerly-held items (R5, R2) are ratified 2026-07-19. Cleared for T4 (transition deferred to explicit human authorization).**

| Requirement | Basis | Status |
|---|---|---|
| Mechanism: M-class + constraint + participant | R9 | ✅ M6 · forced mandate · passive vs. arb |
| Directional prediction (sign-specified) | §5.2 | ✅ add→down-reversal; delete→mirror |
| Null | §5.2 | ✅ signed reversal = 0 |
| Scope | §5.2 | ✅ LQ45/IDX30/IDX80 recon events, liquid, daily |
| Multiplicity family declared | R7.5 | ✅ P-A {I2,I3,I8}, first member |
| Mechanism `blind_to` OOS | §7.3, OS-6 | ✅ theory-first, pre-dates any IDX result |
| Refutation condition in one sentence | R14 | ✅ |
| **Ex-ante criterion incl. effect size** | **R5** | ✅ **CRO-RATIFIED 2026-07-19** — exactly as [[HYP-PA-0001_POWER]] §4 recommends: k=5 td; MDE_stat = cluster-robust conservative bound (~4.97% raw / ~4.22% haircut, single pre-committed basis); Test 2 net-of-cost DELETE-only (N=105); robustness N=98. Estimation window fixed at 230 td; family-adjusted DSR deferral ratified. Frozen-ready; **not yet registered** (T4 deferred to authorization). |
| **Power / MDE: the test can fail** | **R2** | ✅ **Falsifiable; marginal power accepted by the Owner.** MDE_stat is finite and fixed ex ante, so the test can fail (R2 satisfied as *falsifiability*). The conservative MDE_stat may exceed plausible literature effect sizes ([[HYP-PA-0001_POWER]] §4); the Owner **lifted the HOLD to GO on 2026-07-19**, registering on the realized N=210 / K=13 window with the marginal-power risk and the 2021-H2/2022-H1 gaps accepted as **declared limitations** ([[HYP-PA-0001_POWER]] §4a). |
| required_data Available/Obtainable | D-002 | ✅ **Available Today** — WP-D delivered 210 events / 13 clusters (2026-07-17); calendar assembled, blind, custody-clean. |

**Registration status — updated 2026-07-19.** Both formerly-held items are now resolved as ratified decisions. **(a)** The CRO ratified the ex-ante criteria (R5) exactly as [[HYP-PA-0001_POWER]] §4 recommends, fixed the market-model estimation window at 230 td, and ratified deferral of the family-adjusted DSR. **(b)** The Owner lifted the HOLD ([[HYP-PA-0001_POWER]] §4a), electing to register on the realized N=210 / K=13 (2022-08→2026-05) window with the review-date-clustering power risk and the two residual gaps (2021-H2, 2022-H1) accepted as declared limitations rather than closed first. No post-hoc discretion remains over any criterion. **The only step left is the irreversible T4 transition itself, deferred to explicit human authorization** (§5 step 4); nothing in this pass registers the hypothesis or consumes the family slot. The 2026-07-18 assessment above is retained as history.

---

## 5. WP-D · Data-assembly work package (the path to G1)

> A Work Package is an organizational convenience with **no scientific standing** — it does not bound the family ([[RESEARCH_PROGRAM_STANDARD]] §4, PG-8). It is recorded here because it is the single precondition to registering HYP-PA-0001.

**Deliverable — `reconstitution_event_calendar`:**

| Field | Content |
|---|---|
| Source | Published IDX index-review announcements (LQ45 / IDX30 / IDX80), effective dates |
| Coverage | **Target:** 2021-07 → present (the 5-yr `ohlcv` window). **REALIZED (delivered 2026-07-17):** 2022-08-01 → 2026-05-04, 210 events, 13 clusters — 2021-H2 and 2022-H1 remain unsourced ([[COVERAGE_REPORT]] §5). Registration, if it proceeds, is scoped to the realized window only (readiness-review R-3) |
| Rows | one per (index, ticker, event) with `event_type ∈ {ADD, DELETE}`, `announcement_date`, `effective_date` |
| Cross-check | reconcile the terminal state against `idx_tickers` current flags (consistency, not sufficiency) |
| Capability class | **Obtainable Later** ([[DATA_FEASIBILITY_STUDY]] §4.2) — bounded assembly, no vendor upgrade required |

**Custody / blinding discipline (so the later test is admissible):**
- The calendar is assembled from **event dates and membership only** — it must not be conditioned on post-effective returns (no peeking at the outcome when defining the sample), preserving the mechanism's `blind_to` status.
- Market-model parameters and the per-event return σ are estimated on a pre-event estimation window (in-sample); the reversal window is the tested quantity, released under custody once (CU-5 ordinal = 1) when the experiment runs.

**Power / MDE discharge (closes the two held rows):**
```
On assembly, measure:  N_events (realized), σ_event (per-event reversal CAR sd, in-sample)
Then fix ex-ante:      MDE = (z_{1-α/2} + z_{power}) · σ_event / sqrt(N_events),  power = 0.80
Register only if:      the MDE at N_events is <= a plausible economic reversal magnitude
                       (else the sample is underpowered — R2 fails — and the honest
                        outcome is to defer, widen scope, or refuse, NOT to weaken the bar)
```

**Order of operations (family slot consumed only at step 4):**
1. Execute WP-D → assemble the calendar.
2. Count events, measure σ → compute the powered MDE.
3. Fix the ex-ante `validation_criteria` (k, MDE_stat, estimation window; family-adjusted DSR **deferred**); **CRO approval — GRANTED 2026-07-19**.
4. `DRAFT → REGISTERED` (T4/G1) — **the irreversible step; HYP-PA-0001 joins the family permanently.**
5. Run the event-study experiment on 5-yr `ohlcv` (S4–S8), through `research/gatekeeper`.

---

## 6. Traceability

| This artifact | Cites (SSOT) |
|---|---|
| Object form (S1–S3) | [[WORKED_EXAMPLE_END_TO_END]] |
| G1 gate (§4) | [[HYPOTHESIS_LIFECYCLE]] §4.1, R2, R5, R14, §7.3 · [[RESEARCH_PROTOCOL]] §5.2 |
| Family membership | [[DECISION_LOG]] D-028 · [[RESEARCH_PROGRAM]] §2 |
| Mechanism barrier (M6) | [[RESEARCH_PROGRAM_PLAYBOOK]] PB-1 · [[ECONOMIC_MECHANISM_TAXONOMY]] |
| Data capability | [[DATA_FEASIBILITY_STUDY]] §3–§4 |
| WP-D (no family binding) | [[RESEARCH_PROGRAM_STANDARD]] §4 (PG-8) |
| Confirmatory harness spec (pre-registration, no code) | [[HYP-PA-0001_HARNESS_SPEC]] — closes readiness-review C-3 |
| Readiness review lessons applied | HYP-PM-0001 sealed record (`7049d9e`): [[FAILURE_ENTRY]] · [[EVIDENCE_PACKAGE]] · post-mortem (2026-07-18, in-conversation, not yet a governance doc) |

**Parent:** [[RESEARCH_PROGRAM]] · [[OBJECTIVES_2026H2]] (O1). **Registers into:** P-A family {I2,I3,I8} at step 4 above — not before.
