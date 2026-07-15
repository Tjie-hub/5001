# Phase A — Freeze Certificate

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Issuing authority:** Chief Scientific Architect / ISO 42010 Architecture Editor / Phase-Gate Authority
**Basis:** [[PHASE_A_FREEZE_CHECKLIST]] v1.0 — 12 items, 5 PASS, 7 FAIL (5 BLOCKING, 2 MAJOR)
**Subject:** Institutional Research OS — Phase A (Layers L0 + L1 + L2)

---

## 1. Executive Summary

**Phase A is scientifically and architecturally complete. It is not yet freezable.**

Those two sentences are not in tension. The architecture has survived multiple adversarial reviews; the remaining defects are bookkeeping that was never done, and the gap between this certificate and a GO is **one commit, three lines of text, six document headers, and one signature.**

But a freeze is a *state*, not an *opinion*. It asserts that an identified set of documents, at identified versions, is durable and canonical from a stated moment. Three of those preconditions are objectively absent:

1. **There is nothing to freeze.** Every Research OS document is untracked. `git ls-files` returns empty. A freeze certificate that names no revision certifies nothing.
2. **Six of sixteen canonical documents have no version.** A freeze declares *"version X is frozen."* Six documents cannot complete that sentence.
3. **A freeze ratifies.** The Object Model still teaches `L3 Order Book`, `BBO`, `Nanosecond`, and `Latency Arbitrage` as its worked exemplars — data the institution does not have and cannot obtain. Freezing makes that instruction canonical, and per **ADR-L1-006** it instructs researchers to author unfalsifiable — therefore inadmissible — hypotheses.

None of these is a scientific objection. **The science is done.** These are the mechanical preconditions of the word "frozen" meaning anything.

---

## 2. Scope of Phase A

Phase A = **L0 (Governance & Scope) + L1 (Scientific Foundation) + L2 (Research Architecture)**, per **D-010**.

**In scope:** the scientific charter; the epistemology and evidence standard; the domain and mechanism taxonomies; the Research Object Model, Operating Model, Validation Framework, Feature Computation Graph, Research Pipeline, and Failure Library; the governance layer (feasibility, taxonomy, reconciliation, roadmap, decision log); one worked end-to-end example.

**Out of scope, and not assessed by this certificate:** L3–L8; all implementation; Program execution (P0–P6); Phase B. Per **D-001**, `RESEARCH_MASTER_PLAN.md` v3 is a separate frozen artifact executed *inside* this framework as Program P0 and is not re-certified here.

---

## 3. Architecture Status — **COMPLETE, with one blocking defect**

The architecture is sound and is treated as correct. Findings previously raised concerning implementation leakage, executable inheritance, implementation readiness, L3/L5 realization, and architecture incompleteness are **formally withdrawn** and are not re-litigated.

Two findings remain live, and both are ontology defects internal to Phase A — neither is an implementation concern:

- **AQ-1 (Critical, BLOCKING)** — the Object Model's exemplars contradict the binding scope constraint. Evidence: `RESEARCH_OBJECT_MODEL.md:15,28,35` vs [[DATA_FEASIBILITY_STUDY]] §4.3–§4.4. **A three-line exemplar edit.** Not redesign — the falsification review classified it as the highest-leverage action in the program.
- **AQ-2 (High)** — `Accepted Knowledge Object.decay_monitor_id` references a Decay Monitor object that does not exist (`grep -c` → 1 reference, 0 definitions). The Core/Extension partition (**D-005**) is refuted by the ontology's own referential structure, and L1 **P7** makes decay monitoring constitutive rather than optional.

**AQ-4** (bit-identity) is managed by **ADR-L1-005** and recorded at L1 §15.5. **AQ-6** (single-researcher unexecutability) is declared, not absorbed, by **ADR-L1-007**. **AQ-8** is closed.

---

## 4. Scientific Status — **COMPLETE**

**Finding #4 is CLOSED.** [[01_SCIENTIFIC_FOUNDATION]] exists and supplies all 13 required elements ([[PHASE_A_FREEZE_CHECKLIST]] §3).

The finding was audited rather than assumed (**D-011**). It proved **true about artifacts and imprecise about content**: the corpus contained scientific *commitments* — distributed across L2 as gates — but no scientific *foundation*. It stated its rules and defended none of them. Three objects it referenced (mechanism taxonomy, domain set, literature corpus) had no artifact, and *falsifiability* was asserted as a gate criterion at Pipeline S3 and never defined anywhere.

**Disclosed limitation of the artifact.** Roughly one third of the authored L1 restates corpus rules in new vocabulary (R18 ≈ Validation Framework §3; §2.4 custody ≈ Operating Model §7). This is a real drift hazard: two canonical documents now state the same rule in different words. It is recorded — not concealed — at **D-011**, mitigated by L1 §11 recording each correspondence per §5.6, and governed by the rule **L1 owns the reason, L2 owns the rule.** A purely referential L1 was considered and rejected on one ground: **rationale is not compressible by reference.** You cannot cite a defense that does not exist.

