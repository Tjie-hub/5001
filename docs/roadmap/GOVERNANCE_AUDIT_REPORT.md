# Governance Audit Report — Research OS Documentation Corpus

**Auditor role:** Independent Chief Research Governance Auditor
**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** Governance certification only. Scope is bounded by mandate: this audit does not
review scientific content, does not review implementation/code, and proposes zero architectural
or scientific redesign. Where a finding touches a decision already recorded in [[DECISION_LOG]],
that decision is treated as a binding input and is re-verified against current repository state,
not re-litigated.
**Method:** Independent verification, not review-of-review. Every load-bearing claim below was
checked against live repository state on 2026-07-16 — `git cat-file`, `git log`, `git status`,
`git rev-list`, filesystem inventory, and a corpus-wide automated wikilink resolver — rather than
taken on the corpus's own word. Where this audit's conclusion matches a prior internal review
(e.g. [[DECISION_LOG]] D-018/D-024), that agreement is independently derived, stated as such, and
not assumed.
**Corpus audited:** 44 documents — `docs/roadmap/` (18), `docs/governance/` (6),
`docs/research_os/` (18), `docs/Phase_A_Scientific_Foundation/` (1), `docs/references/` (2), plus
`docs/RESEARCH_MASTER_PLAN.md` (root-level, per [[DOCUMENTATION_HIERARCHY_AUDIT]]).

---

## Executive Summary

The Research OS documentation corpus is **governance-mature and unusually self-auditing** — it
records its own contradictions, corrects them with proofs rather than edits, and has never once
described itself as frozen while a condition was outstanding. Every commit hash cited anywhere in
the corpus that this audit spot-checked (7 of 7) resolves to a real commit whose message matches
its cited context exactly. Every ADR the decision log claims exists, exists. The one wikilink this
audit's automated resolver flagged as broken had already been triaged and labeled "reserved, not
phantom" in three separate prior documents before this audit began.

That maturity is the reason this audit can be short and decisive: **the corpus is not hiding its
gaps, and neither is this report.** Five categories fail outright, three for reasons the corpus
itself has never previously stated:

1. **The entire Research OS corpus lives on a single unmerged branch** (`ops/hardening-2026-07-10`,
   82 commits ahead of `master`, never merged) — a fact no document in the 44-file corpus records
   as a risk, despite the corpus repeatedly using the word "permanent."
