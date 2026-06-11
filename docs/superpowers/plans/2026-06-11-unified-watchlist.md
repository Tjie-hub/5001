# Unified Watchlist Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's broken "Agent Live Feed" (Signals) panel with a unified watchlist that merges reversal + premover + bear-dip-scout sources into one ranked, de-duplicated list.

**Architecture:** A pure builder function `build_unified_watchlist()` reads three existing tables (each in its own try/except), normalizes each to a 0–100 strength, merges by ticker (union base; +15 confluence bonus when ≥2 sources agree on direction; conflicts flagged not merged), and returns a sorted list. A thin Flask endpoint exposes it; the dashboard panel swaps its fetch + render.

**Tech Stack:** Python 3.12, sqlite3 (stdlib), Flask blueprint (`routes/flow.py`), pytest, vanilla JS in `templates/watchlist.html`.

**Note on workspace:** This session commits directly to `master` (project convention). No worktree is used.

**Spec:** `docs/superpowers/specs/2026-06-11-unified-watchlist-design.md`

**Refinement vs spec:** The spec said the API defaults to *today*. `reversal_watchlist` is keyed by the EOD `scan_date` (the prior trading day), so "today" would miss it. This plan defaults to the **latest `scan_date`** in `reversal_watchlist` when no `date` is given — a correctness fix faithful to the spec's intent ("the current actionable watchlist").

---

## File Structure

- **Create** `engine/unified_watchlist.py` — the builder + per-source readers. One responsibility: merge/rank watchlists. No Flask, no I/O beyond sqlite reads.
- **Create** `tests/test_unified_watchlist.py` — DB-backed unit tests (temp sqlite).
- **Modify** `routes/flow.py` — add `GET /api/dashboard/unified-watchlist`.
- **Modify** `templates/watchlist.html` — swap the panel markup, the `Promise.all` fetch, and the render function.

---

## Task 1: Unified watchlist builder (TDD)

**Files:**
- Create: `engine/unified_watchlist.py`
- Test: `tests/test_unified_watchlist.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_unified_watchlist.py`:

