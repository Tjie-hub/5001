# Peer Review Standard

> ## ██ THIS DOCUMENT IS INERT AT N=1 ██
>
> **It activates the day a second researcher arrives.** It is written now because it is the document that **closes G-4** — the institution's binding constraint — and because the constraint must be legible before it is relieved, not after. See §1 before using it.

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1) · **Layer:** L2 — Research Architecture (procedural)
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version). **Does NOT supersede** [[RESEARCH_OPERATING_MODEL]] §5–§6 (roles, G4).
**Realized in v3:** **none.** S9 has no v3 realization. O18 Reviewer Sign-off is proposed, not declared (**G-1**).
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **§2.2 (asymmetric justification, R4)**, **LIM6 (adversarial review is structurally compromised at this scale)**, **LIM8 (self-certification is indistinguishable from certification)**, **ADR-L1-007 (declare the deficit; do not absorb it)**, §5.3 (F1–F9), R3 (severity), §8.2 (adversarial argument)
**Governance:** [[DECISION_LOG]] **D-021**, **D-019** · [[EVIDENCE_MODEL]] EV-9

---

## 1. ██ The staffing condition ██

### 1.1 Why this document cannot be used today

**Peer review requires a reviewer who is not the author.** At N=1 there is no such person. This is not a backlog; it is structural:

| | |
|---|---|
| **LIM6** | Adversarial review is **structurally compromised at this scale** |
| **LIM8** | Self-certification is **epistemically indistinguishable from genuine certification** — you cannot even tell whether you did it properly |
| **EV-9** | A single-researcher claim caps at **C2**. **T9 (VALIDATED→ACCEPTED) requires C3** |
| **⇒** | **At N=1 the institution cannot promote any hypothesis to Accepted Knowledge** |

> **Rule PV-1 (justified by LIM6, LIM8, ADR-L1-007):** **At N=1, do not perform peer review on your own work and record it as peer review.**
>
> Per **LIM8** the record would be **indistinguishable from a genuine one** — and that indistinguishability *is* the harm. It does not produce a slightly weaker review; it destroys the institution's ability to know its own epistemic state, permanently and invisibly.
>
> **What you do instead:** mark the claim **C2**, state plainly that **G4 is unmet**, and move on. That is the honest terminal state. **It is not a failure and it must never be treated as one** — a researcher penalised for reaching C2 honestly will reach C3 dishonestly, and per LIM8 nobody will be able to tell.

### 1.2 This is not hypothetical — the corpus is standing here

**[[PHASE_A_FREEZE_CERTIFICATE]] v2.1 is blocked on exactly this document's subject matter.** One open condition: independent adversarial sign-off, owned by an **External Validation Reviewer** (**D-019**). The author was asked to supply it and **declined**, on precisely LIM6/LIM8 grounds.

> **The pipeline this standard governs, and the certificate that would bless the corpus defining it, are stopped by the identical constraint.** Neither can be climbed from inside. Per **D-019**'s rejected alternatives: author self-certification *"would not satisfy the criterion but delete it — R7.4 applied to governance"*; and a fresh-context LLM review *"is not a fresh mind: same model, same priors, same blind spots."*

### 1.3 What changes at N=2

| N | Peer review | Consequence |
|---|---|---|
| **N=1** | **Impossible.** This document is inert | **C2 ceiling. G-4 open.** Everything except acceptance is available |
| **N=2** | **Possible.** Each reviews the other | **C3 reachable → T9 reachable → G-4 CLOSES.** Accepted Knowledge becomes possible **for the first time** |
| **N≥3** | Reviewer independent of *both* author and CRO; role separation per [[RESEARCH_OPERATING_MODEL]] §5 becomes real | **ADR-L1-002 mandates revisiting the epistemology itself** at ≥3 |

> **Rule PV-2 (justified by ADR-L1-007):** **The bar does not move to meet the headcount.** Per ADR-L1-007 — *declare the single-researcher review deficit; do not absorb it.* Weakening G4 to what one person can discharge **would not make the institution able to accept knowledge; it would make it unable to tell whether it should.**

### 1.4 Reciprocal review at N=2 — the trap

