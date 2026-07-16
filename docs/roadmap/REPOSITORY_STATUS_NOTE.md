# Repository Status Note — Branch of Record

**Status:** Governance record · **Date:** 2026-07-16
**Authority:** Records a repository-hygiene fact. Makes no architectural, scientific, or freeze
claim, and decides nothing — the one open question it raises (§3) is explicitly left to the owner.

---

## 1. The fact

The entire Research OS documentation corpus — every canonical document under `docs/roadmap/`,
`docs/governance/`, `docs/research_os/`, `docs/Phase_A_Scientific_Foundation/`, plus
`docs/RESEARCH_MASTER_PLAN.md` — exists **only** on branch `ops/hardening-2026-07-10`.

Verified 2026-07-16:
- `git rev-list master..ops/hardening-2026-07-10 --count` → **82** (commits on this branch not on `master`)
- `git rev-list ops/hardening-2026-07-10..master --count` → **0** (nothing on `master` this branch lacks)
- `git rev-list --left-right --count origin/ops/hardening-2026-07-10...HEAD` → **0 0** (fully synced with the remote — the work is not at risk of local-only loss)

`docs/RESEARCH_MASTER_PLAN.md` itself names this branch as its **"Branch of record"** — the fact is
already surfaced there, just not flagged as a question anywhere.

## 2. Why this is recorded

[[RESEARCH_MASTER_PLAN]] describes itself as a "permanent architectural baseline." Several Research
OS documents use "permanent" and "frozen" in the same sense. A baseline that has never merged to
`master` is durable against **loss** (it is pushed to `origin`) but not against **invisibility** — a
future clone of `master`, a new CI target, or a branch-protection change would not carry it forward.
"Permanent" and "exists only on one long-lived feature branch" are not contradictory, but they are
in tension, and per [[GOVERNANCE_AUDIT_REPORT]] §1 (category 18) no document previously stated the
tension or a plan to resolve it. This note closes the *silence*, not the *branch state*.

## 3. What this note does not decide

Whether and when `ops/hardening-2026-07-10` merges to `master` is **an owner decision**, not a
hygiene action:
- It is a repository-visible, shared-state operation (affects CI targets, collaborators' checkouts,
  and the definition of "current" for anyone who has not read this branch).
- The branch carries substantially more than the Research OS docs (application code, operational
  hardening work) — a merge decision is scoped to the whole branch, not to this documentation
  corpus alone, and is outside this note's authority to make.
- [[GOVERNANCE_AUDIT_REPORT]] §5 lists a merge (or an explicit documented decision not to merge) as
  a recommended, non-blocking action — not a freeze gate.

**Left open. No merge performed by this note or by [[GOVERNANCE_DEBT_CLOSURE]].**

---
*This note may be superseded in place (edit, not new file) once the branch question is decided —
it is a status record, not a versioned standard.*
