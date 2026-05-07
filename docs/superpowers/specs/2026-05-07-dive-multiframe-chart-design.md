# Dive Multi-Timeframe Chart — Design Spec
**Date:** 2026-05-07
**Status:** Approved

## Problem
The `/dive/<ticker>` chart is TradingView-only. TradingView blocks hourly (1H) data for non-authenticated or http-served users. 1D works fine; 1H and 1W do not.

## Solution
Replace the 1H and 1W buttons with a self-hosted lightweight-charts panel backed by yfinance data served from Flask, with SQLite caching. 1D stays on TradingView.

---

## Data Layer

### SQLite table: `ohlcv_cache` (in `walkforward.db`)
```sql
CREATE TABLE IF NOT EXISTS ohlcv_cache (
  ticker    TEXT NOT NULL,
  tf        TEXT NOT NULL,
  fetched_at REAL NOT NULL,
  data      TEXT NOT NULL,
  PRIMARY KEY (ticker, tf)
);
```

### Flask endpoint: `GET /api/ticker/<tk>/ohlcv?tf=1h`
- Accepted `tf` values: `1h`, `1w`
- On request:
  1. Read `ohlcv_cache` for `(ticker, tf)`
  2. If row exists and not expired → return cached `data`
  3. Else → fetch from yfinance, upsert row, return data
- TTL: 15 min for `1h`, 24h for `1w`
- yfinance params:
  - `1h`: `period='60d', interval='1h'`
  - `1w`: `period='2y', interval='1wk'`
- Response shape:
```json
{
  "tf": "1h",
  "ticker": "BRPT",
  "candles": [
    {"time": 1746..., "open": 2370, "high": 2430, "low": 2240, "close": 2400, "volume": 62327700}
  ]
}
```
- `time` is a Unix timestamp (seconds, UTC). lightweight-charts handles timezone display.
- On yfinance error: return `{"error": "..."}` with HTTP 502.
- Empty ticker (delisted/unknown): return `{"error": "no data"}` with HTTP 404.

### Location
New function `api_ohlcv_cache()` added to `app.py`. Cache table initialized in `init_flow_db()` in `stockbit_fetcher.py`.

---

## Frontend

### New dependency
```html
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
```
Added in `<head>` of `dive.html`.

### DOM changes
Two chart containers, mutually exclusive visibility:
```html
<!-- existing, shown only on 1D -->
<div id="tv_chart_wrap"><div id="tv_chart"></div></div>

<!-- new, shown on 1H and 1W -->
<div id="lw_chart_wrap">
  <div id="lw_loading" style="display:none">Loading…</div>
  <div id="lw_chart"></div>
</div>
```

### Chart layout
- Candlestick series (top panel, ~70% height)
- Volume histogram series (bottom panel, ~30% height)
- Dark theme matching CSS vars: background `#0d0f14`, text `#e2e8f0`, up `#22c55e`, down `#ef4444`
- Crosshair, price scale, time scale all visible
- `autoSize: true`

### `setTf(interval)` updated logic
```
'D'  → hide lw_chart_wrap, show tv_chart_wrap, rebuild TradingView widget
'60' → hide tv_chart_wrap, show lw_chart_wrap, fetchAndRender('1h')
'W'  → hide tv_chart_wrap, show lw_chart_wrap, fetchAndRender('1w')
```

### `fetchAndRender(tf)`
1. Show `#lw_loading`, clear `#lw_chart`
2. `GET /api/ticker/<TICKER>/ohlcv?tf=<tf>`
3. On success: create `LightweightCharts.createChart()`, add candlestick + volume series, set data, hide loading
4. On error: show error message in `#lw_chart`
5. Chart instance destroyed and recreated on each call (no stale state)

---

## Error Handling
- yfinance timeout (>10s): return 502, frontend shows "Data unavailable"
- Ticker with no hourly data (delisted): 404, frontend shows "No intraday data for \<ticker\>"
- Network error from frontend: show inline error, 1D button stays functional

---

## Out of Scope
- Pre-fetching hourly data in the scheduler
- Indicators/overlays on the lightweight-charts panel (user can add via TradingView on 1D)
- Saving chart state between page loads
