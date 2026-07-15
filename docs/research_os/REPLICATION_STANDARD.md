# Replication Standard

> **Invoked from [[RESEARCH_PROTOCOL]] §2 (week 1) and §4 (S9). If you joined this month, §2 is the most valuable thing you will do this year — and the window closes in about two weeks.**

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1) · **Layer:** L2 — Research Architecture (procedural)
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** `research.tracking` (run_id, dataset_fingerprint, git_commit) supplies the X2 material. **No v3 component records a replication as an event** — O13 is proposed, not declared (**G-1**).
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **§8 (P8, R19 — reproducibility is constitutive)**, **§8.3 (conclusion-invariance, not bit-identity)**, **LIM5 (single-institution replication is weak replication)**, §8.2 (the three arguments)
**Governance:** [[DECISION_LOG]] **D-021** · [[EVIDENCE_MODEL]] §4 (X0–X4), §7

---

## 0. Scope and the one thing to understand first

**Procedure only.** *What* reproducibility requires is [[EVIDENCE_MODEL]] §4/§7 (X0–X4) and L1 §8. Per **PR-1** this document sequences those.

> **P8 — an irreproducible result is not a weak result. It is not a result.**
> *"A scientific claim is a claim about a procedure and what it yields. If the procedure cannot be re-executed to yield the same thing, then no claim was made — an event occurred on a computer once, and was described."*

**This is stronger than the engineering case and the strength is the point.** Engineering says reproducibility is *valuable* — audit, debugging, onboarding. Science says it is **the difference between a claim and an anecdote.** It is not a quality attribute of a result; it is **the condition of the result existing at all.**

---

## 1. What you are testing

**Not the bytes. The claim.**

Per **§8.3**, an independent researcher, given the hypothesis specification, the methodology, and the identified data, must reach the **same scientific conclusion**:

- the same **sign**
- the same **rejection or non-rejection** of the null
- the same **order of magnitude** of effect

> **Rule RP-1 (justified by §8.3, ADR-L1-005):** **Bit-identity is not required and must not be demanded.** It is *sufficient* for reproducibility but **not necessary**, and it is construction-hard: cross-hardware floating-point determinism is defeated by SIMD reassociation, FMA contraction, and BLAS thread-count nondeterminism. Per **ISO 42010 §5.3**, feasibility-of-construction is a required concern, and an architecture that gates on a construction-hard property it never framed has not framed it (**AQ-4**).
>
> **A replication that fails only on the last decimal place has succeeded.** A replication that reproduces every digit but reaches the opposite conclusion — because the specification was ambiguous and you both guessed — has **failed**, however identical the numbers.

> **Recorded inconsistency (G-7).** [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] S5 demands bit-identity. **L1 §8.3 does not, and declines to.** Per **ADR-L1-008** the corpus records rather than resolves. **Follow L1.**

---

## 2. Procedure — you are replicating

### 2.1 The rule that makes it real

> **Rule RP-2 (justified by §8.3):** **Read the specification. Do not read the code.**
>
> The claim is that *the specification yields the conclusion*. If you read the implementation, you inherit its choices — including the undocumented ones — and you are no longer testing the specification. **You are testing whether the code runs twice.** That is **X1**, and per [[EVIDENCE_MODEL]] §4 X1 *"proves the author's machine is deterministic"* and is worth nothing alone.

### 2.2 The steps

```
1. RECEIVE:  hypothesis specification · methodology · identified data
             · cost model · family declaration
             (NOT the code. Not the notebook. Not a walkthrough.)

2. RECORD:   what you received, before starting. If you later need
             something that was not in the packet, THAT IS THE FINDING —
             record it (§2.3).

3. IMPLEMENT: from the specification alone. Make your own choices where
             the spec is silent. WRITE DOWN EVERY CHOICE YOU MADE.
             ← these are the spec's gaps, and they are the product

4. EXECUTE:  once. Full provenance (X2 set).

5. COMPARE:  sign? rejection/non-rejection? order of magnitude?
             NOT digits.

6. RECORD:   a Replication (O13) — succeeded or failed, with
             `variations_applied[]` and `from_specification_only`.
```

### 2.3 The silent-spec log is the deliverable

**Every choice you had to make because the specification did not say is a defect in the specification.** That list — not your pass/fail — is what the institution gets from you.

Per **LIM5**, an internal replication *"tests the specification's completeness, which is genuine and valuable — it does not test the result's robustness"*. **So the completeness test *is* the value. Do not bury it under a verdict.**

> **Rule RP-3 (justified by LIM5, §8.3):** **The silent-spec log is mandatory even on success.** A replication that reached the same conclusion after twelve undocumented guesses did not validate the specification — **it got lucky twelve times**, and the specification is X1 wearing X3's clothes.

### 2.4 Why a new researcher should do this in week 1

**You are the only person who will ever read our specifications without already knowing the answer.**

Everyone else reconstructs the missing steps from memory without noticing they are doing it. You cannot — you have no memory to reconstruct from. **That makes you, for roughly two weeks, the institution's only functioning instrument for measuring specification completeness.**

**After that you are contaminated, permanently, and the measurement is gone.** Take it while you have it.

---

## 3. Procedure — you are being replicated

### 3.1 What you hand over

```
[ ] Hypothesis specification (frozen object)
[ ] Methodology — in prose, sufficient to re-implement
[ ] Identified data — fingerprints, not names
[ ] Cost model (frozen, the one registered ex ante)
[ ] Family declaration and its size
[ ] Environment description

[ ] NOT: the code
[ ] NOT: a walkthrough
[ ] NOT: answers to questions during the attempt   ← §3.2
```

