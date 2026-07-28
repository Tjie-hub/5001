# Research Program Playbook

> **The operational companion to [[RESEARCH_PROGRAM_STANDARD]]. That document states what must be true of a Program. This one states what you do.**

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1) · **Layer:** L0 — Governance & Scope (procedural)
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version). **Does NOT supersede** [[RESEARCH_PROGRAM_STANDARD]] or [[RESEARCH_OS_MASTER_ROADMAP]] §3.
**Realized in v3:** Program P0 is the **worked instance, executed before the standard existed**; `gate_config` family scoping realizes one program's family. **No governance, cadence, or termination machinery exists.**
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **P4**, §5.2.6 (the family), **R7.5**, §6.4, §5.3 (F-distribution), P7
**Governance:** [[DECISION_LOG]] **D-021**, D-006, D-009

---

## 0. Scope

**Procedure only** (**PR-1**). What a Program must satisfy — objectives, family boundary rules PG-1…PG-17, termination criteria TC1–TC8 — is [[RESEARCH_PROGRAM_STANDARD]]. This document sequences it.

**The one thing to carry through every section:**

> **A Program *is* the multiplicity family boundary** ([[RESEARCH_PROGRAM_STANDARD]] §0.1). Everything procedural below is downstream of that. When you draw a Program boundary, **you are doing science, not project management** — and per **R7.5** you cannot redraw it later.

---

## 1. Initiation runbook (PG-A)

### 1.1 Before you write anything

**Ask the two questions that kill Programs for free.** Per §5.3, F1 is privileged: it costs no data, no custody, no multiplicity budget. **Program-level F1 is the cheapest refusal the institution can make.**

```
Q1. WHY HAS NOBODY ALREADY TAKEN THIS?                       (R16.2, R17)
    Name a barrier from §6.3's seven. Not "it's under-researched."
    ── No barrier ⇒ R17: DEFAULT PRESUMPTION IS THAT THE EFFECT
       DOES NOT EXIST. Someone with more capital and better data
       has already taken it. STOP HERE. Cost: zero.

Q2. WHY US?                                                  (§6.4, PG-2)
    Deviation is A PRIORI LEAST likely where capital is abundant
    and the mechanism is most studied.
    ── Targeting a well-studied class? State why we expect to
       succeed where abundant capital has not. "We'll be more
       rigorous" is not an answer.
```

> **Rule PB-1 (justified by §6.4, ECONOMIC_MECHANISM_TAXONOMY §8.2):** **Prefer M6 (market design) over M5 (behavioral). This inverts the field and it is correct.**
>
> **M6's barrier is structural** — a published rule that **no capital quantity removes.** **M5's barrier is processing cost**, which falls monotonically and which a single competitor removes. Per **R17** barrier quality *is* the persistence claim.
>
> M5 is the largest, most quotable, most accessible literature in finance. **Per §6.4 and P4 it is where the institution's scarce resource is most likely to be wasted.** A Program proposing M5 work carries the heavier burden **at initiation** — not at review, when the money is spent.

### 1.2 Draw the family — the irreversible step

**Do this before the objective, not after.** The boundary is the one decision you cannot revise.

```
1. LIST the [[MARKET_INEFFICIENCY_TAXONOMY]] entries in scope.

2. CHECK EVERY PAIR against MIT §4's interaction structure:

   ── CONFOUNDS?   Both predict the same observable.
                   ⇒ SEVERITY IS ZERO for discriminating them (R3).
                   ⇒ SAME FAMILY. Not negotiable.

   ── SUBSUMES / UPSTREAM?  One's mechanism produces the other's
                   observations. ⇒ Evidence is NOT INDEPENDENT.
                   ⇒ SAME FAMILY. Separate families understate BOTH.

   ── MODIFIES?    Explains persistence without originating.
                   ⇒ Testable only JOINTLY. Same family.

3. MERGE where any of the three holds.                        (PG-7)

4. DECLARE the family. It is now APPEND-ONLY and MONOTONIC.    (PG-3)
```

