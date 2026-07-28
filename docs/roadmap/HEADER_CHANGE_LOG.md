# Header Change Log — Phase B Governance Remediation

**Status:** Canonical governance record · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** Complete log of every document header created or modified during the Phase B governance remediation. Point-in-time record.
**Produced by:** [[GOVERNANCE_REMEDIATION_REPORT]]

---

## 1. Headers CREATED (new files — full standardized metadata assigned at ingestion)

| # | File | Title | ID | Version | Status | Owner | Review Status | Layer |
|---|---|---|---|---|---|---|---|---|
| 1 | `docs/research_os/DATA_ONTOLOGY.md` | L3 Data Ontology Specification | `DATA_ONTOLOGY` | 1.0 | Canonical (candidate; unratified pending D-025-P) | Research Architect *(assigned at ingestion — source declared none, RN-6; confirmation pending)* | None | L3 (schemes agree) |
| 2 | `docs/research_os/RUNTIME_ARCHITECTURE.md` | L4 Runtime Architecture Specification | `RUNTIME_ARCHITECTURE` | 1.0 | Canonical (candidate; unratified pending D-025-P) | Chief Systems Architect (self-declared) | None | L4 (identifier valid; name contested) |
| 3 | `docs/research_os/REFERENCE_ARCHITECTURE.md` | L5 Reference Architecture Specification (refined) | `REFERENCE_ARCHITECTURE` | 1.0 | Canonical (candidate; unratified pending D-025-P) | Chief Enterprise Architect (self-declared) | Self-refinement pass only (not independent) | L5 (CONTESTED) |
| 4 | `docs/archive/REFERENCE_ARCHITECTURE_DRAFT.md` | L5 Reference Architecture (pre-refinement draft) | `REFERENCE_ARCHITECTURE_DRAFT` | 0.1 | **Superseded** (by REFERENCE_ARCHITECTURE v1.0) | Chief Enterprise Architect | Failed L5/L6 boundary test (leakage) | L5 (CONTESTED) |
| 5 | `docs/archive/EXECUTION_SEMANTICS.md` | L4.5 Execution Semantics Specification | `EXECUTION_SEMANTICS` | 0.1 | **Withdrawn** (owner decision in transcript; ratification D-026-P pending) | Chief Systems Architect (self-declared) | None (withdrawn pre-review) | L4.5 (withdrawn designation) |

All five headers carry the full required metadata set: Title · Document ID · Version · Status · Owner · Review Status · Layer · Dependencies · Last Updated · Related Documents, plus a Provenance block naming the source PDF and pages.

## 2. Headers MODIFIED in existing files

**None.** Zero existing files were modified. In particular:

| Candidate flagged by ASI RN-8 | Action taken | Reason |
|---|---|---|
| `FEATURE_COMPUTATION_GRAPH.md` header ("L2 / L5") | **Not modified** | Compliant with the ratified vocabulary ([[LAYER_MAPPING_TABLE]] §1); also a Phase A file (hard constraint) |
| `RESEARCH_VALIDATION_FRAMEWORK.md` header ("L2 / L7") | **Not modified** | Same |
| `FAILURE_LIBRARY_SCHEMA.md` header ("L2 / L8") | **Not modified** | Same |
| `RESEARCH_OS_MASTER_ROADMAP.md` §2 | **Not modified** | Same |
| `FUTURE_GOVERNANCE_OUTLINES.md` | **Not modified** | Same |
| `TAXONOMY_AND_NAMING_STANDARD.md` §3 | **Not modified** | It is the canonical vocabulary source and a Phase A file; amendment path is D-025-P |
| `ARCHITECTURE_SPECIFICATION_INDEX.md` | **Not modified** | Declared the authoritative review baseline for this remediation; corrections recorded in [[LAYER_MAPPING_TABLE]] instead |

## 3. Status values in force (P5)

Draft · Review · Canonical · Superseded · Withdrawn · Archive — as required. Assignments: three Canonical (candidate), one Superseded, one Withdrawn. No document was deleted; complete history is preserved (the source PDF remains in place untouched as the provenance original).
