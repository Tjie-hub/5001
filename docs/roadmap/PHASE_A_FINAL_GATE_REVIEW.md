# Phase A — Final Gate Review

**Version:** 1.0 · **Status:** Gate review record · **Date:** 2026-07-16 · **Layer:** L0
**Reviewer:** Chief Research Architect
**Scope:** G-8 and G-9 closure. **No architecture reviewed, revisited, or introduced.**
**Assessed revision:** `069afc3`
**Constraints honored:** L1 untouched · D-019 untouched · no new architecture · no resolved contradiction reopened.

---

## 0. Two premise corrections

**Neither is a redesign; both change the answer.**

### 0.1 "Treat Phase A as frozen"

Phase A is **not frozen**, and no document may say it is:

> **[[RESEARCH_OS_MASTER_ROADMAP]] §112 / [[PHASE_A_FREEZE_CERTIFICATE]] §144:** *"**Phase A is certified-ready but NOT FROZEN.** No document may describe it as frozen until sign-off is recorded and certificate v3.0 issues naming the reviewer, date, and revision frozen."*

**The instruction is honored as a *working stance* — do not reopen settled decisions — which is exactly how the constraint list itself glosses it** (*"assume every previous architectural decision is frozen unless a logical inconsistency is formally proven"*). **It is not honored as a governance claim.** This document therefore treats the architecture as settled and the gate as open. Writing "Phase A is frozen" would violate the rule G-8 exists to protect.

### 0.2 ⚠️ **G-9 is not a Phase A gate**

The brief frames the final gate as *"G-8 & G-9."* **The Phase A exit checklist has fifteen items. Fourteen are ✅. Exactly one is open:**

> `- [ ]` **Independent adversarial sign-off** on this checklist (Validation Reviewer, **not the author**).

**G-9 appears nowhere on it.** G-9 gates two *other* things:

| Gate | Blocked by G-9? | Authority |
|---|---|---|
| **Phase A freeze** | **NO** | Checklist §7 — G-9 is not an item |
| **Research OS v1.0 freeze** | **YES** | **D-022 §9.3** — *"v1.0 must not be frozen while G-9 is open, even if D-019 is signed tomorrow"* |
| **Any claim above E3** | **YES** | §2.4 / R6 — unenforced custody makes evidential state unknowable |

> **Consequence: Phase A's transition to Phase B requires G-8 alone.** G-9 is real, urgent, and **on a different gate**. Conflating them would hold Phase A hostage to a mechanism its own checklist never asked for.

---

## 1. Gate Assessment

| Gate | Mandatory before Phase B? | Completable during Phase B? | Deferrable? |
|---|---|---|---|
| **G-8** — external sign-off | **NO** — but mandatory before **Phase A freeze** | **YES** | **NO** |
| **G-9** — Dataset Custody mechanism | **NO** | **YES — and should be** | **NO** |

### 1.1 G-8 — mandatory for the *freeze*, not for *Phase B*

**Mandatory before Phase A freeze: definitionally.** G-8 *is* the last checklist item. Phase A freezes when the checklist is discharged; the checklist is discharged when G-8 signs. This is not an argument — it is the identity of the gate.

**Not mandatory before Phase B starts.** The precedent is direct and the owner set it twice:

> **D-020 R-d** — work proceeds on a **candidate baseline**, each document declaring its inheritance of an unsigned L1, **void pending re-derivation, not grandfathered** (§0.4) if review alters the class sets. **D-021 applied the same.** Twenty-four files were authored under it and are committed at `069afc3`.

**L3 is the same class of dependency.** Refusing it now would reverse a decision the owner has made twice, and per **D-019 alternative B** — *"the External Validation Reviewer does not yet exist, so it stalls indefinitely"* — blocking is the option already rejected.

**Not deferrable.** Deferral means "Phase A never freezes." Per **LIM8**, an institution operating on a permanently-unsigned foundation is **indistinguishable from one operating on a signed one** — which is the precise condition G-8 exists to dispel.

