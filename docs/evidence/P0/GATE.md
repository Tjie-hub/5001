# Gate 0 Sign-off — Phase 0 (Audit Triage)

**Tag on close:** `gate/phase-0`
**Checklist source:** EXEC-001 §16 Gate 0 (expanded from PLAN-001 §15 Phase 0 exit criteria)
**Rule:** every item mandatory; phase cannot close with any unticked item; sign-offs written as the role, dated, citing evidence bundle paths (EXEC-001 §4 rule 5). A sign-off that cites no evidence is invalid.

## Checklist

- [x] Every P0 task merged with evidence bundle (`docs/evidence/P0/<task-id>/`) — **16/16 merged**: P0.E1.S1.T1, P0.E1.S1.T2, P0.E1.S2.T1, P0.E1.S2.T2, P0.E1.S2.T3, P0.E1.S2.T4, P0.E1.S2.T5, P0.E1.S2.T6, P0.E2.S1.T1, P0.E2.S1.T2, P0.E2.S2.T1, P0.E2.S2.T2, P0.E2.S3.T1, P0.E2.S3.T2, P0.E2.S3.T3, P0.E2.S3.T4. P0.E1, P0.E2.S1, P0.E2.S2, and P0.E2.S3 all fully closed. P0.E2.S3.T4 (holiday fail-open note logged, `[L-4]`) merged 2026-07-30 — `docs/evidence/P0/P0.E2.S3.T4/`.
- [x] Zero imported-but-unregistered jobs (grep-audit output filed) `[H-1/H-2/AN-8]` — owning tasks P0.E1.S2.T4 (audit) + P0.E1.S2.T6 (disposition of the one finding), both merged 2026-07-30: `scripts/audits/an8_unregistered_jobs.py` checks all scheduler-exported candidates (not just the 6 originally-named ones) — 38/38 clean (37 pre-existing + `run_calendar_coverage_check`, added by P0.E2.S3.T3, 2026-07-30), 0 allowlisted (`run_vpin_backfill` registered daily 18:15 WIB; see `docs/evidence/P0/P0.E1.S2.T6/EVIDENCE.md`). `scripts/pre_merge_gate.py`'s QG-9 runs it for real (auto-wired per `IMPL-DEC-003`) and passes.
- [x] VPIN block demonstrated (test evidence) `[H-8]` — done: gate fixed in P0.E1.S1.T1, full behaviour matrix proven in P0.E1.S1.T2 (`docs/evidence/P0/P0.E1.S1.T2/`)
- [x] Absolute DB path + identity logging (startup log filed) `[H-7]` — owning task P0.E2.S2: T1 done (`config` resolves absolute `DB_PATH` once via `resolve_db_path()`; ~20 modules' duplicate/fallback resolution deleted, cold-reviewed and merged 2026-07-30, `docs/evidence/P0/P0.E2.S2.T1/`); T2 done (`data.db.log_db_identity()` logs the resolved absolute path + stat-derived file identity — size, mtime, device/inode — once at `app.py` startup; real log output captured in `docs/evidence/P0/P0.E2.S2.T2/EVIDENCE.md`, cold-reviewed and merged 2026-07-30). P0.E2.S2 fully closed.
- [x] Date guards live (test evidence) `[M-5, H-3-min]` — owning task P0.E2.S1: T1 done (EOD coverage-fallback date guard, merged 2026-07-30, `docs/evidence/P0/P0.E2.S1.T1/`); T2 done (scan-loop/monitor/distribution-scan freshness guard, cold-reviewed and merged 2026-07-30, `docs/evidence/P0/P0.E2.S1.T2/`). P0.E2.S1 fully closed.
- [x] Legacy baseline declaration written and dated — see "Legacy baseline declaration" section below (2026-07-30, commit `d6f11f3`)
- [x] Pre-merge gate script operational (bring-up item, EXEC-001 §15) — `scripts/pre_merge_gate.py` exists and has been run to a `GATE: PASS` result on every one of the 16 P0 task merges (see each task's `EVIDENCE.md` §"Gate-script output"), most recently 2026-07-30 post-`P0.E2.S3.T4`-merge. **Correction (documentation-consistency finding, Phase 0 close-out review):** this item was left unticked despite the "Bring-up status" table below already recording it `DONE` since 2026-07-23 — a stale checkbox, not a real gap; corrected here with direct evidence rather than carried forward.
- [x] Three-lane sign-off in this file — see "Sign-offs" section below (2026-07-30)

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

**Date:** 2026-07-30
**Commit:** `d6f11f3` (`master`, HEAD at Phase 0 close)
**Written per:** PLAN-001 §15 Phase 0 exit criterion 2 — "a dated statement that legacy outputs are now honest enough to compare against."

### Statement

The legacy Production Engine — the existing, already-running IDX trading
pipeline (scheduler, screeners, scanner, monitor, paper-trade book,
Telegram reporting) that ADR-001 v2 designates as **authoritative
throughout Phases 1–3** and the shadow-comparison baseline for the new
Data Plane — is hereby declared **sufficiently honest to serve as that
baseline**, on the scope and with the limitations below. This
declaration does not certify the legacy engine defect-free; it certifies
that the specific baseline-honesty defects identified by
`Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` as blocking trustworthy
comparison have been closed, and that every defect deliberately left
open is named, not hidden.

### Scope

All 16 Phase 0 tasks (PLAN-001 §3, P0.E1 + P0.E2), covering:
- **P0.E1 — Dead/unregistered capability triage `[H-1, H-2, H-8, AN-8]`:**
  register-or-delete decision for every historically-dead scheduled job
  and report function; VPIN gate fixed from silent no-op to fail-closed-
  with-alarm and its full behaviour matrix proven; repository-wide
  grep-audit (`scripts/audits/an8_unregistered_jobs.py`) confirms zero
  imported-but-unregistered scheduler capabilities remain (38/38 clean).
- **P0.E2.S1 — Date-guard honesty `[M-5, H-3-min]`:** EOD coverage-
  fallback no longer fabricates a row from a stale bar; scan loops and
  the intraday monitor no longer evaluate a stale last bar as current
  (minimal guard — the full Certifier-grade freshness check is Phase 1
  scope, P1.E4.S1).
- **P0.E2.S2 — DB identity `[H-7]`:** `DB_PATH` resolves to a single
  absolute path everywhere (`config.resolve_db_path()`), eliminating ~20
  independently-duplicated (8 of them identically wrong-hardcoded)
  fallback computations; startup now logs the resolved path plus
  stat-derived file identity (size, mtime, device/inode), so a
  silently-wrong DB location is now detectable from the logs alone.
- **P0.E2.S3 — Small severities `[L-1, L-3, L-4, L-5]`:** `/metrics`'s
  `idx_market_risk_score` gauge fixed (was permanently `NaN` on a
  column-name mismatch); dead, buggy `_parse_args` deleted from
  `stockbit_fetcher.py`; an automated December alarm surfaces a missing
  next-year holiday calendar before it silently degrades trading-day
  detection; `_holiday_skip`'s fail-open path (both independent copies)
  now logs a warning instead of failing silently.

Every task's evidence bundle (`docs/evidence/P0/<task-id>/`, all 16 +
the 2 P0.E0 bring-up tasks) contains named-test output, full-suite
regression results, gate-script output, and an independent cold-review
pass with 0 surviving findings (1 Major and 1 Minor finding were raised
and fixed *before* merge, across P0.E2.S1.T2 and P0.E1.S2.T5
respectively — see those tasks' `EVIDENCE.md` "Cold review" sections).

### Known limitations (deliberately not fixed here — named, not hidden)

1. **Everything on the audit's "this week" list not itemized above
   (M-1, M-3, M-9, M-8, M-7, M-6a, and the rest) is deliberately NOT
   fixed in legacy**, per PLAN-001's own explicit instruction (§3
   preamble): "those defects are remediated structurally by v2
   workstreams, and fixing them twice both wastes effort and
   contaminates the shadow-comparison baseline (harness must *explain*
   them instead [HR4])." The Phase 2 comparison harness is the
   mechanism that will surface and explain these, not this declaration.
2. **C-1 (volume-unit ambiguity) and C-2 (corporate-action adjustment)
   are unresolved** — both Critical-severity per the audit, both
   explicitly scheduled as the first Corrections under Phase 1's
   Correction & Supersession Protocol (P1.E2.S2/S3), not Phase 0 scope.
   Any legacy output derived from `ohlcv.volume` carries this known
   unit ambiguity until the C-1 ruling executes.
3. **H-5 (EOD bar authority) is unresolved** — ADR-002 is a named Phase 1
   exit blocker (P1.E2.S4), not decided yet. `INSERT OR REPLACE`
   authority conflicts between the scraper and yfinance backfill remain
   in the legacy path.
4. **The IDX holiday/BI-Rate/FOMC calendar is hardcoded through 2026
   only** (L-5) — P0.E2.S3.T3 added a December advance-warning alarm;
   it did not, and could not, populate future years' data (hand-curated,
   not derivable). If the calendar is not updated before 2027-01-01,
   legacy trading-day detection degrades exactly as documented in that
   task's evidence.
