# ZCode — next tasks after the consolidation (2026-10-07)

**Owner-requested 2026-10-07** ("update next task to zcode"). The consolidation is accepted.
`origin/ops/hardening-2026-07-10` = `30e19dc`, verified with `git ls-remote`. DECISION_LOG on that
tip ends at D-069, so the next free number is **D-070**.

**Where the briefs are:** commit `eba109b` (with `04d412b`) on `fix/telegram-curation`. If origin
doesn't have them yet, read them locally with `git show eba109b:<file>`. That commit is the
production HEAD. Don't push `fix/telegram-curation` yourself.

This note **overrides** the branch points and D-numbers in the two briefs below. Everything else in
them stands.

Run the tasks in order: 0 → 1 → 2.

---

## Task 0 — file D-070 on hardening (governance, docs only)

1. Make a fresh worktree from `origin/ops/hardening-2026-07-10` (`30e19dc`).
2. Append the entry in `DECISION_DRAFT_PRICE_PATTERN_CLOSURE_2026-10-07.md` to the end of
   `docs/roadmap/DECISION_LOG.md`, after D-069:
   - Take the section from `### D-0xx · Daily price-pattern search closed…` to the end of the file.
   - Change only `D-0xx` → `D-070` in the heading. Every other character stays verbatim.
   - Don't copy the draft's preamble (Status / Filing).
   - **No other edits.** Don't change the registries or earlier entries.
3. Check: each of D-060..D-070 appears once and D-066 appears twice; `git diff` only adds lines.
4. Commit as `docs(governance): D-070 -- daily price-pattern search closed; research redirected to
   forced-flow / liquidity / risk-premium mechanisms`.
5. Push as a fast-forward (no force) and verify with `ls-remote`.

The owner approved this on 2026-10-07 ("yes, do both").

## Task 1 — sniper setup filter, HYP-PM-0016, G0 only

Brief: `ZCODE_BRIEF_SNIPER_FILTER_2026-10-07.md`. Overrides:
- **Branch:** `research/sniper-filter-2026-10` from the **post-Task-0 hardening tip**, not from
  `research/exit-study-2026-10`. The exit study is merged there at `0b30e49` content, so its frozen
  functions and sidecars are present. Verify `PREDECLARATION.sha256` and `PORTFOLIO_FIX.sha256`
  before you start.
- **D-number:** still `D-0xx` in the registration draft. Note that the next free number is D-071 at
  the time of writing; the owner assigns it at filing.
- **Cite D-070** (not "the closure draft") as the reason HYP-PM-0016 is the last admitted
  price-feature study.
- **Census:** take N from the post-D-070 log. D-070 adds no trials.

Deliver G0, push the branch, write `HANDOFF_G0.md`, and **STOP on Task 1**: no outcome read, no G1.
Then go straight to Task 2. It's independent and needs no approval.

## Task 2 — structural-event feasibility (no outcomes)

Brief: `ZCODE_BRIEF_STRUCTURAL_EVENTS_FEASIBILITY_2026-10-07.md`. Overrides:
- **Branch:** `research/structural-events-feasibility-2026-10` from the **post-Task-0 hardening
  tip**.
- **Cite D-070** as the decision this feasibility gate serves.

Everything else as briefed:
- **Rule 1: no post-event price** of any kind.
- Read-only DB, no network fetching.
- Deliverables: `FEASIBILITY_2026-10-07.md`, `CENSUS_FEASIBILITY.json`, the scripts, and a
  `HANDOFF.md` stating that no post-event price was read.

Push and STOP.

---

## Hard constraints (all three tasks)

- **Production:** don't touch the production working tree, its checkout, the service or the crontab.
  The owner does the switch to hardening and the 5001 restart, per §5 of
  `HANDOFF_OPS_CONSOLIDATION_2026-10-07.md`.
- **Logs:** `logs/TELEGRAM_OFF` stays. Never print secrets.
- **Git:** no force-push, no branch deletion.
- **Edits:** the only DECISION_LOG change is D-070 in Task 0. No registry edits. No frozen-file edits.
- **Final report:** one combined report after Task 2, covering:
  - the D-070 commit and push
  - the G0 deflation bar, grid and runtime estimate
  - the feasibility ranking
