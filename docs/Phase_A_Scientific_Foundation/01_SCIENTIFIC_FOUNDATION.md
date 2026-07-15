# Scientific Foundation

**Layer:** L1 — Scientific Foundation · **Status:** Canonical (candidate — pending adversarial sign-off) · **Version:** 1.0
**Date:** 2026-07-15 · **Owner:** Chief Research Scientist / Scientific Methodology Architect
**Standard:** ISO/IEC/IEEE 42010:2011 — Architecture Description (see §14 Conformance)
**Authority:** This document is the **scientific foundation of the Institutional Research OS**. Where another document specifies *how* research is conducted, this document specifies *why that method is valid science*. On any question of scientific method — what counts as knowledge, what counts as evidence, what counts as refutation — this document governs, subject to the precedence rules of [[RESEARCH_OS_RECONCILIATION]] §5.

**Scope discipline:** This document contains no implementation, no code, no schemas, no thresholds, and no Phase-B content. It is the substrate the architecture rests on, not the architecture.

**Prior citation:** This artifact is the previously-unwritten seventh canonical document, cited as "Market Inefficiency Foundation" in [[REVISION_IMPACT_ASSESSMENT]] §3/§4, [[RESEARCH_OS_MASTER_ROADMAP]] §2 (L1), and [[TAXONOMY_AND_NAMING_STANDARD]] §3 (L1). Its absence was logged as **AQ-8 (Scientific Foundation concern unframed — High)** and **RQ-5 (phantom file reference)** in the Phase-A falsification review. This document closes AQ-8.

---

## 0. Architecture Description Preface (ISO 42010 §5.2–§5.5)

### 0.1 System identified (§5.2)

The **system-of-interest** is the *Institutional Research OS* — the socio-technical system by which this institution converts market observations into justified, reproducible, decision-grade knowledge about market inefficiency, and by which it retires that knowledge when it ceases to be true.

The system-of-interest is **not** the trading system. Production trading is a *consumer* of this system's outputs and lies outside this architecture description. The relationship is one-directional: research produces knowledge; capital allocation consumes it. The reverse dependency — allowing capital outcomes to determine what counts as knowledge — is prohibited by §2.5.

### 0.2 Stakeholders identified (§5.2)

| Stakeholder | Interest in this document |
|---|---|
| Chief Research Officer (CRO) | Owns the charter; needs the criteria by which knowledge claims are adjudicated |
| Research Architect | Must ensure the L2 architecture *realizes* this epistemology rather than contradicting it |
| Quant Researcher | Must know, ex ante, what would make a hypothesis wrong and what evidence would count |
| Validation Reviewer | Requires an explicit standard of refutation to conduct adversarial review against |
| Data Engineer | Must know why provenance and immutability are scientific requirements, not IT hygiene |
| Capital allocator (external consumer) | Requires an explicit statement of what the institution's knowledge claims do and do not assert |
| Future maintainer | Must be able to reconstruct *why* the method is what it is, without the authors present |

### 0.3 Concerns framed by this document (§5.3)

ISO 42010 §5.3 requires the AD to frame purpose, suitability, feasibility of construction, risks, and evolvability. This document frames the following concerns; each is framed by at least one section, satisfying §5.5.

| # | Concern | Framed in |
|---|---|---|
| C1 | What kind of enterprise is this, and what is it for? (*purpose*) | §1 Scientific worldview |
| C2 | How does this institution know anything? (*suitability of method*) | §2 Epistemology |
| C3 | What kinds of things exist in the world we study? | §3 Ontology |
| C4 | What counts as evidence, and how much is enough? | §4 Philosophy of evidence |
| C5 | How is a claim killed? | §5 Falsification methodology |
| C6 | Why should any inefficiency exist or persist? | §6 Market inefficiency philosophy |
| C7 | Why must economics precede statistics? | §7 Mechanism primacy |
| C8 | Why is reproducibility non-negotiable? (*feasibility, evolvability*) | §8 Reproducibility mandate |
| C9 | What are we taking on faith? (*risks*) | §9 Scientific assumptions |
| C10 | What can this institution not know? (*risks, suitability*) | §10 Scientific limitations |
| C11 | How does the foundation bind the rest of the architecture? | §11 Relationship to Phase-A corpus |
| C12 | Do we all mean the same thing by our words? | §12 Glossary |

### 0.4 Viewpoint specification (§5.4)

This document constitutes the **Scientific Viewpoint** of the Research OS architecture description.

- **Concerns framed:** C1–C12 above.
- **Stakeholders addressed:** all of §0.2.
- **Model kinds used:** (i) *declarative propositions* — numbered, individually contestable assertions (§1, §9); (ii) *normative rules* — statements of the form "X is required / prohibited," each traceable to a proposition (§2, §5, §7, §8); (iii) *domain taxonomy* — a partition of the scientific subject matter into non-overlapping domains with stated boundaries (§6); (iv) *controlled vocabulary* — a term-to-definition mapping (§12); (v) *decision records* — rationale with alternatives considered (§13).
- **Conventions:** Propositions are numbered `P<n>` and are falsifiable *as stated*: each carries a defeater — the observation or argument that would refute it. Rules are numbered `R<n>` and cite the proposition(s) that justify them; a rule whose justifying proposition is refuted is void, not grandfathered. Assumptions are numbered `A<n>` and carry an explicit failure mode. Limitations are numbered `LIM<n>` and carry a statement of what the institution must therefore refrain from claiming. Terms defined in §12 are used in exactly the §12 sense throughout the corpus.
- **Correspondence rule:** where this viewpoint and any L2 viewpoint address the same concern, §11 records the correspondence; unresolved disagreements are recorded in §15 per §5.6.

### 0.5 What this document deliberately does not do

It does not define objects, schemas, fields, stages, gates, thresholds, statistical procedures, storage, or code. Those are L2+ concerns owned by [[RESEARCH_OBJECT_MODEL]], [[RESEARCH_OPERATING_MODEL]], [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]], [[RESEARCH_VALIDATION_FRAMEWORK]], [[FEATURE_COMPUTATION_GRAPH]], and [[FAILURE_LIBRARY_SCHEMA]]. This document supplies the reasons those documents must be able to cite.

---

## 1. Scientific Worldview

### 1.1 The founding proposition

> **P1 — Markets are physical, historical, institutional systems, not mathematical objects.**
> A market is a mechanism: a set of rules, participants with heterogeneous constraints, and a matching process operating in time. Prices are the residue of that mechanism operating, not draws from a distribution that exists independently of it.
> *Defeater:* demonstrate that price behavior is fully explained by a stationary stochastic process whose parameters are invariant to changes in market rules, participant composition, and constraint structure.

P1 is the load-bearing commitment of this institution. Every subsequent rule is downstream of it. If P1 is false, the correct research method is statistical estimation of a fixed data-generating process, and most of this document is unnecessary overhead. We assert P1 because market rules demonstrably change price behavior — tick-size regimes, auto-rejection bands, auction designs, and settlement rules alter observed dynamics in ways no parameter of a stationary process anticipates.

### 1.2 The consequence: inefficiency is a mechanical claim

> **P2 — An inefficiency is a claim about a mechanism, not a claim about a dataset.**
> To assert an inefficiency is to assert: *there exists a structural or behavioral feature of this market, arising from identifiable participants under identifiable constraints, which causes prices to deviate systematically from the value they would take absent that feature.* A pattern in data is evidence *for or against* such a claim. It is never the claim itself.
> *Defeater:* exhibit an inefficiency that is real, exploitable, persistent, and for which no mechanistic account exists even in principle.

P2 is why this institution refuses to be a pattern-mining shop, and it is the proposition that [[RESEARCH_VALIDATION_FRAMEWORK]] §3 operationalizes in the best sentence of the corpus: *"A mechanism is invalid, regardless of statistical significance, if it cannot be explained by fundamental market micro-economics."* That sentence is not a stylistic preference. It is P2 stated as a gate.

### 1.3 The stance: adversarial, not confirmatory

> **P3 — The institution's scientific output is a set of surviving conjectures, not a set of discoveries.**
> Nothing here is ever proven. Knowledge is what has been attacked competently and has not yet broken. Its status is *provisional and revocable by construction* — which is why the Knowledge Object lifecycle terminates in DECAYED/RETIRED rather than in permanence.
> *Defeater:* establish that a finite sample can confer certainty on a universal claim about a non-stationary system.

### 1.4 The economics of the enterprise

> **P4 — The scarce resource is not data or compute; it is the credibility of a claim.**
> Data is abundant, compute is cheap, and hypotheses are free. What is scarce, expensive, and destroyable is the institution's ability to believe its own conclusions. Every methodological rule in this corpus exists to protect that one asset. A rule that does not protect it is bureaucracy and should be removed.

P4 is the test to apply when any future contributor proposes adding process. If the proposed rule does not measurably reduce the probability that the institution believes something false, it fails P4.

### 1.5 Worldview in one paragraph

We study a real, rule-bound, adversarial, time-varying system. We believe inefficiencies arise from identifiable frictions among constrained participants, and persist only where something prevents their arbitrage. We hold all our beliefs conjecturally, we attack them ourselves before the market does, we preserve our failures as carefully as our successes, and we treat the reproducibility of a result as part of the result. We are not trying to be right. We are trying to be *correctable*.

---

## 2. Epistemology

### 2.1 Position: fallibilist, mechanism-first, evidence-bounded

This institution adopts a **critical-rationalist epistemology** (Popper), corrected on two points where naive falsificationism is known to be inadequate for empirical finance, and augmented by a **severity criterion** (Mayo) that supplies what naive falsificationism lacks.

**Correction 1 — the Duhem–Quine problem.** No hypothesis is tested in isolation. A rejected prediction may indict the mechanism, the feature construction, the data, the cost model, the regime assumption, or the test itself. A bare "the test failed" is therefore not knowledge.
> **R1 (justified by P2, P3):** Every falsification must name *what specifically was falsified* and defend that attribution against the alternative auxiliary explanations. This is why the Failure Library records `falsification_reason` and `invalid_assumptions` as first-class structured fields rather than free prose — the schema exists to force the attribution that Duhem–Quine says cannot be assumed.

**Correction 2 — probabilistic refutation.** Financial hypotheses predict distributions, not events. A single contrary observation refutes nothing; a sufficiently weak test corroborates nothing.
> **R2 (justified by P3):** A test is scientifically admissible only if it was *capable of failing*. Corroboration from a test that could not have refuted the hypothesis carries zero evidential weight, regardless of the p-value it produced. This is the epistemological ground for demanding power/MDE analysis — an underpowered test is not weak evidence, it is *no evidence*, and reporting it as weak evidence is an error of kind, not of degree.

**The severity criterion.** Evidence supports a hypothesis to the degree the test would probably have *detected* the hypothesis's falsity had it been false. Severity, not significance, is the currency of this institution.
> **R3 (justified by P3, P4):** Claims of support must be accompanied by an argument for the severity of the test that produced them: what would have had to be true for this test to have caught the error, and was the test in fact capable of that?