**One check I expected to bite, and it does not:** does letting L3 proceed enlarge G-8's review scope? **No.** Per [[TAXONOMY_AND_NAMING_STANDARD]] §3, *"L0, L1, L2 together constitute Phase A."* **L3 is outside Phase A.** L3 work does not grow what the reviewer must read. **Only further L0/L1/L2 amendment does** — see Condition 2 (§3.3).

### 1.2 G-9 — completable during Phase B, and should be

**Not mandatory before Phase B.** The concern in [[PROTOCOL_LAYER_DELIVERY]] §6.4 was that L3 must not be designed before custody enforcement is **decided** — because *"designing L3 without deciding it bakes the unenforceable model in."*

> **It has been decided. D-022 closed it.** [[CUSTODY_MODEL]] §5 specifies Dataset Custody in full: the Partition object, C-SEALED, the release policy (§5.4), receipt-then-release (**CU-14**). **L3 realizes that model; it does not need the model built to specify against it.**
>
> **The distinction the earlier finding turned on was *decide* vs *build*. The decision is closed. Only the build is open.**

**Should be built during Phase B, not after.** Per [[PROTOCOL_LAYER_DELIVERY]] §5.1, G-9 is **the only blocking gap the institution can close by itself** — it needs no external party, no hire, no signature. It is the one item on this review with no dependency on anyone.

**Not deferrable.** Per **D-022 §9.3**, v1.0 cannot freeze while G-9 is open — and per §2.4, until it closes, *"unenforced custody produces a system whose evidential state cannot be known even by its own operators."* Every E3+ claim produced in the interim inherits that.

---

## 2. Risk Analysis

### 2.1 G-8 — Independent adversarial sign-off

| | |
|---|---|
| **Purpose** | Discharge **LIM6/LIM8**: the author cannot establish that his own corpus is sound, because a self-certified corpus and a genuinely certified one are **indistinguishable on inspection**. G-8 is the only act that separates them |
| **Risk if omitted** | **The institution's epistemic state remains unknowable to itself, permanently.** Not "the corpus might be wrong" — *"we cannot tell whether it is."* Every downstream layer inherits an unverified foundation |
| **Probability of latent defect** | **HIGH — and measured.** The author's own red-team found 5 findings; the ARB upheld 1. **Four were inference errors an independent reviewer likely would not have made — and the author made them while explicitly trying not to.** The one that survived (RT-4) was a false claim made through motivated reading. **This is direct evidence LIM8 is operative, not theoretical** |
| **Impact** | **MODERATE, not catastrophic.** Rework is documentary (§0.4: void pending re-derivation). No capital is deployed; **G-4 independently forbids Accepted Knowledge at N=1.** The corpus cannot yet hurt anyone |
| **Mitigation (in force)** | D-020 R-d candidate-baseline declarations on every dependent document; §0.4's non-grandfathering rule; a review package already prepared |
| **Owner** | **External Validation Reviewer** (D-019). **Sourcing is the CRO's.** |
| **Exit criteria** | Certificate **v3.0** issues, naming reviewer, date, and revision frozen (§144). Checklist item 15 → ✅ |

### 2.2 G-9 — Dataset Custody mechanism (RFC-1)

| | |
|---|---|
| **Purpose** | Convert **R6** from statement to control: *"a prohibition that relies on a researcher's discipline is a statement of intent, not a control"* |
| **Risk if omitted** | **Every E3+ claim rests on a control that does not exist, and the breach is invisible by construction.** A contaminated OOS window is **bit-identical** to a clean one |
| **Probability of silent contamination** | **HIGH and rising.** `walk_forward_split()` is a function returning `{'train','test'}`. Nothing prevents reading `['test']`; nothing records that it was read. **Probability approaches 1 as researcher-hours accumulate — and it rises the moment a second researcher joins**, which is the same event that closes G-8 and G-4 |
| **Impact** | **SEVERE and unrecoverable.** Per §2.4 the conversion leaves the data's appearance unchanged. **There is no forensic recovery** — a spent window cannot be identified after the fact, so *every* claim over that corpus is retrospectively unknowable, not just the contaminated one |
| **Mitigation (currently)** | **None mechanical.** [[EXPERIMENT_STANDARD]] §3.2 is procedure — and per R6 that means there is no control. **The mitigation is the work** |
| **Owner** | **Research Architect.** **No external dependency** |
| **Exit criteria** | RFC-1 M1–M3 landed ([[CUSTODY_AMENDMENT]] §7): custody log; partition objects; **release gated behind receipt-then-release (CU-14)** — direct OOS reads no longer possible. Re-run [[CUSTODY_PROPAGATION_AUDIT]] |

