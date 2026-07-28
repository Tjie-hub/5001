# Literature Research Standard

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see §0.3) · **Layer:** L1 — Scientific Foundation
**Owner:** Chief Research Scientist · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** **none.** Stage S1 (Literature Discovery) has no v3 realization and no existing standard; the Literature Card exists in [[RESEARCH_OBJECT_MODEL]] as a five-field stub. This document is greenfield.
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §7.3 (asymmetric constraint — the argument this entire document exists to serve), §4.2 (E0–E7; literature caps at E1), §6.4 (where inefficiency is *a priori* likely — and where it is not), §4.4 (R12, publication bias), §10 (LIM3)
**Governance:** [[RESEARCH_OS_MASTER_ROADMAP]] §2 (L1), [[TAXONOMY_AND_NAMING_STANDARD]] §4 (Stage S1), [[DECISION_LOG]] **D-020**

---

## 0. Authority and scope

### 0.1 What literature is for — the load-bearing claim

The obvious answer is wrong and expensive. Literature is **not** here to tell us what works, to justify a hypothesis, or to lend authority to a result.

> **Literature exists to supply mechanisms that were authored in ignorance of our data.**

That is the whole of it, and the argument is [[01_SCIENTIFIC_FOUNDATION]] §7.3. R18 requires an **ex-ante economic mechanism** for any inefficiency claim. §7.3 then shows the mechanism requirement does its work **only if the mechanism is authored blind to the result** — because a competent economist can supply a plausible story for any result including its opposite, so a retro-fitted mechanism is a *counterfeit*: indistinguishable from the genuine article by inspection.

This creates an acute institutional problem. **Where does a genuinely blind mechanism come from?** Our own researcher, working in our own data, cannot reliably author one — not through dishonesty, but because the ordering is unverifiable from the inside. Per §7.3 the ordering *"must be enforced by process rather than judged by review."*

**Published literature is the institution's primary supply of mechanisms that are blind by construction.** A mechanism proposed in a 2003 paper about a different market cannot have been retro-fitted to a result we obtained in 2026. **The blindness is guaranteed by chronology and geography, not by anyone's discipline** — which is exactly the property §7.3 says cannot be secured any other way.

Everything below follows. The search strategy searches for mechanisms. The extraction methodology extracts mechanisms. The quality assessment assesses whether a mechanism is *specified*, not whether a finding is *true*. **The finding is nearly irrelevant to us; the mechanism is the entire product.**

### 0.2 What literature is not — the E1 ceiling

Per [[EVIDENCE_MODEL]] §1, literature is class **K2**, and K2's ceiling is **E1 — statistical significance without a mechanism *for our market*.** Per Rule EV-1 the ceiling is **absolute and not aggregable**: a hundred papers remain E1.

This is not conservatism. A published finding about the US market in 1990–2010 is evidence about *the US market in 1990–2010*. It is a fact about a different (market, information, participant, constraint, cost) tuple — and per **P6**, efficiency is a property of that tuple, not of "markets." Transporting the finding transports nothing. Transporting the **mechanism** transports a testable conjecture, which is worth a great deal.

> **Rule LR-1 (justified by P6, EV-1):** A literature finding is **never** evidence for a claim about our market. It raises an entry in [[MARKET_INEFFICIENCY_TAXONOMY]] from **RM0 to RM1** and licenses registration. **It licenses nothing else.** In particular it does not license a prior, a weighting, a relaxed threshold, or a shorter test.

### 0.3 The §6.4 inversion — literature's most counter-intuitive consequence

[[01_SCIENTIFIC_FOUNDATION]] §6.4 states that deviation is *a priori* **least** likely where capital is abundant, data is standardized, and the constraint is absent — *"which is exactly where the most-studied effects live, and why replicating famous anomalies is a poor use of this institution's scarce resource (P4)."*

