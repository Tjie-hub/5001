# dive.html Chart Annotations & Badges (G9–G12) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add suspension gap markers (G9), regime strategy hints (G10), crash annotations (G11), and fundamental red flag badges (G12) to the dive.html stock detail page.

**Architecture:** Three new keys (`suspensions`, `recommended_strategy`, `fundamental`) are added to the existing `/api/ticker/<ticker>/full` JSON response in `routes/screener.py`. Frontend in `templates/dive.html` consumes these plus computes crash markers client-side from `_rawCandles`. A new `_contextMarkers` module variable and `refreshContextMarkers()` helper keep G9/G11 markers visible across strategy changes.

**Tech Stack:** Python/Flask, SQLite, vanilla JS, Lightweight Charts v4.2.0

---

## File Map

| File | Change |
|------|--------|
| `routes/screener.py` | Add `suspensions`, `recommended_strategy`, `fundamental` to `api_ticker_full()` |
| `templates/dive.html` | Add `_contextMarkers`, `refreshContextMarkers()`, update `runSelectedStrategy()`, add `renderSuspensions()`, update `renderPrice()`, add `renderCrashMarkers()`, add `renderFundamental()`, wire `loadFull()`, add HTML/CSS for fund badge |
| `tests/test_api_ticker_full.py` | New — backend tests for all three new response fields |

---

## Task 1: Test fixture + `suspensions` field

**Files:**
- Create: `tests/test_api_ticker_full.py`
- Modify: `routes/screener.py:314-341` (the `return jsonify({...})` block)

- [x] **Step 1: Create test file with fixture**

Create `tests/test_api_ticker_full.py`:

```python
"""Tests for new fields added to GET /api/ticker/<ticker>/full."""
import json
import sqlite3
import tempfile
import os
import pytest
import pandas as pd
import numpy as np


def _make_ohlcv_rows(n=30):
    """Return list of (date, open, high, low, close, volume) tuples."""
    import datetime
    start = datetime.date(2026, 1, 2)
    rows = []
    for i in range(n):
        d = start + datetime.timedelta(days=i)
        rows.append((d.isoformat(), 100.0, 102.0, 98.0, 101.0, 1_000_000))
    return rows


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))

    # ohlcv — minimum 30 rows so detect_regime() / calc_adx() warm up
    conn.execute(
        "CREATE TABLE ohlcv "
        "(date TEXT, ticker TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    for row in _make_ohlcv_rows(30):
        conn.execute(
            "INSERT INTO ohlcv VALUES (?, 'TEST', ?, ?, ?, ?, ?)", row
        )

    # suspension_events
    conn.execute("""
        CREATE TABLE suspension_events (
            ticker TEXT,
            last_normal_date TEXT,
            resume_date TEXT,
            missing_td INTEGER,
            gap_pct REAL,
            classification TEXT,
            detected_at TEXT,
            PRIMARY KEY (ticker, last_normal_date, resume_date)
        )
    """)
    conn.execute(
        "INSERT INTO suspension_events VALUES "
        "('TEST','2026-01-10','2026-01-15',3,-0.20,'suspension','2026-01-15T09:00:00')"
    )
    conn.execute(
        "INSERT INTO suspension_events VALUES "
        "('TEST','2026-01-20','2026-01-22',1,-0.05,'data_gap','2026-01-22T09:00:00')"
    )

    # stockbit_keystats
    conn.execute("""
        CREATE TABLE stockbit_keystats (
            ticker TEXT, fetch_date TEXT,
            pe_ttm REAL, pe_ann REAL, pe_forward REAL, pbv REAL,
            ps_ttm REAL, eps_ttm REAL, bvps REAL, earnings_yield REAL,
            pcf_ttm REAL, pfcf_ttm REAL, ev_ebit REAL, ev_ebitda REAL,
            peg_ratio REAL, fcf_per_share REAL, cash_per_share REAL,
            revenue_per_share REAL, current_ratio REAL, quick_ratio REAL,
            roe REAL, roa REAL, market_cap REAL,
            der REAL, npm REAL, div_yield REAL, rev_growth REAL,
            earn_growth REAL, updated_at TEXT,
            PRIMARY KEY (ticker, fetch_date)
        )
    """)

    # tables needed by other parts of api_ticker_full
    conn.execute(
        "CREATE TABLE wf_scores "
        "(ticker TEXT, strategy TEXT, consistency_pct REAL, "
        "avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)"
    )
    conn.execute(
        "CREATE TABLE stockbit_flow "
        "(ticker TEXT, trade_date TEXT, net_lot REAL, net_value REAL, "
        "composite_score REAL, verdict TEXT, smart_money TEXT, last_price REAL)"
    )
    conn.execute(
        "CREATE TABLE broker_flow "
        "(ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT, lot REAL, value REAL)"
    )
    conn.execute(
        "CREATE TABLE suspension_events_idx "
        "ON suspension_events(ticker, resume_date DESC)"
        if False else "SELECT 1"  # index already in CREATE above
    )

    conn.commit()
    conn.close()

    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setattr("scheduler.start_scheduler", lambda: None, raising=False)

    from flask import Flask
    from routes.screener import screener_main_bp
    app = Flask(__name__, template_folder="../templates")
    app.register_blueprint(screener_main_bp)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, str(db)


def _get_full(client):
    c, _ = client
    resp = c.get("/api/ticker/TEST/full")
    assert resp.status_code == 200
    return json.loads(resp.data)
```

