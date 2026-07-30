# Task Card — P0.E2.S2.T2

**Trace tag:** [H-7]
**Story:** P0.E2.S2 — DB identity
**Status:** cold-reviewed (independent pass, 0 findings), merged to master

## Intent
Startup logs the resolved DB path + file id. Pre-figures the Certifier DB-identity check (PLAN-001 §7.3).

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — N/A, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — none (no §8-classifiable event; a clean, unambiguous implementation of the task card as written)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
