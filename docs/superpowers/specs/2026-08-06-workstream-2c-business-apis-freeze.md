# Workstream 2C — Business APIs: FROZEN

**Status:** FROZEN 2026-08-06. Production Engine Phase 2, Workstream 2C (Business APIs) is
complete. Built on the frozen Phase 2A API Foundation and frozen Workstream 2B; no further
additions to this surface without a new, explicit task, same discipline as both prior freezes.

## Endpoint inventory

| Endpoint | Method | Auth | Task | Backing service |
|---|---|---|---|---|
| `/api/v1/watchlists/current` | GET | VIEWER | 2C-1 | `engine.trade_plan.get_snapshot`/`list_snapshot_dates` |
| `/api/v1/watchlists/history` | GET | VIEWER | 2C-1 | `engine.trade_plan.list_snapshot_dates` |
| `/api/v1/watchlists/<date>` | GET | VIEWER | 2C-1 | `engine.trade_plan.get_snapshot` |
| `/api/v1/watchlists/diff` | GET | VIEWER | 2C-1 | `engine.trade_plan.diff_watchlist` |
| `/api/v1/watchlists/persistent` | GET | VIEWER | 2C-1 | `engine.persistent_watchlist.list_watchlist` |
| `/api/v1/snapshots` | GET | VIEWER | 2C-2 | `trade_plan`/`watchlist_report.list_snapshot_inventory` (combined) |
| `/api/v1/snapshots/<date>` | GET | VIEWER | 2C-2 | same, filtered |
| `/api/v1/reports` | GET | VIEWER | 2C-3 | `forward_testing.reporting.build_forward_test_data`/`latest_report_date` |
| `/api/v1/reports/<date>` | GET | VIEWER | 2C-3 | same, `report_exists` |
| `/api/v1/candidates` | GET | VIEWER | 2C-4 | `engine.watchlist_report.get_snapshot`/`list_snapshot_inventory` |
| `/api/v1/candidates/<date>` | GET | VIEWER | 2C-4 | `engine.watchlist_report.get_snapshot` |
| `/api/v1/candidates/screening` | GET | VIEWER | 2C-4 | `screener.db.get_screen_results` |
| `/api/v1/candidates/reversal-watchlist` | GET | VIEWER | 2C-4 | `screener.reversal_filter.get_current_watchlist`/`run_scan` |
| `/api/v1/candidates/premover-watchlist` | GET | VIEWER | 2C-4 | `engine.premover_detector.get_watchlist` |

14 endpoints, all `GET`-only, all `VIEWER`. Verified programmatically as a single set by
`tests/test_v1_business_apis_freeze.py` — the freeze checkpoint test: if a future change to any
endpoint above breaks this file, it has broken the frozen contract.

## Legacy route disposition (2C-4's consumer audit)

| Legacy route | Active consumer | Disposition |
|---|---|---|
| `GET /api/screener/results` | Yes — `templates/workspace.html` | **Kept**, coexists with `/api/v1/candidates/screening` (same underlying call) |
| `GET /api/screener/reversal` | None found | **Removed**, migrated to `/api/v1/candidates/reversal-watchlist` |
| `GET /api/premover/watchlist` | None found | **Removed**, migrated to `/api/v1/candidates/premover-watchlist` |
| `POST /api/premover/run` | None found, but a write/trigger action | **Untouched** — out of this read-only workstream's scope regardless of consumer count |

## Contract consistency (verified, not just declared)

- **Response envelope** — every endpoint returns `{"ok": true, "data": {...}, "meta": {...}}`
  on success via `routes/v1/envelope.py::ok()`; every error case (`404 NOT_FOUND`/`NO_*_DATA`,
  `400 MISSING_DATE`) shares the same `{"ok": false, "error": {"code", "message", "details"}}`
  shape via `ApiError`. No endpoint writes its own response shape.
- **Error handling** — every endpoint shares `api_v1_bp`'s error handlers, so an unmatched path
  under any of the four business prefixes gets the identical `NOT_FOUND` envelope, not a
  per-prefix one-off.
- **Authorization** — all 14 `security/route_policy.py` entries (plus the 4 dynamic
  `<date_str>` rules) are `VIEWER`; nothing in this workstream was more sensitive than what's
  already broadcast to Telegram or served by the legacy routes it coexists with or replaces.
- **Request metadata** — every response's `meta` carries `api_version: "v1"`, a `request_id`,
  and a UTC ISO-8601 `timestamp` — the same `_meta()` call in every case.
- **OpenAPI registration** — all 14 documented in `routes/v1/openapi.py`'s `_PATHS`, verified
  present (with a `get` entry) via `/api/v1/openapi.json` itself in the freeze test.

## No new business logic introduced across all of 2C

Every field traces back to something that already existed before Workstream 2C started:

- **2C-1** added three pure read functions (`trade_plan.get_snapshot`/`list_snapshot_dates`,
  `persistent_watchlist.list_watchlist`) — zero change to `record_snapshot`, `diff_watchlist`,
  or `update_watchlist`.
- **2C-2** added two pure aggregate functions (`trade_plan`/`watchlist_report
  .list_snapshot_inventory`) — `GROUP BY` reads over tables 2C-1/pre-existing code already
  owned; dropped a redundant suggested endpoint (`/snapshots/history`) rather than duplicate
  `/snapshots` itself.
- **2C-3** confirmed Forward-Testing is the *only* persisted structured report subsystem (no
  placeholder EOD/Premarket report endpoints, per the audit); added `report_exists`/
  `latest_report_date` (reading the pre-existing `_job_sentinel` dedup guard, never read before)
  and `build_forward_test_data` (the same six-function assembly `build_forward_test_report`
  already does, minus the text rendering).
- **2C-4** resolved the legacy migration question via a real consumer audit (not a guess); added
  two pure read functions (`watchlist_report.get_snapshot`, `reversal_filter
  .get_current_watchlist` — the latter relocating, not duplicating, logic that used to live
  inline in the now-deleted route); designed then **dropped** `/candidates/diff` before writing
  any code, on discovering `diff_snapshot()` structurally cannot be driven by persisted data
  alone (its "current" side always recomputes `candidate_score()` from live objects whose raw
  inputs are never persisted) — a finding, not a narrowing choice.

## Ready for Phase 2D

Workstream 2C's exit criteria (Watchlist/Snapshot/Report/Candidate Universe APIs complete, the
legacy candidate API question resolved by audit, consistent contract, formally frozen) are met.
Phase 2D (Integration APIs) can begin as its own spec→plan cycle, same as 2A→2B→2C.
