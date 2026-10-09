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

### D-051 · HYP-PM-0009 (I7) executed once → FAILED (F2 · prediction failure); terminal; closeout recorded
**Status:** RECORDED · **Date:** 2026-09-15 · **Type:** Post-execution governance record (registration D-050 lineage) · **Approval authority:** Owner instruction (governance closeout, 2026-09-15)

**Execution.** The single registered execution of HYP-PM-0009 was performed **once** as `EXP-PM-0009/R2`
(`run_utc` 2026-09-15T01:41:30Z, in-sample, repository at registration commit `e0e3f91`) after an
in-script pre-execution integrity gate passed **19/19** (preregistration sha `d19dfd0f…` recomputed over
the frozen block; cohort store `e1375264…fba`; candidate spec `76a96545…`; calendars `5012be23…` /
`a7a4eedf…`; accrual ledger 82,814 candidates exact and MECE). No substantive registered field —
hypothesis, H0/H1, primary endpoint, cohort, exclusions, estimator, thresholds, timing windows,
inference, multiplicity, decision rule — was changed at any point.

**Implementation-defect disclosure (implementation correction only).** A first invocation the same day
(`EXP-PM-0009/R1`, 01:39:02Z) was **INVALID — implementation defect, estimand not evaluated**: an
exit-leg index error made `fwd_return = close(t+1)/close(t+1) − 1 ≡ 0` (θ exactly 0, NW_t = NaN). The
registered outcome formula (`close(t+2)/close(t+1) − 1`) was never computed. The correction changed only
the index arithmetic so the code computes the already-frozen formula. R1's artifacts are preserved
verbatim; R2's k=1 arm reproduces R1's accidentally-shifted arm exactly (deterministic cross-check). The
frozen block hash `d19dfd0f…` verifies unchanged before, during, and after execution and closeout.

**Essential result (primary k=1; entry close(t+1), outcome close(t+2)/close(t+1) − 1).**

| Quantity | Value |
|---|---|
| θ_primary | **+0.0337%** per formation-day (+0.000337) |
| Newey-West HAC t (lag 5) | **0.1102** |
| Two-sided p (Holm = identity, single cell) | **0.912223** |
| Daily observations m(d) | **64** (6 dates skipped and counted; 2026-09-08's single cell disposed by step_1) |
| θ_net sensitivity = θ_primary − 0.006 | **−0.5663%** (sensitivity ONLY, never a verdict) |
| Estimation-layer accounting | population 24,187 net-buying cells → X6 475, X5 17,684, surviving 6,028 (MECE) |
| Robustness (non-confirmatory) | k=2: θ −0.0362%, p 0.928 · k=3: θ +0.2138%, p 0.615 |

**Classification (made exactly once): FAIL — F2 · prediction failure.** The registered kill rule
("θ_primary not positive with two-sided p < 0.05 ⇒ REFUTED, terminates FAILED, mode F2") is met: θ is
nominally positive but p = 0.9122. H0 (θ ≤ 0) is not rejected at the registered one-sided decision
(two-sided statistic, nominal one-sided size 0.025).

**Interpretation constraint, carried verbatim into every record:** I7 carries **NO power claim** (D-050).
**"Non-rejection is not evidence of absence"** — this result must never be reported or used as evidence
of absence. The **R7 PIT provenance limitation** is retained in the result (same-commit `updated_at`
custody timestamps; original vendor payload not independently re-verifiable — a verification, not an
availability, limitation; 200/200 source spot-check matches).

**Terminality.** FAILED is terminal (HL-3). Per the registered `no_rescue` rule and the closeout STOP
condition: no rerun, no alternative timing windows, no subgroup analysis, no explanation-seeking analysis,
no post-hoc power, no new threshold, no cohort modification, no rescue hypothesis, no further P-M
execution. HYP-PM-0009 remains **counted permanently** in P-M {I5, I6, I7, I12} (X8, PG-3, OS-10) — the
family's third member, all three now FAILED F2. Continuation only via **T12 supersession**: a new
hypothesis, new G1, its own slot. The next decision is **Owner-level** selection of the next
already-authorized research candidate, if one exists.

**Closeout records (append-only):** `HYPOTHESIS_REGISTRY.md` (row → FAILED, notes, family ledger) ·
`FAILURE_REGISTRY.md` (row **FAIL-PM-0009**; F2 count 3→4; N=5→6) · `EXPERIMENT_LEDGER.jsonl`
(hypothesis record appended) · `experiments/EXP-PM-0009/{FAILURE_ENTRY,CLOSE_OUT_REPORT}.md` (new) ·
R1/R2 execution artifacts preserved unchanged.

**Related:** D-050 (registration; D-1/D-2 rulings) · D-028 (family) · D-049 (semantic gate — compliant
here trivially: no all-broker net constructed; `identity_affected: false`) ·
`experiments/EXP-PM-0009/MANIFEST.md`.

---

### D-052 · Price-Reversal {R1} family opened; HYP-PM-0012 (failed-breakdown anti-edge) registered; FWD-PM-FADE-001 opened
**Status:** RECORDED · **Date:** 2026-09-21 · **Type:** Family open + registration act (D-028/PG-3) ·
**Approval authority:** Owner instruction 2026-09-21 ("open new family" — approving Option A of
`P-M/forward_fade/OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md`)

**What was registered.** HYP-PM-0012 — the failed-breakdown anti-edge: `low(t) < lo20(t)` AND
`close(t) > lo20(t)` (lo20 = prior-20-session rolling low, shifted 1) on the per-row liquid threshold
universe (`adv20 >= Rp 1e9`, `close >= Rp 50`, >= 18/20 sessions traded), next-open fill, fixed
h ∈ {5,10,20} holding periods, 0.60% RT, dual benchmark (IHSG + equal-weight liquid book, both
required), one-way entry-date-clustered SE. Registered claim: forward excess is NEGATIVE; the
tradeable form is an avoidance/exit overlay candidate, never a short and never a standalone entry.

**In-sample basis (no confirmatory weight).** Three independent builds agree: h=20 −1.46% (t −5.64,
IHSG) / −1.47% (t −8.20, EW-book); ex-2025 −1.88% (t −6.80, IHSG); 12,131 signals, 757 tickers, top
name 0.6%. Discovery debt: 2026-09-17 ~12-arm pattern scan (+6 strictness variants); Bonferroni-18
bar (z ≈ 2.99) cleared by every reported horizon.

**Endpoint (frozen, protocol §3).** 12-month PROMOTE track t < −2.5 on BOTH benchmarks; 18-month
final t < −3.0 both; REJECT if cumulative excess >= 0 on either benchmark or < 100 distinct
signal-dates by month 12; decay haircut −0.5% vs IHSG at month 12.

**Family.** P-M · Price-Reversal {R1} opened at this registration, member 1 of the family, scope:
OHLCV-only short-horizon reversal anti-edges, separately denominated from all existing families.
Widening permitted; narrowing/splitting not.

**ID numbering ruling.** HYP-PM-0011 is reserved-retired (referenced only as the untaken
"conservative reading" in the 2026-09-17 FWD-PM-REGIME-001→002 supersession note); this registration
takes HYP-PM-0012.

**Non-wiring clause.** FWD-PM-REGIME-002 is untouched. Any overlay use requires FADE-001 to clear a
§3 checkpoint first (BOOK_OVERLAY_POLICY §4 two-stage rule).

**Receipts:** `P-M/forward_fade/PROTOCOL.md` (registration sha256
`e195967260888315028f33bbbea558ce2f8e02a9d049338cb655313c36a108c5`) ·
`P-M/forward_fade/ledger.json` (opened empty; first eligible entry 2026-09-22) ·
`P-M/HYP-PM-0012_REGISTERED.md` · `P-M/forward_fade/scripts/fade_failed_breakdown.py`
(SHA256SUMS verified 2026-09-21).

### D-053 · Cross-Sectional Volatility {V1} family determined; FWD-PM-VOLEX-SN-001 spec v2 approved; one pre-declared ex-ante re-measurement authorized; registration deferred to D-054
**Status:** RECORDED · **Date:** 2026-09-23 · **Type:** Family determination + pre-registration act (D-028/PG-3) ·
**Approval authority:** Owner instruction 2026-09-23 (approving Option B of
`P-M/forward_volex/OWNER_DECISION_PACKAGE_V1_FAMILY_2026-09-23.md`, commit `c7980d1`)

**Family.** The sector-neutral volatility overlay, when registered, enters a NEW family
`P-M · Cross-Sectional Volatility {V1}` — cross-sectional volatility-level characteristics from OHLCV
only, applied as within-universe exclusion/tilt, measured as a book-level increment vs the same
unfiltered universe, liquid IDX. Beta, factor-model idiosyncratic volatility, skewness/MAX measures,
and any flow or fundamental input are out of scope until a widening amendment. The family opens at its
first registration (D-054); this act consumes no slot. FWD-PM-VOLEX-001 remains outside {V1} as an
unregistered prospective record, declared non-independent: neither test may be cited as evidence for
the other. HYP-PM-0013 is reserved for the registration.

**Pre-registration audit.** The 2026-09-19 draft was not frozen: its headline "clean" evidence row
conditions on zero-volume sessions in the forward holding window (`ext_panel.py` `z_fwd`); four of the
five evidence rows have no committed code; the entry convention differed between evidence and spec;
and its decision rule had ~0.26–0.54 power at the modern-era effect (+0.20%/mo). Spec v2 repairs all
of these before any forward observation exists.

**Pre-declared re-measurement (the last in-sample look).** The exact v2 spec (PROTOCOL_DRAFT §2–§3):
ex-ante filters only, close(t+1) entry, gross increment, iid t. Script
`P-M/forward_volex/remeasure/remeasure_v2.py`, sha256
`5caa68b8bdd3d65ec8250d5133ed32fa9bb1d8df695de2ecfff00e015959e80b`, pinned before execution. It
passed a synthetic self-test (planted effect recovered against an oracle, null ≈ 0, no look-ahead
through future zero-volume) and a structural-only dry run (no returns computed). **Bar:** pre-2021
formations (2000-07..2020-12) t >= 2.87 (Bonferroni-12 over prior pre-2021 overlay looks) AND mean
>= +0.10%/mo.
- **Clears:** D-054 registers HYP-PM-0013 and opens FWD-PM-VOLEX-SN-001.
- **Fails:** no registration. The result is recorded in EXPERIMENT_LEDGER.jsonl, the draft is marked
  REFUSED-AT-G1, and no re-cut is permitted.

**Input provenance.** The original pre-2021 backfill was never committed and did not survive. It was
regenerated 2026-09-23 by `remeasure/fetch_pre2021.py` (sha256
`d8c016b12ebc5bb7e6111270ef47dcc269653e77168989caea2c321bb4de8b4a`) over the 772 tickers of
`data_gaps/data/hist_meta.pkl`: 1,414,611 bars, identical to the original count; content fingerprint
`fd9f54e34f1d7d61300186f760aec943bcfdb5ccf3c39958e7a0462f327c14c9`. Sector file
`sector_map_frozen_v2.csv` (sha256 `3c2c537a81269c87e70b950514dbe7c43be968a976454d9b29e5683d06c0f15d`)
is identical to production `ticker_sector`. Dry-run structure: 88 valid pre-2021 months (median
universe 108, held 96), and 67 valid 2021-26 months.

**Decision rule v2 (to be frozen at D-054).** 48-month single decision: PASS one-sided t > 1.68 AND
mean >= +0.10%/mo; FAIL mean < +0.10%/mo; otherwise INCONCLUSIVE. Harm stop at n >= 12 if the mean is
< -0.20%/mo. 12- and 24-month reports carry no decision.

**Mechanism.** Leverage- and short-sale-constrained demand for high-volatility names (participant
class: leverage-constrained and retail IDX investors); persistence via the Constraint barrier (no IDX
short side) and the Capacity barrier (the pooled version is absent in the top-ADV tercile). No M-class
assignment: ECONOMIC_MECHANISM_TAXONOMY has no fitting class. Referred to the CRO as a candidate class
amendment (01_SCIENTIFIC_FOUNDATION §3.4). The same absence is recorded for HYP-PM-0010 and
HYP-PM-0012.

**Mandate acknowledgement.** A PASS is not deployable under the current book mandate (needs ~100+
names; negative inside IDX80). The registration's purpose is knowledge.

**Non-wiring.** BOOK_OVERLAY_POLICY (still bound to FWD-PM-VOLEX-001), FWD-PM-REGIME-002, and
FWD-PM-FADE-001 are untouched.

**Receipts:** package `P-M/forward_volex/OWNER_DECISION_PACKAGE_V1_FAMILY_2026-09-23.md` ·
`P-M/forward_volex/PROTOCOL_DRAFT.md` v2 (sha256
`1bc868c73f1cbc4925eb06678202594ea80efa50821b9b908f9d9fc532eaa6c2`) ·
`P-M/forward_volex/remeasure/remeasure_v2.py` (sha256
`5caa68b8bdd3d65ec8250d5133ed32fa9bb1d8df695de2ecfff00e015959e80b`) ·
`P-M/forward_volex/sector_map_frozen_v2.csv`.

---

### D-055 · Rule-first gate adopted: one Rule Card + a frozen single run replaces the DRAFT→POWER→REGISTERED→AUDIT chain for new candidates; past defects become mandatory code checks (`research/rulecard/`)
**Status:** RECORDED · **Date:** 2026-09-24 · **Type:** Research-workflow procedure (governance) ·
**Approval authority:** Owner instruction 2026-09-24 ("approve", Cowork session), approving the recommendation
recorded in `docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md` §0/§3 and the chat recommendation of the
same date.

**Numbering.** D-053 reserved D-054 for the conditional VOLEX-SN registration. The re-measurement failed
(REFUSED AT G1, 2026-09-23), so that registration never happened. D-054 stays reserved-unused, following the
HYP-PM-0011/0013 precedent. This entry is D-055.

**Why.** Seven registered hypotheses executed in ten weeks, zero validated; about 2 MB of markdown in `P-M/`, with
the weight in data admission and chained audits (g1_harness 29 files / 452 KB, broker-flow admission 139 KB, I7
112 KB, HYP-PM-0008 110 KB and never registered). The OHLCV registrations (HYP-PM-0010, -0012) had already slimmed
to a 4–5 KB note plus one protocol. What prevents false discoveries is: freezing before the run, running once,
recording every trial, and PIT discipline. The chained audits did catch real defects, and those are kept — as
tests, not prose.

**Decision.**
1. **Scope.** Every *new* candidate. Frozen tests keep their own protocols unchanged: FWD-PM-REGIME-002,
   FWD-PM-FADE-001, FWD-PM-VOLEX-001, and `BOOK_OVERLAY_POLICY.md`. So do the registries' append-only rules
   and family semantics (D-028/PG-3). `family_mapping` is a required card field, decided by the Owner per card.
2. **Three artefacts plus one ledger line per candidate.**
   - `CARD.yaml`, validated by `research/rulecard/card.py`. It merges DRAFT, POWER and REGISTERED.
   - `RESULT.json`, written once by `python -m research.rulecard.cli run`.
   - `VERDICT.md`, generated from the result; the author adds at most five lines of interpretation.
   - One appended line in `EXPERIMENT_LEDGER.jsonl` (`record_type: rule_card_run`).
   Registry rows are still appended by hand.
3. **Freeze.** `FREEZE.json` pins the card, the rule script and the framework (`research/rulecard/*.py`) by
   sha256, plus the Owner approval. A change to any of the three after the freeze makes the run refuse, because
   the verdict logic lives in the framework. A run refuses if `RESULT.json` exists. A crashed run can resume
   only with an explicit flag, and the resume is recorded in the result.
4. **Hurdles (RULE_FIRST_PROTOCOL R3).**
   - Tier R (published rule, literature-default parameters, ≥2 anchors tagged V/V2): one-sided NW t ≥ 2.0, and
     the predicted sign in the discovery half, the confirmation half and ex-2025.
   - Tier N (novel or scan-derived): t ≥ 3.0 and DSR ≥ 0.95, with every trial counted.
   - A card may raise its hurdle, never lower it.
   - The minimum Bayes factor is used only to calibrate these two thresholds to one false-discovery budget.
     The tests themselves stay pre-registered frequentist severity tests, so **ADR-L1-002 is not superseded**.
     This is recorded because the calibration borrows a Bayesian device.
5. **Power gate (R5).** Planning effect = literature effect × 0.5 (× 0.3 if capacity-sensitive). It must reach
   80% power at the declared N, or the card cannot be frozen. If the rule would fail but fewer than 80% of the
   planned months were realised, the verdict is INCONCLUSIVE_UNDERPOWERED — not FAILED (rule R2).
6. **Central verdict** (`evaluate.py`, never the rule script). In order of precedence:
   - INVALID: a mandatory check failed. This is an implementation or data result, not a hypothesis failure.
   - FAIL or INCONCLUSIVE_UNDERPOWERED.
   - FAIL_NOT_MONOTONE: no Patton-Timmermann dose-response over the declared shape (full range, or median to
     tail). The rule is reclassified as a pattern.
   - EFFECT_PRESENT_MECHANISM_UNCONFIRMED: a pre-declared fingerprint has the wrong sign.
   - PASS_NOT_DEPLOYABLE: the long-only bucket-minus-rest test fails.
   - PASS.

   Lifecycle mapping (HYPOTHESIS_LIFECYCLE):
   - freeze = REGISTERED; run = IN_TESTING.
   - FAIL and FAIL_NOT_MONOTONE go to FAILED (F2 unless defended otherwise).
   - INVALID and INCONCLUSIVE_UNDERPOWERED are terminal but not failures.
   - A PASS is not VALIDATED. Invariant 10 still requires forward evidence.
7. **Mandatory checks as code** (`checks.py`, run on every dry and real run):

   | code | defect it encodes | check |
   |---|---|---|
   | LA-1 | VOLEX ±20 suspension mask; VOLEX-SN `z_fwd` | prefix invariance of the signal and the universe |
   | ZV-1 | REGIME-001 zero-volume carry-forward bars | independent traded-days guard |
   | ID-1 | HYP-PM-0003 / BROKER-001 SUM(lot) identity | predictor coverage and non-degeneracy |
   | EX-1 | EXP-PM-0009/R1 exit-index defect | forward returns non-trivial; exit after entry |
   | FILL-1 | pattern-scan close fill | entry at next-session open |
   | BM-1 | IHSG benchmark bias | EW rest-of-universe benchmark; within-date placebo \|t\| < 3 |
   | SPL-1 | FORU unadjusted split | split band: an ex-ante lookback exclusion; the holding window only invalidates |

   `tests/test_rulecard_checks.py` reproduces each defect on synthetic data. Each check must fail on the defect
   and pass on the clean version.
8. **Audits by exception.** An audit document is written only when a check fails or a result looks wrong
   after the run, and it is at most one page. A new dataset gets a one-page DATA_CARD plus tests instead of an
   admission chain. The DATA_CARD spec is written when the first dataset needs it.

**Alternatives considered.**
- *Keep the chain.* Rejected: the cost per test is the binding constraint, and the chain's real value (catching
  defects) survives as code.