### 2.2 Justification is asymmetric

Confirmation and refutation are not symmetric operations, and the institution's rules deliberately reflect the asymmetry:

| | Confirmation | Refutation |
|---|---|---|
| Logical force | None (affirming the consequent) | Deductive, modulo auxiliaries |
| Institutional cost | High — must be earned repeatedly | Low — accepted on first competent demonstration |
| Standard of proof | Severe test, ex-ante criteria, out-of-sample, net of cost, mechanism-explained | A single sound argument or reproducible contrary result |
| Reversibility | Always revocable | Requires a *new* hypothesis, not a rescue of the old |

> **R4 (justified by P3):** The burden of proof rests permanently and asymmetrically on the *proponent* of a knowledge claim. It never transfers to the skeptic. "You cannot prove it doesn't work" is not a defense; it is a concession.

### 2.3 Prediction precedes observation

> **R5 (justified by P3, P4):** A hypothesis's success criteria must be fixed *before* the evidence that will judge it is seen. Criteria chosen after the data are seen are not criteria; they are descriptions.

This is why pre-registration is architectural rather than procedural. A criterion selected post hoc is unfalsifiable in practice, because the analyst's degrees of freedom silently absorb any result. Pre-registration converts research from *fitting an explanation to an outcome* into *risking a claim against an outcome*, which is the only operation that generates evidence under §2.1.

### 2.4 Knowledge has custody states

The institution recognizes exactly three epistemic states of a claim, mapped to three custody regimes over evidence:

| Epistemic state | What is licensed | Data custody |
|---|---|---|
| **Discovery** | Conjecture, exploration, unlimited searching, no claims | In-sample only. Nothing found here is knowledge; it is *hypothesis material*. |
| **Confirmation** | One severe, pre-registered test of one registered conjecture | Out-of-sample, opened once, against ex-ante criteria |
| **Accepted Knowledge** | Provisional institutional belief; consumable by capital | Sealed. Further contact requires re-registration. |

> **R6 (justified by R5, P4):** Custody must be *enforced*, not requested. A prohibition that relies on a researcher's discipline is a statement of intent, not a control. The epistemological content of custody is that out-of-sample data is a **non-renewable resource**: it can be spent exactly once per hypothesis, and every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged. This invisibility is precisely why it requires a mechanism.

This is the scientific ground for the review's W9 (OOS custody is policy, not mechanism). L1's position: the policy formulation is *epistemologically void*, because unenforced custody produces a system whose evidential state cannot be known even by its own operators.

### 2.5 Prohibited inferences

> **R7:** The following moves produce no knowledge and are prohibited in any institutional claim:
> 1. **Profit as proof.** Realized returns are not evidence of a mechanism. Both fortune and error produce them.
> 2. **Survivorship reasoning.** "This is what remains after we discarded what didn't work" describes a selection process, not a discovery.
> 3. **Retro-fitted mechanism.** Finding a pattern and *then* authoring the economic story that explains it. The story is unconstrained; it will always be available. See §7.3.
> 4. **Threshold migration.** Adjusting a criterion after seeing a near-miss. The criterion was the test; moving it deletes the test.
> 5. **Family reduction.** Narrowing the multiple-testing family after the fact so a survivor clears. The denominator is part of the claim.
> 6. **Appeal to complexity.** "The model is too complex to explain" is a report of the institution's ignorance, not a property of the market.

---

## 3. Ontology

This section states **what kinds of things this institution believes exist in the market** — the scientific ontology. It is distinct from and prior to [[RESEARCH_OBJECT_MODEL]], which is the ontology of *research artifacts* (hypotheses, experiments, reports). The distinction is exact and load-bearing:

> **This document's ontology answers "what is out there that we study?" The Research Object Model answers "what do we produce while studying it?"** A Mechanism (here) is a feature of the world. An `Economic Mechanism Object` (there) is our institutional record of a conjecture about it. Confusing the two is the reification error: mistaking the map's schema for the territory's furniture.

### 3.1 Entities that exist

| Entity | Definition | Mode of existence |
|---|---|---|
| **Market mechanism** | The rule system: matching, tick and lot structure, price limits, auction design, settlement, access rules | *Real and directly knowable* — it is published |
| **Participant class** | A set of agents sharing constraints and objectives (market maker, index fund, retail, foreign institution, state entity) | *Real, partially observable* — inferred from behavior and disclosure |
| **Constraint** | A binding limit on a participant class: inventory, capital, mandate, risk limit, horizon, information access | *Real, mostly unobservable* — the primary source of inefficiency |
| **Order flow** | The realized stream of intentions expressed to the mechanism | *Real, observable at institution-specific fidelity* (see §10.1) |
| **Price** | The output of the mechanism given flow; a **consequence**, never a cause | *Real, observable* |
| **Economic mechanism (inefficiency mechanism)** | A causal structure by which a constraint on a participant class produces a systematic price deviation | *Real if the claim is true; a conjecture until then* |
| **Regime** | A period during which the joint distribution generated by the system is approximately stable | *Real but not directly observable* — always a model, never a measurement (see §9 A5) |
| **Friction** | The unavoidable cost of interacting with the mechanism: spread, impact, fees, latency, rejection | *Real, partially measurable, always non-zero* |

### 3.2 Entities that do not exist (anti-realist commitments)

Naming what we refuse to reify is as important as naming what we admit, because each of these has, historically, been a route by which unfalsifiable claims entered a research institution:

- **"The signal"** — no autonomous entity emits predictive information. There are mechanisms and there are measurements of them. A "signal" that cannot be decomposed into *(constraint → participant behavior → price consequence)* is a curve fit with a name.
- **"True price"** — value is not a hidden observable that price approaches. Deviation is always defined *relative to a stated counterfactual* ("the price absent this friction"), and that counterfactual must be stated or the deviation claim is empty.
- **"The market's opinion"** — the market is a mechanism, not an agent. It has no beliefs, intentions, or memory. Attributing agency to it is a category error that licenses unfalsifiable narrative.
- **"Alpha" as substance** — alpha is not a fluid that exists in a quantity and gets extracted. It is a *summary statistic of a comparison to a benchmark under a cost model*. Change the benchmark or the cost model and the quantity changes, which is not the behavior of a substance.
- **"Stationarity"** — no stable data-generating process exists to be estimated (P1). Stationarity is at best a *local approximation whose scope must be declared*, never a background fact.

### 3.3 The causal order

The institution commits to a strict causal direction, and this ordering constrains what a valid mechanism claim may look like:

```
Market design + participant constraints
        → participant behavior
        → order flow
        → price formation
        → observable price/volume series
        → derived measurements (features)
```

> **R8 (justified by P1, P2):** Explanation flows downward; evidence flows upward. A mechanism claim must be stated at the level of *design and constraints* and must be tested at the level of *measurements*. A claim stated only at the level of measurements ("feature X predicts return Y") is not a mechanism claim and cannot become one by assertion.

### 3.4 Mechanism taxonomy (the classes of inefficiency this institution admits)

A valid mechanism must be classifiable into exactly one primary class below. The taxonomy is a *closed set at the class level* and open at the instance level: a proposed mechanism that fits no class is either a novel class — requiring an amendment to this document and CRO approval — or is not a mechanism.

| Class | The constraint that generates it | Why prices deviate |
|---|---|---|
| **M1 · Inventory / risk-bearing** | Liquidity suppliers hold undesired inventory under risk limits | Compensation demanded for absorbing imbalance |
| **M2 · Information asymmetry** | Some participants know more; others must quote anyway | Adverse-selection premium embedded in price |
| **M3 · Liquidity / price-impact compensation** | Trading is costly and costs scale with size | Illiquid assets discounted for expected impact |
| **M4 · Mandated / price-insensitive flow** | Participants who must trade regardless of price (index, redemption, margin, regulation) | Demand curve is not flat; forced flow moves price |
| **M5 · Behavioral / attention** | Bounded rationality, salience, anchoring, disposition | Systematic mispricing where the bias is unarbitraged |
| **M6 · Market-design artifact** | Venue rules create discontinuities (auto-rejection bands, auctions, tick regimes, halts) | Price paths constrained by rules, not by value |

> **R9 (justified by P2, R8):** Every registered hypothesis must name its class from M1–M6 and identify the *specific constraint* and *specific participant class* the class implicates. "M5 · Behavioral" without a named bias, a named participant class, and a reason that bias is unarbitraged (§6.3) is not a classification.

### 3.5 Scientific domains (L1 subject matter)

L1 owns six domains, partitioned to be **mutually non-overlapping** with explicit boundaries. This set implements review recommendation R4 (merge D1+D2; add Market Design and Limits-to-Arbitrage; promote Cost/Impact to a domain) and discharges the Phase-A exit item *"L1 domain de-overlap"* ([[RESEARCH_OS_MASTER_ROADMAP]] §7). Ordering is deliberate: substrate domains precede phenomenon domains, because a phenomenon is only interpretable against the substrate that produces it.

| # | Domain | Owns (its exclusive subject) | Explicitly does **not** own |
|---|---|---|---|
| **D1** | **Market Design (venue-specific: IDX)** | The concrete rule substrate: tick-size regime, lot size, ARA/ARB auto-rejection bands, auction mechanics, session structure, halts/suspensions, short-sale constraints, settlement, foreign-ownership rules | Participant behavior *within* the rules (→ D2); costs arising from the rules (→ D4) |
| **D2** | **Microstructure & Price Formation** | How flow becomes price given D1: order flow, imbalance, adverse selection, inventory dynamics, liquidity provision and withdrawal, price discovery | The rules themselves (→ D1); why deviations survive (→ D3) |
| **D3** | **Limits to Arbitrage & Persistence** | *Why an inefficiency is not already gone*: capital constraints, horizon risk, noise-trader risk, implementation barriers, capacity, the decay process | The origin of the deviation (→ D2, D5); the measurement of cost (→ D4) |
| **D4** | **Transaction Cost, Impact & Capacity** | The friction that stands between a deviation and its capture: spread, impact functions, fees, slippage, capacity limits, cost-model construction | Whether an effect exists gross of costs (→ D2, D5) |
| **D5** | **Behavioral & Institutional Flow** | Participant-side generators of deviation: bounded rationality, attention, mandated/price-insensitive flow, calendar and index effects | Whether the effect survives friction (→ D4) or arbitrage (→ D3) |
| **D6** | **Inference under Non-Stationarity** | The epistemics of measuring a moving system: regime, structural break, multiplicity, power/MDE, backtest overfitting, decay estimation | Any specific market claim — D6 is method-about-claims, not a claim |

