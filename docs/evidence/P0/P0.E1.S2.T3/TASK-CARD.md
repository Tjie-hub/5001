# Task Card — P0.E1.S2.T3

**Trace tag:** [H-2, AN-8]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** done

**Cold review:** PASS WITH COMMENTS → APPROVE AFTER MINOR FIXES (2026-07-26). Three items required before merge, all resolved: (1) this status line reworded — the prior wording contained the substring "done" inside a negation, which QG-5's naive substring check (`scripts/pre_merge_gate.py:85`) mis-parsed as a done-card; (2) `DEBT-001` and the newly-found `DEBT-002` (timezone inconsistency) both now have a payoff task, `P0.E1.S2.T5` (PLAN-001 §18 changelog); (3) merged into `main` on operator confirmation following the cold review.

## Intent
Register-or-delete the three dead report functions identified by the audit.

**Decision: Option A for all three (register).** Investigation found none of `daily_fetch_report`, `flow_broker_report`, `auto_trade_status_report` is superseded by an already-registered job — each reports content no other registered job produces (fetch-pipeline completeness incl. flow/broker ticker counts; flow-sentiment + news-spike + foreign-accumulation digest; next-morning auto-trade activity digest respectively). All three are fully implemented, contain no dead internal calls, and (for two of the three) name their own intended time in-docstring. Registered as-is; the one content-scope question found (`auto_trade_status_report`'s query is not restricted to auto-trade-originated rows) is out of this task's scope and filed as DEBT-001 rather than fixed inline. Full findings in EVIDENCE.md.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not operator-facing beyond the startup banner lines (already part of the fix diff); no `docs/ops/*` checklist references these reports
- [x] Decision entries — IMPL-DEC-005 (schedule-time choice for `daily_fetch_report`), DEBT-001 (auto_trade_status_report content-scope, payoff task not yet assigned)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble. Disable lever if needed short of a full revert: remove the three `add_job` calls added in `scheduler/__init__.py`; the functions themselves are untouched, so this reverts to the exact pre-task (still-imported, still-dead) state.
