# Decision Log — Institutional Research OS

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Standard:** ISO/IEC/IEEE 42010:2011 §5.7 — *architecture rationale shall be recorded, including alternatives considered*
**Authority:** The corpus-wide register of architectural, scientific, and governance decisions. A decision that is not recorded here has no recorded rationale, and per §5.7 the architecture description is non-conformant to that extent (§4 tracks the outstanding debt).

**Scope discipline — this log does not duplicate.** Where a decision already carries a full ADR in another canonical document, this log records a **pointer**, not a copy (§3). Where a decision was made and its rationale exists only as prose, this log **transcribes** it into decision form. Where a decision was made and its rationale was **never recorded**, this log says so rather than inventing one (§4). Retro-fitting a rationale onto a decision made by someone else, without evidence of their reasoning, would be fabrication — the governance analogue of the retro-fitted mechanism that [[01_SCIENTIFIC_FOUNDATION]] §7.3 prohibits.

---

## 1. Register — governance & scope decisions (L0)

### D-001 · Research OS complements and supersets v3; it does not replace it
**Status:** ACCEPTED · **Date:** 2026-07-14/15 · **Type:** Governance
**Decision:** The Research OS is the institutional framework; `RESEARCH_MASTER_PLAN.md` v3 is the first fully-implemented Research Program executed inside it (Program P0).
**Alternatives considered:** *replace v3* — rejected: v3 is not a plan on paper but a live, tested system (Phase C gatekeeper verified end-to-end 2026-07-14); replacing it discards working infrastructure. *Run in parallel* — rejected: two master plans with clashing phase schemes fork the repository and create two sources of truth.
**Rationale:** The OS's job is to generalize the frame, not rebuild the engine. v3 becomes the reference implementation the OS is validated against.
**Consequences:** Precedence rules required (D-004). v3's frozen invariants are inherited, not re-litigated. On conflict about a *built* mechanism, v3 wins; on conflict about *scientific method or governance*, the OS wins.
**Related:** [[RESEARCH_OS_RECONCILIATION]] §2, §5

### D-002 · The Data Capability Matrix is the binding scope constraint
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance → later re-grounded as Scientific (D-011)
**Decision:** No Research Program may register a hypothesis whose `required_data` is not classified *Available Today* or *Obtainable Later* in [[DATA_FEASIBILITY_STUDY]] §4.
**Alternatives considered:** *scope by scientific ambition, procure data later* — rejected: it architects Layers L3–L8 against datasets that may never exist, which was review finding W1 (Critical).
**Rationale:** Every downstream decision — scope, domains, programs, object model — is downstream of what data actually exists. The inventory was measured from the production database, not assumed.
**Consequences:** The three original Microstructure Programs were re-classed to proxy tiers; P5/P6 retained as Future Capability only. Later re-grounded on scientific rather than administrative authority — see **ADR-L1-006** (§3).
**Related:** [[DATA_FEASIBILITY_STUDY]] §4, §5 · [[RESEARCH_OS_MASTER_ROADMAP]] §3