```python
import sqlite3
import pytest

from engine.unified_watchlist import build_unified_watchlist


def _make_db(path, *, reversal=(), premover=(), bear=(), with_tables=("rev", "prem", "bear")):
    conn = sqlite3.connect(path)
    if "rev" in with_tables:
        conn.execute("""CREATE TABLE reversal_watchlist (
            scan_date TEXT, ticker TEXT, direction TEXT, conviction REAL,
            close INTEGER, smart_money TEXT, verdict TEXT, net_value INTEGER,
            reasons TEXT, created_at TEXT, PRIMARY KEY(scan_date,ticker))""")
        conn.executemany(
            "INSERT INTO reversal_watchlist(scan_date,ticker,direction,conviction,close,smart_money,verdict)"
            " VALUES(?,?,?,?,?,?,?)", reversal)
    if "prem" in with_tables:
        conn.execute("""CREATE TABLE watchlist_premover (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, detected_at TEXT,
            score REAL, close_price INTEGER, pattern_type TEXT)""")
        conn.executemany(
            "INSERT INTO watchlist_premover(ticker,detected_at,score,close_price,pattern_type)"
            " VALUES(?,?,?,?,?)", premover)
    if "bear" in with_tables:
        conn.execute("""CREATE TABLE regime_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, status TEXT, bt_win_rate REAL)""")
        conn.executemany(
            "INSERT INTO regime_watchlist(ticker,status,bt_win_rate) VALUES(?,?,?)", bear)
    conn.commit()
    conn.close()


def test_single_source_passthrough(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "MORNING_TRAP", "BEARISH")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["ticker"] == "BRPT"
    assert r["direction"] == "short"
    assert r["strength"] == 74.4
    assert r["sources"] == ["REVERSAL"]
    assert r["confluence"] is False
    assert r["conflict"] is False
    assert r["close"] == 1760
    assert r["detail"]["reversal"]["smart_money"] == "MORNING_TRAP"


def test_confluence_boost_same_direction(tmp_path):
    db = str(tmp_path / "wl.db")
    # INTP long in premover (60) and bear dip-scout (promoted -> 65); both LONG
    _make_db(db,
             premover=[("INTP", "2026-06-10", 60.0, 4000, "CONTINUATION")],
             bear=[("INTP", "promoted", 55.0)])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["direction"] == "long"
    assert r["confluence"] is True
    # max single strength = 65 (bear promoted) + 15 confluence = 80
    assert r["strength"] == 80.0
    assert set(r["sources"]) == {"PREMOVER", "BEAR_DIP"}


def test_conflict_flagged_not_merged(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db,
             reversal=[("2026-06-10", "ABCD", "short", 74.0, 1000, "STRONG_SELL", "BEARISH")],
             premover=[("ABCD", "2026-06-10", 60.0, 1000, "REVERSAL_BREAKOUT")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    r = items[0]
    assert r["direction"] == "short"          # higher-strength source wins
    assert r["conflict"] is True
    assert r["confluence"] is False
    assert r["strength"] == 74.0              # no merge bonus on conflict


def test_premover_floor_excludes_low_score(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, premover=[("LOWS", "2026-06-10", 50.0, 100, "CONTINUATION")])
    items = build_unified_watchlist(db, "2026-06-10")
    assert items == []


def test_dedupe_one_row_per_ticker(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db,
             reversal=[("2026-06-10", "XYZ", "long", 70.0, 500, "ACCUMULATION", "BULLISH")],
             premover=[("XYZ", "2026-06-10", 60.0, 500, "CONTINUATION")],
             bear=[("XYZ", "active", 52.0)])
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    assert set(items[0]["sources"]) == {"REVERSAL", "PREMOVER", "BEAR_DIP"}


def test_missing_source_table_is_resilient(tmp_path):
    db = str(tmp_path / "wl.db")
    # only reversal table exists; premover + regime tables absent
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "X", "BEARISH")],
             with_tables=("rev",))
    items = build_unified_watchlist(db, "2026-06-10")
    assert len(items) == 1
    assert items[0]["ticker"] == "BRPT"


def test_latest_date_default_when_none(tmp_path):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[
        ("2026-06-09", "OLD", "long", 90.0, 100, "X", "BULLISH"),
        ("2026-06-10", "NEW", "long", 60.0, 200, "Y", "BULLISH"),
    ])
    items = build_unified_watchlist(db, None)   # None -> latest scan_date
    assert [r["ticker"] for r in items] == ["NEW"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python -m pytest tests/test_unified_watchlist.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.unified_watchlist'`

- [ ] **Step 3: Write the implementation**

Create `engine/unified_watchlist.py`:

