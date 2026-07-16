# Documentation Hierarchy Audit — RESEARCH_MASTER_PLAN.md ↔ RESEARCH_OS_MASTER_ROADMAP.md

**Layer:** L0 — Governance & Scope · **Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-16
**Authority:** A documentation-hierarchy ruling only. Makes zero architectural or scientific
claims. Where a finding touches prior governance ([[RESEARCH_OS_RECONCILIATION]],
[[TAXONOMY_AND_NAMING_STANDARD]], [[DECISION_LOG]] D-003/D-008/D-010), that decision is treated
as a binding input and is not reopened.
**Scope:** [[RESEARCH_MASTER_PLAN]] (`docs/RESEARCH_MASTER_PLAN.md`) ↔
[[RESEARCH_OS_MASTER_ROADMAP]] (`docs/roadmap/RESEARCH_OS_MASTER_ROADMAP.md`) only. The
remaining ~28-document corpus is out of scope for this pass.
**Mandate:** audit only. No architecture modified. No scientific concept modified. No content
inside either audited file is edited by this document.

---

## 1. Method

Both files were read in full, cross-checked against the governance record that already speaks to
their relationship ([[RESEARCH_OS_RECONCILIATION]] — "single canonical roadmap," reconciliation
decision), against [[TAXONOMY_AND_NAMING_STANDARD]] (controlled vocabulary, "Phase" retirement),
and against [[DECISION_LOG]] entries D-003, D-007, D-008, D-010, D-014, D-015, D-018 (the prior
decisions that already touch folder placement, terminology, and freeze status). Findings below are
**only** the items that survive that cross-check as still live — a large share of what looks like
overlap on first read is already resolved by [[RESEARCH_OS_RECONCILIATION]] §5 and is recorded
under "Non-findings" (§2.2) rather than re-litigated.

---

## 2. Findings

### 2.1 Live findings

#### F-1 — Broken hierarchy: the link between the two documents is one-directional (Severity: HIGH)

[[RESEARCH_OS_MASTER_ROADMAP]] references [[RESEARCH_MASTER_PLAN]]'s territory throughout (Program
P0 = "v3 Edge Pipeline," §3) and is itself built on top of the reconciliation that subordinates
[[RESEARCH_MASTER_PLAN]]'s scope to the OS. But **`docs/RESEARCH_MASTER_PLAN.md` contains zero
mentions of "Research OS," `RESEARCH_OS_MASTER_ROADMAP`, or `RESEARCH_OS_RECONCILIATION`** (verified
by grep, 0 hits). A reader who opens `RESEARCH_MASTER_PLAN.md` — which self-identifies as `🔒
ARCHITECTURE BASELINE — FROZEN` and "now the canonical `docs/RESEARCH_MASTER_PLAN.md`" (§8) — has
no way to discover that an institutional layer now wraps it, that its "canonical" claim is
scope-limited, or that [[RESEARCH_OS_RECONCILIATION]] exists at all.

This is expected chronologically — `RESEARCH_MASTER_PLAN.md` v3 froze 2026-07-14; the Research OS
track started 2026-07-15 — but the gap has not been closed since, and every day it stays open a
fresh reader has a 50/50 chance of landing on the child document first and never finding the
parent.

#### F-2 — `RESEARCH_MASTER_PLAN.md`'s folder placement is unaccounted for in the canonical folder map (Severity: MEDIUM)

[[RESEARCH_OS_MASTER_ROADMAP]] §8 declares the folder architecture as canonical: `roadmap/
governance/ research_os/ research_programs/ references/`. `docs/RESEARCH_MASTER_PLAN.md` lives at
`docs/` root — outside all five declared folders — and §8 does not mention it as an intentional
exception. The one document besides the roadmap itself that the reconciliation record calls
"canonical" has no named slot in the map that is supposed to be exhaustive.

This reads as an omission, not a violation: relocating a frozen baseline under change control
(§13 of the plan itself: "changes only by an explicit, dated amendment") is the wrong fix — see
§6 below. The fix is to name the exception, not close it by moving the file.

#### F-3 — "Phase A" is reused by the OS for a different referent than the Master Plan's Phase A (Severity: MEDIUM)

`RESEARCH_MASTER_PLAN.md`'s roadmap table (§1) uses phase code **A** for "Research Foundation" —
one of eight delivery milestones, A–H, marked `✅ Completed`. [[RESEARCH_OS_MASTER_ROADMAP]] §2 and
§7 use **"Phase A"** for an unrelated referent: "L0 + L1 + L2," the entire OS
governance/scientific/architecture foundation, whose status is `GO WITH CONDITIONS`, explicitly
**not frozen**, pending one independent signature.

