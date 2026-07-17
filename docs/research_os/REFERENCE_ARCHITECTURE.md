# L5 Reference Architecture Specification — Institutional Research OS

**Title:** L5 Reference Architecture Specification — Institutional Research OS
**Document ID:** `REFERENCE_ARCHITECTURE` (canonical wikilink name)
**Version:** 1.0 · **Status:** **Canonical** — ratified by the Owner 2026-07-17 (**D-027**; L5 slot defined under **D-025**). **Not frozen:** independent review pending ([[ARCHITECTURE_SPECIFICATION_INDEX]] RN-4) and inherits Phase A pending G-8. See [[GOVERNANCE_BASELINE_v1]].
**Owner:** Chief Enterprise Architect (self-declared in source)
**Review Status:** Self-refinement pass only — one "institutional architecture refinement pass" with a self-issued Architecture Review Appendix ("VERIFIED"). Per the corpus's own rule (L1 LIM6/LIM8, [[DECISION_LOG]] D-019), a self-verification is not an independent review; independent review is pending (ASI RN-4).
**Layer:** L5 — Reference Architecture *(**ratified under D-025**, transcript scheme adopted; the L5 slot is now defined as "Reference Architecture". The prior CONTESTED status — no fitting slot in the old ratified vocabulary — is resolved by that ratification; see [[LAYER_MAPPING_TABLE]].)*
**Dependencies:** [[RUNTIME_ARCHITECTURE]] (the components this topology places) · [[DATA_ONTOLOGY]] (Ontological Manifest; Ontological Inviolability rule) · [[CUSTODY_MODEL]] (custody policy the Custody Fence realizes) · [[PEER_REVIEW_STANDARD]] (CRO sign-off in Interaction 4) · [[01_SCIENTIFIC_FOUNDATION]]
**Last Updated:** 2026-07-16 (transcript date) · **Ingested:** 2026-07-16
**Supersedes:** [[REFERENCE_ARCHITECTURE_DRAFT]] v0.1 (the pre-refinement draft, which contained implementation leakage — ASI RN-5)
**Related Documents:** [[ARCHITECTURE_SPECIFICATION_INDEX]] §2.6 · future L6 Technology Profiles (not authored — deliberately deferred)

> **Provenance.** Ingested verbatim from `docs/L3 Data Ontology Specification.pdf` (transcript export, created 2026-07-16 13:35 WIB), pages 25–30 — the **refined** version produced by the "institutional architecture refinement pass". Layout normalized to markdown; page headers, transcript URLs, and commissioning prompts removed. **No wording altered.** Per [[GOVERNANCE_REMEDIATION_REPORT]] P5: only this refined version may be treated as Canonical; the draft is preserved as Superseded at [[REFERENCE_ARCHITECTURE_DRAFT]].

---

**Layer:** L5 — Reference Architecture · **Status:** Canonical Logical Specification · **Owner:** Chief Enterprise Architect *(source self-declaration, preserved)*

This specification defines the architectural topology, logical domains, interaction contracts, and isolation boundaries of the Institutional Research Operating System. As the canonical L5 Reference Architecture, this document acts as the rigid structural membrane between the behavioral semantics of the Runtime Architecture (L4) and the physical realization of the Technology Profiles (L6).

This document describes purely what architectural responsibilities exist and how they are topologically isolated. It completely abstracts how these responsibilities are physically implemented. No implementation may bypass the logical contracts defined herein.

## 1. Reference Architecture Principles

These principles serve as the immutable architectural laws of the L5 layer. Every future physical implementation (L6/L7) must mathematically and structurally guarantee these principles.

1. **Separation of Knowledge and Infrastructure:** The logical representation of scientific knowledge must be completely decoupled from the transient infrastructure that computes or stores it.
2. **Deterministic Promotion:** Artifacts move across logical domains exclusively via deterministic, contract-driven promotion. Manual or out-of-band state mutation is structurally prohibited.
3. **Immutable Knowledge:** Once a knowledge artifact achieves a terminal logical state, its representation is strictly append-only.
4. **Explicit Contracts:** All inter-domain communication occurs through explicit, versioned logical contracts. There are no implicit dependencies or hidden data flows.
5. **Domain Isolation:** Execution contexts and knowledge boundaries are structurally partitioned. Failure or compromise in one domain must be mathematically contained within its defined boundary.
6. **Technology Independence:** The validity of a scientific artifact must be entirely agnostic to the underlying hardware, scheduling mechanisms, or storage mediums.
7. **Scientific Integrity:** Epistemological security (Custody) takes absolute precedence over system performance, availability, or operational convenience.
8. **Lineage Preservation:** Every derived state must possess an unbroken, verifiable causal chain back to its axiomatic origin.
9. **Governance First:** Governance is not a systemic overlay; it is the fundamental structural gatekeeper. No logic executes, and no state transitions, without prior governance authorization.
10. **Implementation Replaceability:** Any L6 technology stack fulfilling an L5 domain contract can be entirely swapped without altering the mathematical validity of the Research OS.

