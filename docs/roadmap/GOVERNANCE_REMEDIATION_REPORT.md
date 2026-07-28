# Governance Remediation Report — Phase B (Post-ASI-Review)

**Status:** Canonical governance record · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** Master record of the Phase B governance remediation executed against the [[ARCHITECTURE_SPECIFICATION_INDEX]] Review Notes (RN-1…RN-10). Records what was remediated, what is blocked and why, and the proposed decisions awaiting the owner. Point-in-time; superseded rather than edited.
**Baseline:** [[ARCHITECTURE_SPECIFICATION_INDEX]] v1.0 (authoritative review baseline — preserved untouched)
**Hard constraints honored:** no Phase A file modified · no technical architecture modified · no scientific content modified · no new concepts · nothing committed

---

## 1. Executive summary

| | |
|---|---|
| **Remediated in full** | RN-2 (PDF-only medium), RN-5 (two L5 versions), RN-6 (missing headers), RN-10 (L4.5 withdrawal undocumented) |
| **Remediated at governance level; final ratification with owner** | RN-8 (layer numbering — canonical scheme determined, mapping table issued, taxonomy amendment drafted as D-025-P), RN-3 (missing decision records — three decisions drafted as D-025-P/D-026-P/D-027-P; the [[DECISION_LOG]] is a Phase A file and cannot be written by this remediation) |
| **Recorded, out of remediation scope by constraint** | RN-1 (Vision naming — Phase A docs), RN-4 (review asymmetry — needs actual reviewers, not documentation), RN-7 (implementation leakage — content change forbidden), RN-9 (fence naming — content change forbidden) |
| **Files created** | 5 ingested documents + 6 governance records (this report and its five companions) |
| **Files modified** | **ZERO** |
| **Phase B freeze** | **BLOCKED** — see [[FREEZE_READINESS_REPORT]] |

## 2. A constraint conflict in the brief, and how it was resolved

The remediation brief simultaneously required *"Update every affected document header"* (P1) and *"DO NOT modify any Phase A document / No Phase A file changed"* (hard constraints, final verification). Under the ASI's original RN-8 framing, every affected header lived in a Phase A file — the two instructions would be unsatisfiable together.

The conflict dissolved on determining the canonical scheme ([[LAYER_MAPPING_TABLE]] §1): **the repository's ratified vocabulary is [[TAXONOMY_AND_NAMING_STANDARD]] §3 (L0–L8)**, so the Phase A dual-labels are *compliant* and need no edit today; the non-compliant headers were those of the un-ingested transcript documents, which this remediation authored fresh (P2) with correct governance annotations. Hard constraints were therefore honored **without** leaving P1 unexecuted. The ASI's RN-8 framing is formally corrected in [[LAYER_MAPPING_TABLE]] §1 (the baseline itself is preserved unedited).

## 3. Review Note dispositions (complete)

