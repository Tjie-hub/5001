# L3 Data Ontology Specification — Institutional Research OS

**Title:** L3 Data Ontology Specification: Institutional Research OS
**Document ID:** `DATA_ONTOLOGY` (canonical wikilink name)
**Version:** 1.0 · **Status:** **Canonical** — ratified by the Owner 2026-07-17 (**D-027**; layer confirmed under **D-025**). **Not frozen:** independent review pending ([[ARCHITECTURE_SPECIFICATION_INDEX]] RN-4) and inherits Phase A pending G-8. See [[GOVERNANCE_BASELINE_v1]].
**Owner:** Research Architect *(assigned at ingestion; **confirmed by the Owner 2026-07-17 per D-027**)*
**Review Status:** None yet — no independent review has occurred (ASI RN-4). Single generation pass. **Independent review commissioned per D-027.**
**Layer:** L3 — Data Ontology *(**ratified under D-025**; identical in both schemes — no collision at L3; see [[LAYER_MAPPING_TABLE]])*
**Dependencies:** [[01_SCIENTIFIC_FOUNDATION]] (E/C/X/F/D/M scales) · [[RESEARCH_OBJECT_MODEL]] (anchor object model) · [[CUSTODY_MODEL]] (custody states, receipt fields) · [[HYPOTHESIS_LIFECYCLE]] (lifecycle states) · [[EVIDENCE_MODEL]] (three-axis thesis) · [[LITERATURE_RESEARCH_STANDARD]] (Q-grades, B-flags)
**Last Updated:** 2026-07-16 (transcript date) · **Ingested:** 2026-07-16
**Related Documents:** [[RUNTIME_ARCHITECTURE]] (downstream — executes this ontology) · [[REFERENCE_ARCHITECTURE]] (downstream) · [[ARCHITECTURE_SPECIFICATION_INDEX]] §2.4

> **Provenance.** Ingested verbatim from `docs/L3 Data Ontology Specification.pdf` (transcript export, created 2026-07-16 13:35 WIB), pages 1–3. Layout normalized to markdown; page headers, transcript URLs, and commissioning prompts removed. **No wording altered.** Known content notes carried from the ASI: RN-7 (the `research.tracking` reference below is implementation leakage — retained unmodified because content changes are out of remediation scope).

---

Based on the canonical Phase A (L0–L2) architecture corpus, the L3 Data Ontology formalizes the semantic entities, relationships, and taxonomies that constitute the institutional research pipeline. This ontology is strictly derived from the existing architecture and acts as the universal blueprint for the runtime schemas, independently of their underlying database technology.

## 1. Primary Knowledge Entities (Core Object Model)

The ontology is anchored by the canonical Research Object Model. All entities require unique identifiers (UUIDs or formatted semantic keys).

**Literature Card (S1)**

- `literature_id`: Unique identifier.
- `mechanism_ref`: ID of the mechanism being supplied.
- `quality_grade`: Assessment metric (Q0–Q4).
- `nine_biases`: Boolean flags for the identified biases (B1–B9).
- `transportability_condition`: Critical constraint parameter.
- `weakest_link`: Assessed fragility metric.
- `replication_status`: Degree of historical replication.
- `sub_class_assignment`: Mechanism taxonomy linkage.

**Economic Mechanism (S2)**

- `mechanism_id`: Unique identifier.
- `taxonomy_class`: Base class mapping (M1–M6).
- `causal_chain`: Structured qualitative causal order.
- `competing_explanations`: Asymmetric constraint variables.
- `falsification_criteria`: Falsification modes (F1–F9).

**Research Hypothesis (S3)**

- `hypothesis_id`: Unique identifier.
- `mechanism_ref`: Parent mechanism lineage.
- `lifecycle_state`: Tracks canonical states (T1-T12 / G1-G4).
- `blind_to`: Cognitive isolation constraint marker.

**Dataset Object (S4)**

- `dataset_id`: Unique identifier.
- `dataset_fingerprint`: Cryptographic hash ensuring immutability.
- `custody_state`: Maps to Custody Axis (e.g., in-sample, out-of-sample).

**Feature Definition (S5)**

- `feature_id`: Format `FeatureName_v[Major].[Minor]_[Hash]`.
- `dependencies_array`: Explicit listing of upstream node lineages.
- `code_commit_hash`: Executable lineage.

**Experiment Object (S6)**

- `experiment_id`: Unique identifier.
- `hypothesis_ref`: Hypothesis being evaluated.
- `run_id`: Execution envelope tracker.
- `deterministic_seed`: Value preserving computational bit-identity.

**Validation Report (S7–S8)**

- `report_id`: Unique identifier.
- `experiment_ref`: Targeted experiment.
- `state`: Enum (DRAFT | FINALIZED).
- `pbo_score`: Probability of Backtest Overfitting metric.
- `dsr_score`: Deflated Sharpe Ratio tracking.

**Failure Library Entry**

- `failure_id`: Unique identifier.
- `hypothesis_ref` / `mechanism_ref` / `experiment_ref`: Lineage traceability.
- `failure_reason`: Categorical enumeration (e.g., Insufficient Signal-to-Noise, Destroyed by Transaction Costs).
- `invalid_assumptions`: Structured array of proven-false a priori assumptions.
- `lessons_learned` & `related_features`: Archival feedback nodes.

## 2. Taxonomic Substrates (The Axes of Assessment)

The objects above map directly against three foundational scientific scales established in the L1 Scientific Foundation:

**The Evidence Axis (E, C, X Models)**

- Evidence Tier (E0–E7): Scale of epistemic weight. Accepted knowledge floors at E4.
- Confidence Score (C0–C4): A process-derived metric factoring the counterfactual tests.
- Reproducibility Level (X0–X4): Represents bit-identity and conclusion-invariance.
- Falsification Modes (F1–F9): The diagnostic taxonomy of mechanism invalidation.

**Market Inefficiency Domains**

- Domain Class (D1–D6): Broad categorical classification.
- Mechanism Class (M1–M6): Canonical causal classification. Instances mapping downwards (I1-I12).

**The Custody Model**

- Custody States: Categorical attributes defining epistemological availability.
- Custody Receipt: Cryptographic objects proving data fence integrity. Fields include: `asset_ref`, `accessor`, `purpose_ref`, `ordinal`, and `prior_receipt`.

## 3. Absolute Lineage & Edge Semantics

Lineage is treated as a first-class ontological entity. A knowledge object or library entity is considered non-compliant if it cannot execute a backward trace.

- `hypothesis_links`: Standard relational edge tracking Hypothesis refinement and supersession.
- `provenance_envelope`: Embedded into `research.tracking`, consisting strictly of (`run_id`, `dataset_fingerprint`, `git_commit`) tuples.
- `custody_events`: Immutable transition events logging `from_state -> to_state`, `fingerprint_before/after`, and bound `receipt_ref`.

## Resolution of Structural Ambiguities

- **Blindness Constraints:** The `blind_to` attribute is logged semantically as an assertion flag on the Hypothesis Object, recognizing that physical automation is impossible at N = 1.
- **Custody Realization:** While physical implementation may be pending for specific boundary transitions (e.g., Publication Custody), their semantic edge relationships (`publication_id` → `content_fingerprint` → `dataset_lineage`) are strictly reserved and mandatory for future resolution.
