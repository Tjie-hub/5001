# Taxonomy & Naming Standard

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Authority:** The controlled vocabulary of the Research OS. Every other document MUST use these terms with exactly these meanings. The word **"Phase" is retired** from structural use (see §2).

---

## 1. The problem

The draft overloaded "Phase" across at least five incompatible axes — architecture layers, research programs, pipeline stages, validation gates, and lifecycle states. "Phase A" meant both "the foundation architecture layer" and "the conceptual research we finished." This standard assigns one word to one axis.

## 2. The six structural axes — one term each

| Axis | **Canonical term** | Numbering | Meaning | Example |
|---|---|---|---|---|
| Architecture strata of the OS | **Layer** | L0–L8 | *What the system is made of.* Stable, rarely changes. | L1 Scientific Foundation |
| A research track / body of work | **Program** | P0, P1, P2… | *What we are researching.* Scoped by [[DATA_FEASIBILITY_STUDY]]. | P1 Order-Flow Imbalance |
| Steps in the research pipeline | **Stage** | S1–S10 | *How one hypothesis moves* literature→knowledge. | S7 Statistical Validation |
| Institutional approval checkpoints | **Gate** | G1–G4 | *Who must approve to proceed.* | G3 Statistical Validation gate |
| Runtime steps of an experiment run | **Step** | (unnumbered) | *Execution mechanics* inside Stage S6. | seed-logging step |
| State of a research object | **Lifecycle State** | (named) | *Status of an object,* e.g. a Hypothesis. | REGISTERED, VALIDATED |

**Rule:** "Phase" may appear only in the proper noun `RESEARCH_MASTER_PLAN.md` (the v3 plan predates this standard and is frozen; see [[RESEARCH_OS_RECONCILIATION]]). It is never used for OS structure.

## 3. Layers (L0–L8) — canonical list

| Layer | Name | Owns |
|---|---|---|
| **L0** | Governance & Scope | This standard, feasibility, reconciliation, roles, ethics |
| **L1** | Scientific Foundation | Domains, literature cards, mechanism taxonomy |
| **L2** | Research Architecture | Research Object Model, Operating Model, FCG (the canonical 7 docs) |
| **L3** | Data Ontology | Dataset objects grounded in feasible data |
| **L4** | Research Infrastructure | Storage, compute, metadata, versioning |
| **L5** | Feature Computation | FCG realization |
| **L6** | Hypothesis Engine | Hypothesis registration & management |
| **L7** | Validation Framework | Statistical/market/scientific validation |
| **L8** | Knowledge Repository | Accepted knowledge + failure library + decay monitoring |

> **L0, L1, L2 together constitute "Phase A" in the old scheme** — the Scientific Foundation *plus* the architecture that supports it. Per owner decision, the Research OS architecture stays *within* Phase A (as L2), not pushed to Phase B. The distinction L0/L1/L2 makes responsibilities explicit without moving the work.

## 4. Stages (S1–S10) — the research pipeline

S1 Literature Discovery · S2 Mechanism Identification · S3 Hypothesis Registration · S4 Data Preparation · S5 Feature Construction · S6 Experiment Execution · S7 Statistical Validation · S8 Robustness Testing · S9 Peer Review · S10 Knowledge Promotion.
*(Unchanged from the canonical Research Pipeline doc — only the label "Stage" is now fixed.)*

## 5. Gates (G1–G4) — approval checkpoints

G1 Hypothesis Registration · G2 Code Review · G3 Statistical Validation · G4 Peer Defense.
*(From the Research Operating Model. Gates guard transitions between Stages; they are not Stages themselves.)*

## 6. Lifecycle States — per object

| Object | Allowed states |
|---|---|
| Hypothesis | REGISTERED → IN_TESTING → (VALIDATED \| FAILED) |
| Experiment | DRAFT → EXECUTED → REVIEWED |
| Validation Report | DRAFT → FINALIZED |
| Knowledge Object | ACCEPTED → (MONITORED → DECAYED \| RETIRED) |

State transitions that touch capital-facing status inherit v3's **receipt-binding** rule (no transition without an evidence receipt).

## 7. Naming conventions (files & objects)
- **Documents:** `UPPER_SNAKE_CASE.md`, one concept per file, version header mandatory.
- **Layers:** `L<n>_<Name>` in prose; folders are concern-named, never `L1/` (see [[MIGRATION_PLAN]]).
- **Programs:** `P<n>_<slug>` → folder `research_programs/p<n>_<slug>/`.
- **Objects:** `snake_case` schema fields; object types `PascalCase` in prose (Hypothesis, CostModel).
- **Cross-references:** `[[DOCUMENT_NAME]]` wikilinks.

## 8. Deprecated terms — do not use
| Deprecated | Use instead |
|---|---|
| "Phase" (for OS structure) | Layer / Program / Stage as appropriate |
| "step" (for pipeline) | Stage |
| "module/section" (for architecture) | Layer |
| "roadmap phase" | Program (scope) or Layer (architecture) |
