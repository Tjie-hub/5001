# Migration Plan — Current Repository → Hybrid Structure

**Status:** Canonical · **Version:** 1.0 · **Date:** 2026-07-15
**Scope:** Move the existing Research OS documents from `docs/Institutional_Research_Architecture/` into the concern-based hybrid layout, non-destructively, preserving git history. **Governance-level only — no code.**

---

## 1. Current state

```
docs/Institutional_Research_Architecture/
  RESEARCH_OBJECT_MODEL.md
  RESEARCH_OPERATING_MODEL.md
  RESEARCH_VALIDATION_FRAMEWORK.md
  FEATURE_COMPUTATION_GRAPH.md
  MARKET_INEFFICIENCY_RESEARCH_PIPELINE.md
  FAILURE_LIBRARY_SCHEMA.md
  MICROSTRUCTURE_RESEARCH_ROADMAP.md
  PHASE_A_ARCHITECTURE_REVIEW.md   (prior review)
docs/governance/   ← NEW (authored this revision)
docs/roadmap/      ← NEW (authored this revision)
docs/research_os/  ← NEW (worked example here)
docs/research_programs/  ← NEW (empty)
docs/references/   ← NEW (empty)
```

## 2. Target mapping

| From | To | Rationale |
|---|---|---|
| `RESEARCH_OBJECT_MODEL.md` | `research_os/` | L2 canonical |
| `RESEARCH_OPERATING_MODEL.md` | `research_os/` | L2 canonical |
| `RESEARCH_VALIDATION_FRAMEWORK.md` | `research_os/` | L2/L7 canonical |
| `FEATURE_COMPUTATION_GRAPH.md` | `research_os/` | L2/L5 canonical |
| `MARKET_INEFFICIENCY_RESEARCH_PIPELINE.md` | `research_os/` | L2 canonical (pipeline) |
| `FAILURE_LIBRARY_SCHEMA.md` | `research_os/` | L2/L8 canonical |
| `Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md` | `research_os/SCIENTIFIC_FOUNDATION.md` | L1 canonical. **Was listed here as `MARKET_INEFFICIENCY_FOUNDATION` — a rename of a file that never existed** ([[DECISION_LOG]] C-6). Authored 2026-07-15. Move also resolves the taxonomy violation — **owner decision D-015 required first** |
| `MICROSTRUCTURE_RESEARCH_ROADMAP.md` | `references/` | supporting/living (not canonical law) |
| `PHASE_A_ARCHITECTURE_REVIEW.md` | `roadmap/` (or `reviews/`) | review record |
| *(already placed)* governance docs | `governance/` | ✅ done |
| *(already placed)* worked example | `research_os/` | ✅ done |

## 3. Execution steps (proposed — awaiting owner go-ahead)

Non-destructive, history-preserving. Run from repo root on a branch.

> ### ⚠️ Step 0 — baseline commit (**hard precondition, added 2026-07-15**)
>
> **This plan was unexecutable as originally written.** Every Research OS document in this repository is **untracked**, and `git mv` fails on an untracked file:
>
> ```
> $ git mv --dry-run docs/Institutional_Research_Architecture/RESEARCH_OBJECT_MODEL.md docs/research_os/
> fatal: not under version control, source=docs/Institutional_Research_Architecture/RESEARCH_OBJECT_MODEL.md
> ```
>
> A rename cannot preserve a history that does not exist. The migration was never blocked on approval alone — it was blocked on a precondition no document had noticed ([[DECISION_LOG]] **D-014**).
>
> ```bash
> # Step 0 — track the corpus FIRST. Docs only; no code, no data.
> git add docs/Institutional_Research_Architecture/ docs/governance/ docs/roadmap/ \
>         docs/research_os/ docs/Phase_A_Scientific_Foundation/
> git commit -m "docs(research-os): baseline Phase A corpus before concern-based migration"
> ```
>
> **Ordering is three commits, and the order is load-bearing: baseline → rename → annotate.** Bundling the baseline into the move would make the move appear as adds rather than renames, destroying the reviewability this plan exists to protect and defeating its own §4 validation check.

