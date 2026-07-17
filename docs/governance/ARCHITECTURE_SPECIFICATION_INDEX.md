# Architecture Specification Index (ASI)

**Subtitle:** Institutional Research Operating System — Master Index of the Architecture Corpus
**Layer:** L0 — Governance & Scope (documentation & governance artifact)
**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see [[PHASE_A_FREEZE_CERTIFICATE]]) · **Date:** 2026-07-16
**Owner:** Chief Architecture Librarian / Architecture Governance Officer
**Supersedes:** — (initial version)

---

## 0. About this document

This is the **master index** of the Institutional Research OS architecture corpus (L0–L5). It is a **governance and documentation artifact only**.

- It introduces **zero new architecture**. Every statement is traceable to an existing corpus document.
- It does **not** redefine any concept, redistribute any responsibility, or merge any layers.
- Where inconsistencies were found during indexing, they are **recorded in §11 (Review Notes)** — never silently resolved. Resolution authority stays with the respective document owners.

**Authoritative sources indexed:**

| Medium | Contents |
|---|---|
| Repository markdown (`docs/governance/`, `docs/Phase_A_Scientific_Foundation/`, `docs/research_os/`, `docs/roadmap/`) | L0, L1, L2 and all governance records (decision log, certificates, reviews) |
| `docs/L3 Data Ontology Specification.pdf` (transcript export, created 2026-07-16 13:35 WIB) | L3 Data Ontology Specification, L4 Runtime Architecture Specification, L4.5 Execution Semantics Specification (**withdrawn**, §2.7), L5 Reference Architecture Specification (draft **and** refined final) |

---

## 1. Corpus Overview

**Purpose.** The corpus specifies an Institutional Research Operating System for market-inefficiency research: a scientifically governed pipeline that takes hypotheses from literature discovery through custody-controlled validation to Accepted Knowledge or the Failure Library, with complete lineage, deterministic reproducibility, and governance gates that cannot be bypassed.

**Scope.** Architecture only, through the logical level. Layer L6 (Technology Profiles) and physical implementation are explicitly out of corpus scope and deferred (per the owner decision recorded in the L3–L5 transcript: "L6 Technology Profiles ← Implementation" follows L5).

**Audience.** Research architects, systems architects, governance officers, validation reviewers, and any researcher onboarding into the institution ([[RESEARCH_PROTOCOL]] is the researcher's procedural entry point; this ASI is the architect's navigational entry point).

**Layer hierarchy.**

| Layer | Name (as indexed) | Realized as |
|---|---|---|
| L0 | Governance & Scope *(the commissioning brief calls this "Vision" — see RN-1)* | 6+ governance docs + governance records in `roadmap/` |
| L1 | Scientific Foundation | [[01_SCIENTIFIC_FOUNDATION]] + 4 L1-layer instance/standard docs |
| L2 | Research Architecture | 15 canonical docs in `research_os/` |
| L3 | Data Ontology | "L3 Data Ontology Specification" (PDF only — see RN-2) |
| L4 | Runtime Architecture | "L4 Runtime Architecture Specification" (PDF only — see RN-2) |
| L5 | Reference Architecture | "L5 Reference Architecture Specification", refined version (PDF only — see RN-2, RN-5) |
| L6 | Technology Profiles | **Not authored — deliberately deferred.** Not a gap. |

**Governance status.** Phase A (L0+L1+L2) is governed by [[DECISION_LOG]] D-001…D-024, certified **GO WITH CONDITIONS** ([[PHASE_A_FREEZE_CERTIFICATE]] v2.1; [[PHASE_A_EXIT_GATE_DECISION]] D-024). L3–L5 have **no decision-log entries and no governance records** (RN-3).

**Freeze status.** **Nothing in the corpus is frozen.** Phase A is certified-ready but NOT FROZEN — one blocking item (**G-8**: independent adversarial sign-off; the author cannot self-certify per L1 LIM6, D-019). **G-9** (Dataset Custody mechanism) blocks the Research OS v1.0 freeze but is not a Phase A exit gate (D-024 §2 Correction A). L3–L5 are unreviewed and unratified (§8). See Appendix B.

---

## 2. Architecture Catalog

### 2.1 L0 — Governance & Scope