5. **`_holiday_skip`'s calendar-check failure mode is still fail-open**
   (L-4) — P0.E2.S3.T4 made the fail-open path observable (logged), not
   fail-closed. A broken calendar import still lets jobs run on a
   holiday; only now there is a WARNING log recording that it happened.
6. **H-3's freshness guard is deliberately minimal** — skip + aggregate
   alert, not the full per-ticker Certifier flag with versioned
   thresholds (that is Phase 1, P1.E4.S1 by name in both this
   declaration's source tasks and PLAN-001 itself).
7. **Two direct `is_trading_day()` call sites in `scheduler/scanner.py`
   have no exception handling at all** (fail-loud, found during
   P0.E2.S3.T4's investigation, confirmed out of L-4's scope and left
   untouched) — a calendar-import failure there raises uncaught, rather
   than either skipping cleanly or failing open. Not itemized in the
   original audit; flagged here for completeness, not fixed.

### Assumptions

- The legacy pipeline remains **authoritative** and **untouched in its
  decision logic** through Phases 1–3 (ADR-001 v2 §13); this declaration
  does not claim legacy is "correct" in an absolute sense, only that its
  outputs are now honest enough that divergences observed once the v2
  Data Plane exists will reflect real behavioral differences, not
  baseline noise from the specific defects this Phase 0 program closed.
- System clock and all date/time reasoning in the audited surfaces
  assume `Asia/Jakarta` (WIB), matching `engine/calendar_filter.py` and
  every scheduler cron entry — unchanged by Phase 0, carried forward as
  a standing assumption for the Phase 1 Clock module to formalize
  (P1.E1.S2).
- The Phase 2 comparison harness (HR5, P1.E6) is the intended mechanism
  for explaining the "Known limitations" above against real shadow
  divergences — this declaration does not substitute for that harness;
  it establishes the floor the harness starts comparing from.

### Evidence references

- `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` — originating evidence,
  FROZEN, read-only.
- `docs/evidence/P0/P0.E0.S1.T1/`, `P0.E0.S2.T1/` — protocol bring-up.
- `docs/evidence/P0/P0.E1.S1.T1/`, `T2/` — VPIN gate.
- `docs/evidence/P0/P0.E1.S2.T1/` through `T6/` — dead jobs/reports
  register-or-delete decision, AN-8 audit, and its two debt payoff
  tasks.
- `docs/evidence/P0/P0.E2.S1.T1/`, `T2/` — date guards.
- `docs/evidence/P0/P0.E2.S2.T1/`, `T2/` — DB identity.
- `docs/evidence/P0/P0.E2.S3.T1/` through `T4/` — small severities.
- `docs/EXEC-STATUS.md` — program dashboard, current as of this
  declaration.
- `docs/EXEC-DECISIONS.md` — 3 DEBT entries filed and closed
  (DEBT-001/002/003), 0 open DEF/DEBT/ARCH-ISS, 0 ADR-CANDs.

### Conclusion

**The legacy engine is now sufficiently trustworthy to serve as the
shadow-comparison baseline for Phase 1 onward**, subject to the seven
named limitations above remaining visible (not silently re-discovered)
in the Phase 2 divergence ledger when the harness comes online.

## Sign-offs

*(written as the role, dated, citing evidence bundle paths — EXEC-001 §4 rule 5, single-operator role-simulation per EXEC-001 line 13. Drafted 2026-07-30 during the formal Phase 0 close-out review, at commit `d6f11f3`; operator review/countersignature recommended before treating Gate 0 as finally closed — see close-out report §"Phase 1 readiness" condition 2.)*

- **Eng — 2026-07-30:** All 16 P0 tasks (`docs/evidence/P0/P0.E1.S1.T1/` through `P0.E2.S3.T4/`) merged to `master` with named-test output and full-suite regression evidence in each bundle. Full suite green at close: 1,307 passed, 1 skipped, 0 failed (re-run fresh at commit `d6f11f3`, not carried from an earlier task's number). No diff exceeded its task card's stated scope (self-review checklist §5.1 completed per-task, cited in each `EVIDENCE.md`).
- **Arch — 2026-07-30:** No ADR-001 v2 FROZEN surface touched by any P0 task (PLAN-001 §16 ADR-Candidate Register remains empty — verified by direct read, not assumed). No new dependency, daemon, framework, or plugin point introduced (ER-12) beyond the one new scheduled job this program added (`run_calendar_coverage_check`, P0.E2.S3.T3), which follows the existing `scheduler.add_job` registration pattern used by ~20 prior jobs. Phase 1 is already decomposed in PLAN-001 §3 (P1.E1–P1.E6) — "next phase decomposed" (EXEC-001 §10) is satisfied.
- **QA — 2026-07-30:** Gate 0 checklist (this file, EXEC-001 §16) — 8/8 items now ticked. `scripts/pre_merge_gate.py` returns `GATE: PASS` at commit `d6f11f3` (full suite 1,307/1,307+1 skipped; QG-4 N/A pre-Phase-1; QG-9 AN-8 38/38 clean, 0 allowlisted; QG-5 evidence-presence — see close-out report's independent-audit finding on this check's coverage gap, not a blocker but flagged for Phase 1). 0 open DEF/DEBT/ARCH-ISS (`docs/EXEC-DECISIONS.md`, independently re-verified by grep, not assumed). Legacy Baseline Declaration written above. **Outstanding, not blocking this sign-off:** the `gate/phase-0` milestone tag (EXEC-001 §2/§10) has not been created or pushed — recorded as a Phase 1 readiness condition, not a Gate 0 checklist item (the checklist does not list tagging as its own line item; completion criteria §10 does).
