# Phase 2 — API Layer: FROZEN

**Status:** FROZEN 2026-08-06. The Production Engine's `/api/v1` API Layer (Phase 2 in full —
Workstream A/2A Foundation, 2B Operational APIs, 2C Business APIs, 2D Integration APIs) is
complete. No further additions to `/api/v1` without a new, explicit task; no change to any
existing contract without a documented critical defect (per every workstream's own "Foundation"
constraint, now applying to the whole layer).

## Full `/api/v1` inventory — 33 endpoints, one blueprint (`api_v1_bp`), all `GET`, all `VIEWER`

| Group | Endpoints | Workstream |
|---|---|---|
| Foundation | `/`, `/openapi.json` | A / 2A |
| Status (PSR) | `/status/jobs/running`, `/status/jobs/latest`, `/status/jobs/failed`, `/status/jobs/history`, `/status/summary` | A / 2A |
| Scheduler | `/scheduler`, `/scheduler/jobs`, `/scheduler/jobs/<job_id>` | 2B-1 |
| Metrics | `/metrics`, `/metrics/jobs`, `/metrics/engine` | 2B-2 |
| Config | `/config`, `/config/runtime` | 2B-3 |
| Health | `/health` | 2B-4 |
| Watchlists | `/watchlists/current`, `/watchlists/history`, `/watchlists/<date>`, `/watchlists/diff`, `/watchlists/persistent` | 2C-1 |
| Snapshots | `/snapshots`, `/snapshots/<date>` | 2C-2 |
| Reports | `/reports`, `/reports/<date>` | 2C-3 |
| Candidates | `/candidates`, `/candidates/<date>`, `/candidates/screening`, `/candidates/reversal-watchlist`, `/candidates/premover-watchlist` | 2C-4 |
| Platform | `/version`, `/capabilities`, `/resources` | 2D |

Verified as one exact set — no drift, no gaps — by `tests/test_phase2_api_freeze.py`: the real
`url_map` matches this table exactly (`TestEveryV1RouteIsRegisteredExactlyOnce`), every route's
`security/route_policy.py` classification matches (`TestEveryV1RouteHasTheExpectedAuthorization`
— and confirms **zero** `/api/v1` routes are `PUBLIC`, unlike legacy `/health`), and the
OpenAPI spec's path set is identical to the real route set with no stale or missing entries
(`TestEveryV1EndpointDocumented`) — closing one gap found during this freeze: `/api/v1/
openapi.json` didn't document itself until now.

## Contract, verified whole-surface (not just per-workstream)

- **Response envelope** — `{"ok": true, "data": {...}, "meta": {...}}` on success,
  `{"ok": false, "error": {"code", "message", "details"}, "meta": {...}}` on error, for every
  one of the 33 endpoints, via the single `routes/v1/envelope.py::ok()`/`ApiError` pair from
  Workstream A Task 1 — never reimplemented.
- **Error handling** — one blueprint, one set of error handlers; an unmatched path anywhere
  under `/api/v1` gets the identical `404 NOT_FOUND` envelope.
- **Authorization** — 33/33 `VIEWER`. Nothing in the whole layer needed a stronger tier; nothing
  needed weaker than `VIEWER` either (confirmed: no `PUBLIC` v1 routes, by design distinct from
  legacy `/health`).
- **Request metadata** — `meta.api_version == "v1"`, `meta.request_id`, `meta.timestamp` (UTC
  ISO-8601) on every response, success or error.
- **OpenAPI** — 33/33 documented, spec content verified to exactly match the live route table.

## What Phase 2 did *not* do (by design, verified across every workstream)

- **No business logic was ever added.** Every field in every response traces to a function that
  already existed before its task began — a read, an aggregate `SELECT`/`GROUP BY`, or (in
  three cases across the whole layer — `scheduler.get_scheduler()` 2B-1, `config
  .sectors_app_mode()` 2B-3, and relocating — not duplicating — the legacy reversal-route
  branching into `screener.reversal_filter.get_current_watchlist()` 2C-4) a minimal getter for
  something that already existed but was unreachable.
- **No writer was ever touched.** `record_snapshot`, `diff_watchlist`, `diff_snapshot`,
  `update_watchlist`, `scan_reversals`, `get_watchlist`'s detection/scoring, every scheduler
  job's own logic, every forward-testing writer — all byte-identical to before Phase 2 started.
- **No storage was introduced.** Every endpoint reads a table or file that already existed with
  a real writer already in production.
- **Two designed endpoints were deliberately dropped, not shipped half-right:**
  `/api/v1/snapshots/history` (2C-2, redundant with `/snapshots` itself) and
  `/api/v1/candidates/diff` (2C-4, structurally impossible to drive from persisted data alone
  without duplicating `diff_snapshot`'s comparison algorithm) — both caught and documented
  before implementation, not shipped and later regretted.
- **One legacy migration was resolved by evidence, not assumption:** 2C-4's consumer audit
  found `GET /api/screener/results` has a real frontend consumer and kept it; found
  `GET /api/screener/reversal` and `GET /api/premover/watchlist` had none and removed them.

## Ready for Phase 3/4/5

Per Phase 2D's integration audit: every *current* consumer (Agent Firm, Scheduler) is in-process
and was never blocked on this layer; Telegram and deploy tooling use orthogonal channels left
untouched. `/api/v1/version`, `/api/v1/capabilities`, and `/api/v1/resources` are the concrete
discovery surface Phase 3 (PWA Dashboard), Phase 4 (Research Engine), and Phase 5 (Agent Firm
externalization, if it happens) can build against without reading source or this document first.
