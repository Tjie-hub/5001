# IDX Suite Unified Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse three fragmented frontends into one shared Jinja shell with a single nav, History-API routing, four redundancy merges, and the outstanding review data-fixes.

**Architecture:** Extract the SPA's topbar + CSS into `base.html` + `static/shell.css` + `static/shell.js`. Every page `{% extends "base.html" %}` and renders server-side; `shell.js` progressively enhances internal nav into fetch-and-swap (History API) with full-navigation fallback. Merges are template/JS moves over unchanged `/api/*` endpoints.

**Tech Stack:** Flask, Jinja2, vanilla JS, existing JSON APIs. Tests: pytest (Python regression gate), manual smoke on `:5001`.

**Reference spec:** `docs/superpowers/specs/2026-06-13-idx-suite-unified-shell-design.md`

---

## File Structure

**Create:**
- `templates/base.html` — shell: `<head>`, topbar (brand/clock/search/mode), `<nav>`, `{% block content %}`, `{% block view_init %}`.
- `static/shell.css` — topbar/nav/shared tokens extracted from the SPA `<style>`.
- `static/shell.js` — global state (clock, search, firm-mode) + History-API router.
- `templates/sector.html` — merged heatmap + rotation table (M4).
- `tests/test_value_format.py` — unit test for the `T`-tier value formatter (A3).
- `static/format.js` — extracted, testable value formatter used by dive + others.

**Modify / rename:**
- `templates/watchlist.html` → `templates/dashboard.html` — extends base; drop own nav + heatmap block; add as-of stamps (A4).
- `templates/backtest_multi.html` → `templates/workspace.html` — extends base; drop duplicated topbar/CSS; remove `panel-fundamental` (M1), dive-modal (M2), `panel-monitor`/`panel-closed` → `panel-trades` (M3), `panel-sector` (M4).
- `templates/screener.html`, `templates/portfolio.html`, `templates/dive.html` — extend base; drop own `<head>`/nav.
- `templates/dive.html` — Net Value relabel + `T` tier (A3); VPIN abs·σ hint (A2-hint).
- `app.py` — `/` → `workspace.html`, `/dashboard` → `dashboard.html`, add `/sector`.
- `routes/screener.py` — `dive()` renders via base (no change to route).

**Acceptance for template-move tasks:** because the live templates are large and
evolve, template-surgery steps specify exact source regions + the end state +
a verification command (load the route on `:5001`), rather than pasting hundreds
of lines of HTML. The new *logic* files (shell.js router, format.js) carry full code.

---

## Phase 1 — Base shell foundation

### Task 1: Extract `format.js` value formatter + `T` tier (A3, TDD)

**Files:**
- Create: `static/format.js`
- Test: `tests/test_value_format.py`

- [ ] **Step 1: Write the failing test**

The formatter must add a trillion tier so `-1.354e12` renders `-1.35T` instead of
`-1354.8B`. We test the pure logic by executing the JS via node.

