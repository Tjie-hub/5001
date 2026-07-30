# Task Card — P0.E2.S3.T3

**Trace tag:** [L-5]
**Story:** P0.E2.S3 — Small severities worth the baseline
**Status:** cold-reviewed (independent pass, 0 findings), merged to master

## Intent
Calendar-year-missing alarm (next-year-December class); trading calendar ownership itself moves under Clock in Phase 1 — this is the minimal alarm only.

(Source: PLAN-001 §3, Phase 0 — Audit Triage; audit finding L-5,
`Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 309: "Calendar
hardcoded through 2026 only — from 2027-01-01 every weekday is a
'trading day' and no blackouts exist. Known maintenance item; worth an
automated 'calendar year missing' alarm in December.")

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — module docstring updated, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — none (no §8-classifiable event; design choices documented in EVIDENCE.md)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
