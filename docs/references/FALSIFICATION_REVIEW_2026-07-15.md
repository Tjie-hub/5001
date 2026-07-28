# Falsification Review — 2026-07-15

**Layer:** — (not layer-scoped; pre-taxonomy artifact) · **Status:** Review record, non-canonical · **Date:** 2026-07-15
**Nature:** Raw pasted review transcript, preserved verbatim below. Renamed from the original
`I withdraw the code mapping.md` per [[MIGRATION_PLAN]] §3 (commit `f5a017c`) — content unchanged
by that move or by this header. It is a point-in-time review record, not architecture; the AQ-1…AQ-8
findings it raised are recorded canonically at [[01_SCIENTIFIC_FOUNDATION]] §15. This header was
added by [[GOVERNANCE_DEBT_CLOSURE]] (repository hygiene only — zero words of the transcript below
are altered).

---

I withdraw the code-mapping premise entirely. Your catatan is correct: I could not have justified it, and neither TOGAF nor ISO/IEC/IEEE 42010 

  supports it.



  But withdrawing it did not dissolve the L5 finding — it relocated it, and made it worse. Reading the documents (which your original brief forbade)

  showed that the requirement that features map to code is not my imported assumption. It is written into the FCG and the Object Model.



  ▎ FCG §4: "Features are versioned using a semantic scheme linked to the Git commit hash of their implementation. Format: 

  ▎ FeatureName_v[Major].[Minor]_[Hash]"

  ▎

  ▎ Research Object Model, Feature Definition: "code_reference: Pointer to the implemented logic in the repository."



  Your compiler analogy is the right test and it fails precisely here. Cytron et al. specify SSA form completely without LLVM — because SSA-form

  identity is mathematical. The FCG defines feature identity as a git hash of an implementation, and the Object Model makes code_reference a

  constituent field of a Feature. An architecture that names its objects after their implementations is not implementation-independent by construction.

  That is a separation-of-concerns defect in the architecture, not an implementation-readiness gap — which means the finding moves in the opposite

  direction from where you asked it to go, on grounds that vindicate your methodology rather than mine.



  I want to be explicit that I am not smuggling the premise back. The old finding was "no Python package exists, therefore the charter is insufficient"

  — that is dead, unjustifiable, withdrawn. The new finding is "the architecture couples ontology to implementation, and separately fails 42010 §5.4 

  by asserting properties without specifying conventions" — different claim, different evidence, located in the object you asked me to evaluate.



  And reading those documents surfaced something neither of us was looking for, which I now rank as the most serious finding in this entire review —

  AQ-1 below. It was invisible under your original "assume the architecture is correct" instruction.



  ---

  Part I — Methodological Grounding (points 1, 2, 3 + catatan)



  You asked for justification from architecture literature rather than engineering convention. Here it is, and it mostly favors you.



  What 42010 actually requires



  ISO/IEC/IEEE 42010:2011 governs architecture descriptions and is deliberately implementation-independent. It never requires code. Its conformance

  criteria are:



  ┌────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

  │ Clause │                                                              Requirement                                                               │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.2   │ Identify the system; identify stakeholders                                                                                             │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.3   │ Identify concerns. Required concerns include: purpose, suitability, feasibility of constructing and deploying, risks,                  │

  │        │ maintainability/evolvability                                                                                                           │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.4   │ Each viewpoint shall specify the concerns framed, the stakeholders, and the model kinds and conventions used                           │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.5   │ One view per viewpoint; every identified concern shall be framed by at least one viewpoint                                             │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.6   │ Record correspondences between views; known inconsistencies shall be recorded                                                          │

  ├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ §5.7   │ Record architecture rationale, including alternatives considered                                                                       │

  └────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  What TOGAF actually says



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  Point 3 — "Why must every layer map to a Python package?"

  It must not. Your examples — Market Ontology, Economic Taxonomy, Causal Theory, Scientific Principles — are exactly right, and note that I never 

  applied the code test to L1: my L1 finding was that the document is absent, not that the code is. That asymmetry is evidence the premise was

  inconsistently applied rather than load-bearing, which is worse, not better.



  The distinction that survives, stated rigorously



  The valid criterion is not "does code exist?" It is 42010 §5.4/§5.5: does the description frame its concerns with defined model kinds and 

  conventions? Applied honestly:



  ┌───────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

  │      Doc      │                                                       42010 §5.4 verdict                                                       │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Research      │ ✅ Conformant. Every one of 10 stages has Input / Process / Output / Validation criteria. This is a properly specified         │

  │ Pipeline      │ viewpoint and the strongest document in the corpus                                                                             │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Object Model  │ ✅ Schemas with typed fields — model kind is clear                                                                             │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Operating     │ ✅ Roles, gates, custody tiers defined                                                                                         │

  │ Model         │                                                                                                                                │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ FCG           │ ❌ Asserts properties without conventions. "Bit-identical outputs regardless of hardware architecture" is a requirement, not a │

  │               │  description. No model kind, no conventions, no framing of how it is achieved or verified                                      │

  └───────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  So the FCG's problem was never LLVM's absence — it is that, unlike Cytron's dominance-frontier algorithms, it supplies claims without conventions.

  And 42010 §5.3 makes feasibility of construction a required concern of the architecture description itself — which is the standard's own rebuttal to

  the idea that constructibility is out of scope for an AD.



  Your corpus already knows how to do this well: DATA_FEASIBILITY_STUDY frames feasibility-of-data with measured evidence, and it is excellent. It

  simply never applied the same discipline to compute.



  Net effect on W6:

  - L3 — WITHDRAWN ENTIRELY. A Dataset Object taxonomy is genuinely conceptual. "No v3 realization" was an irrelevant premise. You are simply right.

  - L5 — REVISED and RECLASSIFIED from Implementation Readiness to Architecture Quality, on grounds of implementation leakage (FCG §4, Object Model

  code_reference) and 42010 §5.4/§5.3 — not missing code.



  And you have a clean choice on L5 that fully vindicates your position: if the FCG is meant to be pure research architecture, then strike the git-hash

  versioning and code_reference — they are implementation leaking into the ontology. Do that, and my finding is not weakened, it is resolved, and the

  FCG becomes what you say it is.



  ---

  Part II — Remaining Objections



  Point 4 — Roadmap Quality contains implementation deductions — Factually incorrect on 2 of 3; conceded on the third's weight



  My Roadmap Quality components last round were: structure+governance (8.5), internal consistency (4), dependency correctness (5), layer-level gates

  (5). "L3 needs contracts" and "L5 needs specification" were scored under Implementation Readiness (3/10), not Roadmap. They never touched the roadmap

  │ §5.7   │ Record architecture rationale, including alternatives considered                                                                       │

  └────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  What TOGAF actually says



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  There is a second asymmetry: tracking is produced by a project activity (committing the docs you authored), not supplied by the environment. A recipe

  that says "preheat the oven" is not defective if you own no oven. A recipe that says "take the dough from the fridge" is defective if the dough was

  never made. Tracking is dough.



  But I concede the placement. This is a Migration Plan defect — one missing line in an otherwise correct plan whose own §4 would have caught it. It

  has nothing to do with the Master Roadmap and I withdraw it from Master Roadmap Quality entirely.



  Point 6 — The em-dash is honesty — Conceded, using your own framework



  You're right, and the correction follows from your own methodology. The em-dash is two pieces of evidence about two different objects:



  - Roadmap Quality: ↑ — accurate reporting of a real gap. It is the opposite of the phantom FOUNDATION reference, and I should have credited it as

  such. I failed to.

  - Architecture Quality: neutral — it reports L5's state; it does not change it.



  I used it validly as evidence about L5 and invalidly as though it were evidence against the roadmap. Corrected: the em-dash is a credit to the 

  roadmap.



  The limit: disclosure is not resolution. A risk register that honestly states "we have no backups" is a good register and a bad backup posture.

  Honesty earns trust in the ledger, not in the balance.



  Point 7 — Absence of a Phase B artifact reducing Phase A readiness — Conceded fully



  You're right and this was a real structural error. IMPLEMENTATION_PLAN.md is a TOGAF Phase E/F artifact. Its absence before Phase A freezes is

  correct sequencing, not a defect. My Overall 5.0 conflated two distinct gates:



  - "Can Phase A freeze?" — Implementation Readiness is irrelevant to this

  - "Can we build?" — Implementation Readiness is the whole question



  Implementation Readiness is low and that is the expected, correct state. It is a position on a ladder, not a failing. It must not feed the freeze

  decision. Withdrawn from the Phase-A assessment.



  Point 8 — Weighted averages are the wrong model — Conceded; framework redesigned below



  You're right, and the reason is precise: a weighted average is a linear utility model, which presupposes compensability. These dimensions are not

  compensatory — excellent architecture cannot offset a lost repository, and excellent implementation cannot repair a wrong ontology. Averaging

  non-compensatory dimensions manufactures a number with no referent.



  I'd steer away from CMMI specifically — it measures process maturity, not artifact readiness. The better fit is TRL-style staged readiness (ISO 

  16290): explicitly staged, explicitly non-compensatory, designed for research→deployment transitions. Redesigned in Part IV.

  │ §5.7   │ Record architecture rationale, including alternatives considered                                                                       │

  └────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  What TOGAF actually says



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  ┌───────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐

  │                     Object Model text                     │                  Feasibility Study classification                  │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ required_data: "e.g., L3 Order Book, Trades, BBO"         │ §4.3 Institutional Only — "not in any current feed"                │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ resolution: "e.g., Nanosecond, Tick, Millisecond"         │ §4.4 Unrealistic — "IDX retail data tier is ≥1-minute"             │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ classification: "e.g., Latency Arbitrage, Inventory Risk" │ §4.4 Unrealistic — "latency-arbitrage research is not the mission" │

  └───────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘



  The Data Feasibility Study is declared the binding scope constraint ("No Research Program may register a hypothesis whose required_data is not

  classified Available Today or Obtainable Later"). The Object Model — which defines the very field required_data — still teaches

  L3/BBO/nanosecond/latency-arbitrage as its worked exemplars. Two canonical documents disagree about what data exists, and the one that disagrees is

  the one a researcher reads when instantiating a Hypothesis.



  The sharpest part: the Impact Assessment presents "the 7 canonical documents are byte-for-byte unchanged" as a preservation guarantee. It is

  simultaneously the mechanism by which the stale ontology survives. Preservation and correction are in direct tension here, and no document notices.



  - Object: Architecture — the roadmap correctly established the constraint; the ontology has not complied

  - Criterion: Ontology consistency; 42010 §5.6 (known inconsistencies shall be recorded — this one is unrecorded)

  - Why not Roadmap: the roadmap did its job. Its only fault is the status claim L2 🟢 "Canonical — preserved," which asserts a compliance that does

  not hold — that fragment alone is a Roadmap defect (RQ-2)



  AQ-2 · Core object holds a mandatory reference to a non-existent object — High



  Accepted Knowledge Object.decay_monitor_id → "Link to the live process tracking the ongoing validity of the mechanism." No Decay Monitor object

  exists in the model. Roadmap §4 places Decay Monitor in "Extension (additive, optional at first)."



  So a Core object carries a required field referencing an Extension object. The Core/Extension partition is refuted by the ontology's own referential

  structure — you cannot instantiate the Core without the Extension.



  - Object: split. The dangling reference is Architecture (ontology consistency). The mis-partition is Roadmap (§4 made that call) → logged as RQ-4

  - Criterion: Ontology consistency / referential integrity



  AQ-3 · Implementation leaked into the ontology — High



  FCG §4 (git-hash feature identity) and Object Model code_reference. Detailed in Part I.

  │ §5.7   │ Record architecture rationale, including alternatives considered                                                                       │

  └────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  What TOGAF actually says



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  AQ-5 · Cross-layer dependencies asserted on unspecified layers — Medium



  Pipeline Stage 5 gates on "redundant compute nodes" (L4 Infrastructure — outline only). Stage 8 stress-tests "varying latency" — Unrealistic per

  feasibility §4.4.



  - Object: Architecture · Criterion: Dependency correctness



  AQ-6 · Methodology is unexecutable by the institution it describes — High



  Operating Model §5 defines five roles; the gates presuppose ≥3 distinct humans:



  - Gate 1: "Requires CRO or delegate approval"

  - Gate 4: "defend the economic causality... in an institutional forum"

  - Stage 9: "Consensus on economic causality" between Validation Reviewer and CRO

  - Quant Researcher: "Prohibited from accessing out-of-sample data during formulation" — while being the same person as the Validation Reviewer who

  must audit it



  For a single-researcher program, the methodology has no degenerate mode. This is the finding I filed last round as a governance-table issue; it is

  now correctly located. It is an architecture defect — the scientific methodology cannot be executed by its own institution — not a formatting

  preference about RACI.



  - Object: Architecture · Criterion: Scientific methodology; institutional maintainability

  - Why not Roadmap: the roadmap merely inherits the gate. The unexecutability originates in Operating Model §5–§6



  AQ-7 · No architecture rationale anywhere — Medium



  42010 §5.7 requires recorded rationale and evidence of alternatives considered. Absent across all six documents. Why a 10-stage pipeline? Why these

  five roles? Why FDR and DSR and PBO? Why immutability-on-use? Each is defensible; none is defended.



  - Object: both. Architecture (AD non-conformance, §5.7) and Roadmap (governance decisions untracked → RQ-3). This is the Decision Log finding, now

  grounded in the standard you named



  AQ-8 · Scientific Foundation concern unframed — High



  L1 has no artifact. Under 42010 §5.5, every identified concern must be framed by ≥1 viewpoint; domains, mechanism taxonomy, and literature corpus are

  framed by nothing.



  - Object: split. The unframed concern is Architecture (§5.5). The phantom file reference in three documents is Roadmap bookkeeping (RQ-5). My round-2

  downgrade to (B)/artifact-management was correct for the roadmap finding and incomplete — it left the architecture half unlogged



  Architecture strengths — substantial and load-bearing



  - The Pipeline is genuinely excellent. All 10 stages carry Input / Process / Output / Validation criteria. This is 42010-conformant viewpoint work

  and would let a new researcher execute S1→S10 unaided

  - Discovery → Confirmation → Accepted custody, ex-ante pre-registration, adversarial reviewer, mandatory Failure Library,

  mechanism-before-significance. This is the hard part and it is right

  - "A mechanism is invalid, regardless of statistical significance, if it cannot be explained by fundamental market micro-economics" — the single best

  sentence in the corpus

  - The worked example proves composition on feasible data. This is Level-3 evidence and most institutional research programs never produce it

  - Extensibility is strong — object-oriented ontology with lineage edges extends cleanly



  ---

  Part IV — Redesigned Framework (staged, non-compensatory)



  Replacing arithmetic weighting per your point 8. Levels gate; they do not average. A level is achieved only when all its criteria hold. Program level

  = min across objects.



  ┌───────┬───────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  ┌───────────────────────────────┬─────────────────────────────┬─────────────────────────────────────────────┬─────────────────────────┐

  │            Object             │            Level            │                 Blocked on                  │  Within-level quality   │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Architecture                  │ RL-1 (RL-3 evidence banked) │ RL-2: AQ-1, AQ-2, AQ-3, AQ-4, AQ-7, AQ-8    │ Strong — 7/10           │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Roadmap                       │ RL-1                        │ RL-2: RQ-1…RQ-5                             │ Strong — 7/10           │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Repository                    │ RL-0                        │ Durability: nothing tracked                 │ Critical — 2/10         │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Implementation (OS framework) │ RL-1                        │ RL-4: no contracts — expected, not a defect │ n/a — correct for stage │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Implementation (P0 / v3)      │ RL-6                        │ RL-7: knowledge lifecycle                   │ Strong                  │

  └───────────────────────────────┴─────────────────────────────┴─────────────────────────────────────────────┴─────────────────────────┘



  Program level = RL-0 (repository gates it). After one commit → RL-1.



  Two results the average concealed:



  1. The architecture has proof it cannot yet claim. The worked example is RL-3 evidence sitting behind an unmet RL-2 gate. An average would have

  smeared this into "7.5/10"; the ladder shows a program that skipped a rung and can reclaim it with edits that are almost all small.

  2. v3 (RL-6) is five rungs ahead of the OS that claims to generalize it (RL-1). The reference implementation is more mature than its own framework.

  That inversion is the single most important structural fact about this program, and neither my earlier scores nor the roadmap surfaces it.



  Scores are within-object only and are never summed. I am not issuing an Overall number — point 8 is right that it would have no referent.



  ---

  Part V — Roadmap Quality, re-audited (implementation deductions removed)



  ┌──────┬───────────────────────────────────────────────────────────────────────┬────────────────────┬───────────────────────────────────────────┐

  │  ID  │                                Finding                                │     Criterion      │        Why Roadmap, not elsewhere         │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-1 │ Exit checklist contains a false ✅ (folder migration)                 │ Auditability       │ The ledger is the roadmap's own artifact  │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-2 │ L2 marked 🟢 "Canonical — preserved" while carrying 7 open edits and  │ Status accuracy    │ The defect is Architecture; the false     │

  │      │ an ontology that violates the binding scope (AQ-1)                    │                    │ status claim is the roadmap's             │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-3 │ No decision log; 6 blockers → 3 with no trace; Transaction-Cost       │ Traceability;      │ Governance decisions are definitionally   │

  │      │ domain silently dropped                                               │ 42010 §5.7         │ roadmap                                   │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-4 │ Core/Extension split refuted by ontology (AQ-2)                       │ Dependency         │ §4 of the roadmap made this partition     │

  │      │                                                                       │ correctness        │                                           │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-5 │ Phantom 7th canonical doc referenced in 3 places                      │ Bookkeeping        │ Artifact management, per your point 5     │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-6 │ Missing edges: SCOPE→L6, L3→L6, L3→L4; P0→L7 understated; v3 R-5 ↔ L4 │ Dependencies       │ Your brief, criterion 2                   │

  │      │  invisible                                                            │                    │                                           │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-7 │ No gate exists for L3–L8                                              │ Exit gates         │ Your brief, criterion 4 — existence only; │

  │      │                                                                       │                    │  criteria are backlog                     │

  └──────┴───────────────────────────────────────────────────────────────────────┴────────────────────┴───────────────────────────────────────────┘



  Credited: feasibility-as-binding-constraint; taxonomy discipline; reconciliation precedence rules; concern-based folders; the L5 em-dash as honest 

  reporting.



  Withdrawn from Roadmap Quality: L3 contracts · L5 specification · Implementation Plan absence · "tracked files" precondition (→ Migration Plan).



  ---

  Part VI — Explicit Withdrawals and Downgrades



  ┌────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────┐

  │                  Finding                   │                                            Disposition                                            │

  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ "Every architecture layer must map to      │ WITHDRAWN — unjustifiable. No support in 42010 or TOGAF                                           │

  │ code"                                      │                                                                                                   │

  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ W6 for L3                                  │ WITHDRAWN ENTIRELY. Dataset ontology is conceptual; "nothing to inherit" was an irrelevant        │

  │                                            │ premise                                                                                           │

  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ W6 for L5                                  │ REVISED + RECLASSIFIED → Architecture Quality (AQ-3/AQ-4), on implementation-leakage and          │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Implementation Plan absence as a Phase-A    │ WITHDRAWN. TOGAF Phase E/F artifact; correct sequencing                                          │

  │ §5.7   │ Record architecture rationale, including alternatives considered                                                                       │

  └────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  What TOGAF actually says



  TOGAF's ADM structurally separates architecture from implementation: Phases A–D produce architecture definition; Phases E (Opportunities & Solutions)

  and F (Migration Planning) produce implementation planning. Your point 3 and point 7 are literally TOGAF's document structure. I conceded the

  two-document split last round on intuition; TOGAF grounds it.



  The answers you asked for



  Point 1 — "Can you prove a research architecture is scientifically incomplete merely because no executable package exists?"

  No. I cannot, and no standard supports it. Withdrawn without reservation. What I was actually evaluating was implementation readiness, and I

  mislabeled it. You caught a real category error.



  Point 2 — "Why does 'nothing to inherit' imply 'specification missing'?"

  It doesn't. The inference no v3 implementation → nothing to inherit → architecture incomplete is invalid, and I made it. Research Definition →

  Architecture Contract → Future Implementation is a legitimate, complete chain with an empty third slot. That is what Phase A is for.



  Point 3 — "Why must every layer map to a Python package?"

  It must not. Your examples — Market Ontology, Economic Taxonomy, Causal Theory, Scientific Principles — are exactly right, and note that I never 

  applied the code test to L1: my L1 finding was that the document is absent, not that the code is. That asymmetry is evidence the premise was

  inconsistently applied rather than load-bearing, which is worse, not better.



  The distinction that survives, stated rigorously



  The valid criterion is not "does code exist?" It is 42010 §5.4/§5.5: does the description frame its concerns with defined model kinds and 

  conventions? Applied honestly:



  ┌───────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

  │      Doc      │                                                       42010 §5.4 verdict                                                       │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Research      │ ✅ Conformant. Every one of 10 stages has Input / Process / Output / Validation criteria. This is a properly specified         │

  │ Pipeline      │ viewpoint and the strongest document in the corpus                                                                             │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Object Model  │ ✅ Schemas with typed fields — model kind is clear                                                                             │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Operating     │ ✅ Roles, gates, custody tiers defined                                                                                         │

  │ Model         │                                                                                                                                │

  ├───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ FCG           │ ❌ Asserts properties without conventions. "Bit-identical outputs regardless of hardware architecture" is a requirement, not a │

  │               │  description. No model kind, no conventions, no framing of how it is achieved or verified                                      │

  └───────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  So the FCG's problem was never LLVM's absence — it is that, unlike Cytron's dominance-frontier algorithms, it supplies claims without conventions.

  And 42010 §5.3 makes feasibility of construction a required concern of the architecture description itself — which is the standard's own rebuttal to

  the idea that constructibility is out of scope for an AD.



  Your corpus already knows how to do this well: DATA_FEASIBILITY_STUDY frames feasibility-of-data with measured evidence, and it is excellent. It

  simply never applied the same discipline to compute.



  Net effect on W6:

  - L3 — WITHDRAWN ENTIRELY. A Dataset Object taxonomy is genuinely conceptual. "No v3 realization" was an irrelevant premise. You are simply right.

  - L5 — REVISED and RECLASSIFIED from Implementation Readiness to Architecture Quality, on grounds of implementation leakage (FCG §4, Object Model

  code_reference) and 42010 §5.4/§5.3 — not missing code.



  And you have a clean choice on L5 that fully vindicates your position: if the FCG is meant to be pure research architecture, then strike the git-hash

  versioning and code_reference — they are implementation leaking into the ontology. Do that, and my finding is not weakened, it is resolved, and the

  FCG becomes what you say it is.



  ---

  Part II — Remaining Objections



  Point 4 — Roadmap Quality contains implementation deductions — Factually incorrect on 2 of 3; conceded on the third's weight



  My Roadmap Quality components last round were: structure+governance (8.5), internal consistency (4), dependency correctness (5), layer-level gates

  (5). "L3 needs contracts" and "L5 needs specification" were scored under Implementation Readiness (3/10), not Roadmap. They never touched the roadmap

  score.



  On gates, I hold — and cite your own brief:



  ▎ Review Criteria §4. Exit Gates. "Review every exit criterion. Determine whether they are measurable, objective, auditable, complete."



  You made exit gates a roadmap review criterion. Whether a gate exists is sequencing and governance — the roadmap's core job. How it is measured is

  implementation backlog. The roadmap has no gate for L3–L8 at all, not even a declaration that one exists. That deduction is properly attributed. I do

  soften it: given the two-document split, deferring gate criteria is legitimate, so this moves 5 → 6.



  Point 5 — "Repository tracked" vs "Linux installed" — Hold, on a principled boundary; withdraw from Master Roadmap



  The distinction is declared scope. The Migration Plan reasons about git state in its own text:



  - §4: "git status shows only renames (R)"

  - §5: "Every step is git mv; git checkout <branch>~1 -- docs/ restores"



  A document is accountable for preconditions it itself reasons about. Having entered the domain of git state to make validation and rollback claims,

  the plan is accountable within it. It never mentions Linux, Python, or backups — so those are genuinely environment assumptions and out of scope.

  Your analogy is not symmetric.



  There is a second asymmetry: tracking is produced by a project activity (committing the docs you authored), not supplied by the environment. A recipe

  that says "preheat the oven" is not defective if you own no oven. A recipe that says "take the dough from the fridge" is defective if the dough was

  never made. Tracking is dough.



  But I concede the placement. This is a Migration Plan defect — one missing line in an otherwise correct plan whose own §4 would have caught it. It

  has nothing to do with the Master Roadmap and I withdraw it from Master Roadmap Quality entirely.



  Point 6 — The em-dash is honesty — Conceded, using your own framework



  You're right, and the correction follows from your own methodology. The em-dash is two pieces of evidence about two different objects:



  - Roadmap Quality: ↑ — accurate reporting of a real gap. It is the opposite of the phantom FOUNDATION reference, and I should have credited it as

  such. I failed to.

  - Architecture Quality: neutral — it reports L5's state; it does not change it.



  I used it validly as evidence about L5 and invalidly as though it were evidence against the roadmap. Corrected: the em-dash is a credit to the

  roadmap.



  The limit: disclosure is not resolution. A risk register that honestly states "we have no backups" is a good register and a bad backup posture.

  Honesty earns trust in the ledger, not in the balance.



  Point 7 — Absence of a Phase B artifact reducing Phase A readiness — Conceded fully



  You're right and this was a real structural error. IMPLEMENTATION_PLAN.md is a TOGAF Phase E/F artifact. Its absence before Phase A freezes is

  correct sequencing, not a defect. My Overall 5.0 conflated two distinct gates:



  - "Can Phase A freeze?" — Implementation Readiness is irrelevant to this

  - "Can we build?" — Implementation Readiness is the whole question



  Implementation Readiness is low and that is the expected, correct state. It is a position on a ladder, not a failing. It must not feed the freeze

  decision. Withdrawn from the Phase-A assessment.



  Point 8 — Weighted averages are the wrong model — Conceded; framework redesigned below



  You're right, and the reason is precise: a weighted average is a linear utility model, which presupposes compensability. These dimensions are not

  compensatory — excellent architecture cannot offset a lost repository, and excellent implementation cannot repair a wrong ontology. Averaging

  non-compensatory dimensions manufactures a number with no referent.



  I'd steer away from CMMI specifically — it measures process maturity, not artifact readiness. The better fit is TRL-style staged readiness (ISO

  16290): explicitly staged, explicitly non-compensatory, designed for research→deployment transitions. Redesigned in Part IV.



  Point 9 — Architecture Quality unscored — Complying; one correction to the premise



  I did not "assume correctness" by choice. Your original brief instructed:



  ▎ "Assume the architecture documents are already correct. Do NOT redesign: Research Object Model, Research Operating Model, Feature Computation

  ▎ Graph, Validation Framework, Research Pipeline, Failure Library, Scientific Foundation. Those documents are outside the scope of this review. Your

  ▎ scope is ONLY: roadmap, sequencing, dependencies, governance, milestones, implementation planning."



  I complied exactly. You have now lifted that constraint, and I'm complying with the new one. I raise this only because it explains why AQ-1 — the

  most serious defect in this review — surfaced in round three rather than round one. The "assume correct" instruction was itself concealing a critical

  finding. That is worth knowing about instructions of that form.



  ---

  Part III — Architecture Quality Assessment



  Evaluated object: the six extant canonical documents + the worked example. Standard: 42010 conformance + your nine criteria. Not evaluated: roadmap,

  repository, implementation.



  AQ-1 · Ontology contradicts the binding scope constraint — Critical



  The Object Model's canonical exemplars encode the pre-feasibility worldview:



  ┌───────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐

  │                     Object Model text                     │                  Feasibility Study classification                  │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ required_data: "e.g., L3 Order Book, Trades, BBO"         │ §4.3 Institutional Only — "not in any current feed"                │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ resolution: "e.g., Nanosecond, Tick, Millisecond"         │ §4.4 Unrealistic — "IDX retail data tier is ≥1-minute"             │

  ├───────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤

  │ classification: "e.g., Latency Arbitrage, Inventory Risk" │ §4.4 Unrealistic — "latency-arbitrage research is not the mission" │

  └───────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘



  The Data Feasibility Study is declared the binding scope constraint ("No Research Program may register a hypothesis whose required_data is not

  classified Available Today or Obtainable Later"). The Object Model — which defines the very field required_data — still teaches

  L3/BBO/nanosecond/latency-arbitrage as its worked exemplars. Two canonical documents disagree about what data exists, and the one that disagrees is

  the one a researcher reads when instantiating a Hypothesis.



  The sharpest part: the Impact Assessment presents "the 7 canonical documents are byte-for-byte unchanged" as a preservation guarantee. It is

  simultaneously the mechanism by which the stale ontology survives. Preservation and correction are in direct tension here, and no document notices.



  - Object: Architecture — the roadmap correctly established the constraint; the ontology has not complied

  - Criterion: Ontology consistency; 42010 §5.6 (known inconsistencies shall be recorded — this one is unrecorded)

  - Why not Roadmap: the roadmap did its job. Its only fault is the status claim L2 🟢 "Canonical — preserved," which asserts a compliance that does

  not hold — that fragment alone is a Roadmap defect (RQ-2)



  AQ-2 · Core object holds a mandatory reference to a non-existent object — High



  Accepted Knowledge Object.decay_monitor_id → "Link to the live process tracking the ongoing validity of the mechanism." No Decay Monitor object

  exists in the model. Roadmap §4 places Decay Monitor in "Extension (additive, optional at first)."



  So a Core object carries a required field referencing an Extension object. The Core/Extension partition is refuted by the ontology's own referential

  structure — you cannot instantiate the Core without the Extension.



  - Object: split. The dangling reference is Architecture (ontology consistency). The mis-partition is Roadmap (§4 made that call) → logged as RQ-4

  - Criterion: Ontology consistency / referential integrity



  AQ-3 · Implementation leaked into the ontology — High



  FCG §4 (git-hash feature identity) and Object Model code_reference. Detailed in Part I.



  - Object: Architecture

  - Criterion: Separation of concerns; layer independence

  - Why not Implementation Readiness: the defect exists in the description and would persist unchanged if every package were written tomorrow. It is

  about what the ontology is, not what exists in research/

  - Resolution options: (a) strike the code coupling → FCG becomes genuinely conceptual, finding closed; (b) retain it → FCG is design-level and

  implementation concerns are legitimately in its scope. Currently it claims (a) and is written as (b). Your call, and (a) is fully consistent with

  your position



  AQ-4 · Construction-hard property asserted without framing — Medium



  FCG §5: "the same inputs must yield bit-identical outputs regardless of the hardware architecture." Pipeline Stage 5 promotes this to a gate:

  "Bit-identical reproducibility across redundant compute nodes."



  Cross-hardware floating-point determinism is a known-hard problem (SIMD reassociation, FMA contraction, BLAS thread-count nondeterminism). 42010 §5.3

  makes feasibility-of-construction a required concern of the AD. The AD asserts the property, gates on it, and never frames it.



  - Object: Architecture

  - Criterion: Reproducibility; 42010 §5.3

  - Why not Implementation: I am not asking for the implementation. I am observing that a required concern of the description is unframed — the same

  discipline DATA_FEASIBILITY_STUDY applies superbly to data, never applied to compute



  AQ-5 · Cross-layer dependencies asserted on unspecified layers — Medium



  Pipeline Stage 5 gates on "redundant compute nodes" (L4 Infrastructure — outline only). Stage 8 stress-tests "varying latency" — Unrealistic per

  feasibility §4.4.



  - Object: Architecture · Criterion: Dependency correctness



  AQ-6 · Methodology is unexecutable by the institution it describes — High



  Operating Model §5 defines five roles; the gates presuppose ≥3 distinct humans:



  - Gate 1: "Requires CRO or delegate approval"

  - Gate 4: "defend the economic causality... in an institutional forum"

  - Stage 9: "Consensus on economic causality" between Validation Reviewer and CRO

  - Quant Researcher: "Prohibited from accessing out-of-sample data during formulation" — while being the same person as the Validation Reviewer who

  must audit it



  For a single-researcher program, the methodology has no degenerate mode. This is the finding I filed last round as a governance-table issue; it is

  now correctly located. It is an architecture defect — the scientific methodology cannot be executed by its own institution — not a formatting

  preference about RACI.



  - Object: Architecture · Criterion: Scientific methodology; institutional maintainability

  - Why not Roadmap: the roadmap merely inherits the gate. The unexecutability originates in Operating Model §5–§6



  AQ-7 · No architecture rationale anywhere — Medium



  42010 §5.7 requires recorded rationale and evidence of alternatives considered. Absent across all six documents. Why a 10-stage pipeline? Why these

  five roles? Why FDR and DSR and PBO? Why immutability-on-use? Each is defensible; none is defended.



  - Object: both. Architecture (AD non-conformance, §5.7) and Roadmap (governance decisions untracked → RQ-3). This is the Decision Log finding, now

  grounded in the standard you named



  AQ-8 · Scientific Foundation concern unframed — High



  L1 has no artifact. Under 42010 §5.5, every identified concern must be framed by ≥1 viewpoint; domains, mechanism taxonomy, and literature corpus are

  framed by nothing.



  - Object: split. The unframed concern is Architecture (§5.5). The phantom file reference in three documents is Roadmap bookkeeping (RQ-5). My round-2

  downgrade to (B)/artifact-management was correct for the roadmap finding and incomplete — it left the architecture half unlogged



  Architecture strengths — substantial and load-bearing



  - The Pipeline is genuinely excellent. All 10 stages carry Input / Process / Output / Validation criteria. This is 42010-conformant viewpoint work

  and would let a new researcher execute S1→S10 unaided

  - Discovery → Confirmation → Accepted custody, ex-ante pre-registration, adversarial reviewer, mandatory Failure Library,

  mechanism-before-significance. This is the hard part and it is right

  - "A mechanism is invalid, regardless of statistical significance, if it cannot be explained by fundamental market micro-economics" — the single best

  sentence in the corpus

  - The worked example proves composition on feasible data. This is Level-3 evidence and most institutional research programs never produce it

  - Extensibility is strong — object-oriented ontology with lineage edges extends cleanly



  ---

  Part IV — Redesigned Framework (staged, non-compensatory)



  Replacing arithmetic weighting per your point 8. Levels gate; they do not average. A level is achieved only when all its criteria hold. Program level

  = min across objects.



  ┌───────┬───────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐

  │ Level │       Name        │                                                   Entry criteria                                                    │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-0  │ Concept           │ Ideas exist; no durable artifacts                                                                                   │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-1  │ Chartered         │ Scope bounded by measured feasibility; controlled vocabulary fixed; canonical authority declared                    │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-2  │ Described         │ Every concern framed with model kinds (§5.4/5.5); ontology internally consistent; rationale recorded (§5.7); known  │

  │       │                   │ inconsistencies recorded (§5.6)                                                                                     │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-3  │ Proven            │ Worked example composes end-to-end on feasible data                                                                 │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-4  │ Specified         │ Per-layer contracts + acceptance criteria (TOGAF Phase E/F)                                                         │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-5  │ Realized          │ Contract-bearing layers implemented                                                                                 │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-6  │ Validated         │ Reference program yields validated knowledge under the framework                                                    │

  ├───────┼───────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ RL-7  │ Institutionalized │ Decay / retirement lifecycle operating                                                                              │

  └───────┴───────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘



  Assessment per object



  ┌───────────────────────────────┬─────────────────────────────┬─────────────────────────────────────────────┬─────────────────────────┐

  │            Object             │            Level            │                 Blocked on                  │  Within-level quality   │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Architecture                  │ RL-1 (RL-3 evidence banked) │ RL-2: AQ-1, AQ-2, AQ-3, AQ-4, AQ-7, AQ-8    │ Strong — 7/10           │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Roadmap                       │ RL-1                        │ RL-2: RQ-1…RQ-5                             │ Strong — 7/10           │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Repository                    │ RL-0                        │ Durability: nothing tracked                 │ Critical — 2/10         │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Implementation (OS framework) │ RL-1                        │ RL-4: no contracts — expected, not a defect │ n/a — correct for stage │

  ├───────────────────────────────┼─────────────────────────────┼─────────────────────────────────────────────┼─────────────────────────┤

  │ Implementation (P0 / v3)      │ RL-6                        │ RL-7: knowledge lifecycle                   │ Strong                  │

  └───────────────────────────────┴─────────────────────────────┴─────────────────────────────────────────────┴─────────────────────────┘



  Program level = RL-0 (repository gates it). After one commit → RL-1.



  Two results the average concealed:



  1. The architecture has proof it cannot yet claim. The worked example is RL-3 evidence sitting behind an unmet RL-2 gate. An average would have

  smeared this into "7.5/10"; the ladder shows a program that skipped a rung and can reclaim it with edits that are almost all small.

  2. v3 (RL-6) is five rungs ahead of the OS that claims to generalize it (RL-1). The reference implementation is more mature than its own framework.

  That inversion is the single most important structural fact about this program, and neither my earlier scores nor the roadmap surfaces it.



  Scores are within-object only and are never summed. I am not issuing an Overall number — point 8 is right that it would have no referent.



  ---

  Part V — Roadmap Quality, re-audited (implementation deductions removed)



  ┌──────┬───────────────────────────────────────────────────────────────────────┬────────────────────┬───────────────────────────────────────────┐

  │  ID  │                                Finding                                │     Criterion      │        Why Roadmap, not elsewhere         │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-1 │ Exit checklist contains a false ✅ (folder migration)                 │ Auditability       │ The ledger is the roadmap's own artifact  │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-2 │ L2 marked 🟢 "Canonical — preserved" while carrying 7 open edits and  │ Status accuracy    │ The defect is Architecture; the false     │

  │      │ an ontology that violates the binding scope (AQ-1)                    │                    │ status claim is the roadmap's             │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-3 │ No decision log; 6 blockers → 3 with no trace; Transaction-Cost       │ Traceability;      │ Governance decisions are definitionally   │

  │      │ domain silently dropped                                               │ 42010 §5.7         │ roadmap                                   │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-4 │ Core/Extension split refuted by ontology (AQ-2)                       │ Dependency         │ §4 of the roadmap made this partition     │

  │      │                                                                       │ correctness        │                                           │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-5 │ Phantom 7th canonical doc referenced in 3 places                      │ Bookkeeping        │ Artifact management, per your point 5     │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-6 │ Missing edges: SCOPE→L6, L3→L6, L3→L4; P0→L7 understated; v3 R-5 ↔ L4 │ Dependencies       │ Your brief, criterion 2                   │

  │      │  invisible                                                            │                    │                                           │

  ├──────┼───────────────────────────────────────────────────────────────────────┼────────────────────┼───────────────────────────────────────────┤

  │ RQ-7 │ No gate exists for L3–L8                                              │ Exit gates         │ Your brief, criterion 4 — existence only; │

  │      │                                                                       │                    │  criteria are backlog                     │

  └──────┴───────────────────────────────────────────────────────────────────────┴────────────────────┴───────────────────────────────────────────┘



  Credited: feasibility-as-binding-constraint; taxonomy discipline; reconciliation precedence rules; concern-based folders; the L5 em-dash as honest

  reporting.



  Withdrawn from Roadmap Quality: L3 contracts · L5 specification · Implementation Plan absence · "tracked files" precondition (→ Migration Plan).



  ---

  Part VI — Explicit Withdrawals and Downgrades



  ┌─────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐

  │                   Finding                   │                                           Disposition                                            │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ "Every architecture layer must map to code" │ WITHDRAWN — unjustifiable. No support in 42010 or TOGAF                                          │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ W6 for L3                                   │ WITHDRAWN ENTIRELY. Dataset ontology is conceptual; "nothing to inherit" was an irrelevant       │

  │                                             │ premise                                                                                          │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ W6 for L5                                   │ REVISED + RECLASSIFIED → Architecture Quality (AQ-3/AQ-4), on implementation-leakage and         │

  │                                             │ §5.4/§5.3 grounds, not missing code                                                              │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Implementation Plan absence as a Phase-A    │ WITHDRAWN. TOGAF Phase E/F artifact; correct sequencing                                          │

  │ deduction                                   │                                                                                                  │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Implementation Readiness feeding the freeze │ WITHDRAWN. Different gate                                                                        │

  │  decision                                   │                                                                                                  │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ "Tracked files" as Master Roadmap defect    │ WITHDRAWN from Master Roadmap; retained as a minor Migration Plan defect, on the declared-scope  │

  │                                             │ principle                                                                                        │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ L5 em-dash as evidence of weakness          │ WITHDRAWN. Reclassified as a credit to Roadmap Quality                                           │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ Weighted-average scoring                    │ WITHDRAWN. Replaced with staged non-compensatory levels                                          │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ F3 (FOUNDATION) as Critical/(A)             │ CONFIRMED at High/(B) for Roadmap; architecture half now logged separately as AQ-8               │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ AQ-1 — ontology contradicts binding scope   │ NEW — Critical. Now the most serious finding in the review                                       │

  ├─────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤

  │ AQ-6 — methodology unexecutable by a solo   │ RELOCATED from governance-formatting to Architecture Quality                                     │

  │ institution                                 │                                                                                                  │

  └─────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘



  ---

  Verdict — GO WITH CONDITIONS (unchanged; conditions re-attributed)



  Architecture: RL-1, strong, blocked on six RL-2 criteria that are almost all small edits — update the Object Model exemplars to feasible data,

  resolve decay_monitor_id, decide FCG's conceptual-vs-design status, frame or soften the bit-identical claim, write rationale, write L1.



  Roadmap: RL-1, strong, blocked on ledger integrity and rationale.



  Repository: RL-0. One command.



  Implementation: correctly deferred. Not assessed against Phase A.



  Highest-leverage action, revised: last round I said the Decision Log. I now say AQ-1 — reconcile the Object Model's exemplars with the Data

  Feasibility Study. Every hour it stays, a researcher reading required_data: [L3 Order Book, BBO] is being taught a scope that your own binding

  constraint forbids. It is also the finding that most vindicates your instinct in this exchange: it lives entirely inside the architecture, has

  nothing to do with repository state or implementation readiness, and I could only find it by abandoning the premise you told me to abandon.