```python
# tests/test_value_format.py
import subprocess, json, pathlib

FMT = pathlib.Path("static/format.js").resolve()

def _fmt(v):
    script = f"const m=require('{FMT}');process.stdout.write(m.fmtSigned({v}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()

def test_trillion_tier():
    assert _fmt(-1.3548e12) == "-1.35T"

def test_billion_tier():
    assert _fmt(2.0e9) == "+2.0B"

def test_million_tier():
    assert _fmt(-3.4e6) == "-3.4M"
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `venv/bin/python -m pytest tests/test_value_format.py -q`
Expected: FAIL (module not found / no such file).

- [ ] **Step 3: Implement `static/format.js`**

```javascript
// static/format.js — shared value/number formatting (UMD: browser + node)
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.IDXFormat = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  function fmtSigned(v) {
    if (v == null || isNaN(v)) return '—';
    const s = v >= 0 ? '+' : '-';
    const a = Math.abs(v);
    if (a >= 1e12) return s + (a / 1e12).toFixed(2) + 'T';
    if (a >= 1e9)  return s + (a / 1e9).toFixed(1) + 'B';
    if (a >= 1e6)  return s + (a / 1e6).toFixed(1) + 'M';
    if (a >= 1e3)  return s + (a / 1e3).toFixed(0) + 'K';
    return s + a.toFixed(0);
  }
  return { fmtSigned };
}));
```

- [ ] **Step 4: Run test, verify PASS**

Run: `venv/bin/python -m pytest tests/test_value_format.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add static/format.js tests/test_value_format.py
git commit -m "feat(format): shared signed-value formatter with trillion tier"
```

### Task 2: Create `shell.css` (extract shared chrome styles)

**Files:**
- Create: `static/shell.css`
- Reference: `templates/backtest_multi.html` `<style>` block (lines ~18–532)

- [ ] **Step 1:** Copy the topbar/nav/token rules from the SPA `<style>` into
  `static/shell.css`: CSS custom properties (`:root` vars), `.topbar`, `.brand*`,
  `.wib-clock`, `.search-wrap*`, mode-toggle button styles, `.tabs*`/nav, modal
  base, and shared atoms (`.btn*`, `.kpi*`, `.table-wrap`, `.data`, `.panel-head`).
  Leave view-specific rules in their own templates for now (deduped in Phase 2).
- [ ] **Step 2:** Verify it parses (no syntax error): `npx --yes csslint static/shell.css || true` (advisory) — primary check is visual in Task 4.
- [ ] **Step 3: Commit**

```bash
git add static/shell.css
git commit -m "feat(shell): extract shared chrome styles to shell.css"
```

### Task 3: Create `shell.js` (global state + History-API router)

**Files:**
- Create: `static/shell.js`

- [ ] **Step 1:** Implement the router + global controls. Full code:

```javascript
// static/shell.js — unified shell: global state + History-API router
(function () {
  'use strict';

  // ── WIB clock ───────────────────────────────────────────────
  function tickClock() {
    const el = document.getElementById('wib-time');
    if (!el) return;
    const now = new Date(Date.now() + (7 * 60 + new Date().getTimezoneOffset()) * 60000);
    el.textContent = now.toTimeString().slice(0, 8);
  }
  setInterval(tickClock, 1000); tickClock();

  // ── Active nav highlight ────────────────────────────────────
  function syncActiveNav() {
    const path = location.pathname;
    document.querySelectorAll('[data-nav]').forEach(a => {
      const href = a.getAttribute('href');
      a.classList.toggle('active', href === path || (href !== '/' && path.startsWith(href)));
    });
  }

  // ── History-API router: progressive enhancement ─────────────
  const MOUNT = 'app-content';
  async function navigate(url, push) {
    const main = document.getElementById(MOUNT);
    if (!main) { location.href = url; return; }
    main.setAttribute('aria-busy', 'true');
    try {
      const res = await fetch(url, { headers: { 'X-Shell-Nav': '1' } });
      if (!res.ok) throw new Error(res.status);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const next = doc.getElementById(MOUNT);
      if (!next) throw new Error('no mount in response');
      main.replaceWith(next);
      if (push) history.pushState({ url }, '', url);
      window.scrollTo(0, 0);
      syncActiveNav();
      document.dispatchEvent(new CustomEvent('shell:mounted', { detail: { url } }));
    } catch (e) {
      location.href = url; // graceful fallback to full navigation
    }
  }

  document.addEventListener('click', e => {
    const a = e.target.closest('a[data-nav]');
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
    const url = a.getAttribute('href');
    if (!url || url.startsWith('http') || url.startsWith('#')) return;
    e.preventDefault();
    navigate(url, true);
  });
  window.addEventListener('popstate', () => navigate(location.pathname, false));

  // ── Global ticker search → /dive/<t> ────────────────────────
  const search = document.getElementById('global-search');
  if (search) {
    search.addEventListener('keydown', e => {
      if (e.key === 'Enter' && search.value.trim()) {
        navigate('/dive/' + search.value.trim().toUpperCase(), true);
      }
    });
    document.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); search.focus(); }
    });
  }

  syncActiveNav();
  window.__shellNavigate = navigate; // expose for view scripts
})();
```

- [ ] **Step 2: Commit**

```bash
git add static/shell.js
git commit -m "feat(shell): global state + History-API router with fallback"
```

### Task 4: Create `base.html` and migrate `/dashboard` + `/screener`

**Files:**
- Create: `templates/base.html`
- Rename: `templates/watchlist.html` → `templates/dashboard.html`
- Modify: `templates/screener.html`, `app.py`

- [ ] **Step 1:** Write `templates/base.html` with this skeleton (real code):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}IDX Suite{% endblock %}</title>
  <link rel="icon" href="/static/favicon.ico">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/shell.css">
  {% block head %}{% endblock %}
</head>
<body>
<header class="topbar">
  <div class="brand"><span class="brand-mark">◆</span> IDX <span class="brand-mark">Suite</span></div>
  <nav class="shell-nav">
    <span class="nav-group">
      <a data-nav href="/dashboard">Dashboard</a>
      <a data-nav href="/sector">Sector</a>
      <a data-nav href="/#calendar">Calendar</a>
    </span>
    <span class="nav-sep"></span>
    <span class="nav-group">
      <a data-nav href="/#trades">Trades</a>
      <a data-nav href="/#signals">Signals</a>
      <a data-nav href="/#scanner">Scanner</a>
      <a data-nav href="/#backtest">Backtest</a>
      <a data-nav href="/#intraday">Intraday</a>
    </span>
    <span class="nav-sep"></span>
    <span class="nav-group">
      <a data-nav href="/screener">Screener</a>
      <a data-nav href="/#brokerflow">Broker Flow</a>
      <a data-nav href="/portfolio">Portfolio</a>
      <a data-nav href="/#audit">Audit</a>
    </span>
  </nav>
  <div class="topbar-right">
    <div class="search-wrap">
      <input type="text" id="global-search" placeholder="Search ticker…" autocomplete="off">
      <span class="search-shortcut">⌘K</span>
    </div>
    <div id="firm-mode-toggle">{% block mode_toggle %}{% endblock %}</div>
    <div class="wib-clock"><span id="wib-time">--:--:--</span> WIB</div>
  </div>
</header>
<main id="app-content">
  {% block content %}{% endblock %}
</main>
<script src="/static/format.js"></script>
<script src="/static/shell.js"></script>
{% block view_init %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2:** `git mv templates/watchlist.html templates/dashboard.html`. Edit
  `dashboard.html`: remove its own `<!doctype>`/`<head>`/`<nav>`; wrap its body in
  `{% extends "base.html" %}{% block content %}…{% endblock %}`; move its page-specific
  CSS into `{% block head %}<style>…</style>{% endblock %}`; move page JS into
  `{% block view_init %}`. Keep all data-loading logic identical.
- [ ] **Step 3:** Same wrapping for `templates/screener.html`.
- [ ] **Step 4:** Edit `app.py`: `dashboard_page()` → `render_template("dashboard.html")`.
- [ ] **Step 5: Verify on running app.** Restart the app, then:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5001/dashboard
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5001/screener
```
Expected: `200` and `200`. Then load `/dashboard` in a browser (or `/run`): topbar +
nav render, clock ticks, clicking "Screener" swaps content without full reload, URL
becomes `/screener`, browser Back returns to `/dashboard`.