**Overlap adjudication rule.** If two domains appear to claim the same question, the boundary column above decides; the question belongs to the domain whose *exclusive subject* contains it. If the boundary is genuinely silent, the question belongs to the domain **earliest** in D1→D6 order (substrate wins over phenomenon), and this document is amended to record the boundary.

**Domain-to-mechanism mapping.** D1 constrains M6; D2 generates M1/M2; D3 gates all of M1–M6 (it decides *persistence*, not existence); D4 gates all of M1–M6 (it decides *capture*); D5 generates M4/M5; D6 governs the testing of all of them.

---

## 4. Philosophy of Evidence

### 4.1 What evidence is

> **P5 — Evidence is the outcome of a test that could have gone the other way.**
> An observation compatible with a hypothesis is not evidence for it unless the observation was *unlikely under the hypothesis's falsity*. Data that cannot discriminate is not weak evidence — it is not evidence.

### 4.2 The hierarchy of evidential weight

Not all evidence is equal. The institution ranks it explicitly, so that reviewers can compare unlike claims. Weight ascends:

| Tier | Kind of evidence | Weight | Why |
|---|---|---|---|
| **E0** | In-sample fit; a pattern found by searching | **Zero** | Guaranteed obtainable by search; discriminates nothing (§2.4) |
| **E1** | Statistical significance without a mechanism | **Zero for acceptance** | Violates P2; admissible only as hypothesis material |
| **E2** | Mechanism-explained effect, in-sample | Low | Explanation may be retro-fitted (§7.3) |
| **E3** | E2 + severe, pre-registered out-of-sample test | Substantial | The claim was risked and survived (§2.3) |
| **E4** | E3 + survives realistic friction (D4) | High | The effect exists in the world we can act in, not only in the world we can measure |
| **E5** | E4 + stable across regimes, or with declared regime scope | High | Discriminates mechanism from regime artifact |
| **E6** | E5 + independently reproduced from the specification alone | **Decisive available** | The result belongs to the institution, not to its author (§8) |
| **E7** | E6 + forward-tested on data that did not exist at registration | **Strongest obtainable** | The only evidence immune to every retrospective bias |

> **R10 (justified by P5, R2):** No Accepted Knowledge claim may rest on evidence below **E4**. Claims resting on E0/E1 are not weak claims; they are *category errors* and must be rejected rather than discounted.

**On E7 and its cost.** Forward evidence is the only tier that no retrospective error can contaminate, but it accrues in wall-clock time and cannot be accelerated. This creates a real, permanent tension between rigor and timeliness. The institution resolves it in one direction: **the timebox for forward evidence is fixed ex ante and never extended to rescue a claim** — extending it is R7.4 (threshold migration) wearing a calendar. A claim that fails its forward test fails; a claim that runs out of time is unproven, not proven.

### 4.3 Evidence is a property of the *process*, not of the *number*

> **R11 (justified by P4, R5):** The same numerical result carries different evidential weight depending on how it was produced. A t-statistic of 3.0 from a single pre-registered test and a t-statistic of 3.0 selected from two hundred searched variants are not the same evidence, and no property of the number itself distinguishes them.

This is the deepest reason the institution records lineage, multiplicity, and provenance: **the evidential weight of a result is not recoverable from the result.** It is recoverable only from the process that produced it. An institution that discards process history has not merely lost an audit trail — it has destroyed its ability to know what its own numbers mean. This is the scientific justification for the entire lineage apparatus of L2, and it is why the multiple-testing family denominator is part of the *claim* and not part of the *analysis*.

### 4.4 Negative evidence is evidence

> **R12 (justified by P4, P3):** A competent refutation is a first-class institutional product, of equal standing to a validated mechanism.

Three reasons, all load-bearing: (i) it maps the boundary of efficiency, which is the substantive scientific object of study; (ii) it prevents the institution from re-purchasing the same failure; (iii) suppressing it produces institutional publication bias, which corrupts every future multiplicity calculation by hiding the denominator. A Failure Library that is optional is a Failure Library that is empty, and an empty one silently biases every DSR the institution ever computes.

### 4.5 The cost of belief

> **R13 (justified by P4):** The evidential bar scales with the consequence of being wrong and with the number of prior attempts. It never scales with how much the institution wants the claim to be true, how much effort it cost, or how elegant it is. Sunk research cost is not evidence.

---

## 5. Falsification Methodology

### 5.1 The requirement

> **R14 (justified by P3, R5):** Every hypothesis must state, before testing, the observation that would refute it. A hypothesis with no stated refutation condition is not admitted — not deferred, not weakened. **Not admitted.**

The test of admissibility is the **counterfactual interview**, and it must be answerable in one sentence:

> *"What would we see, in the data we are about to touch, if this mechanism were not real?"*

If the answer is "nothing in particular," or "it would be weaker," or requires more than one sentence, the hypothesis is not yet a hypothesis. It is an intention.

### 5.2 Anatomy of a falsifiable claim

A hypothesis is falsifiable *in this institution's sense* only if all six are present:

1. **A mechanism** — a named class (M1–M6) with a named constraint and participant class (R9).
2. **A directional prediction** — sign-specified. "Related to" is not a prediction.
3. **A null** — the state of the world if the mechanism is absent, stated as a measurable proposition, not as "no effect."
4. **A scope** — universe, horizon, regime conditions, period. A claim without scope is either trivially true somewhere or unfalsifiable everywhere.
5. **An ex-ante criterion** — including effect size, not significance alone. A statistically detectable effect smaller than its own cost is a *confirmed irrelevance* (see §5.5).
6. **A multiplicity family** — the denominator against which this test is one of N. Declared before, and never narrowed after (R7.5).

Any of the six missing ⇒ the claim is not falsifiable ⇒ Gate 1 refuses it. This list is the scientific content that [[RESEARCH_OPERATING_MODEL]] G1 enforces and that the Hypothesis Object's fields carry.

### 5.3 Modes of falsification (the institution's kill list)

A claim may die in any of these ways. All are equally final; none is a lesser death. Enumerating them matters because the Failure Library's `falsification_reason` must attribute the death to exactly one, and R1 requires that attribution to be *defended* against the others:

| Mode | The claim dies because… |
|---|---|
| **F1 · Mechanistic incoherence** | The mechanism contradicts market micro-economics or the venue's design (D1). Dies at S2 — *before any data* |
| **F2 · Prediction failure** | The pre-registered out-of-sample criterion was not met |
| **F3 · Multiplicity collapse** | The effect does not survive its own family denominator; it is a search artifact |
| **F4 · Cost destruction** | The effect is real and smaller than the friction required to capture it (D4) |
| **F5 · Regime artifact** | The effect is a property of one regime, undeclared at registration |
| **F6 · Provenance failure** | The result cannot be reproduced from its specification. **The claim is void, not pending** (§8.4) |
| **F7 · Look-ahead contamination** | Information unavailable at decision time entered the test |
| **F8 · Capacity extinction** | The effect exists but vanishes at any size the institution could deploy |
| **F9 · Decay** | The effect was real and is now gone; the mechanism was arbitraged or its constraint was removed |

**F1 is privileged.** It is the *cheapest* falsification available, because it consumes no data, no out-of-sample custody, and no multiplicity budget. An institution that routinely kills claims at F1 is operating efficiently; one whose failures cluster at F2–F4 is spending its scarcest resources to learn things it could have reasoned out. **The distribution of failures across F1–F9 is therefore a diagnostic of the institution itself**, and is the highest-value analysis the Failure Library enables.

**F9 is not a failure of the research.** A decayed mechanism was true and is now false — an expected consequence of P1 and D3, not an error. Filing F9 alongside F1 without distinction would corrupt the diagnostic above.

### 5.4 What may never be done to a dying claim

> **R15 (justified by R7, R5):** When a hypothesis fails, the following are prohibited: re-running with adjusted parameters and reporting the survivor; narrowing the universe or period until it passes; adding a filter discovered from the failure; re-labeling the failure as "needs more data"; splitting one dead claim into variants until one survives.
>
> **The only legitimate response to a falsified hypothesis is: record the failure (R12), and — if the failure taught a new mechanism — register a *new* hypothesis, with a new pre-registration, counted in the family.**

The distinction is exact and is the single most abused boundary in quantitative research: *learning from failure* is registering a new risked claim. *Rescuing a failure* is editing the old claim until the evidence stops disagreeing. The first generates knowledge; the second destroys the institution's ability to know anything, and — because a rescued claim looks identical to a survived one — it does so **invisibly**.

### 5.5 Falsification is not symmetric with acceptance

A claim is *refuted* by one competent demonstration. A claim is *accepted* only by surviving all applicable modes F1–F9 at evidence tier ≥E4. This asymmetry is intentional and is the structural expression of R4: it makes the institution slow to believe and fast to disbelieve — the correct configuration for an agent operating in an adversarial system where being wrong costs capital and being late costs only opportunity.

---

## 6. Market Inefficiency Philosophy

### 6.1 Position on efficiency

The institution holds a **conditional, mechanistic view of market efficiency**:

> **P6 — Markets are efficient with respect to a piece of information to the degree that some participant is both able and incentivized to act on it.**
> Efficiency is not a property of "the market." It is a property of a *(market, information, participant, constraint, cost)* tuple. Asking "is the market efficient?" is malformed. The well-formed question is: *"which participant would remove this deviation, what prevents them, and what does it cost them to try?"*
> *Defeater:* demonstrate deviations that persist where an unconstrained participant faces zero cost to remove them.

P6 dissolves the sterile efficient/inefficient dichotomy into a research program. The Efficient Market Hypothesis is not a rival to be refuted; it is the **null against which mechanism claims are stated** (§5.2.3), and it is a *good* null — it is right far more often than it is wrong, which is precisely what makes it useful.

### 6.2 The two-condition test for any inefficiency claim

> **R16 (justified by P6, P2):** An inefficiency claim must answer **both**, independently:
> 1. **Origination** — *why does the deviation arise?* Which constraint, on which participant class, produces it? (Domains D1/D2/D5; classes M1–M6.)
> 2. **Persistence** — *why has it not been arbitraged away?* What prevents the participant who would remove it from doing so? (Domain D3.)
>
> Answering only (1) is the classic failure mode. It produces claims that are economically plausible and empirically dead, because a deviation that anyone could costlessly remove *has already been removed* — before the researcher observed it, by construction.

### 6.3 The persistence question is primary

Most rejected hypotheses in a competent institution die on (2), not (1). Origination stories are cheap: any pattern can be given one. **Persistence stories are expensive, and their scarcity is what makes them informative.** The admissible answers are enumerable:

| Persistence reason | The barrier |
|---|---|
| **Cost barrier** | The deviation is smaller than the friction to capture it (D4) — real but not capturable. *Note: this is F4, an inefficiency that is simultaneously real and worthless* |
| **Capacity barrier** | The deviation is capturable but too small to matter to those who could remove it |
| **Constraint barrier** | Those who could arbitrage it are mandated not to (D5) |
| **Horizon barrier** | Convergence is slower than the arbitrageur's capital can wait (D3) |
| **Risk barrier** | The arbitrage is not riskless; noise-trader risk can force liquidation before convergence |
| **Information barrier** | The deviation is not visible without costly processing |
| **Structural barrier** | The venue's design prevents removal (D1/M6) — e.g., a price limit that mechanically blocks convergence |

