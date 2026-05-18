# PLAN.md — Strategy Modularization Refactor for dive.html

**Role**: Senior Frontend Architect  
**Scope**: `/templates/dive.html`  
**Goal**: Extract hardcoded strategy logic into a pluggable JavaScript registry with UI controls  
**Constraint**: Chart engine (`LightweightCharts.createChart`, candlestick series, volume pane) must remain untouched. Only markers (`series.setMarkers`) change per strategy.

---

## Context & Current State

The `dive.html` file currently renders a stock chart using `lightweight-charts` and displays strategy signals in a **read-only table** fetched from `/api/ticker/<ticker>/full`.

### Current Architecture Flow
```
Server (Python backtest)
    ↓  JSON
renderStrategies() → static HTML table
    
fetchAndRender() → LightweightCharts.createChart()
    ├── Candlestick series (OHLCV)
    ├── Volume histogram
    ├── VWMA 20 line
    └── Volume Profile plugin
```

### Problem
- Strategy signals are **pre-computed on the server**. The frontend cannot run, compare, or visualize different strategies interactively.
- No way for the user to select a strategy and see its **buy/sell markers** plotted directly on the chart.
- The `renderStrategies()` function (line 683) only renders a text table. No chart integration.

### Target Architecture
```
User selects strategy from dropdown
    ↓
JavaScript strategy registry executes on _rawCandles
    ↓
Returns marker array [{time, position, color, shape, text}]
    ↓
candles.setMarkers(markers)  ← only chart mutation
```

---

## Phase 1: Analysis — Identify Current Code Sections

### 1.1 Chart Container & Overlays (Lines 348–364)
The chart has two existing overlay panels inside `#lw_chart_wrap`:
- `.tf-overlay` (top-left): Timeframe buttons (1H, 1D, 1W)
- `.ind-overlay` (top-right): Indicator toggles (VWMA 20, Vol Profile)

**We will add a third overlay panel** below `.tf-overlay` for the strategy selector.

### 1.2 Chart Creation & Data Storage (Lines 544–622)
Inside `fetchAndRender(tf)`:
- `_rawCandles = data.candles` (line 604) stores the full OHLCV array globally.
- `candles` variable (line 576) is the candlestick series instance — this is what receives `setMarkers()`.
- **CRITICAL**: `candles` is a local variable inside `fetchAndRender()`. We must **promote it to module scope** so `runSelectedStrategy()` can access it later.

### 1.3 Strategy Data Rendering (Lines 683–706)
`renderStrategies(strats, closePrice)` renders the server-provided strategy table. It does **not** touch the chart.

**Decision**: We keep `renderStrategies()` as-is for reference (walk-forward scores). The new modular system runs **independently** on the client side and only affects chart markers.

### 1.4 Global State (Lines 424–431)
Key globals already available:
```js
let _rawCandles = [];   // OHLCV array available after fetchAndRender()
let _lwChart = null;    // Chart instance
```

We will add:
```js
let _candleSeries = null;  // NEW: module-scoped candlestick series for setMarkers()
```

---

## Phase 2: Modularization — Build the Strategy Registry

### 2.1 Strategy Interface Contract

Every strategy is a plain JavaScript object with:
```js
{
  name: string,           // Display name
  description: string,    // Tooltip text
  run: function(candles)  // → Array<Marker>
}
```

**Marker shape** (lightweight-charts v4 format):
```js
{
  time: string,           // ISO date or epoch
  position: 'aboveBar' | 'belowBar' | 'inBar',
  color: string,
  shape: 'arrowUp' | 'arrowDown' | 'circle',
  text: string,           // Optional label
  size: number            // 1–4
}
```

### 2.2 Strategy Registry Definition

Insert this code block **after the global variable declarations** (after line 431) and **before `toggleDrawer()`**:

```js
// ═══════════════════════════════════════════════════════════════
// STRATEGY REGISTRY
// ═══════════════════════════════════════════════════════════════

const strategies = {

  Momentum: {
    name: 'Momentum Following',
    description: '2 consecutive higher closes + volume ratio > 1.3x',
    run(candles) {
      const markers = [];
      const N = candles.length;
      if (N < 22) return markers;

      // Pre-compute avg volume (20-period)
      const avgVol = [];
      for (let i = 0; i < N; i++) {
        let sum = 0, count = 0;
        for (let j = Math.max(0, i - 19); j <= i; j++) {
          sum += candles[j].volume;
          count++;
        }
        avgVol.push(sum / count);
      }

      for (let i = 2; i < N; i++) {
        const c0 = candles[i];
        const c1 = candles[i - 1];
        const c2 = candles[i - 2];

        // Entry: 2 up days + volume spike
        const streak2 = c1.close > c2.close && c0.close > c1.close;
        const volOk = avgVol[i] > 0 && c0.volume / avgVol[i] > 1.3;

        if (streak2 && volOk) {
          markers.push({
            time: c0.time,
            position: 'belowBar',
            color: '#22c55e',
            shape: 'arrowUp',
            text: 'M',
            size: 2,
          });
        }
      }
      return markers;
    },
  },

  Flow: {
    name: 'Order Flow',
    description: 'Delta-based: net positive flow for 3+ consecutive bars',
    run(candles) {
      const markers = [];
      const N = candles.length;
      if (N < 5) return markers;

      // Compute delta per bar: (close - open) / (high - low) * volume
      const deltas = candles.map(c => {
        const range = c.high - c.low;
        if (range === 0) return 0;
        return ((c.close - c.open) / range) * c.volume;
      });

      let positiveStreak = 0;
      for (let i = 0; i < N; i++) {
        if (deltas[i] > 0) {
          positiveStreak++;
        } else {
          positiveStreak = 0;
        }

        // Signal after 3+ positive deltas
        if (positiveStreak >= 3) {
          // Only mark once per streak
          const prev = markers[markers.length - 1];
          if (!prev || prev.time !== candles[i - 1]?.time) {
            markers.push({
              time: candles[i].time,
              position: 'belowBar',
              color: '#6366f1',
              shape: 'arrowUp',
              text: 'F',
              size: 2,
            });
          }
        }
      }
      return markers;
    },
  },

  VWAPReversion: {
    name: 'VWAP Reversion',
    description: 'Price > 1.5% below VWAP + volume spike',
    run(candles) {
      const markers = [];
      const N = candles.length;
      if (N < 60) return markers;

      // Compute VWAP (cumulative)
      let cumTPVol = 0, cumVol = 0;
      const vwap = [];
      for (let i = 0; i < N; i++) {
        const tp = (candles[i].high + candles[i].low + candles[i].close) / 3;
        cumTPVol += tp * candles[i].volume;
        cumVol += candles[i].volume;
        vwap.push(cumTPVol / cumVol);
      }

      // Compute 20-period avg volume
      const avgVol = [];
      for (let i = 0; i < N; i++) {
        let sum = 0;
        for (let j = Math.max(0, i - 19); j <= i; j++) sum += candles[j].volume;
        avgVol.push(sum / Math.min(i + 1, 20));
      }

      for (let i = 60; i < N; i++) {
        const c = candles[i];
        const dist = (c.close - vwap[i]) / vwap[i];
        const volOk = avgVol[i] > 0 && c.volume / avgVol[i] > 1.3;

        if (dist < -0.015 && volOk) {
          markers.push({
            time: c.time,
            position: 'belowBar',
            color: '#eab308',
            shape: 'arrowUp',
            text: 'V',
            size: 2,
          });
        }
      }
      return markers;
    },
  },

  Conservative: {
    name: 'Conservative',
    description: 'Vol ratio > 1.3 + close > open + above MA20 + normal ATR',
    run(candles) {
      const markers = [];
      const N = candles.length;
      if (N < 25) return markers;

      // Compute MA20
      const ma20 = [];
      for (let i = 0; i < N; i++) {
        let sum = 0;
        for (let j = Math.max(0, i - 19); j <= i; j++) sum += candles[j].close;
        ma20.push(sum / Math.min(i + 1, 20));
      }

      // Compute ATR14
      const atr = [];
      for (let i = 0; i < N; i++) {
        if (i === 0) { atr.push(candles[i].high - candles[i].low); continue; }
        const tr = Math.max(
          candles[i].high - candles[i].low,
          Math.abs(candles[i].high - candles[i - 1].close),
          Math.abs(candles[i].low - candles[i - 1].close)
        );
        if (i < 14) {
          let sum = 0;
          for (let j = 0; j <= i; j++) {
            const t = j === 0
              ? candles[j].high - candles[j].low
              : Math.max(candles[j].high - candles[j].low,
                         Math.abs(candles[j].high - candles[j - 1].close),
                         Math.abs(candles[j].low - candles[j - 1].close));
            sum += t;
          }
          atr.push(sum / (i + 1));
        } else {
          atr.push((atr[i - 1] * 13 + tr) / 14);
        }
      }

      // Compute ATR MA10
      const atrMA = [];
      for (let i = 0; i < N; i++) {
        let sum = 0;
        for (let j = Math.max(0, i - 9); j <= i; j++) sum += atr[j];
        atrMA.push(sum / Math.min(i + 1, 10));
      }

      // Compute avg volume
      const avgVol = [];
      for (let i = 0; i < N; i++) {
        let sum = 0;
        for (let j = Math.max(0, i - 19); j <= i; j++) sum += candles[j].volume;
        avgVol.push(sum / Math.min(i + 1, 20));
      }

      for (let i = 24; i < N; i++) {
        const c = candles[i];
        const vr = avgVol[i] > 0 ? c.volume / avgVol[i] : 0;
        const bullish = c.close > c.open;
        const aboveMA = c.close > ma20[i];
        const atrOk = atr[i] < atrMA[i] * 1.5;

        if (vr > 1.3 && bullish && aboveMA && atrOk) {
          markers.push({
            time: c.time,
            position: 'belowBar',
            color: '#06b6d4',
            shape: 'arrowUp',
            text: 'C',
            size: 2,
          });
        }
      }
      return markers;
    },
  },

};

// Default active strategy
let _activeStrategy = 'Momentum';

// ═══════════════════════════════════════════════════════════════
```

