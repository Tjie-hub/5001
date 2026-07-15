# Phase A — Freeze Checklist

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Authority:** The auditable gate criteria for Phase A Freeze. Every item is **PASS** or **FAIL** against objective, re-runnable evidence. No scores, no judgement calls, no partial credit.
**Companion:** [[PHASE_A_FREEZE_CERTIFICATE]] — the formal phase-gate decision derived from this checklist.

**Evidence rule:** every FAIL cites a command whose output can be re-obtained, or a line reference in a canonical document. A FAIL that cannot be re-verified by a third party is not a finding and has been struck.

**Severity vocabulary:**
- **BLOCKING** — the freeze is *impossible or invalid* while this holds. Not "inadvisable" — impossible.
- **MAJOR** — a genuine non-conformance, recorded and traceable, that does not make the freeze invalid.
- **MINOR** — a defect with no bearing on the validity of the freeze.

---

## 1. Repository integrity — **FAIL** · BLOCKING

| Check | Result | Evidence |
|---|---|---|
| Corpus is under version control | **FAIL** | `git ls-files docs/Institutional_Research_Architecture/ docs/governance/ docs/roadmap/ docs/research_os/ docs/Phase_A_Scientific_Foundation/` → **empty** |
| A freeze has a referent (commit SHA) | **FAIL** | No commit contains any Research OS document |
| Corpus is durable | **FAIL** | Every document exists only in the working tree |

**Why BLOCKING and not MAJOR.** "Frozen" is a claim about durability at an identified revision. There is presently no revision, so there is no object to freeze and nothing a certificate could refer to. This is not a quality judgement — it is binary and is refuted by one command. **Every other item in this checklist is downstream of it: an artifact that is not tracked cannot be frozen no matter how correct it is.**

**Close by:** [[MIGRATION_PLAN]] §3 Step 0 (one commit). Decision **D-014**.

---

## 2. Canonical document inventory — **PASS**

All 16 canonical documents exist and are reachable. Verified by file-existence test 2026-07-15.

| # | Document | Layer | Status |
|---|---|---|---|
| 1 | `01_SCIENTIFIC_FOUNDATION.md` | L1 | ✅ exists — authored 2026-07-15 |
| 2 | `RESEARCH_OBJECT_MODEL.md` | L2 | ✅ exists |
| 3 | `RESEARCH_OPERATING_MODEL.md` | L2 | ✅ exists |
| 4 | `RESEARCH_VALIDATION_FRAMEWORK.md` | L2/L7 | ✅ exists |
| 5 | `FEATURE_COMPUTATION_GRAPH.md` | L2/L5 | ✅ exists |
| 6 | `MARKET_INEFFICIENCY_RESEARCH_PIPELINE.md` | L2 | ✅ exists |
| 7 | `FAILURE_LIBRARY_SCHEMA.md` | L2/L8 | ✅ exists |
| 8 | `DATA_FEASIBILITY_STUDY.md` | L0 | ✅ exists |
| 9 | `TAXONOMY_AND_NAMING_STANDARD.md` | L0 | ✅ exists |
| 10 | `RESEARCH_OS_RECONCILIATION.md` | L0 | ✅ exists |
| 11 | `FUTURE_GOVERNANCE_OUTLINES.md` | L0 | ✅ exists |
| 12 | `RESEARCH_OS_MASTER_ROADMAP.md` | L0 | ✅ exists |
| 13 | `DECISION_LOG.md` | L0 | ✅ exists |
| 14 | `MIGRATION_PLAN.md` | L0 | ✅ exists |
| 15 | `REVISION_IMPACT_ASSESSMENT.md` | L0 | ✅ exists |
| 16 | `WORKED_EXAMPLE_END_TO_END.md` | L2 (proof) | ✅ exists |

**Phantom documents: zero.** The single phantom in the corpus — *Market Inefficiency Foundation*, claimed byte-for-byte preserved in [[REVISION_IMPACT_ASSESSMENT]] §3 while never existing — was closed by authoring the artifact and corrected at [[DECISION_LOG]] C-1/C-2/C-6.

---

## 3. Scientific completeness — **PASS**

Finding #4 ("L1 Scientific Foundation has no artifact") is **CLOSED**. All 13 required elements are present in [[01_SCIENTIFIC_FOUNDATION]]:

| Element | Location | Element | Location |
|---|---|---|---|
| Scientific philosophy | §1 (P1–P4) | Falsification philosophy | §5 (F1–F9, R14–R15) |
| Epistemology | §2 (R1–R7) | Evidence hierarchy | §4.2 (E0–E7) |
| Market assumptions | §9 (A1–A8) | Reproducibility | §8 (P8, R19) |
| Inefficiency principles | §6 (P6–P7, R16–R17) | Scope boundaries | §10 (LIM1–LIM8) |
| Economic mechanisms | §3.4 (M1–M6) | Doc relationships | §11 |
| Research paradigm | §2.4, §3.3 | Architectural rationale | §13, §14 |
| Scientific method | §5.2, §4 | | |

