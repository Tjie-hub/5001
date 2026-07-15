# Research Program Standard

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see §0.4) · **Layer:** L0 — Governance & Scope
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version). **Does NOT supersede** [[RESEARCH_OS_MASTER_ROADMAP]] §3 (the P0–P6 register) — see §0.2.
**Realized in v3:** partial — Program P0 (v3 Edge Pipeline, NR7 family) is the **worked instance** of this standard, executed before the standard existed; `gate_config` family scoping realizes §3's family boundary in one program. **No v3 component implements program governance, review cadence, or termination.**
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **P4 (the scarce resource is the credibility of a claim)**, §5.2.6 (the multiplicity family), R7.5 (family reduction prohibited), §6.4 (where inefficiency is *a priori* likely), P7 (mortality), LIM3 (the denominator is estimable, not knowable)
**Governance:** [[TAXONOMY_AND_NAMING_STANDARD]] §2 (Program = *what we are researching*), [[DECISION_LOG]] **D-002, D-006, D-009, D-020**

---

## 0. Authority and scope

### 0.1 What a Program is — and the claim that makes this document necessary

Per [[TAXONOMY_AND_NAMING_STANDARD]] §2, a **Program** is *"a research track / body of work — what we are researching,"* numbered P0, P1, P2…, scoped by [[DATA_FEASIBILITY_STUDY]].

That is correct and incomplete. A Program is also — and **primarily, for scientific purposes** — this:

> **A Research Program is the multiplicity family boundary.**

[[01_SCIENTIFIC_FOUNDATION]] §5.2.6 requires every hypothesis to declare *"the denominator against which this test is one of N."* **R7.5** prohibits narrowing it after the fact: *"the denominator is part of the claim."* And per §4.3, *"the multiple-testing family denominator is part of the claim and not part of the analysis."*

**A family with no object is a family with no enforcement.** If the family is a number a researcher writes down, it is a number a researcher can revise — and per §7.3 a revised denominator is indistinguishable from an honest one by inspecting the result. The Program is the object that makes R7.5 structural rather than aspirational: hypotheses join a Program's family at G1 and **never leave** ([[RESEARCH_OBJECT_SCHEMA]] **OS-10**).

This is not theoretical. Program P0's NR7 BULL edge is *significant against zero* — CI [+0.32, +2.06] — **and its DSR collapses under its 42-cell family** ([[RESEARCH_OS_MASTER_ROADMAP]] §3). **The family was decisive; the effect was not.** Everything in this document exists to make that denominator un-narrowable.

### 0.2 Relationship to the roadmap register

[[RESEARCH_OS_MASTER_ROADMAP]] §3 declares Programs **P0–P6** and classifies them Current / Future / Out-of-scope (**D-006**: *nothing deleted, only classified*). **That register is canonical and unaltered here.** This document specifies *how a Program is governed*; it does not add, remove, or reclassify one.

### 0.3 What this document does **not** define — D-009 boundary

> **The Multiple-Testing Family *Policy* is deferred to P1 by owner decision (D-009) and is explicitly not a Phase-A blocker** ([[RESEARCH_OS_MASTER_ROADMAP]] §5).

The distinction is exact and this document stays on its side of it:

| | Owner | Status |
|---|---|---|
| **Family *boundary*** — which claims are in which family | **This document (L0 governance)** | Specified here |
| **Family *policy*** — how to correct for the family; FDR vs DSR vs Bonferroni; family-scoped effective-N | **P1 deliverable** | **D-009 — deferred. Not specified here** |

A boundary is a governance structure: *these hypotheses are one family.* A policy is a statistical method: *given N, adjust thus.* Defining the boundary does not pre-empt the policy and does not reopen D-009 — **but the policy will be uncomputable without the boundary**, which is why the boundary belongs at L0 and belongs now.

### 0.4 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready, NOT FROZEN**; one open condition, an external adversarial signature ([[DECISION_LOG]] **D-018/D-019**).

---

## 1. Objectives

> **Rule PG-1 (justified by P2, R18):** A Program's objective names a **mechanism class or an inefficiency entry** to investigate. It is **never** a return target, a Sharpe target, or a capital objective. *"Find alpha in small caps"* is not an objective; it is an aspiration with a search space attached, and per §7.1 an unbounded search yields an unbounded supply of significant results **whether or not any effect exists**.

