# Gate 0 Sign-off — Phase 0 (Audit Triage)

**Tag on close:** `gate/phase-0`
**Checklist source:** EXEC-001 §16 Gate 0 (expanded from PLAN-001 §15 Phase 0 exit criteria)
**Rule:** every item mandatory; phase cannot close with any unticked item; sign-offs written as the role, dated, citing evidence bundle paths (EXEC-001 §4 rule 5). A sign-off that cites no evidence is invalid.

## Checklist

- [ ] Every P0 task merged with evidence bundle (`docs/evidence/P0/<task-id>/`) — 11/16 merged (P0.E1.S1.T1, P0.E1.S1.T2, P0.E1.S2.T1, P0.E1.S2.T2, P0.E1.S2.T3, P0.E1.S2.T4, P0.E1.S2.T5, P0.E1.S2.T6, P0.E2.S1.T1, P0.E2.S1.T2, P0.E2.S2.T1). P0.E1 and P0.E2.S1 fully closed. P0.E2.S2.T1 (`config` resolves absolute `DB_PATH` once) merged — `docs/evidence/P0/P0.E2.S2.T1/`. Remaining 5 are all P0.E2 (S2.T2, S3.T1–T4). Checkbox stays unticked until all 16 land.
- [x] Zero imported-but-unregistered jobs (grep-audit output filed) `[H-1/H-2/AN-8]` — owning tasks P0.E1.S2.T4 (audit) + P0.E1.S2.T6 (disposition of the one finding), both merged 2026-07-30: `scripts/audits/an8_unregistered_jobs.py` checks all 37 scheduler-exported candidates (not just the 6 originally-named ones) — 37/37 clean, 0 allowlisted (`run_vpin_backfill` registered daily 18:15 WIB; see `docs/evidence/P0/P0.E1.S2.T6/EVIDENCE.md`). `scripts/pre_merge_gate.py`'s QG-9 runs it for real (auto-wired per `IMPL-DEC-003`) and passes.
- [x] VPIN block demonstrated (test evidence) `[H-8]` — done: gate fixed in P0.E1.S1.T1, full behaviour matrix proven in P0.E1.S1.T2 (`docs/evidence/P0/P0.E1.S1.T2/`)
- [ ] Absolute DB path + identity logging (startup log filed) `[H-7]` — owning task P0.E2.S2: T1 done (`config` resolves absolute `DB_PATH` once via `resolve_db_path()`; ~20 modules' duplicate/fallback resolution deleted, cold-reviewed and merged 2026-07-30, `docs/evidence/P0/P0.E2.S2.T1/`); T2 (startup identity logging) remains
- [x] Date guards live (test evidence) `[M-5, H-3-min]` — owning task P0.E2.S1: T1 done (EOD coverage-fallback date guard, merged 2026-07-30, `docs/evidence/P0/P0.E2.S1.T1/`); T2 done (scan-loop/monitor/distribution-scan freshness guard, cold-reviewed and merged 2026-07-30, `docs/evidence/P0/P0.E2.S1.T2/`). P0.E2.S1 fully closed.
- [ ] Legacy baseline declaration written and dated
- [ ] Pre-merge gate script operational (bring-up item, EXEC-001 §15) — `scripts/pre_merge_gate.py`, see below
- [ ] Three-lane sign-off in this file

## Bring-up status (EXEC-001 §15, precondition to any P0 task)

| Item | Status | Evidence |
|---|---|---|
| Constitutional docs committed together, authority chain verified | DONE | commit `89e5d06` |
| Git hygiene: task-branch convention, commit-trailer format agreed | DONE (protocol, this doc + ER-3) | EXEC-001 §2, §1 ER-3 |
| Pre-merge gate script created | DONE (scoped per IMPL-DEC-003) | `scripts/pre_merge_gate.py` |
| `docs/EXEC-DECISIONS.md`, `docs/ops/MIGRATIONS.md`, `docs/EXEC-STATUS.md`, `docs/evidence/` skeletons | DONE | this tree |
| Ops checklists stubbed | DONE | `docs/ops/{daily,deployment,rollback,incident,recovery,monitoring,audit}.md` |
| Cold-review rule understood and calendarized | ACKNOWLEDGED (discipline condition, EXEC-001 §17 condition 3) | EXEC-001 §4 |
| Phase-0 task cards for P0.E1/P0.E2 with evidence lists | DONE | `docs/evidence/P0/<task-id>/TASK-CARD.md` (14 cards) |
| Dashboard initialized with Phase 0 gate checklist | DONE | `docs/EXEC-STATUS.md` |
| Legacy test suite (1,193) runs green locally | DONE — 1,195 passed, 1 skipped, 0 failed | `docs/EXEC-DECISIONS.md` IMPL-DEC-001; run log 2026-07-23 |

Note: legacy suite count is 1,195 collected (1,193 figure in EXEC-001/PLAN-001 is the documents' snapshot count; small drift is expected and not itself a finding).

## Legacy baseline declaration

Not yet written — this is a P0 exit criterion (PLAN-001 §15: "a dated statement that legacy outputs are now honest enough to compare against"), produced after P0.E1/P0.E2 tasks land, not at bring-up.

## Sign-offs

*(written as the role, dated, citing evidence bundle paths — EXEC-001 §4 rule 5. Empty until Phase 0 tasks complete.)*

- Eng:
- Arch:
- QA:
