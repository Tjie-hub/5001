# Task Card — P0.E1.S2.T1

**Trace tag:** [H-1]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** done

## Intent
Register the risk-bundle + EOD-risk-summary jobs, or delete their tiering — explicit decision recorded in the commit message either way.

**Decision: Option A (register).** Both jobs are fully implemented, idempotent, correctly holiday-guarded, and match their own module docstring's documented design ("RED: bundled hourly by scheduler", "ORANGE: EOD summary only") and the audit's own fix text ("Register the two jobs (hourly during session + EOD)"). Nothing about them is obsolete or wrong — they were simply never handed to `scheduler.add_job(...)`. Option B (delete the tiering, send RED immediately) was rejected: it would be a behavioral redesign of the alert-tiering contract, not a minimal fix, and the audit frames deletion as the fallback only if the jobs were found obsolete — they are not.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not operator-facing beyond the startup print-summary lines (already covered as part of this change, not a separate doc)
- [ ] Decision entries — no new OPEN-latitude choice with cross-task consequences beyond what's recorded on this card (schedule-time choice is task-local, not reused elsewhere)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
