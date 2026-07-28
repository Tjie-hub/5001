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