> **R17 (justified by R16, P4):** If a hypothesis's persistence reason is not on this list, the burden is on the proponent to establish a new barrier class, and the default presumption is that **the effect does not exist** — because absent a barrier, someone with more capital and better data has already taken it.

### 6.4 Where inefficiency is *a priori* most likely

This is not a search heuristic — it is a corollary of §6.2, and it is what makes an institution of this size viable at all. Deviation is most probable where origination and persistence conditions coincide:

- Where **mandated flow** meets **thin liquidity** (M4 ∧ M3).
- Where the **venue's design** creates mechanical discontinuities (M6/D1) — auto-rejection bands, auction crosses, halts.
- Where **arbitrage capital is structurally absent** — small caps, constrained access, local-market frictions.
- Where the **information barrier is real** — data that exists but is costly to process.
- Where **capacity is too small** for larger institutions to bother (a barrier that *favors* a small institution — one of the few structural advantages available here).

Conversely, deviation is *a priori least* likely where capital is abundant, data is standardized, and the constraint is absent — which is exactly where the most-studied effects live, and why replicating famous anomalies is a poor use of this institution's scarce resource (P4).

### 6.5 Inefficiency is mortal

> **P7 — Every inefficiency has a finite half-life.**
> Some mechanisms decay by arbitrage as capital discovers them; some vanish when their generating constraint is removed by rule change; some persist for decades because the barrier is structural. **Which of these applies is itself a research question (D3), not an assumption** — a mechanism whose barrier is structural (M6/D1) may outlive one whose barrier is merely informational by an order of magnitude.
> *Defeater:* a mechanism demonstrably invariant across a change to its own generating constraint — which would refute the claim that the constraint generates it.

P7 is why Accepted Knowledge is monitored rather than archived, and it is the scientific justification for the decay lifecycle at L8. It also implies something the institution must accept rather than resent: **research is not a capital-accumulating activity.** Validated knowledge is depreciating inventory, and the institution's steady-state obligation is replacement, not accumulation.

---

## 7. Why Economic Mechanisms Precede Statistical Significance

This section supplies the argument that [[RESEARCH_VALIDATION_FRAMEWORK]] §3 asserts. That document states the rule; this one defends it — as ISO 42010 §5.7 requires and as finding **AQ-7** records to be absent corpus-wide.

### 7.1 The argument from the search space

The space of testable patterns is effectively unbounded: features × transformations × universes × horizons × parameterizations × periods. Under any conventional significance threshold, an unbounded search yields an unbounded supply of "significant" results **whether or not any effect exists**. Statistical significance is therefore *not a filter* over an unbounded search space — it is a *rate*, and searching harder simply produces more of it.

A mechanism requirement is the only known filter that acts on the search space *before* the search. It does not adjust for the multiplicity problem; it **shrinks the space in which multiplicity can occur**, and it does so on grounds independent of the data. This is a difference in kind: FDR, DSR, and PBO are corrections applied *after* the damage; the mechanism requirement prevents the damage from being possible.

### 7.2 The argument from non-stationarity

Under P1, no stable process exists to be estimated. A relationship fitted to a period is a description of that period. The only ground for expecting it to hold in the *next* period is an argument that the *cause* still operates. Statistics describe what happened; mechanisms are what license extrapolation to what has not yet happened.

**A statistical result without a mechanism is a historical fact.** It is not a prediction, and treating it as one is not a small error of degree — it is an inference the evidence cannot support at any sample size. This is why no amount of data rescues an E1 claim: the missing ingredient is not statistical power, it is a warrant for extrapolation, and power cannot supply it.

### 7.3 The argument from asymmetric constraint

Consider two orderings:

| Ordering | What happens |
|---|---|
| **Mechanism → prediction → test** | The mechanism is authored *blind to the result*. It constrains the prediction's sign, scope, conditionality, and expected magnitude. It **can** be wrong, and it frequently is (F1). The test is severe. |
| **Result → mechanism** | The mechanism is authored *knowing the result*. A competent economist can supply a plausible story for **any** result, including the opposite one. It constrains nothing. It **cannot** be wrong. |

The second ordering produces a mechanism that is unfalsifiable *even though every individual statement in it may be true*. Its defect is not falsity — it is that it carries no information, because it was guaranteed to be available whatever the data showed. This is why the ordering is architectural: the pipeline runs S2 (Mechanism) → S3 (Hypothesis) → S6 (Experiment), and no reordering preserves the epistemic content. **The mechanism requirement does its work only if the mechanism is authored in ignorance of the result.** A retro-fitted mechanism is not a partial success; it is a *counterfeit* — indistinguishable from the genuine article by inspection, which is exactly why the ordering must be enforced by process rather than judged by review.

### 7.4 The argument from diagnosis

When a live mechanism degrades, the institution must decide: is this noise, decay (F9), or a broken assumption? With a mechanism, the question is answerable — check whether the constraint still binds, whether the participant class still behaves as modeled, whether the venue rule changed. Without a mechanism, the only available responses are to stare at a drawdown and guess, or to re-fit — which is R7 and F7 in a single motion.

**A mechanism is therefore not merely an entry requirement. It is the institution's only diagnostic instrument for its own live knowledge.** An institution that accepts mechanism-free claims does not merely accept weaker evidence; it forfeits any ability to reason about its holdings after acceptance.

### 7.5 The rule

> **R18 (justified by P2, §7.1–§7.4):** No statistical result, at any significance, effect size, or sample size, is sufficient for an inefficiency claim absent an ex-ante economic mechanism.
> **The mechanism is necessary and not sufficient. Statistics are necessary and not sufficient. The conjunction is required, in that order.**

---

## 8. Why Reproducibility Is Mandatory

### 8.1 Reproducibility is constitutive of the claim, not a property of it

> **P8 — An irreproducible result is not a weak result. It is not a result.**
> A scientific claim is a claim about a *procedure* and what it yields. If the procedure cannot be re-executed to yield the same thing, then no claim was made — an event occurred on a computer once, and was described. The description may be sincere and still be empty.

This is stronger than the ordinary engineering case for reproducibility, and the strength is the point. The engineering case says reproducibility is *valuable* (audit, debugging, onboarding). The scientific case says reproducibility is **the difference between a claim and an anecdote**. It is not a quality attribute of the result; it is the condition of the result existing at all.

### 8.2 The three arguments

**Epistemic (from §4.3).** The evidential weight of a result is not recoverable from the result — only from the process that produced it. Provenance is therefore not metadata *about* the evidence; provenance is *part of* the evidence. An institution that loses the process has not lost the audit trail; it has lost the meaning of its own numbers.

**Institutional (from P4).** Knowledge held only in an individual's working memory or unrecorded environment is not institutional knowledge; it is tribal knowledge with an expiry date attached to a person. It cannot be audited, inherited, defended, or safely retired. It is a liability that reads as an asset on the institution's books.

**Adversarial (from R4, §2.2).** The Validation Reviewer's mandate is to attempt refutation. A result that cannot be re-executed cannot be attacked. Irreproducibility is therefore not merely a gap — it is **structural immunity from criticism**, and P3 holds that a claim immune from criticism is not a knowledge claim. This is the deepest reason F6 voids rather than defers: irreproducibility does not leave a claim unproven, it removes it from the class of things that can be proven or disproven.

### 8.3 What must be reproducible

The **claim**, not the bytes. Reproducibility is a property of the specification: an independent researcher, given the hypothesis specification, the methodology, and the identified data, must reach the *same scientific conclusion* — the same sign, the same rejection or non-rejection of the null, the same order of effect magnitude.

**This document deliberately does not require bit-identity.** Bit-identity is a *sufficient* condition for reproducibility, not a necessary one, and it is a construction-hard property (cross-hardware floating-point determinism is defeated by SIMD reassociation, FMA contraction, and BLAS thread-count nondeterminism). ISO 42010 §5.3 makes feasibility-of-construction a required concern; an architecture that asserts a construction-hard property, gates on it, and never frames it has not framed that concern. This is finding **AQ-4**, and L1's position is that the scientific requirement is *conclusion-invariance under independent re-execution*, which is both weaker and more useful — it is what science actually needs, and it is achievable.

L2/L5 may impose bit-identity as an *implementation strategy* for achieving conclusion-invariance. If it does, it owns the feasibility argument. L1 requires only the conclusion. See §15 for the recorded inconsistency this creates with the corpus as it currently stands.

### 8.4 The rule

> **R19 (justified by P8, §8.2):** A result that cannot be independently reproduced from its specification is **void** (F6) — not "pending," not "provisional," not "weak evidence." It is withdrawn from the corpus and its Accepted Knowledge status, if any, is revoked.

### 8.5 The corollary that costs something

R19 implies that the institution will sometimes void results it believes are true, because reproduction failed for a reason that feels incidental — an unrecorded environment, a lost seed, an unversioned dependency. This is not a defect of the rule; it is the rule working. An institution that makes an exception for a result it likes has replaced R19 with "reproducibility is required except when inconvenient," which is R7.4 (threshold migration) applied to method rather than to data. The exception is not available, and no evidence of a claim's truth is a ground for granting it — that is precisely the direction from which the pressure will come.

---

## 9. Scientific Assumptions

These are the load-bearing beliefs this institution takes on without proof. Each is a **live risk**, not a settled matter. Each carries the failure mode that would follow if it were false, and each is stated so that a future reviewer can attack it directly. This section exists because an assumption that is not written down cannot be revisited — it is simply how everyone thinks.

