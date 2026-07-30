# Task Card — P0.E1.S2.T5

**Trace tag:** [DEBT-001, DEBT-002]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** merged to master 2026-07-30. Cold-reviewed per EXEC-001 §4 as an independent reviewer pass (1 Minor doc-wording finding, fixed before merge; adversarial edge-case probing found no functional defects).

## Intent
Scope `auto_trade_status_report`'s query to auto-trade-originated `paper_trades` rows via a join against the existing `premover_auto_log` table (no schema change needed), and fix its `yesterday` computation to use `datetime.now(WIB)` consistently with the rest of `scheduler/reports.py`.

(Source: PLAN-001 §18 changelog, 2026-07-26 — payoff task for `DEBT-001`/`DEBT-002`, filed during P0.E1.S2.T3's cold review.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not referenced by any docs/ops/* checklist (see EVIDENCE.md)
- [x] Decision entries — DEBT-001, DEBT-002 update filed; both close on this task's merge, per `docs/EXEC-DECISIONS.md`

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — a query-scope + timezone fix confined to one function.
