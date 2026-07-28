# Phase A — Architecture Review

**Reviewer role:** Chief Research Architect / Scientific Program Director
**Date:** 2026-07-15 · **Subject:** Institutional Research OS — Master Research Plan v1.0 (Draft) + 7 architecture documents
**Verdict:** **NO-GO for Phase B** (conditional — 6 blocking items, all resolvable). Phase A is conceptually rich but not yet *scientifically complete* and not yet *feasibility-grounded*.

---

## 1. Executive Review

The Phase A corpus is intellectually serious and, in isolation, above the bar for an institutional research charter. The Research Object Model, Validation Framework, and 10-stage Pipeline are coherent and show real understanding of anti-overfitting discipline (FDR, DSR, PBO/CSCV, pre-registration, Failure Library). If the question were "is this a credible *vision*?", the answer is yes.

But a master plan is not judged as prose — it is judged on whether the next phase can be built against it without discovering that the foundation was fiction. On that test, three structural problems block Phase B:

1. **Feasibility gap (critical).** The entire declared scope — L3 limit-order-book, nanosecond resolution, queue dynamics, auction imbalance messages, depth-of-book updates — presupposes data the platform does not have and, for IDX equities, realistically cannot obtain at that fidelity. The roadmap's *first* research program (LOB/OFI) requires exactly the data least likely to be procurable. Phases B–H would be architected against datasets that may never exist. **No Phase A freeze is defensible until a Data Feasibility Study says, per dataset: procurable Y/N, vendor, cost, history depth, latency, licensing.**

2. **Taxonomy collision.** The word "Phase" is overloaded across three incompatible axes — architecture *layers* (A–H), research *programs* (I/II/III), and pipeline *stages* (1–10). "Phase A" simultaneously names "the scientific foundation layer" and "the conceptual research we finished." This ambiguity will propagate into every downstream document and every status report.

3. **Silent fork of the canonical plan.** This repository already contains a **ratified, frozen** `docs/RESEARCH_MASTER_PLAN.md` (v3, frozen 2026-07-14) with its own Phases A–H (gatekeeper, regime engine, knowledge base, forward-testing, edge registry — much of it *already built and tested*). The Research OS plan is written greenfield and never references it. Two master plans with clashing phase schemes now live in one repo. Governance requires an explicit relationship statement before either advances.

Everything else in this review is secondary to those three. They are not reasons to abandon the work — they are the reasons Phase A is not yet *done*.

---

## 2. Strengths

- **Anti-overfitting spine is institutional-grade.** Pre-registration, ex-ante thresholds, FDR/DSR/PBO-CSCV, mandatory Failure Library, adversarial Validation Reviewer, and a Discovery→Confirmation→Accepted three-tier custody model. This is the hard part and it is largely right.
- **Object-oriented research ontology.** Treating hypotheses, mechanisms, features, experiments, and failures as immutable, versioned, lineage-linked objects is the correct institutional abstraction and prevents "tribal knowledge."
- **Economic-mechanism-first stance.** The insistence that statistical significance is *invalid without an economic mechanism* (Validation Framework §3) is exactly the discipline that separates research from data-mining.
- **Feature Computation Graph as a typed, immutable, versioned DAG** with bit-identical reproducibility requirements — the right model for feature lineage.
- **Negative-result preservation** (Failure Library) with structured falsification reasons — rare, and correct.
- **Role separation** with an independent adversarial reviewer and OOS-access prohibition during formulation.

## 3. Weaknesses

