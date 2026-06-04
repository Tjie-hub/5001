# dive.html Chart Annotations & Badges — Design Spec
_Sprint 17 items G9, G10, G11, G12_
_Date: 2026-06-04_

---

## Overview

Four visual improvements to `templates/dive.html` that surface backend intelligence (suspension events, regime strategy hint, crash detection, fundamental flags) directly on the stock detail page without requiring the user to read logs or cross-reference other views.

All features share a single load path: `loadFull()` calls `/api/ticker/<ticker>/full` (one round trip). Three features add new keys to that response. One feature (G11 crash annotation) is computed purely from `_rawCandles` client-side.

---

## Architecture

```
loadFull()  →  GET /api/ticker/<ticker>/full
                │
                ├── d.suspensions       → renderSuspensions() → _contextMarkers
                ├── d.recommended_strategy → renderPrice()   → #tb-regime tooltip
                ├── d.fundamental       → renderFundamental() → #tb-fund badge
                └── (chart loaded)      → renderCrashMarkers() → _contextMarkers

_contextMarkers (module-level array)
    merged into every applyStrategyMarkers() call
    → _candleSeries.setMarkers([..._contextMarkers, ...strategyMarkers].sort by time)
```

---

## Backend — `routes/screener.py`

### 1. ADX value for `recommended_strategy` lookup

`detect_regime(df)` has 10+ callers across the codebase that depend on it returning a string — do not change its signature. Instead, compute ADX inline in `api_ticker_full` using the already-imported `calc_adx` from `engine.indicators`:

```python
from engine.indicators import calc_adx
adx_series = calc_adx(df, 14)
adx = float(adx_series.iloc[-1]) if not adx_series.empty else 0.0
```

This runs after `detect_regime(df)` and uses the same computation it does internally.

### 2. New field: `suspensions`

Query `suspension_events` for all `classification='suspension'` events for the ticker, ordered by `resume_date DESC`:

```python
susp_rows = conn.execute("""
    SELECT last_normal_date, resume_date, missing_td, gap_pct
    FROM suspension_events
    WHERE ticker=? AND classification='suspension'
    ORDER BY resume_date DESC
""", (ticker,)).fetchall()
suspensions = [
    {'last_normal_date': r[0], 'resume_date': r[1],
     'missing_td': r[2], 'gap_pct': round(r[3], 4)}
    for r in susp_rows
]
```

### 3. New field: `recommended_strategy`

Hardcoded regime×ADX → strategy lookup, computed after `detect_regime()`:

| Regime   | ADX       | recommended_strategy           |
|----------|-----------|-------------------------------|
| BULL     | 25–40     | `"Trend Following Breakout"`   |
| BULL     | > 40      | `"Conservative Confirm"`       |
| BULL     | < 25      | `"vol_weighted"`               |
| BEAR     | any       | `None`                         |
| SIDEWAYS | any       | `"vwap_reversion"`             |
| UNKNOWN  | any       | `None`                         |

Returns `None` (serialised as JSON `null`) when no entry is recommended.

### 4. New field: `fundamental`

Query most recent row from `stockbit_keystats`:

```python
ks = conn.execute("""
    SELECT npm, der, earn_growth FROM stockbit_keystats
    WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1
""", (ticker,)).fetchone()
```

Compute `flags` list server-side:
- `npm < 0` → `"NPM negative"`
- `der > 3` → `"DER > 3"`
- `earn_growth < -100` → `"EPS loss"`

Return `None` if no keystats row. Otherwise:
```json
{"npm": 3.52, "der": 3.47, "earn_growth": 476.97, "flags": ["DER > 3"]}
```

### 5. Updated `return jsonify({...})`

Add three keys:
```python
'suspensions':          suspensions,
'recommended_strategy': recommended_strategy,
'fundamental':          fundamental,
```

---

## Frontend — `templates/dive.html`

### Module-level state

```js
let _contextMarkers = [];   // G9 + G11 markers, persist across strategy changes
```

### G9 — Suspension markers

New function `renderSuspensions(suspensions)` called from `loadFull()` after chart data arrives:

```js
function renderSuspensions(suspensions) {
    if (!suspensions?.length) return;
    suspensions.forEach(s => {
        const pct = (s.gap_pct * 100).toFixed(1);
        const sign = s.gap_pct >= 0 ? '+' : '';
        _contextMarkers.push({
            time:      s.resume_date,
            position:  'aboveBar',
            color:     '#ef4444',
            shape:     'arrowDown',
            text:      `SUSP ${s.missing_td}d ${sign}${pct}%`,
        });
    });
    refreshContextMarkers();   // re-render with context markers visible
}
```

