# RT-4 Contradiction Resolution — Blind Partition vs E7

**Version:** 1.0 · **Status:** Resolution record · **Date:** 2026-07-15 · **Layer:** L0
**Board:** Institutional Architecture Resolution Board
**Mandate:** Determine whether RT-4 is (1) a genuine architectural contradiction, (2) a terminology conflict, (3) a governance conflict, or (4) an incorrect interpretation. **Prove it. Do not assume.**
**Constraint honored:** no document was modified before this classification completed (§7).

---

## Phase 1 · Canonical Reading

### 1.1 [[01_SCIENTIFIC_FOUNDATION]] §4.2 — the tier table (quoted, not summarized)

> | **E6** | E5 + independently reproduced from the specification alone | **Decisive available** | The result belongs to the institution, not to its author (§8) |
> | **E7** | E6 + forward-tested on **data that did not exist at registration** | **Strongest obtainable** | **The only evidence immune to every retrospective bias** |

### 1.2 [[01_SCIENTIFIC_FOUNDATION]] §4.2 — "On E7 and its cost"

> **On E7 and its cost.** Forward evidence is the only tier that no retrospective error can contaminate, but it **accrues in wall-clock time and cannot be accelerated**. This creates a real, permanent tension between rigor and timeliness. The institution resolves it in one direction: **the timebox for forward evidence is fixed ex ante and never extended to rescue a claim** — extending it is R7.4 (threshold migration) wearing a calendar. A claim that fails its forward test fails; a claim that runs out of time is unproven, not proven.

### 1.3 [[EVIDENCE_MODEL]] — three independent restatements of the criterion

> **§52 (K6):** | **K6 · Forward** | Outcome on **data that did not exist at registration** | Promotion to E7 | **E7 — strongest obtainable** |

> **§102 (C4):** | **C4** | **Institutional** | C3 + forward evidence on **data that did not exist at registration** | Capital at scale; used as a reference for other claims |

> **§175 (E6→E7 promotion guard):** | E6→E7 | **Forward-tested on data that did not exist at registration**, within a **timebox fixed ex ante** | **§4.2 is explicit and absolute:** the timebox is never extended to rescue a claim. A claim that fails forward *fails*; a claim that runs out of time is **unproven, not proven** (U12) |

> **§15:** [[01_SCIENTIFIC_FOUNDATION]] §4.2 owns the **evidence tier scale E0–E7**… This document **does not restate that scale, may not renumber it, and may not add tiers.**

### 1.4 [[CUSTODY_MODEL]] — the claim under review

> **§285 (§5.3 partition table):** | **Blind** | **C-SEALED** | **Never, until a declared future date** | **Not releasable.** Reserved for **E7 forward evidence** (§4.2) |

> **§289 (CU-13):** **Rule CU-13 (justified by §4.2 E7, R6):** **A Blind partition is C-SEALED with no release path until its declared date.** It is the only asset in the institution that is **not readable by anyone, including the CRO**. It exists because **E7 — forward evidence on data that did not exist at registration — is the only tier no retrospective error can contaminate**, and per §4.2 *the timebox is fixed ex ante and never extended.* **A Blind partition makes E7 available without waiting in wall-clock time, and it is the only mechanism that can.**

### 1.5 [[CUSTODY_MODEL]] §4.1 / [[RESEARCH_OBJECT_MODEL]] §4.1 — the Dataset Partition object

> **Dataset Partition Object** … · **kind**: Train | Validation | Test | **Out-of-Sample** | **Blind**
> · **scheme_ref**: the split rule, declared **ex ante**
> · **fingerprint**: **its own**, distinct from the parent Dataset's
> · **custody_class**: C-FROZEN-ON-USE, or **C-SEALED** for Out-of-Sample and Blind
> · **release_date**: Blind partitions only — before it, releasable by **nobody, including the CRO** (CU-13)

### 1.6 [[CUSTODY_MODEL]] §4.2 — the transitions that bind the object

> | **T-C2** | CREATED → REGISTERED | **Identity + fingerprint + lineage** | ✅ |
> | **T-C5** | PARTITIONED → LOCKED | **Every partition sealed**; scheme immutable | ✅ |

### 1.7 [[CUSTODY_AMENDMENT]] — the claim, propagated

