# HYP-PM-0003 — REGISTERED (frozen, immutable)

> **This is the frozen registration record.** Per owner/CRO authorization (2026-09-09), HYP-PM-0003 passed **G1** and underwent the irreversible **DRAFT → REGISTERED** transition ([[HYPOTHESIS_LIFECYCLE]] T4/G1, HL-2). The claim is now **risked** and has **joined the P-M family {I5,I6,I7,I12} permanently** (PG-3, OS-10), as its **third** independently-counted member. The bytes between the FROZEN markers are sealed by the SHA-256 in the receipt (§Registration receipt); **any change is a new hypothesis (supersession T12), never an edit** (R15).

<!--FROZEN-START-->
```
hypothesis_id:          HYP-PM-0003
status:                 REGISTERED
program:                P-M · Microstructure Flow
family:                 P-M {I5, I6, I7, I12}   # DECISION_LOG D-028 — append-only; joined permanently (PG-3).
                        Second independently-counted REGISTERED member (Option B, OS-10 —
                        CRO-adopted 2026-09-09, HYP-PM-0003_DRAFT.md §14 / HYP-PM-0003_POWER.md §9).
                        HYP-PM-0002 remains DRAFT/unregistered and consumes no family slot as of this
                        registration; HYP-PM-0003's numbering reflects draft-authorship order, not
                        registration order.
preregistered_at:       2026-09-09T09:22:00Z

mechanism_ref:          M2.1 · Adverse-selection spread component (I7, M2/D2)
                        "A supplier who cannot distinguish informed from uninformed counterparties
                        embeds an expected-loss premium in every quote, so that transaction prices
                        move permanently in the direction of executed flow." (ECONOMIC_MECHANISM_TAXONOMY §3)
participant_class:      liquidity suppliers (uninformed by role) vs. informed traders; no further
                        sub-classification attempted in the primary specification
constraint:             the supplier cannot distinguish informed from uninformed flow (D2)
structural_barrier:     information asymmetry itself — cannot be arbitraged away (removing it would
                        require the supplier to know what the informed trader knows, at which point
                        there is no asymmetry and no premium)

data_instrument:        broker_flow — Dataset A, DS-broker_flow-idx80-nonpit-2025_2026v1, FROZEN
                        (DECISION_LOG D-043). NOT stockbit_flow_bars (HYP-PM-0002's instrument for
                        the same I7 entry — see multiplicity_family below).
dataset_fingerprint:    329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558
                        (per-ticker aggregate over 79 tickers, 1,222,713 rows; scope declared per
                        CU-15 in HYP-PM-0003_DRAFT.md §5 / HYP-PM-0003_FINGERPRINTED_GATE — pins
                        ticker/count/date-range/signed-lot-sum/lot_value-sum; does NOT pin
                        broker_code/side granularity, freq, avg_price, investor_type, or row order)
dataset_population:     79-ticker IDX80 roster (SHA-256 7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0),
                        2025-01-02 -> 2026-08-27 inclusive, excluding 2026-08-25. NON-PIT — no
                        historical-index-composition claim is made.
signed_lot_convention:  net_flow(ticker,date) = SUM(lot) FROM broker_flow, treated as already-signed.
                        No additional BUY-minus-SELL subtraction on top of lot (would double-apply
                        the sign convention).

prediction:             Price displacement conditional on signed daily net broker-flow imbalance on
                        formation day t DOES NOT REVERT over the following k trading days. Positive
                        net flow -> positive contemporaneous/near-term return -> subsequent return
                        CONTINUES in the same direction (does not reverse sign). Signed continuation
                        (per unit_of_analysis below) is > 0.
formation_horizon_k:    7 trading days (PRIMARY), k in {3,7,15} reported as robustness — not a
                        selection scan; k=7 fixed ex ante, matching HYP-PM-0002's primary horizon
                        for cross-comparability.

null_hypothesis:        H0: net-of-cost signed continuation at k=7 <= 0 (full/partial reversion, or
                        no relationship)
alternative:            H1: net-of-cost signed continuation at k=7 > 0

unit_of_analysis:       one (ticker, formation-date) pair where net_flow(ticker,date) != 0 — a
                        cross-sectional daily panel observation. NOT a trade, NOT a broker-day, NOT
                        Dataset A's raw (ticker,trade_date,broker_code,side) row grain, and NOT the
                        79x388=30,652-cell expected grid (the maximum possible, not the actual
                        sample). regime_config.yaml::cell.min_n=100 is NOT invoked as a Dataset-level
                        requirement — it is a trade-level, per-hypothesis/G1 floor unrelated to this
                        panel's unit.

required_data:          broker_flow (Dataset A, frozen, fingerprint above) ; ohlcv (formation-day and
                        post-formation returns; 5-year depth, DATA_FEASIBILITY_STUDY §3, not itself a
                        maturity concern)

statistical_test:       bootstrap_ci (research/statistics.py — the same mechanism cell_verdict,
                        the gatekeeper, and the NR7 study already use), n_boot/ci_level/seed from
                        regime_config.yaml's versioned config, on the pooled k=7 signed-continuation
                        sample. CRO-ADOPTED 2026-09-09 (Option A of the primary-test decision):
                        no new clustered-inference (ticker x time) code implemented before G1 —
                        research/statistics.py contains no such implementation anywhere in this
                        repository; clustered inference is recorded as a FUTURE ROBUSTNESS
                        EXTENSION, not a registration prerequisite.
dependence_treatment:   the HYP-PM-0001 deflation ladder (N, N/10, N/100) ADOPTED as a labeled
                        SENSITIVITY DIAGNOSTIC ONLY — explicitly NOT a formal dependence correction.
                        bootstrap_ci itself performs i.i.d. resampling and does not model either
                        dependence source identified (cross-sectional same-day clustering across the
                        79-ticker panel; serial overlap in the k=7 forward window for the same
                        ticker).

ex_ante_MDE:            FRICTION-ANCHORED (CRO-adopted 2026-09-09, Option A) — not statistically
                        derived. Net-of-cost signed continuation at k=7 must be > 0, i.e. gross
                        signed continuation must clear the round-trip friction floor, cost = the
                        single cost authority engine/exits/costs.py (COMMISSION_BUY 0.15% +
                        SLIPPAGE 0.10% on the buy leg; COMMISSION_SELL 0.25% + SLIPPAGE 0.10% on the
                        sell leg) = ROUND-TRIP ~= 0.60%. MDE (gross continuation that must be
                        cleared) = 0.60%.
                        [Statistically-derived MDE retained ONLY as a reported sensitivity range,
                        NOT the criterion: 0.168% at raw N=20,604 nonzero-net-flow (ticker,date)
                        observations (sigma=8.623%, k=7 forward-return, price-only, pooled 79
                        tickers), 0.533% at N/10, 1.684% at N/100 (HYP-PM-0001's own deflation
                        levels). Unlike HYP-PM-0001 (friction-bound at every deflation level
                        examined), this daily panel's naive statistical MDE crosses the 0.60%
                        friction floor between raw N and N/100 -- power may be a real, co-binding
                        constraint here, not purely friction. This tension is preserved, not
                        resolved by discarding either figure.]
alpha:                  0.05 (two-sided) ; power_target: 0.80 — CRO-adopted 2026-09-09 as
                        HYP-PM-0003's own ex-ante convention (precedent-supported by
                        HYP-PM-0001_POWER.md's sanity-check choice, NOT stated anywhere as a
                        corpus-wide mandate)

multiplicity_family:    P-M {I5, I6, I7, I12} (D-028). Second independently-counted REGISTERED
                        member upon this registration (after HYP-PM-0001, REGISTERED 2026-07-17,
                        FAILED F2; HYP-PM-0002 remains DRAFT/unregistered — consumes no slot until
                        its own separate G1 act, regardless of its lower draft number).
                        CRO-ADOPTED 2026-09-09: Option B, independent counting. Basis: OS-10
                        (RESEARCH_OBJECT_SCHEMA.md §4.5) — "every hypothesis registered under a
                        Program joins its family; no hypothesis leaves." A CRO interpretation of
                        this existing, general counting rule, NOT a new corpus rule. Pipeline
                        separation is explicitly NOT the governing multiplicity criterion —
                        RESEARCH_PROGRAM_PLAYBOOK.md §1.2's CONFOUNDS/SUBSUMES-UPSTREAM/MODIFIES
                        test is a taxonomy-entry/family-drawing mechanism evaluated once, before any
                        hypothesis exists (P-M's family already fixed, D-028); it is not re-applied
                        to compare hypothesis instances within an already-declared family.
                        PRESERVED CAVEAT (scientific/evidential, not a multiplicity blocker):
                        A-PM3.3's provenance investigation established stockbit_flow_bars
                        (HYP-PM-0002's instrument) and broker_flow (this hypothesis's instrument)
                        are genuinely separate Stockbit API products with no shared endpoint, fetch
                        function, or repository-side computation -- but both describe the same
                        underlying executed IDX trades, and repository evidence cannot establish or
                        rule out vendor-internal independence. Any future joint interpretation of
                        HYP-PM-0002's and this hypothesis's results as fully independent
                        confirmations/refutations of I7 should be read against this caveat.

history_maturity_gate:  DECISION_LOG D-046 (Q1=C, QUALIFIED COUNT): Dataset A's genuine,
                        vendor-backfilled span (2025-01-02 -> 2026-08-27) is ELIGIBLE to count toward
                        span-based maturity for regime-stratified and walk-forward validation. It
                        does NOT count toward maturity for forward-observation phenomena (decay
                        estimation) -- not claimed or attempted by this hypothesis.
                        DECISION_LOG D-047: no numeric N threshold exists in the canonical corpus or
                        is invented here; maturity determination is deferred to the appropriate
                        future Program-level process, not resolved by this registration.
                        THIS HYPOTHESIS IS THEREFORE IN-SAMPLE, SINGLE-PASS ONLY. No
                        regime-stratified claim and no walk-forward claim is made. Dataset A's
                        three-regime characterization (D-042: SIDEWAYS 61.6%/BEAR 26.5%/BULL 11.9%)
                        is cited as available evidence, not as a completed maturity ruling.

oos_partition:          NONE. No Out-of-Sample or Blind partition is defined or created by this
                        registration (CUSTODY_MODEL §5.3/§5.4 -- a first-class, separately custodied
                        asset, not created here). The full window, minus formation/horizon trimming,
                        is used IN-SAMPLE.

falsification:          Net-of-cost signed continuation of daily broker-flow-implied price
                        displacement at k=7 trading days is not significantly positive (bootstrap_ci
                        CI does not exclude zero net-of-cost, or the point estimate does not clear
                        the 0.60% round-trip friction floor) ==> M2.1's permanence prediction is
                        REFUTED for this data source and horizon.
one_sentence_refutation:
                        "If the net-of-cost signed continuation of daily broker-flow-implied price
                        displacement at k=7 trading days is not significantly positive net of the
                        0.60% round-trip friction floor, M2.1's permanence prediction is refuted for
                        this data source and horizon, and I5's reversion reading (already null on
                        stockbit_flow_bars at intraday horizon per HYP-PM-0001) gains no support from
                        this test either."

declared_limitations:   NON-PIT (Dataset A) -- no historical-index-composition claim supportable.
                        2026-08-25 gap, cause unresolved -- not repaired, not imputed.
                        lot=0 AND lot_value>0 semantics unresolved (3,700 BUY + 11,963 SELL rows in
                        Dataset A's exact scope) -- contribute 0 to SUM(lot) regardless.
                        Vendor corporate-action-adjustment convention unknown in general; immaterial
                        for THIS window only (zero split events for any Dataset A ticker in-window,
                        this session's F-3 finding) -- would need re-examination for any future
                        window/ticker extension.
                        regime_classification (D-042) is a lightweight descriptive characterization,
                        NOT a formal O15 Regime object -- index-level (IHSG), not per-ticker; carries
                        no evidence tier.
                        asset_class carries only a PROPOSED value (D-039), not formally ratified the
                        way dataset_id was (H-5).
                        History-maturity gate open (D-047, no N) -- validation scope is in-sample
                        only, per this registration's own history_maturity_gate field above.
                        Observation-level independence from HYP-PM-0002 unresolved (A-PM3.3) -- see
                        multiplicity_family caveat above.
                        investor_type-conditioned variant explicitly out of primary scope (deferred,
                        not tested).

mechanism_blind_to:     all Dataset A flow-vs-return outcomes. This draft/registration was prepared
                        without inspecting any return, reversal, or continuation outcome -- every
                        number in this specification comes from schema/coverage inspection, the
                        pre-existing frozen cost authority (engine/exits/costs.py), or Dataset A's
                        already-published governance receipts (D-032...D-047), never from computing
                        flow-vs-return statistics (HYP-PM-0003_DRAFT.md header; HYP-PM-0003_POWER.md
                        header).
```
<!--FROZEN-END-->

