# Multi-Pane Chart Viewer with Order-Flow Delta — Design

**Date:** 2026-06-16
**Status:** Approved design, ready for implementation plan
**Scope:** Workspace-embedded multi-pane charting panel built on `lightweight-charts`, with custom indicators (Volume Profile, Fair Value Gaps, Support/Resistance, VWAP, VWMA, candlestick patterns), an ATAS-style **Delta Volume / CVD** module sourced from Stockbit 1-minute order-flow, and one-click symbol sync to the TradingView Desktop app via CDP.

---

## 1. Motivation

Inspired by two references:
- A YouTube build (Nitin / AI University) of a free multi-pane chart app on `lightweight-charts` replacing the TradingView paid tier (multi-pane, custom Volume Profile + FVG).
- An ATAS order-flow walkthrough (OasisTrading) demonstrating Cumulative Volume Delta (CVD), footprint/delta-by-price profiles, and cluster delta stats.

The existing IDX suite already has rich backend data (daily/weekly/monthly OHLCV, Stockbit broker flow, 1-minute delta bars) but no standalone interactive multi-pane chart. This feature delivers that, reusing existing data instead of adding new external feeds.

**Out of scope (explicit per user):** US / India tickers, yfinance expansion to foreign markets. IDX only.

---

## 2. Data Reality (verified 2026-06-16)

| Source | Table / Route | Content | Coverage |
|---|---|---|---|
| Daily OHLCV (IDX) | `ohlcv` table | O/H/L/C/V | 959 tickers, multi-year |
| D/W/M aggregation | `GET /api/ticker/<t>/ohlcv/<freq>` (`D`/`W`/`ME`) | resampled OHLCV | existing route |
| Hourly OHLCV | `GET /api/ticker/<t>/ohlcv?tf=1h` | hourly candles | existing route (yfinance `.JK`, cached 15min) |
| **Intraday delta** | `stockbit_flow_bars` | 1-min `buy_lot, sell_lot, buy_freq, sell_freq, net_value, price, delta` | **28 trading days** (2026-04-20 → present), ~860 tickers, grows daily via cron |
| Broker flow | `broker_flow`, `bandar_detector` | broker net buy/sell | daily |

**Critical constraint:** intraday delta granularity is **1-minute**, not tick-level. History is a **rolling ~28 days** (no data before 2026-04-20). The Stockbit fetcher cron extends it daily.

**Library:** `lightweight-charts@4.2.0` is already loaded in `templates/workspace.html`.
**TradingView CDP:** TradingView Desktop runs with remote debugging on **port 9222** (verified live). Symbol set expression: `window.TradingViewApi._activeChartWidgetWV.value().setSymbol("BBCA", {})` via `Runtime.evaluate`.

---

## 3. Architecture

Four units, each independently testable:

### 3.1 Indicator engine — `engine/chart_indicators.py` (new)

Pure functions over a pandas OHLCV DataFrame. No I/O, no Flask. Unit-tested with fixtures.

| Function | Signature | Output |
|---|---|---|
| `volume_profile(df, bins=24)` | → dict | `{poc, vah, val, rows:[{price, volume}]}` |
| `fair_value_gaps(df)` | → list | `[{type:'bull'/'bear', top, bottom, date}]` (3-candle gap rule) |
| `support_resistance(df, lookback=5, max_levels=6)` | → dict | `{support:[...], resistance:[...]}` from swing pivots |
| `vwap(df, anchor)` | → Series | session VWAP (1h, reset daily) / anchored VWAP (D) |
| `vwma(df, length=20)` | → Series | volume-weighted MA |
| `detect_patterns(df)` | → list | `[{date, pattern, dir}]` — engulfing, hammer, shooting-star, doji |

FVG rule: bullish gap where `low[i] > high[i-2]`; bearish where `high[i] < low[i-2]`. Zone = the gap between those two extremes.

### 3.2 Delta / order-flow engine — `engine/delta_flow.py` (new)

Reads `stockbit_flow_bars`. Pure compute over the fetched rows (DB read isolated to a thin loader). Unit-tested with synthetic bar fixtures.

| Function | Output | ATAS analogue |
|---|---|---|
| `cvd(ticker, date)` | `[{time, cvd}]` cumulative Σ delta over session | CVD line |
| `cvd_ema(cvd_series, length=9)` | EMA overlay | CVD moving average |
| `delta_bars(ticker, date, period='1min')` | `[{time, delta, buy, sell}]` | per-bar delta histogram |
| `delta_by_price(ticker, date, bins)` | `[{price, volume, delta}]` | footprint-lite / delta profile |
| `session_delta_stats(ticker, date)` | `{total_delta, buy_lot, sell_lot, net_value}` | cluster delta stats |
| `stacked_imbalances(ticker, date, z=2.0)` | `[{time, price, delta}]` where \|delta\| spikes ≥ z·σ | stacked imbalance boxes |

**Honest labeling:** the UI must label delta-by-price as "1-min approximation" and disable the delta panel for dates outside the rolling window (with a clear "no order-flow data before 2026-04-20" message).

### 3.3 TradingView CDP bridge — `engine/tv_bridge.py` (new)

Minimal Python CDP client (websocket to `ws://localhost:9222`). One job: drive the Desktop chart.

