# Evidence — P0.E2.S3.T3

**Date:** 2026-07-30
**Trace tag:** [L-5]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Verification (before coding)

- `docs/PLAN-001-Implementation-Master-Plan.md` §3, line 83: "T3:
  calendar-year-missing alarm `[L-5]`" — confirms this is the correct
  task.
- `docs/EXEC-STATUS.md` §7 "Next up", item 1: `P0.E2.S3.T3` — confirmed
  still next.
- `git log --oneline -5` showed `P0.E2.S3.T2` (`9622e86`) as `HEAD`, no
  intervening work; `git status` showed no `p0/e2-s3-t3-*` branch and no
  stray uncommitted work touching `engine/calendar_filter.py` or
  `scheduler/`. No discrepancy found.
- The pre-existing scaffold at `docs/evidence/P0/P0.E2.S3.T3/TASK-CARD.md`
  independently confirms scope: "Calendar-year-missing alarm
  (next-year-December class); trading calendar ownership itself moves
  under Clock in Phase 1 — this is the minimal alarm only." — matches the
  design implemented here exactly; no redesign of calendar ownership
  attempted.
- Traced `[L-5]` to the original audit:
  `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 309: "**L-5:**
  Calendar hardcoded through 2026 only — from 2027-01-01 every weekday is
  a 'trading day' and no blackouts exist. Known maintenance item; worth
  an automated 'calendar year missing' alarm in December."

## Root-cause analysis

**Why the audit flagged this:** `engine/calendar_filter.py`'s IDX market
holiday data (`IDX_MARKET_HOLIDAYS_2024/2025/2026`) and BI Rate/FOMC
meeting dates (`BI_RATE_DATES_2026`, `FOMC_DATES_2026`) are hand-curated,
sourced from official government/exchange publications each year — they
cannot be derived programmatically (public holidays and central-bank
meeting schedules are set by human decision, not computed). Read the
full module before changing anything: `_MARKET_HOLIDAYS` (used by
`is_trading_day()`) and `_BLACKOUT` (used by `is_blackout_day()`, built
from `BI_RATE_DATES_2026` + `FOMC_DATES_2026` + the currently-empty
`OTHER_BLACKOUT_DATES`) are both built once at import time from these
year-scoped dicts, with no entries beyond 2026.

**Every code path that can trigger a missing-calendar-year condition:**
- `is_trading_day(check_date)` (`engine/calendar_filter.py:229`): weekday
  check (`weekday() >= 5`) is date-arithmetic and remains correct beyond
  2026; the *holiday* check (`check_date in _MARKET_HOLIDAYS`) has zero
  entries for any date `>= 2027-01-01`, so every 2027+ weekday resolves
  `(True, "trading day")` even on an actual Indonesian public holiday.
- `is_blackout_day(check_date)` (line 240): same shape — zero `_BLACKOUT`
  entries for 2027+, so BI Rate/FOMC entry-blackout protection silently
  stops applying the moment the calendar year rolls over.
- Every caller of either function inherits the gap silently: `main()`'s
  own `_holiday_skip()` wrapper (`scheduler/jobs.py:37`, used by nearly
  every scheduled job) would stop skipping on real holidays; entry-signal
  code consulting `is_blackout_day()` would stop suppressing new entries
  around BI/FOMC dates. No exception is raised anywhere — the failure is
  a value that looks legitimate but is wrong, not a crash.

**Whether existing logging/monitoring already covers part of this:**
checked — nothing does. `is_trading_day()`/`is_blackout_day()` have no
internal logging of their own (by design, they're pure lookups); no
scheduled job logs "checked this date against N years of calendar data";
no existing alert fires on calendar staleness. This audit item was
entirely uncovered before this task, confirming the task is additive, not
duplicative of existing coverage.

**Scope boundary (matches the task card's own wording, not invented
here):** this task adds an *alarm*, not a fix. The calendar gap itself
cannot be closed by code — a human must research and add next year's
official holiday/meeting dates. Actually restructuring calendar ownership
(a versioned `Clock`/calendar service) is explicitly Phase 1 scope per
the task card ("trading calendar ownership itself moves under Clock in
Phase 1") and is not touched here.

## Design decisions

**1. What to check.** The audit's sentence covers two structures
(`_MARKET_HOLIDAYS` for holidays, `_BLACKOUT`/`_ALL_EVENTS` for BI/FOMC
blackouts) that live in the same file, right next to each other, and are
maintained together as one annual ritual (three adjacent, similarly-named
dict blocks: `IDX_MARKET_HOLIDAYS_20XX`, `BI_RATE_DATES_20XX`,
`FOMC_DATES_20XX`). Checking `_MARKET_HOLIDAYS` coverage alone — the
higher-blast-radius one, since `is_trading_day()` gates nearly every
scheduled job via `_holiday_skip()`, versus `is_blackout_day()`'s
narrower entry-suppression use — is a sufficient, minimal proxy for "has
the calendar been updated for next year," and the alarm message
explicitly also names the BI/FOMC dicts so a maintainer fixing the
reported gap naturally updates all three together. Building three
independent checks was considered and rejected as disproportionate to a
"Trivial-Low" severity, "minimal alarm" task.

**2. When to check.** The audit's own wording ("alarm in December")
was taken literally: `check_calendar_year_coverage()` returns `None`
outside December regardless of next year's coverage state — alarming in,
say, March that next year isn't ready 9 months early would be noise, not
signal. The December gate is part of the function's own semantics (unit-
tested), not left to the caller/scheduler to enforce.

**3. Where the logic lives.** The pure check (`check_calendar_year_coverage`)
lives in `engine/calendar_filter.py` — the file that already owns every
other piece of calendar logic (`is_trading_day`, `is_blackout_day`,
`get_upcoming_events`) — reusing that module rather than duplicating
calendar-shape knowledge elsewhere. The scheduled job
(`run_calendar_coverage_check`) lives in `scheduler/jobs.py`, alongside
`run_scheduler_heartbeat` — the file's other "system self-check, not a
market signal" job — and is registered via `scheduler.add_job(...)` in
`scheduler/__init__.py`, the exact same registration pattern used by
every other job in this file (no new infrastructure).

**4. Duplicate-alarm prevention.** `run_calendar_coverage_check` is
registered with `CronTrigger(month=12, hour=9, minute=0, timezone=WIB)` —
fires once per day, only in December, matching the cadence of the file's
other single-daily-time jobs (e.g. `market_health_report`'s
`hour=8, minute=45`). That daily cadence is itself the duplicate-
prevention mechanism: nothing in this design can fire the alarm more than
once per scheduled invocation, and up to 31 invocations/year only if the
gap is genuinely left unaddressed through all of December. Persisting
cross-day "already alerted this year" state (a DB row, a sentinel file)
was considered and rejected: it would be new stateful infrastructure for
a "Trivial-Low" audit item explicitly scoped as "minimal," and
`utils.telegram.send_telegram` already has its own built-in rate limiter
(`_MIN_INTERVAL` between sends) as a further backstop against any
runaway-call scenario, independent of this task's own design. A daily
reminder for a known, unresolved, low-severity maintenance gap is
standard alerting practice, not spam.

**5. Does not call `_holiday_skip()`.** Every other scheduled job in
`scheduler/jobs.py` skips on non-trading days via `_holiday_skip()`
(which itself calls `is_trading_day()`). This job deliberately does not
— it must still fire on weekends and December holidays, because the
alarm is about the calendar *data's* completeness, not about market
activity. Gating a calendar-completeness alarm on the very calendar data
whose completeness is in question would also be circular for any future
year where `_holiday_skip()` itself might be affected by a gap.

## Implementation

- **`engine/calendar_filter.py`**: new `check_calendar_year_coverage(today: date = None) -> str | None`
  — pure function, no side effects, no I/O. Module docstring extended
  with one paragraph pointing at the new function and the job that calls
  it (documentation-consistency, not a functional change).
- **`scheduler/jobs.py`**: new `run_calendar_coverage_check()` — calls the
  above, logs a warning and sends one Telegram message if it returns
  non-`None`, wrapped in `try/except Exception` matching every other
  job's "never let this crash the scheduler" convention (see
  `run_scheduler_heartbeat`, the adjacent job, for the same shape).
- **`scheduler/__init__.py`**: `run_calendar_coverage_check` added to the
  existing `from scheduler.jobs import (...)` re-export block; registered
  via one `scheduler.add_job(...)` call, same pattern as the other ~20
  jobs in this file.

**No existing runtime behavior changed.** `is_trading_day()`,
`is_blackout_day()`, `_MARKET_HOLIDAYS`, `_BLACKOUT`, and every other
pre-existing function/constant in `calendar_filter.py` are untouched —
confirmed by regression tests below.

## Tests

New `tests/test_calendar_coverage_alarm.py`, 13 tests:

**`check_calendar_year_coverage()` (pure function):**
- `test_no_alarm_outside_december` — normal operation (2 cases).
- `test_no_alarm_in_december_when_next_year_present` — normal operation,
  December 2025 checking 2026 (which exists in this repo's real data).
- `test_alarm_in_december_when_next_year_missing` — **the missing-
  calendar-year case the audit describes**: December 2026 checking 2027
  (which genuinely does not exist in this repo's real data — confirmed
  by direct inspection of `engine/calendar_filter.py` before writing any
  code, not assumed).
- `test_alarm_message_names_the_missing_dict` — the alarm is actionable
  (names `IDX_MARKET_HOLIDAYS_2027`), not just "something is wrong."
- `test_check_is_deterministic_same_input_same_output` — duplicate-alarm-
  prevention control: pure function, same input always same output.
- `test_december_31_still_checks_next_year` / `test_january_1_of_missing_year_no_longer_triggers_this_alarm`
  — boundary cases for the December-only window.

**`run_calendar_coverage_check()` (scheduled job):**
- `test_job_sends_telegram_when_calendar_missing` — end-to-end: mocked
  missing-calendar check → exactly one `send_telegram` call, message
  contains the year.
- `test_job_sends_nothing_when_calendar_present` — false-positive /
  duplicate-alarm-prevention control: mocked `None` → zero Telegram
  calls.
- `test_job_sends_at_most_one_message_per_invocation` — duplicate-alarm-
  prevention: no loop/retry in the job body that could fire more than one
  alert per scheduled run.
- `test_job_does_not_crash_scheduler_on_unexpected_error` — startup/
  runtime-edge-case control: a simulated exception inside the check is
  caught and logged, not raised, matching every other job's convention.

**Regression (existing calendar behavior unaffected):**
- `test_existing_2026_holiday_detection_unaffected` — New Year's Day 2026
  still correctly detected as a non-trading day.
- `test_existing_2026_trading_day_unaffected` — an ordinary 2026 weekday
  still resolves as a trading day.

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_calendar_coverage_alarm.py -v'
```
```
collected 13 items
tests/test_calendar_coverage_alarm.py .............                      [100%]
13 passed in 0.52s
```

