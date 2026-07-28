# Owner Ratification Package — Phase B Governance Decisions

**Status:** Ratification preparation record · **Version:** 1.0 · **Date:** 2026-07-17
**Authority:** Assembles the three pending proposed decisions (D-025-P, D-026-P, D-027-P) for an Owner Ratification session. **This document decides nothing.** It records background, evidence, and a recommendation for each so the owner can ratify, amend, or reject in one sitting.
**Produced by:** Ratification preparation — no governance status changed, no Phase A file modified, [[DECISION_LOG]] untouched.
**Package under ratification:** Phase B Governance Remediation ([[GOVERNANCE_REMEDIATION_REPORT]]), Independent Review outcome **APPROVE WITH MINOR OBSERVATIONS** (GLM 5.2, 2026-07-17), sole accepted defect **F-1 CLOSED** ([[F1_CLOSURE_REPORT]]).

---

## How to read this package

- Every proposal below carries the `-P` (proposed) suffix. **None is a ratified decision.** The next free ratified ID in [[DECISION_LOG]] is D-025; the proposals are numbered to slot in on ratification, but that write is reserved to the owner.
- The proposals are **drafted, not applied.** Their source text is [[GOVERNANCE_REMEDIATION_REPORT]] §4; this package expands each with the decision-support fields the owner needs and does not alter their substance.
- Ratifying a proposal is the act that permits the follow-on repository edits it names. Until then the repository state is exactly as the remediation left it: additive files only, zero modifications.

---

## D-025-P — Ratify the layer scheme

**Proposal ID:** D-025-P

**Background.**
The Architecture Specification Index review raised **RN-8**: the repository carries two layer-numbering schemes that diverge at L4 and above. The **ratified** vocabulary ([[TAXONOMY_AND_NAMING_STANDARD]] §3, v1.0, a Phase A / L0 canonical file) reads L4 = Research Infrastructure, L5 = Feature Computation, L6 = Hypothesis Engine, L7 = Validation Framework, L8 = Knowledge Repository. The **transcript** scheme the owner used when commissioning the newer specifications reads L4 = Runtime Architecture, L5 = Reference Architecture, L6 = Technology Profiles. The remediation determined that the ratified vocabulary is repository-canonical *today* — an unratified transcript statement cannot displace a ratified standard under the corpus's own integrity rules ([[LAYER_MAPPING_TABLE]] §1). The transcript scheme is a genuine owner decision **in intent** that has never been transacted (no [[DECISION_LOG]] entry, no taxonomy amendment, no version bump).

**Evidence.**
- [[GOVERNANCE_REMEDIATION_REPORT]] §3 (RN-8 disposition), §4 (D-025-P draft text)
- [[LAYER_MAPPING_TABLE]] §1 (canonical-scheme determination), §2 (old ↔ transcript mapping), §3 (per-document disposition; the **five** Phase A labels that become stale under option a), §4 (residual owner actions)
- [[DOCUMENT_REGISTRY_UPDATE]] §2 (REFERENCE_ARCHITECTURE fails strict layer-uniqueness pending this decision)
- Ingested headers carrying the contested annotation: [[REFERENCE_ARCHITECTURE]], [[RUNTIME_ARCHITECTURE]], [[DATA_ONTOLOGY]]
- [[ARCHITECTURE_SPECIFICATION_INDEX]] §11 (RN-8 origin)

**Current Status.** OPEN — proposed, drafted, not applied. Layer identity of [[REFERENCE_ARCHITECTURE]] is **CONTESTED** and [[RUNTIME_ARCHITECTURE]]'s layer *name* is **unadjudicated** until this is decided.

**Decision Required.** Choose one:
- **(a) Adopt the transcript scheme.** Amend [[TAXONOMY_AND_NAMING_STANDARD]] §3 (v1.0 → v2.0) to: L0 Governance & Scope · L1 Scientific Foundation · L2 Research Architecture · L3 Data Ontology · L4 Runtime Architecture · L5 Reference Architecture · L6 Technology Profiles. Update the five compliant-but-then-stale Phase A labels in [[LAYER_MAPPING_TABLE]] §3. Re-annotate the three ingested headers from "contested" to final.
- **(b) Retain the ratified L0–L8 scheme.** Direct the specification owners to re-slot / retitle the three ingested documents to fit existing slots.

**Impact if Approved (option a).** REFERENCE_ARCHITECTURE receives a defined slot (L5); RUNTIME_ARCHITECTURE's name is adjudicated (L4 Runtime Architecture); the three ingested headers move contested → final; the contested-identity freeze blocker (#4) clears. Requires editing Phase A files (TAXONOMY §3 + five labels) — permissible only under the owner's own authority, outside the remediation's hard constraints.