- [x] **Step 2: Write failing test for `suspensions` field**

Append to `tests/test_api_ticker_full.py`:

```python
# ── G9: suspensions ────────────────────────────────────────────────────────


def test_full_includes_suspensions_key(client):
    d = _get_full(client)
    assert "suspensions" in d


def test_suspensions_only_includes_suspension_classification(client):
    d = _get_full(client)
    for s in d["suspensions"]:
        assert s["missing_td"] == 3   # only the 'suspension' row, not 'data_gap'


def test_suspensions_has_correct_fields(client):
    d = _get_full(client)
    assert len(d["suspensions"]) == 1
    s = d["suspensions"][0]
    assert s["last_normal_date"] == "2026-01-10"
    assert s["resume_date"] == "2026-01-15"
    assert s["missing_td"] == 3
    assert abs(s["gap_pct"] - (-0.20)) < 0.001
```

- [x] **Step 3: Run tests to confirm they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
pytest tests/test_api_ticker_full.py::test_full_includes_suspensions_key -v
```

Expected: `FAILED` — `KeyError: 'suspensions'` or `AssertionError`.

- [x] **Step 4: Add `suspensions` field to `api_ticker_full`**

In `routes/screener.py`, inside `api_ticker_full()`, add this block just before `conn.close()`:

```python
# ── SUSPENSIONS ────────────────────────────────────────────────────────
susp_rows = conn.execute("""
    SELECT last_normal_date, resume_date, missing_td, gap_pct
    FROM suspension_events
    WHERE ticker=? AND classification='suspension'
    ORDER BY resume_date DESC
""", (ticker,)).fetchall()
suspensions = [
    {
        'last_normal_date': r[0],
        'resume_date':      r[1],
        'missing_td':       r[2],
        'gap_pct':          round(r[3], 4),
    }
    for r in susp_rows
]
```

Then add `'suspensions': suspensions,` to the `return jsonify({...})` dict.

- [x] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_api_ticker_full.py::test_full_includes_suspensions_key \
       tests/test_api_ticker_full.py::test_suspensions_only_includes_suspension_classification \
       tests/test_api_ticker_full.py::test_suspensions_has_correct_fields -v
```

Expected: all 3 PASS.

- [x] **Step 6: Commit**

```bash
git add routes/screener.py tests/test_api_ticker_full.py
git commit -m "feat(g9): add suspensions field to /api/ticker/full"
```

---

## Task 2: `recommended_strategy` field

**Files:**
- Modify: `routes/screener.py` (inside `api_ticker_full`)
- Modify: `tests/test_api_ticker_full.py` (add tests)

- [x] **Step 1: Write failing tests**

Append to `tests/test_api_ticker_full.py`:

```python
# ── G10: recommended_strategy ──────────────────────────────────────────────


def test_full_includes_recommended_strategy_key(client):
    d = _get_full(client)
    assert "recommended_strategy" in d


def test_recommended_strategy_is_string_or_none(client):
    d = _get_full(client)
    assert d["recommended_strategy"] is None or isinstance(d["recommended_strategy"], str)
```

- [x] **Step 2: Run to confirm failure**

```bash
pytest tests/test_api_ticker_full.py::test_full_includes_recommended_strategy_key -v
```

Expected: `FAILED` — `KeyError`.

- [x] **Step 3: Implement `recommended_strategy`**

In `routes/screener.py`, add two module-level constants near the top of the file (after the imports, before the first route):

```python
# Regime × ADX → recommended strategy display name
_REGIME_STRATEGY_MAP = {
    ('BULL',     'low'):  'Vol-Weighted Entry',
    ('BULL',     'mid'):  'Trend Following Breakout',
    ('BULL',     'high'): 'Conservative Confirm',
    ('BEAR',     'any'):  None,
    ('SIDEWAYS', 'any'):  'VWAP Reversion',
}

def _adx_band(adx: float) -> str:
    if adx < 25:  return 'low'
    if adx <= 40: return 'mid'
    return 'high'
```

Then inside `api_ticker_full()`, after the `regime = detect_regime(df)` call:

```python
# ── RECOMMENDED STRATEGY ───────────────────────────────────────────────
from engine.indicators import calc_adx as _calc_adx
try:
    _adx_val = float(_calc_adx(df, 14).iloc[-1])
except Exception:
    _adx_val = 0.0

if regime in ('BEAR', 'SIDEWAYS'):
    recommended_strategy = _REGIME_STRATEGY_MAP.get((regime, 'any'))
else:
    recommended_strategy = _REGIME_STRATEGY_MAP.get((regime, _adx_band(_adx_val)))
```

Add `'recommended_strategy': recommended_strategy,` to the `return jsonify({...})` dict.

- [x] **Step 4: Run tests**

```bash
pytest tests/test_api_ticker_full.py::test_full_includes_recommended_strategy_key \
       tests/test_api_ticker_full.py::test_recommended_strategy_is_string_or_none -v
```

Expected: both PASS.

- [x] **Step 5: Commit**

```bash
git add routes/screener.py tests/test_api_ticker_full.py
git commit -m "feat(g10): add recommended_strategy field to /api/ticker/full"
```

---

## Task 3: `fundamental` field with flags

**Files:**
- Modify: `routes/screener.py`
- Modify: `tests/test_api_ticker_full.py`

- [x] **Step 1: Write failing tests**

Append to `tests/test_api_ticker_full.py`:

```python
# ── G12: fundamental ───────────────────────────────────────────────────────


def test_full_includes_fundamental_key(client):
    d = _get_full(client)
    assert "fundamental" in d


def test_fundamental_null_when_no_keystats(client):
    # fixture has no keystats rows for TEST
    d = _get_full(client)
    assert d["fundamental"] is None


def test_fundamental_fields_and_flag_der(client):
    c, db = client
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO stockbit_keystats "
        "(ticker, fetch_date, npm, der, earn_growth, updated_at) "
        "VALUES ('TEST', '2026-01-30', -2.5, 3.8, 50.0, '2026-01-30T10:00:00')"
    )
    conn.commit()
    conn.close()
    d = _get_full(client)
    f = d["fundamental"]
    assert f is not None
    assert abs(f["npm"] - (-2.5)) < 0.01
    assert abs(f["der"] - 3.8) < 0.01
    assert "NPM negative" in f["flags"]
    assert "DER > 3" in f["flags"]
    assert "EPS loss" not in f["flags"]


def test_fundamental_flag_eps_loss(client):
    c, db = client
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO stockbit_keystats "
        "(ticker, fetch_date, npm, der, earn_growth, updated_at) "
        "VALUES ('TEST', '2026-01-31', 5.0, 1.5, -150.0, '2026-01-31T10:00:00')"
    )
    conn.commit()
    conn.close()
    d = _get_full(client)
    assert "EPS loss" in d["fundamental"]["flags"]
    assert "NPM negative" not in d["fundamental"]["flags"]


def test_fundamental_empty_flags_when_healthy(client):
    c, db = client
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO stockbit_keystats "
        "(ticker, fetch_date, npm, der, earn_growth, updated_at) "
        "VALUES ('TEST', '2026-02-01', 8.0, 1.2, 20.0, '2026-02-01T10:00:00')"
    )
    conn.commit()
    conn.close()
    d = _get_full(client)
    assert d["fundamental"]["flags"] == []
```