| # | Weakness | Severity | Review item |
|---|---|---|---|
| W1 | Scope presupposes unavailable data (L3/tick/auction-message fidelity); no feasibility gate | **Critical** | 1, 6 |
| W2 | "Phase" overloaded across layers / programs / stages | **Critical** | 2, 8 |
| W3 | Not reconciled with the existing ratified `RESEARCH_MASTER_PLAN.md` v3 | **Critical** | 4, 6 |
| W4 | Phase A conflates *scientific foundation* (literature/mechanisms) with *OS architecture* (object model, pipeline, validation) — the 7 docs are mostly Phase **B** content mislabeled as Phase A support | High | 1, 3, 4 |
| W5 | The single hardest problem — **defining the multiple-testing family across time and researchers** — is glossed as "across the hypothesis space" with no family definition | High | 9 |
| W6 | No **power / minimum-detectable-effect** analysis, yet thresholds are pre-registered — you cannot set thresholds without power | High | 9 |
| W7 | Object model gaps: no first-class Regime, Cost-Model, Reviewer-Signoff, Decay-Monitor, or Lineage-Edge objects; Hypothesis lacks an immutable pre-registration hash+timestamp | High | 6 |
| W8 | Missing foundational domains: market *design/mechanism specifics* (IDX tick/lot/auction/ARA-ARB), Limits-to-Arbitrage (why inefficiency persists), Transaction-Cost & Market-Impact theory as its own domain, Non-stationarity/DGP theory, Statistical-inference foundations, Research ethics/regulatory boundary | High | 1, 5 |
| W9 | OOS-custody is a *policy* ("prohibited from accessing"), not a *mechanism* — no enforcement described | Med | 9 |
| W10 | Success criteria (§13) are process gates, not falsifiable scientific-completeness criteria; no worked end-to-end example proving the objects compose | Med | 5, 10 |
| W11 | Folder structure organizes by transient Phase, coupling the repo to the roadmap | Med | 8 |
| W12 | Decay/half-life is asserted as measurable throughout but has no object schema, no method, and no data plan | Med | 6, 9 |

## 4. Missing Components (documents that must exist before Phase B)

*Review item 7 — each with Name / Purpose / Priority / Dependency / Size.*

| Document | Purpose | Priority | Depends on | Est. size |
|---|---|---|---|---|
| **DATA_FEASIBILITY_STUDY.md** | Per dataset (L3 LOB, depth updates, trade prints, auction messages, broker flow, EOD OHLCV): procurable? vendor, cost, history, latency, licensing, IDX availability. **This decides the real scope.** | **P0 — blocker** | — | 6–10 pp |
| **SCOPE_AND_TAXONOMY.md** | Rename Layers / Programs / Stages; define "Phase" once; declare the Research OS ↔ existing `RESEARCH_MASTER_PLAN.md` v3 relationship (superset? parallel? rename?) | **P0 — blocker** | Feasibility | 3–4 pp |
| **MARKET_DESIGN_IDX.md** | Foundational domain: IDX tick-size regime, lot sizes, ARA/ARB auto-rejection bands, auction mechanics, short-sale constraints, settlement — the mechanism substrate for any inefficiency claim | **P0** | — | 4–6 pp |
| **MULTIPLE_TESTING_FAMILY_POLICY.md** | Formal definition of the testing family across time/researchers/features; how the denominator is fixed; anti-family-hacking rules | **P0** | Object model | 3–5 pp |
| **STATISTICAL_METHODOLOGY.md** | Power/MDE analysis, threshold-derivation procedure, PBO/CSCV parameters, stationarity/structural-break tests, reproducibility-CI definition | P1 | Family policy | 5–8 pp |
| **COST_AND_CAPACITY_MODEL.md** | Institutional friction + market-impact model as a versioned object; capacity/decay of inefficiency vs. size | P1 | Feasibility, Market design | 4–6 pp |
| **DATA_ONTOLOGY.md** (Phase-C precursor stub) | Formal Dataset Object taxonomy grounded in *feasible* data only | P1 | Feasibility | 3–5 pp |
| **WORKED_EXAMPLE_END_TO_END.md** | One IDX-attainable mechanism instantiated through *every* object and *every* pipeline stage, on paper — proves the model composes | P1 | Object model, Pipeline | 4–6 pp |
| **GOVERNANCE_AND_ROLES.md** | Promote roles/gates from the Operating Model into a standalone charter; add OOS-custody *enforcement* mechanism and reviewer sign-off artifact | P2 | Operating model | 3–4 pp |
| **RESEARCH_ETHICS_REGULATORY.md** | Boundaries: what data use / research is legally permissible (esp. auction/flow data) | P2 | — | 2–3 pp |
| **DECAY_MONITORING_SPEC.md** | Schema + method for the referenced `decay_monitor_id`; how ongoing validity is tracked | P2 | Object model | 2–3 pp |
| **GLOSSARY.md** | Single controlled vocabulary (mechanism, feature, hypothesis, regime, family…) | P2 | — | 2 pp |

## 5. Recommended Revisions