**Real-world confirmation (not just mocked):** ran the actual function
against this repo's real calendar data outside pytest:
```
Dec 2026 (missing 2027): IDX market holiday calendar for 2027 is not populated (add IDX_MARKET_HOLIDAYS_2027 to engine/calendar_filter.py). From 2027-01-01, is_trading_day() will treat every weekday as a trading day with no holidays, and BI Rate/FOMC blackout windows for 2027 will not exist either until BI_RATE_DATES_2027/FOMC_DATES_2027 are added in the same update.
Jun 2026 (not December): None
```

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1300 passed, 1 skipped in 25.15s
```
Baseline (post-`P0.E2.S3.T2`) was 1,287 passed/1 skipped/0 failed; +13
from `test_calendar_coverage_alarm.py`. 0 regressions, 0 failures.
Targeted subset run first: `tests/test_calendar_coverage_alarm.py
tests/test_scanner_freshness_guard.py tests/test_scanner_vpin_gate.py
tests/test_scheduler_risk_alert_registration.py` (this task's own tests
plus every existing test that exercises `is_trading_day`/`is_blackout_day`
indirectly) — 38 passed, run before the full suite.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1300 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 38 clean, 0 violations, 0 allowlisted (run_calendar_coverage_check confirmed registered)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```
AN-8 candidate count rose from 37 to 38 (the new job), still 0
allowlisted/0 unregistered — this task did not introduce a new
unregistered-capability defect, verified directly rather than assumed.

