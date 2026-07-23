# Task Card — P0.E1.S1.T2

**Trace tag:** [H-8]
**Story:** P0.E1.S1 — VPIN gate integrity
**Status:** done

## Intent
Regression test proving the enabled VPIN filter actually blocks a synthetic ticker (guards against the silent no-op regressing). Scope elaborated this session into the full required behaviour matrix (PASS/FAIL/DB-unavailable/eval-exception/disabled, plus determinism and no-leak checks) — same task ID and trace tag, no PLAN-001 edit needed (task-card-level elaboration, not a phase/scope/gate change; EXEC-001 §7 change-control ladder routes this as normal implementation, not a plan update).

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not operator-facing/contract-changing (test-only)
- [ ] Decision entries — no new OPEN-latitude choice with consequences beyond what IMPL-DEC-004 (T1) already covers

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
