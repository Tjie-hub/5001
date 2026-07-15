# Experiment Standard

> **Invoked from [[RESEARCH_PROTOCOL]] §4 at Stage S6. Read before you run anything.**

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1) · **Layer:** L2 — Research Architecture (procedural)
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version). **Does NOT supersede** [[RESEARCH_VALIDATION_FRAMEWORK]] or [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] S6.
**Realized in v3:** `research.tracking` (run_id, dataset_fingerprint, git_commit) realizes §4's provenance capture · `research/gatekeeper` realizes S7–S8 · research/production fence realizes part of §3's custody. **The one-shot custody receipt (§3.2) has no realization** — it is currently procedure, not mechanism. See §7.
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **§2.4 (custody), R6 (custody must be enforced)**, R5 (pre-registration), R2 (capable of failing), §8 (reproducibility), R7.4 (threshold migration)
**Governance:** [[DECISION_LOG]] **D-021**

---

## 0. Scope

**Procedure only.** *What* an experiment must satisfy is specified in [[RESEARCH_OBJECT_SCHEMA]] §3.6 (O6), [[HYPOTHESIS_LIFECYCLE]] T5–T7, and [[RESEARCH_VALIDATION_FRAMEWORK]]. Per **PR-1**, this document sequences those; it never restates them.

**One rule governs everything here:**

> **§2.4 / R6 — out-of-sample data is a non-renewable resource.** *"It can be spent exactly once per hypothesis, and every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged. **This invisibility is precisely why it requires a mechanism.**"*

Everything below is the operational consequence of that one sentence.

---

## 1. Before you begin: the three questions

Answer these before opening a terminal. Each is free; each kills experiments that would otherwise cost an out-of-sample window.

| # | Question | If the answer is bad |
|---|---|---|
| **1** | **Could this test fail?** Run the power/MDE analysis (**R2**) | **DO NOT RUN IT.** *"Corroboration from a test that could not have refuted the hypothesis carries zero evidential weight."* An unpowered test produces **no evidence either way** — running it spends custody for nothing |
| **2** | **Is the predicted effect larger than the friction to capture it?** (**PR-3**) | **F4 at zero cost.** An effect smaller than its own cost is a *confirmed irrelevance* (§5.5). Learn this now, not at S8 |
| **3** | **Is the hypothesis frozen and does it contain all six?** ([[RESEARCH_PROTOCOL]] §5.2) | **Not registered ⇒ no experiment.** There is nothing to test |

> **Rule EX-1 (justified by R2, R6):** **Question 1 is a hard stop, and it is the one you will want to skip.** An underpowered test feels like cheap information. It is not information at all, and it **permanently spends the OOS window** for the hypothesis it was run against. Per §2.4 that window does not regenerate. **You get one.**

---

## 2. Pre-flight checklist

Nothing below is optional. Each line corresponds to a way a completed experiment is later discovered to be void.

```
FROZEN OBJECTS — verify each is frozen, not merely written
[ ] Hypothesis frozen at G1              (HL-2 — no post-G1 edits exist)
[ ] Mechanism `authored_at` PREDATES     (OS-6 — §7.3. If it postdates,
    every experiment in its `blind_to`         the mechanism is a counterfeit
                                               and the claim is already void)
[ ] Features frozen, G2 passed           (OS-4)
[ ] Cost model frozen BEFORE this run    (OS-4 — a cost model chosen after
                                          seeing a result is R7.4)
[ ] Dataset fingerprinted, not named     (bind the hash; a silent upstream
                                          revision is F7 through the back door)

CUSTODY — the part that cannot be undone
[ ] OOS period declared in the frozen hypothesis
[ ] OOS has NEVER been touched for this hypothesis  ← §3
[ ] Custody receipt ready to write (who, when, once)

FAMILY — the part everyone gets wrong
[ ] Family declared, and this test counted in it    (R7.5)
[ ] Family size recorded AT EXECUTION TIME
[ ] Every prior variant / re-run / dead sibling is IN the count
                                          (PG-4 — N+1, never a retry of Nth)

CRITERION — read it, do not recall it
[ ] Ex-ante criterion read VERBATIM from the frozen object
[ ] Effect-size floor read verbatim      (significance alone is insufficient)
[ ] Refutation condition read verbatim   (R14)

PROVENANCE — the X2 minimum, or the result will not exist
[ ] run_id · git_commit · seed · environment · dataset fingerprints
    · cost_model_ref · family_ref                (OS-2 — incomplete ⇒ X0 ⇒ VOID)
```

> **Rule EX-2 (justified by R7.4):** **Read the criterion; do not recall it.** You remember it as more favourable than it is. This is not a character flaw — it is why R5 exists. **Open the frozen object and read the string.**

---

## 3. Custody — the one-shot rule

### 3.1 The three states

Per **§2.4**, and they are not a workflow — they are *what you are licensed to do*:

