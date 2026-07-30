# Task Card — P0.E2.S3.T1

**Trace tag:** [L-1]
**Story:** P0.E2.S3 — Small severities worth the baseline
**Status:** cold-reviewed (independent pass, 0 findings), merged to master

## Intent
/metrics endpoint column fix.

(Source: PLAN-001 §3, Phase 0 — Audit Triage; audit finding L-1,
`Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 326: "`/metrics`
`idx_market_risk_score` queries `risk_score`/`computed_at`; the table's
columns are `score`/`created_at` → the gauge is permanently NaN
(`app.py:154`).")

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log)
- [x] Regression run (full-suite output; audit-finding regression tests called out)
- [x] Gate-script output (scripts/pre_merge_gate.py)
- [x] Documentation delta (if operator-facing or contract-changing) — N/A, see EVIDENCE.md
- [x] Decision entries (IDs, if any §8-classifiable event occurred) — none (no §8-classifiable event)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