---

## 5. ISO/IEC/IEEE 42010 Status — **CONFORMANT except §5.7**

| Clause | Status |
|---|---|
| §5.2 System & stakeholders | ✅ PASS |
| §5.3 Concerns (purpose, suitability, feasibility, risks, evolvability) | ✅ PASS |
| §5.4 Viewpoint (concerns, stakeholders, model kinds, conventions) | ✅ PASS |
| §5.5 Every concern framed by ≥1 viewpoint | ✅ PASS — **AQ-8 closed** |
| §5.6 Correspondences + known inconsistencies recorded | ✅ PASS — 8 recorded at L1 §15 |
| §5.7 Rationale incl. alternatives | ⚠️ **PARTIAL** — complete for L0/L1; absent for all six L2 documents (RD-1…RD-7) |

The §5.7 gap is **MAJOR, non-blocking**. The debts are now recorded *with the specific question each must answer*, which differs materially from the prior state in which the absence was itself unrecorded. They are closable only by their original decider. Inventing rationale after the fact would yield a defense that could not be wrong and therefore carries no information — the governance analogue of the retro-fitted mechanism L1 §7.3 prohibits.

---

## 6. Repository Status — **FAIL, BLOCKING**

```
$ git ls-files docs/Institutional_Research_Architecture/ docs/governance/ \
               docs/roadmap/ docs/research_os/ docs/Phase_A_Scientific_Foundation/
(empty)
```

The entire Phase A corpus — 16 canonical documents, every governance artifact, this certificate — exists only in the working tree. Consequences:

- **No freeze is possible.** There is no revision to name.
- **The migration plan was unexecutable as written** (**D-014**): `git mv` fails on untracked files (`fatal: not under version control`, verified by dry run). The migration was never blocked on approval — it was blocked on a precondition no document had noticed. Plan corrected; execution still blocked.
- **`docs/research_programs/` and `docs/references/` will not survive** the baseline commit — both are empty and git does not track empty directories (MINOR).

This is the root blocker. **Every other blocker is cheaper to fix than this one, and this one is a single command.**

---

## 7. Governance Status — **FAIL, BLOCKING**

| Item | Status |
|---|---|
| Version headers on canonical documents | ❌ **BLOCKING** — all six L2 documents lack one, though [[TAXONOMY_AND_NAMING_STANDARD]] §7 makes it **mandatory**. A freeze cannot name a version that does not exist |
| L1 artifact path conforms to the taxonomy | ❌ MAJOR — `docs/Phase_A_Scientific_Foundation/` uses the retired word "Phase" structurally, violating D-003/D-008. **Open owner decision D-015** |
| Per-document v3 cross-references | ❌ MAJOR — explicit exit criterion ([[RESEARCH_OS_RECONCILIATION]] §6); no document contains one |
| Decision Log (§5.7 register) | ✅ PASS — 16 decisions, 8 ADR pointers, 7 itemized debts, 8 evidenced corrections |
| Roadmap status claims verifiable | ✅ PASS — false migration checkbox corrected (C-3) |
| Phantom references | ✅ PASS — zero remain |
| Taxonomy applied; scope constraint binding | ✅ PASS |

**Eight corrections were applied to the canonical corpus this cycle**, each backed by a re-runnable check ([[DECISION_LOG]] §5). Two are worth naming: the roadmap asserted the folder migration complete while [[REVISION_IMPACT_ASSESSMENT]] §2 said it was only planned — two canonical documents contradicting each other; and **C-8**, in which the L1 author's own overclaim of a discharged exit item was reversed.

---

## 8. Remaining Findings — categorised per Part 8

Every open item belongs to exactly one category. **No Phase B work appears here.** No item is future work invented by this certificate; each is either an exit criterion or an objectively evidenced defect.