- *One document without code checks.* Rejected: it would have shipped every defect in the table above.
- *Card only for Tier R.* Rejected: Tier N uses the same path with the stricter hurdle, so there is one path, not
  two.

**Known gaps (recorded, not resolved).**
- Event-time rules (index ADD, event windows) need an engine v2. Only month-end characteristic sorts run today.
- The runner does not write a `research_runs` row (invariants 6/7). The panel fingerprint, git HEAD and hashes
  are in `RESULT.json`; wiring into `research/tracking.py` is a follow-up.
- Price-level filters (Rp 50) read back-adjusted prices, which embed future split information. Returns and value
  traded are unaffected.
- The MR test does not apply to flag (two-group) rules.

**First card.** `P-M/rulecards/RC-0001-MAX/` (lottery avoidance, IDX replication) is filed as a DRAFT. It cannot
be frozen until three things are done: the Step-0 external prior (JKP EM ex-Indonesia), an Owner ruling on the
power haircut (at 0.3 the card is underpowered and must not run), and an Owner ruling on the family (widen `{V1}`,
which D-053 scoped MAX out of, or open a new family).

**Receipts:**
- `research/rulecard/` (card, engine, checks, stats, evaluate, runner, data, synthetic, cli).
- Tests: `tests/test_rulecard_checks.py`, `tests/test_rulecard_engine.py`, `tests/test_rulecard_runner.py`,
  `tests/test_rc0001_max_rule.py`.
- `docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md`
- `docs/research_notes/RULE_CARD_TEMPLATE.yaml`
- `docs/research_programs/P-M/rulecards/RC-0001-MAX/{CARD.yaml,rule.py}`

---

### D-056 · First Rule Card dry run: three backfill data defects recorded and fixed; R5 power rule tightened with a measured noise floor; RC-0001-MAX closed as underpowered and not tested; data-defect correction recorded against the D-053 re-measurement input
**Status:** RECORDED · **Date:** 2026-09-24 · **Type:** Correction to D-055 + data-defect record + disposition ·
**Approval authority:** Owner instruction 2026-09-24 ("approve ketiganya", Cowork session), approving the
three proposals in `P-M/rulecards/RC-0001-MAX/DRY_FINDINGS_2026-09-24.md` §5.

**Source.** The first D-055 dry run on the Owner's machine (RC-0001-MAX, 2026-09-24 03:49 UTC) had 317
formations, 215 valid, median universe 134, and all four no-return checks passing. It also had a
scattered set of skipped months in 2011–2019 that the universe floor did not explain. The follow-up
diagnostics used the pre-2021 backfill only. No MAX value and no signal-to-return relation was computed
at any point.

**1 · Data defects in the pre-2021 backfill (recorded).**
- **ZV-2 — holiday rows.** yfinance prints IDX holidays and vendor gaps as rows for every ticker, with
  zero volume and an unchanged price: 197 of 5,332 dates. Examples: Lebaran 2017–19, 2017-06-01,
  2018-03-30, 2018-12-31, 2019-01-01, 2016-04-13..19. These rows became formation or entry sessions,
  and they emptied the traded-20 window for weeks.
- **DATA-1 — double split adjustment.** `yfinance history(auto_adjust=False)` already split-adjusts
  OHLC. The D-053 loader (`remeasure_v2.split_adjust`) applied `split_hist.pkl` a second time.
  - All 165 events with ratio ≥ 1.5 are continuous in the raw backfill.
  - The second pass created fake jumps of ratio× (HMSP 2016-06 +2,404%, ASII 2012-06 +989%).
- **DATA-2 — scale glitches.** 55 isolated bars are printed at about 1/10 or 10× their neighbours
  (MAPI and TOWR, 2018). They produced monthly "returns" of +924% and +322%.
- **Effect.** The σ of liquid-universe holding returns falls from 76.4% to 16.6% per month once
  DATA-1 and DATA-2 are corrected.

**2 · Framework fixes (under D-055, tested).**
- `engine.non_session_dates` drops a date when fewer than 50% of names traded (against the prior-60
  median) **and** fewer than 20% of prices moved. It is prefix-invariant. A real session with a volume
  hole is kept.
- `data.adjust_unadjusted_splits` adjusts a split event only when the raw prices show the jump.
- `data.drop_scale_glitches` drops a backfill bar that is more than 3× off its 5-bar median. This is
  backfill only, and every dropped bar is listed in the audit.
- Every run now reports the audit counts.
- Tests: `tests/test_rulecard_checks.py` (ZV-2) and `tests/test_rulecard_engine.py` (DATA-1, DATA-2).
  70 pass.

**3 · R5 tightened.**
- The power table uses **σ = max(literature σ, noise floor)**. The noise floor is the σ of the primary
  spread under random bucket assignment on the card's own panel. It is measured by
  `python -m research.rulecard.cli power`, which never calls the rule's `signal()`.
- `power.sigma_noise_floor` is required at freeze.
- **Reason.** A published σ comes from the paper's universe (about 40 names per decile for the IDX MAX
  paper). The liquid IDX universe gives about 12–15 names per decile.
- **First measurement** (corrected backfill, ADV ≥ Rp 1 bn): decile ≈ 6.5%/mo, quintile ≈ 4.6%/mo.
- **Consequence.** With about 245 months, 80% power at t* = 2 needs a true spread of about 1.2%/mo
  (decile) or 0.85%/mo (quintile). Lowering the liquidity floor to Rp 100 m barely helps, because the
  backfill's 772 tickers cap breadth.
- **Structural reading, recorded.** A monthly cross-sectional sort on liquid IDX detects only large
  effects. Every later card must be screened against the noise floor on paper before it is drafted.

**4 · RC-0001-MAX closed: NOT TESTED — UNDERPOWERED.**
- Planning effect 1.6 × 0.5 = 0.80 against ≈ 1.18 needed.
- The card was never frozen and never run. No outcome was computed. **No trial and no family slot were
  consumed**, so the `{V1}`/new-family question is moot.
- The card stays on file with a `disposition` block. The framework refuses to freeze a closed card.
- The disposition would reverse only if the full-panel floor came in below 4.41%/mo, which the backfill
  alone rules out in practice.
- Not a failure. It is not filed in FAILURE_REGISTRY, following the VOLEX-SN and pattern-scan
  precedent.
- One EXPERIMENT_LEDGER line is appended (`record_type: rule_card_disposition`).

**5 · Data-defect correction recorded against the D-053 re-measurement input.**
- The FWD-PM-VOLEX-SN-001 re-measurement (`remeasure_v2.py`, RESULT.json 2026-09-23) read the same
  backfill through the double-adjusting loader, without holiday or glitch handling.
- Its RESULT.json records 38 pre-2021 holdings with a > 35% session move, in 29 of the 88 gating
  months. Those months average +0.197%/mo, against +0.087%/mo for the other 59.
- **Recorded:** the input was defective (DATA-1 and ZV-2, with DATA-2 possible).
- **Not changed:**
  - the verdict (REFUSED AT G1);
  - D-053's no-re-cut rule — no re-run is authorised by this entry;
  - the frozen protocols of FWD-PM-VOLEX-001, -REGIME-002 and -FADE-001.
- The mean in the affected months was higher, so the defect did not flatter the refused result's mean.
  The FAIL is not expected to reverse, but that is **not measured**.
- **Not audited, and likely affected:** any other pre-2021 panel built with the same `split_adjust`,
  including `data_gaps/EXTENDED_PANEL_RESULT_2026-09-19.md` and the VOLEX-001 backtest expectation.
  Those records are point-in-time and are not edited. Their pre-2021 numbers should be read as
  potentially contaminated.
- One EXPERIMENT_LEDGER line is appended (`record_type: data_defect_correction`).

**Alternatives considered.**
- *Run RC-0001 anyway, at about 47% power.* Rejected. A miss could not refute the rule (EVIDENCE_MODEL
  R2), and a run would consume a trial.
- *Lower the haircut to ≥ 0.74.* Rejected. The IDX paper is a 5-year, all-stock, equal-weighted sample,
  the profile most exposed to decay.
- *Re-run the D-053 re-measurement on corrected data.* Not authorised. D-053 spent it, and this entry
  records the defect only.

**Receipts:**
- `P-M/rulecards/RC-0001-MAX/DRY_FINDINGS_2026-09-24.md`
- `P-M/rulecards/RC-0001-MAX/CARD.yaml` (`disposition` block)
- `research/rulecard/{engine,data,card,runner,cli}.py`
- `tests/test_rulecard_{checks,engine,runner}.py`, `tests/test_rc0001_max_rule.py`
- `docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md` (R5)
- `EXPERIMENT_LEDGER.jsonl`: two appended lines

---

### D-057 · Result-validity audit recorded; overlap-robust and gross observability added to FWD-PM-REGIME-002 and FWD-PM-FADE-001 (decision rules unchanged); DB split repair and SPL-1 tightening under D-055
**Status:** RECORDED · **Date:** 2026-09-24 · **Type:** Audit record + observability-only deviations +
framework fixes · **Approval authority:** Owner instruction 2026-09-24 ("approve all", Cowork session),
covering the three items put to the Owner after `AUDIT_2026-09-24_RESULT_VALIDITY.md`.

**Source.**
- `docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md`, which contains:
  - a rules check (R-1…R-14);
  - a result register covering 35 recorded results;
  - DB results (§7).
- It rests on two runs on the Owner's DB, both read-only and on the registration-era corpus
  (≤ 2026-09-16):
  - `P-M/overlap_audit/overlap_audit.py`;
  - `P-M/validity_audit/validity_audit.py` (`RESULT_20260924T063842Z.json`).

**1 · Rules found wrong (recorded; no verdict is edited).**
- **R-1.** A t clustered on entry date, with multi-session holds that overlap. Used by the REGIME-002
  reference, the FADE-001 reference, the pattern scan and the F0–F5 filter table.
  - On a simulated null it rejects 39% at a nominal 5%.
  - In-sample t-statistics shrink ×0.44–0.94 under month-cluster, Driscoll-Kraay and calendar-time
    estimators.
- **R-2.** The round trip is charged to the signal leg only, against gross benchmarks (FADE-001, pattern
  scan). A no-information pattern scores −0.60%.
- **R-3.** A holding-window contamination guard: a trade is dropped if its future window contains a
  > 35% session or a split. This is look-ahead.
  - Measured immaterial for FADE.
  - For T1 it removed 40 winners (mean excess +26%). The look-ahead biased T1 down.
- **R-10.** Power and horizons derived from R-1 standard errors.
- **R-13.** Legacy `wf_edge` walk-forward metrics are not evidence:
  - parameters are fixed;
  - the "train" window is only an indicator warm-up;
  - strategies are selected per ticker;
  - there is no inference.

**2 · Re-readings of recorded results (point-in-time records are not edited).**
- **Every FAILED / NOT CONFIRMED / REFUSED verdict stands.**
- **T1 ex-2025** (+0.93%/trade, t 2.83) is **not established in-sample**. Robust t is 1.5–1.8; without
  the look-ahead guard it is +1.06%, t 1.8–2.2.
- **FADE h20:**
  - against the EW-book, gross −0.89%, robust t −3.6 to −4.4: **survives**;
  - against IHSG, gross −0.86%: **mixed** (month −1.65, DK −1.9, calendar −3.13).
