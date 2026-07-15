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
