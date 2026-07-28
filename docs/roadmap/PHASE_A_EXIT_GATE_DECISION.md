# D-024 — Phase A Exit Gate Decision

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent governance record · **Layer:** L0 — Governance & Scope
**Owner:** Chief Research Architect · **Date:** 2026-07-16 · **Supersedes:** — (initial version)
**Decision ID:** **D-024** · **Log entry:** [[DECISION_LOG]] §2
**Authoritative basis:** [[PHASE_A_FINAL_GATE_REVIEW]] (2026-07-16). **This document records a decision; it performs no review.**
**Assessed revision:** `069afc3`
**Constraints honored:** L1 unmodified · D-019 unmodified · no new architecture · no new gates · no new requirements · no scope expansion.

---

## 1. Executive Decision

| | |
|---|---|
| **Phase A architecture status** | **COMPLETE.** Zero open architectural contradictions. Five raised adversarially ([[RED_TEAM_REVIEW_2026-07-15]]); four disproven by deduction ([[ARB_ADJUDICATION_2026-07-15]]); one (**RT-4**) proven and corrected in four sentences (**D-023**) |
| **Phase A exit status** | **OPEN — by exactly one item.** [[RESEARCH_OS_MASTER_ROADMAP]] §7 lists **fifteen** exit items. **Fourteen are ✅. One is open: G-8** |
| **Repository status** | **Committed locally at `069afc3`; not pushed.** Corpus durable. **L1 unmodified since `222d57f`**; [[PHASE_A_REVIEW_PACKAGE]] v1.1 byte-for-byte intact — the preservation promise made at [[CUSTODY_AMENDMENT]] §1.2 and independently verified by **D-023** |
| **Remaining blocking items** | **G-8** — one independent adversarial sign-off. **This is the sole Phase A exit blocker.** |
| | **G-9** — Dataset Custody mechanism. **Not a Phase A exit gate** (§2, Correction A). Blocks the **Research OS v1.0 freeze** and every claim above **E3** |

> **Phase A's architecture is complete and its gate is open by one signature.**

---

## 2. Corrections to Previous Interpretation

**Both corrections arise from reading the canonical text rather than from any new analysis. Neither changes the architecture.**

### Correction A · G-9 is **not** a Phase A exit gate

**Demonstration — [[RESEARCH_OS_MASTER_ROADMAP]] §7, the Phase A Exit Checklist, in full:**

| # | Item | State |
|---|---|---|
| 1 | Data Feasibility Study authored; Data Capability Matrix is the scope constraint | ✅ |
| 2 | Reconciliation with v3 written; single canonical roadmap declared | ✅ |
| 3 | Taxonomy standard authored; "Phase" retired for OS structure | ✅ |
| 4 | Worked end-to-end example proves the object model composes | ✅ |
| 5 | Programs classified Current vs Future | ✅ |
| 6 | Object model split into Core vs Extension | ✅ |
| 7 | Folder structure migrated to concern-based layout | ✅ |
| 8 | Repository baseline commit | ✅ |
| 9 | Future governance outlined | ✅ |
| 10 | L1 domain de-overlap | ✅ |
| 11 | Architecture rationale recorded (ISO 42010 §5.7) | ✅ |
| 12 | Canonical docs cross-referenced to v3 mechanisms | ✅ |
| 13 | AQ-1 resolved | ✅ |
| 14 | Version headers on all canonical documents | ✅ |
| **15** | **Independent adversarial sign-off** (Validation Reviewer, **not the author**) | **☐ OPEN** |

> **G-9 appears nowhere on this checklist. Custody is not an exit criterion of Phase A, and never was.**

**Which governance milestones G-9 actually blocks:**

| Milestone | Blocked by G-9? | Governing text |
|---|---|---|
| **Phase A exit / freeze** | **NO** | §7 — G-9 is not an item |
| **Research OS v1.0 freeze** | **YES** | **D-022 §9.3:** *"Research OS v1.0 must not be frozen while G-9 is open, **even if D-019 is signed tomorrow**"* |
| **Any claim above E3** | **YES** | **§2.4:** *"unenforced custody produces a system whose evidential state cannot be known even by its own operators"* |

