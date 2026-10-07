# ZCode report — 5001 frontend trim + orphaned job runs + digest stale skip (2026-10-06)

**Branch:** `fix/telegram-curation`, pushed to `origin` at `aa298e2` (on top of
`84b3873` → `6880b26`). Three commits, none amended:

| Commit | Scope |
|---|---|
| `fff3a8b` | `feat(frontend): freeze 5001 frontend — drop portfolio/intelligence/watchlist workspaces, :5004 banner, frozen-path pages (owner-directed 2026-10-06)` |
| `bfe589c` | `fix(status): classify orphaned 'running' rows on read — never mutate the append-only ledger` |
| `aa298e2` | `fix(ops): digest stale skip counts IDX trading days, not calendar days (D4 amendment)` |

## 1. Frontend trim

### Workspace removal (`frontend/src/app/router/`)

- `workspaces.ts`: `portfolio`, `intelligence`, `watchlist` removed from
  `WORKSPACES`, `WORKSPACE_GROUPS` and `WorkspaceId` — eight workspaces → five
  (decision, ticker, market, search, settings). Sidebar and mobile bottom
  navigation shrink automatically (both read the registry).
- `app-router.tsx`: the live `/intelligence` and `/watchlist` routes removed;
  all three old paths (`/portfolio`, `/intelligence`, `/watchlist`) now resolve
  to a new **FrozenWorkspacePage** — a real page naming the retired workspace
  and linking to jurnal26, never a blank SPA error or a 404, so old bookmarks
  work. `/portfolio` additionally carries the stopped-at note. This supersedes
  ADR-006 §5's interim fix, which left client-side `/portfolio` on the 404
  catch-all.
- The domain modules of the removed workspaces (`domains/watchlist/`,
  `domains/intelligence/`) and `api/watchlist.ts` (still feeding Decision
  Center's executive summary) remain in the tree — only the route/nav surfaces
  went. Tree-shaking drops the unrouted pages from the bundle (329 kB built vs
  362 kB before).

### ADR amendment

In the `workspaces.ts` header and in the new
`docs/INTEGRATION_CONSOLIDATION_MAP_2026-10-06.md` (modelled on the 09-03
document), verbatim:

> **Owner-directed 2026-10-06: 5001 frontend frozen; the portfolio,
> intelligence and watchlist workspaces were removed because they duplicate or
> mis-state the jurnal26 ledger.**

### Banner

- SPA: new `app/shell/frozen-banner.tsx` rendered once from `AppShell` — one
  thin line above the global header on every remaining workspace. No landmark
  role (the app's single `banner` landmark stays the header), no dismiss
  state, no new dependencies.
- Legacy: same line added to `templates/base.html` (+ `.frozen-banner` class in
  `static/shell.css`) — covers dashboard, screener, sector, dive, workspace and
  portfolio.
- Link: `http://<window.location.hostname>:5004/` — built from the current
  hostname, no hardcoded IP (verified live from `127.0.0.1`; works identically
  from the LAN address).

### Legacy `/portfolio`

- `templates/portfolio.html` rewritten: banner + "This portfolio store stopped
  at 2026-04-14 and is no longer maintained." + the jurnal26 pointer. The
  holdings/funds/dividends tabs and every editing form are gone.
- `app.py`'s `@app.route("/portfolio")` kept; `/api/v1/investments*` routes and
  the `inv_*` tables untouched (verified: `/api/v1/investments/holdings` still
  answers with live data).
- "Portfolio" nav link removed from `templates/base.html`. The "Intelligence"
  link was left (the brief named only Portfolio); it now leads to the frozen
  banner page, which self-explains and points at :5004.

### Frontend test expectation changes (none deleted)

- `workspaces.test.ts`: eight-workspace assertions → five; added a negative
  assertion for the three retired ids and one that their `ROUTE_PATHS` stay
  registered (the frozen-path contract).
- `app-router.test.tsx`: the ADR-006 §5 block (portfolio → not-found) became a
  freeze block: all three frozen paths render the banner page, the banner link
  targets `http://<hostname>:5004/`, `/portfolio` shows the stopped-at note,
  and the retired workspaces do not resurrect behind their URLs. Sidebar
  navigation tests moved from Portfolio/Watchlist to Market/Search.
- `app-shell.test.tsx`: active-marker test moved `/watchlist` → `/market`
  (documented in a comment).
- `url-normalization.test.ts`: trailing-slash example moved to `/decision/`;
  `/portfolio/` coverage kept under a new frozen-path case.
- `theme-provider.test.tsx`: theme-persistence page `/watchlist` → `/market`.
- e2e `shell-navigation.spec.ts`: history round-trip moved from Portfolio to
  Market/Search; bookmark-safety test moved to `/decision`; new frozen-path
  e2e (banner text, `:5004` href, no 404).
- e2e `responsive-shell.spec.ts`: drawer/sidebar link count 7 → 5 with the new
  href list; test renamed.

## 2. Orphaned `running` rows (`engine/job_status.py`, `routes/v1/status.py`)

**Rule used:** a `running` row is **orphaned when it started before the current
process started**. Process start comes from Linux `/proc` (`/proc/self/stat`
starttime anchored to `/proc/stat` btime — `process_start_epoch()`), which is
available on this box, so the primary rule is what applies here. **Fallback
(only when `/proc` is unreadable): older than 6 h** (`ORPHAN_MAX_AGE_S`). A row
with an unparsable `started_at` stays live (fail-open — never hide a
possibly-running job). The ledger stays append-only: classification happens at
read time and **no row is ever UPDATEd or DELETEd** (tested row-for-row).

- `get_running_jobs()` → live runs only; new `get_orphaned_running_jobs()` →
  the complement.
- `get_status_summary()` gains an **`orphaned`** key; `running` counts live
  runs only; `total` is unchanged (it still counts every row).
- `/api/v1/status/jobs/running` lists only live runs plus `orphaned_count`;
  `/api/v1/status/summary` and `/api/v1/metrics*` carry the new key; OpenAPI
  descriptions updated.

## 3. Digest stale skip (`utils/notify_policy.py`)

**Rule used:** stale = file-day **more than 2 IDX trading days** before today
(weekends plus the holiday lists in `engine/calendar_filter.py`, 2024/2025/2026
sets). **Fallback when the calendar can't be read: 2 calendar days** (the old
rule) — implemented and tested, logged as a warning when hit. An unparsable or
future file-day is never stale (keep and send, never drop). The
"N older items skipped" line and the `.stale` archiving are unchanged.

Effect: a Friday item whose flush failed is sent by Monday's flush (1 trading
day) instead of being dropped (3 calendar days) — the jurnal26-review M3
complaint is closed for the 5001 side too.