| # | Assumption | If false, then… | Status / mitigation |
|---|---|---|---|
| **A1** | **Mechanisms exist and are knowable.** Price deviations have identifiable causes in participant constraints, discoverable from available evidence. | The entire method is misdirected; pattern-mining would strictly dominate. | Accepted on P1. Falsifiable in principle by a long record of mechanism-explained claims failing at the *same rate* as mechanism-free ones — a comparison the Failure Library makes possible. |
| **A2** | **The past constrains the future** — enough that a mechanism observed to have operated may operate again. | No empirical research is possible at all; only real-time reaction. | Irreducible. This is the minimal assumption without which the enterprise is void. Bounded by A5 and LIM2. |
| **A3** | **Available data faithfully represents the mechanism's operation** at the fidelity we claim. | Conclusions describe the data vendor's artifacts, not the market. | **Actively managed** — [[DATA_FEASIBILITY_STUDY]] is the binding scope constraint; fidelity limits are declared in LIM1. |
| **A4** | **Observation does not materially alter the system** at our scale. | The act of research changes the object of research. | Safe at current capacity; **fails at scale** — a mechanism captured at size ceases to be the mechanism observed. Bounded by the capacity requirement (D4) and F8. |
| **A5** | **Regimes exist and are approximately identifiable ex post.** | Regime-conditional claims are unfalsifiable, since the conditioning variable is undefined. | **Weakest assumption in this document.** Regimes are constructs, never measurements (§3.1). Regime-conditional claims carry an elevated burden and must declare the regime definition *ex ante* or fall to F5. |
| **A6** | **The venue's rules are as published and are stable within a sample.** | D1 is fiction and M6 mechanisms are unfounded. | Falsifiable and cheap to check; rule changes must be treated as structural breaks (D6), not as noise. |
| **A7** | **The institution's own multiplicity is countable.** | Every multiplicity correction is a number computed against an unknown denominator, and therefore meaningless. | **Requires institutional discipline to remain true.** A single unlogged search silently falsifies A7 and invalidates every DSR the institution computes thereafter. This is the assumption most easily destroyed by ordinary human behavior. |
| **A8** | **Researchers act in good faith and the method's controls bind them.** | All controls are theater; no epistemology survives. | Bounded by mechanism over policy (R6): the institution prefers controls that do not depend on A8. **Every control that relies on A8 rather than on a mechanism is a place where this assumption is doing load-bearing work** — and each such place should be treated as a defect awaiting a mechanism. |

> **R20:** Every assumption A1–A8 is subject to the same falsification discipline as any hypothesis. A demonstration that one is false is a first-class institutional finding, higher in value than any individual mechanism, because it invalidates a class of them.

---

## 10. Scientific Limitations

What this institution **cannot** know, stated so that no reader — internal or external — mistakes the scope of its claims. Each limitation carries the claim the institution must therefore refrain from making. This section is what makes the institution's claims honest: a claim is only as credible as the explicitness of what it does not cover.

### LIM1 · Observational fidelity is bounded, and the bound is not a detail
The institution observes daily bars deeply, minute-level signed flow and trade prints shallowly, and **never** observes the limit order book, quotes, auction messages, queue position, or cancellations ([[DATA_FEASIBILITY_STUDY]] §4.3–§4.4).
**Therefore:** mechanisms whose operation is *only* visible at unobserved fidelity are **not falsifiable by this institution** and cannot be claimed at all — not "claimed weakly." Where a proxy substitutes for an unobserved quantity, the claim is about *the proxy*, and the inferential gap between proxy and quantity must be stated as part of the claim rather than assumed away. A proxy is a different measurement, not a noisy version of the same one.

### LIM2 · No causal identification, only causal argument
The institution runs no experiments. It cannot randomize; it cannot intervene. Its "causal" mechanism claims are **arguments from constraint and design**, corroborated by observation — not identified causal effects.
**Therefore:** no claim of causal identification may be made. Natural experiments (rule changes, index reconstitutions, halts) are the strongest identification available and should be sought precisely because they are the only place the institution's causal language approaches its literal meaning.

### LIM3 · The multiplicity denominator is estimable, not knowable
A7 requires countable multiplicity, but the true family includes every search ever run, by anyone, including those that pre-date the discipline and those never logged.
**Therefore:** every multiplicity-adjusted statistic is a **lower bound on the correction required.** The true correction is larger by an unknown amount. Adjusted statistics should be read as "at best this severe," never as "this severe."

### LIM4 · Short history caps what is testable, and time is the only remedy
Most non-OHLCV datasets carry 3 weeks to 3.5 months of history. Regime-stratified validation, walk-forward testing, and decay estimation require multi-year spans.
**Therefore:** hypotheses on short-history data must declare a **history-maturity gate** ([[DATA_FEASIBILITY_STUDY]] §5.3) and remain unvalidated until it clears. Waiting is not a failure state; it is the correct state, and it cannot be shortened by cleverness.

### LIM5 · Single-institution replication is weak replication
Independent reproduction (E6) will usually be by the same person, on the same machine, from the same specification. This tests specification completeness — genuinely valuable — but **not** researcher-independence.
**Therefore:** the institution's E6 claims are *specification-reproducible*, not *independently replicated*, and must be labeled as such. Claiming independent replication where only self-replication occurred is a misrepresentation of tier, which under §4.2 is a misrepresentation of evidential weight.

### LIM6 · Adversarial review is structurally compromised at this scale
The methodology presupposes ≥3 distinct humans (CRO, Quant Researcher, Validation Reviewer with an OOS-access firewall between them). A single-researcher institution cannot instantiate the firewall: **the person prohibited from seeing out-of-sample data during formulation is the same person who must audit that prohibition.** This is finding **AQ-6**, and L1 does not pretend it away.
**Therefore:** at single-researcher scale, adversarial review is **an unmet structural requirement, not a satisfied one.** The institution must either (i) substitute mechanisms that do not require role separation — enforced OOS custody (R6), immutable pre-registration hashes, automated gates that cannot be self-waived — or (ii) declare the review requirement unmet and mark affected claims accordingly. **What it may not do is describe the role separation as satisfied because one person performed both roles sequentially.** Sequential performance by one mind is not independence; it is the same prior, applied twice. The degenerate mode is a matter for L0/L2 governance to specify; L1's requirement is only that the deficit be *declared* rather than absorbed.

### LIM7 · Decay is detectable only in arrears
P7 asserts finite half-lives. But distinguishing decay (F9) from an unlucky run requires enough post-decay data to reject the live hypothesis — by which time the mechanism has been dead for exactly as long as it took to notice.
**Therefore:** the institution will always be late in retiring knowledge. Retirement rules should be biased toward premature retirement, because under P4 the cost of holding a false belief exceeds the cost of re-registering a true one that was retired early. Re-registration is cheap; a false belief consumes capital and, worse, credibility.

### LIM8 · This document cannot secure its own application
No epistemology enforces itself. Every rule here can be satisfied in letter and violated in spirit by a researcher under pressure to find something — and the violations that matter (retro-fitted mechanisms §7.3, rescued failures §5.4, unlogged searches A7) are precisely the ones that are **invisible in the artifact they produce.** A rescued claim and a survived claim are identical on inspection.
**Therefore:** the institution's true epistemic state is not verifiable from its outputs alone, and any claim to the contrary is false. This is the strongest argument in the corpus for preferring **mechanisms over policies** (R6) — not because researchers are untrustworthy, but because a mechanism produces evidence of its own operation, and a policy produces only evidence of its own existence.

---

## 11. Relationship to Every Existing Phase-A Document

Per ISO 42010 §5.6, this section records the correspondences between this viewpoint and every other document in the Phase-A corpus. Each row states what the other document *inherits* from L1 and what L1 *requires* of it. Known inconsistencies are recorded in §15 rather than silently resolved.

### 11.1 The L2 canonical architecture documents

| Document | Layer | Inherits from L1 | L1 requires of it | Correspondence |
|---|---|---|---|---|
| [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] | L2 | The S1→S10 ordering **is** §7.3's argument made procedural: Mechanism (S2) precedes Hypothesis (S3) precedes Experiment (S6) precisely so the mechanism is authored blind to the result | That the ordering is never relaxed for expedience; that S2's "must not violate market micro-economics" gate is read as F1, the privileged cheap falsification (§5.3) | **Consistent.** The Pipeline is the operational realization of this document's method. Its per-stage validation criteria are the strongest 42010-conformant work in the corpus |
| [[RESEARCH_OBJECT_MODEL]] | L2 | Its objects are the *artifact* ontology; §3 is the *world* ontology. The Hypothesis Object's fields are §5.2's six admissibility elements given a schema | That Hypothesis carries mechanism class (M1–M6), scope, ex-ante criteria, family denominator, and an immutable pre-registration hash+timestamp; that `required_data` respects the binding scope constraint | **Inconsistent** — see §15.1 (AQ-1) and §15.2 (AQ-2) |
| [[RESEARCH_OPERATING_MODEL]] | L2 | Its Discovery→Confirmation→Accepted tiers **are** §2.4's custody states; its G1 gate **is** §5.2's admissibility test; its adversarial reviewer **is** §2.2's asymmetric burden made a role | That custody be enforced by mechanism, not policy (R6); that the single-researcher deficit be declared, not absorbed (LIM6) | **Partially inconsistent** — see §15.3 (AQ-6), §15.4 (W9) |
| [[RESEARCH_VALIDATION_FRAMEWORK]] | L2/L7 | Its §3 ("a mechanism is invalid, regardless of statistical significance, if it cannot be explained…") is R18. Its FDR/DSR/PBO battery operationalizes §7.1's multiplicity argument and D6 | That severity (R3) and power/MDE (R2) be added — an underpowered test is *no* evidence, not weak evidence; that "Replication" be read at LIM5's honesty (specification-reproducible ≠ independently replicated) | **Consistent in substance; incomplete.** This document supplies the rationale its §3 asserts but never defends (AQ-7) |
| [[FEATURE_COMPUTATION_GRAPH]] | L2/L5 | Immutability-on-use is §4.3: the evidential weight of a result is unrecoverable from the result, so the artifact that produced it must be frozen | That its bit-identity requirement be recognized as an implementation *strategy*, not the scientific requirement (§8.3); that if code-coupled identity is retained, FCG is declared design-level | **Inconsistent** — see §15.5 (AQ-4), §15.6 (AQ-3) |
| [[FAILURE_LIBRARY_SCHEMA]] | L2/L8 | It **is** R12 given a schema. `failure_reason` is §5.3's F1–F9; `invalid_assumptions` is R1's Duhem–Quine attribution requirement | That its `failure_reason` vocabulary align with F1–F9 and separate F9 (decay — not an error) from F1–F8; that its completeness be treated as a precondition of A7, since an incomplete library silently biases every multiplicity calculation | **Consistent.** L1 strengthens the case: this library is the institution's self-diagnostic (§5.3), not merely an archive |
| [[MICROSTRUCTURE_RESEARCH_ROADMAP]] | supporting | Its Programs are instances of §3.4 classes: OFI→M1/M2, Auction Dislocation→M6/M4, Liquidity Vacuum→M1/M3 | That its scope obey [[DATA_FEASIBILITY_STUDY]]; its stated data requirements (L3 LOB, depth updates, auction messages) are Institutional-Only and its research questions are, under LIM1, **not falsifiable by this institution as written** | **Inconsistent as written** — see §15.1. Retained as Future Capability (P5), per roadmap §3 |

### 11.2 The L0 governance documents

