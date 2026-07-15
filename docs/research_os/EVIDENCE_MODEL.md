# Evidence Model

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see §0.3) · **Layer:** L1 — Scientific Foundation
**Owner:** Chief Research Scientist · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** partial — `research/gatekeeper` (8-stage pipeline) computes the statistical inputs to tier assignment; `research.tracking` (run_id, dataset_fingerprint, git_commit) supplies the reproducibility evidence §4 grades; R-10 receipt-bound `set_status` is the only existing enforcement of a promotion rule. **No v3 component implements degradation (§6).**
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §4 (philosophy of evidence: P5, R10–R13; tiers **E0–E7**), §2.1 (severity, R2/R3), §2.4 (custody states), §5.3 (F1–F9), §8 (reproducibility: P8, R19), §10 (LIM1–LIM8)
**Governance:** [[RESEARCH_OS_MASTER_ROADMAP]] §2 (L1), §5 (validation enhancements), [[DECISION_LOG]] **D-020**

---

## 0. Authority and scope

### 0.1 The three-axis thesis

[[01_SCIENTIFIC_FOUNDATION]] §4.2 owns the **evidence tier scale E0–E7** and R10 sets the floor (no Accepted Knowledge below E4). This document does not restate that scale, may not renumber it, and may not add tiers.

What L1 leaves undefined is everything *around* the tier. A tier answers one question — *what kind of test did this claim survive?* — and an institution needs two more answers that the tier cannot give:

> **The Evidence Model's founding claim: evidence tier, institutional confidence, and reproducibility are three distinct axes, and collapsing any two of them is how a research institution comes to believe something it has not established.**

| Axis | Question | Property of | Owner |
|---|---|---|---|
| **E0–E7** | *What test was survived?* | **the test** | [[01_SCIENTIFIC_FOUNDATION]] §4.2 — **not this document** |
| **C0–C4** | *How much does the institution believe it?* | **the belief** | §3 here |
| **X0–X4** | *Does the claim exist at all?* | **the specification** | §4 here |

The axes are orthogonal in principle and constrained in practice. A claim can be E5 and C1 (a strong test, weakly believed — because it is one of forty in its family). A claim can be E6 and X0 (independently reproduced, yet its own specification lost — a real and absurd state, and the reason X exists as an axis). **The constraints between axes are the substance of §5 and §6.**

### 0.2 Why the collapse is the default failure

The natural human operation is to read a strong test as a strong belief. §4.3 forbids it: *"the evidential weight of a result is not recoverable from the result."* A t-statistic of 3.0 from one pre-registered test and a t-statistic of 3.0 selected from two hundred searched variants are the same number, the same tier-eligible test, and **not the same evidence** — and nothing about the number distinguishes them.

So tier alone cannot carry belief. The missing ingredient is the *family* the test came from and the *process* that produced it, and those are C-axis facts. An institution with only an E-axis has no vocabulary for "this was a severe test and I still don't believe it," which is the correct state for most severe tests in a large family.

### 0.3 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready, NOT FROZEN**; one open condition ([[DECISION_LOG]] **D-018/D-019**). If review alters E0–E7 or R10, §5's promotion rules are void pending re-derivation, not grandfathered.

---

## 1. Evidence classes

Before tiering, evidence is **classified**. Class is a statement about the *kind* of thing being offered; tier is a statement about its strength. A class error cannot be repaired by a tier — this is R10's point that E0/E1 claims are *category errors, not weak claims*.

| Class | What it is | Admissible as | Ceiling |
|---|---|---|---|
| **K1 · Theoretical** | An argument from market micro-economics that a mechanism must or cannot operate | **Refutation (F1)** and mechanism authorship | Cannot support a claim alone; **can kill one outright** |
| **K2 · Literature** | A published finding about *another* market or period | **Hypothesis material only** ([[LITERATURE_RESEARCH_STANDARD]]) | **E1** — never higher, in any quantity |
| **K3 · Observational** | A pattern measured in our own data | Depends entirely on custody (§2.4) | E0 in Discovery; up to E7 in Confirmation |
| **K4 · Experimental** | The outcome of a pre-registered test against ex-ante criteria | The institution's primary evidence | E3–E7 |
| **K5 · Replicative** | Independent re-derivation from specification alone | Promotion to E6 (§5) | E6 |
| **K6 · Forward** | Outcome on data that did not exist at registration | Promotion to E7 | **E7 — strongest obtainable** |
| **K7 · Adversarial** | A reviewer's competent attempt at refutation | Refutation, or C-axis promotion (§5.3) | Cannot raise E; **can raise C, and can destroy both** |