2. **D-015 (the L1 document's taxonomy-violating folder location) is still open on disk**, unmoved
   since 2026-07-15, with no scheduled resolution.
3. **The freeze-blocking condition (G-8, independent non-author sign-off) has zero execution
   evidence anywhere in the corpus** — no named reviewer, no scheduled date, no defined process for
   finding one, fifteen months into this program's most recent revision.

None of these three, nor anything else this audit found, requires touching architecture or science
to fix. All are documentation, process, or repository-hygiene actions.

**Overall governance score: 68 / 100** (6 categories full PASS, 9 PASS with minor conditions, 3
FAIL — see §2 for scoring method).

**Verdict: GO WITH CONDITIONS.** See §6.

---

## 1. Findings by category

Legend: **PASS** — no material gap. **PASS (CONDITIONAL)** — sound in design, one or more Minor
gaps in execution. **FAIL** — a Major gap in follow-through, not a design defect.

| # | Category | Verdict | Basis |
|---|---|---|---|
| 1 | Document hierarchy | **PASS** | [[RESEARCH_OS_RECONCILIATION]] adjudicates; [[DOCUMENTATION_HIERARCHY_AUDIT]] (this branch, prior session) closed the RMP↔ROSMR one-directional-link gap it found — verified live in both files. |
| 2 | Authority hierarchy | **PASS** | [[RESEARCH_OS_RECONCILIATION]] §5 gives an explicit, checkable conflict rule (built-mechanism → v3 wins; method/governance → OS wins). D-024 sharpens G-8 vs. G-9 scope with a textual proof, not an assertion. |
| 3 | Cross references | **PASS** | Corpus-wide automated resolver: 49 distinct wikilink targets, 1 pre-triaged exception (`[[RESEARCH_DATABASE_CONCEPT]]`, "reserved, not phantom" — confirmed present in 3 independent documents). Zero undocumented broken links. |
| 4 | Terminology consistency | **PASS (CONDITIONAL)** | The six-axis vocabulary (Layer/Program/Stage/Gate/Step/Lifecycle State) is applied consistently corpus-wide. Residual: `docs/references/MICROSTRUCTURE_RESEARCH_ROADMAP.md` still headers on "Phase I/II" — a non-canonical living doc, low severity, not previously flagged. |
| 5 | Naming standard | **PASS (CONDITIONAL)** | All 44 files are `UPPER_SNAKE_CASE.md` except `01_SCIENTIFIC_FOUNDATION.md`'s numeric prefix — already tied to the open D-015 relocation. |
| 6 | Decision traceability | **PASS** | 24 decisions (D-001–D-024), uniform Status/Date/Type/Rationale/Alternatives/Consequences/Related structure; supersession chain (D-016→D-017→D-018) correctly marked; 8 self-recorded corrections (C-1–C-8) show active self-audit, not just self-report. |
| 7 | ADR coverage | **PASS (CONDITIONAL)** | All 8 ADRs the log indexes (ADR-L1-001…008) exist verbatim in `01_SCIENTIFIC_FOUNDATION.md` §14 — exact match, independently re-counted. Condition: 7 pre-standard decisions (RD-1–RD-7) are self-flagged as undefended ISO 42010 §5.7 non-conformances, closable "only by the original decider" — none assigned. |
| 8 | Implementation traceability (doc-level) | **PASS** | All 6 L2 canonical docs carry a `Realized in v3:` field; claims are honestly hedged, not inflated (`FEATURE_COMPUTATION_GRAPH.md`: "none — no v3 component realizes the FCG"). This audit did not inspect the underlying code, per mandate — only that the documentation's traceability claim is present and non-overclaiming. |
| 9 | Roadmap consistency | **PASS** | [[RESEARCH_OS_MASTER_ROADMAP]] §7's checklist (14 ✅ / 1 open) matches D-024's claim exactly, independently re-counted. RMP's Phase A–H table is untouched and consistent with D-001's "complements, not replace" ruling. |
| 10 | Ownership | **PASS (CONDITIONAL)** | Institutional ownership model is unambiguous in prose (a single "owner" ratifies/declines; the N=1-researcher constraint is explicitly named as the root cause of G-4/G-8). Condition: a structured `**Owner:**` field is present in 30/44 files but absent from the two most load-bearing — `RESEARCH_OS_MASTER_ROADMAP.md` and `RESEARCH_OS_RECONCILIATION.md` — which use `**Authority:**` instead. Two legitimate templates coexist uncodified; [[TAXONOMY_AND_NAMING_STANDARD]] §7 documents neither split. |
| 11 | Version headers | **PASS (CONDITIONAL)** | 40/44 carry a version header. Of the 4 exceptions: `RESEARCH_MASTER_PLAN.md` is the taxonomy standard's own named grandfather exception (legitimate); `PHASE_A_ARCHITECTURE_REVIEW.md` predates the standard (point-in-time record, legitimate); `MICROSTRUCTURE_RESEARCH_ROADMAP.md` is an explicitly non-canonical living doc (legitimate); `FALSIFICATION_REVIEW_2026-07-15.md` has **no header, no title, and no version at all** — a genuine gap. The freeze-critical chain (CERTIFICATE/CHECKLIST/REVIEW_PACKAGE/EXIT_GATE_DECISION) has fully consistent, correctly cross-referenced version headers (v2.0→v2.1, v1.0→v1.1) — verified. |
| 12 | Repository organization | **FAIL** | D-015 ("OPEN — owner decision required," logged 2026-07-15) is confirmed **still open on disk**: `docs/Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md` exists at exactly the taxonomy-violating path the decision log flagged, with no motion in the intervening period. This is the corpus's own named defect, unresolved past its own follow-through window. |
| 13 | Document discoverability | **PASS (CONDITIONAL)** | The RMP↔ROSMR discoverability gap this program's own prior audit found was closed this branch (verified: pointer block present in `RESEARCH_MASTER_PLAN.md`, folder-map exception present in `RESEARCH_OS_MASTER_ROADMAP.md` §8). Residual: `FALSIFICATION_REVIEW_2026-07-15.md` (97,597 bytes, no title) is discoverable only by filename guess. |
| 14 | Change control | **PASS (CONDITIONAL)** | Strong established pattern: explicit change-control clauses (RMP §13), baseline-before-move discipline (D-014), version-bumped supersession with recorded diffs. Condition: 3 governance files from the immediately preceding session — `RESEARCH_MASTER_PLAN.md`, `RESEARCH_OS_MASTER_ROADMAP.md` (both edited), `DOCUMENTATION_HIERARCHY_AUDIT.md` (new) — are **currently uncommitted** in the working tree, a deviation from the corpus's own practice of committing each governance revision as a discrete, reviewable commit. |
| 15 | Freeze governance | **PASS (CONDITIONAL)** | The freeze-decision *mechanism* is rigorous: D-016→D-017→D-018→D-019→D-024 is a coherent, self-correcting chain under explicit epistemic discipline (LIM6/LIM8 — "self-certification is indistinguishable from genuine certification, therefore refused by mechanism"). No document anywhere claims a freeze that hasn't happened. Condition, not defect: the mechanism correctly reports **NOT FROZEN**, gated on G-8 alone for Phase A, and additionally on G-9 for Research OS v1.0. |
| 16 | Review evidence | **PASS (CONDITIONAL)** | Internal adversarial review evidence is exceptionally strong and independently verifiable: RED_TEAM_REVIEW (5 findings, committed) → ARB_ADJUDICATION (1 upheld, 4 rejected with stated reasoning) → RT4_RESOLUTION (two independent formal proofs, D-leg and W-leg) → D-023 correction — all cross-linked, all at verified commit `069afc3`. Condition: the **one review that actually unblocks freeze — a non-author sign-off — has no execution evidence anywhere.** D-019 records only that the author declined to perform it; no successor reviewer is named, scheduled, or sourced. |
| 17 | Unresolved governance debt | **FAIL** | Debt is exhaustively *tracked* (a real strength) but not *closed*, and the volume is material: **G-8** (sign-off, blocks Phase A freeze), **G-9** (custody mechanism / RFC-1, blocks Research OS v1.0 freeze and every E3+ claim), **D-015** (L1 folder location), **RD-1…RD-7** (seven undefended pre-standard decisions), and the **G-1/G-2/G-3/G-6/G-10…G-15** cluster recorded-not-resolved by D-020/D-021 (most materially **G-4**: this institution cannot currently promote any hypothesis to Accepted Knowledge, a structural N=1 ceiling, not a paperwork gap). Every item has a name and a closing condition — none is silent — but the category is, by its own definition, not clean. |
| 18 | Repository maintainability | **FAIL** | `git rev-list master..ops/hardening-2026-07-10` = **82 commits**; `git rev-list ops/hardening-2026-07-10..master` = **0**. The branch is fully synced with `origin` (0 ahead/behind), so the work is not at risk of loss, but it is **not on the repository's main line**, and no document in the corpus — including `RESEARCH_MASTER_PLAN.md`, which names `ops/hardening-2026-07-10` as its own "Branch of record" — flags this as a tension with the word "permanent." A baseline that has never merged is one policy change (branch-protection rule, CI target, a new hire cloning `master`) away from being invisible to the next reader. |

---

## 2. Scoring method

Score = weighted average across the 18 categories: **PASS = 100, PASS (CONDITIONAL) = 65,
FAIL = 15** (not 0 — every FAIL above is a *tracked, named* gap, not a silent or fabricated one,
which the scoring reflects without letting it count as passing).

6 × 100 + 9 × 65 + 3 × 15 = 600 + 585 + 45 = **1,230 / 1,800 = 68.3 → 68 / 100.**

Read as: **governance design is strong (would score ~90+ on process quality alone); governance
follow-through/closure is what drags the score down.** That split is the central fact this report
wants to leave behind — see §6.

---

## 3. Remaining issues by severity

### Critical
None. No finding in this audit involves a fabricated claim, a silent contradiction, or a document
describing something as true that the repository refutes. (The corpus's own prior self-audits, e.g.
D-012's C-1…C-8, already eliminated the class of defect that would land here — this audit found no
new instance of it.)

### Major
| ID | Finding | Category | Why it's Major, not Minor |
|---|---|---|---|
| MJ-1 | G-8 (independent, not-the-author sign-off) has no execution evidence — no reviewer named, sourced, or scheduled. | 15, 16, 17 | It is the **sole** documented blocker to Phase A freeze (D-024), and nothing in the corpus moves it forward — it has been in the identical state since D-019 (2026-07-15). |
| MJ-2 | G-9 (Dataset Custody mechanism, RFC-1) is unbuilt. | 17 | Blocks Research OS v1.0 freeze and, per D-022, every claim above evidence tier E3 — this is not paperwork, it is a stated precondition for the institution's evidential claims to be trustworthy. |
| MJ-3 | D-015 (L1 document's folder location) is open on disk, unresolved since 2026-07-15. | 5, 12 | It is the corpus's *own* named defect against its *own* naming standard (D-003/D-008), open longer than any other item in this audit, with no assigned resolver. |
| MJ-4 | The entire Research OS corpus lives only on an unmerged branch, 82 commits ahead of `master`. | 18 | Not previously recorded anywhere in the 44-document corpus, despite `RESEARCH_MASTER_PLAN.md` naming the branch explicitly and repeatedly using "permanent" and "frozen" elsewhere. Directly bears on the audit's core question. |
| MJ-5 | 3 governance files (2 edits, 1 new) sit uncommitted in the working tree. | 14 | Live governance-hierarchy content is currently unversioned, deviating from the corpus's own established one-commit-per-revision discipline. |

### Minor
| ID | Finding | Category |
|---|---|---|
| MN-1 | `FALSIFICATION_REVIEW_2026-07-15.md` (97,597 bytes) has no title, header, or version — a raw pasted transcript with no document identity. | 11, 13 |
| MN-2 | `docs/references/MICROSTRUCTURE_RESEARCH_ROADMAP.md` still uses retired "Phase I/II" section headers. | 4 |
| MN-3 | Structured `**Owner:**` field present in 30/44 files, absent from `RESEARCH_OS_MASTER_ROADMAP.md` and `RESEARCH_OS_RECONCILIATION.md` — two uncodified header templates coexist. | 10 |
| MN-4 | 7 rationale-debt items (RD-1–RD-7) are self-flagged as undefended and unassigned. | 7, 17 |
| MN-5 | `01_SCIENTIFIC_FOUNDATION.md`'s numeric filename prefix is a residual naming deviation tied to MJ-3. | 5 |
| MN-6 | Two header templates (canonical-doc vs. governance-record) exist by convention but are not documented as a rule in `TAXONOMY_AND_NAMING_STANDARD.md` §7. | 10, 5 |

---

## 4. Recommendations

Ordered by leverage, not severity — several Major items are one action each:

1. **Source and schedule G-8.** The corpus has correctly identified *what* satisfies the criterion
   ("not the author" — D-024 finding B) but has taken no action toward *finding who*. This is the
   highest-leverage single action available: it closes both the sole Phase A freeze blocker and,
   per D-024, G-4 simultaneously ("one person, two blocking gates").
2. **Resolve D-015 now, not later.** Per its own recorded options: (a) `git mv` to
   `docs/research_os/SCIENTIFIC_FOUNDATION.md` — cheapest, and already the corpus's own stated
   recommendation; or (c) formally amend D-003 to grant a standing exception. Either closes it;
   leaving it open indefinitely does not.
3. **Record the branch-permanence tension.** Either merge `ops/hardening-2026-07-10` to `master`,
   or add one sentence to `RESEARCH_MASTER_PLAN.md` and `RESEARCH_OS_MASTER_ROADMAP.md` stating why
   a permanent baseline is allowed to live on a long-running unmerged branch. Silence on this is the
   only place in the corpus where "permanent" is asserted without a supporting argument.
4. **Commit the 3 pending governance files.** Consistent with the corpus's own established
   discipline — this is a one-command action with no design content.
5. **Give `FALSIFICATION_REVIEW_2026-07-15.md` a header**, or explicitly reclassify it in
   `MIGRATION_PLAN.md` as an exempt raw-exhibit appendix rather than a document.
6. **Codify the Owner/Authority header split** in `TAXONOMY_AND_NAMING_STANDARD.md` §7 — two lines,
   turning an emergent pattern into a documented rule.
7. **Assign or explicitly waive RD-1–RD-7.** The corpus's own closing rule already allows "no
   alternatives were considered" as a valid, honest closure — apply it rather than leaving the list
   open indefinitely with no owner.

None of the above touches architecture, scientific content, or code.

---

## 5. Required actions before permanent freeze

This is the narrow subset of §4 that is **binding**, per the corpus's own governance chain (D-018,
D-019, D-022, D-024), independently re-confirmed by this audit:

- [ ] **G-8 — independent, non-author adversarial sign-off**, recorded, with Freeze Certificate
      **v3.0** naming reviewer, date, and revision frozen. *(Blocks: Phase A freeze.)*
- [ ] **G-9 — Dataset Custody mechanism (RFC-1)** built and enforcing, not merely modelled.
      *(Blocks: Research OS v1.0 freeze specifically — D-022 is explicit that this holds "even if
      D-019 is signed tomorrow." Per D-024, does not block Phase A exit / Phase B start.)*
- [ ] **D-015 resolved** — either the `git mv`, or a recorded amendment to D-003. *(Not previously
      listed as freeze-blocking by the corpus; this audit adds it because a "permanent" baseline
      containing a document at a path its own taxonomy prohibits is not a coherent thing to freeze.)*

Everything else in this report (MN-1…MN-6, MJ-4, MJ-5) is a **quality and hygiene** action, not a
freeze gate — recommended before freeze for institutional cleanliness, but not blocking it per any
decision this audit found or was asked to make.

---

## 6. Verdict

## GO WITH CONDITIONS

**This verdict is independently derived, not copied.** It happens to match the corpus's own
D-007/D-018/D-024 self-assessments, and that agreement is worth stating plainly: an outside
audit using different evidence (git-level commit verification, corpus-wide automated
cross-reference resolution, filesystem inspection) reached the same place the corpus's own
internal reviews did. That is a positive signal about the corpus's honesty, not a redundant
exercise.

**Why not READY FOR PERMANENT FREEZE:** three binding conditions remain open (§5), one of which —
G-8 — has been open, unstaffed, and unscheduled since 2026-07-15 with zero forward motion in this
audit's observation window. A "permanent" claim cannot rest on a corpus containing a document at a
self-prohibited path (D-015) or on a sign-off that exists only as a to-do.

**Why not NOT READY:** nothing found here is an architectural defect, a scientific defect, or a
broken governance *mechanism*. The mechanism is sound — arguably better instrumented than most
institutional research programs ever achieve (24 traceable decisions, 8 ADRs, self-recorded
corrections, two independent formal proofs resolving an adversarial finding). What remains is
narrow, named, and entirely executional: staff one review, move one file, merge or explain one
branch, commit three files already written.

**Distance to READY, restated in the corpus's own idiom:** one signature, one `git mv`, one merge
decision, and one RFC. Nothing on this list requires redesigning anything.

*End of Governance Audit Report v1.0 — 2026-07-16.*
