# Research Quality Standard

> **Invoked continuously. Read on day 1 — [[RESEARCH_PROTOCOL]] §2. What "good" means here is not what you expect.**

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1) · **Layer:** L2 — Research Architecture (procedural)
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** partial — `failure_registry` supplies §3's F-distribution material; `research.tracking` supplies §2's provenance material. **No v3 component computes a quality measure.**
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **P4 (credibility is the scarce resource)**, **§4.3 (evidential weight is a property of process, not of the number)**, **§5.3 (the F1–F9 distribution is a diagnostic of the institution itself)**, R11, R12, R13, LIM8
**Governance:** [[DECISION_LOG]] **D-021**

---

## 1. The thesis

> **Quality is a property of the process, never of the result.**

This follows directly from **§4.3**:

> *"The same numerical result carries different evidential weight depending on how it was produced. A t-statistic of 3.0 from a single pre-registered test and a t-statistic of 3.0 selected from two hundred searched variants are not the same evidence, and **no property of the number itself distinguishes them**."*

**If evidential weight is not recoverable from the result, then neither is quality.** They are both properties of what produced it.

### 1.1 The four corners

| | **Good process** | **Bad process** |
|---|---|---|
| **Positive result** | **Excellent** — and rare | **The most dangerous output the institution can produce** |
| **Negative result** | **Excellent** — and normal (**R12**) | Worthless, and it still corrupts the denominator |

> **The top-right cell is the one to understand.** A validated edge produced by a bad process is worse than no edge, because the institution will **act on it** — allocating capital and, worse, allocating its scarce credibility (**P4**). A bad process producing a *negative* result merely wastes time. A bad process producing a *positive* result damages the one asset the institution cannot rebuild.

### 1.2 What quality is not

| ✗ Not a quality signal | Rule |
|---|---|
| The result was positive | §4.3 — weight is not in the number |
| The effect was large | R11 |
| The p-value was small | R11 — a t-stat of 3.0 from 200 searches is not a t-stat of 3.0 |
| It took a long time | **R13** — *sunk research cost is not evidence* |
| It was technically sophisticated | **R7.6** — *"the model is too complex to explain"* reports our ignorance, not the market's structure |
| It was profitable | **R7.1** — *both fortune and error produce returns* |
| Everyone agrees | **LR-2** — consensus is a reason for a *lower* prior (§6.4) |
| It has not been refuted | **EV-8** — nothing promotes by silence. That is the *absence* of a demotion event |

---

## 2. The quality attributes

Six. Each is checkable from the record alone — **which is the test of whether it is real.** An attribute requiring you to ask the author is not an attribute; it is a conversation.

### Q1 · Blindness
> **Was the mechanism authored in ignorance of the result?**

`authored_at` predates every experiment in `blind_to` (**OS-6**). Sourced from literature where possible — **the only supply blind by construction** ([[LITERATURE_RESEARCH_STANDARD]] §0.1).

**Why it is first:** per **§7.3**, the mechanism requirement does its work **only** if the mechanism is blind. Fail Q1 and everything downstream is a counterfeit — *"indistinguishable from the genuine article by inspection"*.

### Q2 · Riskedness
> **Could this have gone the other way?**

Ex-ante criterion frozen (**R5**). Power/MDE showing the test could fail (**R2**). Refutation condition in one sentence (**R14**).

**Per P5:** *evidence is the outcome of a test that could have gone the other way.* Fail Q2 and there is no evidence — **not weak evidence. None.**

### Q3 · Honest denominator
> **Is the family the true one?**

Every variant, re-run, dead sibling counted. Never narrowed (**R7.5**). Confounded Programs merged (**PG-7**).

**Per §4.3:** *the denominator is part of the claim.* Fail Q3 and the correction is wrong **in a direction LIM3 says is unmeasurable.**

### Q4 · Severity
> **Would this test have detected the error had there been one?**

A severity argument **in prose** (**R3/EV-3**). Tested against **rivals**, not against zero (**M-3**). Reversion-permanence cell declared (**M-4**).

**A test against zero is not severe.** Almost nothing is zero.

### Q5 · Reproducibility
> **Does the claim exist?**

X2 minimum. Provenance complete. **Per P8, incomplete ⇒ the claim was never made** (**R19**).

### Q6 · Recorded failure
> **Did the death get written down?**

