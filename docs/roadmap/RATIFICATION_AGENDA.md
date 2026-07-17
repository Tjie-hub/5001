# Ratification Agenda — Phase B Governance Session

**Status:** Ratification preparation record · **Version:** 1.0 · **Date:** 2026-07-17
**Authority:** Agenda for the Owner Ratification session covering pending proposals D-025-P, D-026-P, D-027-P. Procedural only — this document schedules a decision, it does not make one.
**Companion documents:** [[OWNER_RATIFICATION_PACKAGE]] (decision support), [[RATIFICATION_EVIDENCE_INDEX]] (evidence references)
**Convening basis:** Phase B Governance Remediation complete ([[GOVERNANCE_REMEDIATION_REPORT]]); Independent Review **APPROVE WITH MINOR OBSERVATIONS** (GLM 5.2, 2026-07-17); sole accepted defect **F-1 CLOSED** ([[F1_CLOSURE_REPORT]]); no remaining implementation defects.

---

## 1. Opening

- **Purpose of session.** Ratify, amend, or reject the three pending proposed decisions arising from the Phase B governance remediation, and confirm the repository's freeze-readiness position.
- **Authority present.** Owner (sole ratifying authority — only party who may write [[DECISION_LOG]]).
- **Scope boundary — read into the record.**
  - No Phase A file (L0 / L1 / L2) is modified by this session **except** the specific edits an approved D-025-P option (a) authorizes under the owner's own authority.
  - No technical or scientific architecture is redesigned.
  - Ratification is transacted by the owner writing D-025 / D-026 / D-027 into [[DECISION_LOG]]; the preparation package does not and cannot perform that write.
- **Materials confirmed present.** [[OWNER_RATIFICATION_PACKAGE]], [[RATIFICATION_EVIDENCE_INDEX]], [[GOVERNANCE_REMEDIATION_REPORT]], [[FREEZE_READINESS_REPORT]], [[LAYER_MAPPING_TABLE]], [[F1_CLOSURE_REPORT]].

## 2. Review of Independent Findings

- **Independent Review outcome:** APPROVE WITH MINOR OBSERVATIONS (GLM 5.2, 2026-07-17).
- **Accepted defect F-1 (Minor) — CLOSED.** File-count figures in two governance records were unsupported and mutually inconsistent; corrected to the verified canonical count (50 pre-existing + 5 ingested + 6 records = 61). Every *qualitative* conclusion those counts supported (zero broken references; zero duplicate IDs) was independently re-verified true under the corrected count. See [[F1_CLOSURE_REPORT]].
- **Three standing Observations — noted, no action required for approval** (matters for this ratification step, not blockers to it, per [[F1_CLOSURE_REPORT]] §7):
  - **R-1** — contested-layer limbo of [[REFERENCE_ARCHITECTURE]] / [[RUNTIME_ARCHITECTURE]] → addressed by **D-025-P**.
  - **R-2** — the three ingested specs inherit an unsigned L1 (G-8) → structural; addressed by G-8 sign-off, not by ratification.
  - **R-3** — the corpus has no numeric document-ID scheme → deferred to the owner as a new-concept decision, out of remediation scope.
- **Confirmation to record:** no remaining implementation defects; the package is APPROVE WITH MINOR OBSERVATIONS pending Owner Ratification.

## 3. D-025-P — Ratify the layer scheme

- **Read:** [[OWNER_RATIFICATION_PACKAGE]] → D-025-P; evidence in [[RATIFICATION_EVIDENCE_INDEX]] §D-025-P.
- **Question before the owner:** adopt the transcript scheme (option a: amend [[TAXONOMY_AND_NAMING_STANDARD]] §3 v1.0→v2.0, update five Phase A labels, re-annotate three ingested headers), **or** retain the ratified L0–L8 scheme (option b: re-slot/retitle the ingested specs).
- **Recommendation on the table:** option (a) — transacts a decision the owner already made in the transcript.
- **Decision:** ▢ Approve (a) ▢ Approve (b) ▢ Amend ▢ Reject ▢ Defer

## 4. D-026-P — Record the L4.5 withdrawal

- **Read:** [[OWNER_RATIFICATION_PACKAGE]] → D-026-P; evidence in [[RATIFICATION_EVIDENCE_INDEX]] §D-026-P.
- **Question before the owner:** ratify L4.5 Execution Semantics as **Withdrawn**, and direct the L4 owner to confirm [[RUNTIME_ARCHITECTURE]] subsumes Execution Identity / Execution Context (or amend L4) — closing the RN-10 orphan flag.
- **Recommendation on the table:** ratify the withdrawal; assign the L4 subsumption check as a discrete task.
- **Decision:** ▢ Approve ▢ Amend ▢ Reject ▢ Defer · **L4 subsumption owner assigned to:** ____________

## 5. D-027-P — Ratify the ingested corpus

- **Read:** [[OWNER_RATIFICATION_PACKAGE]] → D-027-P; evidence in [[RATIFICATION_EVIDENCE_INDEX]] §D-027-P.
- **Question before the owner:** accept [[DATA_ONTOLOGY]], [[RUNTIME_ARCHITECTURE]], [[REFERENCE_ARCHITECTURE]] as **canonical-candidate** layer specifications; confirm (or reassign) the L3 owner; commission independent reviews (RN-4).
- **Recommendation on the table:** accept candidacy, confirm L3 owner, commission reviews — ideally sequenced after D-025-P so identities are settled.
- **Decision:** ▢ Approve ▢ Amend ▢ Reject ▢ Defer · **L3 owner confirmed / reassigned to:** ____________