| State | Licensed | Data |
|---|---|---|
| **Discovery** | Conjecture, exploration, **unlimited searching**, no claims | In-sample only. **Nothing found here is knowledge. It is hypothesis material** |
| **Confirmation** | **One** severe, pre-registered test of **one** registered conjecture | OOS, **opened once**, against ex-ante criteria |
| **Accepted Knowledge** | Provisional institutional belief | **Sealed.** Further contact requires re-registration |

### 3.2 The procedure

```
BEFORE:  OOS is sealed. You do not look. Not to sanity-check.
         Not to "verify the data loaded." Not once.

OPEN:    Write the custody receipt FIRST:
           - which hypothesis (frozen id)
           - who opened it
           - when
           - which OOS partition
         THEN execute. Once.

AFTER:   The window is spent for this hypothesis. Forever.
         A second look is a SECOND EXPERIMENT, counted in the family,
         against a window that is now in-sample.
```

> **Rule EX-3 (justified by R6, §2.4):** **A glance is an open.** There is no read that does not count — not a plot, not a row count, not a debug print of a head. Per §2.4 *"every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged."*
>
> **The data looks identical afterward. That is the entire problem.** You cannot detect the conversion by inspecting the data, the code, or the result. Only the receipt distinguishes a clean window from a spent one — **so the receipt is the window's only evidence of its own state.**

> **Rule EX-4 (justified by R6, OS-5):** If you **can** read the OOS partition without writing a receipt, **that is a defect in the system, not a permission.** Per **R6**, custody enforced by your discipline is *"a statement of intent, not a control."* **Report it as a finding.**
>
> **Current status: this is exactly the case.** OOS custody is presently **policy, not mechanism** — review finding W9, and L1 §2.4's position on it is blunt: *"the policy formulation is epistemologically void, because unenforced custody produces a system whose evidential state cannot be known even by its own operators."* Recorded as **Gap G-9** ([[PROTOCOL_LAYER_DELIVERY]] §5). Until it is mechanised, **you are the control, and per R6 that means there is no control.**

### 3.3 What to do if you contaminate a window

**Report it. Immediately. Do not proceed.**

```
1. Record the breach: what was seen, when, by whom.
2. The hypothesis degrades: DG9 → E3+ lost → E2 → C ≤ C1.
3. The window is in-sample. Permanently. For this hypothesis.
4. If you still want to test the mechanism: NEW hypothesis,
   NEW registration, counted afresh, against a DIFFERENT window
   — or forward data that does not yet exist (E7).
```

> **There is no penalty for reporting this and there must never be one.** Per **R12** and §5.3, an unreported breach is worse than the breach: it produces a claim whose evidential state is **unknowable**, and per **LIM8** unknowable is indistinguishable from clean. **An institution that punishes the report guarantees it never hears one.**

---

## 4. Execution

```
[ ] Log the seed. Before, not after.
[ ] Log the environment: interpreter, library versions, hardware class.
[ ] Log the git commit. Dirty tree ⇒ DO NOT RUN. The commit is the
    specification; an uncommitted change is an unspecified experiment.
[ ] Bind dataset FINGERPRINTS, not names.
[ ] Run ONCE.
[ ] Do not tune. Do not inspect intermediate output and adjust.
    A tuned run is a NEW experiment, counted in the family (PG-4).
```

> **Rule EX-5 (justified by R19, OS-2):** **If the provenance set is incomplete, the result does not exist.** Not "is weakly supported" — **X0, void** (**R19**). Per §8.5 this will sometimes void a result you believe is true, over a lost seed. *"That is the rule working."*

### 4.1 On bit-identity

**You are not required to produce bit-identical output.** Per **§8.3** and **ADR-L1-005** the requirement is **conclusion-invariance under independent re-execution** — same sign, same rejection or non-rejection of the null, same order of effect magnitude.

> **Recorded inconsistency (G-7, inherited).** [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] S5 states *"bit-identical reproducibility across redundant compute nodes"* as a validation criterion. **L1 §8.3 does not require this and explicitly declines to** — bit-identity is construction-hard (SIMD reassociation, FMA contraction, BLAS thread nondeterminism) and is *sufficient but not necessary*. Per **ADR-L1-008** the corpus **records** such inconsistencies rather than resolving them. **Follow L1: conclusion-invariance.** If you cannot achieve bit-identity, that is not a defect in your experiment.

---

## 5. After the run

### 5.1 It failed

**Normal. Valuable. Go to [[RESEARCH_PROTOCOL]] §5.3 and follow it exactly.**

Record the Failure Entry with **exactly one** F-mode and a **defended** attribution (**R1**). Then stop. **Do not do any of the five things in R15** — and you will want to do at least one of them, because you will genuinely believe it is the right call.

### 5.2 It passed

```
[ ] Criterion met VERBATIM as frozen?     Near-miss ⇒ MISS. (R7.4)
[ ] Survives friction, registered cost model?             (F4)
[ ] Severity argument WRITTEN, in prose?                  (R3/EV-3)
    "what would have had to be true for this test to have caught
     the error, and was the test in fact capable of that?"
[ ] TRUE family denominator computed — every variant, re-run,
    and dead sibling included?                            (R7.5, LIM3)
[ ] Tier assigned honestly?                               (E0-E7)
[ ] → S7/S8 gatekeeper, then S9.
    ██ At N=1 you stop at S9. C2 ceiling. See RESEARCH_PROTOCOL §7 ██
```