### 2.3 The interaction the two gates have — and it is not additive

> **G-9's risk is a function of headcount, and G-8's remedy is headcount.**

**Closing G-8 by hiring raises G-9's probability**: a second researcher doubles the hands that can read an unsealed OOS window, and the new hire has *no* institutional habit to restrain them.

> **∴ RFC-1 should land before or with the hire, not after it.** This is the review's one sequencing constraint, and it falls out of the two gates' interaction rather than from either alone.

---

## 3. Minimal Closure Plan

**Zero new documents. Zero redesign. Zero scope expansion.**

### 3.1 G-8 — closure is a *sourcing* problem, not a work package

**Everything required already exists.** [[PHASE_A_REVIEW_PACKAGE]] **v1.1** is written, canonical, and committed.

| Step | Work | Owner |
|---|---|---|
| **1** | **Re-point the package at `069afc3`** — it currently references the pre-amendment corpus. **One line.** Per §144 the reviewer signs *"the revision frozen"*, so naming it now fixes the target | Program Director |
| **2** | **Enumerate the post-`de98c17` delta** for the reviewer: 24 files, D-020…D-023. **A list, not a document — the DECISION_LOG already holds the rationale** | Program Director |
| **3** | **Engage a reviewer.** ⟵ **the actual gate** | **CRO** |
| **4** | Reviewer signs. Certificate **v3.0** issues | Reviewer |

> ### 3.2 ⚠️ The criterion is *"not the author"* — not *"external"*
>
> **[[RESEARCH_OS_MASTER_ROADMAP]] §108, verbatim:** *"Independent adversarial sign-off on this checklist (Validation Reviewer, **not the author**)."*
>
> **D-019 *named* the owner "External Validation Reviewer." The *criterion* it was attributed against says "not the author."** These are not the same requirement, and the difference is the closure plan:
>
> **A second researcher joining the institution satisfies "not the author" for Phase A — because they did not author it.**
>
> And per [[RESEARCH_PROTOCOL]] §7.3, a second researcher **closes G-4** (T9 → Accepted Knowledge becomes reachable). **One person closes two blocking gates.**
>
> **The residual, stated rather than hidden:** per **PV-3**, at N=2 reciprocal review satisfies *reviewer ≠ author* but not *reviewer has no stake* — **LIM6 is relieved at N=2, not repealed.** **For Phase A specifically the residual is zero**: the new hire has no stake in a corpus they did not write. **Their first act is the moment of maximum independence they will ever possess** — and per [[REPLICATION_STANDARD]] §2.4 that window closes in roughly two weeks, permanently, as they accumulate authorship.
>
> **∴ If a hire is the chosen route, G-8 is their day-one task — not a backlog item.** Deferring it to month two converts a genuinely independent reviewer into a compromised one, at no saving.

### 3.3 G-9 — one work package, already scoped

**[[CUSTODY_AMENDMENT]] §7 already specifies it. Nothing new is needed.**

| Stage | Work | Breaks? |
|---|---|---|
| **M1** | `custody_events` + `custody_receipts`, append-only. **Additive; nothing reads them yet** | No |
| **M2** | Materialize `dataset_partitions` from the existing deterministic scheme. **`walk_forward_split` keeps working unchanged** | No |
| **M3** | **Route OOS reads through a release function that writes the receipt first (CU-14).** ⟵ **this is the gate** | **Yes — deliberately.** Direct OOS reads must stop being possible |

