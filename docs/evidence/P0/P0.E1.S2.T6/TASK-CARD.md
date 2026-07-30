# Task Card — P0.E1.S2.T6

**Trace tag:** [AN-8, new finding via P0.E1.S2.T4]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** merged to master 2026-07-30. Cold-reviewed per EXEC-001 §4 as an independent reviewer pass (0 findings — isolated diff, registration correctness re-derived from source and adversarially checked, not assumed from passing tests).

## Intent
Decide `run_vpin_backfill`'s fate (`scheduler/jobs.py:894`) — register on a schedule, or delete — using the same register-or-delete investigation methodology as T1–T3. Once dispositioned, remove its citation from `scripts/audits/an8_unregistered_jobs.py`'s `ALLOWLIST`.

**Result:** register, daily mon-fri at 18:15 WIB (15 min after `run_vpin_daily_batch`) — not superseded by anything, idempotent/self-healing, matches the existing daily-cadence pattern of `run_ohlcv_reconciliation`/`run_ohlcv_coverage_check`. Full investigation in `EVIDENCE.md`.

(Source: PLAN-001 §18 changelog, 2026-07-26 — new AN-8 finding surfaced by `P0.E1.S2.T4`'s repository-wide grep-audit; not one of the Audit's originally-named 6 dead jobs.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py, incl. AN-8 audit going from allowlisted to clean) — see EVIDENCE.md
- [ ] Documentation delta — not referenced by any docs/ops/* checklist (see EVIDENCE.md)
- [x] Decision entries — DEBT-003 closed (on merge)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — same shape as T1–T3.
