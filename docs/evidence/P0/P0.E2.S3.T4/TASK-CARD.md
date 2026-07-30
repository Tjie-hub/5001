# Task Card — P0.E2.S3.T4

**Trace tag:** [L-4]
**Story:** P0.E2.S3 — Small severities worth the baseline
**Status:** cold-reviewed (independent pass, 0 findings), merged to master — last Phase 0 task

## Intent
Log a note when a holiday check fails open, instead of failing silently.

(Source: PLAN-001 §3, Phase 0 — Audit Triage; audit finding L-4,
`Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 308: "`_holiday_skip`
fails open (calendar import error → job runs on holidays; ohlcv gets
purged later but `stockbit_flow`/`daily_screen` keep junk holiday
rows).")

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — in-file docstrings updated, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — none (no §8-classifiable event)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