| Document | Relationship to L1 |
|---|---|
| [[DATA_FEASIBILITY_STUDY]] | **Binds L1.** Its §4 Capability Matrix is what LIM1 states as an epistemic limit. Its authority is not merely administrative: a mechanism unobservable at attainable fidelity is *unfalsifiable here*, which by R14 means it cannot be admitted. Feasibility is therefore a **scientific** constraint, not a budgetary one — this document exists partly to say so |
| [[TAXONOMY_AND_NAMING_STANDARD]] | **Binds L1's vocabulary.** §12's glossary is L1's scientific extension of it: the taxonomy governs *structural* terms (Layer/Program/Stage/Gate/State); §12 governs *scientific* terms (mechanism, evidence, falsification, regime, family). No term is defined in both; where a term appears in both, the taxonomy governs |
| [[RESEARCH_OS_RECONCILIATION]] | **Locates L1.** Under its §5.4, scientific method and institutional governance are owned by the OS — so this document governs those questions. Under §5.3, mechanisms already built in v3 win on conflict. L1 therefore *describes and justifies* v3's method where they agree, and records disagreement in §15 rather than overriding a tested, frozen system |
| [[RESEARCH_OS_MASTER_ROADMAP]] | **Scheduled L1.** Its §2 marks L1 "🟡 Conceptually done (6 domains); needs domain de-overlap + Market-Design + Limits-to-Arbitrage." §3.5 discharges that item: the six domains D1–D6 are partitioned with explicit non-overlap, Market Design (D1) and Limits-to-Arbitrage (D3) are added, and Cost/Impact (D4) is promoted from a validation concern to a domain |
| [[REVISION_IMPACT_ASSESSMENT]] | **Corrected by L1.** Its §3 claims the "7 canonical architecture documents are byte-for-byte unchanged," listing *Market Inefficiency Foundation* among them. **No such file existed.** This document is that artifact, authored rather than preserved. §15.7 records the correction |
| [[FUTURE_GOVERNANCE_OUTLINES]] | **Sourced by L1.** KNOWLEDGE_LIFECYCLE (L8) inherits P7 and LIM7 — decay is mortality, not error, and retirement should be biased early. RESEARCH_PRIORITIZATION_FRAMEWORK (L0) inherits §6.4: prioritize where origination and persistence conditions coincide, not where effects are famous |
| [[WORKED_EXAMPLE_END_TO_END]] | **Instantiates L1.** Amihud illiquidity is class **M3**, domain **D3+D4**, with an explicit persistence reason (`persistence_theory: limits-to-arbitrage — illiquidity itself deters the arbitrage that would remove the premium`) — a textbook R16 answer to both origination *and* persistence. That the example satisfies §6.2 without having been written against it is genuine independent corroboration that L1 describes the institution's actual practice rather than an aspiration for it |
| [[PHASE_A_ARCHITECTURE_REVIEW]] | **Commissioned L1.** Its W8 ("missing foundational domains") and §8 exit criterion ("domain set revised… no overlap") are discharged by §3.5. Its R4 (merge D1+D2, add Market Design + Limits-to-Arbitrage, promote Cost/Impact) is implemented, with rationale in ADR-L1-004 |
| Falsification review (AQ/RQ findings) | **Specified L1.** AQ-8 ("Scientific Foundation concern unframed — High") is closed by this document under 42010 §5.5. AQ-7 (no rationale) is closed *for L1 only* by §13/§14. AQ-1, AQ-2, AQ-3, AQ-4, AQ-6 concern L2 artifacts and are **recorded, not resolved**, in §15 — resolving them would be redesign, which is outside this document's mandate |

---

## 12. Formal Glossary

The controlled vocabulary of scientific terms. Every corpus document MUST use these terms in exactly these senses. Structural terms (Layer, Program, Stage, Gate, Step, Lifecycle State) are defined by [[TAXONOMY_AND_NAMING_STANDARD]] and are not redefined here.