**Why the correction matters.** Treating G-9 as a Phase A exit gate would hold Phase A hostage to a mechanism its own checklist never required — **and would delay a signature that G-9 does not affect.** The two gates are genuinely open; they are not open on the same door.

### Correction B · The reviewer criterion is **"not the author"**, not "external reviewer"

**Governing document — [[RESEARCH_OS_MASTER_ROADMAP]] §7, item 15, quoted verbatim:**

> *"**Independent adversarial sign-off** on this checklist (Validation Reviewer, **not the author**). Undischargeable by the author by construction — [[01_SCIENTIFIC_FOUNDATION]] LIM6, ADR-L1-007. Package ready: [[PHASE_A_REVIEW_PACKAGE]]."*

**What D-019 said — and what it was doing:**

> *"The **only** remaining condition is independent adversarial review, and it is now formally attributed to an **External Validation Reviewer** rather than left implicitly pending on the author."*

> **D-019 assigned an *owner*; §7 states the *criterion*.** The word "External" was doing the work of *"not the author"* — its stated purpose was *"rather than left implicitly pending on the author"*, i.e. to stop the condition decaying into an author obligation. **It was never an additional requirement of institutional exteriority.** D-019's own alternative C confirms the reading: *"**Human independent reviewer.** The only alternative that satisfies the requirement."* — independent, not external.

**Practical consequence:**

> **A second researcher joining the institution satisfies criterion 15, because they did not author the corpus.** And per [[RESEARCH_PROTOCOL]] §7.3, a second researcher independently closes **G-4** (T9 → Accepted Knowledge becomes reachable for the first time).
>
> **One person closes two blocking gates.**

**The residual, recorded rather than dissolved.** This correction reads the criterion; it does not relax it. Per **LIM6**, *"adversarial review is structurally compromised at this scale"* — and an employed reviewer carries an **institutional** stake that criterion 15's text does not address, even though their **authorship** stake in Phase A is nil. **No new requirement is introduced:** [[PHASE_A_FREEZE_CERTIFICATE]] §144 **already** requires v3.0 to name *"the reviewer, the date, and the revision frozen."* **Naming the reviewer's relationship to the institution is within that existing obligation, and per LIM8 it must be recorded, because it cannot be recovered from the certificate's outputs afterward.**

---

## 3. Gate G-8

| | |
|---|---|
| **Objective** | Discharge **LIM6/LIM8**. The author cannot establish that his own corpus is sound, because per **LIM8** *a self-certified corpus and a genuinely certified one are indistinguishable on inspection*. **G-8 is the only act that separates them** |
| **Owner** | **The reviewer** — a Validation Reviewer who is not the author (§2, Correction B). **Sourcing the reviewer is the CRO's.** |
| **Required evidence** | **[[PHASE_A_REVIEW_PACKAGE]] v1.1 — already written, canonical, committed.** Plus the post-`de98c17` delta: 24 files, **D-020…D-023**, whose rationale is already in [[DECISION_LOG]]. **No new document is required** |
| **Acceptance criteria** | The reviewer reads [[PHASE_A_FREEZE_CHECKLIST]] and adversarially attempts to refute it. **A pass is the *failure of a competent attack*, not the absence of one** — per **PV-4**, *"a review that finds nothing wrong is not a passed review; it is a failed attack"* |
| **Completion event** | **[[PHASE_A_FREEZE_CERTIFICATE]] v3.0 issues**, naming the reviewer, the date, and the revision frozen (§144). Checklist item 15 → ✅. **Phase A is frozen at that moment and not before** |

### 3.1 Why one independent adversarial reviewer satisfies the gate

**Because the gate asks for exactly one thing, and it is a signature — not a quantity of review.**

Per **§2.2**, confirmation and refutation are asymmetric:

> *"Refutation: institutional cost **low** — accepted on first competent demonstration. Standard of proof: **a single sound argument**."*

**The gate's content is: has anyone who is not the author competently attacked this and failed?** That question is answered by **one** such person. A second adds evidence; it does not change the gate's state — the gate is defined by the *existence* of independent scrutiny, not its volume.

**And the corpus already knows a single reviewer is sufficient in principle and necessary in fact:** per **ADR-L1-007** the institution *declares* the single-researcher review deficit rather than absorbing it. **G-8 closes that declaration.** It does not attempt to make the corpus correct; it makes the corpus's correctness **knowable** — which per **§2.4** is precisely what N=1 cannot do for itself.

