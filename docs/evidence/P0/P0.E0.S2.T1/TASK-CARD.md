# Task Card — P0.E0.S2.T1

**Trace tag:** [EXEC-001 §15 bring-up items 3-8, §17 condition 2]
**Story:** P0.E0.S2 — Protocol bring-up: tooling and scaffolding
**Status:** done

## Intent
Stand up the bring-up deliverables EXEC-001 §15 requires before any P0.E1/P0.E2 task starts: the pre-merge gate script, EXEC-DECISIONS/EXEC-STATUS/MIGRATIONS logs, docs/evidence/ skeleton (incl. Gate 0 sign-off doc and the 14 P0.E1/P0.E2 task cards), and the seven §10 ops checklists stubbed.

(Added via change control: PLAN-001 §18 changelog, 2026-07-23.)

## Evidence list (EXEC-001 §3.2)
- [x] Documentation delta — see EVIDENCE.md (full file list)
- [x] Gate-script output — see EVIDENCE.md (scripts/pre_merge_gate.py run, GATE: PASS)
- [ ] Test output / Regression run — covered inside the gate-script run (QG-1 full suite), not a separate named test (this task adds tooling, not application code)

## Rollback lever
git revert of the commit(s) — additive documentation + one standalone script; nothing else in the repo depends on it yet.