- **Pattern scan:** "every mean-reversion pattern is significantly negative" is **withdrawn as
  stated**.
  - Failed breakdown, falling wedge + break and falling wedge survive gross against the EW-book at h5
    and h20.
  - Failed breakout is null; its anti-edge was the cost.
  - Resistance breakout is significant trade-weighted only.
- **EXTENDED_PANEL 2026-09-19** (volatility and dividend "out-of-sample"): **invalid**. It was already
  superseded 2026-09-23 for look-ahead. Its pre-2021 input also carries DATA-1, ZV-2 and DATA-2.
- **DB data:**
  - no holiday rows;
  - **survivorship certain** (0 of 958 names stop trading);
  - rights/bonus ex-date drops exist but are few, and move FADE by < 0.01pp and T1 by −0.06%/trade;
  - **3 of 81 DB splits still gapped:** MLPT 2026-07-21 ×25, RAJA 2026-07-16 ×5, RMKE 2026-07-17 ×5.

**3 · Calibration of the two frozen decision rules (recorded, not changed).**
- REGIME-002 §3: P(PASS | zero effect) ≈ 13–17%. 80% power at +0.928% needs ≈ 73–103 months, against
  the 36 planned.
- FADE-001 §3: P(PROMOTE at 18 months | no information) ≈ 3–14%, against about 0.1% intended.

**4 · Observability-only deviations (Owner option (b)).**
- **Deviation entries:**
  - `P-M/forward_regime/deviation_log.md` DEV-001 (new file);
  - `P-M/forward_fade/deviation_log.md` DEV-001 (new file).
- **Report:** `P-M/forward_robust/robust_report.py` (read-only; tests
  `tests/test_forward_robust_report.py`). At every read it reports, next to the frozen statistic:
  - month-cluster t, Driscoll-Kraay t (L = maximum hold) and calendar-time t;
  - for FADE, the gross contrast.
- **Pre-declared reading:** a frozen PASS or PROMOTE that the gross calendar-time t does not confirm is
  recorded as "<verdict> under the frozen rule; not confirmed under overlap-robust inference". It has
  no automatic consequence.
- **Blind.** Both ledgers held 0 closed rows (REGIME `c06970ac…`, FADE `cb2de076…`).
- **Unchanged:** PROTOCOL.md hashes (`4063752e…`, `e1959672…`), the recorders and the decision rules.

**5 · Framework fixes under D-055 (tested).**
- **SPL-1.** The bar moves from ≤ 0.5% to ≤ 0.1% of holdings with a > 35% session, and any single
  session ≥ 100% now fails. At the old bar, DATA-1's 0.38% passed.
- **DB split repair.** `research/rulecard/data.py::repair_db_splits` runs the repository's
  gap-verified `data/adjustments.py` over DB rows. SPL-1 cannot see a forward split left unadjusted.
- **Test count:** 88 pass, including the robust-report tests.
- `RULE_FIRST_PROTOCOL_2026-09-24.md` §4: the in-house evidence paragraph is corrected.

**6 · VOLEX-001.**
- The partial-session exit hazard was already closed by **DEV-002** (2026-09-23, in
  `forward_exclusion/deviation_log.md`; the scorer waits for complete entry and exit sessions). The
  audit's §4 statement that it was open was wrong and is corrected there.
- **Still open, not decided here:**
  - hazard 2 of the 2026-09-23 suspension audit (run-time `suspension_events` leaking a few sessions
    of look-ahead into forward formations);
  - provisional bars: 814 `is_final=0` rows, 2026-09-16 → 09-24;
  - IHSG missing on 2026-08-25 and 2026-09-16.

  The remedy for the provisional bars and the IHSG gaps is `scripts/repair_provisional_bars.py --apply`.
  It writes to production.

**Alternatives considered.**
- *(a) Change nothing.* Rejected. It leaves a future PASS or PROMOTE read at its nominal error rate.
- *(c) New spec ids with robust inference.* Rejected for now. For T1 it means an honest horizon of
  about 6–9 years, which ends it as a decision test, and it would be a spec change mid-test.

**Receipts:**
- `docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md`
- `P-M/overlap_audit/{overlap_audit.py, RESULT_20260924T043858Z.json}`
- `P-M/validity_audit/{validity_audit.py, RESULT_20260924T063842Z.json}`
- `P-M/forward_robust/robust_report.py`
- `P-M/forward_regime/deviation_log.md`, `P-M/forward_fade/deviation_log.md`
- `research/rulecard/{checks,engine,data}.py`
- `tests/test_{overlap_audit,validity_audit,forward_robust_report,rulecard_checks,rulecard_engine}.py`

### D-058 · Retail universe-screen note filed; price/ADV cutoffs pre-declared for one exploratory in-sample split of the T1 reference; no protocol changed
**Status:** RECORDED · **Date:** 2026-09-25 · **Type:** Exploratory analysis pre-declaration ·
**Approval authority:** Owner instruction 2026-09-25 ("Save and test", Claude Code session).

**Source.** `P-M/universe_screen/SCREEN_HYPOTHESIS_2026-09-25.md`: a NotebookLM-derived proposal for a
structural pre-filter (board status, liquidity, price tier), with the note's own quarantine of the
foreign-participation and PDY-quality filters, plus a repository review added at filing.

**Decision.**
1. The note is filed as a **screen, not a hypothesis**. It takes no family slot and no Rule Card.
2. Cutoffs are fixed before any data is looked at: **P200** (`close >= 200`), **A5** (`adv20 >= Rp 5e9`)
   and **P200+A5**. No other cutoff will be run. `P-M/universe_screen/PREDECLARATION.md`, sha256
   `bee3bd1a9d068f27ad9c42c88bca06aad8d68a07742da413f466965442453ace`.
3. One run splits the spec-002 reference trades (data ≤ 2026-09-16) into in- vs out-of-filter.
   Inference: month-cluster and DK(L=60) t (D-057 R-1). The interpretation rules are the ones fixed in
   the pre-declaration.
4. **FWD-PM-REGIME-002 is untouched.** Its frozen universe stands whatever the split shows. Adopting a
   screen for any live or paper strategy needs a separate Owner decision.
5. **Filter 1 (board status) is not tested.** There is no point-in-time board-status or index-membership
   history in the DB, and a current snapshot would be look-ahead.

**Receipts:** `P-M/universe_screen/{SCREEN_HYPOTHESIS_2026-09-25.md, PREDECLARATION.md, screen_split.py,
RESULT_*.json}`; one `exploratory_split` line in `EXPERIMENT_LEDGER.jsonl`.

### D-059 · Trading cost by liquidity measured; T1 reference net of modeled cost is FRICTION; REGIME-002's 0.60% round trip recorded as materially understated (no protocol changed)
**Status:** RECORDED · **Date:** 2026-09-25 · **Type:** Exploratory measurement, pre-declared ·
**Approval authority:** Owner instruction 2026-09-25 ("start path 1", Claude Code session).

**Why.** D-058 found the T1 ex-2025 edge sits in adv20 < Rp 5bn names. The frozen 0.60% round trip is fees
plus a nominal slippage (PROTOCOL §2, "open ambiguity"), and no fills exist to test it.

**What was run.** `P-M/cost_liquidity/cost_by_adv.py`, once, under `PREDECLARATION.md` (sha256
`ac3a1a19c9a0f21e90b5cc3de66f5117ab435e5fad131b4324c24a6ada3f596b`). The cost model is 0.50% fees, plus the
Abdi-Ranaldo spread floored at one tick, plus 2·σ_d·√(Q/adv20). It was validated against a Roll spread on
1-minute `ticks`.

**Result.** Primary cell (ex-2025, adv20 < Rp 5bn, Rp 100m per position): **+0.11%/trade, DK t 0.13 → FRICTION.**
- Liquid names are negative at every size.
- At Rp 25m the small-cap cell is +0.94%, t 1.1.
- Roll spreads run about 36% below AR, which does not change the verdict.

**Recorded, not decided.**
1. The 0.60% endpoint in FWD-PM-REGIME-002 understates modeled all-in cost by roughly 1–3 pp per trade. A
   forward PASS under it would not imply a tradeable edge.
2. The protocol's remedy (realised fills) still governs. Whether to add a modeled-cost observability line
   to `forward_regime/deviation_log.md`, as D-057 did for robust t, is an **Owner decision**.

**Receipts:** `P-M/cost_liquidity/{PREDECLARATION.md, cost_by_adv.py, RESULT_20260925T022702Z.json, VERDICT.md}`;
`tests/test_cost_by_adv.py`; one `exploratory_split` line in `EXPERIMENT_LEDGER.jsonl`.

### D-060 · Event-time Rule Card engine adopted; RC-0002 (failed breakdown, pre-2021) closed as underpowered; modeled-cost observability added to REGIME-002 (DEV-002); HYP-PM-0008 registration refused
**Status:** RECORDED · **Date:** 2026-09-25 · **Type:** Framework extension (under D-055) + card disposition +
observability-only deviation + registration decision · **Approval authority:** Owner instruction 2026-09-25,
"complete all path with your recommendation" (Claude Code session). The Owner delegated each open
decision below to the recommendation made in that session, and every such decision is stated here.

**1 · Event-time engine (framework, under D-055).**
- `research/rulecard/events.py` adds `signal.formation: event`: 0/1 flags, next-open entry, a fixed hold of
  own sessions, and a day-weighted calendar-time estimand against the EW liquid book. Stale exits are
  flagged, not dropped. No holding-window drop (audit R-3).
- It emits the month-engine record schema, so `evaluate.py`/`checks.py` verdict logic is shared.
- `card.py` and `runner.py` branch on formation. `power` uses random events at `power.event_rate` and never
  calls `signal()`.
- Design: `docs/superpowers/specs/2026-09-25-event-time-rulecard-design.md`. Tests:
  `tests/test_rulecard_events.py` (17). The Rule Card suites are unchanged and pass.
- `framework_sha256` changes. No card was frozen, so nothing is invalidated.

**2 · RC-0002-FB-PRE2021 closed: NOT TESTED — UNDERPOWERED.**
- The rule was FADE-001's, copied. The data was the pre-2021 backfill only (the pattern was discovered on
  2021–26, and the backfill had never been read for it). Tier N, t* = 3.0, `n_trials` 18.
- Dry run: 11,790 events, 183 valid months, median book 125, all structure checks PASS.
- Power: noise floor 2.04 %/mo, which needs 0.58 %/mo for 80% power, against a planning effect of
  0.93 × 0.5 = 0.47. **Not run.**
- No trial or family slot consumed. Not a failure (RC-0001 precedent).
- The haircut was not revisited after the power result (R5). Doing so would move the goalpost.
- **Consequence:** FWD-PM-FADE-001 (forward, open since 2026-09-22) remains the only test of the
  failed-breakdown anti-edge.

**3 · DEV-002 on FWD-PM-REGIME-002 (D-059 point 2 decided: yes).**
- The report now carries a modeled-cost excess row beside the frozen statistic (`robust_report.py`).
- It was first run on a ledger holding 1 trade. That outcome was visible and is recorded in DEV-002.
- The §3 rule is unchanged, and so is the PROTOCOL.md sha256 (`4063752e…`).

**4 · HYP-PM-0008 (I1 band pinning): D-1 option (c), registration refused.**
- Its own §19/D-3 says the capturable leg is structurally absent.
- The decrees are unverified (D-2), and the board/suspension exclusion data does not exist (B4).
- No slot consumed. Any re-opening is a new Rule Card id. Disposition appended to `HYP-PM-0008_SPEC.md`.

**State after D-058…D-060 (the edge search as of 2026-09-25).**
- No tradeable long edge is established.
- T1 is friction under modeled cost (D-059).
- The surviving evidence is the in-sample, 2021–26 avoidance family (failed breakdown / falling wedge vs
  EW book) and VOLEX-001 (AT-RISK). Both are now decided only by their forward tests.

**Receipts:**
- `research/rulecard/{events.py, card.py, runner.py, synthetic.py}`
- `tests/test_rulecard_events.py`, `tests/test_forward_robust_report.py`
- `P-M/rulecards/RC-0002-FB-PRE2021/{CARD.yaml, rule.py, DRY_20260925T032651Z.json, POWER_20260925T032742Z.json}`
- `P-M/forward_regime/deviation_log.md` DEV-002
- `P-M/HYP-PM-0008_SPEC.md` disposition
- two `EXPERIMENT_LEDGER.jsonl` lines

### D-061 · Insider-event screen (SCREEN-PM-INS-001) closed: FAIL (null) on the pre-declared primary; the last unscanned in-house dataset is read
**Status:** RECORDED · **Date:** 2026-09-28 · **Type:** Exploratory screen, pre-declared ·
**Approval authority:** Owner goal 2026-09-28, "complete test for 1 until exhausted" —
recommendation 1 of the what-is-left review.

**What was run.** The `insider_transactions` dataset (98,950 rows, 2017-10 → 2026-09-24, KSEI/IDX
sourced, collected 2026-09-22/25, never previously read by this program) screened through the D-060
event-time engine under `P-M/insider_screen/PREDECLARATION.md` (sha256 `e88a9147…`, committed
`0d5f350` before any number existed). One run; 16 pre-declared cells; PIT convention: flag on the
first own session after the transaction, entry two own sessions later.

**Result.** Primary cell (E1 ≥1% accumulation, h20, ex-2025, gross): **−0.758%/mo, t −0.98, 78
valid months → FAIL (null)** at the pre-declared |t| ≥ 3.0 bar. Descriptive only: E3
director/commissioner BUYs +2.86%/mo (t 1.41, 617 events — thin); E1s ≥1% distributions −2.41%/mo,
t −2.74 at h5 ex-2025 — the avoidance direction from a new instrument, owner-gated and correlated
with {R1}/FADE-001. The RESULT's `net` columns are the engine's mirror-overlay uplift, not a
long-sleeve net — recorded as a mis-specified lens in the verdict.

**Decision.** The insider-accumulation lead is closed at screen level. No slot consumed, nothing
registered; a re-open is a new screen id. The "no tradeable long edge" record now covers every
in-house dataset; the three forward tests (REGIME-002, FADE-001, VOLEX-001) remain the only
deciders.

**Receipts:** `P-M/insider_screen/{PREDECLARATION.md, PREDECLARATION.sha256, insider_screen.py,
RESULT_20260928T035303Z.json, VERDICT.md}`; one `EXPERIMENT_LEDGER.jsonl` line.

### D-062 · Standing no-correlated-registration directive; V2 adversarial review executed (main-session fallback); program-wide deflation audit recorded — only the FADE family survives
**Status:** RECORDED · **Date:** 2026-09-28 · **Type:** Standing directive + review record +
audit record · **Approval authority:** Owner instruction 2026-09-28, "Start item 2. Complete"
(item 2 of the what-is-left review's recommendations; the recommendation's substantive content
was the wait-period governance work).

**1 · Standing directive (the recommendation as written).** No new registration correlated with
an in-flight forward test before that test's first maturity. Concretely: the MIRROR anti-edge
and falling-wedge variants (correlated with {R1}/FWD-PM-FADE-001) and any {T1}-correlated
refinement (e.g. the 002 mid-vol-band variant) stay unregistered until FADE-001's first
closures (~2026-10-19). Screens remain permitted (no slot); registrations are owner decisions.