| Term | Definition | Not to be confused with |
|---|---|---|
| **Accepted Knowledge** | A mechanism claim that has survived F1–F9 at evidence tier ≥E4 and is provisionally believed by the institution, pending decay. Revocable by construction | Proof; permanence; a profitable strategy |
| **Alpha** | A summary statistic of a return comparison to a benchmark under a stated cost model. **Not a substance and not a quantity that exists** | A mechanism; a thing to be "extracted" |
| **Assumption** | A load-bearing belief held without proof, declared in §9 with its failure mode | A fact; a convention |
| **Capacity** | The size at which a mechanism's capture cost consumes its deviation (D4). Extinction at deployable size is **F8** | Liquidity; position limits |
| **Confirmation** | The custody state in which exactly one severe, pre-registered test of a registered hypothesis is executed out-of-sample | Verification; proof; "confirming a pattern" |
| **Constraint** | A binding limit on a participant class (inventory, capital, mandate, horizon, information). **The primary generator of inefficiency** | A model parameter; a risk limit in production |
| **Decay** | The mortality of a mechanism (P7): its deviation vanishes because it was arbitraged or its generating constraint was removed. Filed **F9 — not an error** | Model failure; drawdown; overfitting |
| **Discovery** | The custody state of unconstrained exploration on in-sample data. **Produces hypothesis material, never knowledge** | Finding something; a result |
| **Domain** | One of the six exclusive subject areas D1–D6 of §3.5 | A Program; a data source; a Layer |
| **Evidence** | The outcome of a test that could have gone the other way (P5). Graded E0–E7 by §4.2 | Data; observation; a result; a backtest |
| **Falsification** | The demonstration that a claim is false, attributed to exactly one mode F1–F9 and defended against the alternative auxiliary explanations (R1) | Underperformance; a losing period; a failed run |
| **Family (multiplicity)** | The declared denominator of tests against which one test is counted. **Part of the claim, not of the analysis** (R7.5). Its true size is unknowable (LIM3) | The number of tests reported; a strategy set |
| **Feature** | A derived measurement of the market, positioned at the bottom of the causal order (§3.3). **Evidence flows up from it; explanation never originates in it** | A signal; a predictor; a mechanism |
| **Friction** | The unavoidable cost of interacting with the market mechanism: spread, impact, fees, slippage, rejection. Always non-zero (D4) | Transaction cost estimate; slippage assumption |
| **History-maturity gate** | A declared deferral of validation until a short-history dataset accumulates sufficient span (LIM4) | A delay; a soft threshold |
| **Hypothesis** | A falsifiable claim carrying all six elements of §5.2. Lacking any one, it is not a hypothesis | An idea; a conjecture; a strategy |
| **Inefficiency** | A systematic price deviation caused by an identified constraint on an identified participant class, persisting for an identified reason (R16). **Requires both origination and persistence** | A pattern; an anomaly; a profitable backtest |
| **Look-ahead** | Entry of information unavailable at decision time into a test. Falsification mode **F7** | Data leakage in the ML sense (narrower) |
| **Mechanism** | A causal structure by which a constraint on a participant class produces a systematic price deviation. Classified M1–M6 (§3.4). **A feature of the world** | The `Economic Mechanism Object` (the institution's *record* of a conjecture about one) |
| **Mechanism-first** | The requirement (R18) that an economic mechanism be authored *in ignorance of the result* and precede statistical evidence. **Ordering is the whole content** | Having an explanation; economic plausibility |
| **Origination** | Why a deviation arises. Half of R16; the cheap half | Persistence; the effect itself |
| **Participant class** | A set of agents sharing constraints and objectives (market maker, index fund, retail, foreign institution) | A counterparty; a broker |
| **Persistence** | Why a deviation has not been arbitraged away. The other half of R16; **the expensive, informative half** (§6.3) | Robustness; stability; stationarity |
| **Power / MDE** | The probability a test would detect the effect if present / the smallest effect it could detect. **A test without power is not weak evidence — it is no evidence** (R2) | Sample size; significance |
| **Pre-registration** | Fixing a hypothesis's criteria before the judging evidence is seen (R5). Immutable once registered | Documentation; a plan |
| **Proxy** | A measurement standing in for an unobserved quantity. **A different measurement, not a noisy version of the same one.** The inferential gap is part of the claim (LIM1) | An approximation; an estimate |
| **Regime** | A period during which the joint distribution is approximately stable. **Always a construct, never a measurement** (A5, §3.1) | A market condition; an observable state |
| **Reproducibility** | The property that an independent researcher, from the specification alone, reaches the same scientific conclusion (§8.3). **Constitutive of the claim, not an attribute of it** | Bit-identity (a strategy for it); re-running a script |
| **Severity** | The degree to which a test would probably have detected the hypothesis's falsity had it been false. **The institution's currency of evidence** (R3) | Significance; strictness; a p-value |
| **Signal** | *Deprecated as a scientific term.* No autonomous entity emits predictive information (§3.2). Use *feature* (measurement) or *mechanism* (cause) | — |
| **Worldview** | The set of propositions P1–P8 from which all rules in this corpus derive. Each is individually falsifiable and carries a defeater | Philosophy; preamble; mission statement |

---

## 13. Architecture Rationale (ISO 42010 §5.7)

§5.7 requires recorded rationale *and evidence of alternatives considered*. Finding **AQ-7** records that this is absent across the entire corpus. This section discharges it for L1. It does not discharge it for L2 — the Pipeline, the Object Model, the Operating Model, and the FCG each still owe their own rationale, and §15.8 records that debt.

### 13.1 Why an L1 document exists at all

**Considered:** (a) no L1 — let the method be implicit in L2's gates; (b) an L1 that is a reading list of domains and literature; (c) an L1 that states the epistemology the L2 gates enforce.

**Chosen: (c).** Option (a) is what produced AQ-7 and AQ-8: gates exist, each individually defensible, none defended, and no ground on which to adjudicate a proposed exception to one. Under 42010 §5.5 the Scientific Foundation concern was framed by nothing. Option (b) is a bibliography — it records what was read, not what is believed, and a future maintainer cannot reconstruct a method from a reading list. Option (c) makes the reasons contestable, which is the only property that lets the method be *corrected* rather than merely obeyed. Under P4, an uncontestable method is unmaintainable.

**Rejected consideration:** that L1 is "philosophy" and therefore decorative. The falsification review's own experience is the counter-evidence: it could not adjudicate AQ-3 (implementation leakage) or AQ-4 (bit-identity) without a stated position on what the architecture is *for* — and had to reason from ISO 42010 in the absence of one. Every such adjudication L1 does not supply, a reviewer must invent, inconsistently, forever.

### 13.2 Why critical rationalism rather than Bayesian epistemology

**Considered:** (a) Bayesian — beliefs as probabilities, updated by evidence; (b) critical rationalism — conjecture and refutation; (c) frequentist-only — significance testing without an epistemic frame; (d) hybrid.

**Chosen: (b), with Mayo's severity criterion (§2.1) and an explicit acknowledgment that (a) is a legitimate alternative.**

Reasons: **(i)** Priors are unauditable. In an institution where the researcher is often also the reviewer (LIM6), a prior is a degree of freedom indistinguishable from a preference, and A8 is already carrying more weight than it should. Critical rationalism demands a *stated refutation condition* — an artifact a reviewer can check against, which a prior is not. **(ii)** Under P1 the posterior would be updating toward a parameter that does not exist; the Bayesian machinery is well-defined but its target is not. **(iii)** Option (c) is what §7.1 refutes: significance without an epistemic frame is a rate, not a filter.

**The honest cost:** critical rationalism handles *accumulation* of evidence poorly. It is sharp on refutation and awkward about "how much support does this now have?" — which is exactly what §4.2's tier hierarchy is a workaround for. A Bayesian institution would handle E-tier accumulation more naturally and would pay for it in auditability. **This is a genuine trade, not a dominant choice**, and a future institution with multiple independent researchers and auditable elicited priors should revisit it. The decision is recorded as ADR-L1-002 with that revisit condition attached.

### 13.3 Why mechanism-first rather than statistics-first

**Considered:** (a) statistics-first with mechanism as ex-post explanation; (b) mechanism-first (R18); (c) either, with mechanism raising confidence but not gating.

**Chosen: (b).** §7.1–§7.4 is the full argument. Concisely: (a) is refuted by §7.3 — a mechanism authored knowing the result constrains nothing and cannot be wrong, so it carries no information; it is a *counterfeit indistinguishable by inspection from the genuine article*. (c) collapses into (a) under pressure, because a non-gating requirement is satisfied by any plausible story, and plausible stories are free.

**The cost, stated plainly:** mechanism-first will cause this institution to **discard real, exploitable inefficiencies whose mechanism it cannot articulate.** That is a genuine, recurring, permanent loss, and it will occasionally be visible and painful. It is accepted because the alternative — accepting effects it cannot explain — forfeits the only diagnostic instrument it has for its live knowledge (§7.4), and under P4 an institution that cannot diagnose its own beliefs cannot hold any.

### 13.4 Why reproducibility is constitutive rather than a quality attribute

**Considered:** (a) reproducibility as best practice, encouraged; (b) as a required quality gate; (c) as constitutive — irreproducible ⇒ not a claim (P8/R19).

**Chosen: (c).** Under (a) or (b), reproducibility is a property a result may have in degree, which licenses "this result is true but irreproducible" — a sentence §8.2's adversarial argument shows to be incoherent: a claim that cannot be re-executed cannot be attacked, and a claim immune from criticism is not a knowledge claim under P3. **The cost is real** (§8.5): the institution will void results it believes are true. That is the rule functioning, and the exception is unavailable precisely because the pressure to grant it will always come dressed as evidence that the claim is true.

### 13.5 Why conclusion-invariance rather than bit-identity

**Considered:** (a) bit-identity as the scientific requirement (the corpus's current position); (b) conclusion-invariance (§8.3); (c) silence.

**Chosen: (b).** Bit-identity is sufficient but not necessary, and it is construction-hard across hardware — a required 42010 §5.3 concern the corpus asserts, gates on, and never frames (AQ-4). Science needs the conclusion to be robust to re-execution; it does not need the last mantissa bit. Choosing (b) also *relocates* the problem correctly: bit-identity remains available to L5 as an implementation strategy, and if L5 adopts it, L5 owns the feasibility argument. (c) is what produced AQ-4.

### 13.6 Why six domains, partitioned exclusively

**Considered:** (a) the original six with acknowledged overlap; (b) the review's R4 revision — merge microstructure+price-formation, add Market Design and Limits-to-Arbitrage, promote Cost/Impact; (c) a finer taxonomy of ten-plus domains.

**Chosen: (b), with an explicit adjudication rule (§3.5).** Overlapping domains are not a cosmetic defect: under R16, if no domain *owns* persistence, no reviewer is accountable for asking the persistence question, and §6.3 holds that this is the question most claims should die on. D3's existence as a domain is what makes R16.2 institutionally enforceable rather than aspirational. (c) fragments ownership and multiplies boundary disputes without adding accountability. Ordering substrate-before-phenomenon (D1→D6) encodes §3.3's causal order in the domain list itself.

### 13.7 Why feasibility binds the science

**Considered:** (a) feasibility as a budget/procurement matter, orthogonal to method; (b) feasibility as a scientific constraint (LIM1).

**Chosen: (b).** This is the one place where the falsification review's ranking of AQ-1 as its most serious finding is *derivable from L1 rather than merely asserted*: R14 requires a stated refutation condition; a refutation condition that requires unobtainable data is not a refutation condition; therefore **a mechanism unobservable at attainable fidelity is unfalsifiable here and cannot be admitted at all.** Feasibility is not downstream of the science — for this institution it *is* science. That is why the Object Model teaching `L3 Order Book, BBO, nanosecond` as its exemplars is not an untidy example set; it teaches researchers to author unfalsifiable hypotheses.

---

## 14. Architectural Decision Records

Format per ISO 42010 §5.7 (decision, alternatives, rationale, consequences, revisit condition). Status values: ACCEPTED · SUPERSEDED · REVISIT-SCHEDULED.

---

### ADR-L1-001 · The system-of-interest is the research institution, not the trading system
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** The repository contains a live trading system (v3) whose Phase C gatekeeper is verified end-to-end. It would be natural to treat research as a subsystem of it.
**Decision:** The system-of-interest is the Research OS. Trading is a downstream consumer. The dependency is one-directional (§0.1).
**Alternatives:** (a) research as a subsystem of trading — rejected: it makes capital outcomes the arbiter of truth, which is R7.1 (profit as proof) elevated to an architecture; (b) co-equal peers — rejected: it leaves the arbitration question open, which is how R7.1 re-enters under pressure.
**Consequences:** Research may — and periodically will — conclude that a profitable production behavior is not knowledge. This is correct and must not be treated as a defect of the research.
**Revisit if:** the institution ever ratifies capital outcomes as evidence, which would require refuting P2 first.

---

### ADR-L1-002 · Critical rationalism + severity, not Bayesian epistemology
**Status:** ACCEPTED · **REVISIT-SCHEDULED** · **Date:** 2026-07-15
**Context:** §13.2. The institution needs an auditable standard of evidence under a single-researcher constraint (LIM6) and non-stationarity (P1).
**Decision:** Adopt critical rationalism, corrected for Duhem–Quine and probabilistic refutation, with Mayo's severity criterion as the currency of support (§2.1).
**Alternatives:** Bayesian (rejected — unauditable priors under LIM6; posterior targets a parameter P1 denies exists); frequentist-only (rejected — §7.1: a rate, not a filter); hybrid (rejected — inherits the auditability problem without resolving it).
**Consequences:** Sharp refutation, awkward accumulation. §4.2's E-tier hierarchy is an explicit workaround for the accumulation gap, and it is a ladder rather than a calculus. This is a **known limitation of the chosen frame, not an oversight**.
**Revisit if:** the institution reaches ≥3 independent researchers with elicitable, auditable priors — at which point Bayesian accumulation becomes both tractable and auditable, and the trade may reverse.

---

### ADR-L1-003 · Mechanism-first is a gate, not a preference
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** §13.3, §7.1–§7.4. [[RESEARCH_VALIDATION_FRAMEWORK]] §3 already asserts this. No document defended it (AQ-7).
**Decision:** R18 — no statistical result at any strength suffices absent an ex-ante mechanism. Mechanism necessary, statistics necessary, neither sufficient, order mandatory.
**Alternatives:** statistics-first with ex-post explanation (rejected — §7.3: retro-fitted mechanisms constrain nothing and are counterfeits indistinguishable by inspection); mechanism as confidence-raiser (rejected — collapses to statistics-first under pressure, since plausible stories are free).
**Consequences:** Real inefficiencies will be discarded for want of an articulable mechanism (§13.3). Accepted knowingly. The mechanism requirement is also the institution's only post-acceptance diagnostic (§7.4), which is what makes the trade worth taking.
**Revisit if:** A1 is falsified — i.e., mechanism-explained claims are shown to fail at the same rate as mechanism-free ones over a long record. The Failure Library makes this comparison possible; it is the highest-value analysis the institution can eventually run on itself.

---

### ADR-L1-004 · Six exclusive domains, substrate before phenomenon
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** §13.6. Review W8/R4 and the roadmap's open exit item *"L1 domain de-overlap."*
**Decision:** D1 Market Design (IDX) · D2 Microstructure & Price Formation · D3 Limits to Arbitrage & Persistence · D4 Transaction Cost, Impact & Capacity · D5 Behavioral & Institutional Flow · D6 Inference under Non-Stationarity. Exclusive subjects, explicit non-ownership, adjudication rule (§3.5).
**Alternatives:** original overlapping six (rejected — unowned persistence question makes R16.2 unenforceable); ten-plus domains (rejected — fragments ownership without adding accountability).
**Consequences:** Discharges the roadmap exit item. D1 is venue-specific to IDX and would need a sibling if a second venue is ever added — a known and acceptable scaling seam.
**Revisit if:** a second venue enters scope, or a mechanism arises that no domain owns under the adjudication rule.

---

### ADR-L1-005 · Reproducibility is constitutive; conclusion-invariance is the requirement
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** §13.4, §13.5. AQ-4 records that the corpus asserts and gates on bit-identity without framing its feasibility.
**Decision:** P8/R19 — irreproducible ⇒ void (F6), not pending. The requirement is conclusion-invariance under independent re-execution from the specification (§8.3). Bit-identity is available to L5 as an implementation strategy; if adopted, L5 owns the feasibility argument.
**Alternatives:** bit-identity as the scientific requirement (rejected — sufficient but not necessary, and construction-hard: SIMD reassociation, FMA contraction, BLAS nondeterminism); reproducibility as best practice (rejected — licenses "true but irreproducible," incoherent under §8.2).
**Consequences:** The institution will void results it believes are true (§8.5). This weakens the corpus's current L5 requirement and creates a recorded inconsistency (§15.5) that L2/L5 must resolve — L1 does not resolve it unilaterally, because that would be redesign.
**Revisit if:** L5 demonstrates cross-hardware bit-identity is cheaply attainable, in which case the strategy question is settled without changing the scientific requirement.

---

### ADR-L1-006 · Data feasibility is a scientific constraint, not a budget constraint
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** §13.7. [[DATA_FEASIBILITY_STUDY]] declares itself the binding scope constraint on administrative authority. L1 grounds it on scientific authority.
**Decision:** LIM1 — a mechanism unobservable at attainable fidelity is unfalsifiable by this institution (R14) and is therefore inadmissible, not merely unaffordable. Proxies measure *different quantities*; the inferential gap is part of the claim.
**Alternatives:** feasibility as procurement, orthogonal to method (rejected — it implies the science is correct and merely unfunded, which licenses architecting against data that will never exist; this is precisely the W1/AQ-1 failure).
**Consequences:** Programs P5/P6 are not "deferred research" — they are **currently unfalsifiable claims**, correctly retained as Future Capability and correctly excluded from the executable corpus. Elevates AQ-1 from an untidy example set to a defect that teaches researchers to author unfalsifiable hypotheses.
**Revisit if:** the L1 quote/BBO procurement question ([[DATA_FEASIBILITY_STUDY]] §6) resolves affirmatively — which moves capabilities across the matrix and reopens admissibility.

---

### ADR-L1-007 · Declare the single-researcher review deficit; do not absorb it
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** LIM6 / AQ-6. The Operating Model presupposes ≥3 humans with an OOS firewall; the institution has one researcher.
**Decision:** L1 declares adversarial review **structurally unmet at current scale**. Claims affected must be marked. The institution should substitute controls that do not require role separation (enforced custody, immutable pre-registration hashes, non-self-waivable gates) — R6's "mechanism over policy" applied to governance. Specifying the degenerate mode is L0/L2's job; L1 requires only that the deficit be visible.
**Alternatives:** declare the requirement satisfied by sequential role-play (rejected — one mind applying the same prior twice is not independence; this is the more dangerous option precisely because it is invisible in the artifact, per LIM8); drop adversarial review (rejected — it is R4's asymmetric burden made operational, and dropping it removes the burden).
**Consequences:** The institution's own AD records that its methodology exceeds its capacity. This is uncomfortable and is the point: under LIM8, an unrecorded deficit is indistinguishable from a satisfied requirement.
**Revisit if:** headcount reaches ≥2 with an enforceable OOS firewall between formulation and audit.

---

### ADR-L1-008 · Record L2 inconsistencies; do not resolve them here
**Status:** ACCEPTED · **Date:** 2026-07-15
**Context:** Authoring L1 exposes conflicts with L2 artifacts (AQ-1, AQ-2, AQ-3, AQ-4, AQ-6). The mandate for this document is explicitly *not to redesign anything*.
**Decision:** Record every known inconsistency in §15 per 42010 §5.6, with the L1 position stated and the owning document named. Change no L2 document.
**Alternatives:** silently conform L2 to L1 (rejected — out of mandate, and it would destroy the review trail that makes the conflicts legible); soften L1 to fit L2 (rejected — it would reproduce AQ-1's exact pathology, a foundation shaped to match an artifact rather than the artifact to the foundation); omit the conflicts (rejected — §5.6 requires recording, and AQ-1 is currently an *unrecorded* inconsistency, which is what made it survivable).
**Consequences:** The corpus contains recorded, visible disagreement between L1 and L2 pending resolution. **This is a stronger state than the current one, not a weaker one** — the inconsistencies already existed; they were simply unrecorded, which is the condition under which they persist.
**Revisit:** at each §15 item's resolution.

---

## 15. Known Inconsistencies (ISO 42010 §5.6)

§5.6 requires that known inconsistencies between views **shall be recorded**. Authoring L1 makes several conflicts explicit that were previously implicit. Recording them is this document's job; resolving them is not (ADR-L1-008).

| # | Inconsistency | L1's position | Owner | Finding |
|---|---|---|---|---|
| **15.1** | [[RESEARCH_OBJECT_MODEL]] teaches `required_data: "e.g., L3 Order Book, Trades, BBO"`, `resolution: "e.g., Nanosecond…"`, `classification: "e.g., Latency Arbitrage…"` — all classified Institutional-Only/Unrealistic by the binding scope constraint. [[MICROSTRUCTURE_RESEARCH_ROADMAP]] Phases I–III require the same | Under ADR-L1-006 these exemplars teach researchers to author **unfalsifiable** hypotheses (LIM1). This is why the falsification review ranks AQ-1 as its most serious finding, and L1 independently derives that ranking rather than inheriting it | L2 · Object Model; supporting · Microstructure Roadmap | **AQ-1 (Critical)** |
| **15.2** | `Accepted Knowledge Object.decay_monitor_id` references a Decay Monitor object that does not exist in the model; roadmap §4 places Decay Monitor in the optional Extension set | P7 makes decay monitoring **constitutive** of Accepted Knowledge, not optional — a claim whose mortality is untracked cannot be retired (LIM7), and an unretireable claim is not revocable, contradicting P3 | L2 · Object Model (dangling ref) + Roadmap §4 (partition) | **AQ-2 (High)** / RQ-4 |
| **15.3** | [[RESEARCH_OPERATING_MODEL]] §5–§6 presuppose ≥3 distinct humans; the institution has one | Declare the deficit (ADR-L1-007). L1 does not weaken the requirement — a weakened requirement would be satisfiable, which is worse than an unmet one being visible | L2 · Operating Model | **AQ-6 (High)** |
| **15.4** | OOS custody is stated as a prohibition on a role ("Prohibited from accessing…"), not a mechanism | Epistemologically void (R6): unenforced custody yields a system whose evidential state cannot be known **by its own operators** (LIM8). Out-of-sample data is non-renewable and spends silently | L2 · Operating Model / L4 | W9 |
| **15.5** | [[FEATURE_COMPUTATION_GRAPH]] §5 requires bit-identical cross-hardware output; Pipeline S5 gates on it. L1 requires only conclusion-invariance (§8.3) | L1's requirement is weaker and is the scientifically correct one (ADR-L1-005). L2/L5 may keep bit-identity as a strategy, but then **owns** the 42010 §5.3 feasibility argument it currently omits | L2/L5 · FCG + Pipeline S5 | **AQ-4 (Medium)** |
| **15.6** | FCG §4 defines feature identity by git hash; Object Model `Feature Definition.code_reference` makes an implementation pointer a constituent field | §3's ontology is implementation-independent by construction (a Feature is a *measurement*, identified by its mathematical definition). An ontology that names its objects after their implementations is not conceptual. L1 takes no position on resolution (a) strike the coupling vs (b) declare FCG design-level — **but the corpus currently claims (a) and is written as (b)**, and that is the inconsistency | L2/L5 · FCG + Object Model | **AQ-3 (High)** |
| **15.7** | [[REVISION_IMPACT_ASSESSMENT]] §3 asserts the "7 canonical architecture documents are byte-for-byte unchanged," listing *Market Inefficiency Foundation* — which did not exist | Corrected by this document's existence. The preservation guarantee was, for this document, vacuously true. Note the sharper point the review made: **byte-for-byte preservation is simultaneously the mechanism by which the stale ontology of 15.1 survives.** Preservation and correction are in tension, and no document had noticed | L0 · Impact Assessment (bookkeeping) | **AQ-8 / RQ-5** |
| **15.8** | 42010 §5.7 rationale exists now for L1 only. The Pipeline, Object Model, Operating Model, Validation Framework, and FCG still record none | §13/§14 discharge AQ-7 for L1 and **do not** discharge it corpus-wide. Why a 10-stage pipeline? Why these five roles? Why FDR *and* DSR *and* PBO? Why immutability-on-use? Each is defensible; none is defended | L2 · all canonical docs | **AQ-7 (Medium)** |

---

## 16. Conformance Statement (ISO/IEC/IEEE 42010:2011)

| Clause | Requirement | Where discharged |
|---|---|---|
| **§5.2** | Identify system; identify stakeholders | §0.1, §0.2 |
| **§5.3** | Identify concerns incl. purpose, suitability, feasibility of construction, risks, evolvability | §0.3 (C1–C12); purpose §1; suitability §2; feasibility §8.3 + LIM1 (and §15.5 where the corpus fails it); risks §9; evolvability §13.1, §14 revisit conditions |
| **§5.4** | Viewpoint specifies concerns framed, stakeholders, model kinds and conventions | §0.4 |
| **§5.5** | One view per viewpoint; every concern framed by ≥1 viewpoint | §0.4; C1–C12 each mapped to a section. **This document closes AQ-8** — the Scientific Foundation concern is now framed |
| **§5.6** | Record correspondences between views; **known inconsistencies shall be recorded** | §11 (correspondences); §15 (inconsistencies) |
| **§5.7** | Record architecture rationale **including alternatives considered** | §13 (rationale, alternatives, costs); §14 (8 ADRs). **Discharges AQ-7 for L1 only** — §15.8 records the outstanding corpus-wide debt |

### 16.1 Effect on the Phase-A exit checklist

This document discharges one open item in [[RESEARCH_OS_MASTER_ROADMAP]] §7, and contributes to a second:

- ✅ **L1 domain de-overlap** — six exclusive domains with an adjudication rule; Market Design (D1) and Limits-to-Arbitrage (D3) added; Cost/Impact promoted to D4 (§3.5, ADR-L1-004).
- ✅ **Architecture rationale recorded** (42010 §5.7) — §13/§14 for L1; [[DECISION_LOG]] corpus-wide. Partial by design: the L2 rationale debt (RD-1…RD-7) is closable only by its original decider, not by this document.

**Correction, 2026-07-15 ([[DECISION_LOG]] C-8).** Version 1.0 of this section claimed to discharge the *"7 canonical docs cross-referenced"* exit item. **That was an overclaim by this document's own author.** [[RESEARCH_OS_RECONCILIATION]] §6 requires a one-line cross-reference to the v3 mechanism **inside each of the seven documents**. §11 maps them centrally, to *this* document's inheritance rather than to v3's mechanisms — a different artifact serving a different purpose. The item is reinstated as open:

- ⬜ **7 canonical docs cross-referenced** to their v3 mechanisms — requires an edit inside each document (the annotation commit of [[MIGRATION_PLAN]] §6).
- ⬜ **Independent adversarial sign-off** — by construction, not by the author (LIM6, ADR-L1-007). This document is a *candidate* canonical artifact until that signature exists.
- ⬜ **Repository baseline commit** — this document is untracked as written; durability precedes freeze ([[DECISION_LOG]] D-014).

### 16.2 Maturity effect

Per the falsification review's staged model, Architecture sat at **RL-1 with RL-3 evidence banked**, blocked on six RL-2 criteria: *update Object Model exemplars to feasible data (AQ-1); resolve `decay_monitor_id` (AQ-2); decide FCG's conceptual-vs-design status (AQ-3); frame or soften the bit-identical claim (AQ-4); write rationale (AQ-7); **write L1 (AQ-8)***.

This document closes the sixth. It also converts AQ-1 through AQ-4 from *unrecorded* inconsistencies into **recorded** ones (§15), which is what 42010 §5.6 requires and is a real advance — an unrecorded inconsistency is invisible and therefore permanent. It does not close them: each requires an edit to an L2 document, which is redesign and is outside this document's mandate (ADR-L1-008).

**RL-2 remains blocked on AQ-1, AQ-2, AQ-3, AQ-4, and corpus-wide AQ-7.** Every one is a small edit to a document that already exists. None is scientific redesign — which is exactly what **GO WITH CONDITIONS** meant.

---

*This document is versioned and non-retroactive. Amendments follow [[TAXONOMY_AND_NAMING_STANDARD]] §7 and the versioning discipline of [[FUTURE_GOVERNANCE_OUTLINES]] §3: a change to any proposition P1–P8 or rule R1–R20 forks a new version and does not retroactively alter claims validated under the prior version. Propositions are falsifiable as stated; a demonstration that one is false is a first-class institutional finding (R20).*