```python
"""engine/unified_watchlist.py — merge reversal + premover + bear-dip watchlists.

Weighted union: every flagged ticker appears once. Each source is normalized to a
0-100 strength. When >=2 sources agree on a direction the row gets a +15 confluence
bonus (capped at 100); when sources disagree the row is flagged (conflict) and the
higher-strength source's direction is shown without a merge bonus.

Each source is read in its own try/except so a missing or empty table degrades
gracefully (the source is skipped, never failing the whole panel).
"""
import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)

PREMOVER_FLOOR = 55.0       # min premover score to include (cuts noise)
CONFLUENCE_BONUS = 15.0     # added when >=2 sources agree on direction
BEAR_BASE = 50.0            # bear dip-scout has no native 0-100 score
BEAR_PROMOTED_BONUS = 15.0  # promoted entries rank above merely-active ones


def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def _latest_reversal_date(conn: sqlite3.Connection) -> Optional[str]:
    try:
        row = conn.execute("SELECT MAX(scan_date) FROM reversal_watchlist").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def _read_reversal(conn, scan_date):
    if not scan_date:
        return []
    try:
        rows = conn.execute(
            "SELECT ticker, direction, conviction, close, smart_money, verdict "
            "FROM reversal_watchlist WHERE scan_date=?", (scan_date,)
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: reversal source skipped: %s", e)
        return []
    return [{
        "ticker": r["ticker"], "source": "REVERSAL",
        "direction": (r["direction"] or "long").lower(),
        "strength": float(r["conviction"] or 0.0),
        "close": r["close"],
        "raw": {"conviction": r["conviction"], "smart_money": r["smart_money"],
                "verdict": r["verdict"]},
    } for r in rows]


def _read_premover(conn):
    try:
        rows = conn.execute(
            "SELECT ticker, score, close_price, pattern_type FROM watchlist_premover "
            "WHERE detected_at = (SELECT MAX(detected_at) FROM watchlist_premover) "
            "AND score >= ?", (PREMOVER_FLOOR,)
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: premover source skipped: %s", e)
        return []
    return [{
        "ticker": r["ticker"], "source": "PREMOVER",
        "direction": "long",
        "strength": float(r["score"] or 0.0),
        "close": r["close_price"],
        "raw": {"score": r["score"], "pattern_type": r["pattern_type"]},
    } for r in rows]


def _read_bear(conn):
    try:
        rows = conn.execute(
            "SELECT ticker, status, bt_win_rate FROM regime_watchlist "
            "WHERE status IN ('active','promoted')"
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: bear source skipped: %s", e)
        return []
    out = []
    for r in rows:
        strength = BEAR_BASE + (BEAR_PROMOTED_BONUS if r["status"] == "promoted" else 0.0)
        out.append({
            "ticker": r["ticker"], "source": "BEAR_DIP",
            "direction": "long", "strength": strength, "close": None,
            "raw": {"status": r["status"], "bt_win_rate": r["bt_win_rate"]},
        })
    return out


def build_unified_watchlist(db_path: str, scan_date: Optional[str] = None) -> list[dict]:
    """Merge the three watchlist sources into one ranked, de-duplicated list.

    scan_date: reversal EOD date to read. When None, uses the latest scan_date
    present in reversal_watchlist.
    """
    conn = _conn(db_path)
    try:
        if scan_date is None:
            scan_date = _latest_reversal_date(conn)
        rows = _read_reversal(conn, scan_date) + _read_premover(conn) + _read_bear(conn)
    finally:
        conn.close()

    by_ticker: dict[str, list] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    result = []
    for ticker, group in by_ticker.items():
        dominant = max(group, key=lambda x: x["strength"])
        direction = dominant["direction"]
        agree = [g for g in group if g["direction"] == direction]
        conflict = any(g["direction"] != direction for g in group)
        confluence = len(agree) >= 2
        strength = dominant["strength"]
        if confluence:
            strength = min(100.0, strength + CONFLUENCE_BONUS)

        close = None
        for g in group:
            if g["source"] == "REVERSAL" and g["close"] is not None:
                close = g["close"]
                break
        if close is None:
            for g in group:
                if g["close"] is not None:
                    close = g["close"]
                    break

        result.append({
            "ticker": ticker,
            "direction": direction,
            "strength": round(strength, 1),
            "sources": sorted({g["source"] for g in group}),
            "confluence": confluence,
            "conflict": conflict,
            "close": close,
            "detail": {g["source"].lower(): g["raw"] for g in group},
        })

    result.sort(key=lambda x: (-x["strength"], x["ticker"]))
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python -m pytest tests/test_unified_watchlist.py -q`
Expected: PASS — 7 passed

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add engine/unified_watchlist.py tests/test_unified_watchlist.py
git commit -m "feat(watchlist): unified watchlist builder (union + confluence)"
```

---

## Task 2: API endpoint

**Files:**
- Modify: `routes/flow.py` (add a route after `api_dashboard_watchlist`, ~line 370)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_unified_watchlist.py`:

```python
def test_endpoint_shape(tmp_path, monkeypatch):
    db = str(tmp_path / "wl.db")
    _make_db(db, reversal=[("2026-06-10", "BRPT", "short", 74.4, 1760, "MT", "BEARISH")])
    import config
    monkeypatch.setattr(config, "DB_PATH", db, raising=False)
    import routes.flow as flowmod
    monkeypatch.setattr(flowmod, "DB_PATH", db, raising=False)
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(flowmod.flow_bp)
    client = app.test_client()
    resp = client.get("/api/dashboard/unified-watchlist?date=2026-06-10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["items"][0]["ticker"] == "BRPT"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python -m pytest tests/test_unified_watchlist.py::test_endpoint_shape -q`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Add the endpoint**

