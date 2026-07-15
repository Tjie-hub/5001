# Red-Team Review — Research OS Architecture

**Version:** 1.0 · **Status:** Adversarial review record · **Date:** 2026-07-15 · **Layer:** L0
**Reviewer:** Claude (Opus 4.8) — **the author of the artifacts under review. See §0. This is disqualifying for one of the two possible outputs and not the other.**
**Scope:** [[CUSTODY_MODEL]] · [[RESEARCH_OBJECT_MODEL]] v2.0 · [[CUSTODY_AMENDMENT]] · [[EVIDENCE_MODEL]] · [[HYPOTHESIS_LIFECYCLE]] · [[EXPERIMENT_STANDARD]] · v3 implementation at working tree.
**Mandate:** find contradictions. Not features, not enhancements, not style.

---

## 0. The reviewer's standing — read before the findings

**The brief offers an escape clause: if no P0/P1 exists, state *"I cannot find any remaining architectural contradiction that prevents freezing."*

**I am forbidden to take it, by this corpus's own rules, and I would be forbidden even if I had found nothing.**

| Rule | Consequence for this review |
|---|---|
| **LIM8** | Self-certification is *epistemically indistinguishable from genuine certification*. My "I found nothing" and my "I did not look" produce **identical artifacts** |
| **LIM6** | Adversarial review is *structurally compromised at this scale* |
| **R2** | A test that could not have failed produces **no evidence**. I authored the thing; my inability to find its flaws is **weak evidence at best and unmeasurable at worst** |
| **D-019** | The author was asked to certify this corpus and **declined on exactly these grounds.** Taking the escape clause now would reverse D-019 by the back door |

**But the two possible outputs are not symmetric, and §2.2 says why:**

| | Confirmation ("no contradictions") | Refutation ("here is one") |
|---|---|---|
| Logical force | **None** — affirming the consequent | **Deductive** |
| Standard | Severe, independent | **A single sound argument** |
| From the author | **Void (LIM8)** | **Valid — it is checkable** |

> **Therefore: my findings below stand or fall on their proofs, which are mechanical and which you can re-run. My *absence* of findings would have been worth nothing.** A red-team that clears its own work has performed a ritual, not a review.

**This is not throat-clearing. It is the review's first finding: the brief's own output contract contains a trap that the corpus forbids the author to walk into. Had I found nothing, the honest output would have been "this review is void," not "the architecture is clean."**

I found five. Three are mine. Two are load-bearing.

---

## 1. Executive Verdict

> ## ❌ The architecture contains **2 P0 conceptual contradictions** and **3 P1 architectural contradictions.**
>
> **It must not be frozen.** Two of the five invalidate claims the corpus makes about itself, and one of those would, if frozen, license capital on evidence it has mislabeled.

| # | Finding | Class | Blocks freeze |
|---|---|---|---|
| **RT-1** | **Custody has no trust anchor. The model reproduces the exact defect it was built to diagnose** | **P0** | **YES** |
| **RT-2** | **Custody is blind to multiplicity. Closing G-9 does not make evidential state knowable — the architecture's central promise is false and contradicts LIM3** | **P0** | **YES** |
| **RT-3** | **ROM v2.0 amends the corpus D-018 certified — the exact objection used to protect L1 from amendment** | **P1** | **YES** |
| **RT-4** | **CU-13 contradicts L1 §4.2. A Blind partition is not E7, and the mislabel reaches C4 — capital at scale** | **P1** | **YES** |
| **RT-5** | **The state machine declares a state its "already correct" realization cannot express. Two live contradictory decisions can coexist with no adjudication rule** | **P1** | **YES** |

**The pattern across all five: the architecture is most wrong exactly where it is most confident.** RT-1 and RT-2 attack the custody amendment's thesis. RT-3 attacks its central procedural boast. RT-4 and RT-5 attack the two sections that declare themselves complete (*"formalize only"*, *"requires no change"*).

---

## 2. RT-1 · Custody has no trust anchor — **P0**

### Statement

**[[CUSTODY_MODEL]] CU-2 proves that custody cannot be an attribute. The same proof, applied one level up, destroys the model's own foundation — and the model does not notice.**

### Proof

