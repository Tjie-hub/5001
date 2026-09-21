# HYP-PM-0008 · BLOCKER RESOLUTION AUDIT — D-1 / D-2 — 2026-09-14

**Authority:** generated point-in-time record (audit only). **Scope: D-1 and D-2 only. D-3 untouched.**
**Subject:** `HYP-PM-0008_SPEC.md` (DRAFT), `HYP-PM-0008_CANDIDATE_AUDIT_2026-09-14.md`
**Status of subject at audit time:** DRAFT · OWNER DECISION REQUIRED · not registered, not executed.

> **No empirical test, no backtest, no G1 harness run, no registry mutation, no database write, no
> `g1_config` mutation, no execution.** No outcome statistic was inspected. No event count was estimated.
> No option was chosen on the Owner's behalf. The semantic register was **not** modified.

---

# PART A — D-1 FAMILY FORENSIC ANALYSIS

## A.0 Two corrections to my own prior documents (recorded first, before anything rests on them)

Forensic re-reading of the authoritative sources contradicts two claims I made on 2026-09-14 in
`HYP-PM-0008_SPEC.md` §20/B1 and `HYP-PM-0008_CANDIDATE_AUDIT_2026-09-14.md` §5.2. Both are corrected
here; the original documents are left unedited (append-only discipline), and this section supersedes them.

| # | Prior claim | Correction | Source |
|---|---|---|---|
| **C-1** | "I1 is **confounded with I2 and I3**, both inside P-A's family" | **I1↔I2 is not an authoritative relation.** The §4 interaction graph draws **no I1↔I2 edge**; it draws `I1 <-.-> confounds I3` and, separately, `I2 <-.-> confounds I3`. I2's own entry does **not** mention I1 (it says "Competes with I3"). Only the **I1 prose entry** asserts an I1↔I2 confound, and it is unreciprocated. **The authoritative I1 confound inside P-A is I3 alone** | MIT §4 graph; MIT I2 Interactions; MIT I3 Interactions |
| **C-2** | The semantic register's `VERIFIED` is a status "which the card it cites does not support" | **Too strong as stated.** The register and LC-PM-0009 use "verified" in **two different senses** and are not in direct contradiction — see Part C.4. The register's label is nonetheless **mis-evidenced** (it cites the wrong artifact), which is a real but different defect | `fingerprint.py:207–215`; `OUTSIDE_BAND_INVESTIGATION_v1.json` |

**C-1 materially narrows the D-1 problem** and changes the option matrix: the confound tying I1 to P-A runs
through **I3 only**, not through two of P-A's three entries.

## A.1 Q1 — What exactly makes I1 confounded with I2 and I3?

**With I3 — a genuine, reciprocated `confounds` relation:**

> MIT I3 Interactions: "**Confounds I1** — a band that bound at the close mechanically shapes the next open,
> so I1 and I3 evidence overlap on precisely the observations most likely to be studied."

> MIT I1 Interactions: confounded "with I10 … and with I2"; MIT §4 graph: `I1 <-.->|confounds| I3`.

Both entries are M6/D1 market-design artifacts operating at the same session boundary. The stated
overlap mechanism is specific: **a band that binds at the close shapes the next open.**

**With I2 — NOT ESTABLISHED.** See correction C-1. I2's mechanism is closing-auction clearing under
mandated flow (M6+M4); its declared interactions are "Subsumed-by relation with I8" and "Competes with I3."
There is no I1↔I2 edge in the authoritative graph.

**Two further relations bear on I1 and must not be conflated with a confound:**

| Relation | Kind | MIT §4 consequence | Merge trigger? |
|---|---|---|---|
| I1 ↔ I3 | **Confounds** | "A confirmation supports both equally. Severity is zero for discriminating them (R3). The test must be redesigned or the claim narrowed." | **Yes** (PG-7 + PB §1.2) |
| I12 → I1 | **Modifies** | "**Not a rival.** Must be tested *jointly*, as I12 is testable only through a host entry." | **Yes** under PB §1.2 step 2 ("Testable only JOINTLY. Same family") |
| I10 → I1 | **Rival origination** | Not one of the three recognised relation kinds in the §4 table; recorded in the graph as `rival origination` | **No** — and I10 is in **no declared family** |

> **The I10 relation is a *design* obligation, not a family obligation.** MIT I1: "A test that does not
> separate I1 from I10 tests neither." `HYP-PM-0008_SPEC.md` §3 discharges this by construction — the
> estimand is a difference across an exogenous decree switch, with the rule-unchanged ARA side as a
> within-study placebo. Salience does not move on a decree date.

