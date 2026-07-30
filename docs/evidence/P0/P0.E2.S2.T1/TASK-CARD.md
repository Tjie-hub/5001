# Task Card — P0.E2.S2.T1

**Trace tag:** [H-7]
**Story:** P0.E2.S2 — DB identity
**Status:** cold-reviewed (independent pass, no findings survived — root-cause fix applied during implementation itself, see EVIDENCE.md), merged to master

## Intent
config resolves absolute DB_PATH once; all modules import it; delete per-module fallback path resolution.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (config.py module docstring corrected — see EVIDENCE.md)
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — IMPL-DEC-008

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