## Decision entries filed

None. No `§8`-classifiable event — five design choices were made (what
to check, when to check, where the logic lives, duplicate-alarm
prevention, not calling `_holiday_skip`), all documented above under
"Design decisions" rather than filed as numbered `IMPL-DEC` entries,
consistent with the threshold used for `P0.E2.S2.T2`/`P0.E2.S3.T1`/
`P0.E2.S3.T2`: reasoned scope boundaries within a single task's
implementation, not architectural or governance decisions in the §8
sense.

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: one new pure function, one new
  job function, one new job registration, one new test file, one
  docstring addition. No drive-by changes — `is_trading_day`,
  `is_blackout_day`, every other job in `scheduler/jobs.py`, and every
  other registration in `scheduler/__init__.py` are untouched.
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency (ER-12) — `send_telegram`, `logging`,
  `scheduler.add_job`, `CronTrigger` are all already in active use.
- No forward-phase work smuggled in (ER-2): did not build a versioned
  Clock/calendar service, did not restructure calendar ownership — both
  explicitly Phase 1 per the task card's own wording, left untouched.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S3.T3 ... [L-5]`).

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, against the
operator's explicit checklist:

- **Silent failure paths:** the job's own `try/except Exception` means a
  bug in the alarm mechanism itself fails silently (logged, not
  escalated) — but this exactly matches the established convention for
  every job in this file (`run_scheduler_heartbeat`'s identical
  "never let this crash the scheduler" shape); deviating from it here
  would be new, inconsistent behavior, not a fix. Accepted as a
  convention-match, not a defect.