At N=2, A reviews B and B reviews A. **This satisfies independence and creates a new failure mode nobody names:** mutual leniency. Neither is dishonest; each simply knows they are next.

> **Rule PV-3 (justified by R4, LIM6):** **At N=2, record the reciprocity on every sign-off** (`independence_attestation`, O18). Reciprocal review satisfies *reviewer ≠ author*. It does **not** satisfy *reviewer has no stake*. **LIM6 is relieved at N=2, not repealed** — and the residual must stay visible, because per **LIM8** an invisible deficit is indistinguishable from no deficit.

---

## 2. Your mandate

> **You are not here to approve. You are here to attempt refutation.**

Per **§2.2**, confirmation and refutation are not symmetric, and the institution's rules deliberately reflect it:

| | Confirmation | Refutation |
|---|---|---|
| Logical force | **None** (affirming the consequent) | Deductive, modulo auxiliaries |
| Institutional cost | **High** — earned repeatedly | **Low** — accepted on first competent demonstration |
| Standard of proof | Severe test, ex-ante criteria, OOS, net of cost, mechanism-explained | **A single sound argument** |

> **R4 — the burden of proof rests permanently and asymmetrically on the *proponent*. It never transfers to the skeptic.** *"You cannot prove it doesn't work" is not a defense; it is a concession.*

**You are the skeptic. The burden is never yours.** You are not required to prove the claim wrong. You are required to *try*, competently, and to report what survived.

> **Rule PV-4 (justified by R4, §5.5):** **A review that finds nothing wrong is not a passed review — it is a failed attack.** Report it as such: *"I attempted F1, F3, F4, F5, F7; here is how; none succeeded."* **The record is the attempt, not the verdict.** A sign-off saying "looks good" is not a review; per §8.2 it leaves the claim with *structural immunity from criticism*, which per **P3** means it is not a knowledge claim at all.

---

## 3. The attack, in order of cheapness

**Attack in this order.** Per §5.3, **F1 is privileged** — it consumes no data, no custody, no multiplicity budget. **If you can kill it at F1, everything downstream was wasted anyway and you have saved it.**

### 3.1 F1 — mechanistic incoherence *(free, do this first)*

```
[ ] Does the mechanism name an M-class SUB-CLASS?           (M-1)
[ ] A specific CONSTRAINT and a specific PARTICIPANT CLASS?  (R9)
    "M5 · Behavioral" with no named bias, no named participant
    class, and no reason the bias is unarbitraged is NOT a
    classification. Refuse it.
[ ] Does the causal chain START at a constraint?             (M-2)
    A chain starting at an observable is a correlation with
    arrows drawn on it.
[ ] Is there a PERSISTENCE story citing one of §6.3's seven
    barriers?                                                (R16.2)
    ── No barrier ⇒ R17: default presumption is THE EFFECT
       DOES NOT EXIST. Someone with more capital and better
       data has already taken it. KILL IT HERE.
[ ] Does the mechanism contradict the venue's design (D1)?
[ ] Is the deviation defined against a STATED counterfactual? (§3.2)
    "Deviation from true price" is empty — there is no true price.
```

> **This block kills more claims than all the statistics combined, and it costs nothing.** Per §5.3: *"an institution that routinely kills claims at F1 is operating efficiently; one whose failures cluster at F2–F4 is spending its scarcest resources to learn things it could have reasoned out."*

### 3.2 The retro-fit attack *(free, and the hardest)*

```
[ ] `authored_at` on the Mechanism — does it PREDATE every
    experiment in `blind_to`?                                (OS-6)
[ ] Was the mechanism sourced from LITERATURE (blind by
    chronology and geography), or authored here, after
    looking at our data?                                     (LRS §0.1)
[ ] Does the mechanism predict anything the experiment did
    NOT test?  ── If not, suspect it was shaped to fit.
```

> **Per §7.3 you cannot detect a retro-fit by reading the mechanism.** *"A competent economist can supply a plausible story for any result, including the opposite one."* Its defect **is not falsity** — every sentence may be true — *"it is that it carries no information, because it was guaranteed to be available whatever the data showed."*
>
> **A retro-fitted mechanism is a counterfeit: indistinguishable from the genuine article by inspection.** So do not inspect it. **Check the timestamps and the source.** That is all you have, and it is why the ordering is enforced by process rather than judged by review.