| Field | Value |
|---|---|
| **Layer** | L0 |
| **Document set** | [[DATA_FEASIBILITY_STUDY]] v1.0 · [[TAXONOMY_AND_NAMING_STANDARD]] v1.0 · [[RESEARCH_OS_RECONCILIATION]] v1.0 · [[RESEARCH_PROGRAM_STANDARD]] v1.0 · [[RESEARCH_PROGRAM_PLAYBOOK]] v1.0 · [[FUTURE_GOVERNANCE_OUTLINES]] v0.1 (outlines, not canonical) · governance records: [[RESEARCH_OS_MASTER_ROADMAP]], [[DECISION_LOG]], [[PHASE_A_FREEZE_CHECKLIST]], [[PHASE_A_FREEZE_CERTIFICATE]], [[PHASE_A_EXIT_GATE_DECISION]] (D-024), review records (§8) |
| **Purpose** | Scope constraint, naming law, program governance, decision records, phase-gate certification |
| **Primary responsibility** | What the institution may research (Data Capability Matrix, D-002), what things are called (D-003, taxonomy), how decisions are recorded and gates are certified |
| **Scope** | Governance and scope only; no science, no architecture, no ontology, no runtime |
| **Inputs** | Owner decisions; data reality (feasibility study); review findings |
| **Outputs** | Binding scope constraint; naming standard; decision register D-001…D-024; certificates |
| **Dependencies** | None (root layer) |
| **Downstream dependents** | L1–L5 (all layers operate inside L0's scope constraint and naming law) |
| **Owner** | Chief Research Architect / Chief Research Officer (per doc headers) |
| **Status** | Canonical (candidate where marked — inherits unsigned L1) |
| **Version** | Per document (all 1.0 except FUTURE_GOVERNANCE_OUTLINES 0.1) |
| **Freeze status** | NOT frozen — inside the Phase A gate (G-8 open) |
| **Normative references** | [[DECISION_LOG]], [[TAXONOMY_AND_NAMING_STANDARD]], [[DATA_FEASIBILITY_STUDY]] |
| **Informative references** | [[RESEARCH_OS_MASTER_ROADMAP]] diagrams, [[FUTURE_GOVERNANCE_OUTLINES]] |

### 2.2 L1 — Scientific Foundation

| Field | Value |
|---|---|
| **Layer** | L1 |
| **Document set** | [[01_SCIENTIFIC_FOUNDATION]] v1.0 (the foundation itself) · L1-layer instance/standard docs: [[MARKET_INEFFICIENCY_TAXONOMY]] v1.0 · [[ECONOMIC_MECHANISM_TAXONOMY]] v1.0 · [[EVIDENCE_MODEL]] v1.0 · [[LITERATURE_RESEARCH_STANDARD]] v1.0 |
| **Purpose** | The epistemology of the institution: what may be believed, on what evidence, and how belief is falsified |
| **Primary responsibility** | Owns the **closed sets** (per D-020): propositions P1–P8, rules R1–R20, assumptions A1–A8, limits LIM1–LIM8, mechanism classes M1–M6, domains D1–D6, evidence tiers E0–E7, falsification modes F1–F9; plus 8 ADRs (ADR-L1-001…008) |
| **Scope** | Scientific method and epistemology only; records L2 inconsistencies (§15, per D-013/ADR-L1-008) without resolving them |
| **Inputs** | L0 scope constraint; scientific method; adversarial review findings |
| **Outputs** | Closed vocabularies and laws consumed by every downstream layer |
| **Dependencies** | L0 |
| **Downstream dependents** | L2 (subordination rule §0.1 in each taxonomy doc), L3 (taxonomic substrates), L4 (gates, falsification), L5 (epistemological boundaries) |
| **Owner** | Chief Research Scientist / Scientific Methodology Architect |
| **Status** | Canonical (candidate — **pending adversarial sign-off**, G-8) |
| **Version** | 1.0 (unmodified since baseline `222d57f`; verified at D-024) |
| **Freeze status** | NOT frozen — G-8 is the sole Phase A exit blocker (D-024) |
| **Normative references** | ISO/IEC/IEEE 42010 (preface §0); [[DATA_FEASIBILITY_STUDY]] |
| **Informative references** | [[PHASE_A_REVIEW_PACKAGE]] v1.1 (byte-for-byte intact per D-024) |

### 2.3 L2 — Research Architecture

| Field | Value |
|---|---|
| **Layer** | L2 |
| **Document set** | Core: [[RESEARCH_OBJECT_MODEL]] **v2.0** (amended per D-022) · [[RESEARCH_OPERATING_MODEL]] v1.0 · [[RESEARCH_VALIDATION_FRAMEWORK]] **v1.1** (D-022 §0 amendment) · [[FEATURE_COMPUTATION_GRAPH]] v1.0 · [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] v1.0 (supporting reference — canonical logic in Operating Model, per R7) · [[FAILURE_LIBRARY_SCHEMA]] v1.0 · [[CUSTODY_MODEL]] v1.0 (new at D-022) · Extension/procedural: [[RESEARCH_OBJECT_SCHEMA]] v1.0 · [[HYPOTHESIS_LIFECYCLE]] v1.0 · [[RESEARCH_PROTOCOL]] v1.0 · [[EXPERIMENT_STANDARD]] v1.0 · [[PEER_REVIEW_STANDARD]] v1.0 · [[REPLICATION_STANDARD]] v1.0 · [[RESEARCH_QUALITY_STANDARD]] v1.0 · Proof artifact: [[WORKED_EXAMPLE_END_TO_END]] v1.0 |
| **Purpose** | The research machine on paper: objects, lifecycle, operating model, validation logic, custody policy, failure capture, procedure |
| **Primary responsibility** | Research Object Model (all S-objects), hypothesis lifecycle and transitions, gates G1–G4 (Operating Model §5–§6), custody policy ([[CUSTODY_MODEL]]), validation framework, pipeline stages S1–S10, researcher procedure |
| **Scope** | Architecture of research process; not epistemology (L1's), not data-entity formalization (L3's), not execution (L4's) |
| **Inputs** | L1 closed sets and laws; L0 scope and naming |
| **Outputs** | Object definitions, lifecycle rules, gates, custody policy, procedural standards |
| **Dependencies** | L0, L1 (explicit subordination-rule headers) |
| **Downstream dependents** | L3 (formalizes L2 objects as ontology entities), L4 (executes L2 lifecycle/gates), L5 (topologically isolates L2 concerns) |
| **Owner** | Research Architect (structural docs) / Chief Research Officer (operating model, procedural standards) |
| **Status** | Canonical; several marked "candidate — inherits an unsigned L1" |
| **Version** | Per document (see set above) |
| **Freeze status** | NOT frozen — Phase A gate; additionally Research OS v1.0 freeze blocked by G-9 |
| **Normative references** | [[01_SCIENTIFIC_FOUNDATION]], [[TAXONOMY_AND_NAMING_STANDARD]], [[DECISION_LOG]] D-020/D-021/D-022/D-023 |
| **Informative references** | "Realized in v3" header fields (mapping to existing code, per Phase A checklist item); [[WORKED_EXAMPLE_END_TO_END]] |

### 2.4 L3 — Data Ontology

| Field | Value |
|---|---|
| **Layer** | L3 |
| **Document name** | *L3 Data Ontology Specification: Institutional Research OS* (in `docs/L3 Data Ontology Specification.pdf`) |
| **Purpose** | Formalizes the semantic entities, relationships, and taxonomies of the research pipeline as "the universal blueprint for the runtime schemas, independently of their underlying database technology" (its own words) |
| **Primary responsibility** | Entity formalization: Literature Card (S1), Economic Mechanism (S2), Research Hypothesis (S3), Dataset Object (S4), Feature Definition (S5), Experiment Object (S6), Validation Report (S7–S8), Failure Library Entry — each with identifier and field definitions; taxonomic substrates (Evidence/Confidence/Reproducibility axes, Domain/Mechanism classes, Custody states and receipts); lineage as a first-class ontological entity (`hypothesis_links`, `provenance_envelope`, `custody_events`) |
| **Scope** | Semantic/data formalization only; "strictly derived from the existing architecture" (L0–L2) |
| **Inputs** | L1 closed sets (E, C, X, F, D, M scales); L2 Research Object Model, Custody Model, Hypothesis Lifecycle |
| **Outputs** | Entity/field/edge definitions consumed by L4 as the objects the runtime executes |
| **Dependencies** | L0, L1, L2 |
| **Downstream dependents** | L4 (executes the ontology), L5 (Ontological Manifest in Artifact Bundles; "Ontological Inviolability" conformance rule) |
| **Owner** | **Not declared** — the L3 section carries no Layer/Status/Owner header (RN-6) |
| **Status** | Authored; **unratified** — no decision-log entry, no review record (RN-3) |
| **Version** | **None declared** (RN-6) |
| **Freeze status** | NOT frozen; not a freeze candidate until ingested and reviewed (§10, Appendix B) |
| **Normative references** | L1 scales (E0–E7, C0–C4, X0–X4, F1–F9, D1–D6, M1–M6), L2 Custody Model (receipt fields), L2 lifecycle states |
| **Informative references** | "Resolution of Structural Ambiguities" section (blindness at N=1; pending custody realization) |

### 2.5 L4 — Runtime Architecture

| Field | Value |
|---|---|
| **Layer** | L4 |
| **Document name** | *L4 Runtime Architecture Specification — Institutional Research OS* (in the same PDF) |
| **Purpose** | "The abstract, implementation-independent runtime architecture that executes the L3 Data Ontology … the pure logical machine" (its own words) |
| **Primary responsibility** | 10 runtime principles (deterministic execution, immutable inputs, lineage preservation, reproducibility by construction, idempotency, statelessness, explicit dependency resolution, audit-first, failure transparency, version isolation); 12+ logical components (Dataset Registry & Resolver, Custody Manager, Feature Dependency Resolver, Feature Computation Engine, Experiment Orchestrator, Strategy Evaluation Engine, Statistical Validation Engine, Failure Capture Engine, Decision Engine & Governance Controller, Provenance Recorder & Lineage Engine, Artifact Registry & Publication Pipeline); object lifecycles with legal/illegal transitions and immutable checkpoints; canonical 12-stage execution graph; dependency resolution model; lineage runtime; failure runtime; runtime governance; 7 runtime invariants; state machine; sequence flows; extension model; non-functional requirements |
| **Scope** | Logical runtime only — its constraints forbid SQL schemas, database tables, REST APIs, programming languages, cloud providers, deployment architecture, implementation code |
| **Inputs** | L3 entities and lifecycles; L2 gates (G1–G4) and custody policy; L1 falsification modes (F1–F9) |
| **Outputs** | Behavioral specification consumed by L5 (which maps components to logical domains) |
| **Dependencies** | L0–L3 |
| **Downstream dependents** | L5 |
| **Owner** | Chief Systems Architect (per its header) |
| **Status** | Self-declared "Canonical Logical Specification"; **unratified** — no decision-log entry, no review record (RN-3); contains minor implementation-flavored references not yet cleaned by a refinement pass (RN-7) |
| **Version** | **None declared** (RN-6) |
| **Freeze status** | NOT frozen; not a freeze candidate until ingested and reviewed |
| **Normative references** | L3 ontology objects (S1–S8), L2 gates G1–G4, L1 F1–F9, PBO/DSR validation metrics (L2 Validation Framework) |
| **Informative references** | Sequence diagrams (§11), extension examples (§12) |

### 2.6 L5 — Reference Architecture

| Field | Value |
|---|---|
| **Layer** | L5 |
| **Document name** | *L5 Reference Architecture Specification — Institutional Research OS* — the **refined version** produced by the institutional architecture refinement pass (in the same PDF). The earlier draft in the same transcript is **superseded** (RN-5) |
| **Purpose** | "The architectural topology, logical domains, interaction contracts, and isolation boundaries … the rigid structural membrane between the behavioral semantics of the Runtime Architecture (L4) and the physical realization of the Technology Profiles (L6)" (its own words) |
| **Primary responsibility** | 10 Reference Architecture Principles (separation of knowledge and infrastructure, deterministic promotion, immutable knowledge, explicit contracts, domain isolation, technology independence, scientific integrity, lineage preservation, governance first, implementation replaceability); Logical Knowledge Domains (Acquisition, Processing, Governance, Preservation); Logical Execution Domains (Discovery, Orchestration & Control, Validation); Logical Artifact Architecture (Canonical Artifact Bundle: Logical Payload + Ontological Manifest + Lineage Envelope + Identity Signature); Logical Instruction Repositories (Platform, Structural, Theoretical); Epistemological Boundaries (Custody Fence, Systemic Operational Identity, Custody Policy Interceptors); Logical Deployment Boundaries (Ingress Isolation, Egress Air-Gap, Capital Boundary); Reference Interaction Model (4 inter-domain contracts); 5 Implementation Conformance Rules; Architecture Review Appendix |
| **Scope** | Topology and contracts only — zero vendor, technology, or protocol specifications (verified by its own Review Appendix); technology selection formally delegated to L6 |
| **Inputs** | L4 components and semantics; L3 ontology (manifest mapping); L2 custody policy and peer review; L1 epistemology |
| **Outputs** | Domain contracts and conformance obligations binding any future L6/L7 implementation |
| **Dependencies** | L0–L4 |
| **Downstream dependents** | L6 Technology Profiles (future, not authored) |
| **Owner** | Chief Enterprise Architect (per its header) |
| **Status** | Self-declared "Canonical Logical Specification"; passed one **self**-refinement pass with review appendix ("Architectural Status: VERIFIED"); **unratified** — no decision-log entry, no independent review (RN-3, RN-4) |
| **Version** | **None declared**; two in-transcript versions distinguishable only by position (RN-5, RN-6) |
| **Freeze status** | NOT frozen; not a freeze candidate until ingested and reviewed |
| **Normative references** | L3 Data Ontology ("Ontological Inviolability"), L4 runtime components, L2 Peer Review Standard (CRO sign-off in Interaction 4) |
| **Informative references** | Architecture Review Appendix (leakage-removal record) |

### 2.7 Withdrawn and future items (for completeness of the register)

| Item | Status | Record |
|---|---|---|
| **L4.5 Execution Semantics Specification** | **WITHDRAWN by owner decision.** Authored in the same transcript; the owner then concluded "Saya tidak lagi merekomendasikan membuat L4.5 … L4 yang sudah dihasilkan ternyata jauh lebih lengkap … Menambahkan L4.5 sekarang berisiko menduplikasi konsep" and fixed the roadmap as L0–L5 + L6. Its content is subsumed by L4. | Decision exists **only in the transcript** — no decision-log entry (RN-3) |
| **L5 Reference Architecture (draft version)** | **SUPERSEDED** by the refined version after the refinement pass (which removed named technologies: ACID, SHA/BLAKE, Parquet, Protobuf, PDF, message bus, etc.) | Supersession exists only in the transcript (RN-5) |
| **L6 Technology Profiles** | **FUTURE — deliberately deferred.** Named as the next layer by the owner's roadmap statement in the transcript. | Not a completeness gap |

---

## 3. Architecture Dependency Graph

```
L0  Governance & Scope        (root: scope constraint, naming law, decision authority)
 ↓
L1  Scientific Foundation     (epistemology; owns the closed sets)
 ↓
L2  Research Architecture     (objects, lifecycle, gates, custody policy, procedure)
 ↓
L3  Data Ontology             (formalizes L2 objects as semantic entities and edges)
 ↓
L4  Runtime Architecture      (the logical machine that executes the L3 ontology)
 ↓
L5  Reference Architecture    (topology, domains, contracts around the L4 machine)
 ↓
(L6 Technology Profiles — future; not part of this corpus)
```

**Dependency direction.** Strictly downward-facing: each layer may depend only on layers above it (lower-numbered). No layer may depend on, anticipate, or constrain a layer below it (higher-numbered), except by declaring what that layer must later satisfy (e.g., L5's Implementation Conformance Rules bind L6 without choosing anything for it).

**Ownership along the chain** (as declared in document headers): L0 — Chief Research Architect / CRO; L1 — Chief Research Scientist; L2 — Research Architect / CRO; L3 — undeclared (RN-6); L4 — Chief Systems Architect; L5 — Chief Enterprise Architect.

**Dependency rationale** (each stated by the documents themselves):
- L1 needs L0 because science operates only inside the binding scope constraint (D-002) and naming law (D-003).
- L2 needs L1 because every L2 taxonomy/standard carries an explicit **subordination rule** header ("inherits an unsigned L1").
- L3 needs L2 because it is "strictly derived from the existing architecture" and anchored on "the canonical Research Object Model".
- L4 needs L3 because "the L3 Data Ontology has already defined every scientific entity… the runtime executes the ontology" and its extension model "is rejected at the architecture level" if it mutates a Core L3 Object.
- L5 needs L4 because it is "the rigid structural membrane between the behavioral semantics of the Runtime Architecture (L4) and the physical realization of the Technology Profiles (L6)".

**Forbidden dependencies.**
- Upward mutation: no layer may amend a layer above it (D-013: L1 records L2 inconsistencies, does not resolve them; L4 extension model rejects L3 mutations; L5 "Ontological Inviolability" forbids implementations altering L3 semantics).
- L3 → runtime concepts (verified §6).
- L4 → ontology redefinition (verified §6).
- L5 → technology selection (verified §6; delegated to L6).
- Any layer → implementation/vendor/technology (until L6).

**Layer boundaries.** See §6 for the full boundary matrix.

---

## 4. Architecture Responsibility Matrix

Each concern has **exactly one** owning layer. Reference ≠ ownership: lower layers may *use* a concern but never *redefine* it.

| Architectural concern | Owner | Authoritative location |
|---|---|---|
| Research scope (what may be researched) | L0 | [[DATA_FEASIBILITY_STUDY]] (Data Capability Matrix, D-002) |
| Naming & taxonomy law | L0 | [[TAXONOMY_AND_NAMING_STANDARD]] |
| Decision records & phase gates | L0 | [[DECISION_LOG]], certificates, D-024 |
| Program structure (P-register) | L0 | [[RESEARCH_OS_MASTER_ROADMAP]] §3 + [[RESEARCH_PROGRAM_STANDARD]] |
| Epistemology (propositions, rules, assumptions, limits) | L1 | [[01_SCIENTIFIC_FOUNDATION]] P1–P8, R1–R20, A1–A8, LIM1–LIM8 |
| Closed classification sets (M1–M6, D1–D6, E0–E7, F1–F9) | L1 | [[01_SCIENTIFIC_FOUNDATION]] (closed per D-020) |
| Evidence axes (E-tier, C-confidence, X-reproducibility) & degradation | L1 | [[EVIDENCE_MODEL]] |
| Literature quality grades (Q0–Q4) & bias flags (B1–B9) | L1 | [[LITERATURE_RESEARCH_STANDARD]] |
| Mechanism instances (I1–I12) | L1 | [[ECONOMIC_MECHANISM_TAXONOMY]] |
| Research objects (definition of Hypothesis, Dataset, Feature, Experiment, Report, …) | L2 | [[RESEARCH_OBJECT_MODEL]] v2.0 |
| Object field schemas (extension) | L2 | [[RESEARCH_OBJECT_SCHEMA]] |
| Hypothesis lifecycle states & transitions | L2 | [[HYPOTHESIS_LIFECYCLE]] |
| Gates G1–G4 & institutional roles | L2 | [[RESEARCH_OPERATING_MODEL]] §5–§6 |
| Custody policy (states, receipts, events, the epistemological criterion) | L2 | [[CUSTODY_MODEL]] |
| Validation logic (PBO, DSR, falsification testing) | L2 | [[RESEARCH_VALIDATION_FRAMEWORK]] v1.1 |
| Pipeline stages S1–S10 | L2 | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (canonical logic in Operating Model per R7) |
| Feature-as-scientific-object & DAG law | L2 | [[FEATURE_COMPUTATION_GRAPH]] |
| Failure repository schema | L2 | [[FAILURE_LIBRARY_SCHEMA]] |
| Researcher procedure (what you do) | L2 | [[RESEARCH_PROTOCOL]] (per D-021: protocol ≠ specification) |
| Semantic entity formalization (IDs, fields, edge types) | L3 | L3 Data Ontology Specification §1–§2 |
| Lineage as first-class entity (`provenance_envelope`, `custody_events`, `hypothesis_links`) | L3 | L3 Data Ontology Specification §3 |
| Runtime principles & components | L4 | L4 Runtime Architecture §1–§2 |
| Runtime object lifecycles, state machine, legal/illegal transitions | L4 | L4 Runtime Architecture §3, §10 |
| Execution graph & dependency resolution | L4 | L4 Runtime Architecture §4–§5 |
| Failure runtime & runtime governance enforcement | L4 | L4 Runtime Architecture §7–§8 |
| Runtime invariants | L4 | L4 Runtime Architecture §9 |
| Logical domain topology (Knowledge & Execution Domains) | L5 | L5 Reference Architecture §2–§3 |
| Artifact Bundle structure | L5 | L5 Reference Architecture §4 |
| Inter-domain contracts (Reference Interaction Model) | L5 | L5 Reference Architecture §8 |
| Epistemological/deployment boundaries (Custody Fence, Air-Gap, Capital Boundary) | L5 | L5 Reference Architecture §6–§7 |
| Implementation conformance obligations | L5 | L5 Reference Architecture §9 |
| Technology selection | **L6 (future)** | — deliberately unowned in this corpus |

No duplicated ownership was found at the concern level. Terminology-level collisions are recorded in RN-8/RN-9.

---

## 5. Canonical Vocabulary Index

No terminology is invented here; every term below is quoted from its owning document.

| Concept | Definition (abbreviated) | Owning layer | Authoritative definition | Referenced by | Permitted aliases | Forbidden synonyms |
|---|---|---|---|---|---|---|
| **Data Capability Matrix** | The binding scope constraint on all research | L0 | [[DATA_FEASIBILITY_STUDY]] (D-002) | L1, L2, roadmap | — | — |
| **Phase** | *Retired from structural use* (D-003); survives only as the legacy label "Phase A" for L0+L1+L2 | L0 | [[DECISION_LOG]] D-003 | historical docs | "Phase A" (legacy, fixed meaning) | "Phase B/C/…" for new structure (use layers/programs) |
| **M1–M6** (Mechanism Classes) | Closed causal classification of mechanisms | L1 | [[01_SCIENTIFIC_FOUNDATION]] | L2, L3 (`taxonomy_class`) | — | any extension of the set outside L1 |
| **D1–D6** (Domains) | Six exclusive research domains with adjudication rule | L1 | [[01_SCIENTIFIC_FOUNDATION]] §3.5, ADR-L1-004 | L2, L3 | — | overlapping/merged domain labels |
| **E0–E7** (Evidence Tiers) | Scale of epistemic weight; Accepted Knowledge floors at E4 | L1 | [[01_SCIENTIFIC_FOUNDATION]]; elaborated [[EVIDENCE_MODEL]] | L2, L3 (`Evidence Tier`), L4 | — | — |
| **C0–C4** (Confidence Score) | Process-derived confidence axis | L1 | [[EVIDENCE_MODEL]] (three-axis thesis) | L3 | — | conflation with E-tier |
| **X0–X4** (Reproducibility Level) | Bit-identity / conclusion-invariance axis | L1 | [[EVIDENCE_MODEL]] | L3, L4 (audit replay) | — | conflation with E-tier |
| **F1–F9** (Falsification Modes) | Diagnostic taxonomy of mechanism invalidation | L1 | [[01_SCIENTIFIC_FOUNDATION]] | L2, L3 (`falsification_criteria`), L4 (Failure Capture) | — | — |
| **P1–P8 / R1–R20 / A1–A8 / LIM1–LIM8** | Propositions, rules, assumptions, limits | L1 | [[01_SCIENTIFIC_FOUNDATION]] | all layers | — | — |
| **Q0–Q4 / B1–B9** | Literature quality grades / nine biases | L1 | [[LITERATURE_RESEARCH_STANDARD]] | L3 (Literature Card fields) | — | — |
| **I1–I12** (Mechanism instances) | Instances mapping under M-classes | L1 | [[ECONOMIC_MECHANISM_TAXONOMY]] | L3 | — | — |
| **Research Object** (Hypothesis, Dataset, Feature, Experiment, Validation Report, Failure Entry, Literature Card, Mechanism) | The canonical objects of research | L2 | [[RESEARCH_OBJECT_MODEL]] v2.0 | L3 (S1–S8 formalization), L4, L5 | S1…S8 stage labels (pipeline context) | — |
| **G1–G4** (Gates) | Institutional decision gates | L2 | [[RESEARCH_OPERATING_MODEL]] §5–§6 | L3 (`lifecycle_state`), L4 (Governance Controller), L5 (Interaction 4) | — | — |
| **Custody** (states, receipt, event, axis) | Epistemological availability control; receipt fields `asset_ref, accessor, purpose_ref, ordinal, prior_receipt` | L2 | [[CUSTODY_MODEL]] | L3 §2–§3, L4 (Custody Manager), L5 §6 | "Data Fence" (L5 draft: "The Data Fence"; refined: "Custody Fence") — see RN-9 | — |
| **In-Sample / Out-of-Sample (IS/OOS)** | Custody states of data partitions | L2 | [[CUSTODY_MODEL]] | L3, L4, L5 (Knowledge Processing partitioning) | — | — |
| **Blind partition** | Yields E6 + maximal custody, never E7 | L2/L1 boundary | [[DECISION_LOG]] D-023 ([[RT4_RESOLUTION_2026-07-15]]) | L3 (`blind_to`) | — | "Blind ⇒ E7" (disproven at D-023) |
| **Hypothesis lifecycle states** | Draft → Registered → Active → Evaluated → Accepted/Rejected → Archived (runtime rendering) | L2 | [[HYPOTHESIS_LIFECYCLE]] | L3 (`lifecycle_state`), L4 §3 | — | — |
| **S1–S10** (Pipeline stages) | Stages of the research pipeline | L2 | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] | L3 (entity labels S1–S8), [[WORKED_EXAMPLE_END_TO_END]] | — | — |
| **PBO / DSR** | Probability of Backtest Overfitting / Deflated Sharpe Ratio | L2 | [[RESEARCH_VALIDATION_FRAMEWORK]] | L3 (report fields), L4 (Statistical Validation Engine) | — | — |
| **Provenance Envelope** | `(run_id, dataset_fingerprint, code_commit)` tuple bound to every artifact | L3 (formalized as first-class entity; policy roots in L2) | L3 Data Ontology §3 | L4 §6 (generation), L5 §4 (Lineage Envelope in Artifact Bundle) | "Lineage Envelope" (L4/L5 usage) | — |
| **Dataset Fingerprint** | Cryptographic hash ensuring dataset immutability | L3 | L3 Data Ontology §1 (S4) | L4 (invariant 1), L5 | — | — |
| **Execution Identity / Execution Context** | Deterministic hash of the complete declared execution context | L4 | L4 Runtime Architecture (lineage runtime; elaborated in the withdrawn L4.5 §1 — see RN-10) | L5 (Interaction 1) | — | — |
| **Runtime Invariants (Append-Only Law, etc.)** | The 7 unalterable runtime laws | L4 | L4 Runtime Architecture §9 | L5 conformance rules | — | — |
| **Knowledge Domains** (Acquisition / Processing / Governance / Preservation) | Epistemologically partitioned logical storage domains | L5 | L5 Reference Architecture §2 | — (terminal layer) | — | storage-medium names (Data Lake, Vault — superseded draft terms, RN-5) |
| **Execution Domains** (Discovery / Orchestration & Control / Validation) | Partitioned logical compute topology | L5 | L5 Reference Architecture §3 | — | "Research Sandbox" (draft term for Discovery — superseded) | — |
| **Canonical Artifact Bundle** | Payload + Ontological Manifest + Lineage Envelope + Identity Signature | L5 | L5 Reference Architecture §4 | — | — | "file" |
| **Capital Boundary** | Unidirectional gateway Research OS → Production/Trading OS; crossed only by Accepted Knowledge | L5 (topology) | L5 Reference Architecture §7 | L2 (evidence/custody rationale), L4 (Publication Pipeline) | — | — |
| **Accepted Knowledge** | Terminal epistemic status enabling capital promotion (floors at E4) | L1 (criterion) / L2 (process) | [[EVIDENCE_MODEL]] + [[RESEARCH_OPERATING_MODEL]] | L3, L4, L5 | — | — |
| **Failure Library** | Append-only repository of falsified work | L2 | [[FAILURE_LIBRARY_SCHEMA]] | L3 (entry entity), L4 (Failure Capture Engine), L5 | — | — |

---

## 6. Architecture Boundary Matrix

| Layer | Defines | Must NEVER define | Upstream responsibility (owes to layers above) | Downstream responsibility (owes to layers below) |
|---|---|---|---|---|
| **L0** | Scope, naming, decisions, gates, certification | Science, architecture, ontology, runtime, technology | — (root) | A stable scope constraint and naming law all layers can rely on |
| **L1** | Epistemology; closed classification sets; scientific laws | Process mechanics, object schemas, data entities, runtime, technology | Operate within L0 scope | Closed vocabularies that downstream layers reference but never extend (D-020) |
| **L2** | Research objects, lifecycle, gates, custody policy, validation logic, procedure | Epistemology (defers to L1), entity-level field formalization beyond its object model (L3's), execution mechanics (L4's), topology (L5's), technology | Subordination to L1 (explicit headers) | Object and policy definitions stable enough for L3 to formalize |
| **L3** | Semantic entities, fields, identifiers, edges, lineage entities, taxonomic mappings | **Runtime behavior, execution, components, scheduling** — and technology | Strict derivation from L0–L2; no new science, no new objects | An ontology complete enough that L4 executes it without redefining it |
| **L4** | Runtime principles, components, lifecycles, state machines, execution graph, invariants, runtime governance | **Ontology (entity/field semantics)** — and storage media, technology, deployment | Executes L3 without mutation ("rejected at the architecture level") | Behavioral semantics complete enough that L5 only places, isolates, and contracts them |
| **L5** | Logical domains, boundaries, contracts, artifact structure, conformance obligations | **Technology, vendors, protocols, physical deployment** (delegated to L6) | Preserves L4 semantics and L3 inviolability | Conformance rules binding any future L6 profile |

**Explicit boundary verifications (as required):**

- **L3 never defines runtime — VERIFIED, with one recorded observation.** The L3 document defines entities, fields, axes, and edge semantics only; execution appears nowhere. One borderline item: `provenance_envelope` is described as "embedded into `research.tracking`" — a reference to an existing implementation module, i.e. implementation leakage rather than runtime definition (RN-7).
- **L4 never defines ontology — VERIFIED.** L4 references L3 objects (S5 Feature Definitions, lifecycle states, F1–F9, G1–G4) but defines none; its Extension Model states an extension requiring "mutation of a Core L3 Object … is rejected at the architecture level."
- **L5 never defines technology — VERIFIED for the canonical (refined) version.** Its own Architecture Review Appendix records the removal of all technology references (Parquet, Protobuf, ACID, SQL, SHA/BLAKE, cloud, containers, REST, message buses) and verifies L5/L6 separation ("L5 contains zero vendor, technology, or protocol specifications"). The superseded draft **failed** this test (RN-5) — a reader must not cite the draft.

---

## 7. Architecture Navigation Guide

**Reading order for a new architect:**

1. **This ASI** — orientation, boundaries, and freeze reality.
2. **L0**: [[TAXONOMY_AND_NAMING_STANDARD]] (learn the naming law first), then [[DATA_FEASIBILITY_STUDY]] (the binding scope), then [[DECISION_LOG]] D-001…D-024 (why everything is the way it is), then [[RESEARCH_OS_MASTER_ROADMAP]].
3. **L1**: [[01_SCIENTIFIC_FOUNDATION]] in full (~800 lines) — everything downstream cites its closed sets. Then [[EVIDENCE_MODEL]], [[MARKET_INEFFICIENCY_TAXONOMY]], [[ECONOMIC_MECHANISM_TAXONOMY]], [[LITERATURE_RESEARCH_STANDARD]].
4. **L2 core**: [[RESEARCH_OBJECT_MODEL]] → [[RESEARCH_OPERATING_MODEL]] → [[CUSTODY_MODEL]] → [[RESEARCH_VALIDATION_FRAMEWORK]] → [[HYPOTHESIS_LIFECYCLE]] → [[FEATURE_COMPUTATION_GRAPH]] → [[FAILURE_LIBRARY_SCHEMA]]. Then the procedural face: [[RESEARCH_PROTOCOL]] (single entry point for researchers), [[EXPERIMENT_STANDARD]], [[PEER_REVIEW_STANDARD]], [[REPLICATION_STANDARD]], [[RESEARCH_QUALITY_STANDARD]].
5. **[[WORKED_EXAMPLE_END_TO_END]]** — the composition proof; read before L3 to see what the ontology must carry.
6. **L3 → L4 → L5** in the PDF (`docs/L3 Data Ontology Specification.pdf`), in that order. **Skip the L4.5 section (withdrawn) and the first L5 draft (superseded)**; the canonical L5 is the refined version following the "architecture refinement pass" prompt.

**Prerequisites.** None external. Internally: never read an L2+ document before L1 (every L2 doc's subordination header assumes L1); never read L4 before L3 (L4's components are meaningless without the entities they operate on).

**Review checkpoints for the reader:**
- After L1: can you state the E-tier criterion for Accepted Knowledge and why the author cannot self-certify (LIM6)?
- After L2: can you trace one hypothesis through S1–S10 and G1–G4 with custody receipts at each data touch?
- After L3: can you name the fields of the provenance envelope and the custody receipt?
- After L4: can you list the 7 runtime invariants and one illegal transition per object?
- After L5: can you name the four Knowledge Domains, the three Execution Domains, and what may cross the Capital Boundary?

**Cross-reference strategy.** Repository documents use `[[WIKILINK]]` cross-references and carry `Supersedes` / `Does NOT supersede` header fields — always honor those fields over inference. "Realized in v3" headers map architecture to existing code and are informative, not normative. For L3–L5 (PDF), cross-references are positional within the transcript; use Appendix A of this ASI as the reference map until the documents are ingested (RN-2).

---

## 8. Architecture Review Index

| Document / layer | Maturity | Review status | Approval status | Freeze status | Deferred work | Future dependents |
|---|---|---|---|---|---|---|
| L0 set | Canonical governance | Governance audit (18-category, 2026-07-16, `dc337b9`/`bff41ae`); [[DOCUMENTATION_HIERARCHY_AUDIT]] | D-024 GO WITH CONDITIONS | NOT frozen (Phase A gate) | [[FUTURE_GOVERNANCE_OUTLINES]] items (target L4-old-scheme docs — see RN-8); D-015 owner decision on L1 location **unanswered** | All layers |
| L1 [[01_SCIENTIFIC_FOUNDATION]] | Certified-ready | Multiple: architecture review, red team (5 findings), ARB adjudication (4 of 5 rejected), RT-4 resolution (D-023), final gate review | D-018 certificate v2.1 GO WITH CONDITIONS; D-024 | **NOT frozen — G-8 open** (independent adversarial sign-off; the criterion is "not the author", D-019) | AQ-2; §5.7 L2 rationale debt (RD-1…RD-7, closable only by original decider); recorded 42010 §5.6 inconsistencies (§15) | L2–L5 |
| L2 set | Canonical (several "candidate — inherits unsigned L1") | Red team + ARB + custody propagation audit; zero open architectural contradictions (D-024) | Inside Phase A gate | NOT frozen; **Research OS v1.0 freeze additionally blocked by G-9** (Dataset Custody mechanism — policy exists, mechanism does not) | G-9 closure; N=2 staffing closes G-4 ([[PEER_REVIEW_STANDARD]] staffing condition) | L3–L5 |
| L3 Data Ontology | Authored (single generation pass) | **NONE** — no independent review | **UNRATIFIED** — no decision record | NOT frozen; not yet a freeze candidate | Ingestion into repo as versioned markdown (RN-2); owner + version headers (RN-6); leakage cleanup (RN-7); consistency review against L2 object model | L4, L5, L6 |
| L4 Runtime Architecture | Authored (single generation pass) | **NONE** | **UNRATIFIED** | NOT frozen; not yet a freeze candidate | Same ingestion/header work; refinement pass equivalent to L5's (RN-7) | L5, L6 |
| L4.5 Execution Semantics | **WITHDRAWN** | n/a | Owner decision in transcript only (RN-10) | n/a | Record the withdrawal decision in [[DECISION_LOG]] (pending governance action, Appendix B) | none |
| L5 Reference Architecture (refined) | Authored + one self-refinement pass with review appendix | Self-review only ("Architectural Status: VERIFIED" — author's own appendix; per D-019/LIM8 logic, a self-verification is not independent validation) | **UNRATIFIED** | NOT frozen; not yet a freeze candidate | Ingestion; independent review; supersession of the draft to be recorded (RN-5) | L6 |

---

## 9. Architecture Integrity Rules

These are the standing governance laws this index enforces; each is grounded in an existing corpus rule.

1. **One concept, one owner.** Every architectural concept has exactly one owning layer (§4). Grounded in D-020 (closed sets live in L1; extensions own only instances and omitted rules).
2. **One authoritative definition.** A concept is defined once, in its owning document; all other appearances are references. Grounded in the subordination-rule headers of every L1/L2 taxonomy and standard.
3. **One authoritative location.** Every document has one canonical path; [[TAXONOMY_AND_NAMING_STANDARD]] governs naming and placement (D-015 records the one known location violation — the L1 artifact's path — with the owner decision still pending).
4. **No duplicated architecture.** A new document may extend but never restate a canonical one — enforced in the corpus via explicit "Does NOT supersede" header fields; the L4.5 withdrawal applied exactly this rule ("berisiko menduplikasi konsep yang sudah ada").
5. **No circular ownership.** Dependencies point strictly upward (§3); no layer amends a layer above it (D-013 pattern).
6. **No conflicting terminology.** The vocabulary index (§5) is the collision register; current collisions are RN-8 (layer numbering) and RN-9 (Data Fence / Custody Fence) — recorded, not resolved.
7. **No conflicting responsibilities.** The responsibility matrix (§4) admits exactly one owner per concern; any future document claiming an owned concern must carry a "Does NOT supersede" header or a decision-log entry transferring ownership.
8. **Supersession is explicit and recorded.** A document version is replaced only via a `Supersedes` header and, for governance-relevant changes, a decision-log entry (pattern: ROM v1.0→v2.0 via D-022). In-transcript supersessions (RN-5, RN-10) are **not yet compliant** with this rule.
9. **Self-certification is void.** Author review does not discharge a review gate (L1 LIM6/LIM8, D-019). This applies to L5's own "VERIFIED" appendix exactly as it applied to Phase A.
10. **The index is descriptive, never normative.** This ASI records the corpus; it can never be cited as the definition of any architectural concept.

---

## 10. Corpus Completeness Assessment

Assessment of the **existing** architecture only. No work is invented to inflate completeness.

| Area | Assessment |
|---|---|
| **Vision** | Present in substance (roadmap §1, D-001, L0 purpose statements) but **no document titled "Vision" exists** — see RN-1. Whether a dedicated L0 Vision document is needed is an owner decision, not a recorded gap. |
| **Scientific Foundation (L1)** | **Complete.** Certified-ready; zero open architectural contradictions (D-024). Open items are process (G-8), not content. |
| **Research Architecture (L2)** | **Complete** as architecture. Known, honestly-recorded debts: §5.7 rationale debt (RD-1…RD-7), G-9 (custody is modelled, not mechanized — "a model of a control is not a control", [[CUSTODY_AMENDMENT]]). |
| **Data Ontology (L3)** | **Content-complete relative to L2** (all S-objects, axes, lineage entities formalized) but **governance-incomplete**: not in the repository, no owner, no version, no review, no decision record (RN-2, RN-3, RN-6). |
| **Runtime Architecture (L4)** | Content-complete per its own 13-section structure; same governance incompleteness as L3; carries minor implementation leakage that L5's refinement pass removed from L5 but was never applied to L4 (RN-7). |
| **Reference Architecture (L5)** | Content-complete and leakage-clean (refined version); same governance incompleteness; supersession of its own draft unrecorded outside the transcript (RN-5). |
| **Governance** | Strong for L0–L2 (24 decisions, certificates, adversarial reviews, audits). **Absent for L3–L5** — the single largest genuine gap in the corpus (RN-3). |
| **Vocabulary** | Coherent; two genuine collisions recorded (RN-8 layer numbering, RN-9 fence naming). No undefined load-bearing terms found. |
| **Boundaries** | Sound; all three mandated verifications pass (§6). |
| **Dependency structure** | Acyclic, strictly downward, explicitly rationalized at every step (§3). No forbidden dependency found in the canonical versions. |

**Genuine gaps (exhaustive — nothing else is claimed):**
1. L3–L5 exist only as a chat-transcript PDF, outside the repository's versioning, naming standard, and custody discipline (RN-2).
2. No decision-log entries ratify L3, L4, L5, the L4.5 withdrawal, or the L5 draft supersession (RN-3, RN-5, RN-10).
3. L3 lacks an owner and all three PDF layers lack version identifiers (RN-6).
4. G-8 (one signature) holds the entire corpus's freeze chain open; L3–L5 additionally inherit an unsigned L1 with **zero** reviews of their own (RN-4).
5. Layer-numbering collision between the old roadmap scheme and the new L3–L5 scheme, visible in three L2 document headers (RN-8).

---

## 11. Review Notes

Inconsistencies discovered during indexing. **Recorded only — nothing has been modified.** Resolution authority: respective document owners via [[DECISION_LOG]].

- **RN-1 — "L0 Vision" vs "L0 Governance & Scope".** The commissioning brief for this ASI names L0 "Vision". Every on-disk L0 document and [[RESEARCH_OS_MASTER_ROADMAP]] §2 name L0 "Governance & Scope". No document titled "Vision" exists. This ASI indexes the on-disk name as authoritative.
- **RN-2 — L3–L5 medium.** The L3/L4/L5 specifications exist only inside `docs/L3 Data Ontology Specification.pdf`, a transcript export (the filename names only L3 but the file contains L3, L4, L4.5, and two L5 versions). They are outside the repository's markdown corpus, naming standard, wikilink graph, and git custody. Until ingested, they are canonical **in content** but non-compliant **in form**.
- **RN-3 — No governance records for L3–L5.** [[DECISION_LOG]] ends at D-024 (Phase A exit gate). No decision ratifies L3, L4, or L5 as canonical layers, despite each self-declaring "Canonical Logical Specification".
- **RN-4 — Review asymmetry.** The brief's premise "these documents have already undergone multiple architecture reviews and refinement cycles" is true for L0–L2 (red team, ARB, gate reviews, audits) and for L5 only in the weak sense of one **self**-refinement pass. L3 and L4 have undergone zero review cycles. Per the corpus's own rule (LIM6/LIM8, D-019), L5's self-issued "VERIFIED" is not a discharged review.
- **RN-5 — Two L5 versions.** The transcript contains an L5 draft (with named technologies: ACID, SHA/BLAKE, Parquet, Protobuf, PDF, message bus, and partially Indonesian text) and a refined final version whose appendix records the leakage removal. The refined version is treated as canonical; the supersession is recorded nowhere outside the transcript.
- **RN-6 — Missing headers.** The L3 section carries no Layer/Status/Owner/Version header at all; L4 and L5 carry Layer/Status/Owner but no Version and no Date. All repository documents carry full headers; L3–L5 do not meet that standard.
- **RN-7 — Residual implementation leakage.** L3: `provenance_envelope` "embedded into `research.tracking`" (an implementation module name). L4: "Kahn's Algorithm or DFS", "Pub/Sub abstraction", "`IFeatureNode` contract", "Float math" — the exact class of leakage the L5 refinement pass was commissioned to remove, never applied to L4 or L3.
- **RN-8 — Layer-numbering collision (structural).** The old scheme ([[RESEARCH_OS_MASTER_ROADMAP]] §2 and the roadmap diagram) assigns: L3=Data Ontology, **L4=Research Infrastructure, L5=Feature Computation, L6=Hypothesis Engine, L7=Validation, L8=Knowledge Repository**. The new scheme (this corpus's L4/L5 + the owner's in-transcript roadmap) assigns **L4=Runtime Architecture, L5=Reference Architecture, L6=Technology Profiles**. Three L2 document headers still carry old-scheme dual labels: [[FEATURE_COMPUTATION_GRAPH]] "L2 / L5 — Feature Computation", [[RESEARCH_VALIDATION_FRAMEWORK]] "L2 / L7 — Validation", [[FAILURE_LIBRARY_SCHEMA]] "L2 / L8 — Knowledge Repository". [[FUTURE_GOVERNANCE_OUTLINES]] also targets old-scheme "Layer L4". Under the new scheme these labels are ambiguous. **This is the one genuine structural inconsistency found.** Resolution (re-labeling vs. dual-scheme declaration) is an owner decision requiring a decision-log entry; this ASI indexes both schemes and flags every affected header.
- **RN-9 — Fence naming.** L2/v3 use "write fence"/"Data Fence"; the L5 draft uses "The Data Fence"; the refined L5 renames it "The Custody Fence". Same concept, owner is [[CUSTODY_MODEL]] (L2). Alias mapping recorded in §5; no document declares the rename.
- **RN-10 — L4.5 withdrawal is unrecorded.** The decision to withdraw L4.5 Execution Semantics (sound, and consistent with integrity rule 4) exists only as prose inside the transcript. Its content partially elaborates L4 concepts (e.g., Execution Identity is *defined* most precisely in the withdrawn L4.5 §1). Until the withdrawal is recorded and L4 is confirmed to subsume the needed definitions, there is a small orphaned-definition risk.

---

## Appendix A — Cross-Reference Map

Direction: **row references column-listed documents.** (Repository docs per their headers/wikilinks; L3–L5 per in-text references.)

| Document | References (normative) | Referenced by |
|---|---|---|
| [[DATA_FEASIBILITY_STUDY]] (L0) | — | L1 preface, [[MARKET_INEFFICIENCY_TAXONOMY]], [[WORKED_EXAMPLE_END_TO_END]], roadmap |
| [[TAXONOMY_AND_NAMING_STANDARD]] (L0) | — | [[HYPOTHESIS_LIFECYCLE]] §0.2, D-015, roadmap |
| [[DECISION_LOG]] (L0) | all reviewed docs | virtually every canonical doc |
| [[RESEARCH_OS_MASTER_ROADMAP]] (L0) | [[DATA_FEASIBILITY_STUDY]], [[DECISION_LOG]], [[01_SCIENTIFIC_FOUNDATION]], all L2 docs | [[RESEARCH_PROGRAM_STANDARD]] §0.2, [[RESEARCH_PROGRAM_PLAYBOOK]], D-024 |
| [[01_SCIENTIFIC_FOUNDATION]] (L1) | [[DATA_FEASIBILITY_STUDY]], ISO 42010 | every L1-instance and L2 doc (subordination headers); L3 (axes); L4 (F1–F9, gates); L5 (epistemological boundaries) |
| [[EVIDENCE_MODEL]] (L1) | [[01_SCIENTIFIC_FOUNDATION]] | [[CUSTODY_MODEL]], D-023, L3 (E/C/X axes) |
| [[ECONOMIC_MECHANISM_TAXONOMY]] / [[MARKET_INEFFICIENCY_TAXONOMY]] (L1) | [[01_SCIENTIFIC_FOUNDATION]] §0.1 subordination | L2 pipeline docs, L3 (`taxonomy_class`, Domain Class) |
| [[LITERATURE_RESEARCH_STANDARD]] (L1) | [[01_SCIENTIFIC_FOUNDATION]] | L3 (Literature Card: Q-grades, B-flags) |
| [[RESEARCH_OBJECT_MODEL]] v2.0 (L2) | D-022, [[CUSTODY_MODEL]] §7 | [[RESEARCH_OBJECT_SCHEMA]] §0.1, [[WORKED_EXAMPLE_END_TO_END]], L3 §1 ("anchored by the canonical Research Object Model") |
| [[RESEARCH_OPERATING_MODEL]] (L2) | [[01_SCIENTIFIC_FOUNDATION]] | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (R7), [[PEER_REVIEW_STANDARD]], [[HYPOTHESIS_LIFECYCLE]] §0.2, [[RESEARCH_PROTOCOL]] §0.2, L4 (G1–G4) |
| [[CUSTODY_MODEL]] (L2) | [[01_SCIENTIFIC_FOUNDATION]] §2.4/R6, D-022 | [[RESEARCH_VALIDATION_FRAMEWORK]] §0, ROM v2.0 §3–§4, D-023, L3 §2 (Custody Receipt fields), L4 (Custody Manager), L5 §6 (Custody Fence, Interceptors) |
| [[RESEARCH_VALIDATION_FRAMEWORK]] v1.1 (L2) | [[CUSTODY_MODEL]] (§0 precondition, D-022) | [[EXPERIMENT_STANDARD]] (non-supersession), L3 (PBO/DSR fields), L4 (Statistical Validation Engine), L5 (Interaction 2) |
| [[HYPOTHESIS_LIFECYCLE]] (L2) | [[TAXONOMY_AND_NAMING_STANDARD]] §6, [[RESEARCH_OPERATING_MODEL]] §6–§7 | L3 (`lifecycle_state`), L4 §3 (Hypothesis lifecycle) |
| [[FEATURE_COMPUTATION_GRAPH]] (L2) | [[01_SCIENTIFIC_FOUNDATION]] | L3 (S5 Feature Definition), L4 (Feature Dependency Resolver / Computation Engine), L5 (Structural Instruction Domain) |
| [[FAILURE_LIBRARY_SCHEMA]] (L2) | — | L3 (Failure Library Entry), L4 (Failure Capture Engine), L5 (conformance rule 1) |
| [[WORKED_EXAMPLE_END_TO_END]] (L2 proof) | [[RESEARCH_OBJECT_MODEL]], [[DATA_FEASIBILITY_STUDY]], pipeline S1–S10 | roadmap ("proves" edge), this ASI §7 |
| **L3 Data Ontology** (PDF) | L1 axes, L2 object model / custody / lifecycle | **L4** ("executes the ontology"), **L5** (Ontological Manifest, Ontological Inviolability) |
| **L4 Runtime Architecture** (PDF) | L3 (all objects), L2 gates, L1 F-modes | **L5** (all components mapped to domains), withdrawn L4.5 |
| **L5 Reference Architecture** (PDF, refined) | L4 components, L3 ontology, L2 peer review (CRO sign-off) | future L6 |

---

## Appendix B — Freeze Summary

**Frozen documents:** **None.** ([[RESEARCH_MASTER_PLAN]] v3 is ratified & frozen, but it is a *research plan*, not part of the architecture corpus indexed here — see [[RESEARCH_OS_RECONCILIATION]] for the relationship.)

**Freeze candidates (in dependency order):**

| Candidate | Blocked by | What closure takes |
|---|---|---|
| Phase A (L0+L1+L2) | **G-8 only** — one independent adversarial sign-off; criterion is "not the author", not "external" (D-019/D-024) | One qualified reviewer, [[PHASE_A_REVIEW_PACKAGE]] v1.1 is ready; **zero new documents** ([[PHASE_A_FINAL_GATE_REVIEW]]) |
| Research OS v1.0 | G-8 + **G-9** (Dataset Custody mechanism — policy without mechanism; standing rule from [[CUSTODY_AMENDMENT]]: no freeze while G-9 open) | Custody mechanism implementation (only blocking gap closable without hiring, per [[PROTOCOL_LAYER_DELIVERY]] finding) |
| L3 / L4 / L5 | Not yet freeze candidates: unratified, unreviewed, un-ingested (RN-2, RN-3) | Ingestion → headers → decision-log ratification → independent review — then eligible |

**Deferred work register:** L6 Technology Profiles (deliberate); [[FUTURE_GOVERNANCE_OUTLINES]] items (DB concept, metadata standard — old-scheme "L4" targets, RN-8); L2 §5.7 rationale debt RD-1…RD-7; AQ-2; L4 leakage-refinement pass (RN-7); G-4 closure via N=2 staffing (the same second researcher closes G-8 and G-4 — "one person, two gates", [[PHASE_A_FINAL_GATE_REVIEW]]).

**Owner decisions on record:** D-001…D-024 (see [[DECISION_LOG]]); most recent: D-024 Phase A Exit Gate — GO WITH CONDITIONS, G-8 sole blocker. **Owner decisions pending:** D-015 (L1 artifact location — asked 4×, unanswered); disposition of RN-8 (layer-numbering scheme); formal ratification or rejection of L3–L5 as canonical layers.

**Pending governance actions (implied by the corpus's own rules — no new work invented):**
1. Record the L4.5 withdrawal and the L5 draft supersession in [[DECISION_LOG]] (integrity rule 8).
2. Ingest L3–L5 into the repository under [[TAXONOMY_AND_NAMING_STANDARD]] with full headers (RN-2, RN-6).
3. Obtain the G-8 sign-off — the single signature holding the entire freeze chain open.
4. Adjudicate RN-8 (one layer-numbering scheme, or a recorded dual-scheme rule).

---

*End of Architecture Specification Index v1.0. This document is descriptive only; it defines no architecture and may never be cited as the authoritative definition of any concept it indexes.*
