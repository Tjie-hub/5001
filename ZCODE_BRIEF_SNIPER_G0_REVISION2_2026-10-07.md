# ZCode brief — sniper filter G0 Revision 2: bar 3.29 + fallback leak (2026-10-07)

**Planner review of Revision 1 (`b3dd0bc`): accepted on R1–R7.**
- The sidecar verifies, and all 17 tests pass.
- The code implements every fix.
- No outcome was read.

**Owner ruling 2026-10-07 ("sniper 3.29"):** two changes, then re-freeze and STOP. Revision 2 is
pre-approval and discloses itself. It is not a re-run.

## Changes

**V1. Primary bar = the complete census.**
- `CENSUS_BASE_PRIMARY = 595`: the 561 recount plus the three items it missed — HYP-PM-0015's 6,
  BOS/trendline 8, and the exit study's 20 at its upper bound. The breakdown is in
  `DECISION_DRAFT_CENSUS_RATIFICATION_2026-10-07.md`, commit `2937488` on local
  `ops/hardening-2026-07-10`. Cite it.
- `CENSUS_N_PRIMARY = 599`.
- `BAR_PRIMARY = emax_abs_z(599)`, written to 4 dp (≈ **3.2931**). Compute it; don't type it.
- Add a test asserting the frozen constant equals `round(emax_abs_z(599), 4)`.
- Secondary line unchanged: 280 → 3.07, report-only, can't pass.
- Update §7, C-8 and the HANDOFF bar table.

**V2. Close the last fill-status leak in `select_mask`.**
- The final fallback `prior = arr[mk]` (all prior scored setups, fills known or not) reintroduces the
  R5 leak. Delete it.
- Fallback chain becomes:
  1. trailing-250 with known fills
  2. if that's < 5: **all** prior setups with known fills (any count ≥ 1)
  3. if none: not selected (counted)
- Update §5, and add a test with a prior setup whose fill comes after s; it must never enter any
  fallback.
- Report in the census (counts only) how many setups use each fallback tier.

## Process

1. Same branch and worktree (`research/sniper-filter-2026-10`, `idx-walkforward-sniperfilter`).
2. Add `PREDECLARATION.md` §12 "Revision 2", listing V1–V2 and the Revision-1 sidecar hash
   @ `b3dd0bc`.
3. Re-run the synthetic dry run (fake R only) and the counts-only census.
4. Run all tests, regenerate the sidecar, update `HANDOFF_G0.md`, push, verify with `ls-remote`, and
   **STOP** for the owner's G1 approval.

No outcome may be read. No registry or DECISION_LOG edits. Production untouched. No force-push.
