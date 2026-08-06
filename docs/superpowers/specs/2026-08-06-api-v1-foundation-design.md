# API v1 Foundation — Workstream A, Task 1

**Status:** Approved 2026-08-06 (Production Engine Phase 2 kickoff, Workstream A of 4;
B/C/D are separate future spec→plan cycles, not started).

## Scope

Minimal, proven scaffold — not the full generic toolkit described in the original Phase 2
brief. Pagination/filtering/richer validation are deferred until a real Workstream B/C
endpoint needs them (YAGNI); nothing is currently blocked on this, so the first slice is
kept to what one real migrated endpoint set (PSR) actually exercises.

## Architecture

```
Route (routes/v1/*.py, thin controllers)
    ↓
Service (engine/job_status.py — unchanged)
    ↓
Engine / DB (data/db.py — unchanged)
```

- New `routes/v1/` package, one blueprint `api_v1_bp` mounted at `/api/v1`.
- `routes/status.py` (`status_bp`, shipped this morning as the PSR HTTP API) is migrated
  into `routes/v1/status.py` under `/api/v1/status/*`. The old `/api/status/*` blueprint
  and its `security/route_policy.py` entries are deleted outright — no consumers exist yet
  (verified: no frontend/JS references), so no compatibility shim is needed.
- Auth/authz unchanged: `security/auth.py` (token/role model, `AUTH_MODE` off/shadow/enforce)
  and `security/route_policy.py` (URL-rule → role, fail-closed to ADMIN) are reused as-is.
  New v1 routes get entries in the same `POLICY` dict. No new auth mechanism.

## Components

- `routes/v1/__init__.py` — blueprint definition, `register(app)` helper.
- `routes/v1/envelope.py` — `ok(data)` / `err(code, message, details=None)` envelope
  builders; `ApiError(code, http_status, message, details=None)` exception; blueprint-level
  `errorhandler`s (400/401/403/404/405/500 + `ApiError`) so controllers stay thin.
- `routes/v1/status.py` — the 5 PSR endpoints, reimplemented as controllers over the
  unchanged `engine.job_status` service layer.
- `routes/v1/openapi.py` — assembles an OpenAPI spec from the v1 routes and serves it.
- `tests/test_v1_envelope.py`, `tests/test_v1_status_routes.py` — flat, matching the
  existing `tests/test_*.py` convention (there is no `tests/routes/` package).

## Response envelope

Success:
```json
{"ok": true, "data": {...}, "meta": {"api_version": "v1", "request_id": "...", "timestamp": "..."}}
```
Error:
```json
{"ok": false, "error": {"code": "NOT_FOUND", "message": "...", "details": {}}, "meta": {...}}
```
- `meta.timestamp` — UTC ISO-8601 (`datetime.now(timezone.utc).isoformat()`), generated
  fresh per response.
- `meta.request_id` — reuses `g.correlation_id`, the correlation ID already assigned by
  `app.py`'s `before_request` hook (`X-Request-ID` header if the caller sent one, else a
  fresh `uuid4`). Falls back to generating a `uuid4` only if `g.correlation_id` is absent
  (e.g. a route invoked outside the normal app request cycle, such as a test that registers
  only the v1 blueprint without app.py's `before_request` hook).
- HTTP status codes remain semantically correct (200/4xx/5xx) — the envelope standardizes
  the body shape, it does not replace status codes.

## New endpoints

- `GET /api/v1/` — API root: `{"name": "idx-walkforward-5001 API", "version": "v1",
  "status": "ok"}` via the standard envelope. Route policy: `VIEWER` (consistent with other
  informational endpoints like `/api/status/summary` today; `/health` is the only `PUBLIC`
  liveness probe and stays separate/unversioned).
- `GET /api/v1/openapi.json` — assembled OpenAPI spec. Route policy: `VIEWER` (per explicit
  instruction — not `PUBLIC`).

## Error handling

Controllers raise `ApiError(code, http_status, message, details=None)` for expected failure
cases (e.g. bad `limit` query param); the blueprint's `errorhandler(ApiError)` formats it
into the error envelope at the given status. Framework-level errors (404 on an unmatched v1
route, 405 on a wrong method, uncaught 500) get their own blueprint-level `errorhandler`s so
every response under `/api/v1/*` shares the one envelope shape — including ones the
controller never touches. This does not change `app.py`'s existing top-level 404/500
handlers for non-v1 routes.

## Testing

- TDD: tests written and watched to fail before each piece of implementation.
- Hermetic — temp SQLite via `monkeypatch`, matching `tests/test_status_routes.py`'s
  existing fixture pattern (temp DB path, reload `config`/`engine.job_status`/the route
  module, register only the blueprint under test).
- `tests/test_status_routes.py` is deleted once its coverage is fully ported to
  `tests/test_v1_status_routes.py` (no legacy routes left for it to exercise).
- Full `pytest -q` run before commit.

## Explicitly out of scope for this task

Pagination, filtering, request-body validation beyond what PSR's `limit`/`since` query
params already need, a central multi-blueprint router beyond `app.py`'s existing
`register_blueprint` calls, and any Workstream B/C/D endpoint. These are deferred to their
own spec→plan cycles once a real consumer needs them.