> **Rule LR-2 (justified by §6.4, P4):** **A large, high-quality literature on an effect is a reason for a *lower* prior that the effect survives here, not a higher one.** Heavy study means abundant attention and capital; abundant capital is the *absence* of a persistence barrier (**R17**); and absent a barrier the default presumption is that the effect does not exist.

The literature we want is therefore **not** the well-cited consensus. It is:

- the paper that specifies a **mechanism** well, whatever it concluded;
- the paper about a **constrained, illiquid, capital-scarce market** (§6.4);
- the paper about **market design** (D1/M6) — the strongest barrier class ([[ECONOMIC_MECHANISM_TAXONOMY]] §8.2) and the least-studied;
- the paper that **failed** to find an effect and said why (R12 — negative evidence is a first-class product);
- the paper that documents a **barrier** (D3), which per §6.3 is the scarce and informative half of any claim.

**A search that returns the field's greatest hits has failed.** It found where everyone has looked, which per R17 is where nothing is left.

### 0.4 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready, NOT FROZEN**; one open condition ([[DECISION_LOG]] **D-018/D-019**).

---

## 1. Search strategy

### 1.1 Search by mechanism, never by outcome

> **Rule LR-3 (justified by §7.3, R8):** Searches are specified over **mechanism space**, not outcome space. A search for *"what predicts returns in emerging markets"* is a search for outcomes and will return the most-searched, least-surviving effects (LR-2), pre-filtered by the publication process to be exactly the significant ones (§3.2). A search for *"how do inventory constraints on liquidity suppliers propagate to price under a price-limit regime"* is a search for a causal structure and returns mechanisms.

The distinction is R8 restated for the library: explanation flows downward from constraints; evidence flows upward from measurements. **A literature search runs downward.**

### 1.2 The search frame

Every search declares, before running:

| Element | Content |
|---|---|
| **Target class** | Which M-class or sub-class ([[ECONOMIC_MECHANISM_TAXONOMY]]) is being sourced |
| **Target domain** | Which of D1–D6 ([[01_SCIENTIFIC_FOUNDATION]] §3.5) owns the question |
| **Target field** | Which of the eight sub-class fields is missing — usually *causal chain* or *competing explanations* |
| **Transportability question** | What must be true of our market for this mechanism to operate here at all |
| **Exclusion commitment** | What would make a paper irrelevant — declared **before** reading (§2.2) |

> **Rule LR-4 (justified by R5, R7.5):** The exclusion commitment is declared **before** reading. Exclusions invented while reading are R7.4 — threshold migration applied to the library — and produce a review whose scope was determined by what it found. The failure is invisible afterward: a search that excluded inconvenient papers looks identical to one that never found them.

### 1.3 Search priority (from §6.4)

| Priority | Target | Why |
|---|---|---|
| **1** | **Market design / venue rules** (D1, M6) | Strongest barrier; least studied; **origination is published, not conjectural** |
| **2** | **Limits to arbitrage** (D3) | The persistence half — scarce, informative, decisive (§6.3) |
| **3** | **Emerging / constrained markets** | Capital-scarce, per §6.4 |
| **4** | **Microstructure** (D2) | Well-specified mechanisms; high F1 risk (fair compensation) |
| **5** | **Transaction cost & capacity** (D4) | Needed to kill claims at F4 cheaply |
| **6** | **Behavioral** (D5, M5) | **Deprioritized per LR-2** — most studied, weakest barrier ([[ECONOMIC_MECHANISM_TAXONOMY]] §8.2) |

**Priority 6 is deliberate and will feel wrong.** Behavioral finance is the largest, most accessible, most quotable literature in the field. Per **R17** and §8.2 it is also the one whose barrier — processing cost — erodes monotonically and fastest. Reading it first is how an institution spends its scarcest resource (**P4**: the credibility of a claim) on the conjectures least likely to survive.

### 1.4 Coverage and its limit