In `routes/flow.py`, immediately after the `api_dashboard_watchlist` function (the block ending around line 370), add:

```python
@flow_bp.route('/api/dashboard/unified-watchlist', methods=['GET'])
def api_dashboard_unified_watchlist():
    """Unified watchlist — reversal + premover + bear-dip merged and ranked.

    Query params:
      date — reversal EOD date (default: latest scan_date in reversal_watchlist).

    Returns: date, count, items (ranked, one row per ticker).
    """
    from engine.unified_watchlist import build_unified_watchlist
    query_date = request.args.get('date')  # None -> builder uses latest
    try:
        items = build_unified_watchlist(DB_PATH, query_date)
        return jsonify({'date': query_date or 'latest', 'count': len(items), 'items': items})
    except Exception as e:
        return jsonify({'error': str(e), 'date': query_date or 'latest',
                        'count': 0, 'items': []}), 500
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && venv/bin/python -m pytest tests/test_unified_watchlist.py -q`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add routes/flow.py tests/test_unified_watchlist.py
git commit -m "feat(watchlist): /api/dashboard/unified-watchlist endpoint"
```

---

## Task 3: Dashboard panel swap

**Files:**
- Modify: `templates/watchlist.html` (panel markup ~370-380; CSS ~209; `Promise.all` ~883-897; `renderAgentFeed` ~827)

This task is HTML/JS with no unit test; verification is by loading the page.

- [ ] **Step 1: Replace the panel markup**

Replace the "D11: Agent Live Feed" panel (currently lines 370-380):

```html
    <!-- D11: Agent Live Feed -->
    <div class="panel">
      <div class="ph">
        <span class="pt">Agent Live Feed</span>
        <div class="sig-counts" id="sigCounts" style="margin:0;margin-left:8px"></div>
        <span id="sigTotal" style="font-size:10px;color:var(--text-mute);margin-left:auto"></span>
      </div>
      <div class="pb0">
        <div class="feed-wrap" id="agentFeed"><div class="empty">Loading…</div></div>
      </div>
    </div>
```

with:

```html
    <!-- Unified Watchlist -->
    <div class="panel">
      <div class="ph">
        <span class="pt">Unified Watchlist</span>
        <span id="uwlDate" style="font-size:10px;color:var(--text-mute);margin-left:auto"></span>
      </div>
      <div class="pb0">
        <div class="twrap" id="unifiedWatch"><div class="empty">Loading…</div></div>
      </div>
    </div>
```

- [ ] **Step 2: Add CSS for badges/rows**

In the `<style>` block, after the "Signal count badges" rules (~line 209), add:

```css
/* Unified watchlist */
.src-badge { display:inline-block; font-size:9px; padding:1px 5px; border-radius:3px;
  background:var(--border-soft); color:var(--text-dim); margin-right:3px; }
