# Task Card — P0.E2.S1.T1

**Trace tag:** [M-5]
**Story:** P0.E2.S1 — Date guards
**Status:** done

## Intent
EOD coverage-fallback date guard: assert last bar date == trade_date before treating coverage as valid.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [ ] Documentation delta (if operator-facing or contract-changing) — N/A, no `docs/ops/*` file references this path (see EVIDENCE.md)
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — IMPL-DEC-006

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