> **§207 (M5):** | **M5 · Blind partition** | Seal a forward window with a release date (**CU-13**) — **the only mechanism that makes E7 obtainable without waiting in wall-clock time** | **No** | Small, **high value** |

> **§226 (RFC-8):** | **RFC-8** | Blind partition (M5) | **P1** | Research Architect | **Small, cheap, and the only route to E7 without wall-clock waiting** |

### 1.8 Precedence and voidness

> **[[RESEARCH_OS_RECONCILIATION]] §5.4:** On any conflict about *scientific method or institutional governance*, **the OS wins** (that is its charter).

> **[[01_SCIENTIFIC_FOUNDATION]] §0.4:** a rule whose justifying proposition is refuted is **void, not grandfathered**.

---

## Phase 2 · Formal Definitions

| Term | Definition | Source |
|---|---|---|
| **Registration** | The moment a Hypothesis is frozen at G1/T4 | [[HYPOTHESIS_LIFECYCLE]] T4 |
| **Wall-clock time** | Physical elapsed time in the world | plain |
| **Acceleration** | Obtaining a property in less wall-clock time than the property's generating process requires | plain |
| **Non-existent data** | Data whose referent events **have not yet occurred in the world.** Cannot be observed, fingerprinted, or stored by anyone | derived, §1.2 |
| **Future data** | = Non-existent data, relative to a stated instant | derived |
| **Unobserved data** | Data that **exists** and has **not been read** by a given party | derived |
| **Unavailable data** | Data that **exists** and cannot be read by a given party (access controlled) | derived |
| **Reserved data** | A **declared intent** to collect data that does not yet exist. **Not an object in this architecture** — see §3.2 | derived |
| **Out-of-Sample** | A partition of **existing** data, C-SEALED, released **once per hypothesis** in Confirmation | [[CUSTODY_MODEL]] §5.3 |
| **Blind Partition** | A partition of a Dataset, C-SEALED, with **no release path** until `release_date`. **Carries its own fingerprint** (§1.5) | [[CUSTODY_MODEL]] §4.1, §5.3 |

### 2.1 The overlap that produced the error

> **`Unavailable` and `Non-existent` are distinct and the corpus never conflated them — until CU-13.**

| Property | Non-existent | Unavailable (Blind) |
|---|---|---|
| Referent events occurred? | **No** | **Yes** |
| Can be fingerprinted? | **No** | **Yes — and the object model requires it** |
| Immune to researcher look-ahead? | Yes | **Yes** |
| Immune to **corpus-construction** bias? | **Yes** | **NO** |
| Obtainable without waiting? | **No** | **Yes** |

**CU-13 treats `Unavailable` as if it were `Non-existent`.** Row 4 is where they part, and row 4 is what E7 is *for*.

### 2.2 Which reading of "did not exist at registration" is admissible?

Two candidates:

- **Reading M (metaphysical):** the referent events had not occurred.
- **Reading E (epistemic):** the data was not available to the institution.

> **Reading E is refuted by L1's own justification clause, independently of anything in the Custody Model.**

§4.2 asserts E7 is *"The only evidence immune to **every** retrospective bias"* and *"the only tier that **no retrospective error** can contaminate."* Under Reading E, a sealed-but-existing partition qualifies as E7. But such a partition's parent corpus was constructed **with knowledge of the period**:

- universe selection — **the P0 collector bug is a realized instance** (`liquid_universe` 187 vs `_default_universe` 958);
- corporate-action application — **the P0 audit's top finding is a realized instance** (*corporate actions never applied to the raw corpus*);
- vendor cleaning, `is_final` flagging, survivorship of the ticker list.

These are retrospective biases (**A3**, **LIM1**, **B2**, **B3**). **Under Reading E, E7 is not immune to every retrospective bias — contradicting §4.2's own justification.**

> **∴ Reading E is refuted. "Did not exist at registration" is metaphysical. L1 is not ambiguous — it carries two independent clauses that each force Reading M, and the corpus contains two realized instances of the bias Reading E would admit.**

---

## Phase 3 · Truth Table

Variables: **D-reading** ∈ {M, E} · **Blind content** ∈ {X = existing data sealed, F = reservation for future data}