> **One reviewer converts "we cannot tell whether this is sound" into "one competent adversary tried and failed." That is the entire content of the gate, and it is exactly what one person delivers.**

---

## 4. Interaction Between G-8 and G-9

### 4.1 The gates are not additive

**They are coupled through headcount, in opposite directions:**

| | |
|---|---|
| **G-8's remedy** | **A person.** Per §2 Correction B, the most available route is a second researcher |
| **G-9's risk driver** | **People.** `walk_forward_split()` is a function returning `{'train','test'}`. Nothing prevents reading `['test']`; nothing records that it was read |

> **∴ Closing G-8 raises G-9's probability.** A second researcher doubles the hands that can read an unsealed out-of-sample window — **and the new hire has no institutional habit to restrain them**, precisely because their unfamiliarity is what makes them a good reviewer.
>
> **Treating the gates as two independent items to be closed in any order is therefore wrong. Closing one worsens the other.**

### 4.2 Sequencing requirement

> **RFC-1 — or any equivalent custody mechanism — should land *before* or *together with* onboarding the second researcher.**

**Reasoning:**

1. **G-9's failure mode is unrecoverable.** Per **§2.4**, a contaminated window *"leaves its appearance unchanged."* A spent window **cannot be identified after the fact** — so contamination is not a bug to be found and fixed later; **it retrospectively makes every claim over that corpus unknowable, not just the contaminated one.**
2. **G-9's mitigation is currently nil.** [[EXPERIMENT_STANDARD]] §3.2's receipt is a *procedure a person performs*, and per **R6** *"a prohibition that relies on a researcher's discipline is a statement of intent, not a control."*
3. **RFC-1 has no external dependency.** Per [[PROTOCOL_LAYER_DELIVERY]] §5.1, **G-9 is the only blocking gap the institution can close by itself.** It needs no hire, no signature, no permission.
4. **∴ The cheap, unblocked work should precede the expensive, blocked work** — not for efficiency, but because the expensive work **is the trigger** for the risk the cheap work removes.

**This is not a new gate and not a new condition.** It is a constraint on *how* Condition 1 (§7) is executed, derived from the two gates' interaction and recorded here so it is not discovered afterward.

---

## 5. Phase A Scope Boundary

### 5.1 Formal statement

> **[[TAXONOMY_AND_NAMING_STANDARD]] §3, verbatim:**
>
> *"**L0, L1, L2 together constitute "Phase A" in the old scheme** — the Scientific Foundation *plus* the architecture that supports it. Per owner decision, the Research OS architecture stays *within* Phase A (as L2), not pushed to Phase B."*

| Layer | In Phase A? |
|---|---|
| **L0** — Governance & Scope | **YES** |
| **L1** — Scientific Foundation | **YES** |
| **L2** — Research Architecture | **YES** |
| **L3** — Data Ontology | **NO — outside the Phase A review boundary** |
| L4–L8 | **NO** |

### 5.2 Implication for future amendments

| Action | Effect on the gate |
|---|---|
| **Amend L0, L1, or L2 *before* sign-off** | **Moves the review target.** The reviewer signs *"the revision frozen"* (§144) — so the amendment must be enumerated in the delta they receive |
| **Amend L0, L1, or L2 *after* sign-off** | **Reopens governance.** Certificate v3.0 names a frozen revision; changing what it certifies requires a superseding certificate. **This is Condition 3** (§7) |
| **Author L3 at any time** | **No effect on G-8.** L3 is outside the boundary. **It does not enlarge what the reviewer must read** |

> **This is the boundary's practical value: Phase B work does not grow the Phase A review.** The two proceed in parallel without interfering — which is why Condition 4 (§7) can hold G-9 and L3 outside the exit gate without weakening it.

---

## 6. Decision vs Build

### 6.1 The distinction, recorded

| | Status | Authority |
|---|---|---|
| **Dataset Custody *Model*** — the architecture | **DECIDED and CLOSED** | **D-022.** [[CUSTODY_MODEL]] §5 specifies it in full: the **Dataset Partition object**, **C-SEALED**, the release policy (§5.4), **receipt-then-release (CU-14)**, and the Blind partition (**CU-13**, as corrected by D-023) |
| **Dataset Custody *Mechanism*** — the engineering | **NOT IMPLEMENTED** | **RFC-1** = **G-9.** Scoped at [[CUSTODY_AMENDMENT]] §7: M1 custody log · M2 partition objects · **M3 receipt-gated release** |

