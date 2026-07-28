# HYP-PM-0001 — Order-Flow-Imbalance Inventory Reversal (DRAFT)

> **⛔ TRANSITIONED — this free-era draft was registered on 2026-07-17T07:15:03Z.**
> The frozen, immutable record is **[[HYP-PM-0001_REGISTERED]]** (sha256 `540c2d52…`), which governs. HYP-PM-0001 is now REGISTERED and is the first member of the P-M family {I5,I6,I7,I12} (PG-3). This draft is **retained as free-era history only** ([[HYPOTHESIS_LIFECYCLE]] §2) — it is not the record of truth and must not be edited to change the claim (R15).
>
> **Original draft status (historical): DRAFT — held at G1. NOT registered. No family slot consumed.**
> Free-era candidate ([[HYPOTHESIS_LIFECYCLE]] §2–§3): refine freely; nothing risked until the irreversible `DRAFT → REGISTERED` (T4/G1). Registration is blocked only on fixing the ex-ante MDE from a power calc (deferred by instruction) and CRO sign-off — see §5.
>
> **Update 2026-07-17:** power analysis complete ([[HYP-PM-0001_POWER]]) — **statistical power is abundant (sub-bp MDE over 12.7M bars); the binding constraint is friction (F4), not detectability.** The ex-ante MDE should therefore be **friction-anchored**, not statistical. B-1 closed as a computation; registration awaits **CRO ratification of a friction-based MDE + k** (R5). Family slot still unconsumed.

**Program:** P-M · Microstructure Flow · **Family:** P-M {I5, I6, I7, I12} ([[DECISION_LOG]] D-028) — this would be the **first member**
**Mechanism (I5 = M1.1):** order-flow imbalance → inventory-risk price pressure → **reversion**
**Backlog rank:** #2 for P-M ([[OBJECTIVES_2026H2]] §3) · **Capability:** PROXY · **Date drafted:** 2026-07-17

---

## 1. Mechanism

**Class: M1.1 · Inventory-imbalance mean reversion** ([[ECONOMIC_MECHANISM_TAXONOMY]] §2). A one-sided order-flow imbalance forces liquidity suppliers to absorb inventory; they demand compensation for the price risk of holding it, displacing the price temporarily; the displacement **reverts** as the inventory is worked off. Reversion is M1's signature and its discriminating prediction against M2.

- **Participant class:** liquidity suppliers / market-makers (forced to warehouse imbalance) vs. liquidity-demanding aggressors.
- **Constraint:** inventory risk under finite risk-bearing capacity.

## 2. Inefficiency family & the identification problem

- **Primary entry: I5 · Inventory-imbalance liquidity premium** (M1/D2, [[MARKET_INEFFICIENCY_TAXONOMY]] I5).
- **The confound that defines this family: I5 ↔ I7.** Inventory (I5, M1.1) and adverse selection (I7, M2.1) produce the **same observable** — price moves with flow — and differ **only** in what happens next: **reversion (I5) vs permanence (I7)**. Per MIT §4 this is *the central identification problem of D2*, and *"every D2 claim must state its separation strategy or be refused at G1."* This hypothesis's separation strategy is §4.
- **I6 (illiquidity) and I12 (capacity shielding)** enter as modifiers of the reversal magnitude (§3). The wide P-M family (D-028) exists precisely so these dependent tests share one denominator.

## 3. Structural barrier & prediction

**Barrier (persistence):** inventory risk-bearing. The compensation persists because a one-sided imbalance must be warehoused by *someone*, and bearing it is costly — the barrier is the risk itself, which no arbitrage capital abolishes (it can only price it). **Honest weakness (vs M6):** this is a *risk-compensation* barrier, one category-step from **F1** — reversion that is merely the mechanical bid-ask mid-bounce, or fair compensation for real risk, is a *price, not an inefficiency*. Surviving F1 is the first hurdle (§9).

**Prediction (sign-specified):** price displacement conditional on signed order-flow imbalance in interval *t* **partially reverts** over the following *k* intervals. Positive imbalance → positive contemporaneous return → subsequent **negative** (reversing) return. The signed reversal is **> 0**.

