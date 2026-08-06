# Workstream 2D — Integration APIs: Audit + Design

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2D — final workstream of
Phase 2). Builds on the frozen Phase 2A/2B/2C surfaces; no existing contract changes.

## Step 1 — Integration audit

| Consumer | Status | APIs required today | Auth model | Missing integration point |
|---|---|---|---|---|
| **Dashboard** | Planned (Phase 3) | All of 2B/2C (read-only) | VIEWER token, same as everything else | No client-side capability discovery yet — this is exactly what 2D adds |
| **Agent Firm** | Live, but **in-process only** — `scheduler/jobs.py`/`scanner.py` `import engine.agent_firm.firm` and call it directly as a Python library. Confirmed via source scan: no HTTP client code anywhere under `engine/agent_firm/` calling back into this app's own routes. | None (not an HTTP consumer today) | N/A today | Becomes a real HTTP consumer only if/when it's externalized (Phase 5, out of scope now) |
| **Telegram** | Live, but as a **notification channel + inbound webhook**, not an `/api/v1` consumer — outbound via `send_telegram()`, inbound via `/telegram/updates` (its own HMAC secret, unrelated to `AUTH_MODE`/`/api/v1`) | None | Its own webhook secret | None — orthogonal integration surface, not part of this workstream |
| **Scheduler** | Live, in-process cron jobs calling Python functions directly (`engine.trade_plan.record_snapshot`, etc.) | None (not an HTTP consumer of its own app) | N/A | None |
| **Operational tooling** | Live: `scripts/wait_for_health.sh` (used by `scripts/release.sh`'s deploy pipeline) `curl`s the legacy `PUBLIC /health` — confirmed by reading the script. Does **not** use `/api/v1/health` (2B-4, VIEWER-gated) today. | Legacy `/health` today; could migrate to `/api/v1/health` later (not this task — "no existing contracts may change," and the deploy script isn't broken) | None (public) | Documented, not touched |
| **Research Engine** | Future (Phase 4), per CLAUDE.md's own architecture — explicitly isolated from production by the research/production CI boundary (`test_architecture_boundary.py`). Any future HTTP integration would need to respect that boundary; the Business APIs (2C) are the natural read surface for it | Read-only 2C Business APIs | VIEWER token | Not building anything for it now — audit only |
| **Portfolio Engine** | Future, not yet designed anywhere in this codebase | Unknown | Unknown | Nothing to integrate yet |
| **Execution Engine** | Future, not yet designed anywhere in this codebase | Unknown | Unknown | Nothing to integrate yet |

**Finding:** every *current* consumer either doesn't cross an HTTP boundary at all (Agent Firm,
Scheduler), uses a channel orthogonal to `/api/v1` (Telegram), or uses the pre-`/api/v1` legacy
`/health` (deploy tooling) — deliberately left alone. The actual gap 2D closes is **client-side
discoverability for every future consumer**: today, a new consumer (dashboard, research engine,
external tooling) has to read source code or this doc to know what `/api/v1/*` offers. That's
exactly what Step 2/3/4 build.

## Step 2/3/4 — Platform endpoints

`GET /api/v1/` (the root) **already exists** (Workstream A Task 1: `{"name", "version",
"status"}`) and is frozen — not modified here. Three new endpoints cover what it doesn't:

- **`GET /api/v1/version`** — build/release identity. Reuses
  `engine.config_info.get_config_summary()` verbatim (already built for `/api/v1/config`, 2B-3)
  for `version`/`release_source`/`git_sha`/`built_at`, reshaped with an `api_version` field and
  a static `openapi_url` pointer (`/api/v1/openapi.json`) — no new release-reading code.
- **`GET /api/v1/capabilities`** — feature/capability flags. Reuses
  `engine.config_info.get_runtime_config()` verbatim (`auth_mode`, `edge_score_mode`,
  `sectors_app_mode`, `agent_firm_enabled`, `agent_firm_enforce`,
  `agent_firm_governor_enabled` — already exactly "capability flags", 2B-3) plus the same
  resource-group *names* `/resources` below exposes (so a client can ask "is X on" and "does X
  exist" from one call without cross-referencing two responses).
- **`GET /api/v1/resources`** — the API surface catalog. Derived from
  `routes/v1/openapi.py::_PATHS` (already the single source of truth for every registered v1
  endpoint) grouped by top-level path segment into named resource groups (`scheduler`,
  `metrics`, `config`, `health`, `watchlists`, `snapshots`, `reports`, `candidates`) with each
  group's endpoint list and method — self-describing and impossible to drift out of sync with
  the real route table, since it's read from the same dict the OpenAPI endpoint already serves.
  This is the concrete answer to "avoid hardcoding these into clients" (Step 3): the *server*
  doesn't hardcode a second list either.

No business data anywhere in these three — every field is build metadata, a boolean flag, or a
path/method string.

## New service module

`engine/platform_info.py` — `get_version_info()`, `get_capabilities()`, `get_resource_catalog()`.
Pure aggregation over `engine.config_info` (2B-3, unchanged) and `routes.v1.openapi._PATHS`
(read, never mutated). Mirrors the pattern of every prior task's thin-aggregation module
(`engine/metrics.py`, `engine/config_info.py`, `engine/health.py`).

## Endpoints

- `GET /api/v1/version` — VIEWER.
- `GET /api/v1/capabilities` — VIEWER.
- `GET /api/v1/resources` — VIEWER.

No stronger auth justified by the audit — everything exposed is metadata already visible in
`/api/v1/config`/`/api/v1/openapi.json` (both VIEWER today), recombined for discoverability.

## Workstream 2D freeze (Phase 2 freeze)

After implementation: one final regression test spans **every** `/api/v1` endpoint across
Workstreams A/2A, 2B, 2C, and 2D as a single set (envelope, auth, OpenAPI, meta) — the
capstone freeze test for the whole API layer, superseding (not replacing) the 2B/2C
per-workstream freeze tests, which stay as their own regression guards.
