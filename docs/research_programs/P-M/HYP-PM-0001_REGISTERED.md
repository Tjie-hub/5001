# HYP-PM-0001 — REGISTERED (frozen, immutable)

> **This is the frozen registration record.** Per owner decision (2026-07-17), HYP-PM-0001 passed **G1** and underwent the irreversible **DRAFT → REGISTERED** transition ([[HYPOTHESIS_LIFECYCLE]] T4/G1, HL-2). The claim is now **risked** and has **joined the P-M family {I5,I6,I7,I12} permanently** (PG-3, OS-10). The bytes between the FROZEN markers are sealed by the SHA-256 in the receipt (§Receipt); **any change is a new hypothesis (supersession T12), never an edit** (R15).

<!--FROZEN-START-->
```
hypothesis_id:          HYP-PM-0001
status:                 REGISTERED
program:                P-M · Microstructure Flow
family:                 P-M {I5, I6, I7, I12}   # DECISION_LOG D-028 — append-only; joined permanently (PG-3)
preregistered_at:       2026-07-17T07:15:03Z

mechanism_ref:          M1.1 · Inventory-imbalance mean reversion (I5, M1/D2)
tested_against:         M2.1 · Adverse-selection permanence (I7, M2/D2)   # the D2 confound
structural_barrier:     Inventory risk-bearing (M1). A one-sided order-flow imbalance must be
                        warehoused by liquidity suppliers, who demand compensation for the price
                        risk of the resulting inventory; the compensation persists because the
                        imbalance must be borne by someone — no arbitrage capital abolishes the
                        risk, it can only price it.
participant_class:      liquidity suppliers (forced to warehouse imbalance) vs. aggressors

prediction:             Price displacement conditional on signed order-flow imbalance (OFI) in a
                        1-minute bar PARTIALLY REVERTS over the following k minutes.
                        Positive OFI -> positive contemporaneous return -> subsequent NEGATIVE
                        (reversing) return.  ==> signed reversal > 0.
ofi_interval:           1 minute
reversal_window_k:      15 minutes (PRIMARY, confirmatory)
robustness_gradient:    k in {5, 15, 30} min declared as a CONSISTENCY check (all must agree),
                        NOT a selection scan — a k chosen to make a survivor clear is R15/R7.5.

null_hypothesis:        H0: mean signed reversal over k = 0
alternative:            H1: mean signed reversal, NET OF COST, > 0

ex_ante_MDE:            FRICTION-ANCHORED (owner decision) — not statistical detectability.
                        The reversal must exceed round-trip friction to qualify as an edge:
                        net-of-cost signed reversal > 0, where cost = the single cost authority
                        engine/exits/costs.py (COMMISSION_BUY 0.15% + SLIPPAGE 0.10% on the buy
                        leg; COMMISSION_SELL 0.25% + SLIPPAGE 0.10% on the sell leg) =
                        ROUND-TRIP ~= 0.60%.  MDE (gross reversal that must be cleared) = 0.60%.
                        [Statistical power is abundant: sub-bp MDE over 12.7M bars — HYP-PM-0001_POWER.]
alpha:                  0.05 ; multiplicity = family-adjusted DSR (P-M scan distn) ; PBO via CSCV

required_data:          stockbit_flow_bars (1-min signed lot/freq/delta + price, PROXY) ;
                        ohlcv (returns, Amihud illiquidity) ;
                        broker_flow (foreign/local/govt — informed-flow proxy for the I7 split)
variables:              OFI_t (signed net imbalance, normalized) ; r_t (contemporaneous return) ;
                        rev_{t+1..t+k} (forward reversal) ; illiq (Amihud bucket, I6) ;
                        informed_t (foreign/smart-money proxy, I7 split)

assumptions:            A-PM1 signed-flow proxy correctly signs aggressor direction
                        A-PM2 the 1-min/k horizon spans inventory build-and-offload
                        A-PM3 "informed" classification is point-in-time, not outcome-labelled (F7 guard)
                        A-PM4 the reversal is measured net of the round-trip friction above (F4 guard)
                        A-PM5 PROXY flow is representative of total imbalance, not only retail

d2_separation_strategy: reversion-vs-permanence + informed-flow conditioning (MIT §5.3 G1 req).
                        At PROXY fidelity this is causal ARGUMENT, not identification (LIM2).

falsification:          Displacement conditional on OFI does NOT revert net of cost
                        (signed reversal <= 0 or < MDE) ==> M1.1 REFUTED
                        (-> permanence/M2.1, or F4 friction, or F1 bid-ask-bounce/fair-price).
one_sentence_refutation:
                        "If price displacement conditional on signed order-flow imbalance does not
                        partially revert net of round-trip friction (0.60%) within 15 minutes, the
                        inventory mean-reversion mechanism (M1.1) is refuted for IDX proxy flow."

statistical_methodology:
                        Panel regression of rev_{t+1..t+k} on OFI_t with illiq and informed
                        interactions, DOUBLE-CLUSTERED SE (ticker x time), Newey-West for serial
                        correlation ; decile portfolio sort on OFI_t -> forward-reversal spread,
                        net of the versioned cost model ; bid-ask-bounce control (F1 guard) ;
                        family-adjusted DSR + PBO/CSCV ; I5/I7 discriminator = sign/decay split
                        by informed_t.

expected_evidence_product:
                        Terminal tier C2 (EV-9, N=1). Outcome is either a C2 provisional
                        inventory-reversal edge (reversion confirmed; informed split consistent
                        with I5) OR a competent refutation (permanence => I7/M2.1 dominates ; F4
                        friction kill ; F1 fair-price). Both map a boundary on the D2
                        identification problem and are first-class products (R12, PG-11).
                        No capital at C2 — shadow only.

declared_limitations:   LIM2 — PROXY fidelity (no LOB): I5/I7 separation is argument, not
                        identification; caps confidence.
                        HISTORY-MATURITY GATE (DFS §5.3) — flow proxy is ~1 yr, one regime;
                        regime-stratified & walk-forward validation DEFERRED; the confirmatory
                        test is IN-SAMPLE until the flow history lengthens.
                        C2 CEILING (EV-9) — single-researcher; Accepted Knowledge structurally
                        unavailable (G-4).

mechanism_blind_to:     all IDX flow outcomes — theory-first (Ho & Stoll inventory;
                        Glosten-Milgrom; Amihud-Mendelson). Pre-dates any IDX result (§7.3, OS-6).
```
<!--FROZEN-END-->