**Design note bearing on the I1↔I3 confound's severity:** the stated overlap mechanism runs through *the
next open*. `HYP-PM-0008_SPEC.md` §5 uses **`close` only** and states "`open`, `high` and `low` are not used
anywhere." This does not dissolve the taxonomic relation — PB §1.2 checks *entries*, not *specifications* —
but it is a material fact for the Owner: the specific channel the taxonomy names as the overlap is not
traversed by this design.

## A.2 Q2 — What exactly does PG-7 require?

> **Rule PG-7** (`RESEARCH_PROGRAM_STANDARD.md` §3.3): "**Merging Programs merges families** — permitted, and
> sometimes **mandatory**. Where two **Programs' entries** `confound` or `subsume` each other … their
> evidence is **not independent** and separate families **understate both denominators**. … **The CRO must
> merge on discovery of the dependence** — and per Taxonomy §4 the **I5↔I7 and I2↔I8** relations are the
> live instances."

Three properties, all load-bearing:

1. **PG-7 operates on Programs, not on individual hypotheses or unassigned taxonomy entries.** Its trigger
   condition is two *Programs'* entries confounding. An entry in **no** Program cannot trigger it.
2. **Its named live instances are I5↔I7 and I2↔I8** — both already discharged by D-028. **I1↔I3 is not
   among them**, because at the time PG-7 was written no Program claimed I1.
3. **Direction is one-way.** §3.3: "families may **grow and merge, never shrink or split**." PG-6 forbids
   splitting; PG-7 permits/compels merging. Neither forbids *creating* a new family.

The operational procedure is `RESEARCH_PROGRAM_PLAYBOOK.md` §1.2, and it is stricter than PG-7's prose:

```
2. CHECK EVERY PAIR against MIT §4's interaction structure:
   ── CONFOUNDS?  ⇒ SAME FAMILY. Not negotiable.
   ── SUBSUMES?   ⇒ SAME FAMILY. Separate families understate BOTH.
   ── MODIFIES?   ⇒ Testable only JOINTLY. Same family.
3. MERGE where any of the three holds.                        (PG-7)
```

> **The decisive consequence, stated plainly.** Applying §1.2 literally to I1 requires I1 to share a family
> with **I3** (confounds → "not negotiable") **and** with **I12** (modifies → "same family"). I3 is in
> **P-A**; I12 is in **P-M**. A single family containing I1, I3 and I12 therefore requires **merging P-A
> and P-M**. That direction is legal (families may merge) but it is a far larger act than anything
> contemplated in the HYP-PM-0008 draft, and it would place every P-M and P-A member in one denominator.
> **This possibility is surfaced for the Owner; this audit does not recommend it.**

## A.3 Q3 — What exactly did D-028 close?

D-028 (2026-07-17, ACCEPTED, Owner) did four things and no more:

1. Declared **P-M = P1+P2, family {I5, I6, I7, I12}** and **P-A = P3, family {I2, I3, I8}**.
2. Recorded the rationale: I5↔I7 *confound*, I6↔I12 *near-inseparable*, I8→I2 *upstream*.
3. Stated the forward constraint: "Per **R7.5 / PG-6**, a declared family may never later be **narrowed or
   split**. Once a family has an active registration, **any change requires a formal governance amendment**
   … otherwise the sole remedy is program termination and a new family from zero."
4. "This decision **closes G-6**." — and explicitly: "**P4/P5/P6 remain unaffected (retained, not
   initiated — D-006).**"

## A.4 Q4 — Does D-028 prohibit a new family for I1? **NO.**

This is the central forensic finding of Part A, and it **corrects the framing** in the HYP-PM-0008 draft.

| What D-028 prohibits | What D-028 does not touch |
|---|---|
| **Narrowing or splitting** P-M's `{I5,I6,I7,I12}` or P-A's `{I2,I3,I8}` | **Creating a new family** for a Program not yet initiated |
| Changing a family **with an active registration** without a formal amendment | Entries claimed by **no** declared family (I1, I4, I9, I10, I11) |
| Re-opening the **G-6 merge question** for the then-current programs | P4/P5/P6 — **expressly "retained, not initiated"**, i.e. future initiation with their own families is contemplated by the decision itself |

**"The merge was available once; it has now been exercised"** (`RESEARCH_PROGRAM.md` §2.1) refers to the
**G-6 window** — the one-time opportunity to redraw the boundaries of the *then-existing* Programs. It is a
statement about *those* families, not a standing prohibition on ever declaring another.

> **Therefore: D-028 prohibits a particular class of family change (reduction), not the creation of a new
> family.** My prior SPEC §20/B1 framing — that D-028 "closed the merge window" in a way that blocks a new
> family for I1 — **overstated the constraint** and is corrected here.

**What *does* constrain a new family for I1 is PB §1.2, not D-028** — because a new family containing I1
alone would fail the pair-check against I3 and I12 (A.2). That is a different, and more tractable, problem.