| RN | Finding | Disposition |
|---|---|---|
| RN-1 | "L0 Vision" vs "Governance & Scope" | **RECORDED — no action possible.** Canonical name is on-disk "Governance & Scope"; the ASI already indexes it. Renaming/aliasing would touch Phase A docs. |
| RN-2 | L3–L5 PDF-only | **RESOLVED.** Five documents ingested as repository markdown with full standardized metadata ([[HEADER_CHANGE_LOG]] §1); wording preserved verbatim; source PDF retained as provenance original. |
| RN-3 | No decision records for L3–L5 | **PARTIALLY RESOLVED.** Three decisions drafted ready-to-ratify (§4 below). Writing them into [[DECISION_LOG]] requires modifying a Phase A file — reserved to the owner. |
| RN-4 | Review asymmetry (L3/L4 zero reviews; L5 self-pass only) | **RECORDED in every ingested header** (honest Review Status fields). Not documentable away — requires actual independent review. Queued in [[FREEZE_READINESS_REPORT]]. |
| RN-5 | Two L5 versions, supersession unrecorded | **RESOLVED.** Draft ingested at `docs/archive/` with Status **Superseded** and explicit successor pointer; refined version carries `Supersedes:` header. Only [[REFERENCE_ARCHITECTURE]] may be cited as canonical. |
| RN-6 | Missing headers (L3 no owner; no versions anywhere) | **RESOLVED.** All five ingested docs carry the full metadata set. L3's owner assigned per corpus role pattern (Research Architect) with an explicit confirmation-pending annotation — the one metadata judgment this remediation made, flagged rather than hidden. |
| RN-7 | Implementation leakage in L3/L4 | **RECORDED, retained unmodified** (content changes forbidden by both the brief and wording-preservation). Each ingested header carries the leakage inventory. Cleanup = a future L4/L3 refinement pass, by their owners, mirroring the L5 pass. |
| RN-8 | Layer-numbering collision | **RESOLVED at governance level.** Canonical scheme determined; full mapping + per-document disposition in [[LAYER_MAPPING_TABLE]]; taxonomy amendment drafted as D-025-P. Residual: owner ratification. |
| RN-9 | Data Fence / Custody Fence naming | **RECORDED.** Alias mapping already in ASI §5; a rename declaration would modify content. Owner may fold into D-025-P or a CUSTODY_MODEL minor version. |
| RN-10 | L4.5 withdrawal unrecorded; orphaned definitions | **RESOLVED (record) / FLAGGED (orphan).** Withdrawal quoted verbatim in [[EXECUTION_SEMANTICS]]'s header; ratification drafted as D-026-P. The orphaned-definition risk (Execution Identity/Context defined most precisely in the withdrawn doc, referenced by [[REFERENCE_ARCHITECTURE]] Interaction 1) is preserved-and-flagged, not resolved — resolving it (confirming L4 subsumes the definitions, or amending L4) is an architecture judgment. |

## 4. Proposed decisions (drafted for the owner — NOT applied)

Numbered with a `-P` (proposed) suffix to avoid colliding with the owner's decision sequence; the [[DECISION_LOG]] remains untouched.

**D-025-P — Ratify the layer scheme.** EITHER (a) adopt the transcript scheme: amend [[TAXONOMY_AND_NAMING_STANDARD]] §3 (v1.0→v2.0) to L0 Governance & Scope · L1 Scientific Foundation · L2 Research Architecture · L3 Data Ontology · L4 Runtime Architecture · L5 Reference Architecture · L6 Technology Profiles; update the five compliant-but-then-stale Phase A labels listed in [[LAYER_MAPPING_TABLE]] §3; re-annotate the three ingested headers from "contested" to final; OR (b) retain the ratified L0–L8 scheme and direct the spec owners to re-slot/retitle the ingested documents. *Basis: the owner's own transcript decision favors (a); it has simply never been transacted.*

**D-026-P — Record the L4.5 withdrawal.** Ratify that L4.5 Execution Semantics is Withdrawn (owner rationale quoted in [[EXECUTION_SEMANTICS]]); direct the L4 owner to confirm L4 subsumes Execution Identity/Context or amend L4 accordingly (closes the RN-10 orphan flag).

**D-027-P — Ratify the ingested corpus.** Accept `DATA_ONTOLOGY`, `RUNTIME_ARCHITECTURE`, `REFERENCE_ARCHITECTURE` as canonical-candidate layer specifications (status they now carry), confirm the L3 owner assignment, and commission their independent reviews (RN-4).

## 5. Complete file manifest (this remediation)

**Created (11):**
1. `docs/research_os/DATA_ONTOLOGY.md`
2. `docs/research_os/RUNTIME_ARCHITECTURE.md`
3. `docs/research_os/REFERENCE_ARCHITECTURE.md`
4. `docs/archive/REFERENCE_ARCHITECTURE_DRAFT.md`
5. `docs/archive/EXECUTION_SEMANTICS.md`
6. `docs/roadmap/GOVERNANCE_REMEDIATION_REPORT.md` (this file)
7. `docs/roadmap/HEADER_CHANGE_LOG.md`
8. `docs/roadmap/LAYER_MAPPING_TABLE.md`
9. `docs/roadmap/DOCUMENT_REGISTRY_UPDATE.md`
10. `docs/roadmap/CROSS_REFERENCE_AUDIT.md`
11. `docs/roadmap/FREEZE_READINESS_REPORT.md`

**Modified: none. Deleted: none. Committed: nothing** (per instruction).