- [x] **Step 2: Run to confirm failure**

```bash
pytest tests/test_api_ticker_full.py::test_full_includes_fundamental_key -v
```

Expected: `FAILED` — `KeyError`.

- [x] **Step 3: Implement `fundamental` field**

In `routes/screener.py`, add before `conn.close()`:

```python
# ── FUNDAMENTAL FLAGS ──────────────────────────────────────────────────
ks = conn.execute("""
    SELECT npm, der, earn_growth
    FROM stockbit_keystats
    WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1
""", (ticker,)).fetchone()

if ks is None:
    fundamental = None
else:
    npm, der, earn_growth = ks
    flags = []
    if npm is not None and npm < 0:
        flags.append('NPM negative')
    if der is not None and der > 3:
        flags.append('DER > 3')
    if earn_growth is not None and earn_growth < -100:
        flags.append('EPS loss')
    fundamental = {
        'npm':         npm,
        'der':         der,
        'earn_growth': earn_growth,
        'flags':       flags,
    }
```

Add `'fundamental': fundamental,` to the `return jsonify({...})` dict.

- [x] **Step 4: Run all backend tests**

```bash
pytest tests/test_api_ticker_full.py -v
```

Expected: all tests PASS (3 from Task 1 + 2 from Task 2 + 5 from Task 3 = 10 total).

- [x] **Step 5: Run full suite to check no regressions**

```bash
pytest --tb=short -q
```

Expected: existing tests still pass.

- [x] **Step 6: Commit**

```bash
git add routes/screener.py tests/test_api_ticker_full.py
git commit -m "feat(g12): add fundamental field with flags to /api/ticker/full"
```

---

## Task 4: Frontend infrastructure — `_contextMarkers` + `refreshContextMarkers` + fix `runSelectedStrategy`

**Files:**
- Modify: `templates/dive.html`

No automated test for pure LWC DOM code — verified visually in Task 9.

- [x] **Step 1: Add `_contextMarkers` module variable**

In `templates/dive.html`, find the line:

```js
let _rawCandles = [];
```

Add immediately after it:

```js
let _contextMarkers = [];  // G9 + G11 markers — persist across strategy changes
```

- [x] **Step 2: Add `refreshContextMarkers()` helper**

Find the line:

```js
const _markerCache = {};   // key → markers[]
```

Add this function immediately before it:

```js
function refreshContextMarkers() {
    if (!_candleSeries) return;
    const sorted = [..._contextMarkers]
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    _candleSeries.setMarkers(sorted);
}
```

- [x] **Step 3: Update `runSelectedStrategy()` — clear case**

Find the block:

```js
    if (!key) {
      _candleSeries.setMarkers([]);
      if (countEl) countEl.style.display = 'none';
      return;
    }
```

Replace `_candleSeries.setMarkers([])` with `refreshContextMarkers()`:

```js
    if (!key) {
      refreshContextMarkers();
      if (countEl) countEl.style.display = 'none';
      return;
    }
```

- [x] **Step 4: Update `runSelectedStrategy()` — non-daily timeframe case**

Find the block:

```js
    if (_currentTf !== 'D') {
      _candleSeries.setMarkers([]);
      if (countEl) {
        countEl.textContent = 'daily only';
        countEl.style.display = 'inline-block';
      }
      return;
    }
```

Replace `_candleSeries.setMarkers([])` with `refreshContextMarkers()`:

```js
    if (_currentTf !== 'D') {
      refreshContextMarkers();
      if (countEl) {
        countEl.textContent = 'daily only';
        countEl.style.display = 'inline-block';
      }
      return;
    }
```

- [x] **Step 5: Update `runSelectedStrategy()` — merge with context markers**