**Audit basis (not assumed — tested).** Each element was grep-tested against the canonical corpus before authoring. Result recorded at [[DECISION_LOG]] **D-011**: five elements were present but distributed and undefended, four partial, four wholly absent (market assumptions, evidence hierarchy, document relationships, rationale). Notably, falsifiability was *asserted* as a gate criterion at Pipeline S3 and **never defined** anywhere in the corpus, and the mechanism taxonomy referenced by `Economic Mechanism.classification` had no artifact.

---

## 4. Architecture completeness — **FAIL** · BLOCKING (AQ-1)

| Finding | Severity | Live? | Evidence |
|---|---|---|---|
| **AQ-1** · Ontology contradicts the binding scope constraint | **Critical** | **YES** | `RESEARCH_OBJECT_MODEL.md:15` `required_data … (e.g., L3 Order Book, Trades, BBO)`; `:35` `resolution … (e.g., Nanosecond, Tick, Millisecond)`; `:28` `classification … (e.g., Latency Arbitrage …)` — all classified **Institutional-Only / Unrealistic** by [[DATA_FEASIBILITY_STUDY]] §4.3–§4.4, the declared binding scope constraint |
| **AQ-2** · Core object holds a mandatory reference to a non-existent object | High | **YES** | `grep -c decay_monitor_id RESEARCH_OBJECT_MODEL.md` → **1**; `grep -c "Decay Monitor Object"` → **0**. Dangling reference confirmed |
| **AQ-3** · Implementation leaked into the ontology | — | **WITHDRAWN** | Formally withdrawn by the owner 2026-07-15 |
| **AQ-4** · Bit-identity asserted without framing | Medium | Managed | L1 §8.3 sets the scientific requirement to conclusion-invariance; bit-identity remains available to L5 as a strategy (**ADR-L1-005**). Inconsistency recorded at L1 §15.5 per §5.6 |
| **AQ-6** · Methodology unexecutable by a single-researcher institution | High | Declared | L1 **LIM6** declares the deficit rather than absorbing it (**ADR-L1-007**) |
| **AQ-8** · Scientific Foundation concern unframed | — | **CLOSED** | [[01_SCIENTIFIC_FOUNDATION]] exists |

**Why AQ-1 is BLOCKING.** A freeze ratifies. Freezing the Object Model in its present state makes canonical a document that teaches researchers to instantiate `required_data: L3 Order Book` — data the institution does not have and cannot obtain. Per **ADR-L1-006**, a mechanism unobservable at attainable fidelity is **unfalsifiable**, and per L1 **R14** an unfalsifiable claim is inadmissible. **The frozen ontology would therefore instruct researchers to author inadmissible hypotheses, and the freeze would be the act that makes that instruction canonical.**

This is a three-line edit to exemplar text — explicitly *not* redesign; the falsification review classified it as the single highest-leverage action in the program. It is listed here rather than fixed because [[PHASE_A_FREEZE_CERTIFICATE]]'s mandate scopes edits to the roadmap, migration plan, and decision log. **A certifying authority does not edit the artifact it is certifying.**

---

## 5. ISO/IEC/IEEE 42010 compliance — **FAIL** (§5.7 only) · MAJOR, non-blocking

| Clause | Requirement | Result | Evidence |
|---|---|---|---|
| §5.2 | Identify system; identify stakeholders | **PASS** | L1 §0.1 (system-of-interest), §0.2 (7 stakeholders) |
| §5.3 | Identify concerns incl. purpose, suitability, feasibility of construction, risks, evolvability | **PASS** | L1 §0.3 (C1–C12); feasibility framed at §8.3 + LIM1 |
| §5.4 | Viewpoint specifies concerns, stakeholders, model kinds, conventions | **PASS** | L1 §0.4 — 5 model kinds, numbering conventions, correspondence rule |
| §5.5 | Every identified concern framed by ≥1 viewpoint | **PASS** | C1–C12 each mapped. **AQ-8 closed** — the Scientific Foundation concern was previously framed by nothing |
| §5.6 | Record correspondences; **known inconsistencies shall be recorded** | **PASS** | L1 §11 (correspondences, all 16 docs); §15 (8 recorded inconsistencies) |
| §5.7 | Record rationale **including alternatives considered** | **FAIL** | Present for L0/L1 ([[DECISION_LOG]] 16 decisions + 8 ADRs). **Absent for all six L2 documents** — itemized RD-1…RD-7 |