A Program declares, at initiation:

| Element | Content | Basis |
|---|---|---|
| **Scientific question** | Which [[MARKET_INEFFICIENCY_TAXONOMY]] entries and [[ECONOMIC_MECHANISM_TAXONOMY]] sub-classes it investigates | R18 |
| **Scope** | The entry set — **this defines the family** (§3) | §5.2.6 |
| **Capability class** | Current / Future / Out-of-scope, from [[DATA_FEASIBILITY_STUDY]] | **D-002** (binding), D-006 |
| **Prior** | The institution's *a priori* expectation **and its §6.4 justification** | §6.4 |
| **Success criteria** | §6 — **declared before any work** | R5 |
| **Termination criteria** | §7 — **declared before any work** | **P4** |

> **Rule PG-2 (justified by §6.4, P4, LR-2):** The **prior** is mandatory and must cite §6.4. Deviation is *a priori* **least** likely where capital is abundant and the mechanism is most studied. A Program targeting a heavily-studied class **must state why this institution expects to succeed where abundant capital has not** — and per **R17**, absent a barrier the default presumption is that *the effect does not exist*.
>
> Per [[ECONOMIC_MECHANISM_TAXONOMY]] §8.2 this has a concrete and uncomfortable consequence: **M6 (market design) is the institution's strongest class and M5 (behavioral) its weakest** — the inverse of the field's attention. A Program proposing M5 work carries the heavier burden at initiation, not at review.

### 1.1 The prior is a governance instrument, not a formality

Per **P4**, *"the scarce resource is not data or compute; it is the credibility of a claim."* A Program is an allocation of that resource. Per §6.4, allocating it to well-studied, capital-rich mechanisms is *"a poor use of this institution's scarce resource."*

**The prior field is where a Program is killed before it costs anything** — the F1 of program governance. Per §5.3, F1 is privileged precisely because it consumes no data, no custody, and no multiplicity budget. **A Program refused at initiation is the cheapest refusal the institution can make**, and this standard's highest-value use is making those refusals routine.

---

## 2. Governance

### 2.1 Roles

Per [[RESEARCH_OPERATING_MODEL]] §5. **Its own header records the limitation: §5–§6 presuppose ≥3 distinct humans; the institution has one** (**LIM6**, ADR-L1-007).

| Role | Program responsibility |
|---|---|
| **CRO** | Approves initiation; **owns termination**; arbitrates scope; sole creator of Accepted Knowledge |
| **Research Architect** | Ensures the Program's family is declared and **append-only** (OS-10) |
| **Quant Researcher** | Authors hypotheses within the family |
| **Validation Reviewer** | **Independent adversarial review at every gate** |
| **Data Engineer** | Attests the capability class against [[DATA_FEASIBILITY_STUDY]] |

> **The live constraint, stated rather than designed around.** Per **EV-9/LIM6/LIM8**, a single-researcher institution cannot supply independent adversarial review; **C2 is the practical ceiling for every claim it produces**, and no Program can promote a hypothesis to ACCEPTED ([[HYPOTHESIS_LIFECYCLE]] **G-4**). This standard encodes the separation anyway — **not as aspiration, but because a standard encoding the current reality would make the deficit invisible**, and per **LIM8** an invisible deficit is indistinguishable from no deficit. **[[PHASE_A_FREEZE_CERTIFICATE]] v2.1 stands at this same wall** (D-019).

### 2.2 Gates

Programs inherit **G1–G4** ([[TAXONOMY_AND_NAMING_STANDARD]] §5) at the *hypothesis* level. This standard adds **two program-level gates**:

| Gate | When | Guard |
|---|---|---|
| **PG-A · Initiation** | Before any work | Objective names a mechanism (PG-1) · prior cites §6.4 (PG-2) · capability class attested (**D-002**) · **family declared** (§3) · success **and** termination criteria declared (§6, §7) · **CRO approval** |
| **PG-B · Review** | At each review (§5) | Family integrity verified (**append-only, OS-10**) · termination criteria evaluated (§7) · **F1–F9 distribution reviewed** (§5.2) |

---

## 3. The family boundary

### 3.1 The rule

