# L4 Runtime Architecture Specification — Institutional Research OS

**Title:** L4 Runtime Architecture Specification — Institutional Research OS
**Document ID:** `RUNTIME_ARCHITECTURE` (canonical wikilink name)
**Version:** 1.0 · **Status:** **Canonical** — ratified by the Owner 2026-07-17 (**D-027**; layer name adjudicated under **D-025**). **Not frozen:** independent review pending ([[ARCHITECTURE_SPECIFICATION_INDEX]] RN-4) and inherits Phase A pending G-8. See [[GOVERNANCE_BASELINE_v1]].
**Owner:** Chief Systems Architect (self-declared in source)
**Review Status:** None yet — no independent review has occurred (ASI RN-4). Single generation pass; the refinement pass applied to L5 was never applied here (ASI RN-7 — implementation-flavored references retained unmodified below: "Kahn's Algorithm or DFS", "Pub/Sub abstraction", "IFeatureNode", "Float math"). **Independent review commissioned per D-027; RN-7 cleanup ideally precedes it.**
**Layer:** L4 — Runtime Architecture *(**name ratified under D-025**, transcript scheme adopted. Observation retained for reference: this document's scope additionally spans concerns the prior ratified vocabulary assigned to L5–L8 — see [[LAYER_MAPPING_TABLE]] §2.)*
**Dependencies:** [[DATA_ONTOLOGY]] (the ontology this runtime executes) · [[RESEARCH_OPERATING_MODEL]] (gates G1–G4) · [[CUSTODY_MODEL]] (custody policy) · [[RESEARCH_VALIDATION_FRAMEWORK]] (PBO/DSR) · [[HYPOTHESIS_LIFECYCLE]] · [[01_SCIENTIFIC_FOUNDATION]] (F1–F9)
**Last Updated:** 2026-07-16 (transcript date) · **Ingested:** 2026-07-16
**Related Documents:** [[REFERENCE_ARCHITECTURE]] (downstream) · [[EXECUTION_SEMANTICS]] (Withdrawn elaboration — see its header) · [[ARCHITECTURE_SPECIFICATION_INDEX]] §2.5

> **Provenance.** Ingested verbatim from `docs/L3 Data Ontology Specification.pdf` (transcript export, created 2026-07-16 13:35 WIB), pages 4–12. Layout normalized to markdown (the §10 transition matrix reconstructed from the PDF table layout); page headers, transcript URLs, and commissioning prompts removed. **No wording altered.**

---

**Layer:** L4 — Runtime Architecture Specification · **Status:** Canonical Logical Specification · **Owner:** Chief Systems Architect *(source self-declaration, preserved)*

This document specifies the abstract, implementation-independent runtime architecture that executes the L3 Data Ontology. It establishes the deterministic, reproducible engine required to transition theoretical semantic entities into computed, validated institutional knowledge. No database, programming language, or cloud vendor is specified; this is the pure logical machine.

## 1. Runtime Principles

The Institutional Research OS Runtime is governed by ten absolute principles:

1. **Deterministic Execution:** Identical initial conditions, inputs, and algorithmic structures must produce bit-identical outputs and conclusions across hardware and time.
2. **Immutable Inputs:** Once bound to a runtime execution, an input dataset, feature specification, or configuration parameters can never be modified.
3. **Complete Lineage Preservation:** Every state transition and computed artifact must embed a cryptographic pointer to its complete history (the Provenance Envelope).
4. **Reproducibility by Construction:** Reproducibility is not an after-the-fact test; it is syntactically enforced by the runtime refusing to execute unversioned or unpinned assets.
5. **Idempotent Execution:** Repeated execution of any pipeline stage must yield identical artifacts and state transitions without duplicate side effects.
6. **Stateless Computation:** Compute nodes retain no memory across execution boundaries; all state is explicitly passed in or hydrated from immutable stores.
7. **Explicit Dependency Resolution:** No implicit dependencies are permitted. Every input, down to the random seed and environmental math library, must be declared and resolved prior to execution.
8. **Audit-First Design:** State changes do not occur unless the corresponding audit and lineage events are simultaneously committed.
9. **Failure Transparency:** A scientific failure (e.g., statistical invalidation) is a primary knowledge product. It is captured, classified, and persisted with the exact same rigor as a success.
10. **Version Isolation:** The runtime supports simultaneous execution of multiple ontological versions without namespace or memory collisions.

## 2. Runtime Components

The execution environment is composed of specialized logical engines.

**Dataset Registry & Resolver**

- Responsibilities: Indexes all available raw and processed datasets; resolves abstract data requests into specific, immutable cryptographic fingerprints.
- Inputs: Temporal bounds, domain filters, ontology tags.
- Outputs: Dataset Fingerprint, Physical access URI.
- Invariants: Cannot resolve datasets lacking a verifiable hash.
- Lifecycle: Discovers → Indexes → Resolves → Deprecates.

**Custody Manager**

- Responsibilities: Enforces the epistemological boundary (In-Sample vs. Out-of-Sample). Issues cryptographic Custody Receipts for access.
- Inputs: Accessor identity, Dataset Fingerprint, Hypothesis ID (Purpose).
- Outputs: Custody Receipt.
- Invariants: Denies OOS access unless a valid, pre-registered experiment receipt is provided.

**Feature Dependency Resolver**

- Responsibilities: Parses a target feature, walks its dependency tree, and produces a strictly ordered execution DAG.
- Inputs: Feature Definition (S5).
- Outputs: Topological Execution Graph, detected cycles (errors).
- Invariants: Rejects cyclic dependencies; rejects unpinned upstream nodes.

**Feature Computation Engine**

- Responsibilities: Executes the resolved DAG against hydrated data to produce point-in-time feature vectors.
- Inputs: Dataset, Execution Graph, Custody Receipt.
- Outputs: Computed Feature Vector (immutable artifact).
- Invariants: Must execute in a stateless container; outputs must be deterministically reproducible.

**Experiment Orchestrator**

- Responsibilities: Wraps the Hypothesis, Features, and Data into an isolated execution envelope (Run ID). Manages seed injection and resource dispatch.
- Inputs: Hypothesis Object, Feature Vectors, Run Configuration.
- Outputs: Experiment Object.
- Lifecycle: Scheduled → Provisioned → Executing → Completed → Reclaimed.

**Strategy Evaluation Engine**

- Responsibilities: Simulates the economic mechanism against market friction models (slippage, latency, fees).
- Inputs: Experiment Object, Cost Models.
- Outputs: Raw performance vectors, Trade logs.
- Invariants: Cannot access future data points (strict look-ahead prohibition).

**Statistical Validation Engine**

- Responsibilities: Applies rigorous combinatorially symmetric cross-validation (CSCV) and multiple-testing adjustments (FDR, PBO, DSR).
- Inputs: Raw performance vectors.
- Outputs: Validation Report (Draft).
- Invariants: Operates purely mathematically; oblivious to the underlying economic narrative.

**Failure Capture Engine**

- Responsibilities: Traps falsifications, out-of-bounds metrics, or infrastructure crashes, formatting them for the Failure Library.
- Inputs: Failed Validation Reports, Runtime Exceptions, Falsification Criteria (F1-F9).
- Outputs: Failure Library Entry.
- Invariants: Scientific failures must extract the reason for failure against registered a priori assumptions.

**Decision Engine & Governance Controller**

- Responsibilities: Evaluates Validation Reports against institutional gates (G1-G4) and registers human peer-review overrides or approvals.
- Inputs: Validation Report, Peer Review Sign-offs.
- Outputs: Final Gate Decision.
- Invariants: Automated gates cannot be bypassed by human override; human gates cannot be bypassed by automated thresholds.

**Provenance Recorder & Lineage Engine**

- Responsibilities: Binds the (`run_id`, `dataset_fingerprint`, `code_commit`) into an unbreakable envelope for every artifact.
- Inputs: Component telemetry, Object IDs.
- Outputs: Lineage Edges.
- Invariants: Lineage writing is synchronous and atomic with artifact creation.

**Artifact Registry & Publication Pipeline**

- Responsibilities: Elevates validated experiment outputs into the Accepted Knowledge base or production serving layer.
- Inputs: Finalized Knowledge Object.
- Outputs: Capital-facing Publication.
- Invariants: Cannot publish without an unbroken lineage chain tracing back to a registered hypothesis.

## 3. Runtime Object Lifecycle

**Dataset**

- Registered: Metadata indexed, physical location mapped.
- Verified: Hashed and schema-validated.
- (Immutable Checkpoint) → Frozen: Cryptographic fingerprint locked.
- Referenced: Actively bound to a Custody Receipt.
- Archived: Cold storage, hash preserved for backward reproduction.
- Illegal Transition: Frozen → Verified (Datasets cannot be mutated once frozen).

**Hypothesis**

- Draft: In formulation (In-Sample exploration).
- Registered: Submitted for Gate G1 (Falsifiability).
- (Immutable Checkpoint) → Active: Locked for testing. Parameters cannot be changed.
- Evaluated: Paired with a Validation Report.
- Accepted / Rejected: Terminal institutional state.
- Archived: Replaced by superseding hypothesis.
- Illegal Transition: Evaluated → Active (Requires new Hypothesis ID to prevent HARKing).

**Experiment**

- Created: Bound to Hypothesis and Dataset.
- Scheduled: Queued in Orchestrator.
- Executing: Runtime processing.
- (Immutable Checkpoint) → Completed: Raw outputs finalized.
- Validated: Validation Engine outputs attached.
- Published: Elevated to Knowledge/Failure Library.
- Illegal Transition: Validated → Executing.

## 4. Runtime Execution Graph

The canonical forward-pass execution pipeline:

1. **Research Question:** Unstructured literature discovery.
2. ↓ **Hypothesis Registration (Gate G1):** Formal semantic object created; metrics defined.
3. ↓ **Dataset Resolution:** Abstract data requirements mapped to concrete, hashed data partitions.
4. ↓ **Custody Verification:** Custody Manager issues receipts for In-Sample/OOS access.
5. ↓ **Feature Resolution:** DAG constructed from S5 Feature Definitions.
6. ↓ **Feature Computation:** Stateless execution of the DAG.
7. ↓ **Experiment Execution:** Mechanism simulation via Strategy Engine.
8. ↓ **Statistical Validation (Gate G3):** PBO, DSR, and falsification thresholds calculated.
9. ↓ **Governance Review (Gate G4):** Peer Review Standard applied; economic causality defended.
10. ↓ **Decision:** Automated branching based on G3/G4 outputs.
11. ↓ **Publication:** Emission to capital boundary (if pass).
12. ↓ **Knowledge Archive:** Registration into Accepted Knowledge or Failure Library.

## 5. Dependency Resolution Model

- **Dependency Graph:** A strictly typed Directed Acyclic Graph (DAG). Nodes are Data or Features; Edges are computations.
- **Topological Ordering:** The Dependency Resolver performs a standard Kahn's Algorithm or DFS sort. Execution is strictly topological from leaf data up to the hypothesis target.
- **Cycle Detection:** Resolved dynamically at graph generation. Cycles trigger an immediate Infrastructure Failure.
- **Version Compatibility:** Semantic versioning is strictly enforced. `FeatureA_v1.0` and `FeatureA_v1.1` occupy distinct memory spaces.
- **Dependency Freezing:** At Experiment Created stage, all upstream dependencies undergo a "deep freeze" traversing all branches down to raw data, logging the `code_commit` of every node.
- **Substitution Policy:** Runtime substitutions (e.g., swapping a mock data source) are strictly illegal during the Executing phase.

## 6. Lineage Runtime

- **Provenance Envelope Generation:** At runtime initialization, a globally unique `Run_ID` is generated. All artifacts produced within this context append `[Run_ID, Code_Hash, Dataset_Hash, Deterministic_Seed]` to their metadata.
- **Forward Trace:** Engine can query: *Given Dataset Hash X, what Experiments consumed it?*
- **Backward Trace:** Engine can query: *Given Accepted Knowledge Y, reconstruct the exact DAG, seeds, and hypothesis used to produce it.*
- **Integrity Verification:** Before a transition to Published, the Lineage Engine performs a cryptographic walk from the terminal artifact back to the Hypothesis. A single missing link halts promotion.

## 7. Failure Runtime

Failures are first-class ontological events, categorized dynamically:

- **Infrastructure Failures:** Compute exhaustion, missing data partitions.
  - Action: Captured, logged, automated retry permitted. No scientific impact.
- **Scientific Failures (Validation):** Falsification thresholds triggered, PBO > 0.5, DSR below zero.
  - Action: No retries. Triggers immutable capture.
- **Custody Failures:** Attempted access to OOS data without a receipt, or look-ahead detected.
  - Action: Experiment poisoned. Triggers immediate escalation to Governance Controller.
- **Persistence:** The Failure Capture Engine maps scientific failures to F1-F9 modes, binds the invalidated assumptions, and persists directly to the Failure Library to prevent redundant future research.

## 8. Runtime Governance

No state transition that crosses an epistemological boundary can occur without Governance Controller authorization.

- **Approval Gates (G1, G4):** Requires asynchronous token injection (simulating human cryptographic sign-off).
- **Freeze Gates (G2):** Automated check affirming that all code dependencies are pinned to immutable commits.
- **Publication Gates (G3):** Automated statistical floor.
- **Audit Checkpoints:** The system periodically triggers asynchronous reconstruction tasks, picking random Knowledge Objects and enforcing reproducible re-execution.
- **Custody Checkpoints:** Ephemeral tokens valid only for the lifecycle of one Experiment phase.

## 9. Runtime Invariants

1. Every experiment must execute against exactly one immutable dataset fingerprint.
2. Every feature must resolve all dependencies topologically before execution begins.
3. Every validation report must reference exactly one immutable experiment.
4. Every published artifact must possess an unbroken lineage trace to a registered hypothesis.
5. Execution may never mutate historical artifacts (Append-Only Law).
6. Out-of-sample execution is physically blocked unless a matching, registered Hypothesis `blind_to` constraint exists.
7. A failed experiment cannot be resumed, only cloned into a new lineage branch.

## 10. Runtime State Machine

Transition Matrix (Subset of Core Moves):

| Current State | Action | Next State | Guard Condition |
|---|---|---|---|
| Hypothesis: Draft | Submit to G1 | Hypothesis: Registered | All required L3 ontology fields present |
| Hypothesis: Registered | CRO Sign-off | Hypothesis: Active | Pre-registered thresholds valid |
| Experiment: Created | Enqueue | Experiment: Scheduled | DAG resolved, Data Frozen |
| Experiment: Scheduled | Dispatch | Experiment: Executing | Custody Receipt verified |
| Experiment: Executing | Yield outputs | Experiment: Completed | Seed logged, deterministic exit |
| Experiment: Completed | G3 Validate | Report: Draft | Idempotent generation |
| Report: Draft | G4 Defense (Pass) | Object: Accepted | Peer Review Sign-off received |
| Report: Draft | G4 Defense (Fail) | Failure: Archived | Invalid assumptions logged |

## 11. Runtime Sequence Diagrams

**Flow: New Experiment Execution**

1. Researcher → Experiment Orchestrator: `Initialize Run(Hypothesis_ID)`.
2. Orchestrator → Dataset Resolver: Fetch Fingerprints.
3. Orchestrator → Custody Manager: Request OOS execution receipt.
4. Custody Manager → Orchestrator: Grant Receipt (if blind condition holds).
5. Orchestrator → Feature Dependency Resolver: Lock DAG.
6. Feature Engine → Strategy Engine: Stream computed feature vectors.
7. Strategy Engine → Provenance Recorder: Commit raw outputs + Envelope.
8. Orchestrator → Statistical Validation Engine: Trigger G3 calculation.

**Flow: Audit Replay**

1. Governance Controller → Lineage Engine: Request backward trace for Publication X.
2. Lineage Engine → Orchestrator: Extract (`Code_Hash`, `Dataset_Hash`, `Seed`).
3. Orchestrator → Compute Engine: Re-run execution in shadow space.
4. Compute Engine → Governance Controller: Yield Shadow Artifact.
5. Governance Controller: Assert `Hash(Shadow Artifact) == Hash(Publication X)`.

## 12. Runtime Extension Model

To preserve institutional agility while freezing the L3 Ontology, the runtime implements a strict Interface-Driven Extension Model:

- **New Feature Families:** Can be added by implementing the `IFeatureNode` contract (Requires inputs, deterministic execution block, topological tags). The Resolver automatically accommodates them.
- **New Validation Engines:** Added via Pub/Sub abstraction. The Orchestrator broadcasts `Experiment.Completed`. A new `RegimeStabilityEngine` can subscribe and append its findings to the Validation Report without altering the core pipeline.
- **Backward Compatibility:** Extensions are purely additive. If an extension schema requires mutation of a Core L3 Object, it is rejected at the architecture level.

## 13. Non-Functional Runtime Requirements

- **Determinism:** Float math execution must be constrained to guarantee exact bit-wise identical outputs across differing hardware topologies.
- **Traceability:** O(1) lookup time for the provenance envelope of any generated artifact.
- **Scalability:** Feature Computation Graph must support horizontal partitioning of execution sub-DAGs.
- **Auditability:** Every component interaction is logged to an immutable write-ahead append-only log.
- **Reliability:** Engine crash during execution must result in a clean teardown; partial states are never committed.
- **Portability:** The entire logical pipeline must be capable of executing on a local researcher machine (In-Sample data only) identical to the institutional cluster.