## Registration receipt (HL-1)

> One transition, one receipt. This receipt binds the transition; the SHA-256 seals the frozen object above.

| Field | Value |
|---|---|
| **Hypothesis ID** | HYP-PM-0001 |
| **Transition** | `DRAFT → REGISTERED` (T4 / G1) |
| **Registered at** | 2026-07-17T07:15:03Z |
| **Registered by** | CRO / owner approval (this task, 2026-07-17) — "APPROVED FOR REGISTRATION; G1 satisfied; MDE friction-anchored" |
| **G1 gate** | Satisfied — six §5.2 elements + guards present; D2 separation strategy stated; mechanism blind; MDE fixed ex ante (friction); refutation in one sentence |
| **preregistration_sha256** | `540c2d52dd8751dbda2a6b39ea7935860e12078c666a81e2156ff199ee885199` (SHA-256 of the bytes between the FROZEN markers) |
| **Immutability** | This record is immutable. A revision is a **new** hypothesis (supersession, T12/HL), never an edit (R15, HL-2). Sealed additionally by git commit + push. |
| **Family effect** | HYP-PM-0001 is now the **first member of the P-M family {I5,I6,I7,I12}**; the family is append-only from this point (PG-3). |
| **Next** | Experiment execution (S4–S8 via `research/gatekeeper`) — **not performed here**; the OOS/in-sample partition is released under custody once at run time (CU-5). |

## Lineage

Free-era draft: [[HYP-PM-0001_DRAFT]] (retained as history) · Power analysis: [[HYP-PM-0001_POWER]] · Family decision: [[DECISION_LOG]] D-028 · Program: [[RESEARCH_PROGRAM]] · Objectives: [[OBJECTIVES_2026H2]] O1 · Mechanism: [[ECONOMIC_MECHANISM_TAXONOMY]] §2/§3 · Identification: [[MARKET_INEFFICIENCY_TAXONOMY]] §4–§5 · Data: [[DATA_FEASIBILITY_STUDY]] §4.1/§5.3 · Tier: [[EVIDENCE_MODEL]] EV-9 · Registry: [[HYPOTHESIS_REGISTRY]].
