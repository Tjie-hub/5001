# Task Card — P0.E1.S2.T6

**Trace tag:** [AN-8, new finding via P0.E1.S2.T4]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** not-started

## Intent
Decide `run_vpin_backfill`'s fate (`scheduler/jobs.py:894`) — register on a schedule, or delete — using the same register-or-delete investigation methodology as T1–T3. Once dispositioned, remove its citation from `scripts/audits/an8_unregistered_jobs.py`'s `ALLOWLIST`.

(Source: PLAN-001 §18 changelog, 2026-07-26 — new AN-8 finding surfaced by `P0.E1.S2.T4`'s repository-wide grep-audit; not one of the Audit's originally-named 6 dead jobs.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [ ] Test output (named-test run log)
- [ ] Regression run (full-suite output; audit-finding regression tests called out)
- [ ] Gate-script output (scripts/pre_merge_gate.py, incl. AN-8 audit going from allowlisted to clean)
- [ ] Documentation delta (if operator-facing or contract-changing)
- [ ] Decision entries (IDs, if any §8-classifiable event occurred)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — same shape as T1–T3.