## A.5 Q5 — What precedent does D-048 Option-B establish?

D-048 (2026-09-11, APPROVED Option B, Owner) opened the **P-M · C-family {C2, C3, C7}** as a "**separately-
denominated hypothesis family**", "opened per the registry's own '**family opened at first registration**'
precedent (D-028, PG-3)". Its explicit carve-outs:

- "**No I-taxonomy assignment.** C2, C3, and C7 are **not** classified as I5, I6, I7, or I12. The taxonomy
  assignment question was ruled UNRESOLVED … and remains an **Owner prerogative for the future**."
- "**No pooling.** The C-family is not pooled with, and does not modify, the P-M {I5, I6, I7, I12} family."
- Multiplicity consequence: "P-M {I5,I6,I7,I12} denominator: **unchanged**."

**The precedent, stated exactly:** the Owner may open a new, separately-denominated family inside an
existing Program, **without** assigning its members to the I-taxonomy, and **without** altering any existing
family's denominator. D-048 did this three months after D-028 and treated D-028 as its *authority*, not as
an obstacle — which independently confirms A.4.

> **The precedent's cost, which the Owner should see.** Declining I-taxonomy assignment is precisely what
> makes PB §1.2's pair-check inapplicable: §1.2 checks pairs of **taxonomy entries**, and an unassigned
> family has none to check. Whether that is a legitimate scoping act or the "narrow family declared by
> administrative convenience" that **PB-2** warns against ("**Draw it wide. A wide family is honest and
> expensive. A narrow one is cheap and wrong**") is a governance judgment, not a documentary fact. It is
> recorded here as a tension, unresolved, for the Owner.

## A.6 Q6 — Is there an already-defined lawful family assignment for I1? **NO.**

Exhaustively checked: `HYPOTHESIS_REGISTRY.md` family-slot ledger (3 families: P-M `{I5,I6,I7,I12}`,
P-M C-family `{C2,C3,C7}`, P-A `{I2,I3,I8}`); `RESEARCH_PROGRAM.md` §2.2 active program table;
`RESEARCH_PROGRAM_STANDARD.md` §9 program register; `DECISION_LOG.md` D-006/D-028/D-048/D-049;
`EXPERIMENT_LEDGER.jsonl`; `FAILURE_REGISTRY.md`.

**I1 appears in no family declaration anywhere.** Its only status statement is MIT's own: "**Research
maturity: RM0 · Conjectured. No literature card, no registration. Admissible only.**"

> **One stale fact worth recording:** MIT's I1 entry says "no literature card." That is **no longer true** —
> `LC-PM-0006` … `LC-PM-0010` were created 2026-08-21 and four of them are I1-specific, including one Q4
> journal source (`LC-PM-0007`). The RM0 maturity grade is therefore out of date. This is a documentary
> staleness note, **not** a proposal to edit MIT.

## A.7 Q7 — What exact Owner decision is required?

A single act: **assign HYP-PM-0008 to a multiplicity family, or refuse it.** Four lawful forms exist
(Part B). The decision is reserved to the Owner/CRO because it (a) is a PG-A initiation gate item
("**family declared** … **CRO approval**"), and (b) changes a permanent denominator under PG-3, which is
append-only and irreversible from the moment of registration.

---

# PART B — D-1 OPTION MATRIX

**No option is chosen or recommended here.** Presented for Owner determination.

## Option 1 — JOIN P-A `{I2, I3, I8}`

| | |
|---|---|
| **Source evidence** | MIT I3: "Confounds I1." MIT §4 graph: `I1 <-.-> confounds I3`. PB §1.2: "CONFOUNDS ⇒ **SAME FAMILY. Not negotiable.**" I3 ∈ P-A (D-028) |
| **Governance consequence** | The **only** option that satisfies §1.2's confounds rule for I1↔I3 without merging two Programs. P-A denominator 1 → **2**. HYP-PA-0001 (FAILED F2) is retroactively re-weighted against a larger family — the honest direction (PG-5) |
| **Conflict with existing rules** | **Leaves I12→I1 (`modifies`) unaddressed** — §1.2 also demands same-family for it, and I12 ∈ P-M. **PG-1 scope tension:** P-A is declared "Auction Dislocation … reconstitution/close mechanism as one denominator"; I1 is a price-limit band mechanism. Registering it into P-A widens P-A's *de facto* scope without a scope amendment |
| **Requires an amendment?** | **No** for the registration act itself (registering into a declared family is normal operation). **Arguably yes** for the scope-widening, which the Owner may prefer to record explicitly |
| **Consumes a permanent slot?** | **Yes** — P-A slot #2, permanent, never leaves (PG-3) |

## Option 2 — JOIN P-M `{I5, I6, I7, I12}`

