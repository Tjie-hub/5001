# Document Registry Update — Phase B Governance Remediation

**Status:** Canonical governance record · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** Registry of the architecture corpus after ingestion of the transcript-only documents, with the P3 governance-completion verification for every ingested document.
**Produced by:** [[GOVERNANCE_REMEDIATION_REPORT]]

---

## 1. Registry delta (what this remediation added)

| Document ID | Path | Layer | Status | New/Existing |
|---|---|---|---|---|
| `DATA_ONTOLOGY` | `docs/research_os/DATA_ONTOLOGY.md` | L3 | Canonical (candidate) | **NEW** (ingested from PDF pp. 1–3) |
| `RUNTIME_ARCHITECTURE` | `docs/research_os/RUNTIME_ARCHITECTURE.md` | L4 (name contested) | Canonical (candidate) | **NEW** (ingested from PDF pp. 4–12) |
| `REFERENCE_ARCHITECTURE` | `docs/research_os/REFERENCE_ARCHITECTURE.md` | L5 (contested) | Canonical (candidate) | **NEW** (ingested from PDF pp. 25–30, refined version) |
| `REFERENCE_ARCHITECTURE_DRAFT` | `docs/archive/REFERENCE_ARCHITECTURE_DRAFT.md` | L5 (contested) | **Superseded** | **NEW** (ingested from PDF pp. 20–23) |
| `EXECUTION_SEMANTICS` | `docs/archive/EXECUTION_SEMANTICS.md` | L4.5 (withdrawn) | **Withdrawn** | **NEW** (ingested from PDF pp. 14–19) |

Placement rationale: `research_os/` is the concern-named folder for Research OS architecture documents (TAXONOMY §7: *"folders are concern-named, never `L1/`"*); `archive/` follows the corpus precedent set by `RESEARCH_MASTER_PLAN_v2.md` for non-active documents. The source PDF `docs/L3 Data Ontology Specification.pdf` is retained unmodified as the provenance original.

The full pre-existing registry (L0: 6 docs + governance records; L1: 5 docs; L2: 15 docs) is unchanged and remains as cataloged in [[ARCHITECTURE_SPECIFICATION_INDEX]] §2.1–§2.3.

## 2. P3 Governance-completion verification (per ingested document)

| Check | DATA_ONTOLOGY | RUNTIME_ARCHITECTURE | REFERENCE_ARCHITECTURE | REFERENCE_ARCHITECTURE_DRAFT | EXECUTION_SEMANTICS |
|---|---|---|---|---|---|
| Unique Document ID | ✓ (wikilink name, unique in corpus) | ✓ | ✓ | ✓ | ✓ |
| Unique Layer assignment | ✓ L3 (schemes agree) | **△** L4 identifier unique; layer *name* contested pending D-025-P | **✗ CONTESTED** — no ratified slot; unresolvable without D-025-P | n/a (Superseded — layer inherited from successor's resolution) | n/a (Withdrawn) |
| Owner assigned | ✓ (assigned at ingestion, confirmation pending — source declared none) | ✓ (self-declared) | ✓ (self-declared) | ✓ | ✓ |
| Version assigned | ✓ 1.0 | ✓ 1.0 | ✓ 1.0 | ✓ 0.1 | ✓ 0.1 |
| Review status assigned | ✓ (None — honestly recorded) | ✓ (None) | ✓ (Self-pass only) | ✓ (Failed boundary test) | ✓ (None, withdrawn pre-review) |
| Dependency list present | ✓ | ✓ | ✓ | ✓ | ✓ |
| No duplicated concepts | ✓ formalizes L2 objects, does not restate them | ✓ references L3/L2, defines only runtime | ✓ references L4/L3, defines only topology | ✓ (superseded duplicate of successor — permitted as history) | **△** overlaps L4 by design — this is *why* it was withdrawn; content preserved as history per P5 |

**Notes on non-passing cells (nothing hidden):**
- `REFERENCE_ARCHITECTURE` layer assignment **fails** strict uniqueness until the owner decides D-025-P. This is not repairable by governance remediation: assigning it a ratified slot would require either amending the taxonomy (Phase A file — forbidden) or re-slotting the document (an architecture judgment — forbidden).
- `RUNTIME_ARCHITECTURE`'s span across ratified L4–L8 concerns is recorded in its header and in [[LAYER_MAPPING_TABLE]] §2 as a factual observation, not adjudicated.

## 3. ID uniqueness sweep (whole corpus)

Document ID = canonical wikilink name (the corpus's existing addressing scheme — no new ID scheme invented). A filename-collision sweep across `governance/`, `research_os/`, `roadmap/`, `Phase_A_Scientific_Foundation/`, `archive/` found **zero duplicate basenames** after ingestion (50 pre-existing + 5 ingested + 6 remediation records = 61 total IDs). The corpus has no numeric document-ID scheme; introducing one would be a new governance concept and is left to the owner.