### 3.3 F3 — multiplicity *(free)*

```
[ ] What is the TRUE family denominator?
    Not the declared one. Count: every variant, every re-run,
    every dead sibling, every specification tried.
[ ] Was the family NARROWED after the fact?                  (R7.5)
[ ] Does the claim survive its own denominator?
[ ] Is this Program's family independent of neighbouring
    Programs' — or do their entries confound/subsume?        (PG-7)
```

> **This is where P0's NR7 edge died** — significant against zero, CI [+0.32, +2.06], **DSR collapsed under a 42-cell family**. **Expect it. It is the most common way a real-looking result correctly dies.**

### 3.4 F7 — look-ahead *(cheap)*

```
[ ] Point-in-time argument for every Feature?
[ ] Is any classification labelled BY ITS OUTCOME?
    (e.g. "informed flow" labelled from end-of-day results —
     F7 wearing a participant label. The dominant failure
     mode in flow research.)
[ ] Corporate actions applied at the right time?
[ ] Backfilled or index-inclusion-contaminated data?         (B3)
```

### 3.5 R2 — could it have failed? *(cheap, and the one reviewers skip)*

```
[ ] Power / MDE analysis present?
[ ] Could this test have refuted the hypothesis?
    ── NO ⇒ the result is NOT weak evidence. It is NO evidence.
       An error of KIND, not degree. Refuse it — regardless
       of what it reported.
```

### 3.6 R3 — the severity interrogation *(the core of a real review)*

Per **EV-3**, the severity argument is a **positive obligation on the proponent**, discharged **in prose, not by citing a p-value**:

> *"What would have had to be true for this test to have caught the error, and was the test in fact capable of that?"*

```
[ ] Is a severity argument WRITTEN?
    ── Absent ⇒ the claim is NOT YET EVIDENCE, whatever it
       measured. Not a weak claim. Not evidence. Return it.
[ ] Could the test have distinguished this mechanism from
    its RIVALS — not just from zero?                          (M-3)
    A test against zero is not severe. Almost nothing is zero.
[ ] Check the reversion-permanence cell (M-4):
    inventory (M1) and information (M2) predict the SAME
    displacement and differ only in whether it reverts.
    A test measuring displacement without persistence has
    tested NEITHER.
[ ] Are the confounding entries excluded?                     (MIT §4)
    I5↔I7 is the central identification problem of D2.
    I10 (attention) is the universal rival for anything
    clustering on salient events.
```

> **Rule PV-5 (justified by R3, R4):** **Absence of a severity argument is a refusal, not a request for more detail.** Per R4 the burden never transfers: *"you haven't shown the test was insensitive"* is not a defense the author may offer you.

### 3.7 F4 / F8 — cost and capacity *(cheap)*

```
[ ] Cost model FROZEN BEFORE the run?                        (OS-4)
    A cost model chosen after a result is R7.4.
[ ] Does the effect survive realistic friction?              (F4)
[ ] Is the effect larger than its own cost, or is it a
    *confirmed irrelevance*?                                 (§5.5)
[ ] Capacity: does it survive at any size we could deploy?   (F8)
    A4 is declared to FAIL AT SCALE.
```

### 3.8 F5 — regime *(cheap)*

```
[ ] Regime scope declared EX ANTE, or stable across regimes?
    ── Post-hoc regime scope is R7.4.
[ ] Rests on A5 — the corpus's SELF-DECLARED WEAKEST
    assumption: regimes are constructs, never measurements.
    Elevated burden. Say so.
```

### 3.9 F6 / X — reproducibility *(expensive; do last)*

```
[ ] X2 minimum: could a stranger execute the specification?
[ ] Provenance complete? ── Incomplete ⇒ X0 ⇒ VOID (R19)
[ ] If claiming E6: was X3 achieved BY SOMEONE ELSE?
    ── Author re-running is X1. Worth nothing.
[ ] Record LIM5: internal replication is WEAK replication.
```