| # | D-reading | Blind contains | Blind ⊨ D? | Accelerates? | **CU-13 true?** | **Status** | Why |
|---|---|---|---|---|---|---|---|
| **1** | **M** | **X** | **NO** | Yes | **FALSE** | **INCONSISTENT** | Data existed ⇒ not E7. **This row is the architecture's actual state** (§1.5–§1.6) |
| **2** | M | F | Yes | **No** | **FALSE** | **IMPOSSIBLE** | **F is not constructible.** T-C2 requires a **fingerprint** at REGISTERED; nonexistent data cannot be hashed. The object model **cannot express a reservation** |
| **3** | **E** | X | Yes | Yes | **TRUE** | **IMPOSSIBLE** | **Reading E is refuted** by §2.2 — L1's *"immune to every retrospective bias"* fails under it |
| **4** | E | F | Yes | No | **FALSE** | **IMPOSSIBLE** | Both defects: F not constructible **and** E refuted |

### 3.1 Reading the table

> **Exactly one row is possible. In it, CU-13 is false.**

- **Row 3 is CU-13's only home** — the sole combination under which its claim is true — and it is **impossible**, refuted by L1's justification clause, **not** by anything the Custody Model says.
- **Row 2 is the charitable reading** — "Blind means a reservation for future data" — and it is **impossible in this architecture**: T-C2 requires a fingerprint at REGISTERED, and **you cannot fingerprint what does not exist**. The object model has no `Reserved data` object. *And even if it did, row 2 still makes CU-13 false, because a reservation requires waiting.*
- **Row 1 is what the architecture actually specifies**, and CU-13 is false in it.

> **No interpretation rescues CU-13. RT-4 is not an interpretation artifact.**

---

## Phase 4 · Counterexamples

### 4.1 Attempt: construct a Blind partition that satisfies E7

**Construction:** declare a partition over a date range that has not yet occurred; let it fill as bars arrive; release at `release_date`.

| Test | Result |
|---|---|
| Satisfies **D** (metaphysical)? | **YES** — the bars did not exist at registration |
| Is it a **Dataset Partition** per the object model? | **NO.** T-C2 (CREATED→REGISTERED) requires **identity + fingerprint + lineage**. It has no fingerprint. T-C5 (PARTITIONED→LOCKED) requires *"every partition sealed"* — there is nothing to seal |
| Does it **accelerate**? | **NO** — you wait wall-clock time for the bars |

> **The only construction that reaches E7 is (a) not a Blind partition — it is not constructible in this object model at all — and (b) does not accelerate.** Both legs of CU-13 fail **even in its most charitable case.**

### 4.2 Attempt: construct a Blind partition that violates E7

**Construction:** carve a window from the existing corpus; set `release_date` to a future date; seal with no release path.

| Test | Result |
|---|---|
| Is it a valid Dataset Partition? | **YES** — has a fingerprint, seals, LOCKS |
| Satisfies **D**? | **NO** — the data existed |
| Immune to researcher look-ahead? | **YES** — nobody can read it |
| Immune to **corpus-construction** bias? | **NO** — universe, corporate actions, cleaning all applied with knowledge of the period |
| Is it E7? | **NO.** It is **E6-equivalent with maximal custody assurance** |
| Does CU-13 claim it is E7? | **YES** |

### 4.3 Which interpretation survives

> **§4.2's construction is the architecture's actual state. §4.1's is not constructible. RT-4 is CONFIRMED.**

### 4.4 What a Blind partition is actually worth — recovered, not discarded

The construction in §4.2 is **genuinely valuable**, and mislabeling it destroyed the ability to say why:

> **An ordinary OOS partition is C-SEALED but *releasable* — so per G-9 (no mechanism) it can be read, and per R6 nothing prevents it. A Blind partition has *no release path at all* until its date. It cannot be read by accident, by carelessness, or by the CRO.**
>
> **∴ its value is on the *custody* axis, not the evidence axis.** It provides the strongest obtainable assurance that a Confirmation window is **provably unspent** — because there was no way to spend it. **That strengthens the credibility of an E3 pre-registered OOS test. It does not create E7.**

**RFC-8 survives. Only its rationale was false.**

---

## Phase 5 · Minimal Resolution