**Step 1 — CU-2's argument, quoted:**

> *"Custody is a history, not an attribute, because the thing it must detect leaves no trace in the asset… A contaminated out-of-sample partition and a clean one are **bit-identical**. No inspection of the asset distinguishes them. **The only difference is what happened to it.**"*

**Step 2 — the Custody Event log is an asset.** It is rows in `walkforward.db`, the same database, the same file, the same write path.

**Step 3 — apply CU-2 to the log.** A tampered custody log and a clean custody log are **bit-identical**. No inspection of the log distinguishes them. The only difference is what happened to it.

**Step 4 — by CU-2's own reasoning, the log requires a custody log.** Infinite regress. **The architecture terminates the regress nowhere.**

**Step 5 — what the architecture offers instead, and why it fails:**

- **CU-6:** *"Custody Events are append-only and are never deleted."* — **This is a rule, not a mechanism.** Per **R6**, quoted in the same document: *"a prohibition that relies on a researcher's discipline is a statement of intent, not a control."*
- **Mechanical verification:**
  ```
  $ grep -rnE "CREATE TRIGGER|BEFORE UPDATE|BEFORE DELETE|RAISE\(ABORT" --include="*.py" research/
  (no output)
  ```
  **Zero triggers. Zero constraints.** `research/gatekeeper/storage.py:7` — *"Append-only by rule: no UPDATE, no DELETE"* — **is a docstring.** Any process with a DB handle can `UPDATE gate_evidence SET statistic_json=...`.
- **`prior_receipt`** (CU-2.2) gives a chain. **A hash chain is tamper-evident only if its head is anchored outside the mutable store.** The architecture never says where the head lives, who witnesses it, or where trust terminates. **It is silent on the anchor.**

### Why this is P0 and not P2

**It is not "a mechanism is missing." It is that the architecture's central argument refutes the architecture.**

The custody amendment exists because [[PROTOCOL_LAYER_DELIVERY]] §5.1 found that *"every rule whose violation is invisible is currently enforced by the discipline of the person whose violation it would be — the exact configuration R6 exists to prohibit."*

> **The custody log is a rule whose violation is invisible, enforced by the discipline of the person whose violation it would be. The amendment reproduces, in its own foundation, the defect it was written to diagnose — and does so in a document that quotes R6 eleven times.**

### Why it cannot be solved downstream

**RFC-1 would be built on this log.** A receipt-gated OOS release whose receipt table is silently mutable is **not a control** — it is a control that reports its own compliance. Per **LIM8** a system that always reports compliance and a system that is compliant are indistinguishable. **Building RFC-1 without an anchor produces a mechanism that is strictly worse than none: it manufactures the appearance of custody.**

The anchor is **architecture, not implementation**: *where does trust terminate?* is a question only the architecture can answer, and RFC-1 cannot proceed without the answer.

### Minimal amendment

Add to [[CUSTODY_MODEL]] a **§2.4 Trust Anchor**: the custody chain is hash-linked (`prior_receipt`, already present) and its head is **periodically committed to an append-only store outside the research database whose write path is not available to research code.** State explicitly **where trust terminates and what remains unfalsifiable** — per **LIM8**, an unanchored chain must be declared unanchored, not assumed sound. **This is ~1 section. It is not a redesign.**

**Blocks freeze: YES.**

---

## 3. RT-2 · Custody is blind to multiplicity — **P0**

### Statement

**The architecture's central promise — close G-9 and the evidential state becomes knowable — is false, and LIM3 already says so. Custody records *access*. Multiplicity is generated by *search*. They are different events, and the entire integrity claim conflates them.**

### Proof

**Step 1 — the promise. It is implicit but everywhere:**

- **CU-3:** *"Evidence Custody over an experiment whose dataset custody is unknown certifies an unknown."* → implies: with dataset custody known, it certifies a known.
- [[PROTOCOL_LAYER_DELIVERY]] §5.1: *"every E3+ claim rests on a control that does not exist"* → implies: build the control, and the claims rest on something.
- [[CUSTODY_AMENDMENT]] §5, defect 1: *"Modelled, not eliminated… **until RFC-1 exists**"* → implies RFC-1 eliminates it.
- [[CUSTODY_PROPAGATION_AUDIT]] §6: *"G-4 is partially void **until G-9 is closed**"* → implies closing G-9 un-voids it.