**Impact if Rejected / option (b).** The three ingested specifications must be re-slotted or renamed by their owners to fit the ratified scheme; the transcript scheme the owner originally commissioned under is abandoned. Either outcome is mechanical once decided (both checklists exist in [[GOVERNANCE_REMEDIATION_REPORT]]).

**Dependencies.** [[TAXONOMY_AND_NAMING_STANDARD]] §3 (amendment target under a). Interlocks with D-027-P (two of the three ratified specs derive their layer identity from this decision). RN-9 (Data Fence / Custody Fence naming) may optionally be folded in ([[GOVERNANCE_REMEDIATION_REPORT]] §3, RN-9).

**Blocking Items.** This proposal is itself blocker #4 in [[FREEZE_READINESS_REPORT]] §2 — a document with contested layer identity cannot freeze. It does not block Phase A. It does not resolve the hard blockers G-8 / G-9 / RN-4.

**Recommendation.** **Adopt option (a).** The owner's own transcript decision already favors it; the newer specifications were commissioned under it. Ratifying (a) transacts a decision that was made but never recorded — the exact defect RN-3 flags. Recommendation carries the remediation's own basis note: *"the owner's own transcript decision favors (a); it has simply never been transacted."*

---

## D-026-P — Record the L4.5 withdrawal

**Proposal ID:** D-026-P

**Background.**
The review raised **RN-10**: an "L4.5 Execution Semantics" specification was authored, then **withdrawn by owner decision recorded only in the source transcript** — never formally recorded in the repository. A second, latent risk rides on it: the concepts **Execution Identity** and **Execution Context** are defined most precisely inside the *withdrawn* document, yet are still referenced by [[REFERENCE_ARCHITECTURE]] (Interaction 1). If the withdrawal stands without a home for those definitions, they are orphaned.

**Evidence.**
- [[GOVERNANCE_REMEDIATION_REPORT]] §3 (RN-10 disposition — RESOLVED (record) / FLAGGED (orphan)), §4 (D-026-P draft text)
- [[EXECUTION_SEMANTICS]] header — status **Withdrawn**, owner rationale quoted verbatim from the transcript; "Never became canonical. Do not cite as a layer."
- [[HEADER_CHANGE_LOG]] §1 row 5 (ingested at v0.1, Withdrawn, review status "None — withdrawn pre-review")
- [[LAYER_MAPPING_TABLE]] §2–§3 (L4.5 exists in neither scheme)
- [[REFERENCE_ARCHITECTURE]] Interaction 1 (the reference that creates the orphaned-definition risk)

**Current Status.** OPEN — withdrawal is *recorded in the document header* but **not ratified**; the orphaned-definition risk is *flagged, not resolved*.

**Decision Required.** (1) Ratify that L4.5 Execution Semantics is **Withdrawn** (owner rationale as quoted in [[EXECUTION_SEMANTICS]]). (2) Direct the L4 owner to either confirm that [[RUNTIME_ARCHITECTURE]] (L4) subsumes the Execution Identity / Execution Context definitions, or amend L4 to carry them — closing the RN-10 orphan flag.

**Impact if Approved.** L4.5 withdrawal becomes a ratified governance fact rather than a transcript-only statement; freeze blocker #5 clears once the L4 subsumption confirmation is returned. The document remains preserved in `docs/archive/` as history (never deleted).

**Impact if Rejected.** L4.5 remains in governance limbo (withdrawn in appearance, unratified in fact); the Execution Identity / Context definitions stay orphaned inside a withdrawn document that [[REFERENCE_ARCHITECTURE]] still cites — a latent broken-authority hazard for any future freeze.

