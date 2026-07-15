# Research OS ↔ RESEARCH_MASTER_PLAN Reconciliation

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Authority:** Establishes the **single canonical roadmap** and the relationship between the two plans that currently coexist in this repository. Any future document that implies a different relationship is subordinate to this one.

---

## 1. The problem this resolves

Two master plans exist in one repository:

| | `docs/RESEARCH_MASTER_PLAN.md` (**v3**) | Institutional Research OS |
|---|---|---|
| Status | **Ratified & frozen 2026-07-14** (commit `9db223e`) | Draft (Phase A under review) |
| Nature | **Executed system** — gatekeeper, regime engine, knowledge base, forward-testing, edge registry are *built and tested* | **Scientific charter & architecture** — object model, validation framework, pipeline, FCG |
| Phase scheme | Phases A–H (delivery milestones) | Layers A–H / Programs I–III (conceptual) |
| Altitude | Implementation + governance of one live edge pipeline (NR7 etc.) | Institution-level research operating system |

Left unreconciled, they fork: clashing "Phase" schemes, ambiguous ownership, two competing sources of truth.

## 2. Decision — **Research OS COMPLEMENTS and SUPERSETS; it does not replace**

> **The Research OS is the institutional framework. `RESEARCH_MASTER_PLAN.md` v3 is the first, fully-implemented Research Program executed *inside* that framework.**

Precisely:

- **Research OS `extends`** the existing work by wrapping it in an institution-level scientific charter, object model, and governance layer.
- **Research OS `complements`** v3 — it adds the missing *scientific-method scaffolding* (literature→mechanism→hypothesis provenance, feature graph, failure library) around v3's *statistical-validation machinery*.
- **Research OS does NOT `replace`** v3. Everything in v3 is preserved, canonical, and running. v3 becomes a **reference implementation** the OS is validated against.
- **Research OS does NOT `supersede`** v3's frozen invariants. The OS inherits them.

### Why not "replace"
v3 is not a plan-on-paper; it is a live system (Phase C gatekeeper verified end-to-end 2026-07-14, regime engine built, knowledge base shipped, R-10 lifecycle enforcement closed). Replacing it would discard working, tested infrastructure. The OS's job is to *generalize the frame*, not rebuild the engine.

## 3. The single canonical roadmap

**There is one roadmap: [[RESEARCH_OS_MASTER_ROADMAP]].** It contains two clearly separated tiers:

1. **Institutional Layers (L0–L8)** — the Research OS architecture (this governance layer + the 7 canonical docs).
2. **Research Programs (P1…)** — concrete research tracks. **Program P0 = "v3 Edge Pipeline (NR7 family)" — already delivered**, and it is the worked proof that the framework produces validated knowledge.

`RESEARCH_MASTER_PLAN.md` v3 remains frozen and canonical *for its scope*; the roadmap references it as Program P0's specification rather than duplicating it.

## 4. Concept mapping (v3 → Research OS)

The OS must not reinvent what v3 already implements. Explicit reuse map:

| Research OS concept | Already implemented in v3 — reuse, don't rebuild |
|---|---|
| Hypothesis Object + pre-registration | `research/knowledge` hypotheses table + receipt-bound `set_status` (Task 11) |
| Lineage Edge Object | `hypothesis_links` (append-only) |
| Failure Library | `failure_registry` (append-only) |
| Validation Framework (DSR/multiplicity/OOS/WF) | `research/gatekeeper` 8-stage pipeline (Phase C, verified) |
| Multiple-testing family + no wall-clock decay | v3 Invariant #12 + gate_config family scoping |
| Regime Object | `research/regime` engine + `regime_profiles` (Phase D) |
| Accepted Knowledge + receipt binding | Edge registry + R-10 evidence-gated lifecycle |
| Reproducibility / provenance | `research.tracking` (run_id, dataset_fingerprint, git_commit) |
| Data fence (research vs production) | `tests/test_research_data_fence.py` + R-5 physical split (scoped) |

**Governance rule:** where a Research OS object maps to an existing v3 mechanism, the OS document must *cite* the implementation, and any change goes through v3's amendment process (versioned, non-retroactive), never a silent re-spec.

## 5. Ownership & precedence rules

1. **Scientific charter, object model, validation methodology** → owned by Research OS (this framework).
2. **The live edge pipeline and its frozen invariants** → owned by `RESEARCH_MASTER_PLAN.md` v3.
3. On any conflict about a *mechanism already built*, **v3 wins** (it is tested and frozen); the OS adapts its abstraction to reality.
4. On any conflict about *scientific method or institutional governance*, **the OS wins** (that is its charter).
5. Neither plan's phase/layer numbering is imported into the other — see [[TAXONOMY_AND_NAMING_STANDARD]].

## 6. Action items created by this reconciliation
- [ ] Add **Program P0 = v3 Edge Pipeline** to the master roadmap as "delivered — reference implementation."
- [ ] In each of the 7 canonical OS docs, add a one-line cross-reference to the v3 mechanism it maps to (§4), where one exists.
- [ ] The OS Validation Framework must declare `research/gatekeeper` as its executable realization, not a parallel design.