[[TAXONOMY_AND_NAMING_STANDARD]] already diagnoses this exact failure mode in its own problem
statement ("'Phase A' meant both... the foundation architecture layer and... the conceptual
research we finished") and retires "Phase" from OS structural use, grandfathering only the proper
noun `RESEARCH_MASTER_PLAN.md`. That retirement is not fully carried through: `RESEARCH_OS_MASTER_ROADMAP.md`
itself still uses "Phase A" four times, including as a live section heading (§7 "Phase A Exit
Checklist") — not merely as a backward-compatibility gloss, which is the one use the standard's own
§3 sanctions ("L0, L1, L2 together constitute 'Phase A' in the old scheme"). The document that
defines the retirement is the document most saturated with the retired term.

Net effect: two canonical documents each have a milestone called "Phase A," at different altitudes,
with different freeze states, and nothing at the point of use in either document says "these are
not the same Phase A."

#### F-4 — Both documents self-declare unscoped "canonical" status (Severity: LOW — resolved by the F-1 fix)

`RESEARCH_MASTER_PLAN.md` header: "now the canonical `docs/RESEARCH_MASTER_PLAN.md`."
`RESEARCH_OS_MASTER_ROADMAP.md` header: "**Authority:** The single canonical roadmap." Read
independently, these look like a direct authority conflict. They are not — [[RESEARCH_OS_RECONCILIATION]]
§5 already scopes both correctly ("On any conflict about a mechanism already built, v3 wins... on
any conflict about scientific method or institutional governance, the OS wins") — but that scoping
lives in a third document neither header points to. This finding does not require a new rule, only
a pointer; it collapses once F-1 is fixed.

### 2.2 Non-findings — already resolved by prior governance, not re-opened here

- **Two roadmap/status tables existing at all.** Not duplication: [[RESEARCH_OS_RECONCILIATION]] §3
  already establishes ROSMR's Programs tier (P0…) as the *outer* roadmap and RMP's phase table as
  *Program P0's own internal roadmap* — different altitude, not two competing trackers of the same
  thing.
- **Two different "canonical" architectures (Object Model vs. gatekeeper code, etc.).** Resolved by
  the concept map in [[RESEARCH_OS_RECONCILIATION]] §4 — explicit "reuse, don't rebuild" table.
  Not re-audited here.
- **Conflicting freeze status of "Phase A" as a concept.** Once F-3's naming collision is separated
  out, there is no substantive conflict: RMP's Phase A (Research Foundation) is genuinely
  `✅ Completed`; ROSMR's Phase A (L0+L1+L2) is genuinely `GO WITH CONDITIONS`, not frozen. Both
  statuses are independently correct for their own referent — see [[PHASE_A_FINAL_GATE_REVIEW]] and
  D-018. The problem is the shared label, not a shared fact.
- **Folder migration incompleteness generally** (e.g., `docs/Phase_A_Scientific_Foundation/` still
  on disk, D-015 open). Real, but not part of the RMP↔ROSMR pair audited here — it is a pre-existing
  open item ([[DECISION_LOG]] D-015) outside this audit's two-document scope.

---

## 3. Canonical documentation hierarchy

```
                    RESEARCH_OS_RECONCILIATION.md
                    (adjudicates authority — this ruling is upstream of both)
                                │
                                ▼
              RESEARCH_OS_MASTER_ROADMAP.md  ◄── AUTHORITATIVE for institutional
              (Layers L0–L8, Programs P0–P6,      scope: architecture, scientific
               "the single canonical roadmap")     method, governance, taxonomy
                                │
                                │ Program P0 = "v3 Edge Pipeline (NR7 family)"
                                │ (delivered — reference implementation)
                                ▼
              RESEARCH_MASTER_PLAN.md  ◄── AUTHORITATIVE for its own scope:
              (Phases A–H, FROZEN)         the executed, tested v3 pipeline and
                                            its frozen invariants (§5 inv. 1–12)
```

**Parent:** [[RESEARCH_OS_MASTER_ROADMAP]] — governs institutional scope: what layers exist, what
programs are in flight, what "canonical" means at the OS level. It is the *entry point*.

**Child:** [[RESEARCH_MASTER_PLAN]] — governs one program's (P0's) executed scope: the frozen v3
pipeline. Per [[RESEARCH_OS_RECONCILIATION]] §5 rule 3, it wins on any question about a *mechanism
already built* — that authority is real and is not being weakened here.

**Sibling relationship, not a rival relationship.** The child is not subordinate in *correctness*
(its frozen invariants are not up for revision by the parent) — it is subordinate in *altitude*
(it specifies one program inside the parent's roadmap). This is exactly what
[[RESEARCH_OS_RECONCILIATION]] §2 already says ("complements and supersets; does not replace"); §3
of this audit just draws it as a tree.

---

## 4. Which document is authoritative

**No single document is authoritative for everything — that is not a defect, it is the correct
shape**, and it is already the ruling in [[RESEARCH_OS_RECONCILIATION]] §5. This audit's only
addition is making the split explicit at the point of use:

| Question type | Authoritative document |
|---|---|
| "What layers/programs make up the Research OS? What's in flight?" | [[RESEARCH_OS_MASTER_ROADMAP]] |
| "Is Phase A (L0+L1+L2) frozen? What blocks it?" | [[RESEARCH_OS_MASTER_ROADMAP]] / [[PHASE_A_FINAL_GATE_REVIEW]] |
| "What does the live NR7 gatekeeper/regime/registry system actually do, and is it frozen?" | [[RESEARCH_MASTER_PLAN]] |
| "Can I change a v3 invariant or the forward-test rule?" | [[RESEARCH_MASTER_PLAN]] §13 change control |
| "How do these two documents relate, and who wins on a conflict?" | [[RESEARCH_OS_RECONCILIATION]] |

---

## 5. Parent–child relationships (full tree, this pair only)

```
RESEARCH_OS_RECONCILIATION.md            (adjudicator — states the rule, not a roadmap itself)
 └─ RESEARCH_OS_MASTER_ROADMAP.md        (parent — institutional roadmap)
     └─ RESEARCH_MASTER_PLAN.md          (child — Program P0 specification, frozen)
         └─ [research/gatekeeper, research/regime, research/knowledge — code, not docs]
```

`RESEARCH_MASTER_PLAN.md` has no further documentation children in scope of this audit; its
"children" are the implemented packages it specifies, which is consistent with its own self-
description as an executed system rather than a planning document.

---

## 6. Disposition of `RESEARCH_MASTER_PLAN.md`

**Recommendation: remain as-is, content-unmodified — plus one addition (a short upward pointer),
which is a hierarchy annotation, not an architectural or scientific edit.**

Ruled out:
- **Become a pure "implementation roadmap"** (rewritten/reframed prose) — rejected. The document is
  under explicit, self-declared change control (§13: "changes only by an explicit, dated
  amendment... The roadmap is not redesigned"). Reframing its prose to read as a subordinate
  implementation doc would itself be exactly the kind of edit its own change-control clause exists
  to prevent, for a purely cosmetic hierarchy gain that a two-line pointer achieves for free.
- **Merge into `RESEARCH_OS_MASTER_ROADMAP.md`** — rejected, and already rejected once, in
  substance, by [[RESEARCH_OS_RECONCILIATION]] §2 ("Research OS does NOT replace v3... v3 becomes a
  reference implementation"). A merge would (a) destroy the audit trail of a frozen, ratified,
  owner-signed-off baseline (§8 ratification record — 6 checked items with dates and commit hashes)
  by folding it into a document still mid-revision, and (b) fan out to 10 inbound cross-references
  that would all need retargeting for no gain the parent/child tree in §3 doesn't already deliver.
- **Remain exactly as-is, zero changes at all** — rejected by a narrow margin. This is the only
  finding in this audit (F-1) that has real cost if left unfixed: a reader who never sees
  `RESEARCH_OS_MASTER_ROADMAP.md` because `RESEARCH_MASTER_PLAN.md` never mentions it is a
  recurring failure mode, not a one-time reading accident, since RMP is the older and more likely
  first hit for anyone searching "research master plan."

**Net:** the file's content, freeze status, and invariants are untouched. The only change proposed
anywhere in this audit is additive metadata (§9).

---

## 7. Documentation architecture that minimizes confusion

Two changes, both additive, both reversible, neither touching architecture or science:

1. **Upward pointer in `RESEARCH_MASTER_PLAN.md`.** A short block near the top (after the freeze
   banner, before §1) stating: this plan is Program P0 inside the Research OS; see
   [[RESEARCH_OS_MASTER_ROADMAP]] for the institutional roadmap and
   [[RESEARCH_OS_RECONCILIATION]] for the authority rule. This closes F-1 and F-4 in one edit.
2. **Named exception in `RESEARCH_OS_MASTER_ROADMAP.md` §8's folder map.** One line: `docs/RESEARCH_MASTER_PLAN.md ← Program P0 spec, root-level by design (predates the concern-based layout, frozen under its own change control, not relocated)`. Closes F-2.

F-3 (the "Phase A" collision) is addressed by a **rename of one section heading**, not a file
rename — see §8.

---

## 8. Renaming — recommended (heading only), file renames rejected

**No file is renamed.** Both `RESEARCH_MASTER_PLAN.md` and `RESEARCH_OS_MASTER_ROADMAP.md` have
real inbound reference weight (10 and 24 files respectively, by grep) and Obsidian-style `[[NAME]]`
wikilinks already resolve independent of path, per this repo's own convention
([[MIGRATION_PLAN]] §4). Renaming either file would touch dozens of cross-references to fix a
problem that isn't a filename collision — the two file names are already distinct and unambiguous.

**One heading rename is recommended:** `RESEARCH_OS_MASTER_ROADMAP.md` §7, currently "**Phase A
Exit Checklist**," → **"L0+L1+L2 Exit Checklist (legacy name: 'Phase A')."**

**Why:** [[TAXONOMY_AND_NAMING_STANDARD]] §3 sanctions "Phase A" only as a backward-compatible
*gloss* ("L0, L1, L2 together constitute 'Phase A' in the old scheme"), not as a live structural
heading — that use is exactly what §2 of the same standard retires. The current heading makes the
gloss the primary name instead of the parenthetical, which is what produces F-3's collision with
`RESEARCH_MASTER_PLAN.md`'s unrelated Phase A. Putting "L0+L1+L2" first and "Phase A" second (as an
explicit legacy-name note, not a live term) keeps every existing cross-reference and every piece of
institutional memory that says "Phase A" intact, while making the two Phase A's typographically
distinguishable at the one place — the section heading — most likely to be quoted out of context.

This is a one-line heading edit, applied to prose only. No checklist item, gate, criterion, or
status changes.

---

## 9. Migration plan — zero architectural changes

All three steps are additive-metadata or a single heading label; none touches a status, a gate, an
invariant, a checklist item, or code.

| Step | File | Change | Type |
|---|---|---|---|
| 1 | `docs/RESEARCH_MASTER_PLAN.md` | Insert a short "Position in the Research OS" block after the freeze banner (before current §1), pointing to [[RESEARCH_OS_MASTER_ROADMAP]] and [[RESEARCH_OS_RECONCILIATION]] | Additive pointer |
| 2 | `docs/roadmap/RESEARCH_OS_MASTER_ROADMAP.md` §8 | Add one line naming `docs/RESEARCH_MASTER_PLAN.md` as a declared root-level exception in the folder map | Additive pointer |
| 3 | `docs/roadmap/RESEARCH_OS_MASTER_ROADMAP.md` §7 heading | Rename "Phase A Exit Checklist" → "L0+L1+L2 Exit Checklist (legacy name: 'Phase A')" | Heading label only |

**Sequencing:** independent, can land in any order or as one commit. No baseline/rename/annotate
ordering constraint applies (unlike [[MIGRATION_PLAN]]'s file-move case) — nothing here is a `git
mv`, so [[DECISION_LOG]] D-014's precondition does not apply.

**Explicitly not in scope of this migration:**
- No change to `RESEARCH_MASTER_PLAN.md`'s §1–§8 content, its frozen invariants, its ratification
  record, or its change-control clause.
- No change to `RESEARCH_OS_MASTER_ROADMAP.md`'s Layer table, Program classifications, dependency
  diagram, or Phase A Exit Checklist *items* (only the heading label).
- No change to any of the 28 other documents in the corpus.
- No resolution of [[DECISION_LOG]] D-015 (the `Phase_A_Scientific_Foundation/` folder-location
  question) — out of this audit's two-document scope; flagged only as a related open item.
- No new DECISION_LOG entry is created by this audit; if the owner ratifies §9's three steps, a
  DECISION_LOG entry recording that ratification would follow this corpus's existing convention,
  but is not created here.

**Rollback:** every step is a text insertion or a heading rename in a version-controlled file —
`git diff` / `git checkout -- <file>` reverses any step independently.

---

## 10. Preservation statement

This audit preserves all content in both documents. It adds two pointer blocks and relabels one
section heading. It resolves zero contradictions by changing a technical fact, a status, a gate
criterion, or an invariant — every "conflict" identified in §2.1 was a **labeling/discoverability**
problem, not a substantive one, once traced to its source. The substantive authority question
(what wins on conflict) was already correctly answered by [[RESEARCH_OS_RECONCILIATION]] §5 before
this audit began; this document's contribution is making that answer reachable from both ends of
the relationship instead of one.

*End of Documentation Hierarchy Audit v1.0 — 2026-07-16.*