### 2.3 Promote Candle Series to Module Scope

Inside `fetchAndRender()` (around line 576), change:

```js
// BEFORE (local variable):
const candles = _lwChart.addCandlestickSeries({...});

// AFTER (module-scoped):
_candleSeries = _lwChart.addCandlestickSeries({
  upColor:        '#26A69A', downColor:        '#EF5350',
  borderUpColor:  '#26A69A', borderDownColor:  '#EF5350',
  wickUpColor:    '#26A69A', wickDownColor:    '#EF5350',
});
```

Then replace **all** downstream references from `candles` → `_candleSeries` within `fetchAndRender()`:
- Line 602: `candles.setData(candleData)` → `_candleSeries.setData(candleData)`
- Line 619: `candles.attachPrimitive(_vpPlugin)` → `_candleSeries.attachPrimitive(_vpPlugin)`

**Rationale**: `setMarkers()` must be called on the candlestick series instance. Since `fetchAndRender()` is async and recreates the chart on timeframe change, we store the series reference globally.

---

## Phase 3: UI Binding — Inject Controls

### 3.1 Add Strategy Overlay to Chart

Insert the following HTML **inside `#lw_chart_wrap`**, after the `.ind-overlay` div (after line 357, before line 358):

```html
<!-- Strategy Selector Overlay (bottom-left of chart) -->
<div class="strat-overlay">
  <select id="strat-select" class="strat-select">
    <option value="Momentum" selected>Momentum</option>
    <option value="Flow">Flow</option>
    <option value="VWAPReversion">VWAP Reversion</option>
    <option value="Conservative">Conservative</option>
  </select>
  <button id="strat-run" class="strat-run" onclick="runSelectedStrategy()">▶ Run</button>
</div>
```

### 3.2 Add CSS for the New Overlay

Insert this CSS block **inside the `<style>` section** (after the `.ind-overlay` styles, around line 166):

```css
/* ── STRATEGY OVERLAY ─────────────────────────────── */
.strat-overlay {
  position: absolute; bottom: 10px; left: 12px; z-index: 3;
  display: flex; gap: 6px; align-items: center;
}
.strat-select {
  font-size: 11px; font-weight: 600;
  padding: 4px 10px; border-radius: 6px;
  border: 1px solid var(--border);
  background: rgba(8,9,13,.85); backdrop-filter: blur(10px);
  color: var(--text); cursor: pointer;
  outline: none; min-width: 140px;
}
.strat-select:focus {
  border-color: rgba(99,102,241,.45);
}
.strat-select option {
  background: var(--card); color: var(--text);
}
.strat-run {
  font-size: 11px; font-weight: 700;
  padding: 4px 12px; border-radius: 6px;
  border: 1px solid rgba(99,102,241,.35);
  background: rgba(99,102,241,.18);
  color: var(--accent); cursor: pointer;
  letter-spacing: .03em;
  transition: all .15s;
}
.strat-run:hover {
  background: rgba(99,102,241,.30);
  box-shadow: 0 0 12px var(--accent-glow);
}
.strat-run:active {
  transform: scale(0.96);
}
```

### 3.3 Bind Event Listeners

Insert this function **after the `strategies` registry definition** and **before `toggleDrawer()`**:

```js
// ═══════════════════════════════════════════════════════════════
// STRATEGY RUNNER
// ═══════════════════════════════════════════════════════════════

function runSelectedStrategy() {
  const select = document.getElementById('strat-select');
  const key = select.value;
  const strategy = strategies[key];

  if (!strategy) {
    console.warn('Unknown strategy:', key);
    return;
  }

  if (!_candleSeries || !_rawCandles.length) {
    console.warn('Chart not ready. Wait for data to load.');
    return;
  }

  _activeStrategy = key;

  // 1. Clear existing markers
  _candleSeries.setMarkers([]);

  // 2. Execute strategy
  const markers = strategy.run(_rawCandles);

  // 3. Apply new markers
  _candleSeries.setMarkers(markers);

  // 4. Log for debugging
  console.log(`[Strategy] ${strategy.name} — ${markers.length} signals`);
}
```

### 3.4 Auto-Run on Timeframe Change

After `_lwChart.timeScale().fitContent()` at the end of `fetchAndRender()` (line 621), append:

```js
  // Auto-run active strategy when new data loads
  if (_activeStrategy && strategies[_activeStrategy]) {
    setTimeout(() => runSelectedStrategy(), 50);
  }
```

**Rationale**: When the user switches from 1D → 1H or 1W, new candle data arrives. The previously selected strategy should automatically re-execute on the new dataset.

### 3.5 Update Global Variables Declaration

At the top of the `<script>` block (after line 431), add:

```js
let _candleSeries = null;   // NEW: module-scoped candlestick series
let _activeStrategy = 'Momentum'; // NEW: currently selected strategy key
```

---

## Phase 4: Visualization — Ensure Correct Marker Delivery

### 4.1 Marker Format Verification

lightweight-charts v4 expects markers with these exact fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `time` | Time | Yes | Must match series data time format (ISO string or epoch) |
| `position` | string | Yes | `'aboveBar'`, `'belowBar'`, `'inBar'` |
| `color` | string | Yes | Hex color, e.g. `'#22c55e'` |
| `shape` | string | Yes | `'arrowUp'`, `'arrowDown'`, `'circle'`, `'square'` |
| `text` | string | No | Single-character label recommended |
| `size` | number | No | `1`–`4`, default `1` |

