# Task Card — P0.E1.S2.T5

**Trace tag:** [DEBT-001, DEBT-002]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** not-started

## Intent
Scope `auto_trade_status_report`'s query to auto-trade-originated `paper_trades` rows via a join against the existing `premover_auto_log` table (no schema change needed), and fix its `yesterday` computation to use `datetime.now(WIB)` consistently with the rest of `scheduler/reports.py`.

(Source: PLAN-001 §18 changelog, 2026-07-26 — payoff task for `DEBT-001`/`DEBT-002`, filed during P0.E1.S2.T3's cold review.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [ ] Test output (named-test run log)
- [ ] Regression run (full-suite output; audit-finding regression tests called out)
- [ ] Gate-script output (scripts/pre_merge_gate.py)
- [ ] Documentation delta (if operator-facing or contract-changing)
- [ ] Decision entries (IDs, if any §8-classifiable event occurred — closes DEBT-001/DEBT-002)

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — a query-scope + timezone fix confined to one function.
