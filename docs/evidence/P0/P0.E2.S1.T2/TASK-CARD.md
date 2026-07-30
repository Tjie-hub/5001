# Task Card — P0.E2.S1.T2

**Trace tag:** [H-3]
**Story:** P0.E2.S1 — Date guards
**Status:** cold-reviewed 2026-07-30 (1 Major finding, fixed before merge — `scan_distribution_signals` had no freshness guard despite the evidence bundle's claim otherwise; see EVIDENCE.md "Cold review"), merged to master

## Intent
Minimal freshness guard in scan loops + monitor (skip + aggregate alert). Full guard becomes a Certifier check in Phase 1 — this is deliberately minimal, not the final form.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — N/A, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — IMPL-DEC-007

See `docs/evidence/P0/P0.E2.S1.T2/EVIDENCE.md` for the full bundle.

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
