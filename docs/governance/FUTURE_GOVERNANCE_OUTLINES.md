# Future Governance — Outlines Only

**Layer:** L0 — Governance & Scope · **Status:** Outlines (not yet canonical) · **Version:** 0.1 · **Date:** 2026-07-15
**Purpose:** Reserve and scope the governance documents identified as missing, *without* authoring them yet. These become full L0/L4 documents on the schedule in [[RESEARCH_OS_MASTER_ROADMAP]]. Each outline states purpose, scope, key questions, dependency, and target layer — enough to prevent architectural drift, not enough to over-engineer the first release.

---

## 1. RESEARCH_DATABASE_CONCEPT.md → target Layer L4
**Purpose:** Define the logical + physical data architecture of the Research OS.
**Scope:** research vs production separation (inherits v3 **R-5 physical DB split**, already scoped); append-only evidence tables; storage/compaction for high-volume feeds (12.2M 1-min flow rows, 10.4M ticks — see [[DATA_FEASIBILITY_STUDY]] §6); read models for feature computation.
**Key questions:** one DB or per-domain? retention/compaction policy? how does the FCG read features reproducibly? partition by resolution (daily vs intraday)?
**Depends on:** DATA_FEASIBILITY_STUDY, v3 R-5 scope. **Priority:** P1.

## 2. METADATA_STANDARD.md → target Layer L4
**Purpose:** The universal provenance/metadata schema attached to every research object.
**Scope:** required fields (id, created_at, git_commit, dataset_fingerprint, author, lineage refs, immutability flag); mirrors v3 `research.tracking` envelope; controlled vocab from [[TAXONOMY_AND_NAMING_STANDARD]].
**Key questions:** what is the minimum metadata for reproducibility? how is it enforced (schema vs review)? how do lineage edges serialize?
**Depends on:** Taxonomy, Research Object Model. **Priority:** P1.

## 3. VERSIONING_POLICY.md → target Layer L4
**Purpose:** How objects, features, configs, and thresholds are versioned and frozen.
**Scope:** semantic + git-hash versioning (`Feature_v[M].[m]_[hash]`); immutability-on-use rule; **non-retroactive amendment** discipline (inherits v3 Invariant: no silent threshold changes, versioned config lineage); branch-on-upstream-change for features.
**Key questions:** when does a change fork a new version vs amend in place? who may bump a gate threshold? how are frozen experiments protected?
**Depends on:** Metadata Standard, FCG. **Priority:** P1.

## 4. KNOWLEDGE_LIFECYCLE.md → target Layer L8
**Purpose:** Govern an Accepted Knowledge Object from acceptance → monitoring → decay/retirement.
**Scope:** decay-monitor semantics (the referenced `decay_monitor_id`); half-life re-estimation cadence; demotion criteria; interaction with v3 edge-registry lifecycle (R-10 receipt-bound states) and forward-testing.
**Key questions:** what triggers re-validation? who retires knowledge? how is a decayed mechanism archived without losing lineage?
**Depends on:** Validation Framework, v3 edge registry / R-10. **Priority:** P2.

## 5. RESEARCH_PRIORITIZATION_FRAMEWORK.md → target Layer L0
**Purpose:** Decide *which* Programs/hypotheses to fund next — allocation of scarce research effort.
**Scope:** scoring by (expected scientific value × data availability × mechanism novelty × capacity) ÷ cost; explicit weighting of Available-Today vs Future-Capability work; anti-recency / anti-fashion guardrails.
**Key questions:** how is "scientific value" scored without hindsight? how much effort on Future-Capability (L3) research vs executable work? who arbitrates?
**Depends on:** DATA_FEASIBILITY_STUDY, RESEARCH_OS_RECONCILIATION. **Priority:** P2.

---
*None of these are blockers for Phase-A freeze. They are scheduled as L0/L4/L8 deliverables so the foundation can support later phases without another redesign.*