Failure Entry, exactly one F-mode, attribution **defended** against auxiliaries (**R1**).

**Per §4.4:** *a Failure Library that is optional is a Failure Library that is empty, and an empty one silently biases every DSR the institution ever computes.*

> **Rule QS-1 (justified by P4):** **All six are necessary; none is sufficient; and there is no partial credit.** Per **P4** each exists to *"measurably reduce the probability that the institution believes something false."* Q1–Q6 do not average. **A claim failing Q1 does not score 5/6 — it scores zero**, because a counterfeit mechanism makes the other five measurements of a counterfeit.

---

## 3. The institutional quality metric

**Individual claims are not the unit of quality. The institution is.** And it has exactly one instrument for measuring itself:

> **§5.3:** *"**The distribution of failures across F1–F9 is a diagnostic of the institution itself**, and is the highest-value analysis the Failure Library enables."*

| Distribution | Diagnosis |
|---|---|
| **Clustered at F1** | **Operating efficiently.** Claims die before spending data, custody, or multiplicity budget. **This is the target** |
| **Clustered at F2–F4** | *"Spending its scarcest resources to learn things it could have reasoned out."* **The mechanism work is too weak. A defect in us, not in the market** |
| **Clustered at F6** | **Reproducibility is broken.** Every claim is at risk of X0 |
| **Clustered at F9** | **Not a defect.** Mechanisms decayed. Expected under P7 — *research is not a capital-accumulating activity* |
| **No failures** | **The most alarming state of all** |

### 3.1 Why "no failures" is the alarm

Per **§5.5** the institution is deliberately configured to be **slow to believe and fast to disbelieve**. A body of work with no failures is not a body of work that is going well:

- Either the tests **could not have failed** (**R2**) — in which case they produced **no evidence at all**, whatever they reported;
- Or failures **are not being recorded** (**R12**) — in which case every future DSR is silently biased and per **LIM3** the bias is unmeasurable.

**Both are severe. Neither is visible from the results.** A clean record and a dishonest one look identical — which is why the F-distribution, not the success rate, is the metric.

> **Rule QS-2 (justified by §5.3, R12):** **Report the F1–F9 distribution at every Program review** (**PG-10**). It is the only measurement the institution takes **of itself** rather than of the market, and it is the one that says whether anything else it measures can be trusted.

---

## 4. Anti-patterns

Each is a move that **feels like quality**. That is what makes them worth naming.

| # | Anti-pattern | What it actually is |
|---|---|---|
| **A1** | **Robustness theatre** — twenty sensitivity checks after the fact | Twenty more family members (**R7.5**), presented as rigour. **It grows the denominator while appearing to shrink the doubt** |
| **A2** | **Mechanism prose** — a long, elegant economic story | Length is not blindness. Check `authored_at`, not eloquence (**§7.3**) |
| **A3** | **Statistical escalation** — a fancier test on a failed claim | **R15.** A new test is a new family member. The claim is still dead |
| **A4** | **Cost-model optimism** — friction assumptions that flatter | **F4 deferred, not avoided.** And per **DG5** a later honest revision voids the claim anyway |
| **A5** | **Regime rescue** — "it works in the right regime," discovered after | **R7.4** with **A5** (weakest assumption) underneath |
| **A6** | **The literature shield** — "this is well-documented" | **CR6, LR-14.** Literature never lowers a bar. And per **LR-2** a large literature is a reason for a **lower** prior |
| **A7** | **Provenance debt** — "I'll write it up after it works" | **Per P8, until it is written there is no claim** to write up. And the environment is already gone |
| **A8** | **Silent withdrawal** — quietly dropping a claim that failed | **R12 violation.** The denominator loses a member; **every future correction is wrong by an unknown amount** |
| **A9** | **Confidence inflation from tier** | **EV-4.** C is capped by E, **never raised by it**. E5/C1 is a legitimate and common state |
| **A10** | **Self-review recorded as review** | **LIM8, PV-1.** The record is indistinguishable from a genuine one — **and that is the harm** |

> **A8 is the quietest and the worst.** Nobody notices a claim that simply stops being mentioned. Per §4.4 it *"corrupts every future multiplicity calculation by hiding the denominator"* — and it does so by an amount **no one can subsequently measure** (**LIM3**). **A withdrawn claim that was registered stays in the family. Forever.**

