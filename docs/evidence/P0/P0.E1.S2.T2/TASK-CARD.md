# Task Card — P0.E1.S2.T2

**Trace tag:** [H-1]
**Story:** P0.E1.S2 — Dead jobs/reports decision
**Status:** done

## Intent
Decide run_foreign_snapshot fate; register it on the scheduler or delete it.

**Decision: Option B (delete).** Investigation found it superseded, not merely unregistered: its own `send_telegram` call was already deliberately removed (audit's own account — stale 14:30 docstring, computes a message and logs "no alert"), and its entire computation (`flow_filter.get_top_foreign_accumulation`, top_n=9999, same top-5 buy/sell split) is already folded into `scheduler/reports.py::flow_broker_report`'s "evening report" — which still calls `send_telegram`. It writes no data to the DB and has no other callers. Registering it would permanently duplicate content that already has a designated, more complete home (once `flow_broker_report` is registered under H-2/P0.E1.S2.T3, a separate task, correctly left untouched here). Full findings in EVIDENCE.md.

(Source: PLAN-001 §3, Phase 0 — Audit Triage.)

## Evidence list (EXEC-001 §3.2 — check off what applies as produced)
- [x] Test output (named-test run log) — see EVIDENCE.md
- [x] Regression run (full-suite output; audit-finding regression tests called out) — see EVIDENCE.md
- [x] Gate-script output (scripts/pre_merge_gate.py) — see EVIDENCE.md
- [ ] Documentation delta — not operator-facing (a silent-forever alert path being removed has no operator-visible effect)
- [ ] Decision entries — no OPEN-latitude choice with cross-task consequences beyond what's recorded on this card

## Rollback lever
git revert of the squash commit on main (EXEC-001 §12, commit/task layer) — every P0 change is an isolated trivial fix per PLAN-001 §3 Phase 0 preamble.