### 5.1 Formal proof that RT-4 survives — two independent legs

```
Let D = "the data did not exist at registration"
Let I = "immune to every retrospective bias"      [L1 §4.2, E7's stated justification]
Let W = "accrues in wall-clock time; cannot be accelerated"   [L1 §4.2, cost paragraph]

L1 §4.2 asserts:  E7 ⟹ (D ∧ I ∧ W)

── LEG 1 (the D-leg) ──────────────────────────────────────────
1. Assume Reading E: D means "not available to the institution".
2. Then a sealed existing partition satisfies D.
3. But its corpus was constructed with knowledge of the period
   (universe, corporate actions, cleaning, survivorship).
   Two realized instances exist in this institution's own history.
4. ∴ ¬I  under Reading E.
5. L1 asserts I.  (4) ∧ (5) ⟹ ⊥.
6. ∴ Reading E is REFUTED.  D is metaphysical.               ∎

7. CUSTODY_MODEL §4.1: Dataset Partition has "fingerprint: its own".
   T-C2: CREATED → REGISTERED requires "identity + fingerprint + lineage".
8. A fingerprint hashes content; content requires existence.
9. ∴ every registrable partition — including Blind — contains
   data that EXISTS at registration.
10. ∴ ¬D for a Blind partition.  ∴ ¬E7.
11. CU-13 asserts E7.  (10) ∧ (11) ⟹ ⊥.                      ∎

── LEG 2 (the W-leg) — independent of D's reading ─────────────
12. L1 §4.2: W — E7 cannot be accelerated.
13. CU-13 / M5 / RFC-8: "without waiting in wall-clock time"
    ≡ acceleration.
14. (12) ∧ (13) ⟹ ⊥,  under EVERY reading of D.              ∎

── CONCLUSION ─────────────────────────────────────────────────
Two independent contradictions. Neither depends on the other.
RT-4 SURVIVES formalization.  It is not an interpretation artifact.
```

### 5.2 Classification

> ## RT-4 is **(1) a genuine architectural contradiction** — whose **minimal remedy is category A (terminology).**

**These are different questions and the brief's four options conflate them. Both answers are needed:**

| Question | Answer |
|---|---|
| **Is it a contradiction?** | **YES — genuine, architectural.** Two canonical rules cannot both hold. Survives all four truth-table rows |
| **Is it (2) a terminology conflict?** | **NO.** A terminology conflict is *one word, two meanings across documents.* **E7 has exactly one meaning — L1's.** CU-13 asserts an object satisfies a correctly-defined term when it provably does not. **That is a false proposition, not a naming collision** |
| **Is it (3) governance?** | **NO.** No governance dimension |
| **Is it (4) incorrect interpretation?** | **NO — disproven.** §3 shows no interpretation makes CU-13 true |
| **What does the remedy cost?** | **Category A. Four sentences.** Nothing structural changes |

### 5.3 The contradiction is **inert** — severity, not existence

**The criterion is restated three times in [[EVIDENCE_MODEL]], independently of CU-13:** K6 (§52), C4 (§102), and the **E6→E7 promotion guard (§175)**. **The promotion path does not read CU-13; it reads its own criterion.** A Blind partition would be **refused at E6→E7 by the guard itself**, and refused again at C4's definition.

**Further, the corpus already voids CU-13 by its own precedence rules:** §5.4 (*on scientific method, L1 wins*) and §0.4 (*a rule whose justifying proposition is refuted is void, not grandfathered*).

> **∴ CU-13 cannot promote anything. The contradiction is real and cannot propagate to a decision.** The red-team's *"licenses capital at scale"* was **overstated** — as the ARB already found.

**But inert ≠ absent.** Per **ISO 42010 §5.6** and L1 **§15**, an **unrecorded** inconsistency between canonical documents is a conformance defect, and **freezing** it would make the corpus permanently self-inconsistent at its top evidence tier. **A frozen baseline is the artifact future readers trust without re-deriving.**

### 5.4 Why category A, and not B, C, or D