A search is **complete** when the mechanism's causal chain has no unspecified link and its rivals are enumerated — **not** when a source count is reached. Per **LIM3**, the multiplicity denominator is *estimable, not knowable*; the same applies to the literature. **Exhaustive coverage is not achievable and is not the goal.** Claiming it would be a claim about an unknowable denominator.

---

## 2. Inclusion and exclusion

### 2.1 Inclusion — any one suffices

| # | Include if the paper… |
|---|---|
| **IN1** | **Specifies a mechanism** — a causal chain from a constraint on a participant class to an observable (Rule M-2). **This is the primary criterion; a paper meeting only IN1 is worth more than one meeting all others** |
| **IN2** | **Documents a barrier** to arbitrage (D3) — the scarce half of R16 |
| **IN3** | **Describes market design** and its price consequences (D1/M6) |
| **IN4** | **Reports a failure** to find an expected effect, with an account of why (**R12**) |
| **IN5** | **Specifies a method** for inference under non-stationarity (D6) — method-about-claims, not a claim |
| **IN6** | **Contradicts** an existing Literature Card (§7 — contradiction is signal) |
| **IN7** | **Concerns a market structurally comparable** to ours: capital-scarce, constrained, illiquid (§6.4) |

### 2.2 Exclusion — any one suffices

| # | Exclude if the paper… | Basis |
|---|---|---|
| **EX1** | Reports an effect with **no mechanism** — a pattern with a name | **R18**, E1 ceiling |
| **EX2** | Authors its mechanism **after** its result (visible in structure: the "explanation" section follows the "findings" section and cites nothing prior) | **§7.3** — counterfeit mechanism, **U3** |
| **EX3** | Reports a mechanism **unfalsifiable as stated** — no observation would contradict it | **R14** |
| **EX4** | Depends on data at a fidelity we cannot obtain, **with no proxy path** | [[DATA_FEASIBILITY_STUDY]] — the binding scope constraint (**D-002**) |
| **EX5** | Is a **replication of a famous anomaly** with no new mechanism | **LR-2**, §6.4, P4 |
| **EX6** | Reports **profit** as its evidence | **R7.1**, U1 |
| **EX7** | Cannot be obtained in full text | Cannot assess what cannot be read; a Card from an abstract is a Card about an abstract |

> **Rule LR-5:** EX4 excludes on **fidelity**, never on effort or cost. A mechanism requiring L3 order-book data is excluded not because it is expensive but because per [[DATA_FEASIBILITY_STUDY]] we do not hold it and cannot test it — the paper would generate an unfalsifiable-in-practice conjecture. **If a proxy path exists, the paper is included and the proxy's fidelity limit binds the resulting claim (LIM1)** — the claim is then about the proxy unless the design shows otherwise.

> **Rule LR-6 (justified by §7.3):** **EX2 is the most important exclusion and the hardest to apply.** A retro-fitted mechanism is indistinguishable from a genuine one by inspecting its content — that is §7.3's central point, and it does not stop being true because the author is a professor. The only available tells are **structural**: does the mechanism appear before the result in the paper's own logic? Was it pre-registered? Does it cite prior theory, or only the result it explains? Does it predict anything the paper did not test? These are weak tells and they are all we have. **When in doubt, extract the mechanism and discard the finding** — which costs us nothing, because per LR-1 the finding was never evidence anyway.

---

## 3. Quality assessment

### 3.1 We assess the mechanism, not the finding

> **Rule LR-7 (justified by LR-1):** Quality grades **specification quality of the mechanism**, not credibility of the finding. A paper with a rigorously specified mechanism and a failed replication is **high quality for our purposes**. A paper with a robust, widely-replicated finding and a vague mechanism is **low quality for our purposes** — and per LR-2 its robustness is a reason for a *lower* prior that it survives here.

This inverts conventional appraisal, and the inversion is the point. Conventional appraisal asks *should I believe this result?* We never believe the result (LR-1). We ask: *can I extract from this a mechanism I could risk a claim on?*

