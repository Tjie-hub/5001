# HYP-PA-0001 — Index-Reconstitution Closing-Auction Dislocation (DRAFT)

> **Status: DRAFT — held at G1. NOT registered. No family slot consumed.**
> This is a free-era candidate ([[HYPOTHESIS_LIFECYCLE]] §2–§3): refinement is unlimited and nothing has been risked. It becomes a risked claim only at the irreversible `DRAFT → REGISTERED` transition (T4/G1), which is deferred pending the data work package in §5.

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
                       => event-level SIGNED reversal return (signed against event direction) > 0
null_hypothesis:       H0: mean signed reversal over t+1..t+k = 0
alternative_hypothesis: H1: mean signed reversal > MDE, net of cost
scope:                 LQ45 / IDX30 / IDX80 reconstitution add & delete events;
                       liquid universe; daily frequency; effective dates per published IDX reviews
refutation_condition:  "If the mean signed post-effective reversal is not > MDE net of cost,
                        the mechanism is refuted for IDX."   # one sentence, R14
multiplicity_family:   P_A_AUCTION_DISLOCATION {I2, I3, I8}   # first member; append-only (PG-3)
validation_criteria:   { estimator: event-study CAR, market-model abnormal returns;
                         run_up_window: [announcement .. effective]; reversal_window: [t+1 .. t+k];
                         k: 5 td (candidate — CRO fixes at registration);
                         aggregation: cross-event mean, cluster-robust by review date;
                         alpha: 0.05; net_of_cost: true;
                         DSR_min: family-adjusted via research/gatekeeper;
                         MDE: **TBD — fixed from realized event count at >=80% power (see §5)** }
required_data:         [ ohlcv               # Available Today, 5 yr  ✅
                         reconstitution_event_calendar ]   # Obtainable Later — NOT yet assembled
mechanism_blind_to:    all IDX reconstitution outcomes   # theory-first (Shleifer 1986), §7.3 ✅
status:                DRAFT   # held at G1 — see §4
```

---

## 4. G1 admissibility assessment

The six §5.2 elements plus the G1 guards ([[HYPOTHESIS_LIFECYCLE]] §4.1). **Verdict: 4/6 core + guards satisfied; 2 items held, and they resolve together.**

| Requirement | Basis | Status |
|---|---|---|
| Mechanism: M-class + constraint + participant | R9 | ✅ M6 · forced mandate · passive vs. arb |
| Directional prediction (sign-specified) | §5.2 | ✅ add→down-reversal; delete→mirror |
| Null | §5.2 | ✅ signed reversal = 0 |
| Scope | §5.2 | ✅ LQ45/IDX30/IDX80 recon events, liquid, daily |
| Multiplicity family declared | R7.5 | ✅ P-A {I2,I3,I8}, first member |
| Mechanism `blind_to` OOS | §7.3, OS-6 | ✅ theory-first, pre-dates any IDX result |
| Refutation condition in one sentence | R14 | ✅ |
| **Ex-ante criterion incl. effect size** | **R5** | ⚠️ **HELD** — MDE undetermined until event count known |
| **Power / MDE: the test can fail** | **R2** | ⚠️ **HELD** — same dependency |
| required_data Available/Obtainable | D-002 | ⚠️ Obtainable Later — calendar not yet assembled |

**Why not register now.** Freezing an *unpowered* claim with a guessed MDE into a permanent, un-revisable family slot is the exact R2/R5 failure the gate exists to prevent (refusal is free; a family slot is forever — [[RESEARCH_PROGRAM_PLAYBOOK]] §2.1). The three flagged rows collapse to one root cause: **the reconstitution event history does not exist in the repository.** Per [[DATA_FEASIBILITY_STUDY]] §3, `idx_tickers` holds **current membership flags only — no history of changes**.

---

## 5. WP-D · Data-assembly work package (the path to G1)

> A Work Package is an organizational convenience with **no scientific standing** — it does not bound the family ([[RESEARCH_PROGRAM_STANDARD]] §4, PG-8). It is recorded here because it is the single precondition to registering HYP-PA-0001.

**Deliverable — `reconstitution_event_calendar`:**

| Field | Content |
|---|---|
| Source | Published IDX index-review announcements (LQ45 / IDX30 / IDX80), effective dates |
| Coverage | 2021-07 → present (the 5-yr `ohlcv` window) |
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
3. Fix the ex-ante `validation_criteria` (k, MDE, DSR bar); **CRO approval**.
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

**Parent:** [[RESEARCH_PROGRAM]] · [[OBJECTIVES_2026H2]] (O1). **Registers into:** P-A family {I2,I3,I8} at step 4 above — not before.
