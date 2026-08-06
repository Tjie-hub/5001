# Task 2B-1 — Scheduler APIs

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2B — Operational
APIs; Task 1 of 4). Builds on the frozen API v1 foundation
(`docs/superpowers/specs/2026-08-06-api-v1-foundation-design.md`) — no changes to routing,
envelope, `ApiError`, or auth conventions.

## Gap found before implementing

`GET /api/v1/scheduler/jobs` needs "next run" / "enabled-disabled" / a true registered-jobs
list — none of that exists in `engine.job_status`'s `job_execution_log` table (execution
*history* only, no schedule/trigger state). Only the live `BackgroundScheduler` instance has
it (`job.next_run_time`, `job.trigger`). But `start_scheduler()` returns that instance and
every caller discards the return value (`app.py`'s `__main__` block, `gunicorn.conf.py`'s
`post_worker_init` hook) — nothing makes it reachable from a request handler.

**Decision (user-approved):** add a minimal module-level getter to `scheduler/__init__.py`:
a `_scheduler_instance` global set inside `start_scheduler()` right before it returns (same
object, same call site — zero behavior change to scheduling itself), plus
`get_scheduler() -> BackgroundScheduler | None`. `None` before `start_scheduler()` has run in
the current process (e.g. under pytest, or a request that lands before `init_runtime()`
completes) — the API degrades gracefully rather than erroring (fail-soft, matching the
existing registry-loader/metrics posture in this repo).

## Testing note

`tests/test_scheduler_corporate_actions_registration.py` (and its siblings) explicitly never
call the real `start_scheduler()` — comment: *"start_scheduler() is never invoked directly
anywhere in this suite"* — it's source-inspection style, presumably to avoid spinning up the
real ~20-job production cron table as a live background thread inside pytest. Task 2B-1's
tests follow the same discipline: they build a small local `BackgroundScheduler` with 1-2
throwaway jobs and monkeypatch `scheduler.get_scheduler` to return it, never touching
`scheduler.start_scheduler()`.

## Endpoints

- `GET /api/v1/scheduler` — `{"available": bool, "state": "running"|"paused"|"stopped"|
  "unavailable", "timezone": str|null, "job_count": int}`.
- `GET /api/v1/scheduler/jobs` — `{"jobs": [...], "count": int}`. Each job:
  `{"job_id", "name", "trigger" (str(job.trigger)), "next_run_time" (ISO-8601 or null),
  "paused" (next_run_time is None), "last_run"}`. `last_run` is the matching row from
  `engine.job_status.get_latest_job_status()` (already exists, already used by
  `/api/v1/status/jobs/latest`) joined on `job_name == job.id` — per `_add_job`'s own
  docstring, `job_name` in `job_execution_log` *is* the APScheduler job id, so this join is
  exact, not a heuristic. `null` if the job has never run.
- `GET /api/v1/scheduler/jobs/<job_id>` — single job in the same shape; `ApiError("JOB_NOT_FOUND", 404, ...)` if unmatched.
- All three: `VIEWER`, matching `/api/v1/status/*`.

## Explicitly out of scope

Pausing/resuming/triggering a job (write operations — not requested, and this workstream is
read-only operational visibility only), and any change to which jobs are registered or when
they run.