> **Rule PB-2 (justified by PG-6, R7.5):** **You cannot split this later.** Per **PG-6** a split reduces every resulting denominator — *R7.5 performed at the program level, where it looks like organization rather than manipulation.* If the Program is genuinely too broad, it is **terminated** and a new one initiated with a **family starting from zero** and **no inheritance of survivors.** A survivor cannot migrate to a smaller family. **It dies with its own.**
>
> **Draw it wide. A wide family is honest and expensive. A narrow one is cheap and wrong.**

### 1.3 The PG-A packet

```
[ ] Objective — names a MECHANISM or an INEFFICIENCY ENTRY.  (PG-1)
    NOT a return target. NOT a Sharpe target.
[ ] Scope — the entry set (= the family, from §1.2).
[ ] Capability class — Available Today / Obtainable Later / Future /
    Unrealistic, attested against [[DATA_FEASIBILITY_STUDY]].    (D-002)
[ ] Prior — with its §6.4 justification.                        (PG-2)
[ ] Family declaration — append-only from this moment.          (PG-3)
[ ] Success criteria — including "everything refuted" as a WIN.  (PG-11)
[ ] Termination criteria — TC1–TC8, declared NOW.               (PG-13)
[ ] Timebox — fixed. Never extended to rescue.                  (PG-14)
[ ] Review triggers — events, not calendar.                     (PG-9)
[ ] CRO approval.
```

> **Rule PB-3 (justified by PG-13, R7.4):** **Termination criteria are written before the work, or they are written to be unreachable.** Per **P4** a Program consumes the scarce resource continuously; *a Program that cannot be terminated consumes it forever.* Criteria authored later are authored **by someone who wants the Program to continue** — and per §7.3 that author's product cannot be wrong, which means it carries no information.

---

## 2. Running it

### 2.1 The default answer is no

**Most hypotheses proposed inside a Program should be refused at G1** ([[RESEARCH_PROTOCOL]] §5.2). Refusal costs nothing; registration costs a family slot **permanently** (**PG-3**).

```
Proposed hypothesis?
  ├── Missing any of §5.2's six?          ⇒ REFUSE. Not defer. (R14)
  ├── No persistence barrier?             ⇒ REFUSE. (R17)
  ├── Mechanism authored after looking?   ⇒ REFUSE. (§7.3, U3)
  ├── Test couldn't fail (power)?         ⇒ REFUSE. (R2)
  ├── Predicted effect < friction?        ⇒ REFUSE. F4, free. (PR-3)
  └── Survives all five?                  ⇒ REGISTER. Family +1. Forever.
```

### 2.2 Reviews are triggered, never scheduled

Per **PG-9** there is **no calendar review**. Per **P4**, *"if the proposed rule does not measurably reduce the probability that the institution believes something false, it fails P4"* — and a quarterly review, absent an event, does not. **It is activity that reads as diligence, which is worse than no activity, because it consumes the scarce resource while appearing to protect it.**

| Trigger | Do this |
|---|---|
| **Family milestone** (every N registrations) | **Re-derive C for every prior claim.** The denominator grew ⇒ **DG4** ⇒ **confidence fell, retroactively, for work you already did** |
| **Any VALIDATED** | Independent review before T9 — **██ blocked at N=1 ██** |
| **Market-structure change (D1)** | **Immediate. Highest priority.** **M6 mechanisms may have died** — decay is a **step function on rule change**, not a drift (**EV-11**) |
| **Confounding discovered** | **PG-7 merge may be mandatory.** Do it now — **it cannot be done later** (R7.5) |
| **Assumption failure (A1–A8)** | **DG8** — every dependent claim re-derives at the tier the surviving assumptions support |
| **Termination criterion met** | **§3. Mandatory. Not discretionary** |

### 2.3 Every review reports the F-distribution

Per **PG-10** and §5.3 — *the highest-value analysis the Failure Library enables.* See [[RESEARCH_QUALITY_STANDARD]] §3 for how to read it.

**The row that will be misread: "no failures."** It looks like the Program is working. Per §5.5 it means either the tests could not fail (**R2** ⇒ **no evidence**) or failures are not being recorded (**R12** ⇒ **every future DSR silently biased**). **Both are severe. Neither is visible from the results.**

---

## 3. Termination runbook

### 3.1 Termination is an obligation

> **PG-13:** termination is **mandatory** when a criterion is met — not discretionary, not deferrable.