## Registration receipt (HL-1)

> One transition, one receipt. This receipt binds the transition; the SHA-256 seals the frozen object above.

| Field | Value |
|---|---|
| **Hypothesis ID** | HYP-PM-0003 |
| **Transition** | `DRAFT → REGISTERED` (T4 / G1) |
| **Registered at** | 2026-09-09T09:22:00Z |
| **Registered by** | CRO / owner approval (this task, 2026-09-09) — "Authorize the formal DRAFT → REGISTERED transition for HYP-PM-0003" |
| **G1 gate** | Satisfied — all six §5.2 elements present (mechanism, directional prediction, null, scope, effect_size_floor, multiplicity_family); mechanism `blind_to` stated; family declared (P-M {I5,I6,I7,I12}, D-028); power/MDE showing the test can fail (friction-anchored, 0.60%, plus statistical sensitivity range); refutation condition in one sentence; `required_data` (`broker_flow`/Dataset A, `ohlcv`) resolves to Available Today (`DATA_FEASIBILITY_STUDY` §4.1); CRO approval recorded above |
| **preregistration_sha256** | `a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5` (SHA-256 of the exact frozen specification block reproduced between the FROZEN markers above) |
| **Immutability** | This record is immutable. A revision is a **new** hypothesis (supersession, T12/HL), never an edit (R15, HL-2). |
| **Family effect** | HYP-PM-0003 is now the **second REGISTERED member of the P-M family {I5,I6,I7,I12}**, independently counted (Option B, OS-10, CRO-adopted 2026-09-09) — joins `HYP-PM-0001` (REGISTERED 2026-07-17, FAILED F2). `HYP-PM-0002` remains DRAFT, unregistered, and consumes no slot as of this registration, notwithstanding its lower draft number. |
| **Next** | Experiment execution (S4–S8 via `research/gatekeeper`, or a dedicated script per `EXP-PM-0001`'s precedent) — **not performed here**; no OOS/Blind partition is released (none exists, per `oos_partition: NONE` above — this hypothesis is in-sample only). |

## Lineage

Free-era draft: [[HYP-PM-0003_DRAFT]] (retained as history) · Power analysis: [[HYP-PM-0003_POWER]] · Multiplicity decision: this document's `multiplicity_family` field, CRO-adopted per OS-10 · Family decision: [[DECISION_LOG]] D-028 · History-maturity gates: [[DECISION_LOG]] D-046, D-047 · Dataset A: [[BROKER_FLOW_DATASET_A_EMPIRICAL_READY_HANDOFF_2026-09-09]], FROZEN [[DECISION_LOG]] D-043 · Program: [[RESEARCH_PROGRAM]] · Mechanism: [[ECONOMIC_MECHANISM_TAXONOMY]] §3 · Identification: [[MARKET_INEFFICIENCY_TAXONOMY]] §4–§5 · Data: [[DATA_FEASIBILITY_STUDY]] §4.1/§5.3 · Cost authority: `engine/exits/costs.py` · Statistical test: `research/statistics.py::bootstrap_ci` · Tier: [[EVIDENCE_MODEL]] · Registry: [[HYPOTHESIS_REGISTRY]].