## 2. Logical Knowledge Domains

The reference architecture discards medium-specific storage models in favor of Knowledge Domains. These domains separate information based on its epistemological maturity, mutability, and custody state.

- **Knowledge Acquisition Domain:** The foundational logical boundary for all external stimuli and raw empirical observations. It acts as an append-only, immutable temporal ledger. Once an observation enters this domain and is assigned a deterministic identity, its structural representation can never be altered.
- **Knowledge Processing Domain:** The domain responsible for housing derived structural data (e.g., resolved features). This domain requires rigorous logical partitioning, enforcing a structural void between In-Sample exploratory state and Out-of-Sample verification state.
- **Knowledge Governance Domain:** The highly consistent, transactional domain governing the Institutional Ontology, Hypothesis Lifecycle, Lineage Edges, and Custody Receipts. This domain holds the absolute truth of system state and must mathematically guarantee the prevention of race conditions during governance transitions.
- **Knowledge Preservation Domain:** The terminal repository for finalized, structured scientific artifacts. Assets within this domain are decoupled from their relational metadata and are strictly addressable via their intrinsic logical identity (cryptographic signatures).

## 3. Logical Execution Domains

Execution topology is strictly partitioned to protect out-of-sample integrity and enforce deterministic behavior across all computational environments.

- **Discovery Execution Domain:** An exploratory computational boundary granted read access exclusively to In-Sample partitions within the Knowledge Domains. To prevent epistemological contamination, this domain is subjected to absolute egress isolation; no resultant state may implicitly exit this domain into the institutional canon.
- **Orchestration & Control Domain:** The centralized, determinism-enforcing control plane. It holds responsibility for translating defined research DAGs into isolated execution contexts, injecting deterministic parameters, maintaining operational causality, and recording the execution lineage.
- **Validation Execution Domain:** A highly restricted, ephemeral computational boundary. This domain possesses exclusive contractual authority to access Out-of-Sample partitions for structural simulation and falsification testing. Execution units within this domain must be entirely stateless, existing only for the exact duration of the evaluation contract, after which both the state and the execution unit are logically annihilated.

## 4. Logical Artifact Architecture

Outputs within the system are never modeled as arbitrary files or unstructured data. Every resultant scientific entity is structurally mandated to be a Canonical Artifact Bundle, which acts as the universal unit of knowledge transfer.

Every Artifact Bundle must natively encapsulate:

1. **Logical Payload:** The abstract, mathematically deterministic result of the execution.
2. **Ontological Manifest:** The formal semantic descriptors mapping the payload explicitly to the L3 Data Ontology.
3. **Lineage Envelope:** The unbroken causal graph detailing the precise inputs, execution context, and dependencies responsible for the payload.
4. **Identity Signature:** A deterministic, cryptographic identifier derived from the absolute entirety of the Payload, Manifest, and Lineage. This signature acts as the immutable primary key for the artifact across all domains.

## 5. Logical Instruction Repositories

The definitions of system behavior and scientific inquiry are isolated into distinct structural boundaries to prevent the conflation of infrastructure logic with scientific hypothesis.

- **Platform Instruction Domain:** The logical repository containing the core engine abstractions, deterministic rulesets, and governance enforcement mechanisms. Changes here alter the fundamental "laws of physics" of the research platform and require supreme institutional authorization.
- **Structural Instruction Domain:** The strictly versioned repository holding the mathematical abstractions of the research pipeline (e.g., Feature definitions). This domain is strictly append-only; historical definitions are logically frozen, and refinements demand entirely new identities to preserve reproducibility.
- **Theoretical Instruction Domain:** The operational space where researchers formally define Economic Mechanisms, Hypotheses, and Experimental parameters. This domain depends on the Structural Domain but is entirely subordinate to the Platform Domain's constraints.

## 6. Epistemological Boundaries

Security in this architecture is not defined by traditional access control, but by the structural preservation of scientific validity and custody.

- **The Custody Fence:** A structural and operational partition mandating that exploratory algorithms cannot mathematically reach reserved verification data.
- **Systemic Operational Identity:** Validation executions must operate under autonomous, non-human systemic identities. No human actor, regardless of organizational authority, possesses the logical capability to directly view or interact with the validation data plane.
- **Custody Policy Interceptors:** Every logical interaction attempting to read from a Knowledge Domain must traverse a contractual interceptor. The interceptor's sole responsibility is to instantly deny access unless presented with a mathematically valid, unexpired Custody Receipt issued by the Knowledge Governance Domain.

## 7. Logical Deployment Boundaries