- [ ] **Step 6:** Run full Python suite (regression gate):

```bash
venv/bin/python -m pytest -q
```
Expected: same pass count as before this phase (no new failures).

- [ ] **Step 7: Commit**

```bash
git add templates/base.html templates/dashboard.html templates/screener.html app.py
git commit -m "feat(shell): base.html shell; migrate dashboard + screener"
```

---

## Phase 2 — Migrate remaining pages

### Task 5: Migrate `portfolio.html`, `dive.html`, `workspace.html` to base

**Files:**
- Modify: `templates/portfolio.html`, `templates/dive.html`
- Rename: `templates/backtest_multi.html` → `templates/workspace.html`
- Modify: `app.py`, `routes/backtest_multi.py` blueprint (template name), `routes/screener.py`

- [ ] **Step 1:** `git mv templates/backtest_multi.html templates/workspace.html`.
  Update every `render_template("backtest_multi.html")` reference (`app.py` `/` and
  `/signal-scanner`; grep to confirm) → `"workspace.html"`.
- [ ] **Step 2:** Edit `workspace.html`: delete its `<!doctype>`/`<head>`/duplicate
  `<header class="topbar">`; `{% extends "base.html" %}`; move the 12 `<section
  class="tab-panel">` blocks into `{% block content %}`; move CSS not already in
  shell.css into `{% block head %}`; move JS into `{% block view_init %}`. The
  hash-tab switching JS stays (workspace-internal tabs).