| Grade | Criterion |
|---|---|
| **Q4 · Specified** | Causal chain complete from constraint to observable (Rule M-2); participant class named (R9); scope conditions stated; rivals enumerated (Rule M-3); **falsifiable as stated** |
| **Q3 · Substantial** | Chain complete; rivals thin or scope conditions implicit |
| **Q2 · Partial** | Mechanism identified but the chain has an unspecified link — **usable only as a search lead**, never as the source of a registration |
| **Q1 · Nominal** | Mechanism named but not specified — a label |
| **Q0 · Absent** | No mechanism → **EX1** |

### 3.2 The three appraisals that are not quality grades

Grade is one thing; these are three others, and they attach to the Card separately because each corrupts a *different* downstream calculation:

**(a) Publication-bias exposure.** The published record is a **selected sample**: significant results are published, null results are not. Per §4.4, suppressing negative evidence *"corrupts every future multiplicity calculation by hiding the denominator."* The literature is that corruption at field scale — **the denominator of every published anomaly is unknown and unknowable (LIM3)**. Every Card records this exposure. It is not a criticism of any paper; it is a property of the corpus every paper sits in.

**(b) Replication status.** Recorded factually. A failed replication does **not** lower Q (Rule LR-7) — the mechanism may be perfectly specified and simply not operative there. It is a fact about the finding, and we were never using the finding.

**(c) Transportability.** The explicit answer to: *what must be true of IDX for this mechanism to operate here?* Per **P6**, efficiency is a property of a *(market, information, participant, constraint, cost)* tuple. **A mechanism transports only if its tuple transports.** An M4.1 benchmark-replication mechanism requires benchmark-tracked capital to exist at material scale here — an empirical question about IDX, answerable before any test. **This field kills more candidate hypotheses than any other, at F1 cost: zero data, zero custody, zero multiplicity budget.** It is the single highest-leverage field on the Card.

---

## 4. Extraction methodology

### 4.1 Extract the mechanism; discard the finding

A Literature Card is **not a summary**. Summaries preserve findings, which we do not use, and lose mechanisms, which are the product.

| Extract | Do not extract |
|---|---|
| The **causal chain**: constraint → participant → behavior → flow → price → observable | The effect size |
| The **participant class** and its constraint (R9) | The t-statistic |
| The **barrier** the paper implies or states (D3) | The Sharpe ratio |
| The **scope conditions** under which the mechanism operates | The author's conclusion about profitability |
| The **rivals** the paper considered and how it excluded them | The abstract's confidence |
| The **falsification** the paper's own logic implies | Recommendations |
| The mechanism's **sub-class** ([[ECONOMIC_MECHANISM_TAXONOMY]]) | — |
| The **transportability condition** (§3.2c) | — |

> **Rule LR-8 (justified by R8, Rule M-2):** Extraction must produce a chain **beginning at a constraint**. If the paper's mechanism begins at an observable — *"stocks with characteristic X earn higher returns because of X-risk"* — the extraction has found a **relabeled correlation**, not a mechanism, and the paper is **EX1** regardless of its journal, citations, or the author's eminence.

### 4.2 Extraction is adversarial

> **Rule LR-9 (justified by R4, §2.2):** The extractor's task is to find the **weakest link in the causal chain**, not to represent the paper favorably. Per R4 the burden rests on the *proponent* of a claim; when a paper is proposed as a mechanism source, **the extractor is its proponent** and inherits that burden. A Card that reads as an endorsement has not been extracted; it has been transcribed.

Every Card states, mandatorily: **the one link most likely to fail in our market.** A Card without it is incomplete — because that link is where the hypothesis it spawns will die, and knowing it in advance is what makes the F1 kill available.

---

## 5. Bias identification

Recorded on every Card, because each corrupts a *different* downstream calculation. This is not diligence theatre; an unrecorded bias here becomes an unrecoverable error at validation.

