# Task 2B-4 — Health Expansion + Workstream 2B Freeze

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2B, Task 4 of 4 —
final task before the freeze). Builds on the frozen v1 foundation and 2B-1/2B-2/2B-3.

## Health sources audited

- **Database** — `app.py`'s `/health` route checks connectivity inline (`SELECT MAX(scan_time)
  FROM scheduled_signals`, `SELECT COUNT(*) ... paper_trades`), not extracted as a service
  function. Per the same precedent as 2B-2 (`engine/metrics.py`) and 2B-3
  (`engine/config_info.py`) — `app.py` is not touched — a new `engine/health.py` does its own
  minimal connectivity probe (`SELECT 1`, via `data.db.connect`, the one centralized entry
  point) rather than importing from `app.py` (which would also be a circular-import problem:
  `app.py` is the top-level module that imports routes, not something routes import from).
- **Scheduler** — `scheduler.get_scheduler()` (2B-1), reused as-is: `available` + `.state`.
- **Metrics** — `engine.metrics.get_engine_metrics()` (2B-2), reused as-is: success/failure of
  the call itself is the signal, no new metric interpretation.
- **Configuration** — `engine.config_info.get_config_summary()` /
  `get_runtime_config()` (2B-3), reused as-is: success/failure of the calls is the signal.
- **Release** — `utils.release.release_info()`, already used by `/health` and by 2B-3's
  `/api/v1/config`; informational only (no pass/fail — a version number can't be "unhealthy").
- **Omitted, with reason:** `event_guard`/`macro_panic_state` (from `scheduler.scanner`, used
  by `/health` today) — these are trading-state signals, not operational/infrastructure health;
  Production Status Registry (`engine.job_status`) is deliberately **not** re-aggregated here
  a second time — its own detail already lives at `/api/v1/status/*`, and metrics already
  reflects job-execution health via `/api/v1/metrics/jobs`; adding a third view of the same
  data would be redundant, not a new health signal.

## Aggregation rules (deterministic, no scores)

Three states per component: `healthy` | `degraded` | `unavailable`. Rules:

- **database**: `healthy` if a trivial query succeeds against the configured DB;
  `unavailable` if the connection or query raises. (No `degraded` state for a binary
  connectivity probe.)
- **scheduler**: `healthy` if `get_scheduler()` returns an instance in `state == "running"`;
  `degraded` if an instance exists but isn't running (`paused`/`stopped`/`unknown`);
  `unavailable` if `get_scheduler()` is `None`.
- **metrics**: `healthy` if `get_engine_metrics()` returns without raising; `unavailable` if it
  raises. (No degraded state — the underlying values aren't evaluated, only reachability,
  since 2B-2 already owns interpreting the values themselves.)
- **configuration**: `healthy` if both `get_config_summary()` and `get_runtime_config()` return
  without raising; `unavailable` if either raises.
- **release**: informational only, no status.

**Overall** (strictly derived from the above, no independent judgment):
- `unavailable` if `database` is `unavailable` (every other subsystem depends on the same DB).
- else `degraded` if any of `scheduler`/`metrics`/`configuration` is not `healthy`.
- else `healthy`.

## Endpoint

`GET /api/v1/health` — `VIEWER`. Response shape matches the brief's suggested structure
exactly (`overall`, `components.{database,scheduler,metrics,configuration}.status`,
`components.release.{version,git_sha?}`).

## Workstream 2B freeze

Once 2B-4 lands, all four Operational API groups (`/api/v1/scheduler*`, `/api/v1/metrics*`,
`/api/v1/config*`, `/api/v1/health`) are audited for contract consistency (envelope, error
handling, `VIEWER` auth, OpenAPI registration, `meta` shape) and Workstream 2B is marked
frozen — no further additions without a new, explicit task, same discipline as Phase 2A.
