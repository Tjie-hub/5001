# Workstream 2B — Operational APIs: FROZEN

**Status:** FROZEN 2026-08-06. Production Engine Phase 2, Workstream 2B (Operational APIs) is
complete. Built on the frozen Phase 2A API Foundation
(`docs/superpowers/specs/2026-08-06-api-v1-foundation-design.md`); no further additions to
this surface without a new, explicit task, same discipline as Phase 2A's freeze.

## Endpoint inventory

| Endpoint | Method | Auth | Task | Backing service |
|---|---|---|---|---|
| `/api/v1/scheduler` | GET | VIEWER | 2B-1 | `scheduler.get_scheduler()` |
| `/api/v1/scheduler/jobs` | GET | VIEWER | 2B-1 | `scheduler.get_scheduler()` + `engine.job_status` |
| `/api/v1/scheduler/jobs/<job_id>` | GET | VIEWER | 2B-1 | same, single job |
| `/api/v1/metrics` | GET | VIEWER | 2B-2 | rollup of the three below |
| `/api/v1/metrics/jobs` | GET | VIEWER | 2B-2 | `engine.job_status.get_status_summary()` |
| `/api/v1/metrics/engine` | GET | VIEWER | 2B-2 | `engine.metrics.get_engine_metrics()` |
| `/api/v1/config` | GET | VIEWER | 2B-3 | `engine.config_info.get_config_summary()` |
| `/api/v1/config/runtime` | GET | VIEWER | 2B-3 | `engine.config_info.get_runtime_config()` |
| `/api/v1/health` | GET | VIEWER | 2B-4 | `engine.health.get_health()` |

9 endpoints, all `GET`-only, all `VIEWER`. Verified programmatically as a single set by
`tests/test_v1_operational_apis_freeze.py` — the freeze checkpoint test: if a future change to
any endpoint above breaks that file, it has broken the frozen contract.

## Contract consistency (verified, not just declared)

- **Response envelope** — every endpoint returns `{"ok": true, "data": {...}, "meta": {...}}`
  via `routes/v1/envelope.py::ok()`; nothing here writes its own response shape.
- **Error handling** — every endpoint shares `api_v1_bp`'s error handlers (`ApiError` +
  framework 400/401/403/404/405/500), so an unmatched path under any of these prefixes gets the
  same `{"ok": false, "error": {"code": "NOT_FOUND", ...}}` shape, not a per-endpoint one-off.
- **Authorization** — all nine `security/route_policy.py` entries are `VIEWER`; none needed a
  higher tier (nothing here is state-changing, and nothing surfaced during any of the four
  audits was sensitive enough to warrant inventing a new role, per each task's own instruction
  not to).
- **Request metadata** — every response's `meta` carries `api_version: "v1"`, a `request_id`
  (reused from `g.correlation_id` when present), and a UTC ISO-8601 `timestamp` — the same
  `_meta()` call in every case, not reimplemented per endpoint.
- **OpenAPI registration** — all nine documented in `routes/v1/openapi.py`'s `_PATHS`, verified
  present (with a `get` entry) via `/api/v1/openapi.json` itself in the freeze test.

## No new engine logic introduced across all of 2B

Every field, status, and metric traces back to something that already existed before Workstream
2B started, reused rather than reinvented:

- 2B-1 added exactly one piece of new plumbing: `scheduler.get_scheduler()`, a getter for an
  object (`start_scheduler()`'s return value) that already existed but was unreachable —
  zero change to scheduling behavior.
- 2B-2 added `engine/metrics.py`, extracting `app.py`'s pre-existing Prometheus query set into
  a callable service (that route itself untouched); no new metric was computed that wasn't
  already being computed somewhere.
- 2B-3 added `config.sectors_app_mode()`, mirroring the pre-existing `edge_mode()` getter
  exactly, plus a strict allowlist over already-existing config accessors — no new env reads,
  and an explicit exclusion list for every credential-shaped value.
- 2B-4 added `engine/health.py`, a pure aggregation over 2B-1/2B-2/2B-3's own signals (plus a
  minimal DB connectivity probe via the already-centralized `data.db.connect`) — no new health
  probes, deterministic three-state rule, no scoring.

## Deterministic aggregation rule (2B-4, restated for the record)

Per-component: `healthy` | `degraded` | `unavailable` (database has no degraded state — a
connectivity check is binary; metrics/configuration likewise, since only reachability of an
already-owned service is being checked, not its values). Overall: `unavailable` if database is
unavailable; else `degraded` if any of scheduler/metrics/configuration isn't `healthy`; else
`healthy`. `release` is informational only, no status.

## Ready for Phase 2C

Workstream 2B's exit criteria (scheduler/metrics/config/health APIs complete, consistent
contract, OpenAPI complete, formally frozen) are met. Phase 2C (Business APIs) can begin as its
own spec→plan cycle, same as 2A→2B.