- `set_symbol(symbol)` → resolves the active page's debugger ws URL from `http://localhost:9222/json`, sends `Runtime.evaluate` with the setSymbol expression.
- `is_available()` → quick health probe (`/json/version`).
- **Fail-open:** every method catches connection errors and returns `{ok:false, reason}` — never raises into a request. If TV Desktop is closed, sync is a no-op with a UI toast, charts still work.

### 3.4 Routes — `routes/chart.py` (new blueprint, `url_prefix=/api/chart`)

| Route | Method | Returns |
|---|---|---|
| `/api/chart/<ticker>/indicators?tf=<1h\|D\|W\|M>&inds=vp,fvg,sr,vwap,vwma,patterns` | GET | one JSON bundle: requested overlays computed server-side (reuses existing OHLCV loaders) |
| `/api/chart/<ticker>/delta?date=<YYYY-MM-DD>&parts=cvd,bars,profile,stats,imbalance` | GET | order-flow bundle from `delta_flow` |
| `/api/chart/tv/sync` | POST `{symbol}` | `{ok, reason?}` via `tv_bridge.set_symbol` |
| `/api/chart/tv/status` | GET | `{available}` from `tv_bridge.is_available` |

Candle OHLCV itself continues to come from the existing `/api/ticker/...` routes — no duplication.

### 3.5 Frontend — Workspace panel

New files: `static/charts.js`, `static/charts.css`. Wired into `templates/workspace.html` (library already present).

- **Flexible grid:** toggle **1 / 2 / 4 / 6** panes (CSS grid; layout state in `localStorage`).
- **Per-pane controls:** symbol input · timeframe (1h / D / W / M) · indicator toggle chips (VP, FVG, S&R, VWAP, VWMA, Patterns) · Delta toggle (opens CVD sub-pane + delta-profile overlay).
- **Each pane** = a `lightweight-charts` instance: candlestick series + overlay primitives (VP histogram on price scale, FVG rectangles, S&R price lines, VWAP/VWMA line series, pattern markers) + optional bottom CVD pane.
- **Signal → chart:** clicking a signal row in the existing Workspace signals list loads that ticker into the focused pane **and** fires `POST /api/chart/tv/sync` so TradingView Desktop follows.
- **Refresh:** manual refresh button + optional interval poll reusing existing cached endpoints (no new websocket).

---

## 4. Data Flow

```
Browser pane
  ├─ GET /api/ticker/<t>/ohlcv/<freq>      → candles      → lightweight-charts series
  ├─ GET /api/chart/<t>/indicators?...     → VP/FVG/SR/...  → overlay primitives
  └─ GET /api/chart/<t>/delta?...          → CVD/profile    → bottom sub-pane + profile

Click signal/ticker
  └─ POST /api/chart/tv/sync {symbol}      → tv_bridge → CDP :9222 → TV Desktop setSymbol
```

Sync is **one-directional** (app → TV Desktop). No reverse sync.

---

## 5. Indicator / Delta Caveats (signed off)

1. **Delta granularity = 1-minute**, not tick. "Footprint" is 1-min delta bucketed by price (~12 price levels/day for liquid names) — coarser than ATAS tick footprint, conceptually equivalent. Labeled in UI.
2. **Delta history = rolling ~28 days** (from 2026-04-20). Delta panel disabled with a message for older dates.
3. **VWAP:** true session VWAP on 1h (resets per session); on Daily it is an anchored/rolling VWAP.
4. **Volume Profile:** 1h gives intraday-accurate profile; Daily gives swing-level profile.
5. **True tick footprint / bid-ask ladder:** NOT built — Stockbit exposes 1-min aggregates only.

---

## 6. Testing

- `tests/test_chart_indicators.py` — each indicator function against known fixtures (VP POC on a crafted distribution, FVG detection on a gap fixture, S&R pivots, VWAP/VWMA numeric checks, pattern detection on canonical candles).
- `tests/test_delta_flow.py` — CVD cumulative correctness, delta_by_price bucketing, session stats, imbalance z-score, and the out-of-window date → empty/labeled path.
- `tests/test_tv_bridge.py` — mock CDP socket: correct `Runtime.evaluate` payload for `set_symbol`; connection-refused → fail-open `{ok:false}` (no raise).
- `tests/test_chart_routes.py` — route smoke: indicators bundle shape, delta bundle shape, `/tv/sync` calls bridge, `/tv/status` reflects availability.

All must pass alongside the existing suite (currently 583 tests).

---

## 7. Scope Guard (YAGNI)

- IDX tickers only — no US/India, no foreign yfinance expansion.
- No new realtime websocket feed — reuse existing cached OHLCV + manual/interval refresh.
- TV sync one-directional, symbol-only (no timeframe/indicator mirroring in v1).
- No tick-level footprint, no DOM/tape clone (data not available).
- Reuse existing OHLCV routes for candles; new routes only for indicators, delta, and TV bridge.

---

## 8. File Manifest

**New:**
- `engine/chart_indicators.py`
- `engine/delta_flow.py`
- `engine/tv_bridge.py`
- `routes/chart.py`
- `static/charts.js`
- `static/charts.css`
- `tests/test_chart_indicators.py`
- `tests/test_delta_flow.py`
- `tests/test_tv_bridge.py`
- `tests/test_chart_routes.py`

**Modified:**
- `templates/workspace.html` — chart panel markup + control bar; include `charts.js` / `charts.css`.
- `app.py` — register `chart_bp` blueprint.