**You will not want to.** By the time TC3 (family exhausted) or TC7 (timebox expired) fires, the Program has consumed months and you will have a specific, sincere, locally-reasonable argument for one more test.

> **Per PG-14 / §4.2:** *"the timebox is fixed ex ante and never extended to rescue a claim — extending it is R7.4 wearing a calendar. **A claim that fails its forward test fails; a claim that runs out of time is unproven, not proven.**"* **The same holds for a Program.**

### 3.2 The runbook

```
1. Name the criterion met (TC1–TC8). Exactly one.
2. Compute the FINAL FAMILY SIZE.        ← the Program's most durable
                                            product (PG-15)
3. Compute the F1–F9 distribution.       ← the finding about US (PG-17)
4. Transfer (§8 of the standard). Nothing is deleted.
5. CRO records termination.
6. STOP. Do not "wind down." Do not run one more test.
```

### 3.3 What survives, permanently

Per **PG-15/PG-16**, and none of it is optional:

| Artifact | Why it can never be deleted |
|---|---|
| **Family declaration + final N** | **Every successor inherits it.** Deleting it lets a future Program re-search this ground with a denominator of one (**R7.5**, **LIM3**) |
| **Failure entries** | **R12.** §4.4: an empty library *"silently biases every DSR the institution ever computes"* |
| **Literature Cards** | **LR-15** — including for dead conjectures. The reasoning that led somewhere wrong is institutional knowledge |
| **Refuted mechanisms** | Retained, annotated. A refuted sub-class is **a fact about the market** |
| **RM6 entries** | Permanent. **The record of what the market used to be** |
| **F1–F9 distribution** | **PG-17** — a first-class finding **about us**, not a post-mortem |

> **Rule PB-4 (justified by PG-15, §4.4):** **A terminated Program's most durable product is its denominator.** It is the number that tells every successor how much searching this ground has already absorbed. **Delete it and the next Program will believe it is the first — and per LIM3 nobody will be able to prove otherwise.**

### 3.4 Termination is not failure

Per **P7**: *"research is not a capital-accumulating activity. Validated knowledge is depreciating inventory, and the institution's steady-state obligation is replacement, not accumulation."*

Per **PG-11**: **a Program that competently refutes every entry in its scope has succeeded.** It mapped a boundary of efficiency — per §4.4, *the substantive scientific object of study.*

---

## 4. ██ Worked: what to do about G-6, before P1 starts ██

**A live, unresolved problem — not an illustration.** Recorded as **Gap G-6** ([[KNOWLEDGE_CORPUS_DELIVERY]] §5.2) and [[RESEARCH_PROGRAM_STANDARD]] §9.

### 4.1 The finding

Running §1.2 against the roadmap's Current Programs:

| Pair | Relation (MIT §4) | Consequence |
|---|---|---|
| **I5 ↔ I7** (inventory vs adverse selection) — spans **P1** and **P2** | **CONFOUNDS** — *the central identification problem of D2*. Both predict displacement-with-flow; they differ **only** in reversion vs permanence | **Severity is zero** for discriminating them. **Same family** |
| **I8 → I2** (reconstitution flow → closing auction) — both in **P3** | **UPSTREAM** — I8's mechanism produces I2's observations | Evidence **not independent**. Pooling inflates the sample |
| **I6 ↔ I12** (illiquidity vs capacity shielding) — both in **P2** | **NEAR-INSEPARABLE** (**LIM2** — no causal identification, only causal argument) | **Same family** |

### 4.2 What it means

> **The roadmap's program decomposition is organizational. The family decomposition is scientific. They do not currently coincide.**

Initiated as declared, **P1 and P2 would each understate their denominator** on the I5↔I7 confound. Per **§4.3** that is a process error that inflates the weight of every result in **both** — and per **LIM3** the resulting correction is wrong **in a direction nobody can subsequently measure.**

### 4.3 The decision, and why it cannot wait

```
OPTION A — Merge P1 + P2 into one family.
  ✓ Honest. The I5/I7 confound is real and the evidence is dependent.
  ✗ A large denominator. Fewer claims survive.
  ── This is the CORRECT cost, not an objection.

OPTION B — Keep them separate; declare the confound; test the
           separating prediction (reversion vs permanence, M-4) FIRST.
  ✓ If the separation is established EX ANTE, the families may be
    genuinely independent.
  ✗ Requires solving D2's central identification problem BEFORE
    the Programs that would study it. Per LIM2 we may not be able to.

OPTION C — Initiate as declared.
  ✗ PROHIBITED. Understates both denominators (PG-7).
```