| # | Bias | What it does to us |
|---|---|---|
| **B1** | **Publication bias** | The denominator of the published record is unknown → **any multiplicity correction using a published family is wrong in an unknown direction** (LIM3, §4.4) |
| **B2** | **Survivorship (dataset)** | The paper's universe excludes failures → its effect is partly a selection artifact (**R7.2**) |
| **B3** | **Backfill / index-inclusion** | Data added retrospectively → **F7 look-ahead in the source itself**, inherited silently by anyone who transports the design |
| **B4** | **Retro-fitted mechanism** | The mechanism was authored knowing the result → **the paper's central value to us is void** (§7.3, EX2) |
| **B5** | **Multiple testing within the paper** | Many specifications, one reported → the reported result's severity is unknowable (**R11**) |
| **B6** | **Period selection** | The sample was chosen → **F5 regime artifact** with a citation attached |
| **B7** | **Cost omission** | Gross returns → the effect may be **F4** and the paper cannot know |
| **B8** | **Market-structure obsolescence** | The venue's rules changed since publication → **for M6 mechanisms this is fatal** ([[ECONOMIC_MECHANISM_TAXONOMY]] §6: M6 decays as a step function on rule change), and it is the bias most often missed because papers do not announce that their substrate expired |
| **B9** | **Citation cascade** | A claim is widely cited *to a source that does not establish it* → apparent consensus with no independent support beneath it |

> **Rule LR-10 (justified by §4.4, LIM3):** **B1 is not a property of any paper; it is a property of the corpus.** Every Card carries it. Its consequence must be stated plainly rather than mitigated, because it cannot be mitigated: **the institution can never compute a correct multiplicity correction over a literature-derived family**, since the field's denominator is unknowable. **The only sound response is to treat literature as hypothesis material (LR-1) and to compute multiplicity only over *our own* declared families** — which we can count because we declare them (§5.2.6). This is the concrete reason the E1 ceiling exists and is not merely cautious.

---

## 6. Evidence synthesis

> **Rule LR-11 (justified by EV-1, LR-1):** Synthesis produces a **mechanism**, never a conclusion. Cards are synthesized into a **candidate sub-class** for [[ECONOMIC_MECHANISM_TAXONOMY]] or a **candidate entry** for [[MARKET_INEFFICIENCY_TAXONOMY]] at RM1. **Meta-analysis of findings is prohibited**: it aggregates E1 evidence about other markets into a number, and Rule EV-1 makes class ceilings **non-aggregable**. A meta-analytic effect size is E1 with a confidence interval — a category error dressed in rigor, and more dangerous than the raw finding precisely because it looks like more evidence.

Synthesis output:

| Output | Content |
|---|---|
| **Mechanism statement** | The causal chain, at Rule M-2 quality, sourced from ≥1 Q3+ Card |
| **Sub-class assignment** | The M-class sub-class it instantiates — or a **proposed new sub-class** (amends [[ECONOMIC_MECHANISM_TAXONOMY]], CRO approval) |
| **Barrier statement** | The persistence story, from §6.3's seven barriers. **If no Card supplies one, synthesis fails — Rule I-1 refuses the entry** |
| **Transportability argument** | What must be true of IDX (§3.2c) |
| **Weakest link** | Where it will most likely die (Rule LR-9) |
| **Rival mechanisms** | From the union of the Cards' rivals (Rule M-3) |
| **Falsification** | The one-sentence counterfactual (§5.1) |

**Synthesis failing is the common and correct case.** Most literature supplies origination and no barrier — per §6.3, *"origination stories are cheap: any pattern can be given one. Persistence stories are expensive, and their scarcity is what makes them informative."* A synthesis that fails at the barrier has killed a hypothesis at **F1**: no data, no custody, no multiplicity budget. Per §5.3 that is the institution operating **efficiently**, and per [[MARKET_INEFFICIENCY_TAXONOMY]] §5.2 it is the highest-value use of the taxonomy.