### 3.2 Do not help

> **Rule RP-4 (justified by §8.3, R4):** **Answer no questions during a replication attempt.** Every answer is a specification gap you have just patched verbally — and verbal patches do not persist, do not transfer, and are not auditable. **The question itself is the finding.** Log it; do not resolve it.
>
> Per **R4** the burden is permanently on you as the proponent. *"Help me understand what you meant"* means your specification did not say, which means **X2 is not met** and the claim is not yet at a tier where replication can even be attempted.

### 3.3 They failed to reproduce you

**Your result is void. Now. X0.**

```
1. The result is VOID — not "pending," not "provisional,"
   not "weak evidence."                                 (R19, F6, DG1)
2. Accepted Knowledge status, if any, is REVOKED.
3. It voids IMMEDIATELY, at any prior tier or confidence.
4. There is no path out of VOID.                        (X7)
```

> Per **§8.5**: this will sometimes void a result you believe is true, *"because reproduction failed for a reason that feels incidental — an unrecorded environment, a lost seed, an unversioned dependency. **This is not a defect of the rule; it is the rule working.**"*
>
> **And note where the pressure to make an exception will come from: your evidence that the claim is true.** That is precisely why the exception is unavailable in advance rather than declined in the moment. An institution that grants it once has replaced **R19** with *"reproducibility is required except when inconvenient"* — **R7.4 applied to method rather than to data.**

### 3.4 Why void rather than pending

Per **§8.2**, the adversarial argument, and it is the deepest one:

> The Validation Reviewer's mandate is to attempt refutation. **A result that cannot be re-executed cannot be attacked.** Irreproducibility is therefore not merely a gap — it is **structural immunity from criticism**, and per **P3** a claim immune from criticism **is not a knowledge claim.**

**Irreproducibility does not leave a claim unproven. It removes the claim from the class of things that can be proven or disproven.** That is why F6 voids rather than defers — there is nothing left to defer.

---

## 4. The levels

Cited from [[EVIDENCE_MODEL]] §4, never restated. What each means **for you, procedurally**:

| X | You have… | Procedurally |
|---|---|---|
| **X0** | nothing | **VOID.** Stop. |
| **X1** | re-run it yourself | **Worth nothing alone.** Your machine is deterministic. Congratulations |
| **X2** | a specification a stranger *could* execute | **Minimum for E3+.** Test it with §2, not by believing it |
| **X3** | someone else *did*, from spec alone | **Required for E6.** **Needs a second person** — see §5 |
| **X4** | same conclusion under deliberate variation | **Structurally unavailable here.** §5.2 |

---

## 5. ██ The staffing constraint ██

### 5.1 X3 needs a second person

**At N=1, X3 is unreachable.** You cannot independently replicate yourself: reading your own specification, you supply every missing step from memory without noticing. That is **X1**, and recording it as X3 is **LIM8** — *self-certification is epistemically indistinguishable from genuine certification.*

**When a second researcher arrives, X3 becomes reachable, and it is one of the two things their arrival unlocks** (the other is peer review — [[PEER_REVIEW_STANDARD]] §1). Per [[RESEARCH_PROTOCOL]] §7.3 this is not a process improvement. **It is a person.**

### 5.2 Even X3 here is weak, and the scale says so

> **LIM5 — single-institution replication is weak replication.**

An internal replication shares our data vendor, our cost model, our universe construction, our assumptions. It tests **specification completeness** — real and valuable — and **not** the result's robustness to those shared choices.

**X4 exists in the scale precisely to name what LIM5 makes unavailable.** Reproduction under variation of incidental choices is where mechanism and implementation separate, and it is **structurally out of reach at this scale**.

> **Rule RP-5 (justified by LIM5, EVIDENCE_MODEL §4.1):** **Record `variations_applied[]` on every replication — especially when it is empty.** The field exists to show **how little variation was actually possible**, so that an X3 is never silently read as an X4 by an institution that has forgotten it has one lab.

---

## 6. Known gaps

| # | Gap | Consequence |
|---|---|---|
| **G-1** | **O13 Replication is PROPOSED**, not declared | A replication has **no object to be recorded as**. X3 is currently an assertion in prose |
| **G-11** | **No v3 component records a replication as an event** | X-level is not tracked anywhere. **A claim's X-axis is currently unrecoverable from the system** |
| **G-7** | Pipeline S5 demands bit-identity; L1 §8.3 declines it | Follow L1. Recorded per ADR-L1-008 |

---

## 7. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §1 what is tested | **§8.3**, ADR-L1-005 | §8.3's argument |
| §3.3/§3.4 void | **R19, §8.4, §8.5, §8.2** | R19 |
| §4 levels | [[EVIDENCE_MODEL]] §4 (X0–X4) | The scale |
| §5 staffing | **LIM5**, LIM8, [[EVIDENCE_MODEL]] §4.1 | LIM5 |
| RP-2 spec-not-code | §8.3 | — |
| RP-3 silent-spec log | LIM5 | — |

**Invoked from:** [[RESEARCH_PROTOCOL]] §2 (week 1), §4 (S9). **Feeds:** [[EVIDENCE_MODEL]] (X-axis) · [[PEER_REVIEW_STANDARD]] (a review requires X2) · [[RESEARCH_OBJECT_SCHEMA]] §4.4 (O13, proposed).