Find the line:

```js
    _candleSeries.setMarkers(markers);
```

(This is the line just after `_markerCache[key] = markers;` assignment.) Replace it with:

```js
    const _merged = [..._contextMarkers, ...markers]
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    _candleSeries.setMarkers(_merged);
```

- [x] **Step 6: Commit**

```bash
git add templates/dive.html
git commit -m "feat(g9-g11): add _contextMarkers infrastructure to dive.html"
```

---

## Task 5: G9 — `renderSuspensions()` + G10 — regime hint in `renderPrice()`

**Files:**
- Modify: `templates/dive.html`

- [x] **Step 1: Add `renderSuspensions()` function**

Find the function `function renderPremover(pm) {` and add the following new function immediately before it:

```js
  function renderSuspensions(suspensions) {
    if (!suspensions || !suspensions.length) return;
    suspensions.forEach(function(s) {
      const pct = (s.gap_pct * 100).toFixed(1);
      const sign = s.gap_pct >= 0 ? '+' : '';
      _contextMarkers.push({
        time:     s.resume_date,
        position: 'aboveBar',
        color:    '#ef4444',
        shape:    'arrowDown',
        text:     'SUSP ' + s.missing_td + 'd ' + sign + pct + '%',
      });
    });
    refreshContextMarkers();
  }
```

- [x] **Step 2: Update `renderPrice()` signature for G10**

Find the existing function signature:

```js
  function renderPrice(p, regime) {
```

Change to:

```js
  function renderPrice(p, regime, recommendedStrategy) {
```

- [x] **Step 3: Add tooltip to the regime badge inside `renderPrice()`**

Find these two lines inside `renderPrice()`:

```js
    rb.textContent = regime || '—';
    rb.className = 'regime-badge ' + (regime || '');
```

Add one line after them:

```js
    rb.title = recommendedStrategy
      ? 'Recommended: ' + recommendedStrategy
      : (regime === 'BEAR' ? 'No entry in BEAR regime' : '');
```

- [x] **Step 4: Commit**

```bash
git add templates/dive.html
git commit -m "feat(g9-g10): add renderSuspensions and regime strategy hint"
```

---

## Task 6: G11 — `renderCrashMarkers()` crash detection

**Files:**
- Modify: `templates/dive.html`

- [x] **Step 1: Add `renderCrashMarkers()` function**

Find the function `function renderSuspensions(suspensions) {` added in Task 5 and add the following new function immediately before it:

```js
  function renderCrashMarkers() {
    var candles = _rawCandles;
    if (!candles || candles.length < 11) return;
    var window = 10;
    var threshold = -0.20;
    // collect candidate crash zones: {bar index, drop pct}
    var candidates = [];
    for (var i = 1; i < candles.length - window + 1; i++) {
      var refClose = candles[i - 1].close;
      if (!refClose) continue;
      var minClose = refClose, minIdx = i;
      for (var j = i; j < i + window && j < candles.length; j++) {
        if (candles[j].close < minClose) { minClose = candles[j].close; minIdx = j; }
      }
      var drop = (minClose - refClose) / refClose;
      if (drop < threshold) {
        candidates.push({ idx: minIdx, drop: drop });
      }
    }
    // de-duplicate: merge candidates within 5 bars, keep worst drop
    var survivors = [];
    candidates.forEach(function(c) {
      var merged = false;
      for (var k = 0; k < survivors.length; k++) {
        if (Math.abs(survivors[k].idx - c.idx) <= 5) {
          if (c.drop < survivors[k].drop) survivors[k] = c;
          merged = true;
          break;
        }
      }
      if (!merged) survivors.push(c);
    });
    survivors.forEach(function(s) {
      _contextMarkers.push({
        time:     candles[s.idx].time,
        position: 'aboveBar',
        color:    '#dc2626',
        shape:    'arrowDown',
        text:     'CRASH ' + (s.drop * 100).toFixed(0) + '%',
      });
    });
    if (survivors.length) refreshContextMarkers();
  }
```

- [x] **Step 2: Call `renderCrashMarkers()` after chart data loads**

Find the line at the end of `fetchAndRender`'s success block:

```js
    _lwChart.timeScale().fitContent();

    // Re-apply active strategy markers after data reload (TF switch)
    if (_activeStrategy) {
      setTimeout(() => runSelectedStrategy(), 50);
    }
```

Add `renderCrashMarkers();` just before the `_lwChart.timeScale().fitContent();` line:

```js
    renderCrashMarkers();
    _lwChart.timeScale().fitContent();

    // Re-apply active strategy markers after data reload (TF switch)
    if (_activeStrategy) {
      setTimeout(() => runSelectedStrategy(), 50);
    }
```

- [x] **Step 3: Clear `_contextMarkers` at the top of `fetchAndRender` to avoid duplicates on TF switch**

Find the beginning of the `fetchAndRender` function. The function sets chart data via `_candleSeries.setData(candleData)`. Add a reset just before the crash markers call added in Step 2:

```js
    _contextMarkers = [];   // reset before re-populating (TF switch or reload)
    renderCrashMarkers();
```

Replace the single `renderCrashMarkers();` line added in Step 2 with both lines above.

Note: This means on TF switch, suspension markers are temporarily lost until `loadFull()` re-runs. Since `loadFull()` is called once on page load and isn't re-called on TF switch, also call `renderSuspensions` with cached data. Handle this in Task 8 (wire-up).

- [x] **Step 4: Commit**

```bash
git add templates/dive.html
git commit -m "feat(g11): add crash annotation markers to dive.html chart"
```

---

## Task 7: G12 — fundamental red flag badge

**Files:**
- Modify: `templates/dive.html`

- [x] **Step 1: Add HTML badge to topbar**

Find the topbar HTML:

```html
  <span class="pm-badge" id="tb-pm" title="Pre-mover setup score">Setup —</span>
```

Add immediately after it:

```html
  <span class="fund-badge" id="tb-fund" style="display:none"></span>
```

- [x] **Step 2: Add CSS for `.fund-badge`**

Find the existing `.pm-badge` CSS block (around line 107):

```css
    .pm-badge {
```

Add the following new rule immediately after the `.pm-badge` block (after its closing `}`):

```css
    .fund-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      background: rgba(239,68,68,.15);
      color: #ef4444;
      white-space: nowrap;
      cursor: default;
    }
```

- [x] **Step 3: Add `renderFundamental()` JS function**

Find the `function renderPremover(pm) {` function. Add the following new function immediately before it:

```js
  function renderFundamental(fundamental) {
    var el = document.getElementById('tb-fund');
    if (!fundamental || !fundamental.flags || !fundamental.flags.length) return;
    el.textContent = '⚠️ ' + fundamental.flags.join(' | ');
    var parts = [];
    if (fundamental.npm  != null) parts.push('NPM ' + fundamental.npm.toFixed(1) + '%');
    if (fundamental.der  != null) parts.push('DER ' + fundamental.der.toFixed(2) + 'x');
    if (fundamental.earn_growth != null) parts.push('EPS growth ' + fundamental.earn_growth.toFixed(0) + '%');
    el.title = parts.join(' · ');
    el.style.display = '';
  }
```

- [x] **Step 4: Commit**

```bash
git add templates/dive.html
git commit -m "feat(g12): add fundamental red flag badge to dive.html topbar"
```

---

## Task 8: Wire `loadFull()` + cache suspensions for TF switch

**Files:**
- Modify: `templates/dive.html`

- [x] **Step 1: Cache suspensions at module level**

Find the line:

```js
let _contextMarkers = [];  // G9 + G11 markers — persist across strategy changes
```

Add immediately after it:

```js
let _suspensionsCache = [];  // cached from /full for re-application on TF switch
```

- [x] **Step 2: Update `renderSuspensions()` to save to cache**

Find the `renderSuspensions` function added in Task 5 and update it to save to the cache:

```js
  function renderSuspensions(suspensions) {
    if (!suspensions || !suspensions.length) return;
    _suspensionsCache = suspensions;   // save for TF switch re-application
    suspensions.forEach(function(s) {
      var pct = (s.gap_pct * 100).toFixed(1);
      var sign = s.gap_pct >= 0 ? '+' : '';
      _contextMarkers.push({
        time:     s.resume_date,
        position: 'aboveBar',
        color:    '#ef4444',
        shape:    'arrowDown',
        text:     'SUSP ' + s.missing_td + 'd ' + sign + pct + '%',
      });
    });
    refreshContextMarkers();
  }
```

