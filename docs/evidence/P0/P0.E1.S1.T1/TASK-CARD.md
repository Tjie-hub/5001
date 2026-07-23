# Task Card — P0.E1.S1.T1

**Trace tag:** [H-8, AN-5]
**Story:** P0.E1.S1 — VPIN gate integrity
**Status:** done

## Intent
Fix the `_db_connect` NameError in the VPIN gate; convert the except-path from silent pass-through to a fail-closed skip that raises an alarm.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not operator-facing/contract-changing (internal gate logic only)
- [x] Decision entries — IMPL-DEC-004 (docs/EXEC-DECISIONS.md), for the fail_closed_alarm addition

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
