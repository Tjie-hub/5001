# Revision Impact Assessment

**Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Scope:** Impact of the Phase-A governance/architecture hardening revision on the existing Research OS draft, the seven canonical documents, and the live v3 system.

---

## 1. Summary

The revision is **additive and non-destructive**. It adds a governance layer (L0) and a naming/scope discipline *around* the existing architecture. **Zero canonical architecture documents were rewritten. Zero production code was touched. The frozen v3 plan is untouched.** Risk is low; the change is reversible (new files + a folder move).

## 2. What changed

| Change | Type | Blast radius |
|---|---|---|
| 4 governance docs authored (feasibility, reconciliation, taxonomy, worked example) | Add | new files only |
| 5 future-governance docs outlined | Add | new file only |
| Revised master roadmap (Layers/Programs, current-vs-future, exit checklist, diagram) | Add / supersede draft | replaces the *draft* v1.0 plan (which was never a repo file) |
| Folder structure created (`roadmap/ research_os/ research_programs/ governance/ references/`) | Add | empty dirs; migration of 7 docs is *planned*, not yet executed |
| Status changed NO-GO → **GO WITH CONDITIONS** | Governance decision | roadmap only |

## 3. What did NOT change (preservation guarantees)

- ✅ The **6 existing canonical architecture documents** are byte-for-byte unchanged (Object Model, Operating Model, Validation Framework, FCG, Pipeline, Failure Library).
  - ⚠️ **Correction, 2026-07-15** ([[DECISION_LOG]] C-1): this list previously read "7 … Market Inefficiency Foundation." **No such file existed**, so the preservation guarantee was vacuously true for it. The L1 artifact has now been authored — [[01_SCIENTIFIC_FOUNDATION]] — closing finding AQ-8.
  - ⚠️ **Preservation and correction are in tension here, and this document did not previously notice.** Byte-for-byte preservation is simultaneously the mechanism by which the pre-feasibility ontology survives: the Object Model still teaches `L3 Order Book`, `BBO`, `Nanosecond`, and `Latency Arbitrage` as its worked exemplars, all classified Institutional-Only or Unrealistic by the binding scope constraint ([[DATA_FEASIBILITY_STUDY]] §4.3–§4.4). That is finding **AQ-1 (Critical)**, recorded per ISO 42010 §5.6 at [[01_SCIENTIFIC_FOUNDATION]] §15.1. Preserving a document is not the same as endorsing it.
- ✅ `docs/RESEARCH_MASTER_PLAN.md` **v3 (frozen)** — untouched. Its invariants, gatekeeper, regime engine, knowledge base, edge registry are unaffected.
- ✅ No production code, no database schema, no tests altered.
- ✅ No research direction deleted — Future-Capability programs (P5/P6) retained and clearly separated.

## 4. Impact on the 7 canonical documents (future, non-breaking)

Each gains a **one-line cross-reference** to its v3 mechanism ([[RESEARCH_OS_RECONCILIATION]] §4) and a **layer tag** (L1/L2). These are annotations, not rewrites. Concretely:

| Canonical doc | Layer | Additive note to add later |
|---|---|---|
| Research Object Model | L2 | core-vs-extension split; add preregistration_hash to Hypothesis |
| Research Operating Model | L2 | Gates renamed per taxonomy (G1–G4) |
| Validation Framework | L7 | append power/MDE/structural-break/reproducibility/custody |
| Feature Computation Graph | L5 | note determinism realized in L5 |
| Research Pipeline | — | relabel steps→Stages S1–S10 |
| Failure Library | L8 | map to v3 `failure_registry` |
| ~~Market Inefficiency Foundation~~ → [[01_SCIENTIFIC_FOUNDATION]] | L1 | ✅ **Authored 2026-07-15, not annotated** — the file did not exist. Domain de-overlap discharged (D1–D6 exclusive, Market-Design + Limits-to-Arbitrage added, Cost/Impact promoted). [[DECISION_LOG]] C-2 |

None is a redesign; all are P1/P2, additive.

## 5. Risk assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Two roadmaps still confuse readers | Low | Reconciliation doc declares one canonical roadmap + precedence rules |
| Folder move breaks internal links | Low | Migration plan uses `git mv`; wikilinks are name-based, not path-based |
| Scope creep back into L3 (unavailable) data | Med | Feasibility Matrix is a hard gate on hypothesis registration |
| Short-history feeds used prematurely | Med | History-maturity gate (feasibility §5.3) |

## 6. Reversibility

Fully reversible: delete the new `governance/ roadmap/` files and the empty dirs; the migration (if executed) is a `git mv` that `git mv` reverses. No irreversible action taken.