- [ ] **Step 3:** Wrap `portfolio.html` and `dive.html` the same way.
- [ ] **Step 4:** De-dupe CSS: remove rules from workspace/dashboard/dive that now
  live in `shell.css` (tokens, topbar, nav, buttons, tables). Keep only view-unique CSS.
- [ ] **Step 5: Verify all routes 200 + render under one shell:**

```bash
for p in / /dashboard /screener /portfolio /dive/BRPT; do \
  printf "%s " "$p"; curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:5001$p"; done
```
Expected: all `200`. Browser: every route shows the same topbar+nav; in-app nav
swaps without reload; the workspace hash-tabs still switch.

- [ ] **Step 6:** `venv/bin/python -m pytest -q` → no new failures.
- [ ] **Step 7: Commit**

```bash
git add templates/ app.py routes/
git commit -m "feat(shell): migrate portfolio, dive, workspace to base shell"
```

---

## Phase 3 — Merges M1 + M2

### Task 6: M1 — remove the Screener iframe tab

**Files:** Modify `templates/workspace.html`

- [ ] **Step 1:** Delete the `<section class="tab-panel" id="panel-fundamental">`
  (the `<iframe src="/screener">`) and its `<button data-tab="fundamental">` nav entry
  and any JS referencing `fund-iframe`.
- [ ] **Step 2:** Verify `/screener` still loads standalone (Task 4) and the workspace
  no longer shows a Fundamental tab. `curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/screener` → `200`.
- [ ] **Step 3: Commit** `git commit -am "refactor(shell): M1 drop Screener iframe tab"`

### Task 7: M2 — retire the Dive modal; route ticker chips to `/dive/<t>`

**Files:** Modify `templates/workspace.html`

- [ ] **Step 1:** Delete the `<div class="modal-backdrop" id="dive-modal">` block and
  its JS (`openDiveModal`, `closeDiveModal`, chart-in-modal init).
- [ ] **Step 2:** Replace every `onclick="openDiveModal('TICKER')"` (and equivalent
  chip handlers) with a link `href="/dive/TICKER" data-nav` so the router opens the
  full page in-shell.
- [ ] **Step 3: Verify:** in the workspace, clicking a ticker chip navigates to
  `/dive/<t>` (full page) with no modal; Back returns to the workspace tab.
- [ ] **Step 4:** `venv/bin/python -m pytest -q` → no new failures.
- [ ] **Step 5: Commit** `git commit -am "refactor(shell): M2 single deep-dive, drop modal"`

---

## Phase 4 — M3 Trades workspace

### Task 8: Merge Monitor + Closed Today + Paper into `panel-trades`

**Files:** Modify `templates/workspace.html`

- [ ] **Step 1:** Create `<section class="tab-panel" id="panel-trades">` containing a
  sub-tab strip `Active / Closed Today / History` and three sub-panels:
  - *Active* = the existing `monitor-grid` cards markup + broker-drilldown handler.
  - *Closed Today* = the `closed-grid` markup.
  - *History* = the Paper open+closed tables + KPI row.
- [ ] **Step 2:** Move the JS loaders (`loadMonitor`, `loadClosed`, paper loaders)
  under a single `loadTrades(subview)` dispatcher; wire the sub-tab strip to it.
  Reuse the **unchanged** `/api/paper/*` calls.
- [ ] **Step 3:** Delete `panel-monitor` and `panel-closed` sections and their
  `data-tab` nav buttons; remove the old top-level Monitor/Closed tabs. Add the
  `Trades` workspace tab (default workspace tab).
- [ ] **Step 4: Verify on `:5001`:** Trades tab shows Active cards; sub-tabs switch to
  Closed Today and History; broker drilldown still opens from an Active card; paper
  KPIs render in the Trades header.
- [ ] **Step 5:** `venv/bin/python -m pytest -q` → no new failures.
- [ ] **Step 6: Commit** `git commit -am "feat(shell): M3 unified Trades workspace (Active/Closed/History)"`

---

## Phase 5 — M4 Unified Sector

### Task 9: New `/sector` route; move heatmap off Dashboard

**Files:** Create `templates/sector.html`; Modify `app.py`, `templates/dashboard.html`, `templates/workspace.html`

- [ ] **Step 1:** Add route to `app.py`:

```python
@app.route("/sector")
def sector_page():
    return render_template("sector.html")
```

