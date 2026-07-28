# Layer Mapping Table — RN-8 Resolution (P1)

**Status:** Canonical governance record · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** Records the determination of the repository-canonical layer numbering and the disposition of every document affected by the RN-8 collision ([[ARCHITECTURE_SPECIFICATION_INDEX]] §11). Amendable only by owner decision.
**Produced by:** Phase B Governance Remediation — see [[GOVERNANCE_REMEDIATION_REPORT]]

---

## 1. Determination: which scheme is canonical

**The repository-canonical layer numbering is the ratified vocabulary of [[TAXONOMY_AND_NAMING_STANDARD]] §3 (L0–L8).** Reasoning:

1. The Taxonomy & Naming Standard is the corpus's **only document with definitional authority** over layer identifiers: *"The controlled vocabulary of the Research OS. Every other document MUST use these terms with exactly these meanings"* (its header). It is Canonical, L0, and part of the certified Phase A corpus.
2. The competing scheme (L4 = Runtime Architecture, L5 = Reference Architecture, L6 = Technology Profiles) originates in the 2026-07-16 transcript (`docs/L3 Data Ontology Specification.pdf`). It is a genuine **owner decision in intent**, but it has never been transacted into the repository: no [[DECISION_LOG]] entry, no taxonomy amendment, no version bump. Under the corpus's own integrity rules (explicit supersession, recorded decisions), an unratified transcript statement cannot displace a ratified standard.
3. The two schemes **agree on L0–L3** and diverge only at L4 and above.

**Consequence:** the documents violating the canonical vocabulary are the newly ingested specifications (which self-declare transcript-scheme identifiers), **not** the Phase A documents. The three L2 dual-labels flagged in ASI RN-8 are *compliant* with the ratified vocabulary; RN-8's "collision" is hereby re-characterized: the ASI treated the transcript scheme as the corpus structure, which overstated its governance status.

**The intended end-state is still the transcript scheme** — the owner commissioned L4 Runtime and L5 Reference under it. The ratification path is drafted as proposed decision **D-025-P** in [[GOVERNANCE_REMEDIATION_REPORT]] §4. Until the owner ratifies it, the ratified L0–L8 vocabulary stands.

## 2. Scheme mapping: Old (ratified) ↔ Transcript (proposed)

| Identifier | Ratified scheme (TAXONOMY §3) | Transcript scheme | Mapping status |
|---|---|---|---|
| L0 | Governance & Scope | "Vision" (informal, in prompts only) | **Agree** on identifier; "Vision" never adopted on disk (ASI RN-1) |
| L1 | Scientific Foundation | Scientific Foundation | **Identical** |
| L2 | Research Architecture | Research Architecture | **Identical** |
| L3 | Data Ontology | Data Ontology | **Identical** — no collision at L3 |
| L4 | Research Infrastructure (storage, compute, metadata, versioning) | Runtime Architecture | **Identifier matches, name differs.** The Runtime spec covers the L4-slot concerns (registries=storage, engines=compute, lineage=metadata, version isolation=versioning) **and additionally spans ratified L5–L8 concerns** (Feature Computation Engine→old L5; hypothesis registration→old L6; Statistical Validation Engine→old L7; Artifact Registry/Failure capture→old L8) |
| L5 | Feature Computation (FCG realization) | Reference Architecture | **INCOMPATIBLE.** No ratified slot holds a Reference Architecture; ratified L5 is a functional layer, transcript L5 is an abstraction stratum. The schemes are different *kinds* of decomposition (function vs. abstraction level) — this is the root of RN-8 |
| L6 | Hypothesis Engine | Technology Profiles | **INCOMPATIBLE** (same reason) |
| L7 | Validation Framework | — (physical implementation, mentioned in passing as "L6/L7") | Collision if transcript scheme extends |
| L8 | Knowledge Repository | — | Ratified only |

## 3. Per-document disposition

| Document | Layer label(s) borne | Old → Canonical | Header updated? | Cross-references updated? |
|---|---|---|---|---|
| [[DATA_ONTOLOGY]] (ingested) | self-declared L3 | L3 → **L3** (schemes agree) | **YES** — header states L3 with no-collision annotation | YES — dependency wikilinks added in metadata only; body untouched |
| [[RUNTIME_ARCHITECTURE]] (ingested) | self-declared L4 | transcript-L4 → **L4 identifier valid; layer *name* contested** (Research Infrastructure vs Runtime Architecture) | **YES** — header carries self-declared label + ratified-vocabulary annotation + span observation; final name awaits D-025-P | YES — metadata only |
| [[REFERENCE_ARCHITECTURE]] (ingested) | self-declared L5 | transcript-L5 → **NO ratified slot — CONTESTED** | **YES** — header carries self-declared label + explicit CONTESTED marker pending D-025-P | YES — metadata only |
| [[REFERENCE_ARCHITECTURE_DRAFT]] (ingested, Superseded) | self-declared L5 | same as above | **YES** — same contested annotation | YES — metadata only |
| [[EXECUTION_SEMANTICS]] (ingested, Withdrawn) | self-declared L4.5 | withdrawn — L4.5 exists in **neither** scheme | **YES** — header records the designation as withdrawn with the document | YES — metadata only |
| [[FEATURE_COMPUTATION_GRAPH]] (L2, Phase A) | "L2 / L5 — Feature Computation" | Compliant with ratified vocabulary — **no change required under the canonical determination.** Becomes stale only if D-025-P ratifies the transcript scheme | **NO — not needed today; additionally BLOCKED** (Phase A file, hard constraint). Flagged for the D-025-P execution checklist | NO — none required |
| [[RESEARCH_VALIDATION_FRAMEWORK]] (L2, Phase A) | "L2 / L7 — Validation" | Same | **NO — same** | NO |
| [[FAILURE_LIBRARY_SCHEMA]] (L2, Phase A) | "L2 / L8 — Knowledge Repository" | Same | **NO — same** | NO |
| [[RESEARCH_OS_MASTER_ROADMAP]] §2 + diagram (L0, Phase A) | full old-scheme table L0–L8 | Compliant with ratified vocabulary | **NO — same** | NO |
| [[FUTURE_GOVERNANCE_OUTLINES]] (L0, Phase A) | "target Layer L4" (= Research Infrastructure) | Compliant with ratified vocabulary; target label becomes ambiguous under D-025-P | **NO — same** | NO |
| [[TAXONOMY_AND_NAMING_STANDARD]] §3 (L0, Phase A) | defines the ratified list | **This is the canonical source.** D-025-P would amend it (v1.0 → v2.0) | **NO — it is the standard, and a Phase A file** | NO |
| [[ARCHITECTURE_SPECIFICATION_INDEX]] (L0, baseline) | uses transcript scheme in §1 | The ASI is the frozen review baseline for this remediation — deltas recorded here, not edited into it | **NO — baseline preserved untouched by instruction** | NO — this table is the correction record |

## 4. Residual actions (owner)

1. **Decide D-025-P** ([[GOVERNANCE_REMEDIATION_REPORT]] §4): ratify the transcript scheme (amending TAXONOMY §3 and updating the five Phase A labels above), **or** retain the ratified L0–L8 scheme (requiring the three ingested specs to be re-slotted/renamed by their owners). Either outcome is mechanical once decided; both option checklists are in the report.
2. Until decided: cite layers L0–L3 freely (schemes agree); qualify any citation of "L4"/"L5" with the document name to avoid ambiguity.