## 6. Voting Order

Ratify in dependency order so each decision rests on a settled predecessor:

1. **D-025-P first** — it fixes the layer identities that D-026-P (L4) and D-027-P (two of three specs) depend on. Deciding it first prevents ratifying documents whose layer is still contested.
2. **D-026-P second** — the L4.5 withdrawal and its orphan-definition check reference L4, whose identity D-025-P has just settled.
3. **D-027-P third** — accepts the three specs (now carrying settled identities) as candidates and commissions their reviews.

*Rationale: the dependency graph points D-027-P → D-025-P and D-026-P → D-025-P. Ratifying in reverse would accept documents whose layer identity is still open.*

## 7. Expected Repository Changes after Approval

**On approval of D-025-P option (a) — the only step that edits Phase A files (under owner authority):**
- [[TAXONOMY_AND_NAMING_STANDARD]] §3 amended v1.0 → v2.0 (new L4/L5/L6 names).
- Five Phase A layer labels updated per [[LAYER_MAPPING_TABLE]] §3 ([[FEATURE_COMPUTATION_GRAPH]], [[RESEARCH_VALIDATION_FRAMEWORK]], [[FAILURE_LIBRARY_SCHEMA]], [[RESEARCH_OS_MASTER_ROADMAP]] §2, [[FUTURE_GOVERNANCE_OUTLINES]]).
- Three ingested headers re-annotated contested → final ([[DATA_ONTOLOGY]], [[RUNTIME_ARCHITECTURE]], [[REFERENCE_ARCHITECTURE]]).
- *(Option b instead: the three ingested specs re-slotted/retitled by their owners; no TAXONOMY amendment.)*

**On approval of D-026-P:**
- L4.5 withdrawal recorded as ratified; [[EXECUTION_SEMANTICS]] stays archived as history.
- L4 owner returns a subsumption confirmation (or an L4 amendment) — closes the RN-10 orphan flag.

**On approval of D-027-P:**
- The three ingested specs' status advances from "candidate (unratified)" to accepted candidate; L3 owner annotation confirmed; independent reviews commissioned (RN-4).

**Common to all three (the ratification act itself):**
- Owner writes **D-025 / D-026 / D-027** into [[DECISION_LOG]] (the only edit that records the decisions).
- [[RESEARCH_OS_MASTER_ROADMAP]] §2 layer-status table updated to acknowledge L3–L5 exist (queued on the D-025-P execution checklist, [[CROSS_REFERENCE_AUDIT]] §4).

**Not changed by any approval:** Phase A certification basis, G-8 / G-9 status, the Research OS v1.0 freeze position, or any scientific content.

## 8. Freeze Readiness Checklist

Source of record: [[FREEZE_READINESS_REPORT]] §2 (exhaustive blocker list). Ratifying all three proposals clears the owner-decision blockers only; the hard blockers remain.

| # | Blocker | Type | Cleared by this session? |
|---|---|---|---|
| 1 | **G-8** — independent adversarial sign-off on Phase A (criterion: "not the author") | Hard | ✗ No — needs a reviewer signature, not a ratification |
| 2 | **G-9** — Dataset Custody mechanism (policy exists, mechanism does not) | Hard | ✗ No — needs engineering (RFC-1) |
| 3 | **RN-4** — zero independent reviews of L3/L4; L5 self-pass only | Hard | ◐ Opened by D-027-P (reviews commissioned), not closed |
| 4 | **D-025-P** — layer scheme ratification (contested layer identity) | Owner decision | ✓ Yes — on approval |
| 5 | **D-026-P** — L4.5 withdrawal + orphan-definition confirmation | Owner decision | ✓ Yes — on approval (+ L4 owner's return) |
| 6 | **D-027-P** — ingested-spec candidacy + L3 owner confirmation | Owner decision | ✓ Yes — on approval |

**Deferred, not blockers (for completeness):** RN-7 leakage cleanup (L3/L4 quality passes), RN-9 fence-naming declaration, D-015 (L1 location, still unanswered), L6 Technology Profiles (deliberately unauthored).

**Shortest path to a Phase B freeze after this session** ([[FREEZE_READINESS_REPORT]] §3): (1) these three ratified → (2) G-8 reviewer signs (also closes G-4 — "one person, two gates") → (3) independent L3/L4/L5 reviews (RN-4; RN-7 cleanup ideally first) → (4) G-9 mechanism lands. **No new documents required for any step.**

## 9. Close

- Record each decision (Approve / Amend / Reject / Defer) and any owner assignments (L4 subsumption owner; L3 owner).
- If ratified, owner writes D-025 / D-026 / D-027 into [[DECISION_LOG]].
- Confirm next actions: G-8 sign-off scheduling (day-one task per [[PHASE_A_FINAL_GATE_REVIEW]] — independence window is short), RN-4 reviewer commissioning, RFC-1 (G-9) scoping.

---

*Agenda only. Decisions are recorded by the owner in [[DECISION_LOG]]; nothing in this document changes governance status.*