**Why MAJOR and not BLOCKING.** §5.7 requires rationale to be *recorded*. RD-1…RD-7 are now recorded **as debts, with the specific question each must answer** — which is materially different from the prior state, in which the absence itself was unrecorded and therefore invisible. Each is closable only by its original decider; confabulating a rationale after the fact would produce a defense that could not be wrong and therefore carries no information ([[01_SCIENTIFIC_FOUNDATION]] §7.3, applied to governance). A person-dependency is not a document defect, and the Phase A exit criteria do not include L2 rationale.

---

## 6. Governance completion — **FAIL** · BLOCKING (version headers)

| Check | Result | Evidence |
|---|---|---|
| Canonical documents carry version headers | **FAIL** · **BLOCKING** | `grep -L "Version:"` → **all six L2 documents lack one**: Object Model, Operating Model, Validation Framework, FCG, Pipeline, Failure Library. [[TAXONOMY_AND_NAMING_STANDARD]] §7 makes the version header **mandatory** |
| L1 artifact conforms to the folder standard | **FAIL** · MAJOR | `docs/Phase_A_Scientific_Foundation/` uses the retired word "Phase" structurally and is phase-coupled — violating [[TAXONOMY_AND_NAMING_STANDARD]] §2/§7 and D-008. Open owner decision **D-015** |
| Roadmap status claims match reality | **PASS** | False folder-migration checkbox corrected ([[DECISION_LOG]] C-3) |
| Taxonomy applied repo-wide | **PASS** | Layers/Programs/Stages/Gates disambiguated |
| Scope constraint declared and binding | **PASS** | [[DATA_FEASIBILITY_STUDY]] §4, re-grounded scientifically by **ADR-L1-006** |

**Why the missing version headers are BLOCKING — this is a freeze-specific defect, not a style issue.** A freeze declares *"version X of document Y is frozen."* Six of the sixteen canonical documents **have no version to name.** The certificate would be unable to state what it froze, and any future amendment would have no predecessor to be non-retroactive against — which silently voids the versioning discipline of [[FUTURE_GOVERNANCE_OUTLINES]] §3 before it is ever written. The defect is invisible during authoring and becomes load-bearing at exactly this gate, which is why no prior review caught it.

**Close by:** adding the mandated header to six files. No content changes. Not redesign.

---

## 7. Decision Log completion — **PASS**

| §5.7 requirement | Result | Evidence |
|---|---|---|
| Major architectural decisions recorded | **PASS** | 16 decisions (D-001…D-016) + 8 ADR pointers |
| Rejected alternatives recorded | **PASS** | Present on every decision. Where none were considered, recorded as such (D-009, D-010) rather than invented |
| Rationale recorded | **PASS** | Present on all; owner decisions honestly marked *"recorded only as 'per owner decision'"* |
| Consequences recorded | **PASS** | Present on all, including adverse ones (D-005 CONTESTED, D-011 duplication cost) |
| Traceability | **PASS** | Every decision cites related documents; §5 maps all 8 corrections to evidence |
| No duplication | **PASS** | ADRs referenced by pointer (§3), not copied |

**Self-reporting verified.** The log records against itself: **D-011** discloses that ~⅓ of the authored L1 restates corpus rules in new vocabulary and names the resulting drift hazard; **C-8** records that the L1 author overclaimed an exit item. A decision log that only records favourable facts is not a decision log.

---

## 8. Cross-reference validation — **FAIL** · MAJOR

| Check | Result | Evidence |
|---|---|---|
| Every wikilink resolves | **PASS (3 exceptions, all benign)** | Automated audit of all wikilink targets vs file basenames → 3 unresolved: `[[DOCUMENT_NAME]]` and `[[NAME]]` are **syntax examples** in TAXONOMY §7 / MIGRATION_PLAN §4; `[[RESEARCH_DATABASE_CONCEPT]]` is a **reserved** future document, explicitly outlined-not-authored in [[FUTURE_GOVERNANCE_OUTLINES]] §1 |
| No phantom documents | **PASS** | See §2 |
| 7 canonical docs cross-referenced to v3 mechanisms | **FAIL** · MAJOR | [[RESEARCH_OS_RECONCILIATION]] §6 requires a one-line v3 reference **inside each document**. None contains one. An explicit exit criterion ([[RESEARCH_OS_MASTER_ROADMAP]] §7) |

**Reserved ≠ phantom — the distinction is load-bearing.** A phantom reference asserts that a document *exists* or is *complete* when it does not (the *Market Inefficiency Foundation* case: claimed byte-for-byte preserved, never written). A reserved reference points at a document explicitly declared future. The first is a false statement about the present; the second is a true statement about the plan. Only the first is a defect.

---

## 9. Traceability validation — **PASS**