- **Alarm spam:** bounded to at most one Telegram message per day, only
  in December, via `CronTrigger(month=12, hour=9, minute=0)` — the same
  single-daily-time cadence used by other jobs in this file; `send_telegram`'s
  own built-in rate limiter is a further, independent backstop. Not spam
  by any reasonable definition of the term.
- **False positives:** the check can only fire when `today.month == 12`
  AND no `_MARKET_HOLIDAYS` entry exists for `today.year + 1` — both
  conditions independently verified against this repo's real calendar
  data (December 2025→2026 correctly silent; December 2026→2027
  correctly alarms). The flip-side risk — the check goes silent the
  moment even one placeholder date is added for next year, before the
  full year is actually complete — is a real, accepted scope boundary
  (documented above under "Design decisions" point 1), not a bug: a
  presence check is the minimal, proportionate signal for a Trivial-Low
  severity task; a full-year-completeness check would be
  disproportionate scope.
- **Startup edge cases:** confirmed via direct import
  (`from scheduler import start_scheduler, run_calendar_coverage_check`)
  outside pytest — no import-time error, no circular import, no crash.
  `scheduler.add_job(...)` only registers a cron entry; it does not
  invoke the job at startup regardless of the current date.
- **Configuration interactions:** `send_telegram` already no-ops
  gracefully when `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` are unset or
  placeholder values (`utils/telegram.py:14-18`, pre-existing, read
  before assuming) — this job introduces no new configuration
  requirement or new failure mode around Telegram credentials.
- **Regression risk:** full suite (1,300/1,287 baseline) and gate both
  clean; two new regression tests directly confirm `is_trading_day()`'s
  pre-existing 2026 holiday/weekday behavior is byte-for-byte unchanged;
  AN-8 audit confirms the new job is properly registered (38 candidates
  checked, 0 unregistered, up from 37 — the delta is exactly this task's
  one new job, not a regression).
- **Documentation consistency:** `engine/calendar_filter.py`'s module
  docstring updated to point at the new function/job (in-file, directly
  related to this change — not the audit report, which remains the
  read-only historical record and is correctly left unedited, same
  treatment as every prior L-series task this cycle).

**0 findings.** No code changes required as a result of this review (the
docstring addition was made proactively during implementation, not as a
review finding).

**Time-gate note:** as with every P0 task this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