> **Rule PB-5 (justified by R7.5, PG-6):** **This must be decided at initiation or not at all.**
>
> Per **R7.5** a family may **never be narrowed later**; per **PG-6** it may **never be split**. So the merge is available **once** — before P1 registers its first hypothesis — and **never again.** After that, the only remedy is **terminating both Programs and starting over with a family from zero**, forfeiting every survivor.
>
> **The window is open now. It closes at P1's first registration. Owner: CRO.**

---

## 5. ██ Programs at N=1 ██

Per [[RESEARCH_PROTOCOL]] §7 and **G-4**: **no Program can reach S10 at N=1.** T9 needs C3; a single-researcher claim caps at **C2** (**EV-9**).

**Run Programs anyway. Almost everything of value is still reachable:**

| Reachable at N=1 | Blocked |
|---|---|
| PG-A initiation, family declaration | **T9 → Accepted Knowledge** |
| **F1 kills at S2** — the highest-value activity | Any C≥C3 claim |
| Literature sourcing — the **only** blind mechanism supply | X3 replication |
| Populating MIT / EMT (11 of 12 entries are RM0/RM1) | G4 peer defense |
| Experiments to **C2**, honestly labelled | — |
| **The Failure Library** — the denominator every future claim inherits | — |
| **The F1–F9 distribution** — the institution's only self-measurement | — |

> **Rule PB-6 (justified by PG-11, R12, ADR-L1-007):** **Declare N=1 in the PG-A packet.** State that the Program's **maximum reachable outcome is C2** and that acceptance is **structurally unavailable** — not delayed.
>
> **Do not set success criteria the Program is forbidden to meet.** Per **PG-11** a Program that competently refutes its scope **has succeeded**; per **QS-4**, judging an N=1 institution by its accepted-knowledge count judges it by a number its own rules forbid it to increase. **That pressure, sustained, produces exactly one outcome: someone lowers the bar, and per LIM8 nobody can tell.**

---

## 6. Known gaps

| # | Gap | Consequence |
|---|---|---|
| **G-6** | **P1/P2/P3 family merges mandatory or probable** | **MAJOR, P0.** **Blocks P1 initiation.** §4. Window closes at first registration |
| **G-1** | **O14 Research Program is PROPOSED**, not declared | **A Program has no object to be recorded as. The family has nothing to be append-only *in*** — **PG-3 is currently prose** |
| **G-10** | Family size has **no enforcement** | **R7.5 by omission is undetectable** |
| **G-4** | **T9 unreachable at N=1** | §5. Closed by a second researcher |
| **G-15** | **No component implements program governance, cadence, or termination** | Entirely manual. **PG-13's mandatory termination has nothing to fire it** |

---

## 7. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §1 initiation | [[RESEARCH_PROGRAM_STANDARD]] §1–§3 (PG-A, PG-1…PG-7) | The rules |
| §1.1 the two questions | **R16.2, R17, §6.4** | §6.4 |
| §1.2 family drawing | **PG-3, PG-6, PG-7** · [[MARKET_INEFFICIENCY_TAXONOMY]] §4 | The interaction kinds |
| §2.2 triggers | **PG-9**, P4 · [[EVIDENCE_MODEL]] DG1–DG9 | The triggers |
| §3 termination | **PG-13…PG-17, TC1–TC8**, §4.2 | TC1–TC8 |
| §4 G-6 | [[RESEARCH_PROGRAM_STANDARD]] §9 · [[KNOWLEDGE_CORPUS_DELIVERY]] §5.2 | The finding |
| §5 N=1 | **PG-11, EV-9, LIM6, ADR-L1-007** · [[RESEARCH_PROTOCOL]] §7 | — |

**Invoked from:** [[RESEARCH_PROTOCOL]] §8. **Requires:** [[RESEARCH_PROGRAM_STANDARD]] (the rules) · [[MARKET_INEFFICIENCY_TAXONOMY]] §4 (the confound structure) · [[DATA_FEASIBILITY_STUDY]] (capability class).