```bash
# 1. move canonical L1/L2 docs  (requires Step 0)
git mv docs/Institutional_Research_Architecture/RESEARCH_OBJECT_MODEL.md          docs/research_os/
git mv docs/Institutional_Research_Architecture/RESEARCH_OPERATING_MODEL.md       docs/research_os/
git mv docs/Institutional_Research_Architecture/RESEARCH_VALIDATION_FRAMEWORK.md  docs/research_os/
git mv docs/Institutional_Research_Architecture/FEATURE_COMPUTATION_GRAPH.md      docs/research_os/
git mv docs/Institutional_Research_Architecture/MARKET_INEFFICIENCY_RESEARCH_PIPELINE.md docs/research_os/
git mv docs/Institutional_Research_Architecture/FAILURE_LIBRARY_SCHEMA.md         docs/research_os/
# 2. supporting reference
git mv docs/Institutional_Research_Architecture/MICROSTRUCTURE_RESEARCH_ROADMAP.md docs/references/
# 3. review record
git mv docs/Institutional_Research_Architecture/PHASE_A_ARCHITECTURE_REVIEW.md    docs/roadmap/
# 4. L1 Scientific Foundation — ONLY IF owner resolves D-015 in favour of option (a)
git mv docs/Phase_A_Scientific_Foundation/01_SCIENTIFIC_FOUNDATION.md docs/research_os/SCIENTIFIC_FOUNDATION.md
rmdir docs/Phase_A_Scientific_Foundation 2>/dev/null || true
# 5. retire the old dir once empty
rmdir docs/Institutional_Research_Architecture 2>/dev/null || true
```

**Not moved by this plan:** `docs/Institutional_Research_Architecture/I withdraw the code mapping.md` — a 1,579-line pasted review transcript carrying the AQ-1…AQ-8 findings. It is a review record, not architecture, and its filename is not a document name. Recommend `git mv` to `references/FALSIFICATION_REVIEW_2026-07-15.md` as part of the annotation commit; the AQ findings it contains are already recorded canonically at [[01_SCIENTIFIC_FOUNDATION]] §15.

## 4. Post-migration validation
- [x] **Empty declared folders survive.** `docs/research_programs/` carries a `.gitkeep` (1 file); `docs/references/` holds 2 files. Both non-empty/tracked as declared. **Verified 2026-07-16** by [[GOVERNANCE_DEBT_CLOSURE]] filesystem check.
- [x] `git status` shows only renames (R), no content diffs → confirms non-destructive. **Verified 2026-07-16**: `git diff-tree --name-status f5a017c` shows 9 renamed files with **zero content diff** each, plus the one disclosed exception (`research_programs/.gitkeep`, a new 1-line file, exactly as the commit message states). No undisclosed content change.
- [x] Wikilinks `[[NAME]]` still resolve (they are name-based, path-independent). **Verified 2026-07-16** by an automated corpus-wide resolver in [[GOVERNANCE_AUDIT_REPORT]] §1 (category 3): 49 distinct targets, 1 pre-declared exception (`[[RESEARCH_DATABASE_CONCEPT]]`, already triaged elsewhere as "reserved, not phantom"), zero undocumented breaks.
- [x] Each canonical doc gets its layer tag + v3 cross-reference (a *content* follow-up, separate commit). **Verified 2026-07-16**: all six L2 docs carry a `Realized in v3:` field ([[GOVERNANCE_AUDIT_REPORT]] §1, category 8).
- [ ] Add a `SCOPE_FILE` note where the pasted Master Research Plan v1.0 text should be saved (it currently exists only in chat history — recommend `references/DRAFT_MASTER_PLAN_v1.0_ARCHIVED.md`). **Still open — deferred, not resolved by [[GOVERNANCE_DEBT_CLOSURE]].** No content-authority decision is needed to close it (it is a pure archival copy of already-superseded draft text), but locating and transcribing chat-history text is not a hygiene action this pass performs; low priority, since v1.0 was fully superseded by the ratified v3 baseline.

## 5. Rollback
Every step is `git mv`; `git checkout <branch>~1 -- docs/` or reverse-`git mv` restores. No data touched.

## 6. Sequencing note
Do the **content annotations** (layer tags, v3 cross-refs, domain de-overlap) as a *second* commit after the move, so the move commit is a pure rename (clean history, easy review). Do **not** bundle move + edit.

---
**Recommendation:** execute §3 as one rename-only commit on the current branch after owner approval, then the annotation pass as a second commit. I have prepared but **not executed** the moves — they await your go-ahead.