---

## 4. What you produce

A **Validation Report** (O7) — the record of an **attack**, not a summary.

```
[ ] `attempted_refutations[]`   ← WHAT YOU TRIED. The primary content.
                                   A review with an empty list is not
                                   a review.
[ ] `severity_argument`         ← in prose
[ ] `family_size_at_review`     ← the TRUE denominator, which may
                                   EXCEED the declared one (DG4)
[ ] `evidence_tier` (E) · `confidence` (C) · `reproducibility` (X)
[ ] `f_mode` if refuted — EXACTLY ONE, with `attribution_defense`
                                   defended against auxiliaries (R1)
[ ] `reviewer_independence`     ← author ≠ reviewer, or state that
                                   it is not. At N=2 record RECIPROCITY.
```

> **Rule PV-6 (justified by EV-9, EV-4):** **You can raise C. You cannot raise E. You can destroy both.** Your review is class **K7**. It gates **C1→C2**. It cannot move a claim's evidence tier — only the test that produced it can do that.
>
> **And: assign C low when the family is large, even if the tier is high.** E-high / C-low is the correct and common reading (P0's NR7 is the live instance). An institution without the C axis has no way to write down *"this was a severe test and I still don't believe it"* — which is the correct state for most severe tests in a large family.

---

## 5. What is not a review

| ✗ | Why |
|---|---|
| "Looks good" | Not an attack. Leaves the claim immune from criticism (§8.2) ⇒ **not a knowledge claim** (P3) |
| Checking the arithmetic | Necessary, not sufficient. The arithmetic is almost never the error |
| Reproducing the number | **X1.** Proves determinism, nothing else |
| Asking the author to explain | **RP-4** — the question is the finding. Log it; do not let it be patched verbally |
| Approving because it is probably true | **R13** — your belief is not evidence. **EV-5** — confidence never rises from wanting |
| Approving because a lot of work went in | **R13** — *sunk research cost is not evidence* |
| Approving because capital is waiting | **EV-5** — the most dangerous variant. It **inverts the causal order the institution exists to protect**: research produces knowledge; capital consumes it; **the reverse dependency is prohibited** (§0.1) |
| Softening because you are reviewed next | **PV-3** — record the reciprocity |

---

## 6. Known gaps

| # | Gap | Consequence |
|---|---|---|
| **G-4** | **T9 unreachable at N=1** — this document is inert | **BLOCKING.** No Accepted Knowledge. **Closed by a second researcher, not by a document.** Owner: hiring |
| **G-1** | **O18 Reviewer Sign-off is PROPOSED**, not declared | A review has no object to be recorded as |
| **G-12** | **S9 has no v3 realization** | Peer review is entirely manual and unrecorded |
| **G-13** | **No mechanism prevents a self-review being recorded as independent** | Per **LIM8** the two are indistinguishable. **`reviewer_independence` is currently an attestation, not a control** — and per **R6** an attestation is *"a statement of intent, not a control"* |

---

## 7. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §1 staffing | **LIM6, LIM8, ADR-L1-007, EV-9, D-019** | LIM6/LIM8 |
| §2 mandate | **§2.2 (R4)**, §5.5 | R4 |
| §3 attack order | **§5.3 (F1–F9)** — F1 privileged | The mode definitions |
| §3.2 retro-fit | **§7.3**, OS-6 | §7.3's argument |
| §3.6 severity | **R3, EV-3**, M-3, M-4, [[MARKET_INEFFICIENCY_TAXONOMY]] §4 | The severity criterion |
| §4 output | [[RESEARCH_OBJECT_SCHEMA]] §3.7 (O7), §5.4 (O18) | O7's fields |
| PV-6 C not E | **EV-9, EV-4** | The axes |

**Invoked from:** [[RESEARCH_PROTOCOL]] §4 (S9/G4). **Requires:** [[REPLICATION_STANDARD]] (X2 minimum). **Feeds:** [[EVIDENCE_MODEL]] (C-axis) · [[HYPOTHESIS_LIFECYCLE]] T9 · [[FAILURE_LIBRARY_SCHEMA]] (on refutation).
