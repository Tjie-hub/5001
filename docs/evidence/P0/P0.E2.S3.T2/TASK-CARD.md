# Task Card — P0.E2.S3.T2

**Trace tag:** [L-3]
**Story:** P0.E2.S3 — Small severities worth the baseline
**Status:** cold-reviewed (independent pass, 0 findings), merged to master

## Intent
Delete the dead _parse_args function.

(Source: PLAN-001 §3, Phase 0 — Audit Triage; audit finding L-3,
`Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 328:
"`stockbit_fetcher._parse_args` is dead and buggy (self-referential list
comprehension); `main()` re-implements parsing correctly. Delete.")

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — N/A, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — none (no §8-classifiable event)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