| | |
|---|---|
| **Source evidence** | MIT §4 graph: `I12 -.->|modifies| I1`. §4 table: "Modifies … Must be tested *jointly*." PB §1.2: "MODIFIES ⇒ … Same family." I12 ∈ P-M (D-028) |
| **Governance consequence** | Satisfies §1.2 for the I12 relation. P-M denominator 2 → **3**, retroactively re-weighting HYP-PM-0001 and HYP-PM-0003 (both terminal failures) |
| **Conflict with existing rules** | **Leaves the I1↔I3 `confounds` relation unaddressed** — the *stronger* of the two relations ("not negotiable" vs "tested jointly"). **PG-1 scope conflict is severe:** P-M's declared family is "order-flow imbalance + liquidity/toxicity as one denominator," capability class **PROXY (D2)**; I1 is **M6/D1 market design** and consumes no flow data at all. **MIT §4's `modifies` consequence is "not a rival … tested jointly"** — arguably satisfied by joint testing rather than by co-family membership |
| **Requires an amendment?** | **Probably yes** — a D1 market-design entry in a family declared as a D2 flow denominator is a scope change on its face |
| **Consumes a permanent slot?** | **Yes** — P-M slot #3, permanent |

## Option 3 — NEW SEPARATE FAMILY

Two materially different sub-forms. **They are not interchangeable.**

### 3a — New family **with** explicit I1 assignment

| | |
|---|---|
| **Source evidence** | D-028 does not prohibit new families (A.4); D-006 retains P4/P5/P6 uninitiated; PG-6/PG-7 restrict only shrinking/splitting |
| **Governance consequence** | A new denominator starting at 1. No existing family is touched |
| **Conflict with existing rules** | **Direct conflict with PB §1.2**: naming I1 triggers the pair-check against I3 (confounds, "not negotiable") and I12 (modifies), both of which sit in other families. A one-entry {I1} family is exactly the narrow denominator **PB-2** forbids |
| **Requires an amendment?** | **YES — a formal, superseding governance amendment** explicitly disapplying or qualifying PB §1.2 for this case, with reasons on the record |
| **Consumes a permanent slot?** | **Yes** — new family slot #1, permanent |

### 3b — New separately-denominated family **without** I-taxonomy assignment (the D-048 pattern)

| | |
|---|---|
| **Source evidence** | **D-048 Option B, verbatim precedent**: a separately-denominated family, "**No I-taxonomy assignment made or inferred**," "**No pooling**," existing denominators "**unchanged**" |
| **Governance consequence** | New denominator at 1; P-M and P-A untouched. Identical in form to the C-family act of 2026-09-11 |
| **Conflict with existing rules** | **No documentary conflict** — §1.2's pair-check is inapplicable to an unassigned family. **But the substantive tension with PB-2 is real**: the mechanism *is* I1 in all but name, and declining to name it is what avoids the check. The C-family precedent has the identical property and the Owner accepted it once, recording the taxonomy question as an open Owner prerogative |
| **Requires an amendment?** | **No** — precedented by D-048; requires a new dated decision entry recording the family opening, as D-048 itself did |
| **Consumes a permanent slot?** | **Yes** — new family slot #1, permanent |

## Option 4 — RETIRE / DO NOT REGISTER

| | |
|---|---|
| **Source evidence** | `RESEARCH_PROGRAM.md` §5.2: "**Refusal is the cheapest and most common outcome.** Most proposed hypotheses should be refused at G1. Refusal costs nothing; **registration costs a family slot forever**" |
| **Governance consequence** | No denominator changes anywhere. The mechanism remains in the **free era** (DRAFT/discovery): `LC-PM-0006…0010`, the 2026-08-21 discovery record, and `HYP-PM-0008_SPEC.md` all survive as unrisked material, refinable without limit (HL-2: G1 is a one-way door; before it, refinement is free) |
| **Conflict with existing rules** | **None.** This is the governance-default outcome |
| **Requires an amendment?** | **No** |
| **Consumes a permanent slot?** | **No** |

## B.5 The fifth possibility, surfaced but not tabled as an option

Applying PB §1.2 **literally and completely** to I1 implies a family containing I1 ∪ {I3} ∪ {I12}, i.e.
**merging P-A and P-M**. This is directionally lawful (PG-7 permits merging; only splitting is forbidden)
and would be the maximally honest denominator. It would also pool every P-M and P-A member — 3 terminal
failures plus any new registration — into a single family. It is recorded because the Owner should know
the literal reading exists; it is **not** presented as one of the four requested options, and this audit
does not recommend it.

---

# PART C — D-2 EVIDENCE CHAIN

## C.1 Q1 — What is the exact primary source?

Two decrees, both now **identified by number** (an advance on LC-PM-0009, which named only the 2025 one):

