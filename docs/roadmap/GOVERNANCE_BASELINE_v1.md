# Governance Baseline v1 — Official Repository State (Post Phase B Freeze)

**Version:** 1.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L0 — Governance & Scope
**Date:** 2026-07-17 · **Owner:** Owner (ratification authority)
**Authority:** The official snapshot of the governance state of the repository at the moment Phase B Governance was frozen. This is the reference point future amendments are measured against.
**Certified by:** [[PHASE_B_FREEZE_CERTIFICATE]] · **Closed by:** [[PHASE_B_GOVERNANCE_CLOSURE_REPORT]]

---

## 1. Baseline statement

As of **2026-07-17**, **Phase B Governance is CLOSED and FROZEN**. The governance layer — its decision record, its remediation records, and its layer scheme — is baselined here. Change to this baseline is permitted only through a formal governance amendment (a superseding [[DECISION_LOG]] entry).

## 2. Ratified layer scheme (D-025, option a)

| Layer | Name |
|---|---|
| L0 | Governance & Scope |
| L1 | Scientific Foundation |
| L2 | Research Architecture |
| L3 | Data Ontology |
| L4 | Runtime Architecture |
| L5 | Reference Architecture |
| L6 | Technology Profiles (unauthored — deferred by design) |

*Note:* the ratified names above are the governance decision of record (D-025). Their propagation into [[TAXONOMY_AND_NAMING_STANDARD]] §3 (v1.0 → v2.0) and the five Phase A labels is **owner-authorized and deferred** to the Phase A formal-amendment path — it was not executed in this closure so that Phase A remained undisturbed. Until it is transacted, [[TAXONOMY_AND_NAMING_STANDARD]] §3 still carries the prior vocabulary; cite L4/L5 with the document name where ambiguity is possible.

## 3. Decision record (of record)

- **Ratified this baseline:** D-025 (layer scheme), D-026 (L4.5 withdrawal), D-027 (ingested corpus). See [[DECISION_LOG]] §2b.
- **Prior decisions:** D-001 … D-024 stand unchanged.
- **Open owner item (pre-existing, not Phase B):** D-015 (L1 artifact location).

## 4. Document status register (governance-relevant)

| Document | Layer | Status at baseline |
|---|---|---|
| [[DATA_ONTOLOGY]] | L3 | **Canonical** (ratified D-027; not frozen — RN-4 review pending) |
| [[RUNTIME_ARCHITECTURE]] | L4 | **Canonical** (ratified D-027; L4 name D-025; not frozen — RN-4 pending) |
| [[REFERENCE_ARCHITECTURE]] | L5 | **Canonical** (ratified D-027; L5 slot D-025; not frozen — RN-4 pending) |
| [[REFERENCE_ARCHITECTURE_DRAFT]] | L5 | **Superseded** (history — retained) |
| [[EXECUTION_SEMANTICS]] | (none) | **Withdrawn** (ratified D-026; history — retained) |
| [[PHASE_A_FREEZE_CERTIFICATE]] | L0 | Canonical v2.1 — Phase A certified GO WITH CONDITIONS (unchanged) |
| Phase B governance records | L0 | **Frozen** — [[GOVERNANCE_REMEDIATION_REPORT]], [[LAYER_MAPPING_TABLE]], [[HEADER_CHANGE_LOG]], [[DOCUMENT_REGISTRY_UPDATE]], [[CROSS_REFERENCE_AUDIT]], [[FREEZE_READINESS_REPORT]], [[F1_CLOSURE_REPORT]], [[OWNER_RATIFICATION_PACKAGE]], [[RATIFICATION_AGENDA]], [[RATIFICATION_EVIDENCE_INDEX]], [[PHASE_B_GOVERNANCE_CLOSURE_REPORT]], [[PHASE_B_FREEZE_CERTIFICATE]], this baseline |

## 5. Freeze-chain position at baseline

| Stratum | State | Gate to next state |
|---|---|---|
| **Phase B Governance** | **FROZEN** ✅ | — (amend only by formal decision) |
| Phase A (L0+L1+L2) architecture | Certified GO WITH CONDITIONS — not frozen | G-8 (independent adversarial sign-off) |
| L3 / L4 / L5 specifications | Canonical (ratified) — not frozen | RN-4 independent reviews (commissioned) |
| Research OS v1.0 | Not frozen | G-9 (Dataset Custody mechanism) |

## 6. Open items carried forward (non-governance; not blockers to this baseline)

- **G-8** — Phase A independent adversarial sign-off (also closes G-4 — "one person, two gates").
- **G-9** — Dataset Custody mechanism (RFC-1).
- **RN-4** — independent reviews of L3/L4/L5 (commissioned by D-027).
- **RN-7** — leakage-cleanup passes for L3/L4 (ideally precede their reviews).
- **Deferred TAXONOMY §3 amendment** (D-025 consequence) + RN-9 fence-naming declaration.
- **D-015** — L1 artifact location (pre-existing owner decision).
- **L6 Technology Profiles** — deliberately unauthored.

## 7. History preservation

No document was deleted in reaching this baseline. Superseded and withdrawn documents ([[REFERENCE_ARCHITECTURE_DRAFT]], [[EXECUTION_SEMANTICS]]) and the point-in-time reports they descend from ([[FREEZE_READINESS_REPORT]]) are retained. The source transcript `docs/L3 Data Ontology Specification.pdf` remains in place as the provenance original.

---

*Governance Baseline v1 — the official repository state after the Phase B Governance freeze of 2026-07-17.*