> **Rule EV-1 (justified by R10, §4.2):** Class ceilings are **absolute and not aggregable**. A hundred K2 literature findings remain E1. This is not conservatism — it is what "evidence about a different market" means: it is evidence about *that* market. Volume does not convert it into evidence about ours, and treating a literature consensus as strong evidence is the specific error §6.4 warns about, since consensus marks exactly where deviation is least likely to survive.

> **Rule EV-2 (justified by K1's ceiling, §5.3 F1):** **K1 is asymmetric and that asymmetry is the institution's cheapest instrument.** A theoretical argument can *kill* a claim outright (F1) without touching data, custody, or multiplicity budget. It can never *establish* one. An institution that uses K1 only to defend claims has inverted its most valuable tool.

---

## 2. Acceptable and unacceptable evidence

### 2.1 Unacceptable — refused, not discounted

Per R10, these are **category errors**. The correct response is rejection, not a lower weight. A discounted category error is still a category error, and discounting it teaches the institution that the error is a matter of degree.

| # | Offered as evidence | Why it is not evidence | L1 |
|---|---|---|---|
| **U1** | Realized profit | Both fortune and error produce returns | R7.1 |
| **U2** | "This survived after we discarded what didn't work" | Describes a selection process, not a discovery | R7.2 |
| **U3** | A mechanism authored after seeing the result | Constrains nothing; was guaranteed available | R7.3, §7.3 |
| **U4** | A result meeting a criterion adjusted after a near-miss | Moving the criterion deletes the test | R7.4 |
| **U5** | A survivor after the family was narrowed post hoc | The denominator is part of the claim | R7.5, §5.2.6 |
| **U6** | "The model is too complex to explain" | Reports our ignorance, not the market's structure | R7.6 |
| **U7** | A result from an underpowered test | Not weak evidence — **no evidence** | **R2** |
| **U8** | A result that cannot be reproduced from its specification | **Void, not pending** | **R19**, F6 |
| **U9** | In-sample fit, however strong | Guaranteed by search; discriminates nothing | E0, §2.4 |
| **U10** | Statistical significance without a mechanism | Violates P2 | E1, **R18** |
| **U11** | Sunk research cost, elegance, or effort | Not evidence of anything about the market | **R13** |
| **U12** | An extended forward-test window that finally passed | Threshold migration wearing a calendar | §4.2, R7.4 |

**U7 deserves separate emphasis because it is counter-intuitive and is routinely mishandled.** The instinct is that a weak test gives weak evidence. R2 says otherwise: *corroboration from a test that could not have refuted the hypothesis carries **zero** evidential weight.* An underpowered confirmation is not 20% of a confirmation. It is an **error of kind, not of degree** — and reporting it as "suggestive" is precisely how the error propagates, because "suggestive" is a C-axis word applied to something with no E-axis standing.

### 2.2 Acceptable

Evidence is acceptable when: its class permits the tier claimed (§1); the test was capable of failing (**R2**); a severity argument accompanies any claim of support (**R3**); the multiplicity family was declared before and not narrowed after (§5.2.6, R7.5); the custody state permitted the operation (**§2.4**); and the result is reproducible at X≥2 (§4).

> **Rule EV-3 (justified by R3):** A severity argument is a **positive obligation on the proponent**, discharged in prose, not by citing a p-value. It must answer: *what would have had to be true for this test to have caught the error, and was the test in fact capable of that?* An unanswered severity question means the claim is not yet evidence, whatever it measured. Per **R4** this burden never transfers to the skeptic — "you haven't shown the test was insensitive" is not a defense.

---

## 3. Confidence levels (C0–C4)

Confidence is **the institution's degree of belief**, and it is a distinct axis because §4.3 makes evidential weight a property of the *process*, not the result. Two claims at the same tier can warrant very different belief.

| C | Name | Meaning | What it licenses |
|---|---|---|---|
| **C0** | **None** | No belief. A conjecture or a category error. | Study only |
| **C1** | **Weak** | Believed more likely than not, and **the institution expects to be wrong often at this level** | Continued study; **no capital** |
| **C2** | **Moderate** | Survived a severe test; not yet independent of its author or its family | Shadow deployment; **no capital** |
| **C3** | **Strong** | Survived severe testing, friction, and independent reproduction | **Capital, under decay monitoring** |
| **C4** | **Institutional** | C3 + forward evidence on data that did not exist at registration | Capital at scale; used as a reference for other claims |

> **Rule EV-4 (justified by R4, §2.2):** **Confidence is capped by tier, never raised by it.** C ≤ f(E) per §5.1, and within that cap C is set by the *process* facts — family size, author independence, custody integrity, severity. A severe test in a 42-member family may be E5 and C1. This is not a contradiction; it is the E/C distinction doing exactly the work it exists for, and it is a live state in this institution: Program P0's NR7 BULL edge is significant against zero yet its DSR collapses under a 42-cell family ([[RESEARCH_OS_MASTER_ROADMAP]] §3; Phase B research record). **E-high, C-low is the correct reading of that finding**, and an institution without a C axis has no way to write it down.

> **Rule EV-5 (justified by R13, P4):** Confidence never rises from: how much the claim is wanted, what it cost, how elegant it is, how long it has been believed, or how much capital already depends on it. **The last is the most dangerous and the least often stated**, because it inverts the causal order the institution exists to protect (§0.1 of L1: capital consumes knowledge; knowledge never consumes capital outcomes).

### 3.1 Confidence is not probability

C is an **ordinal institutional state**, not a subjective probability. This is a deliberate consequence of ADR-L1-002 (critical rationalism, not Bayesian epistemology): the institution does not maintain a posterior over hypotheses, because per **LIM3** the multiplicity denominator is *estimable, not knowable*, and a posterior conditioned on an unknowable denominator is a number with the appearance of rigor and none of its content. C says what the institution will *do*, not what it thinks the odds are.

---

## 4. Reproducibility levels (X0–X4)

Per **P8**, an irreproducible result *is not a result*. X is therefore not a quality axis — it is an **existence axis**, and it is the only axis where the bottom value means the claim is not merely unsupported but absent.

Per **§8.3** and **ADR-L1-005**, the requirement is **conclusion-invariance under independent re-execution**, explicitly *not* bit-identity. L1's position: bit-identity is sufficient but not necessary, and is construction-hard (SIMD reassociation, FMA contraction, BLAS thread nondeterminism defeat it across hardware). This document adopts L1's requirement, not the stricter one.

| X | Name | Test | Consequence |
|---|---|---|---|
| **X0** | **Irreproducible** | Cannot be re-executed at all | **VOID (F6)** — withdrawn; Accepted status revoked (**R19**) |
| **X1** | **Re-runnable** | The original author re-runs it and gets the same conclusion | Necessary, worth nothing alone — proves the author's machine is deterministic |
| **X2** | **Specified** | Specification is complete enough that a competent stranger *could* re-derive the conclusion | **Minimum for any tier ≥E3** |
| **X3** | **Reproduced** | An independent party *did* re-derive the same conclusion from the specification alone | Required for **E6** |
| **X4** | **Reproduced under variation** | Same conclusion re-derived under deliberate variation of incidental choices (environment, seed, library, tie-breaks) | Distinguishes the mechanism from the implementation |

> **Rule EV-6 (justified by R19, §8.4):** **X0 is void, not pending.** Not "provisional," not "weak evidence." Withdrawn, with any Accepted Knowledge status revoked. Per **§8.5**, this will sometimes void results the institution believes are true, for reasons that feel incidental — a lost seed, an unrecorded environment. *That is the rule working.* An exception granted for a result we like replaces R19 with "reproducibility is required except when inconvenient," which is threshold migration applied to method. **And the pressure for the exception will come precisely from the evidence that the claim is true** — which is why the exception must be unavailable in advance rather than declined in the moment.

> **Rule EV-7 (justified by §8.2, adversarial argument):** Irreproducibility is not a gap; it is **structural immunity from criticism**. A result that cannot be re-executed cannot be attacked, and per **P3** a claim immune from criticism is not a knowledge claim. This is why X0 removes a claim from the class of things that can be true or false, rather than placing it low on a scale of support.

### 4.1 X4 and the single-institution limit

**X3 is the highest level this institution can currently reach, and X3 here is weaker than X3 elsewhere.** Per **LIM5** (*single-institution replication is weak replication*), a "reproduction" performed inside this institution shares its data vendor, its cost model, its universe construction, and its assumptions. It tests the *specification's completeness*, which is genuine and valuable — it does **not** test the *result's robustness to those shared choices*.

X4 exists in this scale specifically to name what LIM5 makes unavailable: reproduction under variation of incidental choices is the level at which mechanism and implementation separate, and it is **structurally out of reach** at this scale. This is recorded here, in the scale, so that an X3 claim is never read as an X4 claim by an institution that has forgotten it only has one lab.

---

## 5. Promotion rules

Promotion moves a claim **up** an axis. Every promotion requires a **positive act with an evidentiary receipt** — never the passage of time, never the absence of contrary evidence.

> **Rule EV-8 (justified by R4, §2.2):** **Nothing promotes by default.** The burden rests permanently on the proponent (R4); "no one has refuted it" is not a promotion event, it is the *absence* of a demotion event. An institution that promotes on silence has inverted R4 and made the skeptic responsible for the claim.

### 5.1 The C ≤ f(E, X) constraint

Confidence is capped by the weaker of tier and reproducibility. The cap is a **ceiling, not a floor** — meeting it does not earn the confidence, it merely permits it.

| Evidence tier | Reproducibility | **Maximum confidence** |
|---|---|---|
| E0 / E1 | any | **C0** — category error (R10) |
| E2 | ≥X2 | **C1** |
| E3 | ≥X2 | **C1** — below R10's E4 floor: severe test, still no capital |
| E4 | ≥X2 | **C2** |
| E5 | ≥X3 | **C3** |
| E6 | ≥X3 | **C3** |
| E7 | ≥X3 | **C4** |
| any | **X0** | **VOID** — not C0. The claim does not exist (R19). |

**Reading the table where it matters:** E4 caps at C2, and C2 does not license capital. R10 makes E4 the *floor* for Accepted Knowledge, not its sufficient condition — the floor is where the conversation starts. Capital requires **C3**, which requires **E5 + X3**: a severe pre-registered out-of-sample test, surviving realistic friction, stable across regimes or with a declared regime scope, **and** independently reproduced from specification alone.

### 5.2 E-axis promotion

The E scale is L1's; this document specifies only the **events** that move a claim along it.

| Promotion | Required event | Guard |
|---|---|---|
| E0→E1 | A statistically detectable pattern | Still C0. E1 is not progress toward acceptance; it is a *label for a category error* |
| E1→E2 | A mechanism authored **blind to this result**, classified to a sub-class of [[ECONOMIC_MECHANISM_TAXONOMY]] | **The blindness is the whole content** (§7.3). A mechanism authored after the result is U3 and produces a *counterfeit* E2 — indistinguishable from genuine by inspection, which is why the ordering must be enforced by process (S2→S3→S6), never judged at review |
| E2→E3 | A pre-registered OOS test, against ex-ante criteria, that **was capable of failing** | R2 + R5. Custody must have been *enforced*, not requested (**R6**) — an unlogged glance silently converted the OOS data to in-sample while leaving its appearance unchanged |
| E3→E4 | Survives realistic friction under a versioned cost model (D4) | The cost model must be the one registered ex ante, not one selected after |
| E4→E5 | Stable across regimes, **or** with a regime scope declared *ex ante* | **A5 binds** — regimes are constructs, never measurements. A post-hoc regime scope is R7.4 |
| E5→E6 | **X3 achieved** — independently reproduced from specification alone | Reproduction by the author is X1, not X3. Per **LIM5** this is weak replication and the E6 must say so |
| E6→E7 | Forward-tested on data that did not exist at registration, within a **timebox fixed ex ante** | **§4.2 is explicit and absolute:** the timebox is never extended to rescue a claim. A claim that fails forward *fails*; a claim that runs out of time is **unproven, not proven** (U12) |

### 5.3 C-axis promotion

Confidence rises only through events that attack the *process* facts the tier cannot see:

| Promotion | Required event |
|---|---|
| C0→C1 | Tier cap permits it **and** the multiplicity family is declared, sized, and **not narrowed** (R7.5) |
| C1→C2 | Tier cap permits **and** a **K7 adversarial review** was conducted by someone other than the author and failed to refute |
| C2→C3 | Tier cap permits (E5+X3) **and** the claim is independent of its author (X3) **and** friction is charged under a versioned cost model |
| C3→C4 | Tier cap permits (E7) **and** a decay monitor has been live throughout the forward window without triggering |

> **Rule EV-9 (justified by LIM6, ADR-L1-007, D-019):** **C2 is the institution's practical ceiling for a single-researcher claim**, and this is a structural fact, not a temporary staffing gap. C1→C2 requires K7 adversarial review *by someone other than the author*. Per **LIM6** (adversarial review is structurally compromised at this scale) and **LIM8** (self-certification is epistemically indistinguishable from genuine certification), the author cannot supply it. **This is the same constraint that leaves Phase A itself at GO WITH CONDITIONS** (D-019): one open condition, an external signature, undischargeable from inside. The evidence model and its own foundation are blocked by the identical limit — and the honest response is to record the ceiling, not to lower the bar until the institution can reach it.

### 5.4 X-axis promotion

| Promotion | Required event |
|---|---|
| X0→X1 | Result re-executes for its author |
| X1→X2 | Specification complete: hypothesis, methodology, identified data, cost model, family declaration, environment |
| X2→X3 | An independent party re-derives the **same conclusion** — sign, rejection/non-rejection, order of magnitude (**§8.3**) — from the specification **alone** |
| X3→X4 | Same conclusion under deliberate variation of incidental choices. **Structurally unavailable — LIM5, §4.1** |

---

## 6. Degradation rules

**This section has no counterpart in the existing corpus.** L1 supplies the raw material — **P7** (every inefficiency has a finite half-life), **F9** (decay), **R19** (void on reproduction failure) — but specifies no graded degradation, and no v3 component implements one. §6 is the substance of this document's extension.

The asymmetry with §5 is deliberate and is R4 made operational: **promotion requires an event; degradation may occur by the world changing.** A claim can rot without anyone doing anything wrong.

### 6.1 Degradation triggers

| # | Trigger | Effect | Basis |
|---|---|---|---|
| **DG1** | **Reproduction fails** at any later date | → **X0 → VOID**, immediately, at any C | **R19**, F6 |
| **DG2** | **Generating constraint removed** — rule change, mandate change, participant exit | → **C0**, claim **RETIRED** (not falsified) | **P7**, F9, D3 |
| **DG3** | **Decay detected** — the effect is measurably gone | → **C ≤ C1**, RM6 | F9, **LIM7** |
| **DG4** | **Family denominator grows** — later tests reveal the family was larger than declared | → **C reduced** to what the true denominator supports | **R7.5**, LIM3, §4.3 |
| **DG5** | **Cost model revised upward** and the effect no longer survives friction | → **E4 lost → C ≤ C1** | F4, D4 |
| **DG6** | **A confounding entry is confirmed** — a rival mechanism explains the same observations | → **C reduced**; severity was lower than believed | **R3**, [[MARKET_INEFFICIENCY_TAXONOMY]] §4 |
| **DG7** | **Capacity exceeded** — the institution's own deployment altered the mechanism | → **C ≤ C1**, F8 | **A4** ("fails at scale") |
| **DG8** | **An assumption fails** — A1–A8 breached | → every claim depending on it re-derived at the tier the surviving assumptions support | §9, §0.4 (*a rule whose justifying proposition is refuted is void, not grandfathered*) |
| **DG9** | **Custody breach discovered** — OOS data was touched before the registered test | → **E3+ lost → E2 → C ≤ C1** | **R6**, §2.4 |

### 6.2 The three that are not failures

**DG2 and DG3 are not research errors.** Per §6.5 and F9: *"a decayed mechanism was true and is now false — an expected consequence of P1 and D3, not an error."* The institution must file them without blame, because **filing them as failures would corrupt the F1–F9 distribution**, which §5.3 identifies as the highest-value diagnostic the Failure Library enables. An institution that punishes DG2 will stop recording it.

**DG7 is a success that consumed itself.** The mechanism was real; deploying it removed it. Per **A4** this is *expected* at scale, and per [[MARKET_INEFFICIENCY_TAXONOMY]] I12, **the institution's own growth is a decay mechanism for its own edge**. Recording DG7 as a research failure would teach exactly the wrong lesson — that the researcher was wrong, when the researcher was right and then acted.

### 6.3 The asymmetry, stated

| | Promotion | Degradation |
|---|---|---|
| **Requires** | A positive act with a receipt | Nothing — the world may act |
| **Speed** | Slow, gated, adversarial | **Immediate on trigger** |
| **Burden** | On the proponent, permanently (R4) | On no one |
| **Default** | Nothing promotes by silence (EV-8) | A trigger degrades without a decision |
| **Reversal** | — | Requires **re-promotion from the reduced level**, with a **new registration counted afresh in the family** |

> **Rule EV-10 (justified by R15, R4, §5.5):** **A degraded claim does not recover by re-argument.** It recovers only by re-earning its level through §5's events. Re-litigating a degradation is R15's *rescue*: editing the claim until the evidence stops disagreeing. Per §5.5 the institution is deliberately configured to be **slow to believe and fast to disbelieve** — the correct configuration where being wrong costs capital and being late costs only opportunity.

### 6.4 Monitoring obligations

Per **LIM7**, *decay is detectable only in arrears* — the institution learns a mechanism is gone after it has been gone. This is irreducible and it has a consequence that must be stated rather than engineered around:

> **Rule EV-11 (justified by LIM7, P7):** Every C≥C3 claim carries a **live decay monitor** and a **declared decay hypothesis** stating what kind of decay its barrier admits ([[MARKET_INEFFICIENCY_TAXONOMY]] §1). The monitor's design follows the barrier class: an **M6 structural barrier decays as a step function on rule change**, so its monitor watches a **rulebook**, not a return series. Applying return-based decay detection to an M6 mechanism is a category error that will detect nothing until long after the rule changed — the monitor would be watching the one variable the mechanism is not a function of.

> **Rule EV-12 (justified by LIM7, R13):** Because detection lags, the institution **pre-commits to a retirement rule at promotion time** (C2→C3), stating what observation retires the claim. A retirement rule authored *after* degradation begins is R7.4 — threshold migration — and will be authored under exactly the pressure that makes it wrong.

---

## 7. Replication requirements

| Requirement | Level | Rationale |
|---|---|---|
| Every claim ≥E3 | **X2 — specified** | Below X2, no claim exists to test (P8) |
| Every claim ≥E6 | **X3 — independently reproduced** | The result must belong to the institution, not to its author (§8) |
| Every C≥C3 claim | **X3** | Capital requires author-independence |
| Every claim, at any time | **Void on X0** | R19 — no exception, no grace period (§8.5) |

**What must be reproduced is the *claim*, not the bytes** (§8.3): same sign, same rejection or non-rejection of the null, same order of effect magnitude. L2/L5 may pursue bit-identity as an *implementation strategy* for achieving conclusion-invariance, but per §8.3 it then **owns the feasibility argument**, and L1 does not require it.

> **Known inconsistency (recorded, not resolved).** [[01_SCIENTIFIC_FOUNDATION]] §15 records under **AQ-4** that parts of the L2 corpus assert bit-identity while L1 requires only conclusion-invariance. Per **ADR-L1-008**, L1 *records* such inconsistencies rather than resolving them. **This document inherits that inconsistency and does not resolve it either** — X3's definition follows L1 (conclusion-invariance). Any L2 document requiring bit-identity is stricter than this model and must supply its own feasibility argument.

---

## 8. Worked reading — Program P0's NR7 BULL finding

Applying all three axes to the corpus's only substantive research finding, to show the model discriminates where a single axis cannot:

| Axis | Assessment | Basis |
|---|---|---|
| **Class** | **K3/K4** — observational, with pre-registered elements | Program P0 |
| **E** | **E3-ish** — significant against zero, CI [+0.32, +2.06]; **sub-bar on effect size** | [[RESEARCH_OS_MASTER_ROADMAP]] §3 |
| **C** | **C1 — weak.** DSR collapses under the 42-cell family | **Rule EV-4**: the family is a C-axis fact the tier cannot see |
| **X** | **X2** — specified and re-runnable; **not independently reproduced** | `research.tracking` supplies provenance; no external party has re-derived it |
| **Verdict** | **No capital.** C3 requires E5+X3; the claim has neither. **Forward test (E7) is decisive** — exactly as P0 concluded independently. |

**Three things this reading demonstrates:**

1. **The three axes were necessary.** On the E axis alone the finding reads as a real effect that passed its test. Only the C axis records the family collapse; only the X axis records the missing independent reproduction. An institution with one axis would have called this a finding.
2. **The model reproduces a conclusion the institution already reached by other means** — that the forward test is decisive. That is a weak form of validation for the model, and it is worth stating that it is weak: agreeing with one prior conclusion is not evidence the framework is right, it is evidence it is not obviously wrong.
3. **The liquidity-conditional result (LOW_LIQ +2.29% vs HIGH_LIQ −0.47%)** falsified the design's "no axis needed" prediction. Under **DG6**, a confirmed conditioning variable that was not declared *ex ante* reduces confidence rather than raising it: the effect is real *and* the original claim's severity was lower than believed, because the test could not have detected the conditionality it turned out to depend on.

---

## 9. Traceability

| This document | Extends | Never restates |
|---|---|---|
| Classes K1–K7 | [[01_SCIENTIFIC_FOUNDATION]] §4.2 (E0–E7), R10 | **The E scale itself** |
| Unacceptable U1–U12 | R7 (prohibited inferences), R2, R13, R19 | R7's list |
| Confidence C0–C4 | §4.3 (process not number), R4, ADR-L1-002 | — (new axis) |
| Reproducibility X0–X4 | §8 (P8, R19), §8.3 (conclusion-invariance), ADR-L1-005 | The bit-identity argument |
| Promotion EV-8…EV-9 | R4, R5, R6, §4.2 (E7 timebox), LIM5, LIM6 | The tier definitions |
| **Degradation DG1–DG9** | P7, F9, R19, A4, LIM7 | — (**new — no corpus counterpart**) |
| §5.1 C ≤ f(E,X) | R10 (E4 floor) | R10 |

**Upstream:** [[MARKET_INEFFICIENCY_TAXONOMY]] (its *Required evidence* fields cite tiers this model grades) · [[ECONOMIC_MECHANISM_TAXONOMY]] (E1→E2 requires a sub-class).
**Downstream:** [[HYPOTHESIS_LIFECYCLE]] (state transitions carry E/C/X guards) · [[RESEARCH_OBJECT_SCHEMA]] (every object's evidence requirements resolve here) · [[LITERATURE_RESEARCH_STANDARD]] (K2's E1 ceiling is its binding constraint) · [[RESEARCH_PROGRAM_STANDARD]] (a Program is the family denominator C depends on) · [[RESEARCH_VALIDATION_FRAMEWORK]] / `research/gatekeeper` (computes E-axis inputs).