- [ ] **Step 2:** Create `templates/sector.html` extending base. Content = the Sector
  Heatmap markup (moved from `dashboard.html`) above the rotation table markup (moved
  from workspace `panel-sector`). One `loadSector()` populates both, calling the
  unchanged `/api/sector/rotation` (+ heatmap endpoint).
- [ ] **Step 3:** Remove the Sector Heatmap block from `dashboard.html` (keep risk,
  breadth, foreign flow, watchlist).
- [ ] **Step 4:** Delete `panel-sector` + its `data-tab` button from `workspace.html`.
- [ ] **Step 5: Verify:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/sector` → `200`;
  `/sector` shows heatmap + table; `/dashboard` no longer shows the heatmap.
- [ ] **Step 6:** `venv/bin/python -m pytest -q` → no new failures.
- [ ] **Step 7: Commit** `git commit -am "feat(shell): M4 unified /sector (heatmap + rotation)"`

---

## Phase 6 — Review-fix polish (A3 / A4 / A2-hint)

### Task 10: A3 — Net Value label + `T` tier in dive

**Files:** Modify `templates/dive.html`

- [ ] **Step 1:** Change the label `Net Vol (20d)` → `Net Value (20d, IDR)` (the
  `<span>` near `id="flow-net-total"`).
- [ ] **Step 2:** Replace the inline value formatter used for `flow-net-total` (and the
  sibling `fmt`/`fmtSigned` helpers near lines 1150–1159) with `IDXFormat.fmtSigned`
  from `format.js` (already loaded by base). Confirm `format.js` is loaded before
  dive's view script.
- [ ] **Step 3: Verify:** load `/dive/BRPT`; the order-flow total reads
  `Net Value (20d, IDR): -1.35T` (not `-1354.8B`).
- [ ] **Step 4: Commit** `git commit -am "fix(dive): A3 Net Value label + trillion tier"`

### Task 11: A2-hint — VPIN absolute·relative display

**Files:** Modify `templates/dive.html`

- [ ] **Step 1:** In the VPIN render (near `vpin-label` / `vpin-z`, ~lines 864–867),
  show both measures distinctly, e.g.:
  `${vpin.vpin_today.toFixed(3)} abs · ${vpin.vpin_z.toFixed(1)}σ vs ${vpin.lookback_days}d`
  and label the badge as the absolute class. Make clear they are two measures.
- [ ] **Step 2: Verify:** `/dive/BRPT` VPIN shows e.g. `0.985 abs · 0.0σ vs 10d`,
  no longer reading as a contradiction.
- [ ] **Step 3: Commit** `git commit -am "fix(dive): A2-hint absolute vs relative VPIN display"`

### Task 12: A4 — "as of <date>" stamps on Dashboard panels

**Files:** Modify `templates/dashboard.html` (+ `templates/sector.html` heatmap)

- [ ] **Step 1:** For each panel (Market Breadth, Foreign Flow & VPIN, Unified
  Watchlist; and Sector Heatmap on `/sector`), add a small `as of <date>` stamp in the
  panel header, populated from that panel's own response date field (the dashboard API
  payloads already carry the source date; read it in the existing render functions).
- [ ] **Step 2: Verify:** on `/dashboard` each panel header shows `as of 2026-06-12`
  (the last scan date), so empty "INSUFFICIENT_DATA" panels and the 40-row cached
  watchlist no longer look contradictory.
- [ ] **Step 3:** `venv/bin/python -m pytest -q` → no new failures.
- [ ] **Step 4: Commit** `git commit -am "fix(dashboard): A4 per-panel as-of date stamps"`

---

## Final verification

- [ ] All routes 200: `for p in / /dashboard /screener /portfolio /sector /dive/BRPT; do curl -s -o /dev/null -w "$p %{http_code}\n" "http://localhost:5001$p"; done`
- [ ] Full suite green: `venv/bin/python -m pytest -q`
- [ ] Manual smoke: one shell/nav everywhere; in-app nav swaps without reload; Back/forward works; refresh deep-links; no Fundamental tab, no Dive modal, no separate Monitor/Closed tabs; `/sector` merged; dive shows Net Value `T` + VPIN abs·σ; dashboard panels stamped.
- [ ] Update `IDX/IDX_Suite_Review_2026-06-13.md` or memory with completion status.