### 4.2 Time Format Compatibility

The current `candleData` mapping (line 589–591) uses `c.time` directly from the server. Ensure the server returns time in a format lightweight-charts accepts:
- **Daily**: `'2024-01-15'` (YYYY-MM-DD)
- **Hourly**: Unix timestamp (number) or `'2024-01-15 09:30'`

The strategy `run()` functions must use the **same time format** as the candle data. Since `_rawCandles` is passed directly, this is guaranteed as long as strategies use `c.time` verbatim.

### 4.3 Clearing Markers on Strategy Switch

The `runSelectedStrategy()` function already calls:
```js
_candleSeries.setMarkers([]);  // Clear old
_candleSeries.setMarkers(markers); // Set new
```

This is the **only** chart mutation. All other chart layers (candles, volume, VWMA, volume profile) remain untouched.

### 4.4 Visual Styling of Markers

Current color assignments per strategy:

| Strategy | Color Code | Color Name | Letter |
|----------|-----------|------------|--------|
| Momentum | `#22c55e` | Green | M |
| Flow | `#6366f1` | Indigo | F |
| VWAP Reversion | `#eab308` | Yellow | V |
| Conservative | `#06b6d4` | Cyan | C |

These colors are distinct from the existing chart palette (green/red candles, amber VWMA, indigo volume profile) to ensure visual separation.

---

## Summary of Line Changes in dive.html

| Phase | Location | Action | Lines Affected |
|-------|----------|--------|----------------|
| 1 | `<style>` after `.ind-overlay` | Add `.strat-overlay`, `.strat-select`, `.strat-run` CSS | ~167–200 (new) |
| 2 | `#lw_chart_wrap` after `.ind-overlay` | Add strategy `<select>` + `<button>` HTML | After line 357 |
| 3 | `<script>` globals after line 431 | Add `_candleSeries`, `_activeStrategy` | ~432–433 |
| 4 | `<script>` after globals | Insert `strategies` registry object | ~434–650 (new) |
| 5 | `<script>` after registry | Insert `runSelectedStrategy()` function | ~651–680 (new) |
| 6 | `fetchAndRender()` line 576 | Change `const candles` → `_candleSeries` | 576 |
| 7 | `fetchAndRender()` line 602 | Change `candles.setData` → `_candleSeries.setData` | 602 |
| 8 | `fetchAndRender()` line 619 | Change `candles.attachPrimitive` → `_candleSeries.attachPrimitive` | 619 |
| 9 | `fetchAndRender()` after line 621 | Add auto-run on timeframe change | After 621 |

**Total**: ~9 edit points, ~300 lines of new code.

---

## Testing Checklist

- [ ] Page loads without console errors
- [ ] Dropdown shows 4 strategies: Momentum, Flow, VWAP Reversion, Conservative
- [ ] Clicking "Run" places arrow markers on the chart
- [ ] Switching strategy clears old markers and shows new ones
- [ ] Switching timeframe (1H ↔ 1D ↔ 1W) re-runs the active strategy automatically
- [ ] Existing features still work: timeframe buttons, indicator toggles, VWMA, volume profile
- [ ] Server-side strategy table (renderStrategies) remains visible and unchanged
- [ ] No markers appear if `_rawCandles` is empty (chart loading state)

---

## Future Extensibility

To add a new strategy:

1. Implement the `run(candles)` function
2. Add an entry to the `strategies` object
3. Add an `<option>` to the `<select>` dropdown

Example:
```js
strategies.MyNewStrategy = {
  name: 'My New Strategy',
  description: '...',
  run(candles) {
    // Your logic here
    return [{ time: candles[i].time, position: 'belowBar', color: '#fff', shape: 'arrowUp', text: 'N', size: 2 }];
  },
};
```

No changes to chart rendering, CSS, or event binding are required.