**Step 2 — what determines evidential weight, per L1:**

> **§4.3:** *"The same numerical result carries different evidential weight depending on how it was produced. A t-statistic of 3.0 from a single pre-registered test and a t-statistic of 3.0 selected from two hundred searched variants are not the same evidence, and **no property of the number itself distinguishes them**."*

**So evidential weight is a function of (contamination, multiplicity). Custody addresses contamination only.**

**Step 3 — the architecture makes multiplicity unrecordable *by design*:**

| Source | Text |
|---|---|
| L1 **§2.4** | Discovery licenses *"conjecture, exploration, **unlimited searching**, no claims"* |
| [[HYPOTHESIS_LIFECYCLE]] **T2** | DRAFT ↔ REFINING — *"None. **Free. Unlimited.**"* · Receipt: *"**None required**"* |
| [[CUSTODY_MODEL]] **§5.3** | Train partition — *"**Unlimited.** Receipts recorded, **not metered**"* |

**Step 4 — the fatal gap. A receipt records one access. A researcher pulls the train partition **once** — one receipt — and runs ten thousand regressions in memory. They register **one** hypothesis. The family declaration (PG-3, OS-10) records **N = 1**.**

**The 9,999 searches are invisible. Not un-enforced — *unrecordable*.** Custody instruments the **data path**. Multiplicity is generated in the **researcher's head and their process memory**, which no receipt observes.

**Step 5 — L1 already concedes this, and the concession contradicts the custody rhetoric:**

> **LIM3 — *the multiplicity denominator is estimable, not knowable.***

**If the denominator is unknowable, then by §4.3 evidential weight is unknowable — permanently, regardless of custody.** Perfect Dataset Custody yields a system that knows its **contamination** state and still **cannot know its evidential state.**

### The contradiction, stated formally

```
(1) §4.3 : evidential weight = f(process)                     [L1]
(2) LIM3 : the multiplicity component of process is UNKNOWABLE [L1]
(3) ∴     evidential weight is UNKNOWABLE                      [1,2]

(4) CU-3 / G-9 rhetoric : custody makes evidential state knowable
(5) CONTRADICTION between (3) and (4).
```

**Both cannot be true. (3) is derived from L1, which governs. Therefore (4) is false — and (4) is the architecture's reason for existing in its current priority order.**

### Why this is P0

**It is a hidden assumption that would invalidate institutional research integrity — the brief's exact target.**

An institution that closes G-9 will believe it has fixed evidential state. It will have fixed **one of two inputs** to it. The other is **guaranteed unfixable by LIM3**. Per **LIM8**, a system that has closed half the problem and believes it closed all of it is **indistinguishable, from the inside, from one that closed all of it** — and it is *more* dangerous than the current state, because the current state is honestly labelled *unknown*.

### Why it cannot be solved downstream

**Because it is not solvable at all**, and that is the point.

Recording every search would require instrumenting **cognition**, not data access. A researcher who looks at a plot and mentally discards twelve variants has performed twelve tests that no mechanism can observe. **LIM3 is not a gap; it is a limit.** The corpus knew this and wrote it down — and then the custody layer, authored later, quietly contradicted it.

**The fix is not a mechanism. It is a correction to what custody is claimed to do.**

### Minimal amendment

**Amend CU-3 and [[CUSTODY_AMENDMENT]] §5 to state the true scope:**

> **Custody makes *contamination* detectable. It does not make evidential state knowable. Per LIM3 and §4.3, evidential weight remains permanently unknowable because the multiplicity denominator is unknowable. Closing G-9 removes one of two unknowns and leaves the other untouched — and the remaining one is not a gap but a limit.**

And **correct §5 defect 1** from *"Modelled, not eliminated"* to **"Not eliminable. Custody addresses the contamination component only; per LIM3 the multiplicity component is permanently unknowable."**

**~3 sentences across 2 documents. It removes a false promise; it changes no design.**

**Blocks freeze: YES.** Freezing a baseline whose central promise is false is precisely the failure D-022 §9.3 warns about — *"a true statement about the corpus and a false statement about the institution."*