### 3.1 Observable implications
1. Contemporaneous positive relation between signed imbalance and return.
2. Subsequent **partial reversal** of the imbalance-induced component (the M1.1 signature).
3. Reversal **increasing in illiquidity** (I6 interaction — thinner depth ⇒ larger inventory pressure).
4. Reversal **attenuated when the imbalance is information-driven** (I7 test): flow proxied as informed (foreign / smart-money) should show *permanence*, not reversion. Implications 2-vs-4 are the I5/I7 discriminator.

## 4. Assumptions

| # | Assumption | Risk if false |
|---|---|---|
| A-PM1 | The signed-flow proxy (`stockbit_flow_bars` lot/freq/delta) correctly signs aggressor direction | mis-signed flow → mechanism untestable (measures noise) |
| A-PM2 | The 1-minute horizon spans inventory build-and-offload | wrong horizon → reversal missed or aliased |
| A-PM3 | Classification of "informed" flow (broker_flow foreign/smart-money) is point-in-time, not outcome-labelled | **F7 look-ahead** — the I7 split becomes circular ([[ECONOMIC_MECHANISM_TAXONOMY]] M2.2 caveat) |
| A-PM4 | The reversal exceeds round-trip friction | **F4** — a real but non-harvestable premium (fair price) |
| A-PM5 | PROXY flow is representative of total imbalance, not only retail | biased imbalance measure |

> **LIM2 caveat (binding, stated at G1):** at PROXY fidelity (no limit-order book), I5/I7 separation is **causal argument, not causal identification** ([[MARKET_INEFFICIENCY_TAXONOMY]] §5.3, LIM2). The reversion-vs-permanence test + informed-flow conditioning is the *best available* separation, and it caps confidence — it does not achieve identification.

## 5. Required dataset & capability

| Dataset | Role | Capability ([[DATA_FEASIBILITY_STUDY]]) |
|---|---|---|
| `stockbit_flow_bars` (1-min signed lot/freq/delta) | the order-flow imbalance (OFI) | **Available Today — PROXY tier**; ~1 yr history (from 2025-07) |
| `ohlcv` | prices, returns, Amihud illiquidity | Available Today, 5 yr |
| `broker_flow` (foreign/local/govt) | informed-flow proxy for the I7 split | Available Today, ~3.5 mo (short) |

> **History-maturity gate (DFS §5.3, binding):** the intraday flow proxy is short-history. **Regime-stratified and walk-forward validation are deferred until ≥ N months accumulate** ([[HYPOTHESIS_LIFECYCLE]] custody unaffected). A within-sample panel test on ~1 yr of 1-min data is large and likely powered (R2), but **generalization across regimes is gated** — this is a first-class scope rule, declared here, not discovered at review.

## 6. Variables
`OFI_t` = signed net flow imbalance (buy − sell lots, normalized by activity) · `r_t` = contemporaneous return · `rev_{t+1..t+k}` = forward reversal return · `illiq` = Amihud bucket (I6) · `informed_t` = foreign/smart-money net proxy (I7 split).

## 7. Planned statistical methodology (preparation only — no experiment run)
- Pooled/panel regression of forward reversal `rev_{t+1..t+k}` on `OFI_t` with `illiq` and `informed` interactions; **double-clustered** SE (ticker × time), Newey-West for serial correlation.
- Decile portfolio sort on `OFI_t` → forward-reversal spread, net of a versioned cost model (A-PM4/F4).
- **I5/I7 discriminator:** sign and decay of the post-displacement return, split by `informed` (reversion for uninformed = I5; permanence for informed = I7).
- Multiplicity: **family-adjusted DSR** from the P-M scan distribution; **PBO via CSCV**. Bid-ask-bounce control to defend against the F1 category hazard (§3).

## 8. Falsification criteria & one-sentence refutation
- **Ex-ante refutation:** displacement conditional on imbalance does **not** revert net of cost (signed reversal ≤ 0 or < MDE) ⇒ M1.1 refuted (→ permanence/M2.1, or F4 friction, or F1 fair-price). `MDE`: **TBD** from a power calc on the existing flow panel — computable now, deferred per instruction; `k`, DSR bar fixed at registration (R5).
- **One-sentence severe refutation:** *"If price displacement conditional on signed order-flow imbalance does not partially revert (net of cost) within k minutes, the inventory mean-reversion mechanism (M1.1) is refuted for IDX proxy flow."*