**Dependencies.** L4 owner (confirmation or amendment of [[RUNTIME_ARCHITECTURE]]). Interlocks with D-025-P (which fixes L4's identity) and D-027-P (which ratifies the L4 document itself). Resolving the orphan is an **architecture judgment**, explicitly outside the remediation's authority.

**Blocking Items.** Blocker #5 in [[FREEZE_READINESS_REPORT]] §2. Does not block Phase A. Does not resolve G-8 / G-9 / RN-4.

**Recommendation.** **Ratify the withdrawal; commission the L4 subsumption check.** The withdrawal decision was already made by the owner; ratifying it only transacts it. The orphaned-definition confirmation should be assigned as a discrete task to the L4 owner, since it is an architecture judgment the remediation was forbidden to make.

---

## D-027-P — Ratify the ingested corpus

**Proposal ID:** D-027-P

**Background.**
The review raised **RN-2** (L3–L5 existed only inside a PDF transcript), **RN-3** (no decision records for them), **RN-6** (missing headers — L3 had no owner; no versions anywhere), and **RN-4** (review asymmetry: L3 and L4 have zero independent reviews, L5 has only a self-refinement pass). The remediation ingested the three specifications to repository markdown with full standardized metadata, wording preserved verbatim, source PDF retained as the provenance original. They now carry the status **Canonical (candidate; unratified pending D-025-P)**. L3's owner was assigned at ingestion (Research Architect) with an explicit *confirmation-pending* annotation — the one metadata judgment the remediation made, flagged rather than hidden.

**Evidence.**
- [[GOVERNANCE_REMEDIATION_REPORT]] §3 (RN-2 / RN-3 / RN-4 / RN-6 dispositions), §4 (D-027-P draft text), §5 (file manifest)
- [[HEADER_CHANGE_LOG]] §1 (five created headers with full metadata; review-status fields recorded honestly)
- [[DOCUMENT_REGISTRY_UPDATE]] §1 (registry delta), §2 (per-document P3 governance-completion verification), §3 (ID-uniqueness sweep, zero duplicates)
- [[CROSS_REFERENCE_AUDIT]] §1 (zero broken references), §4 (the three specs are cited by no pre-existing document — queued to D-025-P execution)
- Ingested documents: [[DATA_ONTOLOGY]], [[RUNTIME_ARCHITECTURE]], [[REFERENCE_ARCHITECTURE]]; provenance original `docs/L3 Data Ontology Specification.pdf`
- [[F1_CLOSURE_REPORT]] (Independent Review; sole accepted defect F-1 closed; observations R-1/R-2/R-3 stand)

**Current Status.** OPEN — the three specifications carry the *candidate* status they were ingested with; formal acceptance, L3 owner confirmation, and independent reviews are all pending.

**Decision Required.** (1) Accept `DATA_ONTOLOGY`, `RUNTIME_ARCHITECTURE`, `REFERENCE_ARCHITECTURE` as **canonical-candidate layer specifications** (the status they now carry). (2) Confirm (or reassign) the L3 owner assignment. (3) Commission their independent reviews (closing RN-4).

**Impact if Approved.** The three specifications become formally accepted candidates rather than ingested-only text; the L3 ownership annotation moves from "confirmation pending" to confirmed; independent review of L3/L4/L5 is commissioned. Freeze eligibility of the L3–L5 stratum advances (but does not complete — see blocking items).

**Impact if Rejected.** The three specifications remain ingested-but-unratified; L3 ownership stays provisional; RN-4's review deficit persists with no path opened. The corpus keeps three canonical-*candidate* documents that no pre-existing document references.

**Dependencies.** **D-025-P** (the layer identity of two of the three is contested/unadjudicated until it is decided — accepting them cleanly is easier after D-025-P). Independent reviewers must exist (RN-4). Ideally RN-7 leakage-cleanup passes on L3/L4 precede their reviews so reviewers see leakage-free texts ([[FREEZE_READINESS_REPORT]] §3).

**Blocking Items.** The hard blockers remain regardless of this ratification: **G-8** (unsigned L1 — everything downstream inherits it), **G-9** (Dataset Custody mechanism), **RN-4** (no independent reviews yet). Ratifying D-027-P accepts candidacy and commissions review; it does not itself freeze anything.

**Recommendation.** **Accept as canonical candidates and commission the independent reviews**, preferably immediately after D-025-P so the accepted documents carry settled layer identities. Confirm the L3 owner or name a different one. Note explicitly in the ratification record that acceptance is of *candidacy*, not of a freeze — the freeze still waits on G-8 / G-9 / RN-4.

---

## Cross-proposal summary

| Proposal | One-line decision | Freeze blocker it clears | Hard blockers it does **not** clear | Recommended action |
|---|---|---|---|---|
| **D-025-P** | Ratify the layer scheme (recommend option a) | #4 contested layer identity | G-8, G-9, RN-4 | Adopt transcript scheme (a) |
| **D-026-P** | Ratify L4.5 withdrawal + commission L4 subsumption check | #5 L4.5 limbo / orphan flag | G-8, G-9, RN-4 | Ratify withdrawal; assign L4 check |
| **D-027-P** | Accept 3 ingested specs as candidates + commission reviews | opens RN-4 path | G-8, G-9, RN-4 (opened, not closed) | Accept candidacy; commission reviews |

**None of the three touches Phase A of its own accord.** The only Phase A edits any of them *authorizes* are the five label updates and the TAXONOMY §3 amendment under D-025-P option (a) — executed under the owner's authority, which the remediation's hard constraints do not bind.

**After all three ratify, the shortest remaining path to a Phase B freeze** ([[FREEZE_READINESS_REPORT]] §3): G-8 reviewer signs (also closes G-4 — "one person, two gates") → independent L3/L4/L5 reviews (RN-4) → G-9 mechanism lands. **No new documents are required for any of these steps.**

---

*This package is a preparation artifact. It records proposals for decision; it does not record decisions. Ratification is transacted by the owner writing D-025 / D-026 / D-027 into [[DECISION_LOG]] — an act reserved to the owner and not performed here.*