> **Rule PG-3 (justified by R7.5, §5.2.6, OS-10):** A Program's `family_declaration` is **append-only and monotonically non-decreasing**. Every hypothesis registered under it joins the family at **G1/T4**. **No hypothesis ever leaves** — not on failure, not on withdrawal after registration, not on supersession, **not ever**.
>
> Per **R7.5** (*family reduction*): *"narrowing the multiple-testing family after the fact so a survivor clears. The denominator is part of the claim."*
>
> **The append-only rule makes reduction unexpressible**, which per **R6** is the only kind of prohibition that is a control rather than a statement of intent.

### 3.2 What is in the family

| In the family | Not in the family |
|---|---|
| Every hypothesis **REGISTERED** under the Program (T4) | Candidates **WITHDRAWN pre-G1** (T3) — nothing was risked |
| Every **FAILED** hypothesis | Observations (O11) — always E0, no claim (**OS-9**) |
| Every **VOID** hypothesis | Free-era refinements (T2) — unlimited, unrecorded |
| Every **SUPERSEDED** hypothesis **and its successor separately** (T12) | — |
| Every variant, specification, and re-run | — |

> **Rule PG-4 (justified by R15, R7.5):** A **re-run is a new family member.** Per **R15**, *"splitting one dead claim into variants until one survives"* is prohibited; the append-only family is what makes the split *visible in the denominator* rather than invisible in a revision. **N+1, never a retry of the Nth** ([[HYPOTHESIS_LIFECYCLE]] X6, HL-4).

> **Rule PG-5 (justified by §4.4, R12):** **Failures stay in the family — this is the rule's whole point.** Per §4.4, *"a Failure Library that is optional is a Failure Library that is empty, and an empty one silently biases every DSR the institution ever computes."* A family counting only survivors is a denominator counting only numerators, and per **LIM3** the resulting correction is wrong **in a direction no one can subsequently measure**.

### 3.3 Program boundaries and the family

Since the Program *is* the family, **drawing Program boundaries is a scientific act, not an administrative one.** Two rules follow, and they pull in opposite directions:

> **Rule PG-6 (justified by R7.5, PG-3):** **Splitting a Program splits its family — and is therefore prohibited after initiation.** A split reduces every resulting denominator: R7.5 performed at the program level, where it looks like organization rather than manipulation. If a Program is genuinely too broad, it is **terminated** (§7) and a new one initiated — with a **new family starting from zero registrations** and, critically, **no inheritance of the old family's survivors**. A survivor cannot migrate to a smaller family; it dies with its own.

> **Rule PG-7 (justified by §4.3, Taxonomy §4):** **Merging Programs merges families** — permitted, and sometimes **mandatory**. Where two Programs' entries `confound` or `subsume` each other ([[MARKET_INEFFICIENCY_TAXONOMY]] §4), their evidence is **not independent** and separate families **understate both denominators**. Per §4.3, evidential weight is a property of process; treating dependent tests as independent families is a process error that inflates both. **The CRO must merge on discovery of the dependence** — and per Taxonomy §4 the I5↔I7 and I2↔I8 relations are the live instances.

**These two rules make the boundary sticky in one direction only: families may grow and merge, never shrink or split.** That asymmetry is R7.5, restated at the governance layer.

---

## 4. Work packages

A Work Package is a **bounded unit of work with a deliverable**. It is an organizational convenience with **no scientific standing**: it does not bound a family (§3), does not carry evidence, and does not gate anything.

| Type | Deliverable | Standard |
|---|---|---|
| **WP-L · Literature** | Cards + a synthesized mechanism | [[LITERATURE_RESEARCH_STANDARD]] |
| **WP-M · Mechanism** | A sub-class specification (8 fields) | [[ECONOMIC_MECHANISM_TAXONOMY]] |
| **WP-H · Hypothesis** | A registered hypothesis (G1) | [[HYPOTHESIS_LIFECYCLE]] T4 |
| **WP-D · Data** | A Dataset with a fidelity limit | [[DATA_FEASIBILITY_STUDY]] |
| **WP-F · Feature** | A frozen Feature (G2) | [[FEATURE_COMPUTATION_GRAPH]] |
| **WP-E · Experiment** | A Result | [[HYPOTHESIS_LIFECYCLE]] T5–T7 |
| **WP-V · Validation** | A Validation Report | [[RESEARCH_VALIDATION_FRAMEWORK]] |

> **Rule PG-8 (justified by PG-3):** **A Work Package never bounds a family.** Only a Program does. Attaching a family to a WP would let a researcher declare a small denominator by declaring a small package — **R7.5 through the back door**, and the more dangerous route precisely because a Work Package looks like project management rather than science.

