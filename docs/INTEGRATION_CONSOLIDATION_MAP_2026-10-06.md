# Frontend freeze — 5001 UI trimmed to the OS surfaces; jurnal26 (:5004) owns the personal layer

Date: 2026-10-06
Status: Implemented (owner-directed). This document is the amendment record that
drove the implementation, modelled on the 2026-09-03 consolidation map it
partially supersedes.

## ADR amendment (owner-directed 2026-10-06)

> **Owner-directed 2026-10-06: 5001 frontend frozen; the portfolio, intelligence
> and watchlist workspaces were removed because they duplicate or mis-state the
> jurnal26 ledger.**

This is the same kind of dated, user-directed amendment as the 2026-09-03
consolidation (which added `intelligence` to the frozen-seven registry). The
workspace registry in `frontend/src/app/router/workspaces.ts` goes from eight
workspaces to five; the frozen routes for the retired paths remain registered.

## Why

The owner no longer uses the 5001 frontend: since 2026-10-01 it had about 9 human
page loads. The personal journal on port 5004 (`~/jurnal26`) is the screen they
use. The 5001 **backend** stays fully in service: scheduler, API, data and
Telegram. jurnal26 reads the API and the DB, and its Research tab carries a
one-line 5001 health summary.

Some 5001 pages had become misleading:

- **Portfolio and Investment Intelligence** read 5001's own investment store
  (`inv_*` tables, `data/investments.py`). That store stopped at TOWR
  2026-04-14 (16 transactions). jurnal26 is the live ledger (through 2026-09
  plus dividends and plans). There is no sync, so those pages showed stale
  holdings as if they were current.
- **Watchlist** showed the EOD-plan snapshot only. The last pick was ANDI on
  2026-09-28; the plan has run daily since without approving one. jurnal26's
  screened list and snipers cover this need.

## What changed

1. **Workspace registry** (`frontend/src/app/router/workspaces.ts`):
   `portfolio`, `intelligence` and `watchlist` removed from `WORKSPACES`,
   `WORKSPACE_GROUPS` and `WorkspaceId` (eight → five: decision, ticker,
   market, search, settings). Sidebar and bottom navigation shrink with it.
2. **Retirement routes** (`frontend/src/app/router/app-router.tsx`):
   `/portfolio`, `/intelligence` and `/watchlist` resolve to a new
   `FrozenWorkspacePage` — a real page naming the retired workspace and
   pointing at jurnal26, never a blank SPA error or a 404, so old bookmarks
   keep working. `/portfolio` additionally carries the stopped-at note.
   This supersedes ADR-006 §5's interim fix, which left client-side
   `/portfolio` to the catch-all 404.
3. **Freeze banner** (new `frontend/src/app/shell/frozen-banner.tsx`, rendered
   once from `AppShell`): "5001 frontend is frozen. Portfolio, watchlist and
   daily research: **jurnal26 :5004**" on every remaining SPA workspace. The
   link is built from `window.location.hostname` — no hardcoded IP. The same
   line is added to every legacy Flask page via `templates/base.html` (+
   `static/shell.css`), with the same hostname-built link.
4. **Legacy `/portfolio`** (`templates/portfolio.html`, `app.py` route kept):
   renders only the freeze banner plus "This portfolio store stopped at
   2026-04-14 and is no longer maintained." The holdings/funds/dividends tabs
   and the editing forms are gone. The Portfolio link is removed from the
   legacy topbar nav.
5. **Left as they are:** Decision Center, Ticker, Market, Search, Settings
   (SPA), and every other legacy page (dashboard, screener, sector, dive,
   workspace, backtest_multi) apart from the banner.

## What deliberately did NOT change

- **No data deletion.** The `inv_*` tables, `data/investments.py` and the
  `/api/v1/investments*` routes all stay (reads and writes). Permanent deletes
  are the owner's to do. `/api/v1/investments/holdings` still answers.
- **No SPA deletion.** The domain modules of the removed workspaces
  (`domains/watchlist/`, `domains/intelligence/`) and the API/model modules
  they share with live pages (`api/watchlist.ts` feeds Decision Center's
  executive summary) remain in the tree; only their route/nav surfaces were
  removed. Tree-shaking drops the unrouted pages from the production bundle.
- **jurnal26 itself was not touched.**

## Test expectation changes (no test deleted)

- `workspaces.test.ts` — eight-workspace assertions became five, plus a
  negative assertion for the three retired ids and an assertion that their
  `ROUTE_PATHS` entries stay registered.
- `app-router.test.tsx` — the ADR-006 §5 block (portfolio → not-found) became
  a freeze block: the three frozen paths render the banner page; the banner
  link targets `http://<hostname>:5004/`; `/portfolio` shows the stopped-at
  note.
- `app-shell.test.tsx` — active-marker test moved from `/watchlist` to
  `/market`.
- `url-normalization.test.ts` — trailing-slash example moved to `/decision/`,
  with `/portfolio/` coverage kept under the frozen-path contract.
- `theme-provider.test.tsx` — theme-persistence page moved from `/watchlist`
  to `/market`.
- e2e `shell-navigation.spec.ts` — history round-trip moved from Portfolio to
  Market/Search; bookmark-safety test moved to `/decision`; new frozen-path
  e2e (banner text + :5004 href + no 404).
- e2e `responsive-shell.spec.ts` — drawer/sidebar link list is the five
  remaining workspaces.