**R1 — Insert a Phase A.0 "Feasibility & Reconciliation" gate (blocker).** Nothing freezes until (a) the Data Feasibility Study exists, and (b) the Research OS ↔ v3 relationship is written. If the feasible data is daily/intraday OHLCV + broker flow + EOD depth snapshots (the project's actual holdings), **the scientific scope must be rewritten to microstructure-*proxy* research** (VPIN-style toxicity, Amihud illiquidity, close-auction imbalance from EOD data, broker-flow adverse selection) — honest and still institutional — rather than L3/nanosecond research that cannot be executed.

**R2 — Split Phase A into A (Science) and B (Architecture) cleanly (items 3, 4).** Phase A = charter, domains, literature, mechanism taxonomy, feasibility. The Object Model / Operating Model / Validation Framework / Pipeline / FCG / Failure Library are **Phase B (Research Architecture)** artifacts — relabel them. Today they are strong Phase B docs masquerading as Phase A support, which is why "Phase A" feels both done and undefined.

**R3 — Fix the taxonomy (item 2).** Layers A–H → **Architecture Layers**. Roadmap I/II/III → **Research Programs**. Pipeline 1–10 → **Pipeline Stages**. Reserve "Phase" for one axis only (recommend the Layers).

**R4 — Reorganize domains (items 2, 3, 5).** Keep the 6, but: **merge** "Market Microstructure & Inefficiency" (D1) with "Market Mechanism & Price Formation" (D2) — they overlap heavily — and **split out** two new foundational domains that are currently missing: *Market Design (venue-specific)* and *Limits to Arbitrage / persistence theory*. Add *Transaction-Cost & Market-Impact theory* as a domain rather than burying it in validation. Reorder so mechanism-substrate domains (design, microstructure, information, liquidity) precede phenomenon domains (behavioral, asset-pricing).

**R5 — Close the object-model gaps (item 6).** Add first-class **Regime**, **Cost-Model**, **Reviewer-Signoff**, **Decay-Monitor**, and **Lineage-Edge** objects. Add to Hypothesis: `preregistration_hash`, `preregistered_at`, and an immutable-once-REGISTERED constraint. (The existing repo already implements receipt-bound status transitions and `hypothesis_links` — reuse that design rather than reinventing.)

**R6 — Harden validation into a workflow, not a checklist (item 9).** Add ex-ante **power/MDE**, a concrete **multiple-testing family** definition, **stationarity/structural-break** tests, a **reproducibility-CI** step, and an **enforced** OOS custody mechanism (not a policy sentence).

**R7 — Permanent vs. supporting documents (item 4).**
- **Permanent repository documents:** Charter, Research Object Model, Research Operating Model / Governance, Validation Framework, Feature Computation Graph, Failure Library Schema, Data Ontology, Multiple-Testing Family Policy, Glossary. (These define the institution.)
- **Supporting references (living, versioned but not canonical law):** Microstructure Research Roadmap, the Research Pipeline narrative (canonical logic lives in the Operating Model), Literature Cards, the Worked Example, per-program design notes.

**R8 — Add the worked end-to-end example (item 10)** before freeze — it is the cheapest possible de-risking of Phases C–H.

## 6. Updated Phase A Master Plan (structure)

```
ARCHITECTURE LAYERS (was "Phases A–H")
  L0  Charter & Scope         ← scope + feasibility + reconciliation (NEW blocker)
  L1  Scientific Foundation   ← domains, literature, mechanism taxonomy   [Phase A proper]
  L2  Research Architecture   ← Object Model, Operating Model, FCG        [was mislabeled A]
  L3  Data Ontology
  L4  Research Infrastructure
  L5  Feature Computation
  L6  Hypothesis Engine
  L7  Validation Framework
  L8  Knowledge Repository

RESEARCH PROGRAMS (was Roadmap "Phases I–III") — scoped to FEASIBLE data
  P1  Order-Flow / Imbalance (proxy-based if no L3)
  P2  Auction / Close dislocation (EOD-attainable)
  P3  Liquidity stress / toxicity (VPIN, Amihud, spread dynamics)

PIPELINE STAGES 1–10 (unchanged, but gated on L0 feasibility)
```

Phase A (L0 + L1) scope, restated: **charter, feasibility verdict, reconciliation with v3, the domain set (revised), a mechanism taxonomy with causal DAGs, a literature-card corpus, and one fully-worked hypothesis.** Everything else moves to L2+.

## 7. Final Folder Structure

Organize by **stable concern**, not by transient phase:

```
/docs/research_os/
  charter/            CHARTER.md, SCOPE_AND_TAXONOMY.md, GLOSSARY.md,
                      RECONCILIATION_WITH_V3.md, RESEARCH_ETHICS_REGULATORY.md
  foundation/         domains/*.md, MARKET_DESIGN_IDX.md, LIMITS_TO_ARBITRAGE.md,
                      literature_cards/*.md, mechanism_taxonomy.md
  data/               DATA_FEASIBILITY_STUDY.md, DATA_ONTOLOGY.md
  ontology/           RESEARCH_OBJECT_MODEL.md, schemas/*.json
  methods/            STATISTICAL_METHODOLOGY.md, VALIDATION_FRAMEWORK.md,
                      MULTIPLE_TESTING_FAMILY_POLICY.md, COST_AND_CAPACITY_MODEL.md
  operating_model/    RESEARCH_OPERATING_MODEL.md, GOVERNANCE_AND_ROLES.md, PIPELINE.md
  features/           FEATURE_COMPUTATION_GRAPH.md
  programs/           p1_order_flow/, p2_auction/, p3_liquidity/   (was Roadmap I/II/III)
  knowledge/          ACCEPTED_KNOWLEDGE/, FAILURE_LIBRARY_SCHEMA.md, DECAY_MONITORING_SPEC.md
  examples/           WORKED_EXAMPLE_END_TO_END.md
  reviews/            PHASE_A_ARCHITECTURE_REVIEW.md (this doc)
```

Phase/layer status is tracked in a single `ROADMAP.md`, not encoded in folder names.

## 8. Phase A Completion Checklist (Exit Criteria)

*Review item 10 — Phase A cannot be declared frozen until every box is true.*

- [ ] **Data Feasibility Study** complete; every in-scope dataset marked procurable/not, with vendor+cost+history+latency. **(blocker)**
- [ ] **Scope rewritten** to feasible data; any L3/tick/auction claim either backed by a procurement path or removed. **(blocker)**
- [ ] **Reconciliation with `RESEARCH_MASTER_PLAN.md` v3** written and signed — relationship is explicit (superset / parallel / rename / replace). **(blocker)**
- [ ] **Taxonomy fixed** — Layers / Programs / Stages disambiguated repo-wide. **(blocker)**
- [ ] **Domain set revised** — merges/splits applied; Market Design, Limits-to-Arbitrage, Cost/Impact added; each domain has a one-paragraph purpose with **no overlap** (item 5). **(blocker)**
- [ ] **Mechanism taxonomy** exists with causal DAGs for ≥1 mechanism per in-scope program.
- [ ] **Literature-card corpus** — a minimum N cards per retained domain (recommend ≥5), each with reproducible empirical claims.
- [ ] **Multiple-Testing Family Policy** written — the family denominator is formally defined.
- [ ] **One worked end-to-end example** instantiates every object and every pipeline stage on paper. **(blocker for de-risking B)**
- [ ] **Permanent-vs-supporting** classification applied; permanent docs frozen with version headers.
- [ ] **Folder structure** migrated to the concern-based layout.
- [ ] Independent **adversarial review** (the Validation Reviewer role) signs the checklist — not the author.

## 9. Go / No-Go Recommendation

**NO-GO for Phase B.**

The work is strong enough that this is a *conditional* no-go, not a rejection. Phase A is failing on **completeness and grounding**, not on quality of thought. The gate is blocked by six items, in priority order:

1. Data Feasibility Study (decides whether the scope is even executable).
2. Scope rewrite to feasible data.
3. Reconciliation with the existing ratified v3 plan.
4. Taxonomy disambiguation (Layers/Programs/Stages).
5. Domain-set revision (merges/splits + the missing foundational domains).
6. One worked end-to-end example.

Clear those six and Phase A is genuinely complete and Phase B can begin against a foundation that will not dissolve on contact with data. Until then, freezing Phase A would ratify a scope the platform cannot execute and a plan that silently contradicts the one frozen in this repo yesterday.

**Single highest-leverage next action:** write `DATA_FEASIBILITY_STUDY.md`. Every other decision — scope, domains, programs, object model — is downstream of what data actually exists.
```