| Boundary | Decree | Issued | Effective |
|---|---|---|---|
| **R3 start** (symmetric tiered ARB) | **Kep-00055/BEI/03-2023** — Peraturan Nomor II-A, Perdagangan Efek Bersifat Ekuitas | **2023-03-30** | ARB Simetris **Tahap II: 2023-09-04** |
| **R4 start** (flat 15% ARB) | **Kep-00003/BEI/04-2025** — Perubahan Peraturan Nomor II-A | 2025-04-08 | **2025-04-08** |

An IDX-hosted PDF exists for the 2023 decree
(`idx.co.id/Media/y0vjxqur/signed_peraturan_ii_a_perdagangan_efek_bersifat_ekuitas.pdf`).

## C.2 Q2 — Is it actually available? **NO.**

| Attempt | Result |
|---|---|
| Local corpus + ZCodeProject file search (`*kep*`, `*decree*`, `*BEI*`, `*peraturan*`, all PDFs) | **No decree document anywhere.** Only PDF in the corpus is `docs/L3 Data Ontology Specification.pdf` (unrelated) |
| Grep for `Kep-00003` / `00003/BEI` across both corpora | 14 hits — **all are citations**, in LC-PM-0006/0009, Dataset B code/artifacts, and my own two drafts. **Zero document text** |
| `WebFetch` → `idx.co.id/id/peraturan/keputusan-direksi` | **HTTP 403** |
| `WebFetch` → the signed Peraturan II-A PDF | **HTTP 403** |
| `curl` (browser UA) → same PDF | **HTTP 403**, 4,570-byte HTML WAF page |
| `WebFetch` → `indonesia.go.id` (official government portal) | Returned only the site shell; JS-rendered, no article text |

**No WAF-circumvention was attempted.** IDX's 403 is the publisher's access control and was respected.

## C.3 Q3–Q8 — What the retrievable evidence establishes

### Secondary corroboration (retrieved this session)

**Kontan (national financial daily), published 2025-04-08 08:51 WIB — same day, pre-open:**

| Question | Finding |
|---|---|
| **Q3 · effective date** | Tuesday, **2025-04-08** ✓ |
| **Q4 · new band** | ARB **15%** ✓ |
| **Q6 · population covered** | Shares on **Main Board, Development Board, New Economy Board**; **ETF**; **DIRE** — "**untuk seluruh rentang harga**" (all price ranges) ✓ |
| **Q7 · exceptions** | None stated in the ARB clause. *(But the rulebook contains separate regimes — see C.5)* |
| **compound treatment** | Trading halt re-tiered: **8% / 15% / 20%** — confirms LC-PM-0009 condition 5 and `SPEC` §7 E6 |

**Q5 · effective date vs publication date — a genuine asymmetry the Owner should note:**

- **R4:** decree issued **and** effective **2025-04-08** (same day; an emergency response to US tariff
  turbulence). Publication = effect.
- **R3:** decree issued **2023-03-30**, but the symmetric-ARB **Tahap II** took effect **2023-09-04** —
  **over five months later**, and in stages (Tahap I: ARB 15% from 2023-06-05). **Issuance date ≠ effective
  date**, and coding R3 from the decree date would be wrong by five months. LC-PM-0009's staged R2/R3
  timeline is corroborated by this.

### Behavioural corroboration — found inside the local corpus, previously uncited

`docs/research_programs/P-M/dataset_b/artifacts/OUTSIDE_BAND_INVESTIGATION_v1.json` is a **band-model
reconciliation against observed exchange prices**. A naive flat −15% ARB applied across the whole Dataset B
window produced **15 breaches**; the file resolves **15/15, unresolved = 0**:

- **13 breaches are R3-dated, every one before 2025-04-08** (range 2025-01-23 … 2025-03-18), each a legal
  down-move against a **symmetric tiered floor**: observed −17.24% vs a −35% floor; −24.61% vs −25%;
  −19.94%, −19.89%, −19.44%, −18.75%, −18.42% vs −20%. The tiered symmetric R3 table is thus **observed in
  price behaviour**, not merely asserted.
- **Zero breaches on or after 2025-04-08.**
- Two further findings are ARA limit-ups (2025-11-11 BUMI, ceiling 202.50 = 35% of ref 150; 2026-08-18 KIJA,
  ceiling 166.05 = 35% of ref 123) — consistent with **ARA remaining tiered at 35% in the Rp50–200 band**,
  which is the substrate of the SPEC's placebo leg.
- One is a RAJA unapplied 5:1 split (already quarantined — SPEC §7 E4).

This is **revealed-behaviour evidence from the exchange's own price record**, a different and stronger
evidence class than citation cascade. Under "the −15% flat ARB was in force throughout," 13 illegal
down-moves would have to be coincidentally clustered before 2025-04-08. Under the R3/R4 coding, zero
violations occur.

