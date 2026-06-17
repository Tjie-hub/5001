# ATAS-Style Pine Indicators — Design

**Date:** 2026-06-17
**Status:** Approved
**Target:** TradingView Desktop (Pine Script v6), driven via the `tradingview` MCP

## Goal

Two self-contained Pine Script v6 indicators that reproduce an ATAS-style view on
any TradingView symbol, using **TradingView's own price feed** (estimated order
flow), not the project database.

> **Honesty caveat (baked into each script header):** delta and footprint are
> *estimated* from TradingView price/volume via lower-timeframe classification.
> They are NOT the real Stockbit broker buy/sell footprint. For the genuine
> per-broker footprint, the `chart.py` blueprint + lightweight-charts viewer
> remains the source of truth (`stockbit_flow_bars`).

## Architecture — Option A: two indicators

One Pine `indicator()` cannot cleanly own both the price overlay and a separate
pane, so the work splits along that natural seam:

### Indicator 1 — `ATAS VP + Footprint` (overlay = true)

Renders on the price chart.

- **Volume Profile**
  - Lookback: configurable, default **100 bars**; toggle for "visible range".
  - Rows: configurable, default **24**, spanning range high → low.
  - Histogram drawn with `box.new` extending from the right edge leftward.
  - **POC**: the max-volume row, drawn as a distinct line/box.
  - **VAH / VAL**: bound the 70% value area (configurable %), drawn as lines.
- **Delta-colored profile (ATAS touch)**
  - Optional toggle: tint each row by net delta in that price bucket
    (green = net buy, red = net sell) instead of a flat volume color.
- **Footprint clusters (bounded)**
  - Toggle, **default OFF**.
  - When on, renders bid/ask-style numbers via `label.new` on the **last 10
    bars only** (hard cap) to stay within Pine limits.
  - In-script comment documents the Pine limitation explicitly.

### Indicator 2 — `ATAS Delta / CVD` (separate pane)

Renders in its own pane below price.

- **Delta estimation**
  - Primary: `request.security_lower_tf()` pulls intrabar candles (default 1-min
    within each chart bar). Each intrabar's volume is signed by close-vs-open
    (up = buy, down = sell); summed per bar = delta.
  - Fallback: if lower-TF data is unavailable, sign whole-bar volume by
    close-vs-previous-close.
- **Delta histogram**: per-bar, green/red.
  - Optional divergence dots: price up while delta down (and vice versa).
- **CVD line**: cumulative sum of per-bar delta. Optional candle rendering.

## Inputs (both scripts)

Grouped `input.*` controls with sensible defaults so the user can tune without
editing source: lookback length, row count, value-area %, lower-TF resolution,
delta-coloring toggle, footprint toggle, divergence toggle, colors.

## Build & validation flow

1. `pine_new` → create each script.
2. `pine_set_source` → inject source.
3. `pine_smart_compile` → compile.
4. `pine_get_errors` → read errors; iterate until clean.
5. Add both to the live BRPT chart; `capture_screenshot` to confirm visually.

## Out of scope (YAGNI)

- Reading the project DB from Pine (impossible — Pine has no external I/O).
- True tick/order-level bid×ask footprint (not available to Pine).
- Multi-symbol batch rendering.
- Alerts (can be added later if wanted).

## Success criteria

- Both scripts compile cleanly in TradingView (no `pine_get_errors`).
- Indicator 1 shows a readable VP with POC/VAH/VAL on BRPT daily.
- Indicator 2 shows a delta histogram + CVD line that visibly tracks price.
- Footprint toggle works on last 10 bars without breaking the chart.