- **Ingress Isolation:** The boundary where external observations are synthesized. This pipeline is fully decoupled from the core research domains. Observations are staged, verified, and deterministically stamped before being formally admitted to the Knowledge Acquisition Domain.
- **Egress Air-Gap:** The computational domains are logically severed from external state changes. All dependency resolutions must be statically defined and routed through internally controlled, immutable proxy registries.
- **The Capital Boundary:** The ultimate, unidirectional logical gateway separating the Research Operating System from the institutional Production/Trading Operating System. Artifacts may only cross this boundary upon achieving the status of Accepted Knowledge, passing through a rigidly defined, asynchronous promotion contract.

## 8. Reference Interaction Model

This section defines the mandatory logical contracts between major architectural domains.

**Interaction 1: Research Domain ↔ Knowledge Acquisition/Processing Domain**

- Purpose: Epistemological exploration and discovery feature engineering.
- Direction: Read-only from Knowledge; strictly constrained Write-only to Discovery buffers.
- Required Contract: In-Sample Custody Receipt.
- Required Lineage: Read events mathematically logged to the user's execution identity.
- Failure Behaviour: Instant isolation of the execution thread; no data is returned.

**Interaction 2: Orchestration Domain ↔ Validation Domain**

- Purpose: Execution of the formal Validation Framework (CSCV, Falsification).
- Direction: Bidirectional (Orchestration injects context → Validation returns Terminal Payload).
- Required Contract: Ephemeral Systemic Identity Token; Valid Out-of-Sample Custody Receipt.
- Required Lineage: Full Context Graph injection; Deterministic Seed capture.
- Failure Behaviour: Payload annihilated; deterministic execution failure recorded to the Knowledge Governance Domain.

**Interaction 3: Knowledge Governance Domain ↔ Validation Domain**

- Purpose: Verification of custody and ontological state prior to execution.
- Direction: Query/Response.
- Required Contract: State query must match the L3 Ontology transition matrices.
- Failure Behaviour: Complete halt of the Validation execution; invalid transition attempted.

**Interaction 4: Knowledge Governance Domain ↔ Capital Boundary**

- Purpose: Promotion of Accepted Knowledge to live market deployment.
- Direction: Unidirectional (Push from Governance to Capital).
- Required Contract: Fully satisfied Peer Review Sign-Off; Complete Cryptographic Lineage Envelope.
- Required Governance: Final CRO institutional cryptographic signature.
- Failure Behaviour: Promotion is structurally blocked; alert issued to Governance oversight.

## 9. Implementation Conformance Rules

Any L6 or L7 physical implementation claiming conformity to the Institutional Research OS MUST mathematically and structurally obey the following architectural obligations:

1. **Lineage Immutability Obligation:** The implementation shall natively reject any operation (logical or physical) that attempts to mutate, truncate, or overwrite a finalized Lineage Envelope or Failure Library Entry.
2. **Execution Determinism Obligation:** The implementation shall guarantee that execution schedulers, resource allocators, and operational environments inject zero temporal, localized, or systemic variance into the computational payload.
3. **Custody Preservation Obligation:** The implementation shall structurally partition memory and processing contexts such that concurrent execution boundaries share zero observable state. Custody boundaries must be enforced at the lowest possible layer of the execution environment.
4. **Logical State Serialization Parity:** The implementation shall enforce a standardized, deterministic memory and payload layout to guarantee that identical scientific inputs yield exactly identical identity signatures, irrespective of the physical execution hardware.
5. **Ontological Inviolability:** No implementation may bypass, extend, or alter the semantic definitions dictated by the L3 Data Ontology. Data structures must remain subservient to the logical ontology.

## 10. Architecture Review Appendix

**Architectural Status: VERIFIED**

- **Architectural Decisions Retained:** The fundamental tripartite execution model (Discovery, Orchestration, Validation), the rigorous custody model, the strict separation of In-Sample/Out-of-Sample, and the unidirectional Capital Boundary.
- **Architectural Decisions Refined:** Storage has been strictly elevated to "Knowledge Domains." Execution environments are now purely "Logical Domains" rather than hardware/deployment locales.
- **Implementation Leakages Removed:** All references to Parquet, Protobuf, ACID, SQL, Cloud, Containerization, specific hashing algorithms (SHA/BLAKE), Blob vaults, physical message buses, and API paradigms (REST) have been annihilated.
- **Abstraction Improvements:** Artifacts are now defined by their inherent cryptographic/logical identity rather than physical file properties. Security is framed entirely as Epistemological Boundary enforcement rather than network security.
- **Layer Boundary Verification:**
  - **L4/L5 Separation:** L4 maintains the laws of physics (state machines, semantics). L5 maintains the topology and contracts (where logic lives and how boundaries interact).
  - **L5/L6 Separation:** L5 contains zero vendor, technology, or protocol specifications. The choice of how to physically build the Knowledge Governance Domain (e.g., using a specific RDBMS or Graph Database) is formally delegated to L6.

> *Governance note at ingestion: the "VERIFIED" status above is the source document's own self-assessment, preserved verbatim. It does not constitute independent review (see Review Status in the header).*