---

## 5. Review cadence

### 5.1 Event-driven, not calendar-driven

> **Rule PG-9 (justified by P4):** Reviews are triggered by **events that could change what the institution believes**. There is **no calendar review.**
>
> Per **P4**: *"if the proposed rule does not measurably reduce the probability that the institution believes something false, it fails P4"* — and a quarterly review, absent an event, does not. **It is activity, and activity that reads as diligence is worse than no activity**, because it consumes the scarce resource while producing the appearance of protecting it.

| Trigger | Scope |
|---|---|
| **Family milestone** | Every N registrations (declared at PG-A) — **the denominator has grown; every prior claim's C-axis has moved** (**DG4**) |
| **Any VALIDATED** | Before T9. Independent review (LIM6) |
| **Any ACCEPTED** | Full Program review — capital now depends on it |
| **Market-structure change (D1)** | **Immediate.** **M6 mechanisms may have died — decay is a step function on rule change** ([[ECONOMIC_MECHANISM_TAXONOMY]] §6, EV-11) |
| **Termination criterion met** | **Immediate and mandatory** (§7) |
| **Confounding discovered** | Immediate — **PG-7 merge may be mandatory** |
| **Assumption failure (A1–A8)** | Immediate — **DG8**; every dependent claim re-derives |
| **Calendar** | **None** |

### 5.2 The review's primary output

> **Rule PG-10 (justified by §5.3):** Every review reports the Program's **F1–F9 failure distribution**.
>
> Per §5.3: *"**The distribution of failures across F1–F9 is therefore a diagnostic of the institution itself**, and is the highest-value analysis the Failure Library enables."*

| Distribution | Diagnosis |
|---|---|
| **Clustered at F1** | **Operating efficiently.** Claims die before consuming data, custody, or multiplicity budget |
| **Clustered at F2–F4** | *"Spending its scarcest resources to learn things it could have reasoned out."* **The Program's mechanism work is too weak — a defect in the institution, not in the market** |
| **Clustered at F6** | **Reproducibility is broken.** Every claim is at risk of X0 |
| **Clustered at F9** | **Not a defect.** Mechanisms decayed. Expected under P7 — *"research is not a capital-accumulating activity"* |
| **No failures** | **The most alarming state.** Per §5.5 the institution is configured to be *slow to believe and fast to disbelieve*; a Program with no failures is not testing severely (**R2**) — its tests are not capable of failing, and per R2 they are therefore producing **no evidence at all**, regardless of what they report |

**The "no failures" row is the one that will be misread**, because a Program with no failures looks like a Program that is working.

---

## 6. Success criteria

> **Rule PG-11 (justified by R12, P3):** A Program **succeeds** by producing **justified knowledge — positive or negative.** Per **R12**, *"a competent refutation is a first-class institutional product, of equal standing to a validated mechanism."*
>
> **A Program that competently refutes every entry in its scope has succeeded**: it mapped a boundary of efficiency, which per §4.4 is *"the substantive scientific object of study."*

| Outcome | Success? | Why |
|---|---|---|
| Accepted Knowledge (E5+/C3+/X3+) | ✅ | The rare case |
| **Every entry competently refuted** | ✅ | **A mapped boundary + a denominator no future Program can hide from** (§4.4) |
| Mechanisms specified; entries at RM1–RM3 | ⚠️ Partial | Hypothesis material; **not knowledge** (Rule I-2) |
| Effects found, no mechanism | ❌ | **E1 — a category error, not a weak result** (R10, R18) |
| Effects found, mechanism retro-fitted | ❌ | **U3 — a counterfeit** (§7.3) |
| Nothing conclusive; resources exhausted | ❌ | **Terminate** (§7) |
| **Profitable but unexplained** | ❌ | **R7.1 — profit is not evidence.** *"Both fortune and error produce them"* |

> **Rule PG-12 (justified by R13, EV-5):** Success **never** scales with effort, duration, cost, elegance, or how much the institution wants the claim. Per **R13**: *"Sunk research cost is not evidence."* Per **EV-5**, the most dangerous variant is **capital already deployed** — it inverts the causal order the institution exists to protect ([[01_SCIENTIFIC_FOUNDATION]] §0.1: *research produces knowledge; capital consumes it; the reverse dependency is prohibited*).

