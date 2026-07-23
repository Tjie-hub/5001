# Task Card — P0.E1.S2.T4

**Trace tag:** [AN-8]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** not-started

## Intent
Grep-audit proving zero imported-but-unregistered jobs remain. Ships as scripts/audits/an8_unregistered_jobs.py — the pre-merge gate script (docs/EXEC-DECISIONS.md IMPL-DEC-003) wires it in once this task lands.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [ ] Test output (named-test run log)
- [ ] Regression run (full-suite output; audit-finding regression tests called out)
- [ ] Gate-script output (scripts/pre_merge_gate.py)
- [ ] Documentation delta (if operator-facing or contract-changing)
- [ ] Decision entries (IDs, if any §8-classifiable event occurred)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