## Live verification (read-only, production 5001, no restart)

Browser-rendered text captures via Playwright against `http://127.0.0.1:5001`:

```
/decision      h1="Decision Center"    banner="5001 frontend is frozen. Portfolio, watchlist and daily research: jurnal26 :5004"  link="http://127.0.0.1:5004/"
/watchlist     h1="Workspace frozen"   banner=… same …   link="http://127.0.0.1:5004/"
/intelligence  h1="Workspace frozen"   banner=… same …   link="http://127.0.0.1:5004/"
/market        h1="Market"             banner=… same …   link="http://127.0.0.1:5004/"
/portfolio     h1="Portfolio — frozen" (legacy Flask page)
               note="This portfolio store stopped at 2026-04-14 and is no longer maintained."
```

- All old paths return **HTTP 200** (no 404): `/`, `/decision`, `/portfolio`,
  `/watchlist`, `/intelligence`.
- `/api/v1/investments/holdings` still answers with live data (API kept).
- `logs/TELEGRAM_OFF` untouched and in place; nothing was sent.
- No service was restarted; `~/jurnal26` was not touched; no data deleted.

## Test counts

| Suite | Result |
|---|---|
| `npm run lint` | 0 errors, 0 warnings |
| Frontend unit (vitest) | **257 passed** (34 files) |
| Frontend e2e (Playwright, headless chromium — runs fine on this box) | **30 passed** |
| `npm run build` (after tests green) | clean; dist rebuilt and live |
| `tests/engine/test_job_status.py` + `test_v1_status_routes.py` + `test_v1_metrics_routes.py` | **65 passed** |
| `tests/test_notify_policy.py` + `test_notify_policy_classification.py` | **41 passed** |
| `tests/security/test_route_policy.py` + `tests/test_cron_contract.py` | **11 passed** |
| Full suite (project venv, `venv/bin/python -m pytest -q`) | **3,518 passed, 3 skipped, 0 failed** (23 m 20 s) |

Note: a first full-suite attempt with the system `python3` died at collection
(`ModuleNotFoundError: feedparser`); rerun with the project `venv` — that is
the canonical interpreter (same one gunicorn uses).

## Not done / restart-gated (the brief forbids restarting `idx-walkforward`)

1. **Part 2 is a Python fix, so its live effect waits for the owner's next
   restart.** `/api/v1/status/summary` currently still returns the old shape
   with `running: 14` (the 2026-10-05-16:59 restart strays) and no `orphaned`
   key. After a restart those 14 reclassify to `orphaned: 14, running: 0`
   automatically, on read.
2. **Legacy-page banner + Portfolio nav-link removal are staged but partially
   Jinja-cache-gated.** Production gunicorn workers cache compiled templates
   (auto-reload off). The trimmed `/portfolio` body already renders (verified
   live), but its `base.html` shell still serves the pre-change header (no
   banner, old nav) from the per-worker cache. The SPA banner and frozen pages
   are **already live** (dist is served from the working tree). One restart
   makes the legacy shell pick up the banner + nav change.
3. Nothing else: no data deletion (permanent deletes remain the owner's call),
   no jurnal26 changes, nothing sent.