---

## 7. Contradiction handling

> **Rule LR-12 (justified by P3, R12):** Contradictory literature is **not a problem to resolve — it is the most informative state the library can be in.** Two papers finding opposite effects from the same mechanism have located a **scope condition**, and a scope condition is the most valuable object literature produces: it is a *conditionality authored blind to our data*, which per §7.3 is exactly what a pre-registered conditional hypothesis needs and what our own researchers cannot legitimately generate from our data.

Resolution order — **stop at the first that applies**:

| # | Resolution | Meaning |
|---|---|---|
| **1** | **Scope difference** | Both true; the mechanism is conditional. **Record the condition — this is the best available outcome** and it converts a contradiction into a sharper hypothesis |
| **2** | **Market-structure difference** | Both true; the mechanism depends on venue design (D1). **A transportability fact of the first order** |
| **3** | **Period difference** | Both true; the mechanism **decayed** (P7, F9). Records a half-life datum — the D3 question, answered for free |
| **4** | **Method difference** | One is better-powered or better-specified. Prefer on **method quality**, never on result |
| **5** | **Bias difference** | One suffers B1–B9. **Record the bias; do not average** |
| **6** | **Genuine unresolved conflict** | **Record it. Do not resolve it.** |

> **Rule LR-13 (justified by ADR-L1-008, §4.3):** **Never average conflicting findings.** Averaging destroys the scope condition — the only thing of value — and manufactures a number that no paper reported and no market produced. **Recording an unresolved conflict is a legitimate terminal state**, precisely as [[01_SCIENTIFIC_FOUNDATION]] §15 records L2 inconsistencies rather than resolving them (ADR-L1-008). **The corpus's own governance models the behavior this rule requires.**

---

## 8. Citation rules

| # | Rule | Basis |
|---|---|---|
| **CR1** | Cite the **source that establishes** the claim, never a paper that cites it | **B9** — citation cascade |
| **CR2** | Cite a **specific mechanism**, never a paper wholesale. "See Smith (2003)" is not a citation; "Smith (2003) §4 specifies the inventory chain as…" is | Rule LR-8 |
| **CR3** | A citation supporting a **finding** is prohibited in any institutional claim. Citations support **mechanisms** | **LR-1**, EV-1 |
| **CR4** | Every citation resolves to a **Literature Card**, never directly to a paper. **The Card is the institutional object; the paper is its source** | Provenance (§8.2) |
| **CR5** | Citing a Card **inherits its recorded biases** into the citing claim. Biases do not vanish on citation | **B1–B9** |
| **CR6** | A citation may never appear as **authority**. "This is well-established in the literature" is prohibited: it is an appeal to consensus, and per **LR-2** consensus is a reason for a *lower* prior | §6.4, R7.6 |

> **Rule LR-14 (justified by R4, CR6):** **Literature never lowers a bar.** Not a threshold, not a sample requirement, not a tier, not a timebox. Per **R4** the burden rests permanently on the proponent and never transfers. *"This effect is well-documented, so we need less evidence here"* is R4 inverted and R7.5 approaching — it is the exact sentence that precedes a relaxed test, and it should be treated as a red flag rather than a rationale.

---

## 9. Update policy

Cards are **append-only in substance** (**R12** — a suppressed failure hides the denominator).

| Event | Action |
|---|---|
| **New paper on a carded mechanism** | New Card; link. **Never edit the existing Card** — its content is a fact about what was known when |
| **Replication failure** | Record on the Card. **Q unchanged** (Rule LR-7) |
| **Retraction** | Card marked RETRACTED, **retained**. Any claim sourcing it re-derives at the tier its surviving sources support (**DG8**) |
| **Market-structure change** | **B8 triggered.** Every Card whose mechanism depends on the changed rule is flagged. For **M6 mechanisms this is a decay event (DG2)**, not a caveat — the generating constraint was removed, and per [[EVIDENCE_MODEL]] §6.2 it is a retirement, not a failure |
| **Contradiction found** | §7; **never** resolved by editing either Card |
| **Card superseded** | New Card supersedes; **old retained** — the reasoning that led to a dead conjecture is itself institutional knowledge |