**Its exact limit:** it bounds the switch to the interval **(2025-03-18, first post-switch session]** — it
cannot by itself distinguish 2025-04-08 from, say, 2025-04-01. The decree date must come from documents.

### Q8 — Does the evidence support HYP-PM-0008's exact coding?

`SPEC` §5 codes `band_lower = tier(35/25/20)` under R3 and `0.15` flat under R4, with regime boundaries
2023-09-04 and 2025-04-08.

| Coding element | Corroborated? | By what |
|---|---|---|
| R4 = flat 15%, **all price ranges** | **Yes** | Kontan, same-day, verbatim "seluruh rentang harga" |
| R4 effective 2025-04-08 | **Yes** (secondary) + bounded behaviourally | Kontan; OUTSIDE_BAND (no post-date breach) |
| R3 = symmetric tiered 35/25/20 | **Yes** | 2023 secondary sourcing; **observed floors** in OUTSIDE_BAND |
| ARA unchanged/tiered across the switch (**the placebo's substrate**) | **Yes, partially** | R4 decree changes ARB only; ARA 35% observed at two dates, but **only the Rp50–200 tier is evidenced** — the 25% and 20% tiers are unobserved locally |
| **R3 start = 2023-09-04** | **NOT corroborated by any local data** | Dataset B begins 2025-01-02 — it contains **no R2/R3-boundary evidence at all**. Secondary sourcing only |

> **The sharpest residual risk, and it is specific.** `SPEC` §8 uses R3 as the **control arm**. If the
> 2023-09-04 boundary is wrong, the control window silently absorbs **R2 sessions (ARB 15%)** — i.e.
> treatment-like sessions — which would bias `theta_primary` toward zero and corrupt the one contrast the
> hypothesis rests on. This is the single most consequential unverified element in the whole design, and it
> is **the one with the least evidence behind it**.

## C.4 Q9 — Why does the semantic register say VERIFIED while LC-PM-0009 says NOT primary-verified?

**Because the two documents use "verified" in different senses. They are not in direct contradiction** —
correcting my prior claim (C-2).

| | LC-PM-0009 | `DATASET_B_SEMANTIC_REGISTER_v1` |
|---|---|---|
| Sense of "verified" | **Documentary provenance** — was the decree itself retrieved? | **Semantic/empirical adequacy of a data field's meaning** — the register's house vocabulary |
| Its verdict | "corroborated but **NOT primary-verified**"; primary verification is "a **hard S2 prerequisite, not a nicety**" | `"status": "VERIFIED"` |
| House vocabulary evidence | — | Sibling entries set the standard: `broker_flow.value` VERIFIED on "SUM(value)=0 on 70,424/70,424 ticker-days"; `broker_flow.freq` **UNKNOWN**; `idx_tickers.in_idx80` **REJECTED FOR RESEARCH USE**. The register grades **measurements**, not documents |

**Both statements can be true simultaneously**: the decree is not primary-verified *as a document*, and the
regime coding is empirically adequate *as a model of observed prices*.

**However — the register entry is genuinely mis-evidenced.** Read at `fingerprint.py:207–215`, its evidence
field is *"LC-PM-0009: R3 symmetric to 2025-04-07, R4 ARB −15% from 2025-04-08 (SK Kep-00003/BEI/04-2025).
Dataset B: 58 R3 sessions, 328 R4 sessions."* — that is **a Q3 secondary citation plus a session count**,
neither of which is a measurement. The entry does **not** cite `OUTSIDE_BAND_INVESTIGATION_v1.json`, which
is the artifact that would actually justify `VERIFIED` under the register's own standard. The status label
is **defensible but unsupported by its stated evidence**, and the `VERIFIED` string is hard-coded by the
author rather than derived.

**The register was not modified by this audit**, per the brief.

## C.5 Q7 revisited — exceptions that exist in the rulebook, not in the decree

The ARB clause states no exceptions, but **separate regimes exist** and remain unexcludable (SPEC §20 B4):

- **Papan Pemantauan Khusus** — full call auction, ±10% symmetric above Rp10, ±Rp1 at Rp1–10
  (LC-PM-0006 Fact 3): **a different market mechanism**, not an ARB exception. The R4 decree's enumerated
  scope (Main / Development / New Economy boards, ETF, DIRE) **does not include it** — which corroborates
  that PPK names must be removed, while the corpus holds **no board-membership table** to remove them with.
- **IPO first trading day** — limits are **2× normal**, referenced to the offer price; no listing-date table
  is held.

## C.6 Q10 — Can the contradiction be resolved from primary evidence? **NOT FROM EVIDENCE NOW HELD.**

Resolving it requires the decree text, which is 403-blocked from this environment.

---

# PART D — PRIMARY-SOURCE VERIFICATION RESULT

## **PRIMARY VERIFICATION NOT ESTABLISHED**

Per the brief's instruction — *"Do not upgrade 'corroborated' to 'verified' merely because multiple
secondary sources agree"* — the evidence retrieved is classified strictly:

| Class | Content |
|---|---|
| **PRIMARY SOURCE** | **NONE OBTAINED.** Neither Kep-00003/BEI/04-2025 nor Kep-00055/BEI/03-2023 was retrieved in any form. IDX returns HTTP 403 to WebFetch and to `curl`. No local copy exists |
| **SECONDARY CORROBORATION** | Kontan (2025-04-08, same-day, pre-open) — decree number, effective date, 15%, "seluroh rentang harga", enumerated boards/ETF/DIRE, halt tiers. Multiple further outlets (Metro TV, pasardana, InfoPublik, indonesia.go.id, Ajaib) and, for 2023, decree number **Kep-00055/BEI/03-2023** + the staged Tahap I/II timeline |
| **BEHAVIOURAL CORROBORATION** *(non-testimonial, local)* | `OUTSIDE_BAND_INVESTIGATION_v1.json`: 15/15 anomalies resolved, 0 unresolved; 13 sub-band down-moves all pre-2025-04-08 against observed −20/−25/−35 floors; 0 post-date breaches of −15%; two ARA 35% limit-ups |
| **MODEL INFERENCE** *(mine, flagged as such)* | That the 13-vs-0 breach split makes the R4 switch date behaviourally near-certain **within a ~3-week window**; that the R3 tiered floors are observed rather than assumed; that "VERIFIED" and "NOT primary-verified" are compatible senses (C.4) |

### The precise missing evidence

1. **The decree documents themselves** — Kep-00003/BEI/04-2025 and Kep-00055/BEI/03-2023 — establishing
   effective dates, the ARB schedule, and the enumerated scope **from the issuing authority**.
2. **Any local behavioural evidence for the 2023-09-04 boundary.** Dataset B cannot supply it (starts
   2025-01-02). **Production `ohlcv` covers 2021-07-05 onward and therefore can.**

### A cheap, lawful closure path for item 2 — recommended, NOT executed

The same band-reconciliation that produced `OUTSIDE_BAND_INVESTIGATION_v1.json` can be run on `ohlcv` over
**2023-05 → 2023-11** to bound the R2→R3 boundary behaviourally, exactly as the R4 boundary is bounded.
**It reads `close` only, is a predictor-side rule check, and touches no forward return, no outcome, and no
event count for HYP-PM-0008.** It is therefore *not* the §11 feasibility gate and *not* an outcome
inspection. **This audit did not run it** — the brief's "no estimation beyond read-only structural coverage
already available" makes it a new computation requiring Owner authorization.

---

# PART E — UNRESOLVED CONTRADICTIONS

| # | Contradiction | Status |
|---|---|---|
| **E-1** | MIT's **I1 entry** asserts a confound with I2; MIT's **§4 graph** and **I2's own entry** do not | **Real documentary inconsistency in MIT.** Resolved *for this audit* in favour of the graph + I2 entry (A.1). Flagged for the taxonomy owner; **MIT not edited** |
| **E-2** | Semantic register `VERIFIED` vs LC-PM-0009 `NOT primary-verified` | **Dissolved as a contradiction** (different senses, C.4), but replaced by a narrower real defect: the register entry's **stated evidence does not meet its own house standard** and omits the artifact that would. **Register not modified** |
| **E-3** | PB §1.2 applied literally to I1 demands co-family with **both** I3 (P-A) and I12 (P-M) | **Unresolved — structural.** Satisfiable only by merging P-A and P-M (B.5), or by declining I-taxonomy assignment (Option 3b), or by refusal (Option 4). **Owner's to resolve** |
| **E-4** | D-048's "no I-taxonomy assignment" pattern vs **PB-2** "a narrow family is cheap and wrong" | **Unresolved — precedent vs principle.** The Owner accepted this pattern once (C-family). Whether it generalises is a governance judgment |
| **E-5** | MIT I1 "**RM0 · Conjectured. No literature card**" vs five existing LC-PM cards (incl. a Q4) | **Stale documentation**, not a substantive conflict (A.6). Flagged; not edited |

---

# PART F — EXACT OWNER DECISIONS STILL REQUIRED

**D-1 — one decision, four lawful forms** (Part B). Each is permanent and irreversible on registration:

1. **JOIN P-A** — satisfies the I1↔I3 confound; P-A denominator 1→2; leaves I12 unaddressed; scope tension.
2. **JOIN P-M** — satisfies the I12 modifier; P-M denominator 2→3; leaves the *stronger* I1↔I3 confound
   unaddressed; severe D1-vs-D2 scope conflict.
3. **NEW FAMILY** — **3a** with I1 named (**requires a formal governance amendment** disapplying PB §1.2)
   or **3b** without I-taxonomy assignment (**precedented by D-048**, needs a dated decision entry only).
4. **RETIRE / DO NOT REGISTER** — no slot, no amendment; the mechanism stays free-era and refinable.

*(B.5's P-M∪P-A merge is surfaced as the literal reading of §1.2; not tabled, not recommended.)*

**D-2 — one decision, three lawful forms:**

1. **Authorize primary retrieval** of the two decrees by a channel that is not 403-blocked (IDX IDXNet /
   member portal, a subscribed data vendor, or a manual download by the Owner), **and** authorize the
   `ohlcv` R2→R3 boundary reconciliation described in Part D.
2. **Accept the current evidence on the record** — secondary + behavioural — explicitly acknowledging B8
   exposure, and recording that the **2023-09-04 boundary rests on secondary sourcing alone**.
3. **Hold** HYP-PM-0008 until 1 is complete.

**Separately, two documentary defects are referred (no action taken):** E-1 (MIT I1↔I2) and E-2 (register
evidence field). Both are owner/maintainer calls; both registries and MIT are untouched.

---

# PART G — RECOMMENDATION: IS HYP-PM-0008 ELIGIBLE TO PROCEED TO D-3?

## **Not yet — but the remaining gap is narrow, specific, and cheap to close.**

**What improved materially during this audit:**

- **D-1's central obstacle was overstated in the draft and is now removed.** D-028 does **not** prohibit a
  new family (A.4); D-048 supplies a direct, three-month-old precedent for the exact act required (A.5).
  The blocker is a *choice*, not an impasse.
- **The confound set shrank.** I1↔I2 is not an authoritative relation (C-1); the live relation inside P-A is
  **I3 alone**, and the specific channel MIT names for it — *the next open* — is not traversed by a
  close-only specification.
- **D-2's substrate is far better evidenced than the draft assumed.** The R4 switch now has same-day
  secondary sourcing *and* independent behavioural corroboration from the exchange's own price record
  (13 sub-band moves before the date, 0 after). The register/LC-PM-0009 "contradiction" largely dissolves.

**Why eligibility still fails:**

1. **No primary source was obtained** (Part D). For an **M6** hypothesis this is not a formality: B8
   market-structure obsolescence is the bias the literature standard calls **fatal**, and the *entire*
   identification is the decree.
2. **The R3 boundary — the control arm — has zero local evidence.** Everything behavioural in the corpus
   sits on the R4 side. A wrong 2023-09-04 date silently imports ARB-15% sessions into the control window
   and biases the one contrast toward zero. This is the sharpest residual risk and the least-evidenced
   element in the design.
3. **D-3 is downstream by construction.** Deciding whether a non-capturable gross-only test is worth a
   permanent slot is only answerable once the slot's *identity* (D-1) and the test's *validity substrate*
   (D-2) are fixed. Taking D-3 first would be deciding the price of something not yet specified.

**Recommended sequence (not a decision):** close **D-2 item 2** first — the `ohlcv` R2→R3 reconciliation is
cheap, touches no outcome, and either confirms the control arm or kills the design before a family slot is
spent. Only then does D-1 become a decision about something whose validity is established, and only then
does D-3 have a well-posed subject. **Refusing at G1 remains the cheapest lawful outcome and costs nothing
** (`RESEARCH_PROGRAM.md` §5.2).

---

# FINAL STATUS

## **D-1 OWNER DECISION REQUIRED / D-2 NOT VERIFIED**

# CONFIRMATIONS

- **Zero empirical tests** — no return, band-contact event, limit-hit count, power figure, or outcome
  statistic was computed. The `OUTSIDE_BAND` and Kontan findings are **pre-existing artifacts and external
  documents read as evidence**, not computations performed here.
- **Zero backtests.**
- **Zero registry mutation** — `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`,
  `DECISION_LOG.md` unmodified. `MARKET_INEFFICIENCY_TAXONOMY.md` and
  `DATASET_B_SEMANTIC_REGISTER_v1.json` unmodified.
- **Zero database writes** — the only DB access in this session's D-1/D-2 work was none; Part C used JSON
  artifacts and source files on disk.
- **Zero `g1_config` mutation.**
- **Zero execution** — the G1 harness was not invoked.
- **D-3 untouched** — no judgment offered on whether the non-capturable leg is acceptable.
- **No option chosen on the Owner's behalf** for D-1.
- **No WAF circumvention attempted** against idx.co.id.

**Files changed by this task: one** — this report.
