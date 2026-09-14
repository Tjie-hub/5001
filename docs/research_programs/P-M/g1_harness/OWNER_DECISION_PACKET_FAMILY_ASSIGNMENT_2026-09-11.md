# OWNER DECISION PACKET — TAXONOMY/FAMILY ASSIGNMENT + GOVERNANCE RECEIPTS — 2026-09-11

**Mode:** governance documentation only. No empirical analysis, no C7/C6/C8 execution, no harness modification, no commits. This packet presents existing authoritative material and options; **it makes no decision on the Owner's behalf.**

**Situation:** the G1 governance closeout established that the P-M multiplicity family is defined over taxonomy entries **{I5, I6, I7, I12}**, while the G1 arms (C2, C3) and the proposed next test (C7) are **C-numbered discovery candidates with no taxonomy assignment** in any authoritative document. Until assigned (or separately denominated), their results cannot be counted in any multiplicity denominator.

---

## 1. Authoritative definitions (cited)

### I-entries (`docs/research_os/MARKET_INEFFICIENCY_TAXONOMY.md`)

| Entry | Scientific definition (verbatim, abridged) | Required evidence | Key interactions |
|---|---|---|---|
| **I5 · Inventory-imbalance liquidity premium** | "Following a flow imbalance that forces liquidity suppliers into undesired inventory, prices deviate… and revert as the inventory is worked off." | E4 floor, unusually demanding: cost model must charge the **inventory risk borne**; gross-of-risk E4 "establishes only that a premium exists — which nobody disputes". | "**Deeply confounded with I7** … Any test claiming I5 must state how it excluded I7, or it has tested neither (**LIM2**)." Half-life short, competition-sensitive. |
| **I6 · Illiquidity premium** | "Assets that are costly to trade are priced at a discount… expected returns higher by an amount related to expected trading cost." | E4 floor is "the whole test": gross-of-cost confirmation "means nothing… An E3 result here is not partial progress; it is uninformative by construction." | "Interacts with I5 via the shared D4 cost model — a cost-model error propagates to both, so their failures are **not independent**, which matters for the family denominator." |
| **I7 · Adverse-selection premium** | "…transaction prices deviate systematically… in the direction of the informed party's information, and **do not revert**." | E4 floor; discriminating test is **permanence versus reversion**; participant-class attribution is a proxy (LIM1 binds fidelity). | Central I5/I7 identification problem; confounds I2. |
| **I12 · Capacity-shielded deviation** | Persistence of deviations "too small… to interest participants with the capital and skill to remove them". **A modifier, not a competitor** — "testable only through a host entry". | Requires the **capacity gradient** (present below an attention threshold, absent above); "a test that measures the effect without measuring the gradient has not tested I12". | Modifies/subsumed by I6; applies to I1, I4, I9. |

### Family/multiplicity rules (`HYPOTHESIS_REGISTRY.md`, PG-3/OS-10)

- P-M family = **{I5, I6, I7, I12}**, **append-only**; membership counted **from registration** and "never leaves". Two slots consumed: HYP-PM-0001 (FAILED F2), HYP-PM-0003 (FAILED F2). HYP-PM-0002 remains DRAFT, consumes no slot.
- OS-10 (CRO-adopted, Option B): independent registrations are counted **independently** even over overlapping instruments.
- **LIM3** (taxonomy §4): "pooled tests across confounded entries inflate the effective sample and corrupt the family denominator." **LIM2**: an I5-claiming test must state how I7 was excluded. LIM1 binds proxy-fidelity claims.

## 2–3. Candidate-by-candidate analysis

### C2 · conduit disagreement (foreign-owned vs locally-owned brokerage net disagreement) — REGISTERED under `G1_REGISTRATION_v1`; executed; **NOT CONFIRMED**; proposed classification INVALID (controls unimplementable)

| Field | Assessment |
|---|---|
| Candidate definition | Opposite-signed net flow of the two conduit classes (each ≥ 15% of gross) → forward-return resolution. Executed form: unconditional daily contrast (species/liquidity conditioning withdrawn as unimplementable). |
| Closest I-entry | **I5/I7 domain** (signed net flow → direction and permanence of price response). |
| Supporting rule/document | None assigns it. `HYP-PM-0003_REGISTERED` used `SUM(lot)` net flow (registered historically, failed, ≡0 at limit=150) — the nearest registered predecessor, but it does not extend to C2. |
| Required evidence obligation if assigned | An I5 assignment triggers **LIM2** (state the I7 exclusion); an I7 assignment requires the **permanence-vs-reversion** discriminating test. C2's registered contrast is neither. |
| Conflict/risk | C2's executed form cannot satisfy either entry's evidence obligation; assignment after execution would retroactively re-label a test that cannot meet the entry's standard. |
| Authorized by existing governance? | **UNRESOLVED** — no document authorizes any assignment. |

### C3 · breadth surprise (participation asymmetry → next-session return/volume) — REGISTERED; executed; **NOT CONFIRMED**; proposed classification VALID → NOT CONFIRMED (bounded)