> **Rule LR-15 (justified by R12, §4.4):** **A Card is never deleted.** The library is a record of *what the institution believed and why*, not of what is currently true. Deleting a Card destroys the institution's ability to reconstruct why a dead hypothesis once looked alive — which per §5.3 is the F1–F9 distribution's raw material and the highest-value diagnostic the institution has about *itself*.

### 9.1 Review cadence

| Trigger | Scope |
|---|---|
| **Program initiation** | Full search over the Program's target mechanisms (§1.2) |
| **Program review gate** | Delta search since last ([[RESEARCH_PROGRAM_STANDARD]] §5) |
| **Market-structure change (D1)** | **Immediate B8 sweep** — highest-priority trigger; M6 mechanisms may have died |
| **Contradiction** | Immediate; §7 |
| **Calendar** | **None.** A calendar-triggered review is activity, not research (**P4**) |

**The absence of a calendar trigger is deliberate.** Per **P4**, *"if the proposed rule does not measurably reduce the probability that the institution believes something false, it fails P4"* — and a quarterly literature review, absent an event, does not. Reviews are triggered by **events that could change what we believe**, which is the only thing a review is for.

---

## 10. Relationship to the Literature Card object

[[RESEARCH_OBJECT_MODEL]] defines the Literature Card with five fields: `card_id`, `source`, `identified_mechanisms`, `empirical_claims`, `limitations`. **That is a stub**, and this document is its scientific specification — how a Card is sourced, appraised, extracted, biased, synthesized, cited, and updated.

> **Gap recorded (for §11 and the gap analysis).** The stub's field set is **insufficient** for this standard. It has no field for: quality grade (§3.1), the nine biases (§5), the transportability condition (§3.2c) — this document's highest-leverage field — the weakest link (Rule LR-9), replication status, or the sub-class assignment. Per **D-020** this document **does not amend** [[RESEARCH_OBJECT_MODEL]]. The extension is specified in [[RESEARCH_OBJECT_SCHEMA]] §3.1 and the gap is recorded in [[KNOWLEDGE_CORPUS_DELIVERY]] §5.

---

## 11. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §0.1 (literature supplies blind mechanisms) | [[01_SCIENTIFIC_FOUNDATION]] **§7.3** (asymmetric constraint) | §7.3's argument |
| LR-1 (E1 ceiling) | §4.2 (E0–E7), [[EVIDENCE_MODEL]] EV-1 (K2 class) | The tier scale |
| LR-2 (consensus lowers the prior) | **§6.4**, R17, P4 | §6.4 |
| IN/EX criteria | R18, R14, [[DATA_FEASIBILITY_STUDY]] (D-002) | The feasibility matrix |
| Q0–Q4 | Rule M-2, R9 ([[ECONOMIC_MECHANISM_TAXONOMY]]) | The sub-class schema |
| B1–B9 | **§4.4** (publication bias), LIM3, R11 | §4.4 |
| §7 contradiction handling | ADR-L1-008 (record, don't resolve), P7 | §15 |
| CR1–CR6, LR-14 | R4 (burden never transfers), R7.6 | R7 |

**Downstream:** [[MARKET_INEFFICIENCY_TAXONOMY]] (RM0→RM1) · [[ECONOMIC_MECHANISM_TAXONOMY]] (candidate sub-classes) · [[EVIDENCE_MODEL]] (K2 class) · [[HYPOTHESIS_LIFECYCLE]] (a registration cites a Card) · [[RESEARCH_OBJECT_SCHEMA]] §3.1 (the extended Card) · [[RESEARCH_PROGRAM_STANDARD]] (Program initiation requires a search).