> **M0 is already done** (custody classes declared in ROM v2.0 §3.2). **M4/M5 are not required for G-9** and are excluded as scope expansion.
>
> **The rule for M3, from CU-14:** **receipt-then-release, never release-then-receipt.** A crash between read and receipt would erase the record of a spent window while the window stays spent. **Receipt-first fails safe; release-first fails silent — and silent failure is the entire threat model.**
>
> **A migration that stops at M2 is worse than none:** it builds a custody log that records nothing, and per **LIM8** a log that always reports compliance is indistinguishable from compliance.

### 3.4 What is deliberately excluded

| Excluded | Why |
|---|---|
| RFC-2…RFC-8 | Not on either gate |
| G-1 (O10–O14, D-005 amendment) | MAJOR, not blocking. **Blocks L3's completion, not Phase A's freeze** |
| G-6 (P1/P2/P3 family merges) | **Blocks P1's first registration, not Phase A.** Window closes at that registration (PB-5) |
| M4 / M5 (Publication, Blind partition) | Beyond G-9's exit criteria |
| Any new document | **The package exists. The RFC is scoped. Writing more would be the failure P4 names** |

---

## 4. Go / No-Go

> # GO WITH CONDITIONS

**Phase A may transition to Phase B upon closure of G-8 alone.**

### Rationale

**The architecture is done.** Zero open contradictions: five raised adversarially, four disproven by deduction, one (RT-4) proven and corrected in four sentences (**D-023**). L1 has not been touched since `222d57f`; D-019's package is intact — a promise made in D-022 §1.2 and independently verified by D-023.

**The two remaining items are not architecture defects, and they are not the same kind of thing:**

- **G-8 is a signature.** It needs a person. **No amount of work by this institution can produce it** — that is ADR-L1-007's finding, not a scheduling problem.
- **G-9 is a mechanism.** It needs code. **It is the only blocking gap the institution can close alone**, and it needs nobody's permission.

**Neither blocks Phase B's start.** The candidate-baseline precedent (D-020 R-d) is established, applied to 24 committed files, and L3 is the same class of dependency. G-9's *decision* closed at D-022; only its *build* is open, and L3 specifies against the model rather than the mechanism.

### Conditions

| # | Condition | Owner |
|---|---|---|
| **1** | **RFC-1 (M1–M3) lands before or with any second researcher.** Headcount is G-8's remedy and G-9's risk multiplier (§2.3) | Research Architect |
| **2** | **Review package re-pointed at `069afc3`; post-`de98c17` delta enumerated.** One line + one list | Program Director |
| **3** | **L0/L1/L2 amendment pause during the review window** — otherwise the scope moves under the reviewer. **L3 work is unaffected: L3 is outside Phase A** | CRO |
| **4** | **L3 documents declare candidate-baseline inheritance** per D-020 R-d — void pending re-derivation, not grandfathered | Research Architect |
| **5** | **If G-8 is closed by hiring: sign-off is the hire's day-one task**, with a replication (REPLICATION_STANDARD §2.4). **Both windows close in ~2 weeks and never reopen** | CRO |

### Why not GO

Phase A cannot freeze without G-8, and **G-8 is not in the institution's gift.** An unconditional GO would assert a freeze the corpus forbids describing.

### Why not NO-GO

**No architectural defect remains, and neither open item is one.** NO-GO would block Phase B on a signature that does not exist and a mechanism that Phase B does not require — reversing D-020's precedent to no benefit and stalling indefinitely, which is **D-019 alternative B**, already rejected.

---

## 5. Verdict, stated plainly

> **Phase A's architecture is complete and its gate is open by one signature.**
>
> **Phase B may start now.** **Phase A freezes when someone who is not the author reads the checklist and signs it.**
>
> **The most useful finding in this review is that both remaining gates may be closed by one hire — and that the hire's first two weeks are the only window in which their independence is worth anything.** After that they are an author, and per **LIM8** their signature becomes indistinguishable from mine.