| # | Finding | Category | Severity | Close by |
|---|---|---|---|---|
| 1 | Corpus untracked; no revision to freeze | **E** Repository | **BLOCKING** | One commit ([[MIGRATION_PLAN]] Step 0) |
| 2 | AQ-1 — Object Model exemplars contradict binding scope | **A** Architecture defect | **BLOCKING** | 3-line exemplar edit |
| 3 | Six L2 documents lack mandatory version headers | **F** Governance | **BLOCKING** | 6 headers, no content change |
| 4 | Independent adversarial sign-off unmet | **F** Governance | **BLOCKING** | Signature — not by the author (LIM6) |
| 5 | Folder migration decided, not executed | **E** Repository | **BLOCKING** | `git mv`, after #1 |
| 6 | AQ-2 — `decay_monitor_id` dangling; Core/Extension refuted | **A** Architecture defect | MAJOR | Define the object, or repartition (D-005) |
| 7 | Per-document v3 cross-references absent | **D** Documentation | MAJOR | 7 one-line additions |
| 8 | §5.7 rationale absent for L2 (RD-1…RD-7) | **B** Ambiguity | MAJOR | Original decider only |
| 9 | D-015 — L1 path violates the taxonomy | **F** Governance | MAJOR | Owner decision |
| 10 | Empty declared folders will not survive Step 0 | **E** Repository | MINOR | `.gitkeep` |
| 11 | `[[RESEARCH_DATABASE_CONCEPT]]` unresolved | **G** Future phase | NONE | Reserved, not phantom — correctly deferred |

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Corpus loss before baseline commit** | Medium | **Severe** | The entire Phase A corpus is untracked. A lost working tree loses everything — L1, the decision log, this certificate. **This is the largest live risk in the program and it is one command from zero.** |
| **AQ-1 ratified by freeze** | High if frozen now | **Severe** | Freezing canonises an ontology that teaches unfalsifiable hypotheses. Every researcher instantiating a Hypothesis reads that document |
| **Version-header gap voids amendment discipline** | High if frozen now | Moderate | Non-retroactive amendment requires a predecessor version to be non-retroactive *against*. Six documents have none |
| **Self-certification of adversarial review** | Medium | **Severe** | LIM8: rules get satisfied in letter and violated in spirit under pressure to close. This certificate refuses the waiver rather than relying on discipline |
| **L1↔L2 rule drift** (D-011) | Medium | Moderate | Recorded at L1 §11 per §5.6; governed by *L1 owns the reason, L2 owns the rule* |
| **Freeze pressure converts conditions to intentions** | **High** | Moderate | The conditions are enumerated with re-runnable evidence so that closure is verifiable rather than asserted |

---

## 10. Formal Phase-Gate Decision

# NO-GO

**for Phase A Freeze, as of 2026-07-15.**

**This is not a rejection of the architecture.** The architecture is approved. The science is complete. Finding #4 is closed. Nothing in the blocking set requires redesign, new architecture, or new scientific work.

**The decision is compelled by one fact that admits no judgement:** the corpus is untracked. A freeze is a claim about durability at an identified revision. There is no revision. A certificate issuing GO would refer to nothing — it would be a statement about files that exist only in a working tree, on a machine, unbacked. That alone forecloses GO, independent of every other finding.

**GO WITH CONDITIONS was considered and rejected.** It is the right instrument when conditions can close *in parallel* with the approved state taking effect. Here, all five blocking conditions are **preconditions of the state transition itself** — you cannot freeze first and become tracked, versioned, and reviewed afterwards. A conditional GO on a transition whose conditions must precede it is a NO-GO with softer wording, and the softer wording is precisely what LIM8 warns will be read as GO while the conditions quietly become intentions.

### Conditions for GO — exhaustive, objectively necessary, none invented

| | Condition | Category | Effort |
|---|---|---|---|
| 1 | **Baseline commit** — track the corpus; the freeze acquires a referent | E | One command |
| 2 | **AQ-1** — reconcile Object Model exemplars with the binding scope constraint | A | Three lines |
| 3 | **Version headers** — add the mandated header to six L2 documents | F | Six lines |
| 4 | **Folder migration** — execute [[MIGRATION_PLAN]] §3 (after #1) | E | One commit |
| 5 | **Independent adversarial sign-off** — Validation Reviewer, not the author | F | One signature |

Conditions 1–4 are mechanical and can be completed in a single session. **Condition 5 cannot be discharged by the author of this certificate under any circumstances** — that is its entire purpose (LIM6, ADR-L1-007). Per LIM6 the institution may substitute mechanisms that do not require role separation, or formally declare the requirement unmet and mark affected claims. It may not describe sequential role-play by one mind as independence.

**On closure:** conditions 6–11 of §8 are MAJOR or MINOR and do **not** block the freeze. They are recorded, traceable, and closable after it.

---

## 11. Certification

This certificate is issued against re-runnable evidence. Every FAIL in [[PHASE_A_FREEZE_CHECKLIST]] cites a command or a line reference a third party can re-execute. No item rests on the issuer's judgement.

**Issued:** 2026-07-15 · **Decision:** NO-GO · **Distance to GO:** one commit, three lines, six headers, one signature.

**This certificate is itself untracked** and shares the corpus's durability risk (§9, row 1). It should be included in the baseline commit it demands.

> **Re-issue rule:** this certificate is superseded, never edited. When the conditions close, a **v1.1** is issued against a re-run of [[PHASE_A_FREEZE_CHECKLIST]] and must name the baseline commit SHA it certifies. A certificate that cannot name the revision it froze has not certified a freeze.

---

*Recorded as an architectural act per [[DECISION_LOG]] **D-012**. Supersedes the freeze assessment at **D-016**, which reached the same decision on three of the five blocking grounds; the version-header defect (§7) and AQ-1's blocking status (§3) were identified by this audit.*