---

## 7. Termination criteria

### 7.1 Termination is an obligation

> **Rule PG-13 (justified by P4):** **Termination criteria are declared at PG-A, before any work**, and termination is **mandatory** when one is met — not discretionary, not deferrable.
>
> Per **P4**, the scarce resource is the credibility of a claim, and a Program consumes it continuously. **A Program that cannot be terminated consumes the scarce resource forever.** Per **R7.4**, extending a Program past its declared criterion to rescue it is threshold migration — **at the program level, where it is hardest to see and easiest to justify.**

| # | Criterion | Basis |
|---|---|---|
| **TC1** | **Every entry in scope refuted** | **Success** (PG-11), not failure |
| **TC2** | **Capability class degraded** — required data proved unobtainable | **D-002** — feasibility is a *scientific* constraint (ADR-L1-006), not a budget one |
| **TC3** | **Family exhausted** — declared N reached without a survivor | **R7.5** — extending N is family manipulation deferred |
| **TC4** | **Prior falsified** — the §6.4 justification proved wrong | PG-2 |
| **TC5** | **Mechanisms structurally untestable** at our fidelity | **LIM1** — e.g. [[ECONOMIC_MECHANISM_TAXONOMY]] M2.3, untestable absent cancellation data |
| **TC6** | **F1–F9 clustered at F6** — reproducibility broken | **R19** — every claim at risk of X0 |
| **TC7** | **Timebox expired** | **§4.2 — the forward-evidence timebox is fixed ex ante and never extended to rescue a claim** |
| **TC8** | **Superseded** by a merged Program (PG-7) | Family dependence discovered |

### 7.2 The timebox rule

> **Rule PG-14 (justified by §4.2, R7.4, U12):** A Program's timebox is **fixed at PG-A and never extended to rescue it.**
>
> Per §4.2, in full: *"the timebox for forward evidence is fixed ex ante and never extended to rescue a claim — extending it is R7.4 (threshold migration) wearing a calendar. A claim that fails its forward test fails; a claim that runs out of time is **unproven, not proven**."*
>
> The same holds for a Program. **A Program that runs out of time is unproven, not promising.**

### 7.3 Termination is not failure

Per **P7**, *"research is not a capital-accumulating activity. Validated knowledge is depreciating inventory, and the institution's steady-state obligation is replacement, not accumulation."*

A terminated Program that **recorded its failures** produced: a mapped boundary (§4.4), a denominator every future Program inherits (LIM3), and an F1–F9 datum about the institution (§5.3). **That is output.**

> **Rule PG-15 (justified by R12, §4.4):** A terminated Program's family, failures, and lineage are **retained permanently**. Deleting them *"corrupts every future multiplicity calculation by hiding the denominator"* (§4.4). **A terminated Program's most durable product is its denominator** — the number that tells every successor how much searching this ground has already absorbed.

---

## 8. Knowledge transfer

> **Rule PG-16 (justified by §8.2 institutional argument):** A Program's output is **institutional**, never personal. Per §8.2: *"Knowledge held only in an individual's working memory or unrecorded environment is not institutional knowledge; it is tribal knowledge with an expiry date attached to a person. It cannot be audited, inherited, defended, or safely retired. **It is a liability that reads as an asset on the institution's books.**"*

At termination or completion, a Program transfers — **or it did not happen**:

| Artifact | Destination | Basis |
|---|---|---|
| **Family declaration + final N** | Permanent. **Every successor inherits it** | **R7.5**, LIM3 |
| **Failure entries (F1–F9)** | [[FAILURE_LIBRARY_SCHEMA]]. **Never deleted** | **R12**, §4.4 |
| **Literature Cards** | Permanent, **including for dead conjectures** | LR-15 |
| **Mechanism specifications** | [[ECONOMIC_MECHANISM_TAXONOMY]]. **Refuted sub-classes retained** | §9 there |
| **Maturity transitions** | [[MARKET_INEFFICIENCY_TAXONOMY]]. **RM6 permanent** | §6 there |
| **Accepted Knowledge** | O9, with a **live decay monitor and a pre-committed retirement rule** | P7, EV-11, EV-12 |
| **Lineage** | Complete. **Any break voids the claim** | **R19**, OS-12 |