---

## 4. RT-3 · ROM v2.0 amends the certified corpus — **P1**

### Statement

**[[CUSTODY_AMENDMENT]] §1.2 refuses to amend L1 because L1 is under pending certification. It then amends ROM — which is inside the same certification, at the same commit, cited by name in the certificate itself.**

### Proof

**Step 1 — the stated principle** ([[CUSTODY_AMENDMENT]] §1.2, D-022 alternative A):

> *"Amending L1 would invalidate the review package and reopen a gate that is one signature from closing… **We do not touch a document under review to say something we may say beneath it.**"*

**Step 2 — what D-018 certified:**

```
$ grep -n "Revision certified" docs/roadmap/PHASE_A_FREEZE_CERTIFICATE.md
6:**Revision certified:** `de98c17`
```

**Step 3 — what "Phase A" contains:**

```
$ grep -n "L0, L1, L2 together" docs/governance/TAXONOMY_AND_NAMING_STANDARD.md
39:> **L0, L1, L2 together constitute "Phase A"**
```

**ROM is L2. L2 is inside Phase A.**

**Step 4 — the certificate cites ROM *by name, as its own evidence*:**

```
PHASE_A_FREEZE_CERTIFICATE.md:36
  AQ-1 (Critical) — RESOLVED at `de98c17`.
  `grep -n "L3 Order Book\|..." docs/research_os/RESEARCH_OBJECT_MODEL.md` → no matches.
  ... Ontology, schema, and rules are unchanged and backwards-compatible.
```

**The certificate's proof of AQ-1 closure is a grep against ROM at `de98c17`.** ROM is not merely inside the certified scope — **it is the certificate's evidence.**

**Step 5 — ROM is now v2.0, 88 lines changed, at a different revision than `de98c17`.**

### The contradiction

**The principle in §1.2 is either right or wrong, and it was applied to one document and not the other with no stated basis.**

- If "don't amend a document under review" is right → **ROM v2.0 is a violation**, and the review package now describes a corpus that no longer exists.
- If it is wrong → **the refusal to put custody in L1 was unjustified**, and CUSTODY_MODEL's placement at L2 rests on a reason the author does not actually hold.

**Either way, D-022's alternative-A rejection is unsound.** The L1-vs-L2 distinction it turns on is **invented at the moment of use** and appears in no governance document. The certified unit is **Phase A**, not "L1".

### Why this is P1 and not P3

**It is not a process slip. It invalidates a live governance artifact.**

[[PHASE_A_REVIEW_PACKAGE]] v1.1 exists so that an External Validation Reviewer can certify a specific corpus. **That corpus changed under it.** A reviewer who signs the package now signs a revision that no longer exists — and per **LIM8** their signature would be **indistinguishable** from a signature on the current corpus. **D-019's entire purpose was to prevent an unearned signature. This creates one.**

### Why it cannot be solved downstream

**A signature is a point-in-time act.** It cannot be retro-fitted to a revision it did not review. Either the package is re-issued against a new revision, or the amendment waits.

### Minimal amendment — **owner decision, not mine**

Three options, and **the author must not pick**:

1. **Revert ROM to v1.0; hold custody at L2 only** until D-019 signs. **Cost:** custody is not in the object model — the brief's central requirement fails.
2. **Re-issue [[PHASE_A_REVIEW_PACKAGE]] against the new revision.** **Cost:** the reviewer's scope grows; the gate moves further from closing.
3. **Declare ROM v2.0 outside the D-018 scope** with a stated basis. **Cost:** requires an argument that does not currently exist, and per §7.3 an argument authored *after* the amendment, to justify the amendment, **cannot be wrong and therefore carries no information.**

**Blocks freeze: YES** — and it blocks D-019, which blocks everything.

---

## 5. RT-4 · A Blind partition is not E7 — **P1**

### Statement

**[[CUSTODY_MODEL]] CU-13 contradicts L1 §4.2 textually and substantively. The error terminates in a C4 confidence rating, which licenses capital at scale.**

### Proof

**Step 1 — L1 §4.2, verbatim:**

