# IDX Suite — Unified Shell + Frontend Consolidation (Option B)

**Date:** 2026-06-13
**Source:** `IDX/IDX_Suite_Review_2026-06-13.md` (live LAN review, sections 3–5)
**Status:** Approved design, ready for implementation plan

---

## 1. Context & motivation

A live review of the running app (`192.168.31.214:5001`) found it functionally
healthy but fragmented into **three separate frontends**, each with its own
template, nav, and visual language:

- Main SPA "IDX Suite v2.6" (`backtest_multi.html`, `/`) — 12 hash-tabs + 3 modals
- Market Dashboard (`watchlist.html`, `/dashboard`) — its own 4-link nav
- Deep Dive (`dive.html`, `/dive/<t>`) — "← Dashboard" link only

Plus standalone `screener.html` (`/screener`) and `portfolio.html` (`/portfolio`).

The friction is **inconsistent navigation and overlapping names** (Dashboard's
"Signals/Screener" vs the SPA's "Signals/Scanner"), so the suite feels like many
disconnected apps. The review recommends **Option B**: one shell, one nav, behind
clean bookmarkable URLs.

An audit of every tab/page also surfaced genuine **redundancy** to collapse
(see §3).

### Related work already shipped (this session, separate from this spec)
The review's **Section 3 logic bugs** were fixed under TDD before this design:
- **A1** scanner duplicate/empty rows — `dedupe_and_filter_scan_rows()` in
  `routes/backtest.py`, wired into both scan branches. (`tests/test_scan_filter.py`)
- **A2** VPIN z-score saturation — `VPIN_Z_MIN_STD=0.02` floor in `engine/vpin.py`
  neutralizes fabricated extreme z-scores. (`tests/test_vpin_engine.py`)

The remaining review items (**A3** Net Value label, **A4** dashboard date stamps,
**A2-hint** absolute-vs-relative VPIN display) are *frontend* and are folded into
this shell work (§5) so the templates are touched once.

## 2. Goals / non-goals

**Goals**
- One shared shell: identical top bar, nav, and visual language on every route.
- One CSS/JS codebase for chrome (nav, top bar, global state, router).
- Clean deep-linkable URLs (`/dashboard`, `/dive/BRPT`, `/sector`) that load the
  shared shell; in-app navigation swaps content without a full reload.
- Collapse the four redundant areas (§3) so each function lives in exactly one place.
- Fold in the three outstanding frontend review fixes (§5).

**Non-goals**
- No backend/API changes for the merges — they reuse existing `/api/*` JSON.
- No JS-framework rewrite. This stays Flask + Jinja + vanilla JS.
- No restyling of individual view internals beyond what a merge requires.
- No change to scheduler, strategy, or agent logic.

## 3. Current-state audit (redundancy found)

| Area | Today | Verdict |
|---|---|---|
| **Fundamental** tab | literally `<iframe src="/screener">` | duplicate of `/screener` — **drop** |
| **Dive modal** (in SPA) | compact chart+price+strategies+flow | subset of full `/dive/<t>` — **drop modal** |
| **Monitor** + **Closed Today** + **Paper Trades** | three cuts of the paper book | **merge** into one Trades view |
| **Sector Rotation** tab + Dashboard **Sector Heatmap** | same momentum data, two views | **merge** into one Sector view |

**Kept distinct (not duplicates):** Scanner (multi-strategy scan) vs Screener
(fundamental filter) vs Intraday (VPIN scan) — different engines. Signals
(scheduler output) vs Dashboard Watchlist (curated setups) — different sources.

## 4. Target architecture

### 4.1 Shared Jinja shell + client router

```
templates/
  base.html        NEW — <head> assets, top bar, primary nav,
                   {% block content %}; loads shell.css + shell.js
  dashboard.html   renamed from watchlist.html; {% extends "base.html" %}  (landing)
  workspace.html   renamed from backtest_multi.html; the trade cockpit (tabs)
  screener.html    {% extends "base.html" %}  (no longer iframed)
  portfolio.html   {% extends "base.html" %}
  sector.html      NEW — heatmap + rotation table (merged)
  dive.html        {% extends "base.html" %}  (the one canonical deep-dive)
static/
  shell.css        one stylesheet for top bar / nav / shared tokens
  shell.js         global state (mode toggle, clock, ticker search) + router
```

**Routing model — server-rendered routes + History-API enhancement.**
Every route renders fully server-side (deep-link / bookmark / refresh all work).
`shell.js` then *progressively enhances*: it intercepts clicks on internal nav
links, `fetch`es the target route, swaps the `<main id="app-content">` region,
and calls `history.pushState`. `popstate` (back/forward) re-fetches+swaps. If
fetch fails or JS is disabled, the link behaves as a normal full navigation
(graceful fallback). Heavy view scripts (Dive chart) initialize on mount via a
per-view init hook, not on global load.

### 4.2 Navigation IA

**Top bar (persists on every route):**
`IDX Suite` · 🔍 ticker search · `SHADOW / ENFORCE ▾` mode toggle · clock.

**Primary nav, grouped by separators:**
- **Market:** Dashboard · Sector · Calendar
- **Trade:** Trades · Signals · Scanner · Backtest · Intraday
- **Research:** Screener · Broker Flow · Portfolio · Audit

**Dive** is contextual (opens from any ticker chip → `/dive/<t>` in-shell).

### 4.3 Routes vs workspace tabs (resolved)

- **Standalone routes** (own URL, extend base directly): `/dashboard`, `/screener`,
  `/portfolio`, `/sector`, `/dive/<t>`.
- **Workspace tabs** (live inside `workspace.html` at `/`, hash-addressed):
  Trades, Signals, Scanner, Backtest, Intraday, Broker Flow, Calendar, Audit.

The top-bar nav links to both kinds uniformly; the router handles the swap so a
tab and a route feel identical to the user.

## 5. The four merges + folded review fixes

**M1 — Screener.** Delete `panel-fundamental` (the iframe). `screener.html`
extends `base.html`; nav points to `/screener`. *No backend change.*

**M2 — One Deep Dive.** Delete the `dive-modal` markup + its JS in the workspace.
Every ticker chip routes to `/dive/<t>`. The full page is the sole deep-dive.

**M3 — Trades workspace.** New `panel-trades` with a sub-tab strip
*Active / Closed Today / History*:
- *Active* = Monitor's position cards + broker-flow drilldown (unchanged interaction)
- *Closed Today* = paper closed trades filtered to today
- *History* = full paper book (open + closed tables + KPIs)

Delete `panel-monitor` and `panel-closed`. Paper KPIs move to the Trades header.
*Reuses existing `/api/paper/*`; no backend change.*

**M4 — Unified Sector.** New `/sector` route (`sector.html`) renders the heatmap
(moved out of Dashboard) above the rotation table (moved out of the SPA tab). One
`loadSector()` feeds both. Dashboard drops its heatmap block; keeps risk gauge,
breadth, foreign flow, and unified watchlist. Delete `panel-sector` from the SPA.

**Folded review fixes (frontend, done while templates are open):**
- **A3** — `dive.html`: relabel "Net Vol (20d)" → **"Net Value (20d, IDR)"**; add a
  `T` tier (≥1e12) to the value formatter so `−1354.8B` renders `−1.35T`. (Verified:
  the figure is net **value** in rupiah from `stockbit_flow.net_value`, not a scaling
  bug — it was mislabeled.)
- **A4** — `dashboard.html`: add an **"as of \<date\>"** stamp to each panel header
  (breadth, foreign flow, sector heatmap on `/sector`, watchlist), sourced from that
  panel's own data date, so stale-vs-empty panels stop looking contradictory.
- **A2-hint** — `dive.html`: render VPIN as `0.985 abs · 0.0σ vs 10d` so the absolute
  label and the relative z-score read as two distinct measures, not a contradiction.

## 6. Data flow

All views consume existing JSON endpoints unchanged:
- Dashboard: `/api/dashboard/*` (risk, breadth, foreign flow, watchlist)
- Sector: existing sector-rotation + heatmap endpoints
- Trades: `/api/paper/*`, broker via `/api/ticker/<t>/broker`
- Dive: `/api/ticker/<t>/full`
- Scanner/Backtest/etc.: unchanged

The shell adds no new data dependency; global state (mode, clock, search) is
client-only in `shell.js`, reading the same mode/status endpoints the SPA uses today.

## 7. Error handling & edge cases

- **Router fetch failure:** fall back to full-page navigation (link's default).
- **JS disabled:** every route is a real server-rendered page — works without the router.
- **Deep link / refresh on a hash tab** (e.g. `/#scanner`): workspace.html restores
  the active tab from the hash on load (existing behavior, preserved).
- **Back/forward:** `popstate` re-fetches+swaps; scroll position reset to top on nav.
- **Active-nav highlight:** derived from `location.pathname` (+ hash for workspace tabs).
- **Double-init guard:** view init hooks are idempotent; re-mount tears down prior
  chart instances (Dive) to avoid leaks.

## 8. Testing strategy

- **Python suite stays green:** merges are template/JS over unchanged APIs; run the
  full `pytest` suite after each phase as a regression gate.
- **Shell smoke (manual via `/run` on 5001):** for each nav target — content swaps,
  URL updates, browser back/forward works, refresh deep-links correctly, JS-off
  fallback loads the server page.
- **A3 formatter:** unit-test the value formatter's `T` tier (pure JS function pulled
  to a testable helper, or assert via a small DOM check) — `1.354e12 → "1.35T"`.
- **A4/A2-hint:** visual verification on `/dashboard` and `/dive/BRPT` against the
  cached 12-Jun data.

## 9. Phased rollout

Each phase leaves the app fully working; ship/verify before the next.

1. **Base shell foundation** — create `base.html`, `shell.css`, `shell.js`
   (top bar, nav, global state, router). Migrate `dashboard.html` (rename from
   watchlist) and `screener.html` to extend it. Verify both routes + router.
2. **Migrate remaining pages** — `portfolio.html`, `dive.html`, and
   `workspace.html` (rename from backtest_multi) extend base; unify nav; remove the
   old per-page navs. Verify all routes under one shell.
3. **M1 + M2** — drop the Fundamental iframe tab and the Dive modal; route ticker
   chips to `/dive/<t>`.
4. **M3 Trades** — merge Monitor + Closed Today + Paper into the Trades sub-tab view.
5. **M4 Sector** — new `/sector`; move heatmap off Dashboard; delete SPA sector tab.
6. **Review-fix polish** — A3 (Net Value label + `T` tier), A4 (as-of stamps),
   A2-hint (VPIN abs·σ display).

## 10. Risks & mitigations

- **Large templates, manual moves** → phase per area, re-run pytest + manual smoke
  each phase; keep diffs reviewable.
- **Router edge cases** (back button, hash tabs) → progressive-enhancement design so
  worst case degrades to normal navigation.
- **CSS divergence** between the three current visual languages → consolidate tokens
  into `shell.css` in Phase 1; later phases inherit, not redefine.
- **Chart re-init leaks on Dive remount** → idempotent teardown in the view init hook.

## 11. Out of scope / future

- Restyling individual view internals beyond merge needs.
- Consolidating Scanner/Screener/Intraday engines (kept distinct by design).
- Any new analytics or data sources.
