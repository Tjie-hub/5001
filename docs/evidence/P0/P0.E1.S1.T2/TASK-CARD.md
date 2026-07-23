# Task Card — P0.E1.S1.T2

**Trace tag:** [H-8]
**Story:** P0.E1.S1 — VPIN gate integrity
**Status:** not-started

## Intent
Regression test proving the enabled VPIN filter actually blocks a synthetic ticker (guards against the silent no-op regressing).

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [ ] Test output (named-test run log)
- [ ] Regression run (full-suite output; audit-finding regression tests called out)
- [ ] Gate-script output (scripts/pre_merge_gate.py)
- [ ] Documentation delta (if operator-facing or contract-changing)
- [ ] Decision entries (IDs, if any §8-classifiable event occurred)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