## 9. Expected evidence product
At N=1 the terminal tier is **C2** ([[EVIDENCE_MODEL]] EV-9). Outcome is either a **C2 provisional inventory-reversal edge** (reversion confirmed; informed-flow split consistent with I5) or a **competent refutation** (permanence ⇒ I7/M2.1 dominates · F4 friction kill · F1 fair-price/bid-ask-bounce). **Either maps a boundary on the D2 identification problem and is a first-class product** (R12, PG-11). No capital at C2 — shadow only.

---

## 10. G1 admissibility assessment

The six §5.2 elements + G1 guards ([[HYPOTHESIS_LIFECYCLE]] §4.1). **Verdict: G1 substantially satisfiable now — data exists; 1 item held pending a (deferred) power calc.**

| Requirement | Status |
|---|---|
| Mechanism: M-class + constraint + participant | ✅ M1.1 · inventory risk · supplier vs aggressor |
| Directional prediction (sign-specified) | ✅ reversal > 0 |
| Null | ✅ no reversal (permanence or zero) |
| Scope | ✅ liquid IDX universe, 1-min, ~1 yr proxy flow |
| Multiplicity family declared | ✅ P-M {I5,I6,I7,I12} |
| **D2 separation strategy stated** (MIT §5.3 G1 requirement) | ✅ reversion-vs-permanence + informed-flow split (LIM2-capped) |
| Mechanism `blind_to` OOS | ✅ theory-first (Ho-Stoll, Glosten-Milgrom, Amihud-Mendelson) — pre-dates any IDX result |
| Refutation condition in one sentence | ✅ §8 |
| required_data Available/Obtainable | ✅ Available Today (PROXY) — **history-maturity gate on regime validation** (§5) |
| Power / test can fail (R2) | ⚠️ large 1-min panel ⇒ within-sample power likely adequate; **MDE not yet fixed** (needs the deferred power calc) |
| **Ex-ante criterion incl. effect size (R5)** | ⚠️ **HELD** — `MDE`, `k`, DSR bar to be fixed at registration |
| CRO approval | pending |

## 11. Outstanding blockers & registration readiness

| Blocker | Nature | Blocks registration? |
|---|---|---|
| **B-1 · MDE not fixed** | needs a power calc on the existing flow panel (computable now; **deferred by instruction**) | **Yes** until run — but data exists; not data-blocked like HYP-PA-0001 |
| **B-2 · CRO ex-ante sign-off** | fix `k`, MDE, DSR bar (R5) | Yes |
| B-3 · History-maturity gate | regime/walk-forward validation deferred until ≥N months | No — gates *validation*, not registration |
| B-4 · LIM2 identification ceiling | PROXY fidelity ⇒ I5/I7 is argument, not identification | No — caps confidence (≤C2), declared |

> **Registration readiness:** unlike [[HYP-PA-0001_DRAFT|HYP-PA-0001]] (blocked on missing data), HYP-PM-0001's data **exists today**. The only thing between this draft and a valid G1 registration is **running the power calc to fix the MDE (B-1, currently deferred) and the CRO's ex-ante sign-off (B-2)**. No experiment, inference, or registration is performed here.

## 12. Traceability
Family [[DECISION_LOG]] D-028 · Mechanism [[ECONOMIC_MECHANISM_TAXONOMY]] §2 (M1.1) / §3 (M2.1) · Identification problem [[MARKET_INEFFICIENCY_TAXONOMY]] §4–§5 (I5↔I7, LIM2) · Gate [[HYPOTHESIS_LIFECYCLE]] §4.1 · Data [[DATA_FEASIBILITY_STUDY]] §4.1/§5.3 · Tier [[EVIDENCE_MODEL]] EV-9. **Parent:** [[RESEARCH_PROGRAM]] · [[OBJECTIVES_2026H2]] (O1). **Registers into** P-M family at a later step — not before.