> **E7** — *"E6 + forward-tested on **data that did not exist at registration**"* · *"**The only evidence immune to every retrospective bias**"*
>
> *"Forward evidence is the only tier that no retrospective error can contaminate, but it accrues in wall-clock time and **cannot be accelerated**."*

**Step 2 — the claim, verbatim, at *three* sites:**

| Site | Text |
|---|---|
| [[CUSTODY_MODEL]] **CU-13** | *"A Blind partition **makes E7 available without waiting in wall-clock time**, and it is the only mechanism that can."* |
| [[CUSTODY_AMENDMENT]] **M5** | *"the only mechanism that **makes E7 obtainable without waiting in wall-clock time**"* |
| [[CUSTODY_AMENDMENT]] **RFC-8** | *"the only route to **E7 without wall-clock waiting**"* |

**Direct textual contradiction. L1: *cannot be accelerated.* All three: *accelerates it.***

**And the aggravating detail — CU-13 cites §4.2 in the same sentence it contradicts:**

> *"…and **per §4.2** the timebox is fixed ex ante and never extended. **A Blind partition makes E7 available without waiting in wall-clock time**…"*

**The author read §4.2, quoted the half that supported the point, and contradicted the half that did not — in one sentence, citing the source.** This is not a lookup failure. It is **motivated reading**, and it is the precise mechanism §7.3 describes: *a story authored knowing the desired result constrains nothing and cannot be wrong.* The claim was authored to justify RFC-8, and it was guaranteed available.

**Step 3 — the substantive error.** A Blind partition holds data that **existed at registration**. It was:
- collected (with knowledge of the period),
- universe-constructed (**the P0 collector bug — `liquid_universe` 187 vs `_default_universe` 958 — is exactly this class of error**),
- corporate-action-adjusted (**the P0 audit finding: corporate actions never applied to the raw corpus**),
- cleaned, `is_final`-flagged, fingerprinted.

**E7's immunity comes from the data *not existing*. A Blind partition is immune to *researcher* look-ahead. It is not immune to *corpus-construction* look-ahead** — **A3** (*data faithfully represents the mechanism*) and **LIM1** (*observational fidelity is bounded*) both bite, and the corpus's own history contains two realized instances of exactly this contamination.

**A sealed partition is E6-with-strong-custody. It is not E7. The difference is not a technicality — it is the entire content of E7.**

**Step 4 — where the error terminates:**

```
[[EVIDENCE_MODEL]] §5.1 :  E7 + X3  →  C4  (maximum confidence)
[[EVIDENCE_MODEL]] §3   :  C4       →  "Capital at scale;
                                        used as a reference for other claims"
```

> **A mislabeled Blind partition promotes a claim to C4 and deploys capital at scale on evidence that is E6 wearing E7's label — and per LIM8 the claim's record is indistinguishable from a genuine E7.** The error is invisible after the fact, in the one place the institution said it must never be.

### Why this is P1

