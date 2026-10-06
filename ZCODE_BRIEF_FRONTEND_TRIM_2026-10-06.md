# ZCode brief — 5001 frontend trim + orphaned job runs + digest stale skip (2026-10-06)

**Branch:** `fix/telegram-curation` (on top of `b2b5e26` and later). New commits; do not amend.
**Category:** Production (frontend + small backend). **Owner-directed 2026-10-06.**

## Why

The owner no longer uses the 5001 frontend: since 2026-10-01 it had about 9 human page loads. The
personal journal on port 5004 (`~/jurnal26`) is the screen they use. The 5001 **backend** stays fully
in service: scheduler, API, data and Telegram. jurnal26 reads the API and the DB, and its Research tab
now carries a one-line 5001 health summary (`/api/system` in jurnal26).

Some 5001 pages are now misleading:

- **Portfolio and Investment Intelligence** read 5001's own investment store (`inv_*` tables,
  `data/investments.py`). That store stopped at TOWR 2026-04-14 (16 transactions). jurnal26 is the
  live ledger (through 2026-09 plus dividends and plans). There is no sync, so these pages show stale
  holdings as if they were current.
- **Watchlist** shows the EOD-plan snapshot only. The last pick was ANDI on 2026-09-28; the plan has
  run daily since without approving one. jurnal26's screened list and snipers cover this need.

The direction is to freeze the 5001 frontend, remove what misleads, and point to 5004. Do not delete
the SPA, and do not build anything new in it.

## Hard constraints

- `logs/TELEGRAM_OFF` stays in place, and nothing is sent. Do not restart `idx-walkforward`.
- **No data deletion.** The `inv_*` tables, `data/investments.py` and the `/api/v1/investments*`
  routes stay. Only the UI surfaces go. Permanent deletes are the owner's to do.
- Do not touch `~/jurnal26`.
- Production serves `frontend/dist` from the working tree, and `dist` is not tracked by git, so
  `npm run build` makes the change live immediately with no restart. That is intended here. Build
  only after the frontend tests pass.
- Never print tokens or secrets.

## 1. Frontend trim

1. **Remove these three workspaces:**
   - `portfolio`
   - `intelligence`
   - `watchlist`

   They are defined in `frontend/src/app/router/workspaces.ts` (`WORKSPACES`), with routes and nav.
   Requests to their old paths (`/portfolio`, `/intelligence`, `/watchlist`) must still resolve to a
   page that shows the banner from item 3, not a blank SPA error or a 404, so old bookmarks work.
2. **The workspace set is frozen by ADR** (header of `workspaces.ts`, "frozen-seven", Phase 4 P4-16
   §14). The 2026-09-03 consolidation shows the precedent: a user-directed, dated amendment.
   - Write the same kind of short amendment: "Owner-directed 2026-10-06: 5001 frontend frozen; the
     portfolio, intelligence and watchlist workspaces were removed because they duplicate or
     mis-state the jurnal26 ledger."
   - Put it in the file header comment and in a new `docs/INTEGRATION_CONSOLIDATION_MAP_2026-10-06.md`,
     modelled on the 09-03 document.
   - Update `workspaces.test.ts`, `url-normalization.test.ts` and any e2e test to the new set. Do not
     delete a test to make it pass: change its expectation, and say so in the report.
3. **Banner.** One thin line at the top of every remaining SPA workspace, and of the legacy Flask
   pages (`templates/base.html` and anything not extending it, e.g. `portfolio.html`):
   > 5001 frontend is frozen. Portfolio, watchlist and daily research: **jurnal26 :5004**.
   - Link it to `http://<same host>:5004/`. Build the link from `window.location.hostname`; no
     hardcoded IP.
   - Plain text and a link only: no dismiss state, no new dependencies.
4. **Legacy pages:**
   - Remove the "Portfolio" nav link in `templates/base.html`.
   - Keep the `/portfolio` Flask route, but it renders only the banner plus one sentence: "This
     portfolio store stopped at 2026-04-14 and is no longer maintained." It must no longer render the
     holdings or the editing forms. Leave its API routes alone.
   - Leave every other legacy page (dashboard, screener, sector, dive, workspace, backtest_multi)
     unchanged apart from the banner.
5. Leave Decision Center, Ticker, Market, EOD, Premarket, Search and Settings as they are.

## 2. Orphaned `running` rows in `job_execution_log`

`/api/v1/status/summary` reports `running: 14`. All 14 are rows from runs that were in progress when
the service restarted on 2026-10-05 at 16:59 (intraday screener runs from 09:05 onward, etc.). The
module docstring in `engine/job_status.py` says an orphaned `running` row is left by design, so that
the ledger stays append-only.

**Keep that design.** Do not rewrite or delete old rows. Classify them on read instead:

- A `running` row is **orphaned** when it started before the current process started. If startup
  time isn't reliably available, the fallback is "older than 6 h"; say which you used.
- `get_running_jobs()` and `get_status_summary()` stop counting orphaned rows as `running`. The
  summary gains an `orphaned` count. `/api/v1/status/jobs/running` lists only live runs, plus
  `orphaned_count`.
- Add tests:
  - a row from before process start counts as orphaned
  - a fresh row counts as running
  - the summary counts are correct
  - nothing in `job_execution_log` is UPDATEd or DELETEd
- If a different remedy fits the code better, propose it in the report and do not implement it. An
  example would be a startup pass that appends a closing record without mutating the original row.

## 3. Digest stale skip: calendar days → trading days

`utils/notify_policy.py` D4 archives buffer items whose file-day is more than **2 calendar days** old.

- **Problem:** a Friday item whose flush fails is dropped on Monday. The jurnal26 review (its M3)
  also noted that jurnal26 items written during a 5001 outage would be dropped the same way.
- **Change:** stale = more than **2 IDX trading days** before today. Use the holiday list in
  `engine/calendar_filter.py` plus weekends, and keep the fallback to calendar days if the calendar
  can't be read.
- Keep the existing "N older items skipped" line.
- Add tests:
  - Friday → Monday is kept
  - 3 trading days back is skipped
  - an Indonesian holiday inside the window is not counted

## Done-criteria

- Frontend: `npm run lint`, the unit tests and the build all pass. Run the e2e/Playwright suite if
  it runs headless here; if not, say why.
- Then `npm run build` so production serves the trimmed UI.
- Python: the targeted suites pass:
  - `tests/test_notify_policy*.py`
  - the job-status tests
  - `tests/security/test_route_policy.py`
  - `test_cron_contract.py`

  Then run the full suite in the background and report the exact counts.
- Verify live, read-only:
  - `/`, `/decision`, `/portfolio` and `/watchlist` on 5001 show the banner, and the old paths do
    not 404.
  - `/api/v1/investments/holdings` still answers, since the API is kept.
  - `/api/v1/status/summary` shows `orphaned` (it will still show 14 until the owner restarts the
    service, if your fix is in Python; say which).
- Commit (Conventional Commits: `feat(frontend): …`, `fix(status): …`, `fix(ops): …`) and push to
  `fix/telegram-curation`.
- Write the report `ZCODE_REPORT_FRONTEND_TRIM_2026-10-06.md`. It covers:
  - what changed, per section
  - the ADR amendment text
  - the orphan rule used
  - before/after screenshots or text captures of the banner
  - test counts
  - anything not done
