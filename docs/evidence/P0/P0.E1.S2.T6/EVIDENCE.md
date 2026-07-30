# Evidence — P0.E1.S2.T6

**Date:** 2026-07-30
**Trace tag:** [AN-8, DEBT-003, new finding via P0.E1.S2.T4]

## Investigation

`run_vpin_backfill(days=90)` (`scheduler/jobs.py:894`) backfills `vpin_scores` for
tickers/dates that `daily_screen` has data for but `vpin_scores` doesn't yet.
Compared against its sibling `run_vpin_daily_batch` (registered, 18:00 WIB
daily) to decide register vs. delete vs. manual/CLI-only, per the same
methodology T1–T3 used for the Audit's original 6 findings:

- **Not superseded.** `run_vpin_daily_batch` only ever computes VPIN for
  "today" (or an explicit `date_str`); it has no retroactive gap-fill logic.
  `run_vpin_backfill` is the only code path that can heal a gap left by a
  daily-batch failure, a scheduler outage, or a day VPIN scoring didn't exist
  yet for. Deleting it would remove real, non-duplicated capability.
- **Cheap to run on a schedule.** It is idempotent by construction — per
  date it first computes `already = {tickers with vpin_scores row}` and
  skips entirely (`continue`) once every ticker for that date is covered.
  With the daily batch running normally, a scheduled backfill pass is a
  fast set of `SELECT` no-ops on every run; it only does real work when a
  gap actually exists.
- **Matches an established pattern in this codebase.** `run_ohlcv_reconciliation`
  (21:00 WIB) and `run_ohlcv_coverage_check` (17:00 WIB) are both daily,
  mon-fri, self-healing/reconciliation-style jobs scheduled shortly after
  their data source — not weekly, not manual-only. `run_vpin_backfill` is
  the same shape of job for VPIN coverage instead of OHLCV coverage.

**Disposition: register**, daily mon-fri at **18:15 WIB** — 15 minutes after
`run_vpin_daily_batch` (18:00), the same "shortly after its data source"
offset used by the two precedents above.

## Deliverable

- `scheduler/__init__.py` — `scheduler.add_job(run_vpin_backfill, ..., id="vpin_backfill", name="VPIN Backfill 18:15")`, immediately after the `vpin_daily_batch` registration.
- `scripts/audits/an8_unregistered_jobs.py` — `ALLOWLIST` emptied (was `{"run_vpin_backfill": ...}`, citing this task as the follow-up; now dispositioned, entry removed per the original citation's own instruction: "Remove this entry once T6 dispositions it.").
- `tests/test_scheduler_vpin_backfill_registration.py` (new, 3 tests).

## Test output (named tests)

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_scheduler_vpin_backfill_registration.py tests/test_an8_audit.py -v
```
```
============================= test session starts ==============================
collected 9 items

tests/test_scheduler_vpin_backfill_registration.py ...                   [ 33%]
tests/test_an8_audit.py ......                                           [100%]

============================== 9 passed in 0.43s ===============================
```

New tests (`tests/test_scheduler_vpin_backfill_registration.py`, 3), mirroring the idiom `tests/test_scheduler_report_registration.py` established for T3:
- `run_vpin_backfill` is registered at 18:15 WIB, mon-fri.
- It runs after (not before/concurrent with) `run_vpin_daily_batch`, its own data source.
- Its job id is unique (no accidental double-registration).

`tests/test_an8_audit.py::test_real_repo_an8_audit_matches_current_allowlist` (T4's own integration test) re-run unchanged and still passes: with `run_vpin_backfill` now registered, the empty `ALLOWLIST` is exactly right — 37/37 clean, 0 violations, 0 allowlisted.

## Direct audit-script run (before/after)

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/audits/an8_unregistered_jobs.py
```
```
AN-8 audit: 37 candidate(s) clean, 0 violation(s)
...
  [OK]   run_vpin_backfill: registered (scheduler.add_job)
...
AN-8: PASS — zero unwired capabilities
```
Previously (T4 baseline): `run_vpin_backfill: allowlisted — ...`. Now: `registered`. The one previously-allowlisted candidate is now clean the same way every other registered job is — no special-cased exception remains in the audit.

## Regression run (full suite)

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q
```
```
1239 passed, 1 skipped in 21.73s
```
Baseline (branched from `master` after P0.E1.S2.T4) was 1,236 passed/1 skipped/0 failed; +3 from this task's new tests, 0 regressions. (This branch forked before P0.E1.S2.T5 merged, so this run doesn't include T5's 5 tests.)

**Post-reconciliation re-verification (cold review, 2026-07-30):** after merging `master` (with T5 already merged) into this branch and resolving doc conflicts, the full suite was re-run: **1,244 passed, 1 skipped, 0 failed** (1,236 T4 baseline + 5 T5 tests + 3 T6 tests) — confirms T5 and T6 compose cleanly with no interaction effects.

## Gate-script output

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py
```
```
[PASS] QG-1 full test suite — 1239 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted
[PASS] QG-5 evidence presence — 7 done-task cards checked, all have evidence

GATE: PASS
```

## Documentation delta

None required by any `docs/ops/*` checklist (no existing reference to `run_vpin_backfill` or the VPIN backfill job there). The registration itself is visible in `scheduler/__init__.py`'s job list, which is the only place this class of change has ever been documented for T1–T3 either.

## Decision entries filed

- `DEBT-003` — closed. Append-only update recorded in `docs/EXEC-DECISIONS.md` (entry not edited, per §8 rule). Closes on merge, not before (same convention used for DEBT-001/DEBT-002 in P0.E1.S2.T5).

## Verification commands

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_scheduler_vpin_backfill_registration.py -v
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/audits/an8_unregistered_jobs.py
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py
```