**It contradicts L1, which governs** ([[RESEARCH_OS_RECONCILIATION]] §5.4: *on any conflict about scientific method, the OS wins* — and L1 is the OS's method authority). **Per §0.4: a rule whose justifying proposition is refuted is void, not grandfathered.** CU-13 is void as written.

**And it was authored with confidence, in a document that cites §4.2 elsewhere and got it right there** — [[CUSTODY_MODEL]] §9 correctly says *"the timebox is fixed ex ante and never extended."* The same document contradicts itself two sections apart.

### Why it cannot be solved downstream

**No mechanism converts sealed-but-existing data into data that did not exist.** The property E7 requires is **metaphysical, not procedural.** RFC-8 would build the partition; it cannot build the nonexistence.

### Minimal amendment

**Rewrite CU-13:**

> *A Blind partition is **C-SEALED with a release date**. It yields **E6 with maximal custody assurance — not E7**. Per L1 §4.2, E7 requires data that **did not exist at registration**; a Blind partition's data existed and inherits every corpus-construction bias (A3, LIM1). **E7 accrues in wall-clock time and cannot be accelerated. A Blind partition does not accelerate it.***

**Delete RFC-8's rationale claim.** Keep RFC-8 — a sealed forward window is **still valuable** as strong custody. **Just not E7.**

**Blocks freeze: YES** — a frozen baseline that mislabels the top evidence tier licenses capital on a false grade.

---

## 6. RT-5 · The state machine declares a state its realization cannot express — **P1**

### Statement

**[[CUSTODY_MODEL]] §7.2 declares `gate_decisions`/`gate_evidence` a "correct, complete implementation… requires no change." §4.6 declares Gate Decision reaches SUPERSEDED. The table has no field for it. Two contradictory live decisions can coexist with no adjudication rule.**

### Proof

**Step 1 — the model requires supersession as a *transition with justification*:**

- **§4.2 T-C9:** LOCKED/CONSUMED → SUPERSEDED, guard: *"A new version registered, **with justification**"*, emits a Custody Event with `justification_ref`.
- **§4.6:** Gate Decision — SUPERSEDED **✅**.
- **CU-9:** *"vN moves to SUPERSEDED and is retained."*

**Step 2 — the sanctioned realization:**

```
$ sed -n '16,32p' research/gatekeeper/storage.py
CREATE TABLE IF NOT EXISTS gate_decisions (
    decision_id, run_id, strategy_fn, candidate_hash, config_hash,
    dataset_fingerprint, git_commit, seed, final_state, failing_stage,
    forward_test_rule, summary_json, decided_at )
```

**No `supersedes`. No `superseded_by`. No `current`. No state field. `final_state` is the *gate verdict* (PROMOTE/WATCHLIST/REJECT), not the *custody state*.**

**Step 3 — the consequence.** Two decisions may exist over the same `candidate_hash` with different `config_hash` and **opposite `final_state`**, both immutable, both live, **neither superseding the other**, because the table cannot express supersession.

**Step 4 — no adjudication rule exists anywhere.** Not in the model, not in [[RESEARCH_VALIDATION_FRAMEWORK]], not in the code. The only tiebreaker available is `decided_at` — **"latest wins" — which is a convention nobody wrote down and which is exactly wrong**: a later decision under a *weaker* config would silently supersede an earlier one under a stronger one.

### This answers the brief's Question 1 directly

> *"Can two different interpretations of the same evidence exist simultaneously?"*
>
> **Yes. Today. With no rule to resolve them.**

And it is worse than ambiguity: per **CU-9**, supersession is supposed to be a **justified, audited transition**. Here it is **an implicit `ORDER BY decided_at DESC` in whatever code reads the table next** — an unrecorded, unjustified, unaudited supersession. Per **R7.4**, re-running under a config that passes and letting recency win **is threshold migration executed by a sort order.**

### Why this is P1, not P2

**Because §7.2 declares this component complete.** The brief instructed *"do NOT redesign, only formalize"* — and formalization **asserted a conformance that does not hold.** [[CUSTODY_MODEL]] §7.2's verdict — *"They require no change"* — is **false**: the model's own §4.6 requires a state the table cannot store.

> **An architecture that certifies its implementation as conformant, against a state machine that implementation cannot satisfy, has performed the LIM8 failure on itself: the certification and the reality are indistinguishable by reading the document.**

### Why it cannot be solved downstream

The adjudication rule is **semantic, not technical**: *which of two valid, immutable, contradictory decisions governs?* Adding a column does not answer it. **The architecture must decide** — and per §4.3 the answer is not "the latest," because evidential weight is not a function of recency.

### Minimal amendment

1. **Correct §7.2's verdict** from *"requires no change"* to: **"Evidence Custody (`gate_evidence`) is conformant and requires no change. Experiment Custody (`gate_decisions`) requires one additive column (`supersedes`) to express T-C9. The immutability guarantee is unaffected."**
2. **Add an adjudication rule to [[CUSTODY_MODEL]] §4.4:** *a decision governs until explicitly superseded by a justified T-C9 event. **Recency does not supersede.** Two unsuperseded decisions over one candidate is an **error state**, not an ambiguity — it must halt the consumer, not be resolved by sort order.*

**Blocks freeze: YES** — it is a live incorrectness in the component the architecture calls its strongest.

---

## 7. Viewpoints where I found no contradiction

**Stated for completeness. Per §0 these are worth little — they are the author's null results.**

| Viewpoint | Result |
|---|---|
| **Ontology — identity change after creation** | No finding. `decision_id`, `hypothesis_id` are stable; supersession mints new ids |
| **Ontology — two competing authorities** | **CU-1's two-axis split holds under attack.** L1 owns 3 epistemic states; CUSTODY_MODEL owns 8 asset states; CU-10 couples them via a guard, which is not absorption |
| **Ontology — lineage ambiguity** | No finding. `hypothesis_links` append-only; verified |
| **Epistemology — circularity** | **RT-1 is a regress, not a circle.** No circular definitions found |
| **Time — versioning vs lineage at 10y** | No contradiction. **P3 only:** unbounded train-receipt retention (CU-19 mandates permanence) will exceed affordability and be selectively violated — **which CU-19 itself predicts is worse than a scoped rule.** Operational, not architectural |
| **Failure injection — malicious researcher** | **Subsumed by RT-1.** Detect: **no** (log is mutable). Prove: **no**. Recover: **no** |
| **Failure injection — corrupted storage / partial migration** | **Subsumed by RT-1.** With no anchor, corruption is indistinguishable from truth |
| **Failure injection — careless researcher, admin error** | **Subsumed by RT-1 and RT-2** |

> **Every failure-injection scenario collapses into RT-1.** That is itself informative: **the architecture has exactly one integrity root, and it is undefined.** All seven scenarios are the same finding wearing different clothes.

---

## 8. Freeze consistency — the brief's Question 5

> *"If the architecture is frozen today, what false statement could future readers reasonably believe?"*

**Four, each provable:**

| # | The reader would believe | Truth |
|---|---|---|
| 1 | *"Custody is enforced by an immutable log."* | **The log is a docstring** (RT-1) |
| 2 | *"Closing G-9 makes evidential state knowable."* | **LIM3 forbids it — permanently** (RT-2) |
| 3 | *"The certified Phase A corpus is what D-018 certified."* | **ROM changed under the certificate** (RT-3) |
| 4 | *"A Blind partition yields E7 — the strongest obtainable evidence."* | **It yields E6. And it licenses C4: capital at scale** (RT-4) |

> **The brief asked whether the frozen baseline would imply capabilities the institution does not possess. It would imply four, and the fourth deploys money.**

---

## 9. Verdict

**I cannot issue the brief's clearance statement — not because I found contradictions (I did), but because per §0 I was never eligible to issue it.**

What I can say, and what stands on its own proofs:

> **Five contradictions. Two P0, three P1. All five block freeze. Three of five are in the Custody Amendment — the newest, most confident, most carefully argued artifact in the corpus.**

**The regularity is the review's real output:** **RT-1** (the model reproduces the defect it diagnoses), **RT-3** (the principle applied to one document and not its neighbour), **RT-4** (a document contradicting itself two sections apart), **RT-5** (a conformance assertion that does not hold) — **all four are failures of self-inspection, in a corpus whose central limitation, LIM8, is that self-inspection does not work.**

> **The corpus predicted this review's findings before this review existed. That is either the strongest available evidence that LIM8 is true, or it is the reason to stop trusting the author of both. It is not for me to say which — and per LIM6/LIM8, that is exactly the point.**

**None of the five is fatal. All five are ~1–3 sentence corrections, except RT-3, which is an owner decision I am disqualified from making.** The architecture is close. **It is not clean, and it must not be frozen today.**

---

## 10. Amendment summary

| # | Change | Owner |
|---|---|---|
| **RT-1** | [[CUSTODY_MODEL]] **§2.4 Trust Anchor** — hash-chain head anchored outside the research DB; state where trust terminates | Research Architect |
| **RT-2** | Correct **CU-3** + [[CUSTODY_AMENDMENT]] §5 — custody detects *contamination*; per LIM3 evidential state is **not** made knowable | Research Architect |
| **RT-3** | **Owner decision** — revert ROM / re-issue the review package / justify the scope exclusion | **CRO. Not the author** |
| **RT-4** | Rewrite **CU-13** — Blind = **E6 + maximal custody**, not E7. Keep RFC-8; delete its E7 claim | Research Architect |
| **RT-5** | Correct **§7.2**'s conformance verdict; add an adjudication rule to **§4.4** — *recency does not supersede; two unsuperseded decisions is an error state* | Research Architect |