.src-badge.conf { background:var(--green-dim,#1d3); color:#fff; }
.src-badge.warn { background:var(--red-dim,#d33); color:#fff; }
tr.row-conf { background:rgba(40,200,120,0.08); }
.dir-long  { color:var(--green,#1a8f4a); }
.dir-short { color:var(--red,#c0392b); }
```

- [ ] **Step 3: Swap the fetch + render in the loader**

In the `Promise.all` block (~line 883), change the signals fetch line:

```javascript
      fetch('/api/dashboard/signals').then(r=>r.json()),
```
to:
```javascript
      fetch('/api/dashboard/unified-watchlist').then(r=>r.json()),
```

Change the destructuring (~line 883):
```javascript
    const [risk, wl, sec, signals, chk, vpinRes] = await Promise.all([
```
to:
```javascript
    const [risk, wl, sec, uwl, chk, vpinRes] = await Promise.all([
```

Change the render call (~line 897):
```javascript
    renderAgentFeed(signals);
```
to:
```javascript
    renderUnifiedWatchlist(uwl);
```

- [ ] **Step 4: Replace the render function**

Replace the entire `renderAgentFeed(d)` function (starts line 827, ends at its closing brace before the next `function`) with:

```javascript
function renderUnifiedWatchlist(d) {
  const items = (d && d.items) || [];
  document.getElementById('uwlDate').textContent =
    d && d.date ? `${d.count||items.length} · ${d.date}` : '';
  const el = document.getElementById('unifiedWatch');
  if (items.length === 0) {
    el.innerHTML = '<div class="empty">No watchlist setups</div>';
    return;
  }
  const body = items.map((r, i) => {
    const arrow  = r.direction === 'short' ? '▼' : '▲';
    const dirCls = r.direction === 'short' ? 'dir-short' : 'dir-long';
    const badges = (r.sources || []).map(s => `<span class="src-badge">${s}</span>`).join('');
    const conf   = r.confluence ? '<span class="src-badge conf">CONFLUENCE</span>' : '';
    const warn   = r.conflict   ? '<span class="src-badge warn">⚠</span>' : '';
    const broker = (r.detail && r.detail.reversal && r.detail.reversal.smart_money) || '—';
    const close  = (r.close != null) ? Number(r.close).toLocaleString() : '—';
    return `<tr class="${r.confluence ? 'row-conf' : ''}">
      <td>${i + 1}</td>
      <td><b>${r.ticker}</b></td>
      <td class="${dirCls}">${arrow} ${r.direction}</td>
      <td>${(r.strength ?? 0).toFixed(1)}</td>
      <td>${close}</td>
      <td>${badges}${conf}${warn}</td>
      <td>${broker}</td>
    </tr>`;
  }).join('');
  el.innerHTML = `<table><thead><tr>
      <th>#</th><th>Ticker</th><th>Dir</th><th>Str</th><th>Close</th><th>Sources</th><th>Broker</th>
    </tr></thead><tbody>${body}</tbody></table>`;
}
```

- [ ] **Step 5: Verify in the browser**

Run (app auto-runs on 5001; restart to pick up template if needed):
```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && pkill -f "python3 app.py"; sleep 2; (source venv/bin/activate; nohup python3 app.py > app.log 2>&1 &); sleep 6
curl -s "http://localhost:5001/api/dashboard/unified-watchlist" | head -c 400
```
Expected: JSON with `count` and `items` (BRPT/INTP/BBTN from the latest reversal scan).
Then open `http://localhost:5001/dashboard` — the old "Agent Live Feed" panel now shows the "Unified Watchlist" table; no console errors.

- [ ] **Step 6: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add templates/watchlist.html
git commit -m "feat(dashboard): swap Signals panel for Unified Watchlist"
```

---

## Self-Review

**Spec coverage:**
- Sources & normalization → Task 1 `_read_*` (reversal native conviction; premover ≥55 floor; bear base 50 +15 promoted). ✓
- Merge logic (union, confluence +15, conflict flag, dedupe, close fallback, sort) → Task 1 `build_unified_watchlist`. ✓
- API contract (`/api/dashboard/unified-watchlist`, success/error shapes) → Task 2. ✓
- Frontend (remove Signals panel + badges + fetch; add ranked table with badges/confluence/conflict/empty-state) → Task 3. ✓
- Testing (passthrough, confluence, conflict, floor, dedupe, resilience) → Task 1 Step 1 (+ endpoint test in Task 2). ✓
- Out-of-scope (foreign flow, agent-firm repair, no new tables) → respected. ✓

**Placeholder scan:** none — all steps carry full code/commands.

**Type/name consistency:** `build_unified_watchlist(db_path, scan_date=None)`, row keys `ticker/direction/strength/sources/confluence/conflict/close/detail`, source tags `REVERSAL/PREMOVER/BEAR_DIP`, frontend reads `d.items/d.date/d.count` and `detail.reversal.smart_money` — all consistent across tasks. ✓