- [x] **Step 3: Re-apply suspensions after TF switch resets `_contextMarkers`**

In Task 6 Step 3, we added `_contextMarkers = []` then `renderCrashMarkers()`. Now add suspension re-application after crash markers:

Find the block added in Task 6:

```js
    _contextMarkers = [];   // reset before re-populating (TF switch or reload)
    renderCrashMarkers();
```

Replace with:

```js
    _contextMarkers = [];   // reset before re-populating (TF switch or reload)
    renderCrashMarkers();
    renderSuspensions(_suspensionsCache);
```

- [x] **Step 4: Wire all render functions into `loadFull()`**

Find the `loadFull()` function. It currently ends with:

```js
    renderPrice(d.price, d.regime);
    renderStrategies(d.strategies, d.price.close);
    renderVpin(d.vpin);
    try { renderFlow(d.flow); }
    catch(e) { document.getElementById('flow-loading').textContent = 'Error loading flow data.'; }
    try { renderBroker(d.broker); }
    catch(e) { document.getElementById('broker-loading').textContent = 'Error loading broker data.'; }
    if (d.premover) renderPremover(d.premover);
```

Make these changes:

1. Update `renderPrice` call to pass `d.recommended_strategy`:
```js
    renderPrice(d.price, d.regime, d.recommended_strategy);
```

2. Add after `if (d.premover) renderPremover(d.premover);`:
```js
    renderSuspensions(d.suspensions || []);
    renderFundamental(d.fundamental);
```

Full updated block:
```js
    renderPrice(d.price, d.regime, d.recommended_strategy);
    renderStrategies(d.strategies, d.price.close);
    renderVpin(d.vpin);
    try { renderFlow(d.flow); }
    catch(e) { document.getElementById('flow-loading').textContent = 'Error loading flow data.'; }
    try { renderBroker(d.broker); }
    catch(e) { document.getElementById('broker-loading').textContent = 'Error loading broker data.'; }
    if (d.premover) renderPremover(d.premover);
    renderSuspensions(d.suspensions || []);
    renderFundamental(d.fundamental);
```

- [x] **Step 5: Commit**

```bash
git add templates/dive.html
git commit -m "feat(g9-g12): wire all annotation render calls into loadFull()"
```

---

## Task 9: Smoke test + update TODO.md

**Files:**
- Modify: `TODO.md`

- [x] **Step 1: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
pytest --tb=short -q
```

Expected: all tests pass including the 10 new `test_api_ticker_full.py` tests.

- [x] **Step 2: Start the Flask app and open BRPT in the browser**

```bash
python app.py &
```

Open `http://localhost:5001/dive/BRPT` in a browser.

Verify:
- **G9**: Chart shows a red `▼ SUSP 5d -22%` marker at the May 25 resumption bar.
- **G10**: Hover over the regime badge (e.g. "SIDEWAYS") — tooltip shows "Recommended: vwap_reversion".
- **G11**: If BRPT has any 10-bar window with >20% drop, a red `▼ CRASH -XX%` marker appears.
- **G12**: If BRPT has DER > 3 (it does: 3.47), topbar shows `⚠️ DER > 3` badge in red.
- Switching to 1H or 1W timeframe: context markers remain visible.
- Selecting a strategy from dropdown: strategy markers appear merged with context markers.
- Deselecting strategy (choosing "— Strategy —"): context markers remain, strategy markers clear.

- [x] **Step 3: Mark G9–G12 complete in TODO.md**

In `TODO.md`, find the G9–G12 items under `## 🔲 Sprint 17` and change their `- [ ]` to `- [x]`, adding `SHIPPED 2026-06-04` after each description. Also update the `_Last updated` line at the top.

- [x] **Step 4: Final commit**

```bash
git add TODO.md
git commit -m "chore: mark G9-G12 complete in TODO.md"
```