---

## 5. Self-audit

### 5.1 The honest caveat

> **Rule QS-3 (justified by LIM8):** **You cannot audit yourself, and this section cannot fix that.**
>
> **LIM8:** self-certification is *epistemically indistinguishable from genuine certification.* A self-audit that passes and a self-audit that was performed sloppily produce the **same artifact.**
>
> **What self-audit is for:** catching the errors you would have caught anyway, earlier and cheaper. **What it is not for:** establishing that your work is sound. **Only §6 does that, and §6 needs a second person.**

### 5.2 Before you claim anything

```
[ ] Q1 Blindness      — `authored_at` predates `blind_to`? Sourced from
                         literature, or authored here after looking?
[ ] Q2 Riskedness      — could this test have failed? Power analysis?
[ ] Q3 Denominator     — count again. Include the ones you don't want to.
[ ] Q4 Severity        — written in prose? Against rivals, not zero?
[ ] Q5 Reproducibility — could a stranger execute the spec?
[ ] Q6 Failure         — recorded, one mode, attribution defended?

[ ] Which of the six R7 prohibited inferences am I closest to?
[ ] Which of R15's five rescues do I most want to perform right now?
    ── Write the answer down. It is data about the institution (PR-2).
```

### 5.3 The two questions that actually work

Most self-audit is theatre. These two are not:

> **1. "If this result had come out the other way, would I be treating this test as valid?"**
>
> If no, the test was not the test. You have already migrated a threshold in your head (**R7.4**) — you simply have not written it down yet.

> **2. "What would I say if a colleague showed me this?"**
>
> You know. You have known since §5.2. Per **R4** the burden is on the proponent, and **right now that is you.**

---

## 6. Quality at N=1

**Everything above is available to you alone except §2's Q4 verification and any C≥C3 claim.** Per [[RESEARCH_PROTOCOL]] §7, at N=1 you can do all of it and you cannot *certify* any of it.

> **Rule QS-4 (justified by R12, PG-11, ADR-L1-007):** **At N=1, quality is measured by the F1–F9 distribution and by Q1–Q6 compliance — not by outcomes**, because the outcome that would validate the work (**Accepted Knowledge**) is **structurally unavailable** (**G-4**).
>
> **A year of competently recorded F1 refutations is a high-quality year.** Per **R12** and §4.4 it maps a boundary of efficiency — *"the substantive scientific object of study"* — and it builds the denominator every future claim inherits. Per **PG-11**, *a Program that competently refutes every entry in its scope has succeeded.*
>
> **Judging an N=1 institution by its accepted-knowledge count judges it by a number its own rules forbid it to increase.** That pressure, applied for long enough, produces exactly one outcome: someone lowers the bar and per **LIM8** nobody can tell.

---

## 7. Known gaps

| # | Gap | Consequence |
|---|---|---|
| **G-14** | **No component computes an F1–F9 distribution**, though `failure_registry` holds the data | §3's metric — *"the highest-value analysis the Failure Library enables"* — is **currently not computed** |
| **G-13** | Q1 (`authored_at`/`blind_to`) has **no enforcement**; O2's fields are proposed (**G-1**) | **Blindness is currently an attestation, not a control.** Per **R6**, *"a statement of intent, not a control"* — and Q1 is the attribute the other five depend on |
| **G-4** | Q4 verification requires a non-author | **§6.** N=2 closes it |

---

## 8. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §1 quality = process | **§4.3, R11** | §4.3's argument |
| §2 Q1–Q6 | R5, R2, R3, R7.5, R19, R12, §7.3 | The rules |
| **§3 F-distribution** | **§5.3** | The mode definitions |
| §4 anti-patterns | R7, R13, R15, LR-2, EV-4, LIM8 | R7's list |
| §5 self-audit | **LIM8**, R4 | LIM8 |
| §6 N=1 | **PG-11, R12, ADR-L1-007** · [[RESEARCH_PROTOCOL]] §7 | — |

**Invoked from:** [[RESEARCH_PROTOCOL]] §2 (day 1), continuously.
**Related:** [[PEER_REVIEW_STANDARD]] (§2's attributes are what a reviewer attacks) · [[RESEARCH_PROGRAM_PLAYBOOK]] (§3's distribution is a review deliverable) · [[EVIDENCE_MODEL]] (E/C/X).
