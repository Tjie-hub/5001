# Task Card — P0.E1.S2.T4

**Trace tag:** [AN-8]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** merged to master 2026-07-30. Cold-reviewed per EXEC-001 §4 (0 findings — diff scoped exactly to task card, no FROZEN-surface/scheduler-logic changes, cross-doc references consistent, test/gate output independently reproduced).

## Intent
Grep-audit proving zero imported-but-unregistered jobs remain. Ships as scripts/audits/an8_unregistered_jobs.py — the pre-merge gate script (docs/EXEC-DECISIONS.md IMPL-DEC-003) wires it in once this task lands.

**Result:** 37 candidates checked (every name re-exported from scheduler/__init__.py, not only the Audit's originally-named 6). 36 clean, 1 new finding — `run_vpin_backfill` (unwired, no callers anywhere in the repo). Allowlisted with a citation to its follow-up task, `P0.E1.S2.T6` (PLAN-001 §18 changelog). Full methodology and per-candidate findings in `AUDIT-REPORT.md`.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md; QG-9 now enforced for real, not PENDING
- [ ] Documentation delta — not operator-facing (an internal audit tool; no docs/ops/* reference)
- [x] Decision entries — DEBT-003 (run_vpin_backfill unwired capability; payoff task P0.E1.S2.T6 assigned)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