**2 · V2 adversarial review executed.** The cold-subagent backend was unavailable
(model-not-found, twice); the 2026-09-21 owner-accepted fallback applied — main-session
execution, one pass, independence deficit recorded in the artifact. Contract honored
(read-only; all writes under /tmp; `run_formation.py` never executed; `git status` byte-identical).
Full findings: `P-M/ZCODE_REVIEW_V2_FINDINGS_2026-09-28.md`. Verdicts:
- **STANDS:** C-9 (all four fronts: hashes, +88/−0 additivity at current HEAD, added-content
  inspection, code trace incl. weekly look-ahead and exit semantics), C-6 (exact: BULL 9
  episodes/98 sessions — infeasible by 2 sessions even on a sessions reading), C-7/C-8 (within
  recorded drift; score+2 ex-2025 −4.43 exact), G-1..G-4.
- **STANDS with qualifiers:** C-1 (drifted reproduction +1.22/t 3.84 vs claimed +1.26/3.90;
  D-057's robust 1.5–1.8 remains the recorded inference).
- **NOT TESTED as-frozen:** C-2 figures, C-3, C-4, C-5 — systemic finding **F-1**: the frozen
  manifest cannot regenerate its own inputs (§6 names `t1.py`/`t2.py`, absent; the
  `f5/f20/m5/m20/bad20` forward columns have no producer; the limitation-9 execution audit was
  never staged). Restoring the lost drivers is an **owner decision**; until then the deflation
  audit below is the program-wide guard.

**3 · Program-wide deflation audit** (`AUDIT_2026-09-28_DEFLATION.md`,
`deflation_audit/RESULT_2026-09-28.json`). Census: **252 disclosed trials**. E[max |Z|] bar:
1.46 / 2.28 / 2.59 / **2.84** at N=8/50/120/252. Only the **FADE avoidance family** (h20 gross
vs EW-book 4.4; vs IHSG calendar 3.13) survives the full-census bar — and it is already owned
by FWD-PM-FADE-001. T1's raw statistics clear the bar only as the overlapping-hold estimator
D-057 re-read at 1.5–1.8 robust (dies everywhere). VOLEX (2.59) and insider E1s (2.74) die at
full census. Hansen SPA is recorded as blocked by F-1, not skipped. Practical guard going
forward: a future candidate must clear ~2.8–3.0 |Z| after its own grid joins the census.

**Receipts:** `P-M/ZCODE_REVIEW_V2_FINDINGS_2026-09-28.md`; `AUDIT_2026-09-28_DEFLATION.md`;
`deflation_audit/{deflation_audit.py, RESULT_2026-09-28.json}`; one `EXPERIMENT_LEDGER.jsonl`
line; `/tmp/frz_review/` (reviewer scratch, outside the repo).

---

### D-063 · Seven queued owner decisions resolved per the recommendation: windows not re-joined; FORU/TGUK bars settled; F-1 accepted (deflation audit is the standing guard); revocation closed as mitigated; VOLEX-SN attribution declined; BOOK_OVERLAY_POLICY evidence corrected early; TREND-003 declined, HYP-PM-0007 alias ratified, Mimosa re-audit substituted locally
**Status:** RECORDED · **Date:** 2026-09-29 · **Type:** Owner rulings (batch) · **Approval authority:**
Owner instruction 2026-09-29, "for 7 waiting decision do the recomended". Each ruling below is
Claude's recommendation adopted verbatim under that instruction; the evidence was gathered in-session.

**1 · Forward-test windows 09-07..09-28 — NOT re-joined (option a).** The falsely closed windows
(registry identity was `git HEAD`; fixed `88446f6`) are configuration-identical apart from the commit
sha, but re-joining them would be the first exception to "cohorts are never pooled" to recover about
15 of 125 sessions. The clean window starts at the 2026-09-29 deploy. The closed windows stay closed
and are never cited toward a GO/NO-GO.

**2 · FORU / TGUK provisional bars — settled.**
- **TGUK 09-16/18/21:** settled to yfinance raw values (100 / 101 / 111). No corporate action: from
  09-22 on, local and yfinance bars match exactly (121, 109, 119, 108, 98). The repair script's
  "rebase needed" came from local references on 09-15 and 09-17 being truncated intraday snapshots
  finalised by pre-fill-gate code (89 vs 91, 107 vs 110). Those two final bars are **recorded, not
  mutated**.
- **FORU 09-18/21/22:** finalised **as-is**. They are correct raw prints: 3010 and 2560 equal yfinance
  × 19.504 exactly. 176 on 09-22 is the auto-reject-upper limit from a reference of about 131
  (= 2560 / 19.5). The corporate action behind the 19.5 factor is **unconfirmed**: public sources
  report no FORU split, and the factor is non-integral. **No `corporate_actions` row is written**, so
  FORU's 09-21 → 09-22 discontinuity stands in the raw corpus. Research must exclude FORU from
  2026-09-14 onward until the action is identified; that is an open data item, not a ruling.
- Pre-write rows: `backups/ohlcv_provisional_pre_repair_2026-09-29.csv`.

**3 · F-1 — accepted; drivers not re-staged.** `t1.py`/`t2.py`, the `f5/f20/m5/m20/bad20` producer and
the limitation-9 audit script were never committed and are absent from this host. "Restoring" them
means rewriting them, and the V2 reviewer's rewrite already failed a subset check (7,523 trades at
the cutoff vs 7,287 full-sample). A rewrite would be a new artifact, not the frozen evidence.
C-2..C-5 are recorded as **NOT REPRODUCIBLE** (permanent), and D-062's deflation audit is the
standing program-wide guard. If the original drivers surface on the Dell/ZCode host, they may be
staged under a later dated entry. **New rule:** a frozen manifest's driver scripts are committed with
the manifest, or the manifest is not frozen.

**4 · Stockbit token revocation source — closed as MITIGATED, no controlled test.** No revocation
since 2026-09-22 (`logs/auto_token.log`). Re-login on 401/403 (`ad9485c`) plus the 17:30
finalisation retry made a revocation harmless, as the 09-28 fill-gate run showed. A controlled
revocation test would deliberately put an EOD run at risk for a question that no longer changes any
control. It reopens only if revocations recur.

**5 · VOLEX-SN descriptive attribution — DECLINED.** The re-measurement's own note stands: it would
mean further looks at the same data and cannot change the verdict. D-062's deflation audit already
kills VOLEX at full census (2.59 < 2.84). An attribution would add looks, not information.

**6 · BOOK_OVERLAY_POLICY — early review executed (evidence correction only; rule unchanged).** §4's
cited prior (high-vol decile −2.93%/mo vs +0.78%/mo) came from a look-ahead-filtered measurement
(D-053; AUDIT_2026-09-24 row 32, UNVERIFIED). A dated §8 entry now cites VOLEX-001's audited
pooled **+0.30%/mo (t 2.6)** as the sole basis and marks the §3 book table as an in-sample operating
figure. The rule stays **ACTIVE**: §7 ties withdrawal to VOLEX-001 failing, and it has not failed.
Withdrawing early on a weakened prior would itself be a decision taken on an interim look.

**7a · TREND-003 ("episode-onset" variant) — DECLINED.** It is {T1}-correlated, so D-062's standing
directive bars registering it before REGIME-002's first read, and D-062's deflation audit finds T1
dead everywhere at 1.5–1.8 robust. It may be re-offered only after that read, with its §6
multiplicity accounting (001/002/003 as one adaptive family).

**7b · HYP-PM-0007 alias — RATIFIED.** research.db `BROKER-001` (BFI-001, prereg sha `91c0eb9a…`,
executed 2026-09-03) **is HYP-PM-0007**, the **4th member of P-M {I5,I6,I7,I12}**. Counting an
executed, pre-registered trial is the conservative reading (rule X8, OS-10); leaving it unassigned
kept a real trial out of the family denominator. Outcome as owner-ratified 2026-09-11: primary
**INVALID · data** (identity-attenuated NV/GV); structure secondaries valid → NOT CONFIRMED. Filed as
**FAIL-PM-0007** (INVALID · data, outside F1–F9, mirroring FAIL-PM-0004-G1). research.db
`hypothesis_links` is not written from this session (research-owned table); the documentary alias is
authoritative until a research job populates it.

**7c · Mimosa re-audit — substituted locally; the Mimosa run itself stays owed on the ZCode host.**
Mimosa is not installed on this host. As the local equivalent: `tests/security/` 55/55 pass at HEAD,
and a secret-shape scan of all 121 commits since 2026-09-11 found 0 hits. The prior `scanner_enobufs`
reports were a scanner resource error on docs-only commits (PROVENANCE_BASELINE_COMMIT_2026-09-12
§A.1), not detections.

**Files changed:** this entry · `HYPOTHESIS_REGISTRY.md` (HYP-PM-0007 row + family ledger 3→4) ·
`FAILURE_REGISTRY.md` (FAIL-PM-0007 + distribution) · `EXPERIMENT_LEDGER.jsonl` (one line) ·
`BOOK_OVERLAY_POLICY.md` (§8) · `P-M/HANDOFF_2026-09-23.md` (09-29 addendum) · `ohlcv` (6 bars).

---

### D-064 · Broad edge search recorded: SCREEN-PM-CF-001 ({CF} issuance) FAIL; SCREEN-PM-LC-001 ({LC} young listings) PASS at screen level but era-concentrated — {LC} NOT opened; census bar corrected to the exact two-sided value; issuance-event adjustment added (opt-in) with a forward-window monitor
**Status:** RECORDED · **Date:** 2026-09-29 · **Type:** Screen verdicts + methodology correction +
engineering · **Approval authority:** Owner instruction 2026-09-29, "do the recommended A–D and
push", on the checker review `P-M/broad_search/CHECKER_REVIEW_2026-09-29.md`.

**A · Screen verdicts (ZCode, `9131d56` → `0029123` → `1abaa52`; checked `6b0566d`).**
- Process verified: freeze before run, hashes match, no post-freeze drift, and an independent
  re-run reproduced S2 exactly (−2.4475 %/mo, t −3.6557, 62 mo). The estimator is a calendar-time
  portfolio (non-overlapping months), and the listing proxy flags real listings.
- **SCREEN-PM-CF-001 = FAIL (null)**: primary −0.635 %/mo, t −0.56; grid max |t| 1.10; the
  discovery half has the wrong sign. The `{CF}` issuance lead closes at screen level.
- **SCREEN-PM-LC-001 = PASS (screen level)** under its frozen rule: −2.448 %/mo, t −3.66, discovery
  half same sign (−1.26, t −1.29), vs IHSG t −3.21, placebo t −0.41. Stop rule honoured. Checker
  findings, attached to the verdict:
  - **Era-concentrated.** By year vs IHSG: 2021 −10.6, 2022 −3.7, 2023 −3.1, 2024 −0.3, 2025 −2.1,
    2026 +1.2 %/mo. Dropping 2021 gives t −2.32; the last ~33 months are ≈ null. This is mostly the
    2021–23 IPO-boom unwind.
  - **{V}-independence untested**: the vol cells ran on the pooled window (disclosed deviation), with
    t ≈ −1.8.
  - **Book economics +0.15 %/mo** net.
  - **Issuance-correction defect in the screen's `wealth_correct`.** It tested materiality on the
    holder's return rather than the mechanical step, and it skipped every non-drop print, so TERP-priced
    rights and all reverse splits went uncorrected (12 applied vs 25 by the correct rule). A validity
    re-run with the correct rule (an audit, not a variant) gives **−2.456 %/mo, t −3.664**: S2 is
    unaffected, and only one young window (PDPP bonus) spans an ex-date. S1's bias ran toward its own
    hypothesis and it still returned null, so the null stands.
- **B · `{LC}` NOT opened; RC-0003 not drafted.** The pass is carried by 2021–23, book economics are
  small, and D-062 independence is unshown. A prospective no-slot recorder remains available on
  request.
- **Census:** 252 → **266** disclosed trials (14 broad-search arms; the checker's diagnostics add no
  arm).

**C · Deflation bar corrected (supersedes D-062 §3's bar values; D-062's receipt is not edited).**
`deflation_audit.py` applied the one-sided Bailey–López de Prado approximation to the two-sided
|Z|. The exact E[max|Z|] for N iid normals (`deflation_audit/bar_v2.py` →
`RESULT_2026-09-29_v2.json`) is **1.78 / 2.51 / 2.81 / 3.04 / 3.06 at N = 8 / 50 / 120 / 252 / 266**
(was 1.46 / 2.28 / 2.59 / 2.84 / 2.86).
- Re-read: FADE vs EW-book 4.4 and vs IHSG 3.13, T1-D 3.84, and S2 3.66 all still clear.
- T1's raw overlapping-hold 2.98 no longer clears full census (already dead under D-057's robust
  re-read).
- VOLEX 2.59 and insider 2.74 now fail from N = 120. **Nothing recorded as dead revives.**
- The standing guard for any future candidate is **|Z| ≥ 3.06** after its own arms join.