### 6.2 Why this does not reopen Phase A architecture

**Because the earlier concern was about *deciding*, and the decision is closed.**

[[PROTOCOL_LAYER_DELIVERY]] §6.4 held that custody enforcement must be **decided** before L3 is designed, because *"designing L3 without deciding it bakes the unenforceable model in."* **That condition is discharged: D-022 decided it.** L3 now specifies **against a model that exists**; it does not require the mechanism to exist in order to do so.

**The architecture is unaffected by the build for three reasons:**

1. **The model is complete and unambiguous.** RFC-1 implements [[CUSTODY_MODEL]] §5; it does not extend, reinterpret, or negotiate it.
2. **Building it changes no canonical document.** Per **§5.2** above, only an L0/L1/L2 amendment touches the gate. RFC-1 is code.
3. **Failing to build it does not falsify the model.** Per **R6**, an unenforced rule is *"a statement of intent, not a control"* — **which is a statement about the institution's compliance, not about the architecture's correctness.** The model correctly specifies a control that does not yet exist. **That is a true architecture and a false institution — and the amendment says so** ([[CUSTODY_AMENDMENT]] §5: *"A model of a control is not a control"*).

> **∴ G-9 is engineering debt against a closed architectural decision. It is real, it is urgent, and it is not a Phase A architecture defect.**

---

## 7. Final Decision

> # GO WITH CONDITIONS

**Phase A architecture is complete. Phase A exit is gated by G-8 alone. Phase B may proceed.**

### Conditions

| # | Condition | Owner |
|---|---|---|
| **1** | **Complete G-8.** One independent adversarial sign-off; certificate v3.0 issues naming reviewer, date, and revision frozen. *Execution constraint per §4.2: if closed by hiring, RFC-1 lands **before or with** the hire, and sign-off is the reviewer's first task — per [[REPLICATION_STANDARD]] §2.4 their independence window is roughly two weeks and does not reopen* | **CRO** (sourcing) · Reviewer (act) |
| **2** | **Preserve Phase A artifacts.** Corpus durable at `069afc3`. **L1 unmodified since `222d57f`; [[PHASE_A_REVIEW_PACKAGE]] v1.1 intact.** Both preserved through D-020…D-023 and verified by D-023 | Program Director |
| **3** | **No modifications to L0/L1/L2 without reopening governance.** Before sign-off: the amendment must be enumerated in the reviewer's delta. After sign-off: a superseding certificate is required (§5.2) | **CRO** |
| **4** | **G-9 proceeds independently as implementation work and is not a prerequisite for entering Phase B.** Per §2 Correction A it is not a Phase A exit gate; per D-022 §9.3 it remains a **v1.0 freeze blocker** and per §2.4 it bounds every claim above **E3** | Research Architect |

### Rationale

**The architecture is done and the remaining items are not architecture.** G-8 is **a signature** — no work by this institution can produce it (**ADR-L1-007**). G-9 is **a mechanism** — no one else's permission is required to build it. Neither blocks Phase B: the candidate-baseline precedent (**D-020 R-d**) is established, was applied to 24 committed files, and L3 is the same class of dependency.

**Not GO:** Phase A cannot freeze without G-8, and G-8 is not in the institution's gift. An unconditional GO would assert a freeze the corpus forbids describing (**§144**).

**Not NO-GO:** no architectural defect remains, and neither open item is one. NO-GO would block Phase B on a signature that does not exist and a mechanism Phase B does not require — reversing D-020's precedent to no benefit, and stalling indefinitely, which is **D-019 alternative B**, already rejected.

---

## 8. Status

**Phase A is *certified-ready but NOT FROZEN*** ([[PHASE_A_FREEZE_CERTIFICATE]] §144, [[RESEARCH_OS_MASTER_ROADMAP]] §112). **No document may describe it as frozen until sign-off is recorded and certificate v3.0 issues.** This document does not.

**Phase A freezes when someone who is not the author reads the checklist and signs it.**
