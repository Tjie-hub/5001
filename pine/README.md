# ATAS-style Pine indicators

Self-contained Pine Script v6 indicators that reproduce an ATAS-style view on
any TradingView symbol using TradingView's own price feed (estimated order flow).

> **Honesty:** delta & footprint here are ESTIMATED from OHLCV, NOT the real
> Stockbit broker footprint. For genuine per-broker flow use the `chart.py`
> viewer (`stockbit_flow_bars`). See
> `docs/superpowers/specs/2026-06-17-atas-pine-indicators-design.md`.

## Files
- `atas_vp_footprint.pine` — overlay: volume profile (POC/VAH/VAL), delta-colored
  rows, optional bounded footprint (last N bars, default off).
- `atas_delta_cvd.pine` — separate pane: per-bar estimated delta histogram +
  cumulative delta (CVD) line + price/delta divergence markers.

## Install (one click each in TradingView Desktop)
1. Open the Pine Editor (bottom toolbar).
2. Paste the contents of a `.pine` file.
3. Press **Ctrl+Enter** (or click **Add to chart**).
4. Repeat for the second file.

Note: a **free TradingView plan caps indicators per chart** — remove an existing
study (e.g. the built-in Auto Anchored Volume Profile) if "Add to chart" shows
an upgrade prompt instead of adding.

Both compile clean on Pine v6.