> **Rule EX-6 (justified by R11, §4.3):** **The number does not carry its weight.** *"A t-statistic of 3.0 from a single pre-registered test and a t-statistic of 3.0 selected from two hundred searched variants are not the same evidence, and no property of the number itself distinguishes them."*
>
> **This is not hypothetical here.** Program P0's NR7 BULL edge is significant against zero — CI [+0.32, +2.06] — **and its DSR collapses under its 42-cell family.** **E-high, C-low.** The family was decisive; the effect was not. **Expect this outcome. It is the most common way a real-looking result dies, and it dies for a correct reason.**

### 5.3 The five prohibited moves

You have a result. You want a better one. **These do not exist as options** ([[HYPOTHESIS_LIFECYCLE]] §5, X1–X10):

| ✗ | The move | Why you will want it |
|---|---|---|
| **X1** | Adjust the criterion after a near-miss | It is *so close* and the threshold was arbitrary anyway |
| **X2** | Re-run with different parameters, report the survivor | The first parameterization was clearly wrong |
| **X3** | Narrow the universe/period until it passes | The excluded names are obviously different |
| **X4** | Add a filter discovered from the failure | The filter genuinely explains what happened |
| **X10** | Extend the window until it passes | It just needs more time |

**Each is locally reasonable. That is what makes them dangerous.** Per §5.4, a rescued claim is *indistinguishable from a survived one*, so no reviewer can catch you — **including you.**

**The only path forward from a failure: a NEW hypothesis, NEW registration, counted afresh in the family** (**R15**).

---

## 6. Re-running

> **Rule EX-7 (justified by PG-4, R7.5, R15):** **Every re-run is a new family member.** N+1. Never a retry of the Nth.
>
> This is not bookkeeping. Per **R15**, *"splitting one dead claim into variants until one survives"* is prohibited, and the append-only family (**OS-10**) is what makes the split **visible in the denominator** rather than invisible in a revision. **A re-run that does not grow the family has narrowed it** — which is **R7.5**, performed by omission.

| You want to re-run because… | Verdict |
|---|---|
| The code had a genuine bug | **Fix, re-run. Family grows. Record both runs** — the buggy one is the denominator's business too |
| An upstream dependency changed | **New Feature version** (branch-on-upstream-change). New experiment. Family grows |
| A different parameterization "makes more sense" | **X2. Prohibited.** Unless registered ex ante as a declared variant — in which case it was already in the family |
| The cost model was revised | **HL-4 may apply — but only if** the revision was authored **blind to this hypothesis's fate** (condition 2). A cost model revised *because* it killed a claim you liked is **R7.4 relocated to an auxiliary, where it is harder to see** |
| It nearly passed | **X1. Prohibited.** A near-miss is a miss |

---

## 7. Known gaps

Per **ADR-L1-008** — record, do not resolve. See [[PROTOCOL_LAYER_DELIVERY]] §5.

| # | Gap | Consequence |
|---|---|---|
| **G-9** | **OOS custody is policy, not mechanism** (review W9). §3.2's receipt is procedure; nothing enforces it | **Per R6 there is no control.** Per L1 §2.4 the policy formulation is *"epistemologically void — unenforced custody produces a system whose evidential state cannot be known even by its own operators."* **The most consequential unmechanised rule in the corpus** |
| **G-7** | Pipeline S5 requires **bit-identity**; L1 §8.3 requires **conclusion-invariance** and declines bit-identity | Follow L1. Recorded per ADR-L1-008, inherited from [[KNOWLEDGE_CORPUS_DELIVERY]] |
| **G-10** | **Family size at execution has no enforcement** — nothing prevents recording a smaller N | **R7.5 by omission** is currently undetectable. Depends on O14 (**G-1**, proposed) |

---

## 8. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §3 custody procedure | **§2.4, R6** | The three states' definitions |
| §2 pre-flight | [[RESEARCH_OBJECT_SCHEMA]] §3.6 (O6), [[HYPOTHESIS_LIFECYCLE]] T5 | O6's field list |
| §5.2 pass procedure | R7.4, R3, EV-3, R11 | The severity criterion |
| §5.3 / §6 prohibitions | **[[HYPOTHESIS_LIFECYCLE]] §5 (X1–X10)**, R15 | X1–X10 — cited, not re-argued |
| §4.1 bit-identity | **§8.3, ADR-L1-005** | §8.3's argument |
| EX-1 power | **R2** | R2 |
| EX-7 re-runs | **PG-4, OS-10** | OS-10 |

**Invoked from:** [[RESEARCH_PROTOCOL]] §4 (S6). **Feeds:** [[RESEARCH_VALIDATION_FRAMEWORK]] / `research/gatekeeper` (S7–S8) · [[PEER_REVIEW_STANDARD]] (S9) · [[FAILURE_LIBRARY_SCHEMA]] (on failure).