> **Rule PG-17 (justified by §5.3, R12):** The **F1–F9 distribution** transfers as a **first-class finding about the institution**, not as a project post-mortem. It is per §5.3 the highest-value analysis the Failure Library enables, and it is the only artifact here that is about *us* rather than about the market.

---

## 9. Program register

The register is [[RESEARCH_OS_MASTER_ROADMAP]] §3 (**canonical, unaltered — D-006**). This standard's obligations, applied to it:

| Program | Class | Obligation under this standard |
|---|---|---|
| **P0 · v3 Edge Pipeline (NR7)** | ✅ Delivered | **The worked instance — executed before the standard existed.** Its 42-cell family collapse is §0.1's evidence that PG-3 is load-bearing. **Its family declaration is retroactively binding: no successor may narrow it** (R7.5) |
| **P1 · Order-Flow Imbalance (PROXY)** | 🟢 Current | PG-A required. **Owns the D-009 family policy.** Scope: [[MARKET_INEFFICIENCY_TAXONOMY]] I5, I7 — **and per Taxonomy §4 the I5↔I7 confound is the identification problem of D2; PG-7 merge with P2 must be evaluated at initiation** |
| **P2 · Liquidity / Toxicity** | 🟢 Current | PG-A required. Scope: I6, I12. **I6↔I12 near-inseparable (LIM2) — a single family** |
| **P3 · Close/Auction Dislocation (PROXY)** | 🟢 Current | PG-A required. Scope: I2, I3, I8. **I8 is causally upstream of I2 — PG-7 mandatory: one family, not three** |
| **P4 · Informed-Flow** | 🟡 Immature | **Blocked on LIM4** — history maturity (3.5 mo). **Time is the only remedy.** PG-A must state the timebox (PG-14) |
| **P5 · L3 Microstructure** | 🔵 Future | **TC2 pre-met** — L3 LOB not held. **Retained, not initiated** (D-006) |
| **P6 · Latency/HFT** | ⚫ Out of scope | Documented as excluded. **Retained** (D-006) |

> **§9's most consequential finding.** Three of four Current Programs have **mandatory or probable PG-7 merges** on the confound structure of [[MARKET_INEFFICIENCY_TAXONOMY]] §4. Initiated as separate families, **P1/P2/P3 would each understate their denominator** — and per §4.3 the resulting corrections would be wrong in a direction **LIM3** says is unmeasurable. **The roadmap's program decomposition is organizational; the family decomposition is scientific, and they do not currently coincide.** Recorded as **Gap G-6** ([[KNOWLEDGE_CORPUS_DELIVERY]] §5) — a real finding this standard produced on contact with the existing register.

---

## 10. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §0.1 Program = family boundary | [[01_SCIENTIFIC_FOUNDATION]] §5.2.6, **R7.5**, §4.3 | R7.5 |
| §0.3 boundary ≠ policy | **D-009** (policy deferred to P1) | The deferral |
| §1 objectives, PG-2 prior | **§6.4**, R17, P4, R18 | §6.4 |
| §3 family, PG-3…PG-7 | R7.5, R15, §4.4, [[RESEARCH_OBJECT_SCHEMA]] OS-10 | OS-10 |
| §5 cadence, PG-9 | **P4** (anti-bureaucracy) | P4 |
| §5.2 F1–F9 diagnostic | **§5.3** | The mode definitions |
| §6 success, PG-11 | **R12**, P3, R10, R7.1 | R12 |
| §7 termination, PG-13/14 | **P4**, §4.2 (timebox), R7.4, D-002 | §4.2 |
| §8 transfer, PG-16 | **§8.2** (institutional argument) | §8.2 |
| §9 register | [[RESEARCH_OS_MASTER_ROADMAP]] §3, **D-006** | The register |

**Upstream:** [[DATA_FEASIBILITY_STUDY]] (D-002, capability class) · [[MARKET_INEFFICIENCY_TAXONOMY]] (scope + confound structure) · [[TAXONOMY_AND_NAMING_STANDARD]] §2 (the term *Program*).
**Downstream:** [[HYPOTHESIS_LIFECYCLE]] (T4 joins the family) · [[RESEARCH_OBJECT_SCHEMA]] §4.5 (O14, **PROPOSED**) · [[EVIDENCE_MODEL]] (the family determines C) · [[LITERATURE_RESEARCH_STANDARD]] §9.1 (initiation triggers a search).