### D-003 · "Phase" is retired from structural use
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** Six structural axes, one term each: Layer (L0–L8) · Program (P0–P6) · Stage (S1–S10) · Gate (G1–G4) · Step · Lifecycle State. "Phase" survives only in the proper noun `RESEARCH_MASTER_PLAN.md`, which predates the standard and is frozen.
**Alternatives considered:** *reserve "Phase" for the Layers axis* (review R3's recommendation) — rejected: it collides with v3's frozen Phases A–H, which are delivery milestones on a different axis. Retiring the word entirely was the only option that does not require editing a frozen document.
**Rationale:** "Phase" was overloaded across five incompatible axes; "Phase A" named both the foundation layer and the completed conceptual work. The ambiguity propagates into every downstream document and status report.
**Consequences:** Repo-wide vocabulary change. One known violation remains open — see **D-015**.
**Related:** [[TAXONOMY_AND_NAMING_STANDARD]] §2, §8

### D-004 · Single canonical roadmap
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** [[RESEARCH_OS_MASTER_ROADMAP]] is the one roadmap, holding two separated tiers: Institutional Layers (L0–L8) and Research Programs (P0…). v3 remains frozen and canonical *for its scope*, referenced as P0's specification rather than duplicated.
**Alternatives considered:** *two roadmaps with a cross-reference* — rejected: leaves ownership ambiguous and status reporting forked.
**Rationale:** Precedence must be decidable by reading one document.
**Consequences:** Any document implying a different relationship is subordinate.
**Related:** [[RESEARCH_OS_RECONCILIATION]] §3

### D-005 · Object model split into Core (mandatory) vs Extension (additive)
**Status:** **CONTESTED** — refuted by the ontology's own referential structure · **Date:** 2026-07-15 · **Type:** Architectural
**Decision:** Core ships first (Hypothesis, Dataset, Feature, Experiment, Knowledge Object + the foundational science objects); Regime, Cost Model, Decay Monitor, Reviewer Sign-off, Lineage Edge are additive extensions.
**Alternatives considered:** *ship all objects at once* — rejected as over-engineering the first release.
**Rationale:** Do not over-engineer the first release; several extensions already exist as v3 mechanisms, so "optional" meant "not required to *define* the first release," not "unbuilt."
**Consequences:** **The partition does not hold as drawn.** `Accepted Knowledge Object.decay_monitor_id` is a Core field referencing an Extension object — the Core cannot be instantiated without the Extension (finding AQ-2 / RQ-4). Additionally [[01_SCIENTIFIC_FOUNDATION]] P7 makes decay monitoring *constitutive* of Accepted Knowledge, not optional: a claim whose mortality is untracked cannot be retired, and an unretireable claim contradicts P3's revocability. **Resolution required before the partition is used.** Open — see §4.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §4 · [[RESEARCH_OBJECT_MODEL]] · [[01_SCIENTIFIC_FOUNDATION]] §15.2

### D-006 · Programs classified Current vs Future; nothing deleted
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** P0 delivered · P1–P4 Current (proxy tiers) · P5 Future (Institutional) · P6 Out of scope. Future directions are preserved and classified, never deleted.
**Alternatives considered:** *delete infeasible programs* — rejected: destroys legitimate research vision and the record of why it is out of reach. *Keep them unmarked* — rejected: that is exactly the W1 failure.
**Rationale:** Classification preserves ambition while preventing work from being architected against unobtainable data.
**Consequences:** P5/P6 are not "deferred research." Per **ADR-L1-006** they are **currently unfalsifiable claims** — correctly retained, correctly excluded from executable scope.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §3 · [[DATA_FEASIBILITY_STUDY]] §4.3–§4.4

### D-007 · Status escalated NO-GO → GO WITH CONDITIONS
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** Phase A moves from conditional NO-GO to GO WITH CONDITIONS.
**Rationale:** The six blocking items of [[PHASE_A_ARCHITECTURE_REVIEW]] §9 were addressed: feasibility study authored, scope re-grounded, v3 reconciled, taxonomy fixed, programs classified, worked example authored. Remaining work is governance and documentation, not scientific redesign.
**Consequences:** Freeze is gated on the §7 exit checklist, not on new architecture. See **D-016** for the current freeze assessment.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §1

### D-008 · Concern-based folder architecture, not phase-coupled
**Status:** ACCEPTED — **not yet executed** · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** `roadmap/ governance/ research_os/ research_programs/ references/`. Status lives in the roadmap, never in folder names.
**Alternatives considered:** *organize by Phase/Layer* (`L1/`, `L2/`) — rejected: couples the repository to a transient roadmap and reintroduces the retired vocabulary (D-003).
**Rationale:** Folders should track stable concerns; roadmap status is not stable.
**Consequences:** Migration of the seven canonical documents was **planned, not executed** — the roadmap checkbox asserting completion was false and is corrected this revision. Execution is blocked on D-014.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §8 · [[MIGRATION_PLAN]]

### D-009 · Multiple-Testing Family Policy deferred to P1
**Status:** ACCEPTED (owner decision) · **Date:** 2026-07-15 · **Type:** Scientific / scope
**Decision:** The Multiple-Testing Family Policy is a P1 deliverable, not a Phase-A freeze blocker.
**Alternatives considered:** **Not recorded at the time.** [[PHASE_A_ARCHITECTURE_REVIEW]] §4 had classified it **P0 — blocker**; the owner overrode. The reasoning for the override is not documented anywhere in the corpus.
**Rationale:** Recorded only as "per owner decision" ([[RESEARCH_OS_MASTER_ROADMAP]] §5).
**Consequences:** **A live tension the log must not paper over.** [[01_SCIENTIFIC_FOUNDATION]] §5.2 makes the family denominator one of six mandatory elements of a falsifiable claim, and R7.5 prohibits narrowing it post hoc. Assumption A7 ("the institution's own multiplicity is countable") is the assumption most easily destroyed by ordinary behavior, and LIM3 holds that the denominator is estimable but never knowable. Deferring the *policy* does not defer the *requirement*: hypotheses registered before the policy exists must still declare a family, and those declarations will be un-adjudicated by any standard until P1 lands.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §5 · [[01_SCIENTIFIC_FOUNDATION]] §5.2, A7, LIM3

### D-010 · The Research OS architecture stays inside Phase A as L2
**Status:** ACCEPTED (owner decision) · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** "Phase A" (old scheme) = L0 + L1 + L2. The Object Model, Operating Model, Validation Framework, FCG, Pipeline, and Failure Library remain Phase-A artifacts, tagged L2.
**Alternatives considered:** [[PHASE_A_ARCHITECTURE_REVIEW]] **R2** recommended splitting them out as Phase B (Research Architecture), on the argument that they are "strong Phase B docs masquerading as Phase A support." The owner declined. The reasoning for declining is not recorded.
**Rationale:** Recorded only as "per owner decision" ([[TAXONOMY_AND_NAMING_STANDARD]] §3). The L0/L1/L2 split makes responsibilities explicit without moving the work.
**Consequences:** Phase A carries both the science and the architecture that supports it. This is why L1's absence was felt as "Phase A is both done and undefined" — the layer distinction resolved the ambiguity without relocating any document.
**Related:** [[TAXONOMY_AND_NAMING_STANDARD]] §3 · [[PHASE_A_ARCHITECTURE_REVIEW]] §5 R2

---

## 2. Register — decisions from this review (2026-07-15)

### D-011 · Finding #4 is upheld in substance but restated; L1 authored rather than assembled by reference
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Architectural / Scientific
**Context:** Finding #4 stated "L1 Scientific Foundation has no artifact." An audit tested each required L1 element against the canonical corpus rather than assuming the finding true.
**Audit result:** The corpus contained **scientific commitments but no scientific foundation.** Of thirteen required elements: five were present but distributed and undefended (philosophy, paradigm, method, reproducibility, scope); four were partial (epistemology had custody tiers but no theory of evidence; inefficiency principles had `half_life_estimate` and `persistence_theory` but no requirement to answer persistence; mechanisms had a schema but no taxonomy; falsifiability was *asserted* as a gate criterion at Pipeline S3 and never *defined*); four were wholly absent (market assumptions, evidence hierarchy, document relationships, rationale).
**Decision:** Finding #4 is **true as stated about artifacts** — no document framed the Scientific Foundation concern, so under 42010 §5.5 the concern was framed by nothing — and **imprecise as stated about content**. The precise finding is: *the corpus states its scientific rules and defends none of them, and three of its own referenced objects (mechanism taxonomy, domain set, literature corpus) have no artifact.* L1 was authored rather than assembled by reference.
**Alternatives considered:** *Canonical-minimal L1 — a short document that formalizes by reference only.* Rejected on one ground: **rationale is not compressible by reference.** You cannot cite a defense that does not exist, and AQ-7 established that no canonical document defends any of its choices. The genuinely absent elements (assumptions, evidence hierarchy, mechanism taxonomy, domain partition, rationale, ADRs) had no referent to point at.
**Consequences — recorded against this decision, not hidden:** the authored L1 is ~800 lines where a purely referential one would be ~300. The excess is derivation, which was the point; but roughly a third of it **restates corpus rules in new vocabulary** (R18 restates [[RESEARCH_VALIDATION_FRAMEWORK]] §3; §2.4's custody states restate [[RESEARCH_OPERATING_MODEL]] §7; §5.2's six elements restate the Hypothesis Object's fields). **This creates a real drift hazard: two canonical documents now state the same rule in different words, and amending one will silently desynchronize the other.** The hazard is mitigated, not eliminated, by [[01_SCIENTIFIC_FOUNDATION]] §11, which records each correspondence explicitly per 42010 §5.6. The governing principle going forward: **L1 owns the reason, L2 owns the rule.** A future editor who finds the two disagreeing should treat L2 as authoritative on *what* the rule is and L1 as authoritative on *why* it exists.
**Related:** [[01_SCIENTIFIC_FOUNDATION]] §11, §13.1 · finding AQ-8

### D-012 · This review is recorded as an architectural decision
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** The 2026-07-15 Phase-A condition-resolution review is itself a recorded architectural act: it audited Finding #4 rather than executing it, produced this log, corrected four false or phantom statements in the canonical corpus, and repaired an unexecutable migration plan.
**Rationale:** 42010 §5.7 requires rationale for architectural decisions. A review that changes canonical documents *is* an architectural decision and would otherwise be the only unrecorded one in the register — the same defect it was convened to fix.
**Consequences:** The corrections in §5 are traceable to this decision. The review found no grounds to redesign anything, consistent with its mandate.
**Related:** this document · [[RESEARCH_OS_MASTER_ROADMAP]] §7

### D-013 · L1 records L2 inconsistencies; it does not resolve them
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Architectural
**Decision:** Pointer to **ADR-L1-008** ([[01_SCIENTIFIC_FOUNDATION]] §14). Not restated here.
**Consequences:** AQ-1, AQ-2, AQ-3, AQ-4, AQ-6 are recorded as 42010 §5.6 inconsistencies in [[01_SCIENTIFIC_FOUNDATION]] §15 and remain open. RL-2 stays blocked on them. Each is a small edit to an existing document; none is scientific redesign.
**Related:** [[01_SCIENTIFIC_FOUNDATION]] §15

### D-014 · A baseline commit is a precondition of migration, not a step within it
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance
**Context:** [[MIGRATION_PLAN]] §3 specified `git mv` for each canonical document. **Every Research OS document in this repository is untracked.** `git mv` fails on an untracked file (`fatal: not under version control` — verified by dry run 2026-07-15).
**Decision:** The migration plan is **unexecutable as written**. A baseline commit that tracks the corpus is a hard precondition, inserted as Step 0. The rename commit follows; the annotation pass follows that.
**Alternatives considered:** *`mv` + `git add` instead of `git mv`* — rejected: git infers renames from content similarity, so this happens to preserve history for unmodified files, but it is fragile and defeats the plan's own §4 validation check ("`git status` shows only renames"). *Bundle baseline + move in one commit* — rejected: the move would appear as adds, not renames, destroying the reviewability the plan exists to protect.
**Rationale:** The plan's non-destructive, history-preserving guarantee is void until the history exists. There is no history to preserve for an untracked file.
**Consequences:** Repository maturity is the binding constraint on the folder migration, and the migration was never blocked on approval alone — it was blocked on a precondition no document had noticed. Three ordered commits: **baseline → rename → annotate**.
**Related:** [[MIGRATION_PLAN]] §3, §6

### D-015 · The L1 artifact's location violates the taxonomy standard
**Status:** **OPEN — owner decision required** · **Date:** 2026-07-15 · **Type:** Governance
**Context:** [[01_SCIENTIFIC_FOUNDATION]] was authored at `docs/Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md` at the owner's explicit instruction. That path violates two canonical decisions: **D-003** (the word "Phase" is retired from structural use) and **D-008** (folders are concern-based, never phase-coupled; L1+L2 live in `research_os/`).
**Options:** (a) `git mv` to `docs/research_os/SCIENTIFIC_FOUNDATION.md`, conforming to D-003/D-008 — recommended, and cheapest before the baseline commit; (b) keep the path and record a standing exception, which weakens D-003 by precedent; (c) amend D-003.
**Rationale for recording rather than deciding:** the path was an explicit instruction, and a governance standard is not something an editor may silently enforce against its owner. But an unrecorded violation of a canonical standard is exactly the failure mode that produced the phantom references corrected in §5 — so it is recorded.
**Consequences:** Until resolved, the repository contains a canonical document at a path its own canonical taxonomy prohibits.
**Related:** [[TAXONOMY_AND_NAMING_STANDARD]] §2, §7 · [[MIGRATION_PLAN]] §2

### D-016 · Phase A freeze assessment
**Status:** **SUPERSEDED by D-017** (same decision, two further blocking grounds) · **Date:** 2026-07-15 · **Type:** Governance
**Decision:** **NO-GO for Phase A Freeze** — narrowly, and on governance grounds only, not scientific ones.
**Rationale:** The scientific foundation is complete and Finding #4 is closed. Freeze is blocked by three items, none requiring redesign: (i) the corpus is **untracked** — an unfrozen repository cannot host a frozen phase, and "frozen" is a claim about durability that `git ls-files` currently refutes (D-014); (ii) **independent adversarial sign-off** is unmet and is undischargeable by the author by construction (LIM6 / ADR-L1-007); (iii) the **per-document v3 cross-reference** exit item remains open ([[RESEARCH_OS_RECONCILIATION]] §6).
**Alternatives considered:** *GO, treating the three as post-freeze cleanup* — rejected: (i) makes the freeze unverifiable, and (ii) is the one exit criterion whose entire purpose is that the author cannot self-certify. Waiving it would be the governance analogue of R7.4 (threshold migration).
**Consequences:** Freeze is one commit and one review away. All five open findings (AQ-1..AQ-4, AQ-7) are small edits to existing documents.
**Related:** [[RESEARCH_OS_MASTER_ROADMAP]] §7 · [[01_SCIENTIFIC_FOUNDATION]] §16

### D-018 · Phase A Freeze certified GO WITH CONDITIONS at `de98c17`
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance · **Supersedes:** D-017
**Decision:** **GO WITH CONDITIONS**, one condition: independent adversarial sign-off by a Validation Reviewer who is not the author. **The freeze does not take effect until that is recorded.** Certificate: [[PHASE_A_FREEZE_CERTIFICATE]] v2.0 against [[PHASE_A_FREEZE_CHECKLIST]] v2.0 (12 items, 10 PASS / 2 FAIL).
**Context:** Four of D-017's five blocking grounds resolved by evidence at `de98c17` — corpus tracked (`222d57f`), migration executed as renames (`f5a017c`), version headers added, AQ-1 exemplars reconciled (`de98c17`).
**Alternatives considered:** **GO — rejected**: this authority authored the corpus and cannot satisfy a criterion whose text reads *"not the author."* Certifying it would delete the criterion rather than meet it (R7.4). **NO-GO — rejected**: it would imply outstanding work, and none remains within this authority's power.
**Rationale — and why this does not contradict D-017.** D-017 rejected GO WITH CONDITIONS on the reasoning that *a conditional GO on a transition whose conditions must precede it is a NO-GO in softer wording.* **That reasoning still holds; the facts changed.** At D-017, four of five conditions were work the author had not done — a conditions list there would have offloaded the author's own undone work, which is exactly how conditions decay into intentions. Those four are done. The remaining condition is **not work**: it is a second signature on completed work, by a party this authority cannot be. Different object, different instrument.
**Consequences:** Phase A is **certified-ready but NOT FROZEN**. No document may describe it as frozen until sign-off is recorded and v3.0 of the certificate issues naming the reviewer, date, and revision. The live risk is no longer corpus loss but **self-certification under closure pressure** (LIM8) — refused here by mechanism rather than by discipline.
**Related:** [[PHASE_A_FREEZE_CERTIFICATE]] v2.0 · [[PHASE_A_REVIEW_PACKAGE]] · [[01_SCIENTIFIC_FOUNDATION]] LIM6, LIM8, ADR-L1-006/007

### D-017 · Phase A Freeze certified NO-GO; GO WITH CONDITIONS explicitly rejected
**Status:** **SUPERSEDED by D-018** (four of five blockers resolved at `de98c17`) · **Date:** 2026-07-15 · **Type:** Governance · **Supersedes:** D-016
**Decision:** **NO-GO for Phase A Freeze.** Formal certificate issued: [[PHASE_A_FREEZE_CERTIFICATE]], against [[PHASE_A_FREEZE_CHECKLIST]] (12 items, 5 PASS / 7 FAIL, 5 BLOCKING).
**Context:** A dedicated freeze audit found two blocking grounds beyond D-016's three. Both are **freeze-specific defects invisible during authoring**, which is why four prior reviews did not surface them:
- **Version headers absent from all six L2 canonical documents**, though [[TAXONOMY_AND_NAMING_STANDARD]] §7 makes them mandatory. A freeze declares *"version X of document Y is frozen"*; six documents cannot complete that sentence. It also silently voids non-retroactive amendment, which needs a predecessor version to be non-retroactive *against*.
- **AQ-1 is blocking, not merely open.** A freeze ratifies. Freezing canonises an ontology teaching `L3 Order Book` / `BBO` / `Nanosecond` exemplars, which per ADR-L1-006 instructs researchers to author unfalsifiable — therefore inadmissible (R14) — hypotheses.
**Alternatives considered:** **GO WITH CONDITIONS — rejected.** That instrument fits conditions closing *in parallel* with the approved state taking effect. All five blocking conditions are **preconditions of the state transition**: one cannot freeze first and become tracked, versioned, and independently reviewed afterwards. A conditional GO on a transition whose conditions must precede it is a NO-GO in softer wording — and per LIM8 the softer wording is what gets read as GO while the conditions decay into intentions. **GO — rejected**: `git ls-files` is empty; a GO would certify nothing.
**Rationale:** The decision is compelled by a binary fact, not a judgement: there is no revision to freeze. This is not a scientific objection — the science is complete and Finding #4 is closed.
**Consequences:** Distance to GO is **one commit, three lines, six headers, one signature**. Condition 5 (adversarial sign-off) is undischargeable by the certificate's author by construction. Corpus loss before the baseline commit is now the largest live risk in the program.
**Related:** [[PHASE_A_FREEZE_CERTIFICATE]] · [[PHASE_A_FREEZE_CHECKLIST]] · [[01_SCIENTIFIC_FOUNDATION]] LIM6, LIM8, ADR-L1-006/007

### D-019 · Author validation declined — independent validation requirement remains open
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance

**Background.** After completion of Phase A, the architecture author was requested to perform the final independent validation required for Phase A Freeze. **The author declined.** The Scientific Foundation itself requires that independent validation be performed by a reviewer who is not the author; performing both roles would violate **LIM6** (sequential performance by one mind is not independent validation) and **LIM8** (self-certification is epistemically indistinguishable from genuine independent certification). The requirement therefore cannot honestly be declared satisfied.

**Decision:** The author declines to perform the independent validation.

**Rationale:** Independent validation requires a reviewer who is not the author.

**Alternatives considered:**
- **A — Author self-certification.** **REJECTED.** The criterion reads *"Validation Reviewer, not the author"* ([[RESEARCH_OS_MASTER_ROADMAP]] §7). Certifying under it would not satisfy the criterion but delete it — R7.4 (threshold migration) applied to governance.
- **B — Fresh-context LLM review.** **REJECTED.** A fresh context is not a fresh mind: same model, same priors, same blind spots. Per **LIM5** it would test *specification completeness* — genuinely valuable — but would be *specification-reproducible, not independently replicated*. It does not satisfy independence and may not be recorded as if it did.
- **C — Human independent reviewer.** **The only alternative that satisfies the requirement.** Not yet performed.

**Rejected:** A and B. **Reason:** neither satisfies the independence requirement defined by the Scientific Foundation.

**Consequences:** Phase A remains **GO WITH CONDITIONS**. The **only** remaining condition is independent adversarial review, and it is now formally attributed to an **External Validation Reviewer** rather than left implicitly pending on the author. Phase A is **certified-ready but NOT FROZEN**; no document may describe it as frozen until sign-off is recorded and certificate v3.0 issues. Per **LIM6**, the institution retains a second legitimate path: formally declare the requirement unmet and mark affected claims accordingly. That is a governance choice reserved to the owner and is **not** equivalent to freezing.

**Why this entry exists.** **LIM8** holds that the institution's true epistemic state is not verifiable from its outputs alone: a self-certified corpus and an independently certified one are indistinguishable on inspection. A request for author self-certification, and its refusal, leaves no trace in any artifact unless it is recorded here. This entry is that trace. It is a record, not a reproach.

**Related:** [[PHASE_A_FREEZE_CERTIFICATE]] v2.1 · [[PHASE_A_FREEZE_CHECKLIST]] v2.1 · [[PHASE_A_REVIEW_PACKAGE]] v1.1 · [[01_SCIENTIFIC_FOUNDATION]] LIM5, LIM6, LIM8, R7.4, ADR-L1-007 · D-018

### D-020 · The Research Knowledge Corpus extends L0/L1/L2; it is not a new layer and not a "Phase B"
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance / Architectural

**Background.** The owner commissioned a "Phase B — Research Knowledge Layer" of seven canonical documents: `MARKET_INEFFICIENCY_TAXONOMY`, `ECONOMIC_MECHANISM_TAXONOMY`, `RESEARCH_OBJECT_SCHEMA`, `EVIDENCE_MODEL`, `LITERATURE_RESEARCH_STANDARD`, `HYPOTHESIS_LIFECYCLE`, `RESEARCH_PROGRAM_STANDARD`, under the binding constraint *"do not duplicate their contents; only extend them."* Audit against the certified corpus found three conflicts:

1. **"Phase A is complete" is contradicted by the corpus.** Phase A is **GO WITH CONDITIONS, NOT FROZEN** (D-018/D-019); the roadmap states no document may describe it as frozen until sign-off is recorded.
2. **"Phase" is retired from structural use** (**D-003**), and the seven deliverables do not form one layer regardless: they span L0 (program standard), L1 (taxonomies, evidence, literature), and L2 (object schema, lifecycle).
3. **Five of seven collide with canonical documents.** `ECONOMIC_MECHANISM_TAXONOMY` vs [[01_SCIENTIFIC_FOUNDATION]] §3.4 (**M1–M6, declared a closed set at class level, amendable only by CRO**); `RESEARCH_OBJECT_SCHEMA` vs [[RESEARCH_OBJECT_MODEL]] v1.0; `MARKET_INEFFICIENCY_TAXONOMY` vs §3.5/§6; `EVIDENCE_MODEL` vs §4.2 (E0–E7); `HYPOTHESIS_LIFECYCLE` vs [[TAXONOMY_AND_NAMING_STANDARD]] §6 and [[RESEARCH_OPERATING_MODEL]] §6–§7. Authored as declared, they would create **two authorities for the same content** — the AQ-1-class defect the corpus had just closed at `de98c17`.

**Decision:** The corpus is authored as a **strict extension**, filed by owning layer, under three binding rules:

- **R-a · Classes are L1's; instances are the corpus's.** L1 retains the closed sets **M1–M6, D1–D6, E0–E7, F1–F9**. The new documents populate *instances* and *sub-classes* beneath them and specify the rules L1 deliberately omits. **No new document may grow its own class set** — there is no `M7.x`, no `E8`, no `D7` reachable from here.
- **R-b · Extend, never restate.** Where a field, scale, or rule exists upstream, the new document **cites** it. Where a facet is *absent* upstream, the new document specifies it and **flags the delta as a gap**, never as an amendment.
- **R-c · File by owning layer, not by delivery batch.** `governance/` ← L0 (Program Standard); `research_os/` ← L1 (three taxonomies + literature standard) and L2 (object schema + lifecycle). Status lives in the roadmap, never in a folder name (**D-008**).

**Alternatives considered:**
- **A — Author as specified; supersede the colliding L1/L2 sections.** **REJECTED.** Requires amending a document whose independent certification is *pending* (D-019), reopening exactly the content the sign-off is over. It would also transfer the mechanism-class set out of L1, where §3.4 places its amendment authority with the CRO — a governance change disguised as a documentation task.
- **B — Block until Phase A sign-off.** **REJECTED by the owner.** Strictly correct under the gate, but the External Validation Reviewer does not yet exist (D-019), so it stalls indefinitely. The open condition is a **signature on completed work, not missing content**; rework risk is real and bounded, and each new document declares its inheritance of an unsigned baseline in its own header (**R-d**).
- **C — Drop the two directly-colliding documents.** **REJECTED.** Leaves the mechanism-instance catalogue and the object-schema facets unwritten while the collision was resolvable by subordination.
- **D — Amend [[TAXONOMY_AND_NAMING_STANDARD]] to readmit "Phase" as a structural axis.** **REJECTED.** Reverses **D-003** and the reason it was written; the seven deliverables are not one layer under any naming.

**Rejected:** A, B, C, D.

**Consequences.**
- Seven documents authored at `research_os/` (6) and `governance/` (1), each carrying a **baseline-inheritance clause (R-d)**: authored against an unsigned L1; **void pending re-derivation, not grandfathered**, if review alters the class sets they subordinate to ([[01_SCIENTIFIC_FOUNDATION]] §0.4).
- **Six gaps recorded, not resolved** — per **ADR-L1-008** — in [[KNOWLEDGE_CORPUS_DELIVERY]] §5. Two require amendments this decision withholds authority for: **G-1** (five proposed objects need a **D-005** amendment) and **G-2** (the 4-state `status` enumeration in [[TAXONOMY_AND_NAMING_STANDARD]] §6 and [[RESEARCH_OBJECT_MODEL]] under-specifies a 12-state machine).
- **G-3 is a real cost of R-b**: [[RESEARCH_OBJECT_MODEL]] declares fields, [[RESEARCH_OBJECT_SCHEMA]] declares facets, **and neither is complete alone.** Accepted deliberately — the alternative was amending a pending-certification document. Revisit once L1 is signed.
- **G-4 is the finding that matters most.** [[HYPOTHESIS_LIFECYCLE]] T9 (VALIDATED → ACCEPTED) requires adversarial review by a non-author. Per **LIM6/LIM8** and **EV-9**, a single-researcher institution cannot supply it: **C2 is the ceiling and T9 requires C3.** **The institution cannot currently promote any hypothesis to Accepted Knowledge** — blocked by the identical constraint that leaves this corpus's own foundation at GO WITH CONDITIONS. The pipeline and the certificate stand at the same wall.
- **G-6** ([[RESEARCH_PROGRAM_STANDARD]] §9): three of four Current Programs have mandatory or probable family merges on the confound structure of [[MARKET_INEFFICIENCY_TAXONOMY]] §4. **The roadmap's program decomposition is organizational; the family decomposition is scientific, and they do not coincide.**
- **D-009 is not reopened.** [[RESEARCH_PROGRAM_STANDARD]] defines the family **boundary** (a governance structure: which claims are one family); the family **policy** (the statistical correction) remains a P1 deliverable.
- Phase A's status is **unchanged**: GO WITH CONDITIONS, one open condition, external signature.

**Why this entry exists.** Per **LIM8**, a corpus that quietly duplicated its own foundation and one that extended it are indistinguishable by inspecting the result — the reader sees seven plausible documents either way. The subordination rules R-a/R-b are the only difference, and they leave no trace unless recorded. This entry is that trace.

**Related:** [[KNOWLEDGE_CORPUS_DELIVERY]] · [[MARKET_INEFFICIENCY_TAXONOMY]] · [[ECONOMIC_MECHANISM_TAXONOMY]] · [[EVIDENCE_MODEL]] · [[LITERATURE_RESEARCH_STANDARD]] · [[RESEARCH_OBJECT_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]] · [[RESEARCH_PROGRAM_STANDARD]] · [[01_SCIENTIFIC_FOUNDATION]] §0.4, §3.4, LIM6, LIM8, ADR-L1-008 · D-003, D-005, D-008, D-009, D-018, D-019

### D-021 · The Institutional Research Protocol is procedure, not specification; and it precedes L3
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Governance / Architectural

**Background.** The owner directed that the **operational research methodology** be completed *before* L3 Data Ontology, commissioning six documents — `RESEARCH_PROTOCOL`, `EXPERIMENT_STANDARD`, `REPLICATION_STANDARD`, `PEER_REVIEW_STANDARD`, `RESEARCH_QUALITY_STANDARD`, `RESEARCH_PROGRAM_PLAYBOOK` — against one question: *"if a researcher joins tomorrow, what do they follow to produce research consistent with the Scientific Foundation?"* The sequencing argument offered was that one cannot know what data must represent until the methodology that consumes it exists.

The six deliverables collide with [[RESEARCH_OPERATING_MODEL]] (roles, G1–G4), [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (S1–S10), [[HYPOTHESIS_LIFECYCLE]], [[EVIDENCE_MODEL]], and [[RESEARCH_PROGRAM_STANDARD]] — the same collision class **D-020** resolved. **D-020's rules are applied by precedent; the owner is not re-consulted on a question already decided.**

**Decision:** The IRP is authored as a **strict procedural layer** under three rules:

- **R-a · Specification vs procedure (PR-1).** **A specification states what must be true. A protocol states what you do, in what order, and what to do when you cannot.** Where a specification exists, the protocol **cites and sequences** it; it never restates it. This is D-020's seam moved: D-020 separated *classes from instances*; D-021 separates *specification from procedure*.
- **R-b · Procedures legislate nothing.** No IRP document may add a rule, gate, stage, state, or object. The dependency graph is **bipartite and one-directional** ([[PROTOCOL_LAYER_DELIVERY]] §2) — nothing flows back from procedure to specification.
- **R-c · IRP is not a layer.** It is **the procedural face of L2**. There is no L2.5. Five documents file at `research_os/` (L2), one at `governance/` (L0). Status lives in the roadmap, never a folder name (**D-008**).

**Alternatives considered:**
- **A — Proceed to L3 first, per [[KNOWLEDGE_CORPUS_DELIVERY]] §6.3's recommendation.** **REJECTED, and the owner's argument is upheld with a concrete instance.** Authoring [[EXPERIMENT_STANDARD]] §3 produced a requirement L3 could not otherwise have derived: **a Dataset must carry a custody partition whose state is a recorded fact, not an attribute** — because per §2.4 a contaminated OOS window is *indistinguishable from a clean one by inspection*, so the partition's **history** is the only evidence of its state. An L3 designed first would have modelled custody as a field, and that model is unfixable later. **The procedural layer told the data layer what to represent.**
- **B — Declare IRP a new layer between L2 and L3.** **REJECTED.** It adds a structural axis to a scheme **D-003** exists to keep singular, and the content is L2's procedural face, not a distinct stratum.
- **C — Weaken G4 so the pipeline completes at N=1.** **REJECTED on ADR-L1-007** — *declare the single-researcher review deficit; do not absorb it.* Weakening G4 *"would not make the institution able to accept knowledge; it would make it unable to tell whether it should."*
- **D — Extend the chain to a trading system, as the brief's sequence implies.** **REJECTED on §0.1 / ADR-L1-001.** Production trading is a **consumer**, explicitly outside this architecture description. Making it a downstream *layer* would let capital outcomes determine what counts as knowledge — **prohibited by §2.5**, and per **EV-5** the most dangerous inversion the evidence model names. **The chain terminates at L6/L7.**

**Rejected:** A, B, C, D.

**Consequences.**
- Six documents authored (~1,900 lines) with **zero new rules, gates, stages, or states.** [[RESEARCH_PROTOCOL]] is the single entry point; the other five are invoked from it.
- **The N-dependency is made explicit and is the layer's spine.** At **N=1**: C2 ceiling, T9 unreachable, [[PEER_REVIEW_STANDARD]] **inert**. At **N=2**: one researcher may review the other → C3 reachable → **G-4 closes**. At **N≥3**: **ADR-L1-002** mandates revisiting the epistemology itself. **The owner's framing question — "if a researcher joins tomorrow" — names the event that relieves the corpus's binding constraint.** Not a tool, not a document. A person.
- **Seven new gaps recorded, not resolved** (ADR-L1-008): **G-9, G-13, G-10, G-11, G-12, G-14, G-15** — [[PROTOCOL_LAYER_DELIVERY]] §5.
- **██ G-9 is the finding, and it outranks G-4. ██** Writing the procedures down forced the question *"what actually stops a researcher from looking at out-of-sample data?"* **The answer is nothing.** **§2.4** makes OOS non-renewable and states that *"every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged — this invisibility is precisely why it requires a mechanism."* **R6** requires enforcement, not request. The roadmap §5 lists OOS-custody enforcement as a *planned* enhancement. **It is still policy.** L1's verdict on exactly this state (§2.4): *"the policy formulation is **epistemologically void**, because unenforced custody produces a system whose evidential state cannot be known even by its own operators."*
  > **Every E3+ claim this institution produces rests on a control that does not exist, and the breach is invisible by construction. G-4 is a wall the institution can see and has declared. G-9 is a floor it cannot.** G-9 is also **the only blocking gap the institution can close by itself** — by mechanism rather than by hiring.
- **G-13 generalises G-9:** blindness (`authored_at`/`blind_to`, **OS-6**) and reviewer independence (**O18**) are likewise **attestations, not controls**. Per §7.3 and LIM8 respectively, **neither violation is detectable by inspecting the product.** The pattern across G-9/G-10/G-13 is one finding: *every rule whose violation is invisible is currently enforced by the discipline of the person whose violation it would be* — **the exact configuration R6 exists to prohibit.**
- **Readiness for L3: GO WITH CONDITIONS**, with **U17/G-9 now ahead of G-1** — custody is a property of how data is partitioned and accessed, so it must be decided **before** L3 is designed.
- Phase A's status is **unchanged**: GO WITH CONDITIONS, one open condition, external signature.

**Why this entry exists.** Per **LIM8**, a procedural layer that quietly re-legislated its own specification and one that faithfully sequenced it are indistinguishable by reading the result — six plausible documents either way. **PR-1 and the bipartite graph are the only difference**, and they leave no trace unless recorded. This entry is that trace.

**Related:** [[PROTOCOL_LAYER_DELIVERY]] · [[RESEARCH_PROTOCOL]] · [[EXPERIMENT_STANDARD]] · [[REPLICATION_STANDARD]] · [[PEER_REVIEW_STANDARD]] · [[RESEARCH_QUALITY_STANDARD]] · [[RESEARCH_PROGRAM_PLAYBOOK]] · [[01_SCIENTIFIC_FOUNDATION]] §0.1, §2.4, §7.3, R6, LIM6, LIM8, ADR-L1-001, ADR-L1-002, ADR-L1-007, ADR-L1-008 · D-003, D-008, D-018, D-019, **D-020**

### D-022 · Custody becomes foundational: modelled at L2, amended into the Research Object Model, L1 untouched
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Architectural

**Background.** [[CUSTODY_PROPAGATION_AUDIT]] found that `custody` appears **zero times in the entire codebase** and is absent from five of nine canonical layers — including [[RESEARCH_OBJECT_MODEL]] and [[RESEARCH_VALIDATION_FRAMEWORK]]. The owner authorized a canonical architectural amendment, requiring: exactly one definition of Custody; **Custody inside the Research Object Model itself, not an extension layer**; backward compatibility; and *"do NOT redesign — only formalize"* the existing Evidence Custody.

**The premise was half wrong, and the correction shaped the amendment.** [[01_SCIENTIFIC_FOUNDATION]] **§2.4 already declares three epistemic custody states, and R6 already supplies all five of the brief's "define why" requirements verbatim** — OOS non-renewable, policy insufficient, mechanism required, the epistemological rationale, and why the invisibility is decisive. **Custody's epistemology was never missing. The *object* was.** L1 §0.5 excludes objects by design (*"those are L2+ concerns"*), so L1 declared custody and correctly could not model it — and nothing beneath L1 ever did.

**Decision:** Custody is made foundational under four rules:

- **R-a · One definition, layered.** [[CUSTODY_MODEL]] (**L2**) is the single canonical model. It **cites L1 §2.4/R6 and does not restate them** — restating would create the parallel authority the brief forbids.
- **R-b · Two orthogonal axes (CU-1).** L1 owns the **three epistemic states** (Discovery/Confirmation/Accepted) as a **closed set** — what the institution is licensed to do with a *claim*. [[CUSTODY_MODEL]] §4 owns the **eight asset states** (Created…Archived) — what state an *asset* is in. **Neither may absorb the other.**
- **R-c · Custody enters the ROM itself.** [[RESEARCH_OBJECT_MODEL]] **v1.0 → v2.0**: §3 declares the mandatory custody facet and a class per object; §4 adds **Dataset Partition, Candidate, Evidence, Publication, Custody Event/Receipt**. **v1.0's eight objects are byte-identical.** Custody is not an extension.
- **R-d · Formalize, never redesign.** `gate_evidence` + `gate_decisions` **already implement Evidence Custody correctly** — append-only, no UPDATE, no DELETE, *"a superseding evaluation is a new decision_id."* [[CUSTODY_MODEL]] §7 contains **a citation and a verdict, not a design.**

**Alternatives considered:**
- **A — Put CUSTODY_MODEL at L1.** **REJECTED, decisively.** L1 is under **pending certification**; its independent adversarial sign-off is the single open condition of the Phase-A gate (**D-018/D-019**). **Amending L1 would invalidate the review package and reopen a gate that is one signature from closing** — to say something L1 already says (§2.4/R6) and that may be said beneath it. **We do not touch a document under review to restate it.**
- **B — Four custody documents, per the brief's shape.** **REJECTED on the brief's own constraint:** *"there must be exactly one canonical definition of Custody."* Four documents would be four authorities. Consolidated into one, with the four domains as §5–§8.
- **C — Make `wf_scores`/`backtest_cache` immutable.** **REJECTED.** They are **caches**; overwriting a cache is correct. **The defect was never the overwrite — it was that a cache is read as a publication.** Declared **C-DERIVED** with **CU-18** (a Publication may be materialized from a cache; it may never be one). This is what keeps the amendment at **zero code changes**; the alternative would rewrite `jobs.py`, `optimizer.py`, `backtest_roller.py`, `screener/`, `routes/` for no epistemic gain.
- **D — Conscript `security/audit_trail.py` as the custody log.** **REJECTED (CU-7).** It is RBAC/security — it records *who called an endpoint*. Custody records *what happened to a research asset*. Merging would subordinate an epistemic control to an access-control table with different authority, retention, and consumers.

**Rejected:** A, B, C, D.

**Consequences.**
- **Delivered:** [[CUSTODY_MODEL]] (new, L2) · [[RESEARCH_OBJECT_MODEL]] v2.0 (major) · [[RESEARCH_VALIDATION_FRAMEWORK]] v1.1 (minor) · [[CUSTODY_AMENDMENT]] (propagation, compatibility, audit, migration, RFCs, freeze). **Zero code changes** — every existing implementation remains valid ([[CUSTODY_AMENDMENT]] §4).
- **The one structural change: Dataset Partition is promoted from attribute to object** (**CU-11**). A Dataset is Locked while its train partition is Consumed a hundred times and its OOS partition is Released once — **one object cannot hold four states.** And custody is a **history** (**CU-2**), which attaches to the thing accessed: *the window is accessed; the dataset is not.* Objection answered: **determinism is not custody** — `walk_forward_split` yields identical windows on every call, which is precisely why anyone can materialize the test window with no record. **Reproducibility is what makes a window dangerous, not what makes it safe.**
- **Institutional audit: 1 of 6 defects eliminated, 3 modelled, 1 narrowed, 1 explicitly not** ([[CUSTODY_AMENDMENT]] §5). **Evidence ambiguity is genuinely closed** — it was a *naming* gap, and naming is what an architecture does. **Policy-only enforcement is NOT closed**: per **R6** the gap between *modelled* and *eliminated* is exactly the gap between a statement of intent and a control. **A model of a control is not a control.** Claiming otherwise would be indistinguishable, per **LIM8**, from having built one.
- **8 RFCs. RFC-1 (Dataset Custody mechanism = G-9) is the only P0** and the only one that converts intent into control. **RFC-8 (Blind partition) is small and is the only route to E7 forward evidence without waiting in wall-clock time.**
- **The owner's priority ordering — P0 G-9 · P1 G-4 · P2 governance — is upheld with the corpus's own argument: G-4 is *partially void* until G-9 closes.** A reviewer cannot attack a claim whose custody state is unknowable; per §8.2 a claim that cannot be attacked has *structural immunity from criticism*, and per **P3** that is not a knowledge claim. **Hiring a second researcher to review an unknowable substrate buys the appearance of independent review — and per LIM8 the appearance is indistinguishable from the real thing, which makes it worse than no review, because it would be recorded as one.**
- **FREEZE: NO — and custody was never the reason.** The architecture is now **complete** ([[CUSTODY_AMENDMENT]] §9.1); the freeze remains blocked by **G-8** (L1 unsigned), unchanged since D-018. **New binding condition: v1.0 must not be frozen while G-9 is open, even if D-019 is signed tomorrow** — freezing a baseline in which custody is modelled but unenforced would make *"custody exists"* a **true statement about the corpus and a false statement about the institution**, and per **LIM8** those are indistinguishable to any future reader of a frozen baseline.

**Why this entry exists.** Per **LIM8**, an amendment that faithfully subordinated itself to L1 §2.4 and one that quietly re-legislated custody at L2 are indistinguishable by reading the result. **R-a and R-b are the only difference.** This entry is that trace.

**Related:** [[CUSTODY_MODEL]] · [[CUSTODY_AMENDMENT]] · [[CUSTODY_PROPAGATION_AUDIT]] · [[RESEARCH_OBJECT_MODEL]] v2.0 · [[RESEARCH_VALIDATION_FRAMEWORK]] v1.1 · [[01_SCIENTIFIC_FOUNDATION]] §0.1, §0.5, §2.4, §4.2, R6, R12, LIM8, ADR-L1-008 · D-005, D-018, D-019, **D-020**, **D-021**

### D-023 · RT-4 resolved — a Blind partition yields E6 + maximal custody, never E7
**Status:** ACCEPTED · **Date:** 2026-07-15 · **Type:** Architectural (terminology correction)

**Background.** An adversarial review ([[RED_TEAM_REVIEW_2026-07-15]]) raised five findings; the Board ([[ARB_ADJUDICATION_2026-07-15]]) upheld exactly one — **RT-4**: CU-13 claims a Blind partition *"makes E7 available without waiting in wall-clock time"*, while [[01_SCIENTIFIC_FOUNDATION]] §4.2 defines E7 as requiring **data that did not exist at registration** and states it *"accrues in wall-clock time and **cannot be accelerated**."* The Resolution Board was asked to determine whether this is a genuine contradiction, a terminology conflict, a governance conflict, or a misinterpretation — **by proof, not assumption** ([[RT4_RESOLUTION_2026-07-15]]).

**Finding: RT-4 SURVIVES formalization. It is a genuine architectural contradiction with two independent proofs.**

- **D-leg.** Suppose *"did not exist"* is **epistemic** (unavailable to the institution) — then a sealed existing partition qualifies as E7. But its corpus was universe-selected, corporate-action-adjusted and vendor-cleaned **with knowledge of its period** — retrospective biases (**A3**, **LIM1**), of which **this institution has two realized instances** (the P0 collector bug, `liquid_universe` 187 vs `_default_universe` 958; and the P0 audit's finding that corporate actions were never applied to the raw corpus). **∴ ¬"immune to every retrospective bias" — contradicting §4.2's own justification clause. The epistemic reading is refuted by L1, not by the Custody Model.** ∴ *"did not exist"* is **metaphysical**. And **every registrable partition contains existing data**, because **T-C2 requires a fingerprint at REGISTERED and you cannot fingerprint what does not exist.** ∴ ¬E7. ∎
- **W-leg, independent of the D-leg.** §4.2: E7 **cannot be accelerated**. CU-13/M5/RFC-8: *"without waiting in wall-clock time"*. **Contradiction under every reading.** ∎
- **Truth table:** of four (reading × content) combinations, **exactly one is possible — and CU-13 is false in it.** CU-13's only true row requires the refuted epistemic reading; the charitable "reservation for future data" reading is **not constructible in the object model at all** (no fingerprint ⇒ no REGISTERED) *and still* requires waiting.

**Decision:** **Category A — terminology correction. Four sentences, two documents.** A Blind partition yields **E6-equivalent evidence with maximal custody assurance**, never E7. The acceleration claim is deleted at all three sites (CU-13, M5, RFC-8).

**Alternatives considered:**
- **B — amend L1 to disambiguate *"did not exist."*** **REJECTED: L1 is not ambiguous.** Two independent clauses — *"immune to every retrospective bias"* and *"cannot be accelerated"* — each force the metaphysical reading. **The ambiguity was in the author, not the text.** ⇒ **L1 untouched; D-019's review package undisturbed.**
- **C — cross-reference correction.** **REJECTED.** CU-13 cites §4.2 **correctly** (for the timebox) and then contradicts it. The reference is right; the claim is wrong.
- **D — architectural correction.** **REJECTED.** Nothing structural changes: the Blind partition object, C-SEALED, `release_date`, the state machine, T-C2/T-C5, CU-14, and §5.4's release policy all stand. **RFC-8 survives.**
- **Deleting the Blind partition.** **REJECTED.** Its custody value is real and was obscured by the mislabel — see below.

**Rejected:** B, C, D, deletion.

**Consequences.**
- **Severity was overstated and is now bounded.** The contradiction is **inert**: [[EVIDENCE_MODEL]] restates the nonexistence criterion **three times independently** — K6, C4, and the **E6→E7 promotion guard** — so the promotion path never reads CU-13 and would refuse a Blind partition on its own criterion. The corpus additionally voids CU-13 by **§5.4** (*on scientific method, L1 wins*) and **§0.4** (*a rule whose justifying proposition is refuted is void, not grandfathered*). **It could not have promoted anything.** The red-team's *"licenses capital at scale"* was wrong.
- **But inert ≠ absent.** Per **ISO 42010 §5.6** and L1 **§15**, an *unrecorded* inconsistency between canonical documents is a conformance defect, and **a frozen baseline is the artifact future readers trust without re-deriving.**
- **What the Blind partition actually is, recovered:** an ordinary OOS partition is C-SEALED but **releasable** — per **G-9** nothing mechanically prevents it being read, and per **R6** an unenforced seal *"is a statement of intent, not a control."* **A Blind partition has no release path at all**, so its window is **provably unspent** rather than *supposed* to be. **Its value is on the custody axis, not the evidence axis.** It strengthens an **E3** pre-registered OOS test; it creates no new tier.
- **Root cause, recorded because it will recur:** the architecture **had no name for the thing the author had built** — a window whose custody state is provable rather than asserted — **so the author took the nearest impressive label.** The correction names the thing and keeps the thing.
- **Zero impact** on L1, [[EVIDENCE_MODEL]], [[RESEARCH_OBJECT_MODEL]], [[RESEARCH_VALIDATION_FRAMEWORK]], [[EXPERIMENT_STANDARD]], the roadmap, or any object/state/class/rule.
- **RT-4 is RESOLVED and no longer blocks freeze. Remaining blockers: G-8 (L1 unsigned, D-019) and G-9 (Dataset Custody unmechanised) — neither architectural.**

**Why this entry exists.** Per **LIM8**, a corpus that quietly deleted an embarrassing claim and one that proved the claim false before removing it are indistinguishable by reading the result. **The proof at [[RT4_RESOLUTION_2026-07-15]] §5.1 is the only difference.** This entry is that trace.

**Related:** [[RT4_RESOLUTION_2026-07-15]] · [[ARB_ADJUDICATION_2026-07-15]] · [[RED_TEAM_REVIEW_2026-07-15]] · [[CUSTODY_MODEL]] CU-13 · [[CUSTODY_AMENDMENT]] M5/RFC-8 · [[01_SCIENTIFIC_FOUNDATION]] §0.4, §4.2, §15, A3, LIM1 · **D-022**

### D-024 · Phase A Exit Gate — GO WITH CONDITIONS; G-8 is the sole exit blocker
**Status:** ACCEPTED · **Date:** 2026-07-16 · **Type:** Governance
**Recorded in full:** [[PHASE_A_EXIT_GATE_DECISION]] — not duplicated here.

**Decision:** **GO WITH CONDITIONS.** Phase A architecture is **COMPLETE** (zero open contradictions: five raised adversarially, four disproven, RT-4 proven and corrected at D-023). **Phase A exit is gated by G-8 alone.** Phase B may proceed. Assessed at `069afc3`.

**Two corrections to prior interpretation — both from reading the canonical text, neither changing the architecture:**
- **A · G-9 is not a Phase A exit gate.** [[RESEARCH_OS_MASTER_ROADMAP]] §7 lists **fifteen** exit items; **fourteen are ✅ and the one open item is G-8. G-9 appears nowhere on the checklist.** G-9 blocks the **Research OS v1.0 freeze** (**D-022 §9.3** — *"even if D-019 is signed tomorrow"*) and every claim above **E3** (§2.4). **Both gates are open; they are not open on the same door.**
- **B · The reviewer criterion is *"not the author"*, not *"external"*.** §7 item 15 verbatim: *"Independent adversarial sign-off … (Validation Reviewer, **not the author**)."* **D-019 assigned an *owner* ("External Validation Reviewer"); §7 states the *criterion*.** "External" was doing the work of *"not the author"* — its stated purpose was *"rather than left implicitly pending on the author"* — and D-019's own alternative C reads *"**Human independent reviewer.** The only alternative that satisfies the requirement."* **Consequence: a second researcher satisfies criterion 15 (they did not author the corpus) and independently closes G-4 ([[RESEARCH_PROTOCOL]] §7.3). One person, two blocking gates.** *This reads the criterion; it does not relax it. Residual recorded: per **LIM6** an employed reviewer carries an institutional stake the text does not address, even though their authorship stake is nil — and per **§144** the certificate already must name the reviewer.*

**Sequencing requirement (not a new gate — a constraint on Condition 1).** **The gates are not additive: G-8's remedy is headcount and G-9's risk driver is headcount.** A second researcher doubles the hands that can read an unsealed OOS window, and has no institutional habit to restrain them. Per §2.4 contamination *"leaves its appearance unchanged"* and is unrecoverable after the fact. **∴ RFC-1 (or equivalent) lands before or with the hire** — the unblocked work precedes the blocked work because **the blocked work is the trigger for the risk the unblocked work removes.**

**Scope boundary formalized.** Per [[TAXONOMY_AND_NAMING_STANDARD]] §3, **Phase A = L0 + L1 + L2. L3 is outside the review boundary** — so Phase B work does not enlarge what the reviewer must read. L0/L1/L2 amendment **before** sign-off moves the review target; **after** sign-off it reopens governance.

**Decision vs build.** The Dataset Custody **Model** is **decided and closed** (D-022; [[CUSTODY_MODEL]] §5). The Dataset Custody **Mechanism** is **unbuilt** (RFC-1 = G-9). The earlier *"decide custody before designing L3"* condition is **discharged** — L3 specifies against a model that exists. **G-9 is engineering debt against a closed architectural decision, not a Phase A architecture defect:** per **R6** an unenforced rule reports on the institution's compliance, not the architecture's correctness.

**Conditions:** (1) **Complete G-8** — one independent adversarial sign-off; certificate **v3.0** issues naming reviewer, date, and revision frozen. (2) **Preserve Phase A artifacts** — L1 unmodified since `222d57f`; [[PHASE_A_REVIEW_PACKAGE]] v1.1 intact. (3) **No L0/L1/L2 modification without reopening governance.** (4) **G-9 proceeds independently as implementation work; not a prerequisite for entering Phase B.**

**Consequences.** Closure requires **zero new documents** — the review package exists and RFC-1 is scoped. **Phase A remains *certified-ready but NOT FROZEN*** (§144, roadmap §112); nothing here describes it as frozen. **Phase A freezes when someone who is not the author reads the checklist and signs it.**

**Related:** [[PHASE_A_EXIT_GATE_DECISION]] · [[PHASE_A_FINAL_GATE_REVIEW]] · [[PHASE_A_FREEZE_CERTIFICATE]] §144 · [[PHASE_A_REVIEW_PACKAGE]] · [[RESEARCH_OS_MASTER_ROADMAP]] §7 · [[TAXONOMY_AND_NAMING_STANDARD]] §3 · [[01_SCIENTIFIC_FOUNDATION]] §2.2, §2.4, R6, LIM6, LIM8, ADR-L1-007 · D-018, D-019, **D-020** R-d, **D-022**, **D-023**

---

## 2b. Phase B governance decisions — Owner-ratified 2026-07-17

These three were proposed by the Phase B Governance Remediation ([[GOVERNANCE_REMEDIATION_REPORT]] §4) as D-025-P / D-026-P / D-027-P, prepared for ratification in [[OWNER_RATIFICATION_PACKAGE]], and **ratified by the Owner on 2026-07-17**. The `-P` (proposed) suffix is retired; they are recorded decisions. Ratification followed the Independent Review (GLM 5.2 — **APPROVE WITH MINOR OBSERVATIONS**) and the closure of its sole accepted defect ([[F1_CLOSURE_REPORT]]). They govern the L3–L5 corpus and the layer scheme; they do **not** alter Phase A's frozen scientific content (L1) or its exit-gate standing (G-8).

### D-025 · Layer scheme ratified — transcript scheme adopted
**Status:** ACCEPTED · **Date:** 2026-07-17 · **Type:** Governance · **Approval authority:** Owner (ratification) · **Supersedes proposal:** D-025-P
**Decision:** Option (a) adopted. The transcript layer scheme is ratified as repository-canonical: **L0 Governance & Scope · L1 Scientific Foundation · L2 Research Architecture · L3 Data Ontology · L4 Runtime Architecture · L5 Reference Architecture · L6 Technology Profiles.** [[REFERENCE_ARCHITECTURE]] receives a defined L5 slot; [[RUNTIME_ARCHITECTURE]]'s L4 name is adjudicated (Runtime Architecture); the three ingested headers move contested → final.
**Rationale:** The owner's own transcript decision favored option (a); ratification transacts a decision already made but never recorded (RN-3 / RN-8). Recorded per ISO 42010 §5.7.
**Affected documents:** [[DATA_ONTOLOGY]] (L3 confirmed) · [[RUNTIME_ARCHITECTURE]] (L4 name final) · [[REFERENCE_ARCHITECTURE]] (L5 slot final) · [[LAYER_MAPPING_TABLE]] · [[TAXONOMY_AND_NAMING_STANDARD]] §3 (amendment authorized — see Consequences).
**Consequences:** The consequential amendment of [[TAXONOMY_AND_NAMING_STANDARD]] §3 to v2.0 and the five Phase A layer-label updates ([[LAYER_MAPPING_TABLE]] §3) are **owner-authorized but deferred to the Phase A formal-amendment path** — not executed in this closure, because Phase A must remain undisturbed (per D-024 condition 3, an L0/L1/L2 edit reopens Phase A governance; a Phase A file is not edited inside a Phase B status-closure). Until that amendment is transacted, cite L4/L5 by the ratified names alongside the document name for clarity. RN-9 (fence naming) may be folded into that amendment at the owner's discretion.
**Related:** [[GOVERNANCE_REMEDIATION_REPORT]] §4 · [[LAYER_MAPPING_TABLE]] · [[OWNER_RATIFICATION_PACKAGE]] · D-003, D-024

### D-026 · L4.5 Execution Semantics withdrawal ratified
**Status:** ACCEPTED · **Date:** 2026-07-17 · **Type:** Governance · **Approval authority:** Owner · **Supersedes proposal:** D-026-P
**Decision:** The L4.5 Execution Semantics specification is ratified as **Withdrawn** (owner rationale quoted verbatim in [[EXECUTION_SEMANTICS]]). The L4 owner is directed to confirm that [[RUNTIME_ARCHITECTURE]] (L4) subsumes the Execution Identity / Execution Context definitions, or to amend L4 accordingly — closing the RN-10 orphan flag.
**Rationale:** The withdrawal was decided by the owner in the source transcript; ratification records it (RN-10). L4.5 exists in neither layer scheme.
**Affected documents:** [[EXECUTION_SEMANTICS]] (Withdrawn — ratified) · [[RUNTIME_ARCHITECTURE]] (subsumption confirmation directed).
**Consequences:** [[EXECUTION_SEMANTICS]] remains preserved in `docs/archive/` as history — never deleted, never cited as a layer. The orphaned-definition confirmation is assigned to the L4 owner as a discrete follow-on (architecture judgment, tracked, not performed in this closure).
**Related:** [[GOVERNANCE_REMEDIATION_REPORT]] §4 · [[EXECUTION_SEMANTICS]] · D-025

### D-027 · Ingested L3–L5 corpus ratified as canonical
**Status:** ACCEPTED · **Date:** 2026-07-17 · **Type:** Governance · **Approval authority:** Owner · **Supersedes proposal:** D-027-P
**Decision:** [[DATA_ONTOLOGY]], [[RUNTIME_ARCHITECTURE]], [[REFERENCE_ARCHITECTURE]] are accepted as **Canonical** layer specifications (the "candidate / unratified" qualifier is retired). The L3 owner assignment (Research Architect, assigned at ingestion) is **confirmed**. Independent reviews of all three are **commissioned** (RN-4).
**Rationale:** The three were ingested with full metadata, wording preserved, provenance retained; ratification accepts them into the canon and opens the review track. Records RN-2 / RN-3 / RN-4 / RN-6 closure at the governance level.
**Affected documents:** [[DATA_ONTOLOGY]], [[RUNTIME_ARCHITECTURE]], [[REFERENCE_ARCHITECTURE]] (status → Canonical) · [[DOCUMENT_REGISTRY_UPDATE]] · [[HEADER_CHANGE_LOG]].
**Consequences:** Canonical status is of the *specifications as ratified*; it is **not** a freeze. Independent review (RN-4) remains pending and the three inherit Phase A's still-open G-8 sign-off — they are **Canonical but not frozen**. Independent review and the RN-7 leakage-cleanup passes proceed as downstream work, outside this closure.
**Related:** [[GOVERNANCE_REMEDIATION_REPORT]] §4 · [[DOCUMENT_REGISTRY_UPDATE]] · [[F1_CLOSURE_REPORT]] · D-025, D-026

---

## 2c. Research Program operating decisions — Owner-ratified 2026-07-17

Decisions taken by the Owner acting as Research Director / CRO in operating the Research OS. They instantiate the frozen standards; they do **not** amend them. This subsection is the authoritative governance record for such rulings — the operating documents in `docs/research_programs/` cite it and do not carry the decision themselves (SSOT).

### D-028 · G-6 family merge — P-M and P-A hypothesis families declared before first registration
**Status:** ACCEPTED · **Date:** 2026-07-17 · **Type:** Research Program governance · **Approval authority:** Owner (Research Director / CRO)
**Decision:** The **G-6** family-merge question ([[RESEARCH_PROGRAM_PLAYBOOK]] §6, §4) is resolved by owner ruling **before any hypothesis registration**. Two active programs are declared with the following **multiplicity families**, which are append-only and monotonic from this decision (PG-3):

- **P-M · Microstructure Flow** = merged **P1 + P2** · Family: **I5, I6, I7, I12**
- **P-A · Auction Dislocation** = **P3** · Family: **I2, I3, I8**

These are the statistical hypothesis families that govern **admissibility, multiplicity control, denominator accounting, and experiment registration** for all work in the two programs. Program status is *Ready for Hypothesis Registration*; formal initiation occurs at the first registration (G1 / T4), at which point the first hypothesis joins its declared family permanently.
**Rationale:** The merge pays the correct statistical cost rather than understating multiplicity (Option A, [[RESEARCH_PROGRAM_PLAYBOOK]] §4.3 — *"the correct cost, not an objection"*). (1) The in-scope entries share causal mechanisms — I5↔I7 *confound*, I6↔I12 *near-inseparable* (LIM2), I8→I2 *upstream* ([[MARKET_INEFFICIENCY_TAXONOMY]] §4) — so **ex-ante separation is unreliable at current data fidelity**. (2) Merged, **wider families produce statistically honest denominators**; kept separate they would each understate multiplicity, inflating every result's evidential weight (§4.3) in a direction LIM3 says is unmeasurable. This applies the R7.5 / PG-6 / PG-7 principle at the program boundary.
**Affected documents:** [[RESEARCH_PROGRAM]] §2 (records the merge; cites this decision) · [[OBJECTIVES_2026H2]] §3 (scored backlog scoped to these families). No frozen standard is edited; [[RESEARCH_OS_MASTER_ROADMAP]] §3 (the P0–P6 register, D-006) is **unaltered** — this is an operating selection over it, not a reclassification of it.
**Consequences:** Effective immediately and **binding before the first hypothesis registration**. Per **R7.5 / PG-6**, a declared family may never later be narrowed or split. Once a family has an active registration, **any change requires a formal governance amendment** (a superseding decision entry here) and **is permitted only where the governance framework allows** — otherwise the sole remedy is program termination and a new family from zero, forfeiting every survivor ([[RESEARCH_PROGRAM_PLAYBOOK]] §1.2, PB-2). This decision **closes G-6**. P4/P5/P6 remain unaffected (retained, not initiated — D-006).
**Related:** [[RESEARCH_PROGRAM]] · [[RESEARCH_PROGRAM_STANDARD]] §9 · [[RESEARCH_PROGRAM_PLAYBOOK]] §4 · [[MARKET_INEFFICIENCY_TAXONOMY]] §4 · D-006, D-009, D-020

---

## 2d. Production admission decisions — T7 Production Admission audit, 2026-08-19

### D-029 · NR7_BULL demoted APPROVED → SHADOW — the Evidence Model's C3 capital bar was never satisfied
**Status:** ACCEPTED · **Date:** 2026-08-19 · **Type:** Production admission governance · **Approval authority:** Owner

**Strategy:** `NR7_BULL` (registry ID; `strategy_fn: "NR7 Breakout"`) · **Previous status:** APPROVED (v1, since 2026-07-04) · **New status:** SHADOW (v2) · **Owner decision:** DEMOTE

**Decision:** `NR7_BULL` is demoted from `APPROVED` to `SHADOW`. `registry/edge_registry.yaml`'s v1 entry (APPROVED) is marked `SUPERSEDED` — a `_LIFECYCLE` state, preserved unchanged as the permanent historical record of the original 2026-07-04 approval, per `registry/manifests/NR7_BULL_v1.yaml`. A new v2 entry (SHADOW) is admitted in its place via `engine/registry_loader.py`'s `_LIFECYCLE_DEBT` grandfather (rekeyed `("NR7_BULL", 2)`), which — as SHADOW — structurally cannot produce live capital execution (`registry_governance()`/`_edge_selectable()`, T7 invariant #4/#8, verified this session). No strategy in `registry/edge_registry.yaml` is currently `APPROVED`.

**Reason:** [[EVIDENCE_MODEL]] §5.1 requires confidence **C3** (evidence tier **E5** + reproducibility **X3**) before any capital may follow a claim. §8's own worked example, applying the model explicitly to this strategy, scores it:

| Axis | Score |
|---|---|
| Evidence class | K3/K4 |
| Evidence tier (E) | **E3-ish** — absent E5 |
| Confidence (C) | C1 |
| Reproducibility (X) | **X2** — absent X3 |

and concludes verbatim: *"Verdict. No capital. C3 requires E5+X3; the claim has neither."* This is a direct, unresolved contradiction with the strategy's prior `APPROVED` (live-capital) status in the Edge Registry — found during the T7 Production Admission audit (`Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §10) when comparing what `engine/registry_loader.py::validate_evidence()` actually enforces (receipt *existence* — a `gate_decision.final_state` flag and `forward.{verdict,n,exp_pct}` thresholds) against what the Evidence Model requires (evidence *class/tier/confidence/reproducibility*, which the registry schema does not record or check at all).

**Why receipt-binding (R-10) did not already prevent this:** `docs/RESEARCH_MASTER_PLAN.md` v3's invariant #10 ("every promoted edge has forward-test evidence... `NR7_BULL` is the sole, dated, deadlined exception") governs whether a receipt *exists* — a narrower, different question from what confidence tier the receipt's contents *support* (Evidence Model §5.1). Both were simultaneously true: `NR7_BULL` had a receipt (grandfathered, invariant #10 satisfied) and that receipt's evidence did not clear the capital bar (Evidence Model's own §8 verdict). Per CLAUDE.md's Decision-Making Hierarchy: v3 governs disputes about its own receipt-binding mechanism; the Research OS governs disputes about scientific-method/evidence-sufficiency, and on that question its answer — applied to this exact strategy — is unambiguous.

**No evidence fabricated or modified.** This decision does not manufacture E5/X3 evidence to justify demotion, nor does it alter `NR7_BULL`'s recorded backtest/forward-test results (`registry/manifests/NR7_BULL_v1.yaml`, preserved byte-for-byte; `registry/manifests/NR7_BULL_v2.yaml` carries the same `artifacts`/`evidence_summary` forward unchanged, plus the demotion record). The strategy is not deleted or retired — it remains SHADOW-tracked and available for future evidence development; re-promotion to APPROVED requires actual C3 (E5+X3) evidence, never fabricated.

**Compounding structural finding (not actioned here):** [[01_SCIENTIFIC_FOUNDATION]] ADR-L1-007 declares independent/adversarial review structurally unmet at the institution's current one-researcher headcount. Since C3 requires X3 (independent reproduction by someone other than the claim's author), **no claim can currently reach C3 under any evidence accumulated**, regardless of how much data supports any other axis, until headcount reaches ≥2 with an enforceable OOS firewall (ADR-L1-007's own revisit condition). This is a standing constraint on **all** future APPROVED promotions, not specific to `NR7_BULL` — recorded here as context, not resolved; no other registry entries exist to which it currently applies.

**Consequences:** Production verified post-change: `registry_governance("NR7 Breakout")` returns the `'SHADOW'` sentinel (not a frozen universe); `_edge_selectable()` excludes it from live selection for a ticker in its former APPROVED universe even against a positive legacy `wf_edge` row (`tests/test_registry_lifecycle.py::test_nr7_breakout_excluded_from_live_selection_after_demotion`); `startup_summary()` now reports **0 approved, 1 shadow**. `scheduler/jobs.py::run_phase5_bull_watch()` (the NR7-specific regime-band monitor, keyed to `approved_universe()`) degrades safely to a no-op — verified by direct call, no crash. Shadow/research tracking (forward_testing, `research_runs`, gatekeeper) is untouched and remains functional — nothing in that pipeline reads registry `status` as a precondition. Full regression suite: 2418 passed (3 pre-existing, unrelated failures unchanged).

**Files changed:** `registry/edge_registry.yaml` (v1→SUPERSEDED, v2 SHADOW added), `registry/manifests/NR7_BULL_v2.yaml` (new), `engine/registry_loader.py` (`_LIFECYCLE_DEBT` rekeyed + reason updated), `tests/test_registry_lifecycle.py`, `tests/test_registry_loader.py`, `tests/test_nr7_live_pipeline_e2e.py` (fixture updates + new production-verification tests), this entry, and `docs/RESEARCH_MASTER_PLAN.md` (dated amendment, invariant #10 exception description only — no rewrite).

**Related:** [[EVIDENCE_MODEL]] §3, §5.1, §8 · [[01_SCIENTIFIC_FOUNDATION]] ADR-L1-007 · `docs/RESEARCH_MASTER_PLAN.md` §5 invariant #10 · `Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §10 · D-022 (custody), D-024 (G-8/G-9 gate scope)

### D-030 · Premover EOD admission model ratified — permanent, Registry-independent channel; stays OFF
**Status:** ACCEPTED · **Date:** 2026-08-20 · **Type:** Production admission governance · **Approval authority:** Owner

**Component:** `run_premover_eod()` (`scheduler/jobs.py:680`) → `paper_trade.py`'s `get_premover_mode()`/`set_premover_mode()`/`evaluate_premover_trade()` (`auto_trade_from_premover` in `paper_config`) · **Live mode:** `off` (verified against the production DB this session) · **Owner decision:** RATIFY THE EXISTING MECHANISM AS PERMANENT — DO NOT MIGRATE TO THE EDGE REGISTRY

**Decision:** Premover EOD's existing `off`/`shadow`/`enforce` discipline is ratified as its permanent, intended admission model — a channel structurally separate from, and not migrating into, the Edge Registry's `strategy_fn`/`universe_artifact` schema. `auto_trade_from_premover` remains `off` by default (T7 audit §4.3's dormant state is unchanged by this decision). Enabling `shadow` or `enforce` in the future is an ordinary operator action under this already-tested mechanism (`set_premover_mode()`, `POST /api/paper/premover_mode`, admin-RBAC), not an architecture change requiring further governance — the same graduated-rollout shape this repository already uses for `AUTH_MODE`/`EDGE_SCORE_MODE`/`SECTORS_APP_MODE`.

**Reason:** Traced independently this session, not merely re-summarized from the audit. Two findings settle this:
1. **Original design intent predates the Registry by a month and was never strategy-shaped.** `docs/superpowers/specs/2026-06-05-g6-premover-auto-trade-design.md` (2026-06-05) — the source design for this exact feature — specifies `off`/`shadow`/`enforce` as the complete admission model; it contains no concept of `strategy_fn`, backtest evidence, or `gate_decision` at all, because premover is a live per-ticker pattern scanner (`engine/premover_detector.py::run_scan()`, REVERSAL_BREAKOUT-style setups scored 0-100), not a named, backtested strategy population. The current implementation (`scheduler/jobs.py:680-736`) matches that 2026-06-05 spec line-for-line, including the exact gate order (DD circuit breaker → max positions → duplicate → regime) in `evaluate_premover_trade()` (`paper_trade.py:700-745`).
2. **The Edge Registry's schema has no natural fit.** `universe_artifact` is a frozen *ticker set* keyed to one `strategy_fn` with a manifest evidence receipt (`registry/SCHEMA.md`-shaped). Premover fires per-ticker on its own live signal, with no fixed universe and no backtest/`gate_decisions` trail to receipt — forcing a placeholder `strategy_fn` into the Registry to satisfy the schema would create an entry with no real evidence behind it, which is exactly the fabricated-evidence failure mode D-029 and the Evidence Model discipline exist to prevent. `open_trade()`'s `strategy=None` handling (`paper_trade.py:296`, resolves to `get_best_strategy_for_ticker()` — a backtest-cache lookup or `"Momentum Following"` default) is a display/attribution label applied *after* premover's own decision, not a Registry-checked admission — this was true before this decision and remains true; nothing about that resolution changes here.

**Consequences:** No code changes. `admission_path`/`registry_hash` (T7 invariant #9, `paper_trade.py`) remain `NULL` for premover-opened trades, as already documented in the audit §9 "Not wired" note — correct, since attributing a Registry admission state to a channel this decision holds outside the Registry would be misleading, not merely incomplete. This closes `Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §4.3 as a permanent architectural position rather than an open owner decision. Live-verified this session: `paper_config.auto_trade_from_premover = 'off'`; the production `paper_trades` table has zero rows (open or closed) — no live or historical exposure through this or any channel today.

**Files changed:** none (documentation only — this entry; a status note in `Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §4.3/§11 pointing here).

**Related:** `docs/superpowers/specs/2026-06-05-g6-premover-auto-trade-design.md` · `Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §4.3, §9, §11 · CLAUDE.md "Research → production contract (Edge Registry)" · D-029 (adjacent T7 admission decision, same audit)

### D-031 · `wf_edge` legacy dual-use channel — owner decision package
**Status:** ACCEPTED — IMPLEMENTED · **Date:** 2026-08-20 (proposed, revised, ratified, and implemented same day — see "Revision" and "Implementation" below) · **Type:** Production admission governance · **Approval authority:** Owner (ratified — both the scope-(ii) fail-closed fix and scope-(i) Option C terms below are approved as written)

**Component:** `scheduler/scanner.py::_edge_selectable()` (`:654-692`) and its unconstrained sibling `get_ticker_best_strategies()` (`:697-713`, `candidates=None`), reached from `adaptive_strategy_selector()` (`:835-924`, the only trade-path caller) at `:906`.

**Revision (same-day, before ratification):** independently re-traced from source per the owner's explicit instruction not to assume the prior draft was correct. That re-trace found the exposure is **sharper and more specific** than the first draft of this entry stated — see "Sharper finding" below. This revision restructures the entry into three explicit options plus a split recommendation; it does not change Status (still PROPOSED) or touch any code.

**Reachability (re-verified this session, `scheduler/scanner.py`):** `adaptive_strategy_selector()` passes `_edge_selectable()` a constrained candidate list per regime (`:895`), and falls back to the fully unconstrained `get_ticker_best_strategies()` (`:906`) whenever that constrained call yields nothing **and** the current regime has no counter-trend candidate — true for **every BULL regime** (`_COUNTER_TREND_BOOK = {'Crash Recovery', 'Panic Rebound'}` never appears in `_REGIME_STRATEGY_MAP['BULL_MODERATE'|'BULL_STRONG']`). Cross-referenced against the live `disabled_strategies` config (`vwap_reversion,vol_weighted,conservative,momentum,Liquidity Sweep,ORB,Volume Profile POC,Inside Bar Breakout`): for BULL regimes, the *only* non-disabled, non-SHADOW candidate in the constrained path is `Trend Following Breakout` — so the unconstrained fallback triggers routinely, not as a rare edge case, whenever that one strategy has no positive `wf_edge` row for a given ticker.

**Sharper finding (the reason this revision exists):** `_edge_selectable()`'s `candidates is None` branch (the fallback's own path) sets `ungoverned = None` and **skips the `registry_governance()` check loop entirely** — it never calls `registry_governance()` for any strategy name. The function's own code comment three lines above ("SHADOW — excluded outright, never falls back to the ungoverned legacy path") is therefore **only true for the constrained branch**, not for `candidates=None`. Verified live and reproducible today: `NR7 Breakout` — demoted `APPROVED → SHADOW` **yesterday** by D-029 specifically because its evidence failed the Evidence Model's C3 capital bar — has **43 tickers with positive `wf_edge.expectancy_pct` right now** (`KREN 5.77%, PIPA 5.59%, MDRN 5.12%, TIRT 4.85%, DPUM 4.34%, ...`, checked against the live production DB this session). Any of those 43 tickers hitting the BULL-regime fallback condition would re-select `NR7 Breakout` **with no registry check at all**, silently defeating the SHADOW exclusion D-029/D-030 both rely on being absolute. This is not "an ungoverned legacy strategy trading without review" (the original framing) — it is **a strategy the owner explicitly reviewed and excluded, reachable again through a different code path the exclusion was never wired into**. No other call site of this unconstrained path exists outside `adaptive_strategy_selector()` (checked: `migrations/applied/patch_adaptive_strategy.py` is a historical, already-applied one-time migration script, not live code). No existing test covers this scenario — `tests/test_edge_selector.py`'s fixture explicitly monkeypatches `registry_governance` to always return `None` ("isolate it from the real Edge Registry"), and `tests/test_t7_fail_closed_admission.py` explicitly scopes the entire legacy `wf_edge` branch out of its coverage as "a separate, pre-existing, explicitly flagged issue... deliberately untouched."

---

#### Option A — Registry migration

Every strategy currently reachable only via `wf_edge` (`Trend Following Breakout`, plus whichever of `momentum`/`vol_weighted`/`vwap_reversion`/`conservative`/`Liquidity Sweep` are ever re-enabled) would need: a `strategy_fn` identity already present in `engine.strategy_specs.SPECS`/`_CHECKER_DISPATCH` (T7 invariant #6 lineage test) — most already qualify, this part is cheap; a **frozen** `universe_artifact`, which is a real behavior change from today's live, self-updating `wf_edge` query — the universe stops tracking new research runs until re-approved; a manifest with real `gate_decisions`/forward-test evidence meeting the same C3 (E5+X3) bar D-029 just enforced — not yet checked whether any of these strategies have real `gate_decisions` rows at all (T7's audit found **zero** for the three paths it did check: counter-trend book, momentum, premover; unaudited here, but the pattern is not encouraging).

**Grandfathering implications:** `_LIFECYCLE_DEBT` was designed and used exactly once, as an individually-justified, dated exception (CLAUDE.md: "the default action is to shrink it, not add to it"). Migrating 5-8 strategies this way would mean mass-grandfathering, which dilutes the mechanism from "rare, reviewed exception" into a routine onboarding step — a real cost to the discipline D-029 just spent effort restoring.

**Testing requirements:** new lineage/evidence tests per strategy (mirroring `test_registry_lifecycle.py`), plus — regardless of whether Option A is chosen — the fail-closed fix described under "Recommendation" below, since Registry migration alone does not close the SHADOW-bypass (see next paragraph).

**Risk — the critical dependency:** migrating strategies into the Registry does **not**, by itself, stop them from trading through the unconstrained fallback, because that fallback does not consult `registry_governance()` at all. A strategy migrated and placed at SHADOW would be exactly as exposed as `NR7 Breakout` is today. Option A only delivers its intended safety benefit if paired with the fail-closed fix — it cannot substitute for it. Effort: high (weeks-to-months per strategy, forward-test n≥15 per CLAUDE.md's Phase 5 rule); timeline risk of pressure to backfill thin evidence.

#### Option B — Remove legacy `wf_edge` authorization

Given `registry/edge_registry.yaml` has **zero APPROVED entries today**, removing `wf_edge` as an authorization source (disabling both the constrained and unconstrained branches, or just their `wf_edge` query) means `_edge_selectable()`'s `governed` list — currently always empty — is *all* it would ever return. `get_ticker_best_strategies()` would always return `[]`. **Net effect: the main daily scan cycle would stop generating any BUY signal for any strategy, system-wide, immediately** — not a narrow, surgical closure of the SHADOW-bypass, but a full stop of production signal generation as currently configured, since nothing is APPROVED to replace it.

**Rollback:** trivial to revert (a code/config flag), but the operational surprise (zero signals from an otherwise-running scheduler) is real and immediate.

**Behavioral change:** from "scans generate signals for several legacy strategies with positive backtested expectancy, unreviewed by the Registry" to "scans generate no signals at all until at least one strategy clears real Registry admission." Given `paper_trades` is empty today anyway, the practical difference *right now* is small, but this removes whatever passive signal-generation capability currently exists, not just the unsafe sliver of it (the SHADOW-bypass).

**Testing requirements:** `tests/test_edge_selector.py::test_edge_selectable_none_candidates_scans_all` and siblings currently assert the legacy scan-all behavior — would need to be deliberately rewritten to assert exclusion (a visible, intentional test change, not a silent one), plus a regression test proving `adaptive_strategy_selector()` returns only counter-trend-book output (itself currently empty) system-wide.

**Risk:** broad, immediate, system-wide behavior change bundled into what looks like a narrow safety fix — removes real (if unreviewed) signal-generation capability, not just the SHADOW-bypass defect.

#### Option C — Bounded legacy exception

**Scope must split in two, given the sharper finding above — treating both halves identically would be imprecise:**
- **(i) Constrained per-candidate branch** (`_edge_selectable(conn, ticker, wf_candidates)` for strategies named in `_REGIME_STRATEGY_MAP` with no registry entry, `registry_governance() is None`) — this branch **already** correctly excludes SHADOW strategies via its own registry-check loop. This is the genuine "legacy, unreviewed, but not violating anything already decided" exposure Phase 2C/audit C-6 intended, and is the appropriate subject of a bounded exception.
- **(ii) Unconstrained fallback** (`candidates=None`) — does **not** belong in a "legacy exception" at all. It isn't a policy question of how much legacy trust to extend; it silently violates a guarantee (D-029/D-030's SHADOW exclusion) the owner already made, one day before this session, for a specific, named reason. This must be closed as a fail-closed correctness fix, not bounded as an exception — see Recommendation.

**For scope (i), if ratified:**
- **Deadline:** dated, mirroring `_LIFECYCLE_DEBT`'s `NR7_BULL` precedent (owner to set the exact date/trigger — e.g. N months from ratification, or "next real signal from this branch," whichever the owner prefers) by which every strategy still relying on it clears the Gatekeeper into a real Registry entry or moves to `disabled_strategies`.
- **Monitoring:** `admission_path` (T7 invariant #9) currently records nothing for legacy-branch opens — this exception should require either a `LEGACY_WF_EDGE` value wired into that column, or at minimum a periodic report of what the branch actually selected, so usage is visible rather than invisible.
- **Allowed/forbidden, by construction not just policy:** allowed only where `registry_governance() is None` (no entry at all); forbidden for any strategy with any registry entry regardless of status — which is exactly what the scope-(ii) fix enforces mechanically rather than by convention.
- **Owner:** Tjie, matching every other T7/registry decision to date.
- **Evidence/audit requirements:** none fabricated retroactively (mirrors D-029's own rule) — the exception documents an absence of evidence, it does not manufacture any.
- **Termination point:** the earlier of the stated deadline, or the first live trade actually opened through this branch for a ticker/strategy pair with zero `gate_decisions` history — either should force re-review, not silent continuation.

---

### Recommendation

**Not a single clean pick among A/B/C — the sharper finding splits this into two decisions of different urgency and kind:**

1. **Close the unconstrained-fallback SHADOW-bypass (scope (ii)) as a fail-closed correctness fix, independent of A/B/C.** This is not "how much legacy trust do we extend" — it is making an already-ratified guarantee (SHADOW is excluded, full stop) actually hold everywhere the code claims it does. The fix is small in shape (the `candidates is None` branch needs the same `registry_governance()` check the constrained branch already has) but **is not implemented here** per your explicit instruction not to modify `_edge_selectable()` this turn — flagged for a dedicated, minimal, test-covered change once you ratify this characterization.
2. **For the narrower, already-correctly-excluding constrained branch (scope (i)), recommend Option C** — not by default resemblance to `_LIFECYCLE_DEBT`, but because: Registry (Option A) is the intended long-term interface, but its effort (weeks-to-months, mass-grandfathering pressure) is disproportionate to today's actual risk, given `paper_trades` is empty and no live-broker execution exists anywhere in this codebase; full removal (Option B) forces a system-wide stop of all signal generation the owner hasn't asked for, to fix a defect that's actually narrower than that (once (ii) is fixed) than it appears. Option C, correctly scoped to exclude (ii), is the proportionate answer for what remains.

Net: **two ratification decisions, not one** — (a) approve the scope-(ii) fail-closed fix as a follow-up implementation task, and (b) approve Option C's terms (deadline, monitoring, owner) for scope (i). Both await explicit owner sign-off; neither is implemented by this entry.

### Implementation (2026-08-20, same day as ratification)

**Both halves of the Recommendation, as ratified, are implemented:**

1. **Scope (ii) fail-closed fix — done.** `scheduler/scanner.py::_edge_selectable()`'s `candidates is None`
   branch no longer skips `registry_governance()`. It now queries `wf_edge` unconstrained (as before,
   the "which strategies" scan is unchanged), then independently checks each found strategy's registry
   status: included only if `registry_governance()` returns a set containing the ticker (APPROVED);
   excluded if `'SHADOW'` or `None` (unregistered) — no legacy exception on this path, matching Decision
   1 exactly. `get_ticker_best_strategies()` and `adaptive_strategy_selector()` needed no changes — both
   call into the fixed function and inherit the corrected behavior.
2. **Scope (i) Option C exception — implemented, unchanged in substance, explicit in scope; deadline
   deliberately left unset.** The explicit-candidates branch's logic is byte-for-byte the same (still:
   APPROVED → selectable if ticker in universe; SHADOW → excluded; unregistered → legacy `wf_edge`
   query, this decision's bounded exception). A module-level comment now makes the exception's scope
   and its D-031 authority explicit in the code rather than only in this document.
   **Deadline correction (2026-08-20, same day, before commit):** the first implementation pass wrote
   `D031_WF_EDGE_LEGACY_EXCEPTION_DEADLINE = "2027-01-08"` into `scheduler/scanner.py`, adopted **by
   analogy** to `engine/registry_loader.py`'s unrelated `_LIFECYCLE_DEBT` (`NR7_BULL`) deadline. On
   review, this section's own ratified text (below, "Deadline:") explicitly leaves the exact date as
   **"owner to set the exact date/trigger"** — it was never actually fixed at 2027-01-08 by the owner's
   ratification of this decision. Treating an inferred-by-analogy date as if it were an approved
   governance decision would have been exactly the silent-assumption failure mode this corpus's own
   discipline exists to prevent. **The constant has been removed from code, and no replacement date has
   been substituted.** The exception remains bounded in scope and mechanics (as ratified) but is not yet
   bounded in time — that is an explicit open item, not an oversight, pending a separate owner decision
   on the actual date/trigger. **Observability** is satisfied by pre-existing infrastructure, not new code: every trade this branch's
   output can lead to already carries `admission_path='UNREGISTERED'` in `paper_trades` (T7 invariant #9),
   which is how a legacy-exception open is distinguished after the fact — a real, working audit trail,
   confirmed by reading `scheduler/scanner.py`'s Step 7 auto-open block, which computes `admission_path`
   unconditionally for every trade it opens regardless of which branch selected the strategy.

**Regression tests added:** `tests/test_t7_wf_edge_fallback_fix.py` (9 tests, real on-disk registry +
`wf_edge` fixtures, nothing mocked) — covers the full candidates=None / explicit / empty matrix across
APPROVED/SHADOW/unregistered, a structural reproduction of the real `NR7 Breakout` SHADOW scenario (real
strategy name, synthetic tickers/data, no production DB touched), and an end-to-end
`adaptive_strategy_selector()` proof. Two pre-existing tests in `tests/test_edge_selector.py` that
asserted the old buggy scan-all behavior were corrected (`test_edge_selectable_none_candidates_scans_all`
→ `test_edge_selectable_none_candidates_is_registry_only`;
`test_get_ticker_best_strategies_uses_edge` → `test_get_ticker_best_strategies_registry_only_no_admission`),
plus one new adjacent positive-path test.

**Verification:** focused suite (104 tests across every file touching `_edge_selectable`/
`get_ticker_best_strategies`/`adaptive_strategy_selector`, plus premover/registry-loader/execution-model
tests) — all pass. Full repository suite: 2436 passed, 3 failed, all 3 confirmed pre-existing and
unrelated (`.stignore` contract, `news_filter` request-mocking shape — neither file touched this session).
Live-verified post-fix: registry unchanged (0 approved, 1 shadow — `NR7_BULL`), `paper_trades` unchanged
(0 rows), Premover EOD unchanged (`auto_trade_from_premover='off'`, D-030 untouched). No strategy
promoted; no admission bypass introduced; no live-capital authorization changed.

**Files changed:** `scheduler/scanner.py` (`_edge_selectable()` fix; the exception's deadline is
explicitly unset in code, see "Deadline correction" above — no constant defines one),
`tests/test_t7_wf_edge_fallback_fix.py` (new), `tests/test_edge_selector.py` (2 tests corrected, 1 added),
`Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` (implementation/verification note, §11), this entry.

**Related:** `Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md` §4.4, §11 · `docs/superpowers/plans/2026-07-07-m1-registry-inversion.md` (original M1 design + its now-stale "always passes explicit candidates" assumption, `:523-526`) · `docs/superpowers/plans/2026-07-04-phase2c-edge-selector.md` (Phase 2C / audit C-6 origin) · `engine/registry_loader.py:40-47` (`_LIFECYCLE_DEBT` pattern Option C mirrors for scope (i) only, and whose deadline this decision's exception adopts by analogy) · `tests/test_edge_selector.py`, `tests/test_t7_fail_closed_admission.py` (both explicitly scoped this branch out before this fix) · D-029, D-030 (adjacent T7 admission decisions)

---

## 2e. Broker-Flow-v002 Phase 1 preparation — Owner-directed decisions, 2026-09-08

**Scope note, read before either entry below:** `broker-flow-v002` and its Phase 1 hypotheses (H0-H3)
are **not yet a registered research object in this repository** — no entry exists for them in
`docs/research_programs/HYPOTHESIS_REGISTRY.md`, and the authoritative preregistration corpus
(`BROKER_FLOW_PREREGISTRATION.md` and siblings) is understood to live on a separate machine
(Windows/ZCode, `C:\Users\tjies\ZCodeProject\`) not reachable from the session that recorded D-032.
That session verified this repository contains no file, prior commit, or prior DECISION_LOG entry
matching `broker-flow-v002` under any name. D-032 is therefore a **Dell-side record of owner
instructions issued directly in that session**, not a verified cross-check against the actual
preregistration text, and not itself an amendment to that document. Whoever holds the authoritative
corpus must independently ensure D-032 and the real preregistration stay consistent; this entry
cannot do that reconciliation from here.

### D-032 · Broker-Flow-v002 Phase 1 — analytical window and freeze-strategy decisions recorded; §4/§5 and turnover left explicitly open
**Status:** ACCEPTED (Decisions A, B) / OPEN — UNRESOLVED (Items C, D) · **Date:** 2026-09-08 · **Type:** Research-scope owner decision (data preparation, pre-registration) · **Approval authority:** Owner

**Decision A — Analytical coverage (ACCEPTED).** Quoted as issued: *"Retain the original broker-flow
analytical window beginning 2025-01-02 through the v002 freeze date. Do not redefine the analytical
window merely to accommodate current data coverage. Historical coverage gaps must be repaired where
technically/vendor-supported before freeze. The current tiered coverage must be explicitly audited
after repair."*

**Decision B — Freeze strategy (ACCEPTED).** Quoted as issued: *"Choose complete-backfill-before-freeze.
Do NOT freeze broker-flow-v002 with the currently known structural coverage gap merely to make Phase 1
executable. If vendor/data limitations make complete coverage impossible, STOP and escalate rather than
silently changing the specification."*

**Consequence of A+B, traced against this session's own read-only findings:** `broker_flow` in
`data/walkforward.db` has two coverage tiers over `[2025-01-02, 2026-09-04)` — 291 dates at ~96-108
tickers/day, 102 dates at up to ~829 tickers/day. Against the full active universe (958 tickers), the
completion predicate (`broker_flow` row OR confirmed-empty `bandar_detector` marker — reused from
`tools/broker_flow_idx80_gap.py`, not reinvented) shows **0 of 393 dates fully complete** and
**~275,253 missing ticker-day cells** as of this entry (re-measured live, see "Read-only validation"
below). Per Decision B, none of this may be frozen as-is. Per Decision A, this gap must be closed by
backfill (mechanically prepared, not yet authorized or run — see
`tools/agent_backfill_broker_flow_full_universe.py`), and the resulting coverage must be **re-audited**,
not assumed, before any freeze. No code change follows from this entry; the backfill driver referenced
here was built and dry-run validated in the immediately preceding session, independent of this decision
record.

**Item C — §4/§5 H1 contradiction (OPEN — NOT RESOLVED).** Recorded verbatim, not resolved: *"The
locked preregistration contains a contradiction between: §4: no train/test split for H0/H1
specification tests; §5: H0/H1 language containing OOS/fold criteria. This requires a dated explicit
preregistration decision before H1 results can be interpreted. No H1 fold criterion is to be silently
added or removed."* This item **blocks interpretation of any H1 result** until resolved by whoever
holds and amends the authoritative preregistration. Nothing in this repository resolves it, and no
attempt was made to.

**Item D — H1 turnover definition (OPEN — NOT RESOLVED).** Recorded verbatim, not resolved: *"The §5
≤200% monthly turnover criterion remains unresolved until an explicit mathematical operational
definition is recorded. Do not invent a turnover formula. H1 cannot receive a definitive verdict based
on that criterion until it is formally defined."* No formula was invented or implied anywhere in this
session or this entry.

**Read-only validation performed before recording this entry** (all against live `data/walkforward.db`,
read-only connections only — nothing written):
- Analytical window per Decision A: `[2025-01-02, 2026-09-04)` (2026-09-04 taken from the previously
  stated target artifact name `walkforward_v002_20260904.db`, not itself a new scope decision).
- Coverage: 393 IHSG-confirmed trading dates in window; 0 fully complete; ~275,253 missing ticker-day
  cells against the 958-ticker active universe.
- Driver: `tools/agent_backfill_broker_flow_full_universe.py` present, `--dry-run` re-run this session,
  `vendor_calls_made: false`, exit code 1 (PARTIAL — work pending, nothing executed).
- No `broker-flow-v002` or `walkforward_v002*` artifact exists anywhere on this machine
  (`data/frozen/` contains only the unrelated, untouched `stockbit-flow-bars-v002`).

**Files changed:** none besides this entry. No preregistration document was created, edited, or
touched — none is reachable from this session (see scope note above). No code was changed. No dataset
was created, frozen, or transferred. No H0/H1/H2/H3 test was run.

**Related:** the immediately preceding sessions' preflight/decision-pack/orchestrator-build exchanges
(not separately filed as repository documents — this DECISION_LOG entry is the first persisted record
of them) · `tools/agent_backfill_broker_flow_full_universe.py`, `tests/test_agent_backfill_broker_flow_full_universe.py`
(driver + tests, built and dry-run validated prior to this entry, unmodified by it) ·
`data/frozen/stockbit-flow-bars-v002/MANIFEST.json` (the adjacent, confirmed-wrong-dataset artifact
this decision does not touch).

---

## 2f. Broker-Flow IDX80 Dataset admission — Owner approval of the decision surface, 2026-09-09

**Scope note, read before the entry below:** the decision surface consists of the admission package
`docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` (Rev 2 — §G checklist, §H
decision block, §J receipt gates, §K discrepancies) and the Owner decision memo derived from it. The Owner
approved the decision surface by a single approval issued directly in the drafting session (external to this
repository — recorded here on the same basis as D-032's scope note). That approval selected **H-1 only**;
it did not specify options among H-2…H-6. Per the package's own rule against silently choosing unresolved
sub-options, H-2…H-6 are recorded here as **still open**, not inferred. Nothing in this entry declares,
fingerprints, or freezes a Dataset Object, registers a hypothesis, runs any empirical or back-and-forward
test, modifies `data/walkforward.db`, performs a vendor call, or repairs 2026-08-25.

### D-033 · Broker-Flow IDX80 Dataset Object — Owner approves the IDX80-scoped admission path (H-1); H-2…H-6 and capability_class remain explicitly open
**Status:** APPROVED (H-1 only) / OPEN — UNRESOLVED (H-2, H-3, H-4, H-5, H-6) · **Date:** 2026-09-09 · **Type:** Research-scope owner decision (dataset governance — admission path) · **Approval authority:** Owner

**H-1 — APPROVED.** The Owner approved proceeding with the proposed **IDX80-scoped Dataset Object
admission path** as drafted in the Rev 2 admission package. Recorded explicitly against D-032 Decision B:
this approval **is** the explicit specification decision for an IDX80-scoped path — it is **not** an implicit
workaround for Decision B, and it does **not** amend, supersede, or satisfy Decision B's full-active-universe
freeze basis for `broker-flow-v002`, which remains of record unchanged. Per the Owner's approval terms:
this is **not** automatic fingerprinting or freezing; no empirical/back-and-forward tests are authorized;
no hypothesis registration is authorized; 2026-08-25 must **not** be repaired unless separately authorized;
**all evidence/receipt gates are preserved**. **No lifecycle transition occurred by this entry** — the
Dataset Object is **not DECLARED**; DECLARED remains gated on the §J.1 receipts (R-1…R-10) and on the
resolutions of H-2…H-6 below.

**H-2 — OPEN (analytical window end).** 2026-08-27 (proposed/authorized backfill scope) vs the
v002-freeze-date boundary of D-032 Decision A — not specified by the approval; requires explicit resolution
before the boundary can be finalized.

**H-3 — OPEN (2026-08-25).** Ratify proposed exclusion vs direct cause-investigation/repair-first vs
deferral — not specified; no repair is authorized by this entry.

**H-4 — OPEN (DECLARED authority).** Authority for the DECLARED transition (governance gap; package §K.7) —
not specified.

**H-5 — OPEN (dataset ID / registry).** Interim non-canonical identifier vs registry machinery — not
specified; `dataset_id` remains UNASSIGNED and the proposed string remains NON-CANONICAL / PENDING REGISTRY
DECISION.

**H-6 — OPEN (P1/P2 provenance boundary).** Resolution mechanism for the P1/P2 overlap — not specified;
remains an admission blocker per package §B/§F.6 (R-6).

**CRO — `capability_class` remains a CRO decision** (package §J R-7); not addressed by this approval.

**Effect and gates.** The admission path is approved subject to the package's §J.1 receipts (R-1…R-10) and
the resolutions of H-2…H-6. FINGERPRINTED and FROZEN remain unreachable (§J.2 F-1…F-5 preserved). The
approval itself was issued external to this repository; the corresponding canonical authorization receipt
(R-1) remains outstanding and is a separate artifact from this entry.

**Files changed:** this entry · `docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md`
(status annotations only: header note, §G DECLARED row, §H H-1 row and recorded-outcome line, §J R-10 status
cell — no field values fabricated, H-2…H-6 left open). No code was changed. No dataset was created, declared,
fingerprinted, or frozen. No DB, vendor, backfill, or repair operation was performed.

**Related:** D-032 (Broker-Flow-v002 Phase 1 — Decisions A, B; Items C and D still OPEN) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` (Rev 2, §G/§H/§J/§K) ·
`docs/governance/DATA_FEASIBILITY_STUDY.md` §4–§5 (binding capability constraint; §K.6 inventory
discrepancy reconciliation outstanding) · `tools/broker_flow_idx80_gap.py` (canonical coverage predicate,
D-032-provenance; §J.2 F-2)

---

## 2g. Broker-Flow IDX80 Dataset population candidates — H-7C/H-8A persistence, 2026-09-09

**Scope note, read before the entries below:** H-7C and H-8A were approved by the Owner in-session
(external to this repository, on the same basis as D-032's and D-033's scope notes) as follow-on
decisions against the still-open items recorded in D-033. Neither entry below authorizes DECLARED,
FINGERPRINTED, or FROZEN for either candidate Dataset Object, registers a hypothesis, runs any
empirical or forward test, modifies `data/walkforward.db` or any application/schema code, performs a
vendor call, or repairs `2026-08-25`. D-033's H-2 (analytical window end), H-3 (2026-08-25 treatment),
H-4 (DECLARED authority), and H-5 (dataset ID / registry) are **not** addressed by either entry and
remain OPEN exactly as recorded in D-033, now understood to apply independently to each of the two
candidates named below.

### D-034 · Broker-Flow IDX80 Dataset population split ratified — H-7C approved (Dataset A / Dataset B recorded as separate O4 candidates, not collapsed)
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-scope owner decision (dataset population definition) · **Approval authority:** Owner

**H-7C — APPROVED.** Quoted as issued: *"Treat the August non-PIT IDX80 backfill population and the
PIT-aware population as separate Dataset candidates. Do not collapse them."* This is recorded as the
Owner's resolution of D-033's **H-6** item ("P1/P2 provenance boundary — resolution mechanism... not
specified") — resolved **by splitting, not merging** the two populations into independent candidates,
rather than by adopting a single unified Dataset Object. This entry does not amend, supersede, or
re-open D-032 or D-033's other items; it resolves H-6 only.

**Evidentiary basis (distinct from the decision itself).** This session's read-only H-6 provenance
investigation (recorded as this entry's supporting evidence, not as a separate Owner decision) found
`broker_flow`'s composite primary key `(ticker, trade_date, broker_code, side)` structurally
prevents duplicate/overlapping rows, and that the ordinary-live write path (`stockbit_fetcher.py`) and
the IDX80 backfill write path (`tools/backfill_broker_flow_idx80.py`) are independently gap-gated
against each other, making P1/P2 co-writes to the same cell structurally impossible
[DB-VERIFIED / CANONICAL — see the population specification artifact §0 and Dataset A/B sections
below for the full evidentiary record]. The Owner's H-7C decision was made against this evidence but
is recorded here as an act of Owner authority, not as a conclusion this session reached on its own.

**Candidates named by this decision:**
- **Dataset A** — `DS-broker_flow-idx80-nonpit-2025_2026v1` (interim/non-canonical, H-5 open):
  analytical window `2025-01-02` → `2026-08-27` inclusive, excluding `2026-08-25`; current-at-backfill
  `idx_tickers.in_idx80=1` roster (79 tickers) applied uniformly across the window; **NON-PIT** by
  construction.
- **Dataset B** — `DS-broker_flow-idx80-pit-2025_2026-04v1` (interim/non-canonical, H-5 open): named
  for its reliably-evidenced continuous PIT-aware window only; per-date roster drawn from
  `idx80_reconstitution_periods` / `idx80_membership_history`.

Full identity, inclusion/exclusion predicates, provenance status, coverage, universe integrity, known
gaps, O4 field mapping, capability/fidelity, and freeze-prerequisite detail for both candidates are
specified in the referenced population specification artifact, not restated here.

**Files changed:** none besides this entry. The referenced population specification artifact
(`docs/research_programs/P-M/BROKER_FLOW_DATASET_POPULATION_SPECIFICATION_H7C_2026-09-09.md`) already
exists, created earlier in the same session as a read-only governance/specification artifact; it is
untouched by this entry. No code was changed. No dataset was created, declared, fingerprinted, or
frozen. No DB, vendor, backfill, or repair operation was performed.

**Related:** D-033 (H-1 APPROVED; H-2…H-6 OPEN — this entry resolves H-6 only, H-2…H-5 remain OPEN
and now apply independently to Dataset A and Dataset B) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_POPULATION_SPECIFICATION_H7C_2026-09-09.md` (full
Dataset A / Dataset B specification, §0 evidence-integrity finding, §5 comparison table, §6
governance recommendation) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` (origin of the H-2…H-6
open-item numbering this entry references).

---

### D-035 · Broker-Flow IDX80 admission scope extended to both H-7C candidates — H-8A approved; Dataset A coverage-reconciliation evidence recorded
**Status:** APPROVED (H-8A) · evidence section below is a record, not a decision · **Date:** 2026-09-09
· **Type:** Research-scope owner decision (admission-path scope extension) + read-only evidence
record · **Approval authority:** Owner (H-8A) / session read-only investigation (evidence section)

**H-8A — APPROVED.** Quoted as issued: *"H-1's IDX80-scoped admission approval applies separately to
both H-7C candidates: Dataset A: `DS-broker_flow-idx80-nonpit-2025_2026v1`; Dataset B: PIT-aware
candidate."* This extends D-033's **H-1** approval (previously stated against a single undifferentiated
IDX80-scoped admission path) to cover Dataset A and Dataset B **independently**, following D-034's
split. It does **not** merge the two candidates, does **not** grant either candidate any lifecycle
status beyond what D-033 already grants under H-1, and does **not** resolve D-033's H-2, H-3, H-4, or
H-5 — those remain OPEN and, per this entry, apply separately to Dataset A and Dataset B rather than to
a single undifferentiated candidate.

**Evidence record (Dataset A only — not an Owner decision, recorded for traceability).** In a
follow-on read-only reconciliation of the ~904-row aggregate discrepancy reported in the H-7C
population specification (Dataset A section), this session traced the figure to two accounting causes
— test-suite log contamination and a DONE-line undercount from two interrupted-but-completed log
blocks — yielding an exact match between the properly-scoped DB write count (24,109 cells) and the
log's per-date first-seen-missing sum (24,109). A subsequently-surfaced 144-cell residual
(30,652 expected − 24,109 backfill-touched − 6,399 ordinary-live-covered = 144) was independently
traced to exactly two dates (`2026-04-17`, `2026-04-20`) × 72 identical tickers written by a pre-campaign
catch-up pass on `2026-04-20T17:00`, with the remaining 7 tickers per date genuinely covered by the
2026-08-27–29 backfill campaign. This closes the full identity **30,652 = 24,109 + 144 + 6,399** with
zero genuinely missing cells, classified **FULLY RECONCILED** against the completeness predicate in
`tools/broker_flow_idx80_gap.py::broker_cell_complete()`.

This evidence record does **not** authorize DECLARED, FINGERPRINTED, or FROZEN for Dataset A; does
**not** resolve D-033's H-2/H-3/H-4/H-5; and does **not** resolve the open ambiguity between the
DECLARED→FINGERPRINTED→FROZEN lifecycle in [[RESEARCH_OBJECT_SCHEMA]] §3.4 and the
CREATED→REGISTERED→...→ARCHIVED lifecycle in [[CUSTODY_MODEL]] §4.1–4.2 — that ambiguity remains
unresolved and is not silently resolved by this entry. No dedicated repository artifact currently
holds this reconciliation independent of this entry; that is noted as a governance gap, not closed
here.

**Files changed:** none besides this entry. No code was changed. No dataset was created, declared,
fingerprinted, or frozen. No DB, vendor, backfill, or repair operation was performed.

**Related:** D-033 (H-1 APPROVED single-candidate form) · D-034 (H-7C split; introduces Dataset A /
Dataset B as the two candidates this entry extends H-1 to) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_POPULATION_SPECIFICATION_H7C_2026-09-09.md` (Dataset A
§A.6, reporting the original ~904-row discrepancy this entry's evidence section reconciles) ·
`tools/broker_flow_idx80_gap.py::broker_cell_complete()` (canonical completeness predicate used to
classify the reconciliation as FULLY RECONCILED).

---

## 2h. Broker-Flow IDX80 Dataset A — DECLARED-gate decision surface ruled, 2026-09-09

**Scope note, read before the entries below:** D-036, D-037, D-038 rule on the three items identified as
DECLARED-blocking in `docs/research_programs/P-M/BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §5
(D-1, D-2, D-3 of that document — not to be confused with this log's own D-numbering). Approved by the Owner
in-session (external to this repository, on the same basis as prior scope notes in this section). **None of
these three entries transitions Dataset A, or any other Dataset Object, to DECLARED, FINGERPRINTED, or
FROZEN** — they rule on prerequisites and interpretation only. No hypothesis is registered and no empirical
test is authorized by any of the three.

### D-036 · O4 Dataset lifecycle vs CUSTODY_MODEL asset-state — Option B ratified (orthogonal axes, not synonyms)
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-scope owner decision (lifecycle interpretation) · **Approval authority:** Owner

**Decision — APPROVED (Option B).** Quoted as issued: *"DECLARED and REGISTERED are treated as orthogonal
lifecycle concepts rather than synonyms. Preserve DECLARED as the Research Object admission/lifecycle state and
REGISTERED as the custody identity/registration state, unless a higher-precedence governance rule requires
otherwise."*

This resolves, for O4 Dataset objects generally (not only Dataset A), the ambiguity recorded in
`BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §1 between [[RESEARCH_OBJECT_SCHEMA]] §3.4's
`DECLARED → FINGERPRINTED → FROZEN` lifecycle facet and [[CUSTODY_MODEL]] §4.1's `CREATED → REGISTERED → ... →
ARCHIVED` asset-state machine. By the terms of this decision, §3.4's Lifecycle facet is treated as its own
claim-readiness axis — analogous to [[CUSTODY_AMENDMENT]] §3 row 9's explicit *"orthogonal, no collision"*
ruling for Hypothesis's 12-state lifecycle against the same 8-state custody axis — rather than as a synonym
replaced by CUSTODY_MODEL's REGISTERED state (row 6's weaker *"resolves to"* wording is not read as
replacement).

**Consequence.** DECLARED does **not** require a computed `broker_flow` fingerprint as a precondition;
fingerprinting remains gated at the `FINGERPRINTED` step, per §3.4's original, literal text. A Dataset's
separate CUSTODY_MODEL asset-state (CREATED/REGISTERED/etc.) tracks underneath DECLARED without collision,
exactly as ruled for Hypothesis.

**Scope and limits.** This decision rules on the *interpretation* of two existing canonical documents; it does
**not** amend either document's text (amendment remains Research Architect authority per each document's own
header), and it does **not** itself transition Dataset A or any other Dataset Object to DECLARED, FINGERPRINTED,
or FROZEN. The qualifier *"unless a higher-precedence governance rule requires otherwise"* is preserved
verbatim — this ruling stands unless and until a document ranked higher in the Decision-Making Hierarchy
(`.claude/rules/research-governance.md`) is shown to require a different reading.

**Files changed:** none besides this entry. No dataset was created, declared, fingerprinted, or frozen. No DB,
vendor, backfill, or repair operation was performed.

**Related:** [[RESEARCH_OBJECT_SCHEMA]] §3.4 · [[CUSTODY_MODEL]] §4.1, §4.6, CU-1 · [[CUSTODY_AMENDMENT]] §3 rows
6 and 9 · `docs/research_programs/P-M/BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §1 (D-1 origin),
§5 (decision surface).

---

### D-037 · Dataset A `capability_class` approved (Option A) — Available Today, informed-flow/adverse-selection proxy
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** CRO capability-class approval (O4 Dataset field) · **Approval authority:** CRO (issued via Owner decision, this session)

**Decision — APPROVED (Option A).** Quoted as issued: *"Approve the proposed CRO capability_class as: Available
Today, informed-flow/adverse-selection proxy, per DATA_FEASIBILITY_STUDY §4.1."*

`capability_class` for `DS-broker_flow-idx80-nonpit-2025_2026v1` (Dataset A) is set to **Available Today**,
category **informed-flow / adverse-selection proxy** (not true OFI — proxy tier), exactly as
[[DATA_FEASIBILITY_STUDY]] §4.1 already states following its 2026-09-09 correction (this session; `broker_flow`
inventory span corrected from ~3.5 mo to ~20 mo [DB-VERIFIED]).

**Scope and limits.** This approval does **not** clear the [[DATA_FEASIBILITY_STUDY]] §5.3 history-maturity gate
for `broker_flow` — that determination was explicitly left open by the 2026-09-09 correction and remains a
separate, unresolved item for any future hypothesis binding this dataset, not a DECLARED-blocking condition per
se. This approval is scoped to Dataset A's `capability_class` field only; it does not extend to Dataset B or to
`broker_flow` generally beyond what [[DATA_FEASIBILITY_STUDY]] §4.1 already states.

**Files changed:** none besides this entry. No dataset was created, declared, fingerprinted, or frozen. No DB,
vendor, backfill, or repair operation was performed.

**Related:** [[RESEARCH_OBJECT_SCHEMA]] §3.4 (`capability_class` field, CRO approval ownership) ·
[[DATA_FEASIBILITY_STUDY]] §4.1, §5.3 (corrected 2026-09-09) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §3 (R-7), §4, §5 (D-2
origin).

---

### D-038 · R-1 authorization-receipt sufficiency ruled (Option A) — D-032 + D-033 sufficient, no separate artifact required
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-scope owner decision (receipt-sufficiency ruling) · **Approval authority:** Owner

**Decision — APPROVED (Option A).** Quoted as issued: *"D-032 + D-033, as persisted in DECISION_LOG.md, are
sufficient to satisfy R-1. No separate authorization-receipt artifact is required."*

R-1 (`docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §J.1: "Persisted Owner
authorization receipt for the data-layer backfill") is satisfied by D-032 (analytical-window and freeze-strategy
decisions) and D-033 (Owner approves the IDX80-scoped admission path, H-1), as persisted in this document. No
separate authorization-receipt artifact will be produced.

**Scope and limits.** This ruling is specific to R-1's textual requirement; it does not rule on R-10's separate
branch-commit question (D-032 through D-038 remain working-tree-only as of this entry), and does not itself
grant DECLARED status.

**Files changed:** none besides this entry. No dataset was created, declared, fingerprinted, or frozen. No DB,
vendor, backfill, or repair operation was performed.

**Related:** D-032, D-033 · `docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §J.1
R-1 · `docs/research_programs/P-M/BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §3 (R-1), §5 (D-3
origin).

---

### D-039 · Dataset A `asset_class` sufficient for DECLARED at PROPOSED tier — no separate ratification required
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-scope owner decision (O4 field-gating micro-decision) · **Approval authority:** Owner

**Decision — APPROVED.** Quoted as issued: *"The existing PROPOSED `asset_class` value in the Dataset A
admission draft — 'IDX equities, IDX80 universe (fixed backfill-time roster — not PIT membership)' — is
sufficient for the DECLARED gate without separate Owner ratification. No separate `asset_class` ratification is
required at DECLARED. Its status remains PROPOSED/declared metadata as applicable under the governing schema,
with any later ratification or refinement handled at the appropriate subsequent lifecycle gate if required."*

This closes the one residual item identified when the DECLARED gate was re-run following D-036/D-037/D-038: `asset_class`
(one of ROM's five cited O4 mandatory fields) carried only a PROPOSED value from
`BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §A.2, never explicitly Owner-ratified the way `dataset_id`
was via H-5, and — unlike `regime_classification` (F-5) and `provenance_hash` (F-1) — had no existing F-item
deferring it to `FROZEN`. This entry establishes, for Dataset A specifically, that `asset_class` did not need
that ratification to clear DECLARED; its PROPOSED status stands as sufficient, with ratification or refinement
available (not required) at a later gate.

**Scope and limits.** This decision does **not** alter Dataset A's substantive scope (universe, window,
exclusion, NON-PIT status) — the quoted `asset_class` string is adopted verbatim from the admission draft,
unmodified. It does not itself transition Dataset A to DECLARED, FINGERPRINTED, or FROZEN, and does not
generalize to any other O4 field or any other Dataset Object without a separate ruling.

**Files changed:** none besides this entry. No dataset was created, declared, fingerprinted, or frozen. No DB,
vendor, backfill, or repair operation was performed.

**Related:** D-036, D-037, D-038 (the three prior rulings this completes) ·
`docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §A.2 (`asset_class` PROPOSED
value, origin) · `docs/research_programs/P-M/BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md` §4 (O4
field closure).

---

### D-040 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to DECLARED
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner

**Decision.** Dataset A enters `DECLARED` ([[RESEARCH_OBJECT_SCHEMA]] §3.4), all ten §J.1 receipts (R-1…R-10,
[[DECISION_LOG]] D-032…D-039) and the four lifecycle/field micro-decisions (D-036…D-039) having closed with no
remaining blocker, per `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md`.

**Not authorized by this transition:** FINGERPRINTED, FROZEN, hypothesis registration, or empirical testing —
each remains gated on its own separate prerequisites (F-1…F-5, [[HYPOTHESIS_LIFECYCLE]] G1) and requires its
own future decision.

**Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (DECLARED row updated
from "NOT ACTIONED" to "DECLARED, 2026-09-09") · `BROKER_FLOW_DATASET_A_DECLARED_TRANSITION_REQUEST_2026-09-09.md`
(status annotation only). No code, DB, schema, fingerprint, or freeze operation performed.

**Related:** D-032…D-039 · `BROKER_FLOW_DATASET_A_DECLARED_READINESS_2026-09-09.md`.

---

### D-041 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to FINGERPRINTED
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner

**Decision.** Dataset A enters `FINGERPRINTED` ([[RESEARCH_OBJECT_SCHEMA]] §3.4), with `provenance_hash =
329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558` (scope declared per
`BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` §2) and the formal coverage-audit receipt (§3 of the
same document) both on record.

**Not authorized by this transition:** FROZEN, hypothesis registration, or empirical testing — each remains
gated on F-3/F-4/F-5 and [[HYPOTHESIS_LIFECYCLE]] G1 respectively.

**Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (FINGERPRINTED row) ·
`BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md` (status annotation only).

**Related:** D-040 · `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md`.

---

### D-042 · Dataset A `regime_classification` — Option B ratified for F-5 (lightweight characterization, not O15)
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** O4 Dataset field-gating decision (FROZEN prerequisite) · **Approval authority:** Owner

**Decision — APPROVED (Option B).** Quoted as issued: *"Authorize a narrow, lightweight, evidence-derived
`regime_classification` characterization for the sample window, following the worked-example style rather than
creating a full O15 Regime object."* Scope as issued: characterize 2025-01-02 → 2026-08-27 using only existing
canonical market evidence; do not alter Dataset A; do not create a formal O15 Regime object; do not invent or
infer unsupported classifications; document methodology, evidence, and limitations; keep the result descriptive
rather than trade-conditioned. **This authorization is scoped only to satisfying F-5 for Dataset A's FROZEN
gate.**

**Result.** `regime_classification` populated:
> *"mixed — SIDEWAYS 61.6% / BEAR 26.5% / BULL 11.9% of trading days (rule-based, ADX(14)>25 & MA-slope(20,5)
> thresholds, reusing `engine/regime_filter.py::detect_regime()`'s existing definition, applied daily to IHSG);
> includes a documented ~41.5% peak-to-trough IHSG drawdown (2026-01-20 peak 9,134.70 → 2026-06-08 trough
> 5,342.14), followed by partial recovery. Overall window return −10.32%. Descriptive characterization only —
> not an O15 Regime object; not trade-conditioned; not applied to any strategy."*

Full methodology, evidence, and limitations: `BROKER_FLOW_DATASET_A_REGIME_CHARACTERIZATION_2026-09-09.md`. No
new threshold or classification rule was invented — the exact, already-canonical `detect_regime()` rule was
applied day-by-day across the window rather than only its usual single-latest-bar use. `regime_profiles` was
not written to and does not exist as a table in this database; no O15 Regime object lifecycle was entered.

**Scope and limits.** This decision and its result do not alter Dataset A's population, universe, window, or
exclusion; do not register a hypothesis; do not run an empirical test; and do not themselves transition Dataset
A to FROZEN.

**Files changed:** this entry · `BROKER_FLOW_DATASET_A_REGIME_CHARACTERIZATION_2026-09-09.md` (new).

**Related:** `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` §C (F-5 origin) · `WORKED_EXAMPLE_END_TO_END.md`
§S4 (style precedent) · `engine/regime_filter.py::detect_regime()` (reused methodology).

---

### D-043 · Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` transitioned to FROZEN
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** O4 Dataset lifecycle transition · **Approval authority:** Owner

**Decision.** Dataset A enters `FROZEN` ([[RESEARCH_OBJECT_SCHEMA]] §3.4). F-1…F-5 ([[DECISION_LOG]] D-040,
D-041, and this session's F-3/F-4 closure + D-042's F-5 closure) are all satisfied. The CUSTODY asset-state's
frozen condition was already triggered at FINGERPRINTED (D-041, per ROM v2.0 §3.2 "Frozen on fingerprint") and
requires no separate action here. `provenance_hash` remains
`329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`, unchanged.

**Not authorized by this transition:** hypothesis registration or empirical testing — each remains gated on
[[HYPOTHESIS_LIFECYCLE]] G1 and requires its own future decision. Amendment after FROZEN is prohibited per
[[RESEARCH_OBJECT_SCHEMA]] §3.4 Ownership ("Amend after freeze: prohibited"); any future correction is a new
Dataset version, per Versioning ("Immutable on fingerprint. A revised dataset is a new Dataset").

**Files changed:** this entry · `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §G (FROZEN row) ·
`BROKER_FLOW_DATASET_A_FROZEN_TRANSITION_REQUEST_2026-09-09.md` (status annotation only).

**Related:** D-040, D-041, D-042 · `BROKER_FLOW_DATASET_A_FROZEN_GATE_2026-09-09.md` ·
`BROKER_FLOW_DATASET_A_REGIME_CHARACTERIZATION_2026-09-09.md`.

---

### D-046 · History-maturity gate — backfilled-history counting rule, Option C (QUALIFIED COUNT) ratified
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-governance interpretive decision · **Approval authority:** Owner/CRO

**Decision — APPROVED (Option C — QUALIFIED COUNT).** For [[DATA_FEASIBILITY_STUDY]] §5.3 / LIM4's
history-maturity gate: **genuine vendor-backfilled historical data counts toward span-based maturity for
regime-stratified validation and walk-forward validation.** It does **not**, by itself, advance maturity for
**forward-observation phenomena — including decay estimation** (LIM7: *"decay is detectable only in
arrears"*) — which require genuinely elapsed future observation that backfill cannot supply by its nature.

**This is a qualified counting rule, not a blanket maturity clearance.** It resolves *whether backfilled span
is eligible to count at all* (Q1) — it does not resolve, and does not attempt to resolve, *how much span is
required* (`N`, still unassigned anywhere in the corpus) or *how a Dataset Object's specific population is
checked against that requirement* (previously explored as Q3 and resolved separately, see below). Both
remain open.

**Consequence for Dataset A.** `DS-broker_flow-idx80-nonpit-2025_2026v1`'s genuine historical span
(`2025-01-02 → 2026-08-27`, ~20 months, confirmed non-synthetic vendor-backfilled data — this session's F-3
finding) is **eligible to be considered** for regime-stratified / walk-forward maturity. **Dataset A is NOT
thereby declared mature or cleared for validation.** No numeric or qualitative sufficiency bar is applied or
satisfied by this entry. For decay-estimation purposes specifically, Dataset A's maturity clock is unaffected
by this ruling and would run only from genuinely elapsed future observation, if and when that becomes relevant
to a specific hypothesis.

**Preserved, unchanged by this entry:**
- **F-5 (`regime_classification`) remains CLOSED** (D-042).
- **Dataset A remains FROZEN** (D-043) — this entry performs no lifecycle transition and does not touch
  Dataset A's population, universe, window, or exclusion.
- **Q3 remains resolved as previously recorded:** `regime_config.yaml::cell.min_n=100` is a trade-level,
  per-hypothesis/G1 statistical floor (gatekeeper `min_n_cell`, NR7 `t3_min_n`) — it is **not** a Dataset-level
  maturity threshold and plays no role in this ruling.
- **`N` is explicitly NOT assigned a value by this entry.** No numeric or qualitative sufficiency standard is
  invented here; that remains a separate, still-open determination.

**Not authorized by this entry:** hypothesis registration, empirical validation, walk-forward or
regime-stratified testing, or any modification to Dataset A.

**Files changed:** this entry only. `DATA_FEASIBILITY_STUDY.md` was **not** modified — no existing governance
mechanic requires an interpretive ruling of this kind to be written back into the study itself; §5.3's text
already states the requirement in a form this ruling merely interprets, without contradicting or overriding it.

**Related:** LIM4, LIM7 · [[DATA_FEASIBILITY_STUDY]] §5.3 · `HYP-PM-0001_DRAFT.md` §5, `HYP-PM-0001_POWER.md`
§3–§4 (precedent, silent on this exact question) · this session's F-3 finding (backfilled-data genuineness) ·
D-042 (Dataset A regime characterization) · D-043 (FROZEN, unaffected).

---

### D-047 · History-maturity gate — `N` threshold deferred to per-Program PG-A initiation (Option 3)
**Status:** APPROVED · **Date:** 2026-09-09 · **Type:** Research-governance interpretive decision · **Approval authority:** Owner/CRO

**Decision — APPROVED (Option 3 — DEFER ENTIRELY TO PER-PROGRAM INITIATION).** The remaining `≥N months`
question under [[DATA_FEASIBILITY_STUDY]] §5.3 / LIM4 is resolved as follows:

- **The canonical corpus does not define a numeric `N`.** Exhaustive search (`≥N months`, `N months`,
  `multi-year`, `12/18/24/36 months`) found no numeric candidate anywhere in `docs/` or `research/`.
- **"Multi-year" is not operationally quantified** anywhere LIM4 or §5.3 use the term.
- **`min_n=100` is not applicable as a Dataset-level maturity threshold** — confirmed (Q3): it is a trade-level,
  per-hypothesis/G1 statistical floor (`regime_config.yaml::cell.min_n`, gatekeeper `min_n_cell`, NR7
  `t3_min_n`), unrelated to raw dataset span or regime-day counts.
- **The prior one-regime precedent (`HYP-PM-0001_POWER.md`, `EXP-PM-0001/FAILURE_ENTRY.md`) establishes
  insufficiency, not sufficiency,** of multi-regime presence — observing only one regime is disqualifying;
  observing more than one is not thereby stated anywhere to be sufficient.
- **No new Dataset-level observation threshold is invented by this entry.**
- **History maturity remains a prerequisite to be assessed at Program initiation (PG-A)**, per
  `RESEARCH_PROGRAM_STANDARD.md` §PG-A/PG-14 and `OBJECTIVES_2026H2.md` O5's existing directive — *"monitor
  history depth; when LIM4 clears, run the PG-A initiation packet"* — using the evidence available at that
  time, not a threshold fixed now.
- **The PG-A initiation packet for Program P4 (Informed-Flow) must make the LIM4 maturity determination
  explicit** before any validation/generalization scope is authorized under that Program.
- **PG-14's Program timebox is a separate mechanism** (the forward-evidence timebox, fixed ex ante at PG-A,
  never extended to rescue a claim) and is unaffected by this entry.
- **Dataset A's D-046-eligible span (`2025-01-02 → 2026-08-27`) and D-042's three-regime characterization may
  be considered as evidence at the future PG-A assessment, but neither constitutes pre-clearance** of the gate
  — this entry does not rule Dataset A, or any dataset, mature.
- **Decay estimation remains subject to D-046's genuinely-elapsed-future requirement**, unaffected by this
  entry — backfilled span does not advance decay maturity under any option considered.

**Preserved, unchanged by this entry:**
- **Dataset A remains FROZEN** (D-043) — no lifecycle transition performed; Dataset A's population, universe,
  window, and exclusion are untouched.
- **F-5 (`regime_classification`) remains CLOSED** (D-042).
- **Q1 remains resolved as Option C (QUALIFIED COUNT)** (D-046).
- **Q3 remains resolved:** `min_n=100` is trade-level/per-hypothesis/G1, not a Dataset-level maturity threshold.

**Not authorized by this entry:** hypothesis registration or empirical validation — neither is performed or
enabled by this ruling. No Program P4 PG-A packet is initiated by this entry; it only states what that future
packet must do.

**Files changed:** this entry only. `DATA_FEASIBILITY_STUDY.md` was **not** modified — this ruling interprets
and defers application of §5.3's existing text; it does not amend it. Dataset A was not modified.

**Related:** LIM4, LIM7 · [[DATA_FEASIBILITY_STUDY]] §5.3 · `RESEARCH_PROGRAM_STANDARD.md` §PG-A, PG-13, PG-14 ·
`OBJECTIVES_2026H2.md` O5 · `RESEARCH_PROGRAM.md` (P4 row, "Not initiated — timebox watch only") ·
`HYP-PM-0001_POWER.md`, `EXP-PM-0001/FAILURE_ENTRY.md` (one-regime insufficiency precedent) · D-042, D-043,
D-046.

---

## 2i. G1/C-family governance — family determination (Option B), governance receipts, and G1 Run 1 classification, 2026-09-11

**Scope note, read before the entries below:** the Owner decisions receipted here were issued via the ZCode
execution session (external to this repository) and are recorded **on the same basis as D-032's and D-033's
scope notes** — as receipts of Owner directives, not as independently verified cross-checks. The empirical
artifacts they receipt (frozen store, run output, manifests) are hash-pinned in
`docs/research_programs/P-M/dataset_b/artifacts/DATASET_B_FREEZE_MANIFEST_v1.json` and
`docs/research_programs/P-M/g1_harness/G1_RUN_MANIFEST_RUN1_2026-09-11.json`. Nothing in this section
executes any empirical test, modifies any dataset, or amends any methodology.

### D-048 · C-family determination — {C2, C3, C7} formalized as a separately-denominated family (Option B); no I-taxonomy assignment made
**Status:** APPROVED (Option B) · **Date:** 2026-09-11 · **Type:** Research-scope owner decision (multiplicity/family determination) · **Approval authority:** Owner

**Decision.** Per the Owner's approval of Option B from
`docs/research_programs/P-M/g1_harness/OWNER_DECISION_PACKET_FAMILY_ASSIGNMENT_2026-09-11.md`: the
already-registered arms **{C2, C3, C7}** are formalized as a **separately-denominated hypothesis family**
("P-M · C-family"), opened per the registry's own "family opened at first registration" precedent (D-028,
PG-3), with the G1 replacement registration (`g1_harness/G1_REGISTRATION_v1_2026-09-11.md`) as its first
registration act and `C7_REGISTRATION_v1_2026-09-11.md` as the C7 member registration.

**Explicitly NOT decided / NOT done by this entry:**
- **No I-taxonomy assignment.** C2, C3, and C7 are **not** classified as I5, I6, I7, or I12. The taxonomy
  assignment question was ruled UNRESOLVED in `g1_harness/G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` (no
  authoritative document assigns any C-number to an I-entry) and remains an Owner prerogative for the future.
- **No pooling.** The C-family is not pooled with, and does not modify, the P-M {I5, I6, I7, I12} family.
- **No empirical execution authorized** by this entry (C7 has not run; C2/C3 were executed under the prior
  owner-authorized G1 registration and are receipted below).

**Multiplicity consequences.** P-M {I5, I6, I7, I12} denominator: **unchanged** (2 consumed members;
HYP-PM-0001, HYP-PM-0003). C-family denominator: **3 registered arms** — C2 (executed, governance-invalidated),
C3 (executed, valid bounded null), C7 (registered, pending execution). C1a/C1b are WITHDRAWN pre-execution and
**do not count** (same no-slot treatment as pre-registration drafts, per the registry's DRAFT precedent).

**Governance receipts (entered by this entry; hashes pinned in the cited manifests):**

| # | Receipt | Identity |
|---|---|---|
| 1 | **Dataset B freeze** | store sha256 `21661f033145ef90…`; freeze manifest v1 `dataset_b/artifacts/DATASET_B_FREEZE_MANIFEST_v1.json` (sidecar `95f2c998…`); FINGERPRINT_v2 `1a68ab1c…`; 30,880 cells (30,877 SUCCESS + 3 EMPTY), 0 failed/truncated |
| 2 | **BFI-002 replacement registration** | `g1_harness/G1_REGISTRATION_v1_2026-09-11.md` — dated NEW registration; original `BROKER_FLOW_PREREGISTRATION.md` NOT FOUND (retrieval report 2026-09-11); not a reconstruction |
| 3 | **C1a/C1b withdrawal** | freq UNKNOWN/FORBIDDEN (SEMANTIC_REGISTER_v1); arms `WITHDRAWN_FREQ_DEPENDENT`, unconditional, never executed |
| 4 | **NF ratification** | `NF = (buy_lot − sell_lot)/(buy_lot + sell_lot)` from production `stockbit_flow`; T+1; market-flow-control only; window digest `60f5f91c…` (record `g1_harness/G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md` §3) |
| 5 | **Six C7 owner decisions** | outcome/contrast/horizons/multiplicity/MDE/persistence — incorporated verbatim in `C7_REGISTRATION_v1_2026-09-11.md` §3 |
| 6 | **G1 Run 1 + classification** | executed 2026-09-11, exit 0; classification ledger in the entry below |
| 7 | **C-family decision** | this entry (D-048, Option B) |

**G1 Run 1 classification ledger (preserved exactly):**
- **C1a = INVALID / non-reportable** (WITHDRAWN before execution; freq UNKNOWN; no numbers produced).
- **C1b = WITHDRAWN / never implemented** (no C1b cell existed in the harness).
- **C2 = INVALID** (governance-invalidated: registered species-mix control unimplementable — freq-dependent; executed unconditional contrast does not test the designed conditional estimand).
- **C3 = VALID → NOT CONFIRMED, bounded** (executed exactly as registered; determinate null: primary k=5 θ = +5.8 bp, NW t = +0.323, Holm p = 1.0; robust to family recomposition).
- **G1 overall = SPLIT / governance-invalidated** (one valid bounded null + one governance-invalidated arm + two withdrawn arms; not a clean test of the original three-arm design).

**Not authorized by this entry:** C7 execution (the `c7_registered` gate remains FALSE); any empirical run;
any methodology, threshold, k-set, cost, exclusion, or inference change; any I-taxonomy assignment; any
alteration of the G1 result or artifacts.

**Provenance condition on future execution:** `docs/research_programs/P-M/g1_harness/` and
`docs/research_programs/P-M/dataset_b/` are currently **untracked** in git. Before any future empirical
execution, the authoritative harness/governance files (list in
`g1_harness/G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` §E2) must be committed, ZCode recorded as sole owner of
`g1_harness/`, and the immutable `runs/<run_id>/` provenance wrapper **implemented or the execution
explicitly gated on it** (closeout §E3). Execution from an uncommitted/ambiguous source state is prohibited.

**Files changed:** this entry · `HYPOTHESIS_REGISTRY.md` (C-family rows) · no code, no datasets, no
methodology files.

**Related:** D-032 (window/freeze decisions; Items C, D OPEN) · D-033 (admission path) ·
`G1_OWNER_DECISION_PACKET_FAMILY_ASSIGNMENT_2026-09-11.md` · `G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` ·
`G1_REGISTRATION_v1_2026-09-11.md` · `C7_REGISTRATION_v1_2026-09-11.md`.

---

## 2j. C7 governance — ratifications, semantic hard gate, EXPERIMENT_LEDGER, and C7 execution authorization, 2026-09-11

**Scope note:** the Owner decisions below were issued via the ZCode execution session (external to this
repository) and are recorded **on the same basis as D-032/D-033/D-048** — as receipts of Owner directives.
This section ratifies the forensic reclassifications, adopts the all-broker-net semantic hard gate,
receipts the Dataset B freeze, ratifies the C7 NF construction, adopts the EXPERIMENT_LEDGER, and
authorizes `c7_registered=true`. **C7 execution itself was separately authorized by the Owner** and is
executed under `g1_harness/C7_REGISTRATION_v1_2026-09-11.md` as registered — no methodology change.

### D-049 · Historical reclassifications ratified; all-broker-net semantic hard gate adopted; C7 NF ratified; EXPERIMENT_LEDGER adopted; Dataset B freeze receipted; c7_registered authorized
**Status:** APPROVED · **Date:** 2026-09-11 · **Type:** Governance ratification + research-gate adoption · **Approval authority:** Owner

**R-1 · Historical reclassifications (owner-ratified; original records preserved):**
- **HYP-PM-0003 → INVALID — DATA/SEMANTICS.** The registered predictor `SUM(lot)` is the exchange
  accounting identity (independently measured: identically zero on 68.10% of the 97,762 ticker-days in
  the Dataset A window; |net|/Σ|lot| p90 = 0.002). The registered F2 remains the historical outcome for
  the registered artifact predictor; substantively, the M2.1/I7 hypothesis was never tested on a valid
  directional observable.
- **BROKER-001 / BFI-001 PRIMARY (BFI_broad = NV/GV) → INVALID — DATA.** Independently measured on the
  exact Dataset A window: |NV/GV| p50 = 0.0, p90 = 0.00201, p99 = 0.0146, max = 0.0602 (near-degenerate;
  P(≥0.2) = 0). BFI-001's structure secondaries (CONC t=−2.65 Holm 0.097; BREADTH t=+2.41 Holm 0.164;
  LOKAL t=+2.43 Holm 0.164) remain **VALID → NOT CONFIRMED** footprints.
- **G1 C2 → INVALID — SPECIFICATION.** The registered "conduit disagreement" state is algebraically
  coupled (`for + loc + pem ≡ 0`, integer-exact in 100.00% of 30,877 frozen-store cells) and the
  execution gate (gross-participation ≥ 15%) inflates incidence 26.6% → 72.5% versus the descriptive
  net-share form. The C2 G1 number is reportable only as an unconditional thresholded foreign-net
  direction contrast.

**R-2 · All-broker-net semantic hard gate (ADOPTED as a pre-execution gate; appended to
DATASET_B_SEMANTIC_REGISTER):** all-broker aggregate net flow constructed from the two sides of the same
transaction population MUST NOT be treated as a directional predictor; any net/gross quantity must first
pass the five-part validation (accounting identity, semantic source, aggregation level, truncation
behavior, PIT availability) recorded in `g1_harness/G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` Part G and
enforced for C7 in `run_c7`'s registered outcome check (intensity = gross/ADV20 — a Σ|value|
construction, not a net).

**R-3 · C7 NF ratified:** `NF = (buy_lot − sell_lot)/(buy_lot + sell_lot)` from production `stockbit_flow`
(T+1 availability; market-flow-control interpretation only; zero-denominator excluded; window digest
`60f5f91c…` re-verified pre-run). Note: C7's registered outcome/contrast does not consume NF — the
ratification removes the ambiguity flag only.

**R-4 · EXPERIMENT_LEDGER adopted:** `docs/research_programs/EXPERIMENT_LEDGER.jsonl` — non-destructive
unified index over HYPOTHESIS_REGISTRY, research.db (hypotheses/failure_registry/gate_decisions), the
DECISION_LOG receipts, and the g1_harness registration artifacts. Existing registries remain append-only
sources of record; the ledger is the derived canonical index and is itself append-only.

**R-5 · Dataset B freeze receipted:** store sha256 `21661f03…`, freeze manifest v1
(`DATASET_B_FREEZE_MANIFEST_v1.json`, sidecar `95f2c998…`), FINGERPRINT_v2 `1a68ab1c…` — reproduced at
freeze and re-verified at C7 preflight.

**R-6 · `c7_registered = true` authorized** (C7_REGISTRATION_v1, owner-approved six decisions of
2026-09-11). Freq remains UNKNOWN/UNUSED on the C7 path (freq-free by construction, poison-tested).

**Not authorized by this entry:** H0–H3/P0 reconstruction (original remains NOT FOUND); D-032 Items C/D
resolution; any C1a/C1b revival; any methodology/threshold/horizon/inference change.

**Files changed:** this entry · `DATASET_B_SEMANTIC_REGISTER_v1.json` (appended gate entry) ·
`EXPERIMENT_LEDGER.jsonl` (new) · `FAILURE_REGISTRY.md` (owner-ratification annotation) ·
`HYPOTHESIS_REGISTRY.md` (HYP-PM-0003 reclassification annotation) · `g1_config.json` (`c7_registered=true`).

**Related:** D-032, D-033, D-048 · `G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` ·
`OWNER_DECISION_PACKET_FAMILY_ASSIGNMENT_2026-09-11.md` · `C7_REGISTRATION_v1_2026-09-11.md` ·
`FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md`.

---

## 2k. I7 registration authorization — D-1 population, D-2 power/MDE ruling, 2026-09-14

### D-050 · I7 (intraday execution timing): v004 PIT population accepted; ex-ante statistical power/MDE requirement closed by Owner ruling at the 0.60% economic floor; registration authorized
**Status:** APPROVED · **Date:** 2026-09-14 · **Type:** Research-scope owner decision (population + ex-ante criterion + registration authorization) · **Approval authority:** Owner / CRO

**Context.** I7 — *intraday execution timing / adverse-selection sequencing*, mechanism class M2, taxonomy
entry **I7** — reached G1 with five of six §5.2 intake elements satisfied and two Owner decisions
outstanding (`I7_OWNER_DECISION_PACKAGE_2026-09-14.md`).

**D-1 · Population substitution — ACCEPTED.** The PIT-valid **v004** cohort is I7's registration
population, superseding the ~277-session historical window described in the candidate specification §7/§12,
from which it is **disjoint**. Bound **by fingerprint, not by name** (`RESEARCH_OBJECT_SCHEMA` l.233):

| Field | Value |
|---|---|
| Sessions · window | **76** · 2026-04-28 → 2026-09-11 |
| Admissible ticker-days · tickers · bar rows | **61,335** · **868** · **19,793,865** |
| Store sha256 | `e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba` |

The historical interval is excluded wholesale under **E-PIT-1**: 99.41% of its cells were written >120 days
after their session (median lag **364 days**), which `LITERATURE_RESEARCH_STANDARD` bias **B3** classes as
*"F7 look-ahead in the source itself"*. Acceptance was available as a population declaration rather than a
preregistration amendment because I7 was in **DRAFT** (HL-2: *"Before it, refine freely"*). §7/§12 are
superseded **as descriptions**, not as parameters. **Closed.**

**D-2 · Ex-ante MDE / assumed σ / feasibility gate — CLOSED BY OWNER RULING.** The Owner explicitly
authorizes I7 to proceed **without an ex-ante statistical power/MDE claim beyond the already-authorized
0.60% economic/friction floor**.

- **Retained:** the **0.60% round-trip friction floor** from the versioned cost authority
  (`engine/exits/costs.py`), authoritatively supported by the ratified `HYP-PM-0001_POWER` §3–§4
  methodology (*"the ex-ante MDE must be economic, not statistical"*), by program gate **F4**
  (`RESEARCH_PROGRAM` §6.1) and by **PR-3** (`EXPERIMENT_STANDARD` §1 Q2). It is already declared in the I7
  specification §14 (`theta_net = theta_primary − 0.006`).
- **Accepted as a governance limitation:** the absence of an authoritative, I7-specific **assumed σ** and of
  an applicable **feasibility gate**. A corpus search (`I7_D2_METHODOLOGY_SEARCH_2026-09-14.md`,
  `I7_D2_EVIDENCE_RECORD_2026-09-14.md`) found neither.
- **Explicitly NOT filled** by estimation from the frozen cohort, by analogy to HYP-PM-0001 / HYP-PM-0003 /
  C7 / HYP-PM-0008, or by newly invented methodology. **No power-derived minimum-N or stopping rule exists
  for I7**, and none may be introduced post-registration (R15).

**Consequence for interpretation, recorded now:** I7 carries **no power claim**. A non-rejection is
therefore **not** evidence of absence, and must never be reported as one. This is the same limitation the
Owner recorded for C7 (D-049 lineage, `C7_REGISTRATION_v1` §3 item 5), reached here on its own evidence
rather than by analogy.

**Also recorded at registration:** the **R7 provenance limitation** — PIT status rests on
`stockbit_flow.updated_at`, a same-commit write timestamp; the vendor's original payload is not preserved,
so the cohort supports *"this system held these values contemporaneously"* but not *"the original vendor
response is independently re-verifiable"*. A **verification**, not an availability, limitation.
`point_in_time` is declared **true with this qualification**; `custody_partition` is **in-sample**.
The **B4 limitation** (Papan Pemantauan Khusus / board membership unidentifiable) is likewise declared.

**Registration authorized** conditional on all other G1 gates passing, which were verified before the
transition: 27/27 tests, 8/8 executable validation gates, ledger reconciliation exact and MECE, v003
immutable, cohort unchanged.

**Family effect.** I7 registers as **HYP-PM-0009**, the **third** member of **P-M {I5, I6, I7, I12}**
(D-028), joining HYP-PM-0001 (FAILED F2) and HYP-PM-0003 (FAILED F2 → INVALID-DATA). The slot is permanent
(PG-3, OS-10). `HYP-PM-0002` remains DRAFT and consumes no slot; `HYP-PM-0007` remains provisionally
reserved for the unratified BROKER-001 alias; `HYP-PM-0008` is an unregistered DRAFT (I1 price-limit).

**Not authorized by this entry:** execution of I7; any change to the cohort, exclusions, estimator, primary
endpoint, threshold, inference, multiplicity or decision rule; any variant or follow-up; any retest of C3 or
C7; activation of the prospective capture service.

**Files changed:** this entry · `HYPOTHESIS_REGISTRY.md` (HYP-PM-0009 row + family ledger) ·
`HYP-PM-0009_REGISTERED.md` (new frozen record).

**Related:** D-028 (family declaration) · D-049 (semantic gate; C7 MDE precedent) ·
`I7_OWNER_DECISION_PACKAGE_2026-09-14.md` · `I7_G1_GAP_CLOSURE_2026-09-14.md` ·
`I7_D2_EVIDENCE_RECORD_2026-09-14.md` · `I7_ACCRUAL_READINESS_2026-09-14.md`.

---

## 3. Pointers — decisions recorded in full elsewhere (not duplicated)

Per 42010 §5.7 the rationale must be *recorded*, not *centralized*. These eight carry full ADRs in [[01_SCIENTIFIC_FOUNDATION]] §14 and are indexed here only.

| ID | Decision | Type |
|---|---|---|
| ADR-L1-001 | System-of-interest is the research institution, not the trading system | Architectural |
| ADR-L1-002 | Critical rationalism + severity, not Bayesian epistemology (**revisit at ≥3 researchers**) | Scientific |
| ADR-L1-003 | Mechanism-first is a gate, not a preference | Scientific |
| ADR-L1-004 | Six exclusive domains, substrate before phenomenon | Scientific |
| ADR-L1-005 | Reproducibility is constitutive; conclusion-invariance, not bit-identity | Scientific |
| ADR-L1-006 | Data feasibility is a scientific constraint, not a budget constraint | Architectural |
| ADR-L1-007 | Declare the single-researcher review deficit; do not absorb it | Governance |
| ADR-L1-008 | Record L2 inconsistencies; do not resolve them here | Architectural |

---

## 4. Outstanding rationale debt (ISO 42010 §5.7 non-conformance)

These decisions **were made** and their rationale **was never recorded**. They are listed rather than reconstructed: each was made by a prior author, and inventing a plausible justification after the fact would produce a rationale that could not be wrong and therefore carries no information — the governance analogue of the retro-fitted mechanism ([[01_SCIENTIFIC_FOUNDATION]] §7.3). **Only the original decider can close these.**

| # | Undefended decision | Document | Question to answer |
|---|---|---|---|
| RD-1 | Why **ten** pipeline stages, and why these ten? | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] | What alternative decompositions were considered? Why is Robustness (S8) separate from Statistical Validation (S7)? |
| RD-2 | Why **these five roles**? | [[RESEARCH_OPERATING_MODEL]] §5 | Why five and not three? What made the Validation Reviewer's independence non-negotiable while other separations were not? (Compounded by AQ-6 — the institution has one researcher.) |
| RD-3 | Why **four gates** at these four points? | [[RESEARCH_OPERATING_MODEL]] §6 | Why is Code Review (G2) a gate but Data Preparation is not? |
| RD-4 | Why **FDR *and* DSR *and* PBO**? | [[RESEARCH_VALIDATION_FRAMEWORK]] §1 | Each is defensible alone. What does the conjunction buy that a subset does not, and what is the cost of the overlap? |
| RD-5 | Why **immutability-on-use** rather than immutability-on-creation? | [[FEATURE_COMPUTATION_GRAPH]] §5 | What alternatives to freezing-at-first-experiment were considered? |
| RD-6 | Why is **half-life estimable** at all? | [[RESEARCH_OBJECT_MODEL]] (Economic Mechanism) | `half_life_estimate` is a required field with no stated method and no data plan (review W12). LIM7 holds that decay is detectable only in arrears. |
| RD-7 | Why **daily-anchored** rather than intraday-anchored inaugural scope? | [[DATA_FEASIBILITY_STUDY]] §5.2 | Recorded as a consequence ("anchor on the deepest data"), which is a reason — but the alternatives are not recorded. **Weakest debt on this list.** |

**Closing rule:** a debt is closed by adding an ADR to the owning document, or a decision entry here, containing the alternatives that were actually considered. If none were considered, the honest record is *"no alternatives were considered"* — which is itself information, and materially more useful than a confabulated defense.

---

## 5. Corrections applied to the canonical corpus (this revision)

Each is a factual correction of a statement objectively contradicted by the repository. No architecture was redesigned. Traceable to **D-012**.

| # | Document | Was | Now | Evidence |
|---|---|---|---|---|
| C-1 | [[REVISION_IMPACT_ASSESSMENT]] §3 | "the **7 canonical architecture documents** are byte-for-byte unchanged (… Market Inefficiency Foundation)" | 6 documents preserved; the 7th never existed and has now been authored | `ls docs/Institutional_Research_Architecture/` — no such file |
| C-2 | [[REVISION_IMPACT_ASSESSMENT]] §4 | Table row "Market Inefficiency Foundation \| L1 \| domain de-overlap…" | Row points to the authored artifact; de-overlap discharged | [[01_SCIENTIFIC_FOUNDATION]] §3.5 |
| C-3 | [[RESEARCH_OS_MASTER_ROADMAP]] §7 | `- [x] **Folder structure** migrated to concern-based hybrid layout (this revision). ✅` | `- [ ]` — **the checkbox was false** | Files remain in `docs/Institutional_Research_Architecture/`; [[REVISION_IMPACT_ASSESSMENT]] §2 itself says migration is "*planned*, not yet executed" — two canonical documents contradicted each other |
| C-4 | [[RESEARCH_OS_MASTER_ROADMAP]] §2 | L1 "🟡 Conceptually done (6 domains)" | 🟢 — artifact exists; the "6 domains" were never written down | Audit D-011 |
| C-5 | [[RESEARCH_OS_MASTER_ROADMAP]] §6 | Dependency graph missing SCOPE→L6, L3→L4, L3→L6 | Edges added | Falsification review, roadmap findings |
| C-6 | [[MIGRATION_PLAN]] §2 | Row `MARKET_INEFFICIENCY_FOUNDATION (domains) → research_os/` — a rename of a file that never existed | Points to the authored artifact | Phantom reference |
| C-7 | [[MIGRATION_PLAN]] §3 | Bare `git mv` sequence | **Step 0 baseline commit inserted** — the plan was unexecutable | `git mv --dry-run` → `fatal: not under version control`. See **D-014** |
| C-8 | [[01_SCIENTIFIC_FOUNDATION]] §16.1 | Claimed the "7 canonical docs cross-referenced" exit item discharged | `⬜` — **overclaimed by its own author** | [[RESEARCH_OS_RECONCILIATION]] §6 requires a one-line v3 cross-reference *inside each of the 7 documents*; §11 maps them centrally to L1, which is a different artifact |

---

*This log is append-only in spirit: entries are amended by adding a superseding entry, never by silent edit. Status values: ACCEPTED · CONTESTED · OPEN · SUPERSEDED. A decision whose justifying premise is refuted is void, not grandfathered — the governance counterpart of [[01_SCIENTIFIC_FOUNDATION]] §0.4's rule for rules.*