| | Required? | Proof |
|---|---|---|
| **B · Definition correction** (amend L1 to disambiguate "did not exist") | **NO** | **§2.2: L1 is not ambiguous.** Two independent clauses — *"immune to every retrospective bias"* and *"cannot be accelerated"* — each force Reading M. **The ambiguity was in the author, not the text.** ⇒ **L1 is untouched. D-019's review package is undisturbed.** |
| **C · Cross-reference correction** | **NO** | CU-13's citation of §4.2 is **correct** — it cites the timebox accurately. The *reference* is right; the *claim* is wrong |
| **D · Architectural correction** | **NO** | Nothing structural changes: the Blind partition **object**, its **C-SEALED** class, `release_date`, the **state machine**, **T-C2/T-C5**, **CU-14**, **§5.4 release policy** — all stand exactly as specified. **RFC-8 survives** |
| **A · Terminology correction** | **YES — and it is sufficient** | Four sentences misapply a correctly-defined term to an object that provably fails its definition |

---

## Phase 6 · Impact Analysis

| Document | Impact | Why |
|---|---|---|
| **[[01_SCIENTIFIC_FOUNDATION]]** | **NONE** | Not ambiguous (§2.2). **Untouched — D-019 undisturbed** |
| **[[EVIDENCE_MODEL]]** | **NONE** | Its K6, C4, and E6→E7 guards **independently restate the criterion and are already correct** |
| **[[RESEARCH_OBJECT_MODEL]]** | **NONE** | The Dataset Partition object is correct as specified — **its fingerprint requirement is what proves CU-13 wrong** |
| **[[RESEARCH_VALIDATION_FRAMEWORK]]** | **NONE** | — |
| **[[EXPERIMENT_STANDARD]]** | **NONE** | — |
| **[[RESEARCH_OS_MASTER_ROADMAP]]** | **NONE** | RFC-8 lives in [[CUSTODY_AMENDMENT]] |
| **Research OS structure** | **NONE** | No layer, object, state, rule, or class changes |
| **[[CUSTODY_MODEL]]** | **2 edits** | CU-13 (§289) · §5.3 Blind row (§285) |
| **[[CUSTODY_AMENDMENT]]** | **2 edits** | M5 (§207) · RFC-8 (§226) |

> **Total: four sentences, in two documents, both uncommitted. Zero impact on any certified artifact. Zero impact on any object, state, or rule.**

---

## 7. Amendment applied

Per the brief — *"If the contradiction survives, prove why no interpretation can eliminate it. **Only then may a document be amended**"* — §5.1 discharges the proof. The minimal correction is applied at §6's four sites and **nowhere else**.

**Recorded in [[DECISION_LOG]] D-023.**

---

## 8. Verdict

1. **Formal proof:** §5.1 — two independent contradictions (D-leg, W-leg), neither dependent on the other.
2. **Reasoning:** §2.2 refutes Reading E from L1's own justification clause; §1.5–§1.6 prove every registrable partition contains existing data; §3 shows exactly one truth-table row is possible and CU-13 is false in it.
3. **Minimal correction:** **Category A — terminology.** Four sentences. Blind = **E6-equivalent with maximal custody assurance**, not E7. Acceleration claim deleted.
4. **Why no larger correction:** L1 is unambiguous (⇒ not B); the citation is correct (⇒ not C); no object, state, class, or rule changes (⇒ not D). **RFC-8 survives with a corrected rationale — its custody value was real; only its evidence claim was false.**
5. **Does RT-4 remain a freeze blocker?**

> ## ❌ NO — RT-4 is **RESOLVED** and no longer blocks freeze.
>
> **Remaining blockers: G-8 (L1 unsigned, D-019) and G-9 (Dataset Custody unmechanised).** Both predate this contradiction; neither is architectural.

**The contradiction did not disappear under formalization — it hardened.** Formalization eliminated the ambiguity that made it arguable and proved it survives every interpretation. **What formalization did dissolve was its *severity*: it is inert, cannot propagate, and costs four sentences.**

> **A closing note the Board considers material.** RT-4 was the only red-team finding to survive adjudication, and it is the one where the author reached for a term because **no term existed for the thing he had built.** A Blind partition is genuinely valuable — it is the only asset with *no release path*, which makes its window **provably unspent** rather than merely *supposed* to be. **The architecture had no name for that, so the author took the nearest impressive label.** The correction gives the thing its true name and keeps the thing.