**D · Issuance-event adjustment + monitor.**
- `data/adjustments.py` gains `load_issuance_events()` and `correct_issuance()`. They apply a
  holder-wealth factor φ = P_ex/(m·P_ex − c) at rights/bonus/reverse-split ex-dates, gap-verified
  (the step must have φ's direction and correcting must bring it closer to zero), with a 5%
  materiality floor on the step, and volume scaled by 1/φ.
- **Opt-in**: `research.rulecard.data.load_extended_ohlcv(issuance=False)` by default, so every
  result frozen before 2026-09-29 reproduces. **New research runs set `issuance=True` and record it
  in their params.** `load_split_factors`/`adjust_ohlcv` are unchanged.
- `scripts/check_issuance_windows.py` (cron 09:45 weekdays) alerts once when a recorded
  REGIME/FADE/VOLEX **holding** window spans such an ex-date. It is detection only; the frozen
  protocols and ledgers are untouched (ZCode's proposed recorder censoring would have changed
  in-flight rules, the §3.2e prohibition).
- First run: 2 VOLEX-001 hold hits (BUVA ex 09-25, ENRG ex 10-05, both HELD). They are logged as
  **OBS-2026-09-29, no deviation**: equal-weight held vs same-universe benchmark ⇒ net ≈ 0.01%.
- ZCode's audit "zero windows" was correct at its 09-16 cutoff and did not cover the VOLEX hold.

**Files:** this entry · `P-M/broad_search/CHECKER_REVIEW_2026-09-29.md` · `deflation_audit/bar_v2.py` +
`RESULT_2026-09-29_v2.json` · `data/adjustments.py` · `research/rulecard/data.py` ·
`scripts/check_issuance_windows.py` · `deploy/crontab` · `forward_exclusion/deviation_log.md` ·
`EXPERIMENT_LEDGER.jsonl` (3 lines) · tests.

---

### D-066 · NR7_BULL retired from SHADOW after the P4 evidence-honesty corrections — every stratum negative and the former headline was not phantom-fill-inflated
**Status:** DECIDED · **Date:** 2026-10-01 · **Type:** Registry lifecycle (owner decision) ·
**Approval authority:** Owner decision 2026-10-01, ratifying the proposal
`P-M/priors/D-066_PROPOSAL_NR7_RETIRE_2026-09-30.md` (read, cited, left untouched) per the planner's
recommendation recorded in `HANDOFF_P4_2026-10-01.md` §"Owner decisions — 2026-10-01" item 2.

**A · What changed.** `registry/edge_registry.yaml` NR7_BULL v2 `status: SHADOW` → `RETIRED` with an
appended changelog sentence (the D-029 shape: status change + changelog; the entry's provenance fields
are untouched). v1 remains SUPERSEDED and byte-preserved.

**B · Evidence.** D-029 (2026-08-19) had demoted v1 for failing the Evidence Model's C3/E5+X3 capital
bar but left SHADOW as a tracking slot. P4 closed the remaining hope:
- **P4-1** (as-of-entry-date ADV gating, `fix/p4-evidence-honesty-on-p3`): the study's two local
  passes (T2 chronological retention, T3 BULL stratum) were look-ahead artifacts; corrected they flip
  PASS → FAIL (T1 +0.099% → −1.150%/trade, N 1337 → 899).
- **P4-6** (liquidity-scaled costs, layered): T1 −1.298%/trade.
- **P4-2** (ARA/ARB fillability, same branch): T1 **−1.262%**/trade (N 899 unchanged), BULL −0.390%,
  BEAR −1.549% — and, decisively, the correction is *small and slightly positive-ward* for NR7, i.e.
  the old headline was **not** propped up by unfillable phantom exits; it was already negative
  honestly. Nothing argues for restoring even shadow tracking.

**C · Engineering consequence (the D-029 lesson re-applied).** A naive status flip would have made
`registry_governance("NR7 Breakout")` return `None` (= UNREGISTERED) — the sole state where the
D-031 Option C legacy `wf_edge` fallback is licensed — re-exposing a retired strategy to live
selection, the exact hole D-029 documented and closed. Executed as the smallest safe change instead:
lifecycle-state records are now collected at load (`lifecycle` key), `registry_governance()` /
`admission_path()` return a **RETIRED** sentinel for registered-but-terminal strategies (same
T7 contract as SHADOW: exclude outright, never fall back), `engine/admission.py` maps it to a
hard non-admission, and `startup_summary()` reports "1 retired". The `("NR7_BULL", 2)` entry was
removed from `_LIFECYCLE_DEBT`: a lifecycle state is skipped before the debt check runs, so the
grandfather was unreachable dead code (removal is the allowlist's allowed shrink direction).
`tests/test_registry_lifecycle.py::test_nr7_breakout_excluded_from_live_selection_after_demotion`
(D-029's production canary) passes unchanged on the real registry against a positive legacy
`wf_edge` row — exclusion holds under RETIRED.

**D · Directed follow-ups (flagged, not actioned here).** The D-066 proposal records three
live-surface inconsistencies that now contradict a RETIRED entry and need their own pass:
`'NR7 Breakout'` still in `_REGIME_STRATEGY_MAP` (scanner dispatch) and not in `_DEFAULT_DISABLED`;
the phase5 regime-band watch job alerting via `approved_universe("NR7 Breakout")`; and the stale
"one approved edge" Telegram copy in `engine/phase5_watch.py` / `scheduler/scanner.py` comments.
The registry sentinel keeps all of them from opening anything, but the alerts and framing should be
cleaned up deliberately. `CLAUDE.md` (FROZEN) invariant #10's row naming NR7_BULL as the sole
lifecycle-debt exception is now stale — amending it is the Owner's call.

**Files:** this entry · `registry/edge_registry.yaml` · `engine/registry_loader.py` ·
`engine/admission.py` · `tests/test_registry_lifecycle.py` · proposal cited (not edited) ·
`HANDOFF_P4_2026-10-01.md` · branch `gov/d066-retire-nr7-bull`.

---

### D-065 · Gatekeeper gate config v3: Stage 9 PBO/CSCV implemented — closes a framework-vs-code gap
**Status:** RECORDED · **Date:** 2026-10-05 · **Type:** Methodology (pre-registered gate change) +
engineering · **Approval authority:** Owner instruction 2026-10-05, "fix all", on the gap list from the
literature comparison (gap 2: "PBO/CSCV stage; threshold literature default").

- **Gap found.** [[RESEARCH_VALIDATION_FRAMEWORK]] §1 states PBO via CSCV "must be applied", but
  `research/gatekeeper/stages.py` ran eight stages without it. The framework promised a check the code
  never ran (same class as the §5 corrections: a canonical claim contradicted by the repository).
- **Change.** `statistics.pbo_cscv()` (Bailey, Borwein, Lopez de Prado & Zhu 2015; deterministic,
  per-block sums over C(S,S/2) splits) and **Stage 9 `pbo`** before FT eligibility. Thresholds in the
  hashed config: `n_splits 16`, **WATCH at PBO >= 0.25, FAIL at PBO >= 0.50** (overfit more likely
  than not). `gate_config.yaml` version 2 -> **3**: a new config_hash and a new decision lineage;
  no existing gate decision is touched (append-only).
- **Posture: no matrix -> WATCH, never PASS.** CSCV needs a common-period trial matrix (e.g.
  parameter variants). The current scan family is regime cells, which trade in different months, so
  for those candidates Stage 9 returns WATCH: nothing reaches PROMOTE without the overfitting check the
  framework makes mandatory. A strategy that wants PROMOTE must supply `trial_returns` (T x N).
- **Consequence.** Under v3 a candidate identical to the v2 "clean strong" fixture is WATCHLIST unless
  it carries a trial matrix. The gatekeeper has never issued a PROMOTE, so no live promotion changes.
- **Tests.** statistics (noise -> PBO ~0.5, persistent edge -> ~0, determinism, input checks), stage
  banding incl. the no-matrix WATCH, pipeline PROMOTE-with-matrix / WATCHLIST-without; suite 3463 pass.
  Two pre-existing failures (`tests/test_routes_telegram_redaction.py`) come from the live
  `logs/TELEGRAM_OFF` kill file (commit `12e8978`), not from this change.
- **RD-4 note.** This implements the third leg of "FDR and DSR and PBO" but does not close rationale
  debt RD-4 (why the conjunction); only the original decider can.

### D-066 · P-M Price-Reversal widened {R1} -> {R1, R2}; HYP-PM-0014 registered (bank 2-ATR climax-low liquidity provision); FWD-PM-BANK-001 opened
**Status:** RECORDED · **Date:** 2026-10-05 · **Type:** Family amendment + registration + forward-test open ·
**Approval authority:** Owner, 2026-10-05, "Approve and push", on
`P-M/forward_bank/OWNER_DECISION_PACKAGE_R2_BANK_2026-10-05.md` (commit `59dd6fd`).

- **Family.** Price-Reversal widened by formal amendment (D-028 mechanism) to {R1, R2}. R2 = OHLCV-only
  short-horizon *positive* reversal after a volatility climax in mega-cap liquid names. Widened rather than
  a new family because invariant 12 scopes families by data epoch + feature space and R2 shares R1's; a new
  family would split multiplicity (PG-3/PG-6/R7.5). Registered count 1 -> 2.
- **HYP-PM-0014** frozen as `P-M/forward_bank/PROTOCOL.md` sha256 `2371cc48658f…` (recorder `c8e440c47adf…`,
  SHA256SUMS.txt). Primary BBCA 10-session net excess vs EW liquid book (0.60% RT); secondary big-4 pooled.
  GO >= +0.50% and t >= 2.0 at N >= 15 primary events or 36 months.
- **Risks accepted (stated in the package):** BBCA selected after ~120 looks; frozen pre-2021 OOS t 2.36 is
  below the program deflation bar 3.06 (D-064); OOS effect half the in-sample; primary read ~2029-2030.
- **FWD-PM-BANK-001** opened `2026-10-05T16:09:16+00:00`, cron 09:40; no back-fill (the 2026-09-24/29 firings
  are refused). The personal jurnal26 Telegram alert on the same rule is not the recorder and not evidence.

### D-067 · P-M Price-Learning {L1} family opened; HYP-PM-0015 registered (price-learning cross-sectional ranking model); G0 frozen; G1 single run approved
**Status:** RECORDED · **Date:** 2026-10-06 · **Type:** New family + registration + G0 freeze + G1 approval ·
**Approval authority:** Owner, 2026-10-06, "yes, approve G0", on `P-M/ml_rank/HANDOFF_G0.md` (branch
`research/ml-rank-2026-10` @ `f16aa9e`; PREDECLARATION.md sha256 `5d4dd3d81563…`), after planner review.

- **Family.** Price-Learning opened as {L1}: fitted models combining OHLCV/volume features (no existing family
  covers a learned combination; {T1} and {R1,R2} are fixed rules on the same data epoch). Registered count 0 -> 1.
  Multiplicity is carried at program level: the 6 grid arms (M1 ridge x3, M2 HistGBR x3; M0 is an uncounted
  baseline) enter the census at this filing, N 270 -> 276, which raises the bar for the NEXT gate, not this one.
- **HYP-PM-0015.** One G1 walk-forward run: train 2001->, validation 2016-01..2021-09 (configuration chosen on
  mean monthly rank IC), test 2021-10..latest complete month read once. PASS on test only if: net top-quintile
  excess vs the EW base book > 0 with Newey-West t (lag 3) >= 3.06 (frozen; exact E[max|Z|] @ N=266 = 3.0558);
  beats M0 paired t >= 2; PBO < 0.5; leave-one-year-out > 0; IHSG reported, not gating. If only M0 passes, M0 is
  the finding. Null handling and the failure-row text are in `P-M/ml_rank/REGISTRATION_DRAFT.md` §4.
- **Deviations acknowledged by the owner:** D-1 (beta/idiosyncratic volatility against the EW-panel market proxy,
  because no IHSG exists before 2021-07), D-2..D-5 as declared in PREDECLARATION §13.
- **Freeze condition (planner review).** PREDECLARATION.sha256 covers the predeclaration only; the driver and PIT
  tests are frozen by the commit. G1 must run from `f16aa9e` with `ml_rank_model.py` byte-identical (sha256
  `47752c25fcea…`) and record the commit and driver hash in the RESULT; any change re-opens G0.
- **Boundaries.** Research-side only; production, ~/jurnal26 and `research/broad-search-v2-zcode` untouched;
  G1 machine-gated on `ML_RANK_G1_APPROVED=1`.

### D-068 · HYP-PM-0015 G1 NULL — FAILED (F2); Price-Learning {L1} question closed
**Status:** RECORDED · **Date:** 2026-10-06 · **Type:** Result filing (predeclared null handling) ·
**Approval authority:** Owner, 2026-10-06, "yes, file it", after planner review of `P-M/ml_rank/VERDICT.md`
(commit `e3127dd`).

- **Run.** One G1 run, `run_id 167749f2791f…`, git `f4a84df`, driver sha256 `47752c25fcea…` and PREDECLARATION
  sha256 `5d4dd3d81563…` verified before and at run time (the D-067 freeze condition holds). Test 2021-10..2026-09,
  60 months, read once.
- **Result (net top-quintile excess vs the EW base book, Newey-West t lag 3; bar 3.06):** M0 +0.45%/mo t 1.20;
  M1 ridge a10 +0.20% t 0.42; M2 HistGBR d3 +0.81% t 1.71 -> condition 1 fails for all. Beats-M0: M1 t -0.59, M2
  t 0.78 -> condition 2 fails. PBO 0.51 -> condition 3 fails. Leave-one-year-out passes for M0 and M2 only. 2025
  negative for all three. Rank IC positive (t 4.4-4.8) without converting into top-quintile net excess.
- **Filing.** HYP-PM-0015 -> **FAILED (F2)**, FAILURE_REGISTRY **FAIL-PM-0015**. The "only M0 passes" clause is not
  triggered (M0 fails condition 1). Price-Learning {L1} keeps its slot count 1 (X8) and the question closes at G1;
  any new price-learning work is a new registration by formal amendment and inherits this multiplicity.
- **Disclosures accepted:** +87 final rows for 2026-10-05 between G0 and G1 (post-cutoff, cannot enter any
  feature, label or book return); one benign log-of-zero warning on suspended names (excluded by rule).
- **Reading for the program:** price/volume-only learning reproduces "low volatility + momentum" and does not
  clear the bar; the volatility-exclusion overlay (FWD-PM-VOLEX-001) remains the live price-based test.

### D-069 · Decision-number collision recorded: D-066 was assigned twice (2026-10-07)
Two different decisions were filed as D-066 on separate branches and met at the 2026-10-07
consolidation merge:
(a) **2026-10-01, NR7_BULL retired from SHADOW**: ops/hardening-2026-07-10, cited by the
CLAUDE.md invariant #10 amendment.
(b) **2026-10-05, P-M Price-Reversal widened {R1} → {R1, R2}; HYP-PM-0014 registered;
FWD-PM-BANK-001 opened**: research lineage.
Both entries stay verbatim and in place. From here on they are cited as **D-066** (a) and
**D-066-B** (b). An unqualified "D-066" in a document dated before 2026-10-07 resolves by its
subject. D-065, D-067 and D-068 are unaffected. No decision content changes. Next free number:
D-070.

### D-070 · Daily price-pattern search closed; research redirected to forced-flow, liquidity and risk-premium mechanisms (2026-10-07)

**Context.**

The census now stands at 276 trials, with a deflation bar of about 3.06. Almost every candidate
derived its signal from daily OHLCV shape. All of these came back null, an anti-edge, or an artefact:

- chart and swing patterns: double top, lower highs, staircase bottom, exhaustion, BOS / CHoCH,
  trendline breaks
- breakout and continuation families
- the sniper support-zone entry since 2021
- price-only learning: HYP-PM-0015, FAILED (D-068)
- the exit / position-management practice study: no arm recommended (2026-10-07)

Two patterns recur:
- an **era flip**, where results positive in 2001–2021 fail or reverse in 2021-10..2026
- **low power**: single-pattern event studies with a few hundred events

The only survivors so far are a risk premium (volatility exclusion, FWD-PM-VOLEX-001) and liquidity
provision (bank 2-ATR climax low, HYP-PM-0014, FWD-PM-BANK-001). Both are still in forward test, and
neither predicts a price pattern.

**Decision.**

1. **No new registration, and no new exploratory edge study, whose signal is derived from daily
   OHLCV shape.** This covers chart and swing patterns, breakouts, trendlines, candlesticks,
   indicator thresholds and price-only learning.

   The exception is a study that names a **new economic mechanism**, one that isn't price
   prediction: forced flow, liquidity provision, a risk premium, an institutional or rule
   constraint. That mechanism must be accepted in its own D-entry before G0.

   Price and volume may still be used as **controls, filters or risk measures** inside a
   mechanism-led study.
2. **HYP-PM-0016 (the sniper setup filter, briefed 2026-10-07 before this decision) is the last
   admitted price-feature study.** It is allowed because it filters an existing owner entry rule
   and its pre-registered baseline is a risk measure (low volatility). It counts in {L1} as briefed.
3. **Running forward tests continue unchanged:** VOLEX-001, BANK-001, FADE-001 and REGIME-002. No
   rule changes mid-test (Research Master Plan §3.2e).
4. **Next research direction:** structural events with a forced-flow or rule mechanism. In order:
   - tender offers
   - index reconstitution (IDX80, LQ45 / IDX30 if the history can be sourced)
   - rights issues, if not already covered by {CF} (D-064)
   - dividend ex-dates
   - splits, bonus and reverse splits

   Each starts with a **feasibility gate** (counts, point-in-time dates, power from pre-event
   volatility only, no event outcomes read) before any registration.
5. **Preference for pooled cross-sectional designs** where the mechanism allows them, over
   single-pattern event studies (power).
6. **Owner chart questions** (e.g. "analyze MAPI") may still be answered descriptively. They are not
   edge research and are not tested as such unless a mechanism under (1) is named.

**Multiplicity.**
- Nothing is removed from the census, and no family is narrowed (D-028).
- Price-pattern families stay counted forever (X8).
- This closes the search; it doesn't erase it.

**Amendment.** Only by a superseding D-entry.

### D-071 · Research census ratified at N = 595 under the stricter count; deflation bar ≈ 3.29 for new gates (2026-10-08)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Governance (multiplicity census) ·
**Approval authority:** Owner, 2026-10-07, "use 3.28 as primary bar" (the stricter recount
governs) and "sniper 3.29"; filed on "file both" 2026-10-08. Draft:
`DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md` (`2937488`, edited `5f8798a`).

**Context.**

- **Two counts in circulation.** The recorded census was **276**: D-064's 266, plus XP-001's 4
  arms, plus HYP-PM-0015's 6 configurations (D-067). Its bar is ≈ 3.07.
- **The recount.** The 2026-10-05 broad-search-v2 recount (`origin/research/broad-search-v2-zcode`,
  `P-M/broad_search_v2/recount/RECOUNT_W0_2026-10-05.md` and `CENSUS_NOTE.md`) counted studies the
  recorded census never included: 245 script-countable trials from the 2026-09-24/25 chart-pattern
  studies (13 artifacts in `Claude outputs/`, checksummed in place); the double-top study at its
  upper bound, +20; a +20 placeholder for the gap-market microstructure battery (no surviving
  scripts); X1's 6 arms. That gave N = 561, bar 3.2745, never ratified.
- **The recount missed three items:** HYP-PM-0015's 6 configurations (it started from 270, not
  276); the 2026-10-06 BOS / trendline-break study, 8 tests (`Claude outputs/bos_study_2026-10-06/
  bos_study.py`); the 2026-10-07 exit / position-management study, 10 non-baseline arms × 2 entry
  populations = **20** at the upper bound (10 if the random-entry control counted 0; the upper
  bound is taken per REVIEW_R1 §1, where over-counting only raises the bar).
- Descriptive statistics count 0 (no trading-rule return statistic): the owner's chart questions
  and the 2026-10-07 opening-minutes volatility profile.

**Decision.**

1. **The census is ratified at N = 595:**

   | Component | Trials |
   |---|---|
   | Recorded at D-064 / XP-001 | 270 |
   | 2026-09-24/25 pattern studies | 245 |
   | Double-top study (upper bound) | 20 |
   | Gap-battery placeholder | 20 |
   | X1 | 6 |
   | HYP-PM-0015 | 6 |
   | BOS / trendline-break | 8 |
   | Exit study (upper bound) | 20 |
   | **Total** | **595** |

   This supersedes the 276 count for every gate from this date. The bar is the exact two-sided
   E[max|Z|] (`deflation_audit/bar_v2.py`): **3.2912 at N = 595**.
2. **Each new gate freezes its bar at the census + its own configurations**, computed exactly at
   G0. HYP-PM-0016's 4 configurations gave N = 599, bar **3.2931** (D-072); the census after D-072
   is **599**. Bars computed under the 276 count (≈ 3.07) may be reported as a secondary line only,
   and no configuration passes on them.
3. **Nothing recorded as dead revives** (the bar only rose). The survivor re-reads of RECOUNT_W0 §4
   stand: FADE avoidance vs the EW book (|Z| 4.4) clears; T1-D (3.84) and S2 / {LC} (3.66) clear,
   with S2 era-concentrated and {LC} unopened per D-064 §B. **FADE avoidance vs the IHSG calendar
   (3.13) no longer clears.** FWD-PM-FADE-001 continues unchanged (Research Master Plan §3.2e) and
   is judged on its own frozen protocol, not on this bar.
4. **The two placeholder lines** (double top at its upper bound, gap-battery +20) stay until their
   trials are reconstructed from session records. Reconstruction may only replace a placeholder
   with an exact count at or above its value; a lower count needs its own superseding entry with
   evidence.
5. **Exploratory studies count from now on.** An exploratory study with a reported return
   statistic enters the census when it is run, registered or not: filed in `CENSUS_UPDATE.md`, with
   its script committed or checksummed, in the same session. This closes the F-1 gap that left 300+
   trials uncounted.

**Owner choice recorded:** the exit study is counted at its upper bound, 20 (the draft default;
counting 10 would give N = 585, bar 3.286, a negligible difference).

**Multiplicity.** No family is narrowed (D-028). Hypotheses keep their family counts (X8). This
entry only raises the program-wide census, which is append-only and monotonic. No wall-clock decay
(invariant 12).

**Amendment.** Only by a superseding D-entry.

### D-072 · HYP-PM-0016 (sniper setup filter) registered in {L1}, G0 frozen, G1 NULL — FAILED (F2)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Registration + G0 freeze + result filing
(predeclared null handling) · **Approval authority:** Owner, 2026-10-07: "yes, do both" (brief
`ZCODE_BRIEF_SNIPER_FILTER_2026-10-07.md` as overridden by `ZCODE_NEXT_TASKS_2026-10-07.md`
`7ccb15d`); pre-approval Revisions 1 and 2 (`3f2da64`, `5f8798a`); "sniper 3.29"; G1 approval of
Revision 2; filed on "file both" 2026-10-08. Branch `research/sniper-filter-2026-10`.

- **Why admitted.** D-070 §2 names HYP-PM-0016 as the last admitted price-feature study: it filters
  an existing owner entry rule (meta-labelling; the entry stays) and its pre-registered baseline is
  a risk measure (low volatility).
- **Family.** Price-Learning **{L1}** (D-067), slot **2**; inherits {L1}'s multiplicity. Census
  595 + 4 configurations = **599**; frozen primary bar **3.2931** (exact E[max|Z|]); 3.0713 at the
  old 280 count reported as a secondary line only.
- **Study (frozen).** One G1 walk-forward on the exit study's filled E-SN sniper setups (3,682;
  outcome = the frozen X1 net R): 10 setup-day features, each ranked over the trailing 250 sessions
  of strictly-earlier, already-filled setups; M0 = low Parkinson-60 + 126-session momentum rank
  mean; M1 = L2 logistic (C ∈ {0.1, 10}, chosen on validation); M2 = shallow HistGBR; selection =
  top 40% of scores. Train 2001–2015-12, validation 2016-01..2021-09, test 2021-10.. read once.
  Pass: NW t ≥ 3.2931 on the selected-minus-all monthly R difference, selected mean R > 0, both
  halves > 0, M1/M2 beat M0 at paired t ≥ 2, PBO < 0.5.
- **Freeze.** G0 `72b4bd5`, Revision 1 `b3dd0bc`, Revision 2 `d261260` (disclosed pre-approval
  revisions, no outcome read). PREDECLARATION sha256 `aa68e12e…`; sidecar verified at run time;
  snapshot sha256 `c42c151e…`, dataset fingerprint `f42275e3…` (zero drift) checked before any
  outcome.
- **Result** (`RESULT_20261007T090305Z.json`, commit `b9e5e5b`, single run). Test n = 1,429,
  all-setups mean −0.043R. No configuration passes: best NW t +0.23 (M2) vs 3.2931; selected mean R
  negative everywhere (M1b −0.010R, M2 −0.029R, M0 −0.124R, the worst); first half negative for
  all. M1b/M2 beat M0 (paired t 2.43 / 2.12). PBO 0.461.
- **Filing.** HYP-PM-0016 → **FAILED (F2)**, FAILURE_REGISTRY **FAIL-PM-0016**. No forward test is
  built (predeclaration §8 applies only if a model passes). {L1} slot count 2 (X8). With this
  entry the daily price-feature search is closed in full (D-070).
- **Reading for the program:** filtering the owner's sniper entry by price/volume features does not
  produce profitable trades in 2021-10..2026-09; the HYP-PM-0015 low-vol + momentum lesson does not
  transfer to this entry (it selected the worst setups).

**Amendment.** Only by a superseding D-entry.

---

### D-073 · Mechanism accepted: dividend clientele flow (pre-cum demand D1, ex-day tax clientele D2); first {SE} G0 (2026-10-08)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Mechanism acceptance (D-070 §1). No
registration and no G0 yet. · **Approval authority:** Owner, 2026-10-08: "D first", "2%" (draft
`DECISION_DRAFT_MECHANISMS_A_D_2026-10-08.md` @ `468fe8c`). Sources: Task 2 feasibility
(`research/structural-events-feasibility-2026-10` @ `1c20f56`) and Task 3
(`research/mechanism-inventory-b-2026-10` @ `571dee3`). The planner's pre-event facts used
**pre-event data only**; no post-event price was read.

- **Mechanism.** A cash dividend is a scheduled event, and the right to it is fixed at the cum date.
  Two flows follow.
  - **(i) Pre-cum demand.** Yield and dividend-capture buyers concentrate their purchases before the
    cum date. This is price pressure from demand, not news (the dividend-month premium, Hartzmark &
    Solomon 2013).
  - **(ii) Ex-day tax clientele.** Holders are taxed differently on dividends:
    - non-residents: 20% withholding, or the treaty rate
    - resident individuals: 10% final, or exempt if reinvested under the 2021 rules
    - resident corporates: their own rules

    Capital gains are taxed at 0.1% of sale proceeds. So the marginal holder values one rupiah of
    dividend at less than one rupiah of price, and the ex-date drop should be smaller than the
    dividend.
- **Predictions (directions declared).**
  - **D1:** excess return vs the EW liquid book over the 10 sessions ending at the cum-date close
    is > 0.
  - **D2:** capture return is > 0.
    - Formula: (P_ex open + 0.9 × dividend − P_cum close) / P_cum close − 0.60% round trip, minus
      the EW book's return from the cum close to the ex open.
    - Population: yield ≥ **2%** at the close before the cum date (owner, 2026-10-08).
- **Pre-event facts (planner).**
  - 576 liquid events (ADV20 ≥ Rp 10bn, IDR dividend > 0, 20 pre-bars). Task 2 counted 574.
  - Yield p10/p25/p50/p75/p90: 0.45 / 1.17 / 2.52 / 5.02 / 8.5%. 333 events have yield ≥ 2%.
  - 60% of cum dates fall in May–July.
  - 560 of 574 events are in 2021-10 or later.
  - Power (pre-event σ 2.36%/day):
    - D1: MDE ≈ 0.95% treating events as independent, 1.63% clustered by month.
    - D2: MDE ≈ 0.43% independent, about 0.7% clustered.
- **Decision.**
  1. Mechanism accepted as forced flow / clientele under D-070 §1. **Its G0 is the first in {SE}.**
  2. **Design limits for the G0** (the G0 freezes the details):
     - **Arms:** exactly two tested arms, D1 and D2. No horizon grid and no yield grid.
     - **Population:**
       - IDR cash dividends with `dividend_value` > 0 and stored cum and ex dates.
       - Several dividends on one cum date are summed.
       - ADV20 ≥ Rp 10bn on the session before the cum date.
       - Events with a split, bonus, reverse split or rights ex-date inside the window are excluded.
     - **PIT anchor for D1 (required).**
       - D1 entry = the later of cum−10 and the first session after a point-in-time announcement
         anchor.
       - The anchor is the approving AGM (`rups` event).
       - `dividend_created` may be the anchor only if it falls before the cum date and isn't a
         backfill artefact. The G0 must show both.
       - Events with no anchor are dropped from D1 but stay in D2.
     - **Benchmark:** a total-return EW liquid book, with dividends added back on each ex-date.
       5001's bars are raw, so a price-only book would count other stocks' ex-day drops as negative
       returns.
     - **Inference:**
       - clustering by event month and by repeat ticker
       - both halves (2009 → 2023-12 and 2024-01 →) must be > 0
       - required control: a Parkinson-60-decile-matched book, to guard against overlap with VOLEX
         {V} (D-062)
     - **Report:** by month (AGM season vs the rest), by yield tercile, and by a PIT
       foreign-ownership proxy if one exists. If none exists, the report says so.
  3. The D-064 ex-date monitor (detection only) continues unchanged.
  4. **Honest prior:**
     - D1 is likely null: it is underpowered for an effect the size the literature reports.
     - D2 is the real test of the clientele claim. A positive result may still fall inside the cost
       on mid-yield names.
     - Neither arm becomes a trading rule before a forward test.
- **Falsification.** Either of these:
  - the D1 or D2 pooled mean is ≤ 0, below the frozen bar, or flips sign across the halves
  - D2 is positive only gross of the 10% tax, or only in the top yield tercile
- **Multiplicity.** New family **{SE} Structural-event forced flow**, opened at the first G0
  registration (D-028, PG-3). Registration HYP-PM-0017. Census 599 + 2 = **601**, bar **3.2940**,
  recomputed exactly at G0 (D-071 §2).

**Amendment.** Only by a superseding D-entry.

---

### D-074 · Mechanism accepted: tender-offer price floor (arbitrage spread to a contractual price with a deadline); G1 under a stop rule, forward recorder (2026-10-08)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Mechanism acceptance (D-070 §1). No
registration and no G0 yet. · **Approval authority:** Owner, 2026-10-08: "G1 + stop rule"; G0 after
D-073's (draft @ `468fe8c`).

- **Mechanism.** A tender offer is a public, contractual commitment to buy at a fixed price until
  `tender_end`, with payment on `tender_paydate`. While the offer is open it sets a floor under the
  price. A market price below the offer is an arbitrage spread, bounded by deal risk and the time to
  payment. It is not a prediction. Mandatory offers (POJK 9/POJK.04/2018) are rarely withdrawn. The
  spread pays for:
  - time value
  - settlement and acceptance friction for retail holders
  - proration risk on partial voluntary offers
- **Prediction (direction declared).** For offers priced above the market at entry, the price
  converges towards the offer by `tender_end`, and the mean net return is > 0.
- **Pre-event facts (planner).**
  - 165 events. 129 have 20 pre-bars.
  - **67 of 129 offers are priced below the market**, so they have no spread and are ineligible.
  - Eligible events (spread ≥ 0.6% at the close before `tender_start`):
    - 8 at ADV20 ≥ Rp 10bn (median spread 7.4%)
    - **26** at ≥ Rp 1bn (median 3.6%)
    - 61 with no liquidity floor (median 5.0%)
  - Eligible events run 2021 → 2026. The median window is 22 sessions (range 4–25).
  - MDE ≈ 7.5% under the feasibility convention (σ 2.42%/day, n = 26). That convention is
    pessimistic for a price pinned under an offer.
- **Decision.**
  1. Mechanism accepted as a rule-constraint forced-flow mechanism under D-070 §1.
  2. **Design limits for the G0** (filed after D-073's G0):
     - **Population:**
       - a stored `tender_price`, `tender_start` and `tender_end`
       - ADV20 ≥ Rp 1bn on the session before `tender_start`
       - spread at that close ≥ the 0.60% round trip plus the D-059 modelled cost for the name's ADV
     - **Entry:** that close.
     - **One tested arm:**
       - Market exit at the `tender_end` close, net of the modelled cost.
       - Test: pooled mean with month-clustered t, plus > 0 excess vs the EW liquid book.
       - Report only: acceptance at the offer price, paid on `tender_paydate` with no proration.
         This is the upper bound and is not tested.
     - **Stop rule (owner):** if the frozen population has fewer than **20** eligible events, there
       is no G1 and a descriptive spread ledger is filed instead. If stopped, the arm still counts
       in the census from registration (X8).
     - **Report:** mandatory vs voluntary offers, and full vs partial (`tender_percentage`).
  3. **Forward recorder** (no hypothesis and no census arm). Every new offer is logged at
     `tender_start` with its spread, and at `tender_end` with its convergence. The first case is
     DOOH: offer 148, window 2026-10-05 → 11-03.
  4. **Honest prior:** at n ≈ 26, expect a small positive mean below the bar, or a stop. The
     recorder is the durable output.
- **Falsification.** Either of these:
  - the pooled net market-exit return is ≤ 0 or below the frozen bar
  - losses concentrate in withdrawn or prorated deals that the rule can't exclude in advance
- **Multiplicity.** Family {SE}, 1 tested arm. Registration HYP-PM-0018. Census 601 + 1 = **602**,
  bar **3.2945**, recomputed exactly at G0.

**Amendment.** Only by a superseding D-entry.

---

### D-075 · Mechanism accepted: market-stress reversal (liquidity provision to forced sellers); one beta-adjusted arm; census ledger 601 (2026-10-08)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Mechanism acceptance (D-070 §1) plus a census
note. No registration and no G0 yet. · **Approval authority:** Owner, 2026-10-08: "go with
recommendations, file it" (draft `DECISION_DRAFT_MECHANISM_MARKET_STRESS_REVERSAL_2026-10-08.md` @
`8de96d9`). The planner's pre-event facts used **pre-event data only**; no return after any stress day's
close was computed.

- **Why.**
  - Price-only reversal on IDX is exhausted and negative: S1-PM-0006, the 2026-09-17 pattern scan
    (HYP-PM-0012), the exhaustion and confirmed-bottom grids, the chart-bottom studies, the factor-zoo
    short-horizon reversal, HYP-PM-0001 and HYP-PA-0001.
  - The literature places reversal profit in liquidity provision to forced sellers, largest when liquidity
    is scarce (Nagel 2012, RFS). The surviving IDX reversal (HYP-PM-0014, big-4 bank 2-ATR climax low) fits
    that reading.
  - This entry admits a direct test on market-wide stress days.
- **Mechanism.** On market-wide stress days, selling is driven by balance sheets more than by news: margin
  calls and deleveraging, stop-outs, foreign outflows, redemptions.
  - IDX concentrates this: heavy retail margin, ARB limits that spread the selling over sessions, and short
    selling that is barely available.
  - The stocks that fell most fell partly for reasons unrelated to value. Liquidity supplied that day earns a
    premium, which shows as a partial reversal.
  - Conditioning on market stress selects the days when large falls are forced. Most large falls are not
    forced, which is why price-only reversal fails.
- **Prediction (direction declared).** On a stress day t, the liquid names with the largest day-t falls
  outperform over the next 5 sessions, beta-adjusted and net of cost.
- **Pre-event facts (planner).**
  - **Stress day:** the EW liquid return (ADV20 ≥ Rp 10bn, known on t−1) is ≤ **−2.5 ×** its trailing
    250-session standard deviation (known before t).
  - **Counts:**
    - long panel `data/history_long.db` (at least 30 liquid names from 2005-01-31): **105 days / 63
      episodes**, 2007 → 2026, spread across years
    - 5001 panel 2021-07+: 32 days / 21 episodes
    - A fixed −2.5% threshold is regime-biased: 30 of its 47 days since 2021 fall in 2026.
  - **Universe:** liquid names per day, median 137 (5001 panel) and 70 (long panel). The bottom-quintile
    basket is about 14–27 names.
  - **Power:** MDE ≈ 0.8–1.3% over 5 sessions at n = 63 (planner approximation; the G0 recomputes it from
    pre-event dispersion).
- **Decision.**
  1. **Mechanism accepted** as liquidity provision under forced selling (D-070 §1).
  2. **Design limits for the G0** (the G0 freezes the details):
     - **Event:** the first stress day of each episode. A new episode needs more than 5 sessions without a
       stress day. The threshold is **−2.5σ, fixed now** (owner).
     - **One tested arm, S1 (owner: S1 only):**
       - Basket: an equal-weight portfolio of the liquid names in the bottom quintile of day-t return.
         Exclude zero-volume ARB names.
       - Entry: the close of t. Exit: the close of t+5.
       - Outcome: basket − β × EW liquid market (β = trailing-250, known before t), net of the D-059
         modelled cost per name.
     - **Report only (not tested):** the market-level rebound (S2); later-in-episode stress days; horizons 1,
       10 and 20.
     - **Entry-timing check (required):** the 15:49 pre-close agreement rate from 2025+ minute bars, which is
       a pre-event fact. S1 must also be > 0 with entry at the close of t+1.
     - **Inference:** one observation per episode. Halves E1 2007 → 2020 (long panel) and E2 2021-07 →
       (5001 panel) must both be > 0.
     - **Required controls:** a Parkinson-60-decile-matched book (VOLEX {V}, D-062); excluding the big-4 banks
       (HYP-PM-0014); excluding names with an ex-date inside the window.
     - **The G0 must disclose:**
       - `history_long` provenance, adjustment and survivorship
       - the nominal ADV floor across 2007–2026
       - the panel's earlier VOLEX out-of-sample use, which asked a different question
  3. **Honest prior:** NULL is likely if IDX stress selling continues for days, which ARB makes plausible. A
     pass in E1 only reads as decayed.
- **Falsification.** Any one of these:
  - the S1 beta-adjusted net mean is ≤ 0 or below the frozen bar
  - a sign flip across the halves
  - positive only at close-t entry
  - explained by the Parkinson-matched control
- **Family (owner).** **Price-Reversal {R1, R2} → {R1, R2, R3}**, widened by formal amendment at the G0
  registration (D-028, PG-3/PG-6). The feature space is still a price reversal, with HYP-PM-0014 as its
  closest relative. A new family was declined because it would escape the reversal family's count. Order:
  G0 after D-073's (owner).
- **Census note.**
  - The census ledger stands at **601**: D-071/D-072's 599 plus two exploratory arms run 2026-10-08, the A/D
    "trap" check and the volume-profile swing check, both null.
  - Consequences:
    - D-073's G0 freezes at **603** (bar 3.2950), not 601.
    - D-074's at 604 (3.2954).
    - This arm at 605 (about 3.2959) if its G0 is third.
  - All are recomputed exactly at each G0 (D-071 §2).
  - The 2026-10-08 audit of production screens against the market is **not** counted as an arm: it
    evaluated existing outputs and selected nothing.

**Amendment.** Only by a superseding D-entry.

### D-076 · HYP-PM-0017 (dividend clientele) registered in {SE}, G0 frozen at N=607; census ledger 605 (supersedes D-075's census note)
**Status:** RECORDED · **Date:** 2026-10-08 · **Type:** Registration + G0 freeze + census correction ·
**Approval authority:** Owner, 2026-10-08: "approve D-073". The G0 is branch
`research/dividend-clientele-2026-10` @ `0309cc6`, which re-freezes the first G0 `97eeb9b`.

- **Why admitted.** D-073 accepted the dividend-clientele mechanism (D-070 §1). This is the first
  registration in {SE}.
- **Family.** **{SE} Structural-event forced flow**, a new family opened at this registration (D-028,
  PG-3), slot **1**. Its scope is contractual or calendar corporate events that force or attract flow:
  dividends (D-073), tender offers (D-074), and later index and lock-up events, if admitted. It is
  denominated separately from the price families. Its multiplicity is carried at program level in the
  census, so the separate family loosens no bar. It may be widened by formal amendment, never narrowed
  or split.
- **Census (supersedes D-075's census note).** The ledger is **605**:
  - 599 after D-071/D-072
  - + 2 exploratory arms on 2026-10-08: the A/D "trap" check and the volume-profile swing check
  - + 4 exploratory arms on 2026-10-08: the NR7 post-mortem's winner-vs-loser entry-time comparisons
    (gap, stop distance in ATR, planned R:R and ADV, each checked across halves with a permutation
    test; all inconsistent, permutation p 0.26–1.00)

  This registration adds **2** arms, making **607**. The frozen primary bar is **3.2968** (exact
  `e_max_abs_z(607)` = 3.296828). The first G0 froze at 603 (3.2950) under D-075's count. It was
  re-frozen before approval; no outcome was read, and only N and the bar changed.
  - Consequences: the D-075 G0 freezes at **608** (3.2973), or **609** (3.2978) if D-074's G0 registers
    first. D-074's G0 would be 608 if it came first. All are recomputed exactly at each G0 (D-071 §2).
- **Study (frozen).** PREDECLARATION sha256 `50c91491…` (the sidecar covers the predeclaration, drivers,
  synthetic fixture and PIT tests).
  - **D1, pre-cum demand:** n = 547. The window starts at the anchor and ends at cum; it runs 3–10
    sessions, with a median of 5. The anchor is the earlier of:
    - the latest `rups_date` 1–90 calendar days before cum
    - a non-artefact `dividend_created`, where an artefact is a `created` on or after the ex-date, or a
      `created` date shared by more than 50 rows
  - **D2, ex-day capture:** events with yield ≥ 2%, n = 324; tercile edges 3.48% / 6.23%.
  - **Benchmark:** outcomes are measured against the total-return EW liquid book, net of the 0.60%
    round trip. A Parkinson-60-decile-matched book is the control.
  - **Primary t:** min(month-mean t, two-way cluster t).
  - **Halves:** cum ≤ 2023-12-31 and cum ≥ 2024-01-01; both must be > 0.
  - **D2** must also pass at the 0.9 tax factor, and not in the top tercile alone.
  - **Era:** the 5001 panel starts 2021-07-05, so the study is effectively 2021-07+. 562 liquid events;
    2,603 earlier events can't map to a session.
  - **Power:** the minimum detectable effect is 2.59% for D1 (a null is likely, as predeclared) and
    0.17% for D2.
- **Data.** The walkforward snapshot sha256 is `a2d7e675…`, with its dataset fingerprint in
  `CENSUS_G0.json`. G1 verifies both before reading any outcome.
- **G1.** One run with `DIVIDEND_G1_APPROVED=1`, then RESULT, VERDICT and HANDOFF, then STOP. A null is a
  useful, predeclared outcome (D-073's honest prior).
- **Forward test.** Only if an arm passes: new liquid dividends after the G1 date, under the frozen rules,
  recorded at cum and ex. The host would be the D-064 ex-date monitor lineage, gated by the owner.

**Amendment.** Only by a superseding D-entry.


### D-077 · HYP-PM-0017 (dividend clientele) G1 NULL — FAILED (F2); {SE} slot 1 consumed
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Result filing (predeclared null handling) ·
**Approval authority:** Owner, 2026-10-09: "file it". G1 approved under D-076; run on branch
`research/dividend-clientele-2026-10`, result commit `89c3af9`.

- **Run.** One frozen run (`RESULT_20261008T085015Z.json`) at N = 607, bar **3.2968**. Snapshot
  `a2d7e675…` and fingerprint `9c26e0df…` were verified before any outcome. The populations match the G0
  census (D1 547, D2 324).
- **D1, pre-cum run-up: FAIL on every condition.**
  - Mean **−0.51%**, primary t −1.90 (month t −0.93), win rate 42%.
  - Halves −0.32% (2021-07..2023) and −0.65% (2024→). Parkinson control −0.44%.
  - There is no pre-cum run-up in liquid IDX dividends 2021-07..2026-09.
- **D2, ex-day capture (yield ≥ 2%): FAIL on strength and halves; the controls pass.**
  - Net mean **+1.33%** at the 0.9 tax factor (gross +2.00%), primary t +1.81 (month t +2.02), against
    the bar of 3.2968.
  - Halves **+3.67% → −0.19%**, a sign flip.
  - By year: 2021 +10.3%, 2022 +1.9%, 2023 +4.7%, 2024 +0.4%, 2025 −0.6%, 2026 −0.3%.
  - The ex-drop median is 0.69 of the dividend, so the clientele direction is real but has decayed to
    about zero after tax and cost.
  - Terciles: +0.09% / +0.33% / +3.57%.
- **Filing.**
  - HYP-PM-0017 → **FAILED (F2)**; FAILURE_REGISTRY **FAIL-PM-0017**. The classification is F2, not F9:
    the registered prediction failed at its own pooled gate, and the decay is the reading.
  - No forward test (PREDECLARATION §8). The D-064 ex-date monitor stays detection-only.
  - {SE} keeps the slot (X8). The census already counted both arms (ledger 607).
- **Reading for the program.** D-073's honest prior held: D1 was null, and D2 was the real test. D2 is
  another IDX effect that was large in 2021–23 and gone by 2024–26, the same decay pattern as VOLEX
  and NR7. D-074 (tender offers) is not affected; it stays NOT NOW unless the owner reorders.

**Amendment.** Only by a superseding D-entry.

### D-078 · HYP-PM-0019 (market-stress reversal) registered; Price-Reversal widened to {R1, R2, R3}; G0 frozen at N=608
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Registration + family widening (D-028, PG-3/PG-6)
+ G0 freeze · **Approval authority:** Owner, 2026-10-09: "approve stress". The G0 is branch
`research/market-stress-reversal-2026-10` @ `fa78700`, which re-freezes the first G0 `843e562`.

- **Why admitted.** D-075 accepted the liquidity-provision mechanism (D-070 §1) and ordered this G0
  after D-073's. D-073's G0 was approved (D-076) and run (D-077).
- **Family.** **Price-Reversal {R1, R2} → {R1, R2, R3}**, widened by formal amendment. R3 is market-stress
  liquidity provision: the first −2.5σ day of an episode in the EW liquid market, with the losers' basket
  bought at the close. HYP-PM-0019 takes slot **3** and inherits the family's multiplicity. The family
  may be widened, never narrowed or split.
- **Census.** The ledger stands at 607: 605 (D-076) plus HYP-PM-0017's 2 arms. This arm makes it
  **608**. The frozen primary bar is **3.2973** (exact `e_max_abs_z(608)` = 3.297294). D-074 is not
  registered, so the contingency at 609 does not apply.
- **Study (frozen).** PREDECLARATION sha256 `23979b75…`; the sidecar covers the predeclaration, drivers,
  synthetic fixture and PIT tests.
  - **Arm S1:** the liquid names in the bottom quintile of day-t return (ADV20 ≥ Rp 10bn in true rupiah,
    known by t−1; zero-volume ARB names excluded).
  - **Outcome:** close t → close t+5, total return, minus β (trailing-250) × the EW liquid market, net of
    the D-059 modelled cost.
  - **Inference:** one observation per episode, t = mean / sd × √n.
  - **Pass:** mean > 0 and t ≥ 3.2973. Also both halves > 0 (E1 2007–2020, n 46; E2 2021-07→, n 17),
    entry at the close of t+1 > 0, and the Parkinson-60-decile-matched excess > 0.
  - **Controls (reported):** excluding the big-4 banks; excluding names with an ex-date in the window.
- **Data.**
  - The E1 panel is `history_long` (built from yfinance; `adj_close` ≡ `close`, so dividends are added
    back from `corporate_action_events`). The E2 panel is 5001 `ohlcv`.
  - On their overlap the two panels' stress flags disagree on 6.9% of flagged days, inside the 20% limit.
  - The 15:49 pre-close flag agrees with the close flag on 5 of 7 days in 2025+; both misses are
    borderline days.
  - The snapshots and fingerprint are pinned at G0, and G1 verifies them before any outcome.
- **Power.** The minimum detectable effect is about 1.4% at n = 63. Honest prior (D-075): a NULL is
  likely, and a pass in E1 only would read as decayed.
- **G1.** One run with `STRESS_G1_APPROVED=1`, then RESULT, VERDICT and HANDOFF, then STOP.
- **Forward test.** Only if S1 passes: every new first-day stress episode after the G1 date, recorded at
  t and t+5, about 3–6 a year. A verdict would take years.

**Amendment.** Only by a superseding D-entry.

### D-079 · HYP-PM-0019 (market-stress reversal) G1 NULL — FAILED (F2); Price-Reversal slot 3 consumed
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Result filing · **Approval authority:** Owner,
2026-10-09: "file it". G1 approved under D-078; run on branch `research/market-stress-reversal-2026-10`,
result commit `82e8afa`.

- **Run.** One frozen run (`RESULT_20261009T020022Z.json`, runtime 11 min) at N = 608, bar **3.2973**.
  Before any outcome, ZCode verified the sidecar (`23979b75…`), both snapshots (`a2d7e675…`,
  `7d298068…`) and the fingerprint (`9c26e0df…`).
- **Result: falsified on the primary clause; every secondary condition is negative.**

  | Measure | Result |
  |---|---|
  | S1, n 63 | mean R **−2.12%**, t **−6.18** |
  | E1 2007–2020 (n 46) | −1.66% |
  | E2 2021-07→ (n 17) | −3.37% |
  | Entry at the close of t+1 | −2.01% |
  | Parkinson-60-matched excess | −2.41% |
  | Controls: ex-big-4 / ex-ex-date | −2.11% / −2.15%, no sign flip |

  - The beta-adjusted **gross** excess is ≈ −0.09%: there is no edge before cost.
  - S2, the market level, is −1.37%: continuation, not reversal.
  - No events fall in 2021-H1.
- **Cost note.** The modelled cost averages 2.03% per round trip on names with ADV ≥ Rp 10bn. That is
  high for that liquidity. It is not material here, because the result is null gross, but the D-059
  cost model's level for liquid names is flagged for a check before it is reused.
- **Filing.**
  - HYP-PM-0019 → **FAILED (F2)**; FAILURE_REGISTRY **FAIL-PM-0019**.
  - No forward recorder.
  - Price-Reversal {R1, R2, R3} keeps the slot (X8).
- **Reading for the program.** D-075's honest prior held. On IDX, even forced selling on market-wide
  stress days continues for at least a week. With this, every price-based reversal formulation tested
  is null or negative, including the one conditioned on liquidity. The only surviving reversal record is
  HYP-PM-0014, the big-4 bank climax low, which is in its forward test.

**Amendment.** Only by a superseding D-entry.

### D-080 · HYP-PM-0018 (tender-offer floor) registered in {SE}, G0 frozen at N=609; stop rule fired — no G1, dormant
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Registration + G0 freeze + stop-rule filing ·
**Approval authority:** Owner, 2026-10-09: "go for D-074", then "file it". The G0 is branch
`research/tender-offer-floor-2026-10` @ `d53ba8c`, frozen from brief `f86d272`.

- **Family and census.**
  - {SE}, slot **2** (D-076).
  - The census was 608 after D-078; this 1 arm makes **609**, bar **3.2978** (exact
    `e_max_abs_z(609)` = 3.297758). D-074's "602 / 3.2945" is superseded.
  - The arm counts from registration even though no G1 runs (D-074 stop rule, X8).
- **Study (frozen).** PREDECLARATION sha256 `237ffa72…`; the sidecar covers the predeclaration, drivers
  and PIT tests.
  - **Entry:** the close before `tender_start`. The offer is treated as public then, since the offer
    statement is published before the window (POJK 9/2018). `tender_created` is audited only: 104 of 165
    are on or before the start, 61 after, and 18 on or after the end.
  - **Population:** ADV20 ≥ Rp 1bn in true rupiah; spread to the **split-rescaled** offer price ≥ 0.60%
    plus the D-059 cost. The basis check found `tender_price` is **as announced** (LPGI, PTRO, EDGE), the
    opposite of `dividend_value`. Every vendor field needs its own basis test.
  - **Arm:** market exit at the `tender_end` close; month-clustered t.
- **Stop rule: FIRED.** Only **12** events are eligible, below the floor of 20.
  - The waterfall from 165 rows:
    - 35 fail rule 1 (34 before price coverage, plus KEJU with start ≥ end)
    - 4 still open
    - 1 has no entry bar
    - 28 have zero volume at entry
    - 60 are offered at or below the market
    - 16 are under the true-ADV floor
    - 9 have a spread below the cost
    - **12 remain**
  - The planner's 26 is fully reconciled to these frozen conventions.
  - The minimum detectable effect is 8.70% at n 12, larger than the median spread of 4.32%, so even full
    convergence could not be detected.
  - The deliverable is `SPREAD_LEDGER.md` (pre-entry facts only). `g1_run.py` is frozen and refuses to
    run while the stop holds.
- **Status: REGISTERED — dormant.** Not WITHDRAWN: that state is pre-registration and uncounted, while
  this arm is registered and counted. Not FAILED: no claim was tested. A G1 may run later under the same
  frozen rules if the eligible count reaches 20 through new settled offers. That needs owner approval
  and a census recomputed at the time.
- **Mandatory vs voluntary:** no rule is possible, because `event_note` is empty on all 165 rows. The
  full/partial cut is degenerate: the maximum `tender_percentage` is 90%.
- **Forward recorder (D-074 §3; no census arm).**
  - Every new offer is logged at `tender_start` (spread, ADV) and at `tender_end` (convergence).
  - Lineage: the D-064 ex-date monitor `scripts/check_issuance_windows.py`.
  - First case: DOOH (offer 148, 2026-10-05 → 11-03).
  - Not built yet; owner-gated.
- **Program state after D-077/D-079/D-080.** Every mechanism accepted under D-070 §1 has now been tested
  or stopped. The census ledger is **609**. The next study needs a new mechanism D-entry.

**Amendment.** Only by a superseding D-entry.

### D-081 · Volume basis: `ohlcv.volume` is consolidated from 2026-07-06; research liquidity uses regular-market volume
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Data-basis rule ·
**Approval authority:** Owner, 2026-10-09: "file it". The evidence is ZCode's audit, branch
`research/data-audits-2026-10` @ `3bacdcc` (`P-M/data_audits/minute_volume/DIAGNOSIS.md`), verified
independently by the planner the same day.

- **Finding.** From **2026-07-06** the vendor's daily OHLC volume, and the minute print tape, report
  **consolidated** volume, including the negotiated (NG) market.
  - It flip-flopped on 07-08/09 and has been permanent since **2026-07-10**.
  - The trade-book minute bars (`stockbit_flow_bars`) stay **regular-market only**, as before.
  - Planner check, same tickers each day, ohlcv vs `(max buy_lot + max sell_lot) × 100`:
    - 07-01..03: 1.00
    - 07-06: 31.7G vs 17.6G (0.55)
    - 07-07: 0.55
    - 07-08: 1.00
    - 07-10: 0.67
    - 07-14: 0.51
  - The bars are structurally intact. The trade-book endpoint **cannot** backfill the gap: a dry run
    returned 12/12 identical totals, because NG volume was never in it.
- **Consequence.** Every ADV, turnover or liquidity floor, and every "volume vs N-day average" signal
  built on `ohlcv.volume` has a level break at 2026-07-06.
  - Post-break liquidity reads about 1.5–2× higher on volume that a retail order can't trade against.
  - Windows that span the break fire spuriously.
  - Broker-flow lots (`broker_flow`) are regular-market only and unaffected.
- **Rule (research, effective now; not retroactive).**
  1. New studies take ADV and liquidity floors from **regular-market volume**: `(max buy_lot + max
     sell_lot) × 100` from the minute bars on dates ≥ 2026-07-06, and `ohlcv.volume` before.
     - The frozen function `adv_regular` is due from the volume-basis task
       (`research/volume-basis-2026-10`).
     - Until it is frozen, a study must disclose its basis.
  2. Any study whose sample spans 2026-07-06 must state its volume basis in the predeclaration.
  3. **Past verdicts are not recomputed.** The few post-break events in D-077/D-079/D-080 used
     consolidated ADV. None is near a margin that would change its verdict (HYP-PM-0018 stays below its
     n ≥ 20 stop either way).
- **Production.** No change by this entry.
  - ZCode's `0001-flow-capture-alert.patch` (`3bacdcc`) is proposed only.
  - The production consumers (volume-surge signals, liquidity tiers) are being mapped in the
    volume-basis task. Any production fix is a separate owner-approved change plus a restart.

**Amendment.** Only by a superseding D-entry.

### D-082 · Cost model: `cost_realised` (Roll on ticks) replaces D-059's Abdi-Ranaldo spread for new studies
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Methodology rule ·
**Approval authority:** Owner, 2026-10-09: "file it". The evidence is
`research/data-audits-2026-10` @ `3bacdcc`, `P-M/cost_audit/` (`COST_AUDIT.md`, `COST_AUDIT.json`).

- **Finding.** On 24.45M tick prints (2026-04-18 → 10-08), the D-059 Abdi-Ranaldo spread overstates the
  realised Roll spread by **1.5–2.4×**, worst in the liquid buckets (confirming D-059's own suspicion).
  - Round-trip cost, D-059 → realised, on normal days:

    | ADV bucket | D-059 | Realised |
    |---|---|---|
    | 1–2bn | 3.42% | 2.86% |
    | 2–5bn | 3.00% | 2.44% |
    | 5–20bn | 2.35% | 1.96% |
    | 20–100bn | 1.83% | 1.47% |
    | >100bn | 1.62% | 1.13% |

  - Realised spreads in liquid names do **not** widen on stress days. The stress basket's 2.03% is about
    1.5pp real cost plus 0.35–0.55pp AR overstatement.
- **Rule (effective now; not retroactive).**
  1. New studies use `P-M/cost_audit/cost_realised.py` (sha256 `65051253…`; API
     `realised_spread(adv, daytype)`, `d059_cost_realised(adv, sigma_d, daytype, q)`, valid at ADV ≥ Rp
     1bn). Studies cite the path, the commit and the sha256.
  2. D-059's function stays frozen, and is used only to reproduce past results.
  3. **No past verdict is recomputed.**
     - HYP-PM-0019 (D-079) fails at zero cost (gross ≈ −0.09%).
     - HYP-PM-0018 (D-080): a corrected floor likely adds one event (PTRO-2022 missed by 0.02pp), giving
       13 < 20, so the stop rule is unchanged.
     - D-059's own T1 = FRICTION reading is not reopened by this entry.
- **Limits.**
  - Roll is a spread estimator without quotes; Lee-Ready can't be used, since the corpus has no quote
    midpoint.
  - The tick sample is only 2026-04 → 10. Earlier years inherit the bucket ratios.

**Amendment.** Only by a superseding D-entry.

### D-083 · Mechanism accepted: retail ownership (KSEI) — new family Ownership-Clientele {OC}
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Mechanism acceptance (D-070 §1) ·
**Approval authority:** Owner, 2026-10-09. Asked "run the study myself instead of handing it to
ZCode?", the owner answered "Yes, run it": D-entry, then a G0 freeze with no returns read, then stop
for G1 approval. The draft is `P-M/data_acquisition/08_RETAIL_PATHS_1_4_FEASIBILITY_2026-10-09.md`
§Draft mechanism D-entries, item 2.

- **Mechanism (not price prediction).** It concerns clientele demand.
  - Stocks held mostly by individuals carry lottery-like retail demand and trade above value
    (Kumar 2009; Han and Kumar 2013; NBER w29543 on retail lottery amplification). They underperform
    after the holding is observed.
  - A month's rise in the individual share (retail inflow) is the same demand arriving. It too is
    followed by underperformance.
- **Data.** KSEI public month-end holding composition, by investor type × local/foreign, for 211
  months (2009-03 → 2026-09) with no gaps. The data is outside the repo at `~/idx_external/ksei/` and
  is hash-pinned in the G0.
- **Family.** A new family, **Ownership-Clientele {OC}**, opened by this entry. Slot 1 is A1 (level)
  and slot 2 is A2 (flow).
  - It is not {SE}: there is no discrete event. It is not {V}: the volatility exclusion is a required
    control, not the mechanism.
  - Incrementality over VOLEX (FWD-PM-VOLEX-001) is a pass condition.
- **Design constraints for the G0.**
  - Monthly cross-section, with the PIT rule frozen at G0.
  - Liquidity on the D-081 basis; costs from D-082 `cost_realised`.
  - The bar at the census + 2.
  - Both halves (2009–2017, 2018–2026) must carry the predicted sign (the era-flip lesson, D-070).
- **Honest prior.** The individual share has doubled since 2016 (median 14% → 27%), so the clientele
  changed over the sample. An era split is plausible, and a NULL is plausible.

**Amendment.** Only by a superseding D-entry.

### D-084 · HYP-PM-0020 (retail ownership, KSEI) registered in {OC}, G0 frozen at N=611; G1 approved
**Status:** RECORDED · **Date:** 2026-10-09 · **Type:** Registration + G0 freeze + G1 approval ·
**Approval authority:** Owner, 2026-10-09: "approve G1". The G0 is branch
`research/retail-ownership-2026-10` @ `b7f84ac`.

- **Family and census.**
  - {OC}, slots 1–2 (D-083): A1 level and A2 flow.
  - The census was 609 after D-080; these 2 arms make **611**, bar **3.2987** (exact 3.298685).
  - Both arms count from registration (X8).
- **Frozen study.** PREDECLARATION sha256 `601c7a9d…`; the sidecar covers the predeclaration, the
  modules, the tests, the KSEI manifest and the fetch/parse scripts.
  - Snapshots: history_long `7d298068…` and walkforward `a2d7e675…`.
  - KSEI: manifest `ae06e4a2…`, CSV `38c8a90b…`.
  - 209 monthly formations, 2009-04 → 2026-08. The formation is the 5th session after the file date,
    delayed past a late zip stamp (4 of 210).
  - Universe: median 150 names.
  - Pass: NW t ≥ bar, both halves > 0, and FM incremental over VOLEX (t ≤ −2).
  - MDE 1.68% a month (optimistic); stated in advance.
- **G1:** one run, `OC_G1_APPROVED=1`. The verdict comes from the computed booleans only.

**Amendment.** Only by a superseding D-entry.

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