| Field | Assessment |
|---|---|
| Candidate definition | Breadth = (n_buy − n_sell)/(n_buy + n_sell) from full-population store rows; surprise vs trailing median; broad/narrow state contrast. |
| Closest I-entry | **I5-domain** (breadth extreme = one-sided participation → crowding/inventory → fade), possibly I7 for the permanent component. The map classifies family B as its own mechanism; no I-entry names breadth. |
| Supporting rule/document | None assigns it. Family map B: "NEW FAMILY (independent: corr w/ species −0.147)". |
| Required evidence obligation if assigned to I5 | LIM2 I7-exclusion statement; net-of-risk cost model — C3's registered form measured gross state contrasts only. |
| Conflict/risk | C3's executed null (all horizons, sign flip at k=10) is bounded and clean **as a state-contrast test**; assigning it to I5 post-execution would attach an evidence standard it was not registered to meet. |
| Authorized by existing governance? | **UNRESOLVED.** |

### C7 · intensity-state (gross ≥ 2× ADV20 state → outcome) — REGISTERED (owner-approved six decisions); **not executed**

| Field | Assessment |
|---|---|
| Candidate definition | intensity = gross/ADV20 (median-20, shift-1); high ⇔ ≥ 2.0; contrast: high vs non-high daily forward-return spread (owner decision 2026-09-11). |
| Closest I-entry | **I6-domain** (execution/liquidity information; the map labels D/H "execution-type") or **I5** (inventory persistence 48%/46% vs 11.3%). Neither is documented. |
| Supporting rule/document | Family map D/H ("execution-type; freq-free"); custody handoff primary-survivor designation. No I-entry assignment. |
| Required evidence obligation if assigned to I6 | I6's E4 standard: only net-of-realistic-friction results are claims; C7's registered 0.60% RT sensitivity is a reported reading, and I6's own note says failures on the shared D4 cost model are **not independent** across I5/I6 assignments. If assigned to I5: LIM2 applies. |
| Conflict/risk | Assigning C7 to I6 would place a state-contrast test under an entry whose required evidence is a net-of-cost premium measurement — a different claim. Not authorized anywhere. |
| Authorized by existing governance? | **UNRESOLVED.** |

## 4. Minimum owner choices (presented, not decided)

| Option | Content | Multiplicity consequence | Governance load |
|---|---|---|---|
| **A. Assign each C-arm to an existing I-entry** | C2 → I5-or-I7 domain; C3 → I5 domain; C7 → I6 domain (illustrative affinities only — the Owner would fix each) | P-M {I5,I6,I7,I12} denominator grows by the assigned arms (2–3 new members; the 2 consumed slots are preserved — append-only, never reused). LIM2 separation statements attach to any I5 assignment; I5/I6 share the D4 cost model (failures not independent). | Highest: each assignment carries its entry's full evidence obligations, which the executed C2/C3 forms were not registered to meet. |
| **B. Separate C-family with its own denominator** | Formalize the already-registered {C2, C3, C7} set as its own family (C1a/C1b withdrawn, not members), opened per the registry's own "family opened at first registration" precedent (D-028). | New family row: 3 registered arms, 1 executed (C3 not confirmed), C2 governance-invalidated, C7 pending. P-M {I5,…} denominator untouched at 2 consumed. | Lowest: one registry row + one DECISION_LOG receipt; no I-entry obligations triggered. |
| **C. Leave the C-arms unassigned** | C2/C3 results remain unregistered in the ledger; C7 stays non-executable indefinitely. | No denominator change; C7 ineligible for preflight. | Zero load, but the program's own primary-survivor line (C3/C7) stays uncountable. |

**Recommendation (minimum governance, supported by existing hierarchy):** **Option B.** The C-arms were already registered as their own family under one owner-authorized registration and one single-cell C7 registration; formalizing that set with its own denominator requires one registry row and triggers no I-entry evidence obligations. Option A remains available to the Owner if a taxonomy assignment is desired, but it imports LIM2/D4 obligations that no existing document discharges for the C-arms. **The choice is the Owner's.**

## 5. Governance receipt list (to be entered AFTER owner approval — not written now)

1. Dataset B freeze (store sha `21661f03…`; freeze manifest v1 `95f2c998…`).
2. BFI-002 replacement registration v1 (`G1_REGISTRATION_v1_2026-09-11.md`) — as the authorized replacement, original NOT FOUND.
3. C1a/C1b withdrawal (freq UNKNOWN; unconditional).
4. NF ratification (stockbit_flow share-ratio construction; digest `60f5f91c…`).
5. Six C7 owner decisions (outcome/contrast/horizons/multiplicity/MDE/persistence treatment).
6. G1 Run 1 + split classification (C1a INVALID, C1b WITHDRAWN/never implemented, C2 INVALID, C3 VALID→NOT CONFIRMED, G1 SPLIT/governance-invalidated).
7. Taxonomy/family assignment decision (Option A/B/C as chosen).
8. Required registry rows: G1 family row (per Option), C7 registration row, G1 FAIL ledger entry, and the DECISION_LOG entry receipting items 1–7.

---

## OWNER DECISION REQUIRED

- **Exact decision:** choose **A** (assign C2/C3/C7 to I5/I6/I7 entries, with the evidence obligations above), **B** (register the C-set as its own separately-denominated family), or **C** (leave unassigned; C7 remains non-executable).
- **Affected candidates:** C2, C3, C7 (C1a/C1b unaffected — withdrawn).
- **Multiplicity consequence:** A → P-M {I5,I6,I7,I12} grows by 2–3 members with LIM2/D4 obligations attached; B → new separate C-family (denominator = its own registered arms); C → no counting possible.
- **C7 preflight eligibility:** C7 becomes eligible for preflight **only** under A or B, after the receipts in §5 are entered. Under C it remains paused indefinitely.
- **Governance receipts to enter:** the seven-item list in §5.

*Prepared read-only. Nothing executed, nothing committed, nothing modified outside this packet.*
