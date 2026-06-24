# Multi-Pane Chart Viewer

A local, self-contained charting web app. Flask backend (port **5050**) fetches
OHLCV via `yfinance` and computes indicators server-side; a single-page vanilla-JS
frontend renders candlesticks with [TradingView lightweight-charts](https://github.com/tradingview/lightweight-charts).

> Lives in `chart-viewer/` inside the IDX walkforward repo but is fully isolated —
> its own venv and dependencies, nothing shared with the trading suite. Port 5050
> is used because 5000/5001/5002 are taken on this machine.

## Run

```bash
cd chart-viewer
bash start.sh            # creates venv, installs deps, serves on :5050
```

Then open http://localhost:5050.

## Features

- **Pane selector**: 1 / 2 / 4 / 6 / 8 panes in a responsive grid that resizes with the window.
- **Per-pane controls**: symbol (text), market (IDX / US / Crypto), timeframe
  (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo).
- **Markets**: IDX auto-appends `.JK` (e.g. `BBCA` → `BBCA.JK`); US as-is (`AAPL`);
  crypto as-is (`BTC-USD`).
- **Session badges** (top-right): live open/closed for Jakarta (WIB), US (NYSE), and crypto.
- **Indicators** (toggle per pane, computed in pandas/numpy):
  - Overlays: SMA 20/50/200, EMA(20), Bollinger Bands, VWAP (session-anchored intraday).
  - Volume Profile — POC / VAH / VAL drawn as price levels.
  - Fair Value Gaps — bullish/bearish 3-candle imbalances (arrows + recent zone lines).
  - Bottom oscillators (own stacked scales): Volume, RSI(14), MACD(12/26/9).

## API

`GET /api/ohlcv?symbol=BBCA&market=IDX&timeframe=1d`

Returns `{ symbol, timeframe, bars, candles[], volume[], indicators{} }`.
Responses are cached ~60s per (symbol, interval, period) to respect yfinance limits.
Unavailable timeframe/range or invalid symbols return a JSON `error` with HTTP 404/502.

## yfinance range limits (handled automatically)

| Timeframe | Interval | Period fetched |
|-----------|----------|----------------|
| 1m        | 1m       | 7d  |
| 5/15/30m  | "        | 60d |
| 1h        | 60m      | 729d |
| 1d        | 1d       | 2y  |
| 1wk       | 1wk      | 10y |
| 1mo       | 1mo      | max |

## Stack

Backend: Flask + yfinance + pandas + numpy only. Frontend: lightweight-charts from CDN
(`unpkg`, pinned v4.1.3) — no build step, no framework.