Call site in `loadFull()`:
```js
renderSuspensions(d.suspensions);
```

### G10 — Regime strategy hint

`renderPrice(p, regime, recommendedStrategy)` gains a third parameter. The existing `#tb-regime` badge gets a `title` attribute:

```js
rb.title = recommendedStrategy
    ? `Recommended: ${recommendedStrategy}`
    : (regime === 'BEAR' ? 'No entry in BEAR regime' : '');
```

`loadFull()` passes `d.recommended_strategy`:
```js
renderPrice(d.price, d.regime, d.recommended_strategy);
```

### G11 — Crash annotations

New function `renderCrashMarkers()` called after `_rawCandles` is populated (end of `initChart()`):

**Algorithm:**
1. For each bar `i` from index 1 to `n-1`, compute `maxDrop = min(close[i..i+9]) / close[i-1] - 1`.
2. If `maxDrop < -0.20`, find `argmin` (the bar index of the lowest close in that window).
3. Collect all such `argmin` indices, de-duplicate by merging any two within 5 bars (keep the worse one).
4. For each survivor, push a marker:

```js
{
    time:     _rawCandles[argmin].time,
    position: 'aboveBar',
    color:    '#ef4444',
    shape:    'arrowDown',
    text:     `CRASH ${(drop*100).toFixed(0)}%`,
}
```

Results appended to `_contextMarkers`. Calls `refreshContextMarkers()` after.

### G12 — Fundamental flag badge

**HTML** — new `<span>` in topbar after `#tb-pm`:
```html
<span class="fund-badge" id="tb-fund" style="display:none"></span>
```

**CSS:**
```css
.fund-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
    background: rgba(239,68,68,.15);
    color: #ef4444;
    white-space: nowrap;
}
```

**JS** — new `renderFundamental(fundamental)` called from `loadFull()`:
```js
function renderFundamental(fundamental) {
    const el = document.getElementById('tb-fund');
    if (!fundamental?.flags?.length) return;
    el.textContent = '⚠️ ' + fundamental.flags.join(' | ');
    el.title = [
        fundamental.npm  != null ? `NPM ${fundamental.npm.toFixed(1)}%`   : '',
        fundamental.der  != null ? `DER ${fundamental.der.toFixed(2)}x`   : '',
        fundamental.earn_growth != null ? `EPS growth ${fundamental.earn_growth.toFixed(0)}%` : '',
    ].filter(Boolean).join(' · ');
    el.style.display = '';
}
```

### New `refreshContextMarkers()` helper

Used by G9/G11 to render context markers immediately (before any strategy is selected):

```js
function refreshContextMarkers() {
    if (!_candleSeries) return;
    const sorted = [..._contextMarkers]
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    _candleSeries.setMarkers(sorted);
}
```

### Updated `runSelectedStrategy()`

Two changes:

1. **Clear case** (`!key`): replace `_candleSeries.setMarkers([])` with `refreshContextMarkers()` so context markers survive strategy deselection.

2. **Active strategy case**: replace `_candleSeries.setMarkers(markers)` with a merged+sorted call:

```js
const merged = [..._contextMarkers, ...markers]
    .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
_candleSeries.setMarkers(merged);
```

The non-daily timeframe branch (`_currentTf !== 'D'`) also replaces `setMarkers([])` with `refreshContextMarkers()` so suspension and crash markers remain visible on 1H/1W views.

---

## Error handling

- `suspensions`: missing table or query error → catch, return `[]`. Frontend renders nothing.
- `recommended_strategy`: `detect_regime()` throws → catch, return `null`. Existing `regime = 'UNKNOWN'` fallback unchanged.
- `fundamental`: no keystats row → return `null`. `renderFundamental(null)` no-ops.
- G11 crash scan: `_rawCandles` empty or < 11 bars → early return, no markers.

---

## Out of scope

- G9 shaded background band (deferred — requires custom `ISeriesPrimitive`).
- G10 live ADX-derived strategy recommendation (uses hardcoded lookup table per design decision).
- G12 displaying all keystats values — only `npm`, `der`, `earn_growth` surfaced; full fundamentals page is a separate feature.