| Chain | Result | Evidence |
|---|---|---|
| Finding → resolution | **PASS** | AQ-1…AQ-8 each traced to a recorded position (L1 §15) or a closure |
| Decision → rationale → consequence | **PASS** | [[DECISION_LOG]] D-001…D-016 |
| Rule → justifying proposition | **PASS** | L1 R1–R20 each cite P1–P8; §0.4 makes a rule void when its proposition is refuted |
| Scope constraint → science | **PASS** | [[DATA_FEASIBILITY_STUDY]] §4 → **ADR-L1-006** → LIM1 → R14 |
| Correction → evidence | **PASS** | [[DECISION_LOG]] §5, C-1…C-8, each with a re-runnable check |
| Exit criterion → checklist item | **PASS** | This document |

---

## 10. Roadmap integrity — **PASS**

| Check | Result | Evidence |
|---|---|---|
| Single canonical roadmap declared | **PASS** | D-004; [[RESEARCH_OS_RECONCILIATION]] §3 |
| Status claims verifiable | **PASS** | C-3 corrected the one false checkbox; C-4 corrected L1 status |
| Dependency edges correct | **PASS** | C-5 added `SCOPE→L6`, `L3→L6`, `L3→L4`, each with a stated reason |
| Exit checklist matches reality | **PASS** | 4 open items, each traceable to a checklist FAIL here |
| Programs classified by feasibility | **PASS** | D-006; P5/P6 retained as Future Capability |

---

## 11. Migration readiness — **FAIL** · BLOCKING

| Check | Result | Evidence |
|---|---|---|
| Migration plan is executable | **FAIL** | Was unexecutable as written. `git mv --dry-run …RESEARCH_OBJECT_MODEL.md docs/research_os/` → `fatal: not under version control`. **Plan corrected** (Step 0 inserted, C-7 / D-014); **execution still blocked on §1** |
| Ordering is correct | **PASS** | baseline → rename → annotate. Bundling would render moves as adds, defeating the plan's own §4 rename-only validation |
| Repository structure matches roadmap §8 | **FAIL** | 7 canonical docs remain in `docs/Institutional_Research_Architecture/`; roadmap §8 places them in `research_os/` |
| Declared folders will survive the baseline commit | **FAIL** · MINOR | `docs/research_programs/` and `docs/references/` contain **0 files**. Git does not track empty directories — both vanish at Step 0. Needs `.gitkeep` or creation at move time |
| Migration is reversible | **PASS** | All `git mv`; reverse-`git mv` restores. No data touched |

---

## 12. Phase gate approval — **FAIL** · BLOCKING

| Check | Result | Evidence |
|---|---|---|
| Independent adversarial sign-off | **FAIL** | Unmet. Required by [[RESEARCH_OS_MASTER_ROADMAP]] §7: *"Validation Reviewer, **not the author**"* |
| Sign-off is dischargeable by the current author | **FAIL — structurally** | [[01_SCIENTIFIC_FOUNDATION]] **LIM6** / **ADR-L1-007**: the institution has one researcher; the party prohibited from seeing OOS data is the same party who must audit the prohibition |

**Why this cannot be waived.** This is the one exit criterion whose entire purpose is that the author cannot self-certify. An author who declares their own work adversarially reviewed has not satisfied it — they have deleted it. Waiving it would be the governance analogue of **R7.4 (threshold migration)**: moving the criterion after seeing that it fails. Per LIM6 the institution may *substitute mechanisms that do not require role separation*, or *declare the requirement unmet* — but **not** describe sequential role-play by one mind as independence.

---

## Summary

| # | Item | Result | Severity |
|---|---|---|---|
| 1 | Repository integrity | **FAIL** | **BLOCKING** |
| 2 | Canonical document inventory | PASS | — |
| 3 | Scientific completeness | PASS | — |
| 4 | Architecture completeness | **FAIL** | **BLOCKING** (AQ-1) |
| 5 | ISO 42010 compliance | **FAIL** (§5.7) | MAJOR |
| 6 | Governance completion | **FAIL** | **BLOCKING** (version headers) |
| 7 | Decision Log completion | PASS | — |
| 8 | Cross-reference validation | **FAIL** | MAJOR |
| 9 | Traceability validation | PASS | — |
| 10 | Roadmap integrity | PASS | — |
| 11 | Migration readiness | **FAIL** | **BLOCKING** |
| 12 | Phase gate approval | **FAIL** | **BLOCKING** |

**5 PASS · 7 FAIL — of which 5 BLOCKING, 2 MAJOR.**

**Not one FAIL requires redesign.** The blocking set is: one commit · three lines of exemplar text · six version headers · one signature. The distance from here to GO is mechanical, and that is the strongest statement this checklist makes about the architecture — the science is done, and what remains is bookkeeping that has not yet been done.

**→ Decision: [[PHASE_A_FREEZE_CERTIFICATE]]**
