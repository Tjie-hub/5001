"""Local multi-pane charting backend.

Flask on :5050 with a single JSON endpoint (/api/ohlcv) that fetches OHLCV via
yfinance, computes indicators server-side, and caches each response ~60s.
"""

from __future__ import annotations

import threading
import time

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request, send_from_directory

import indicators as ind

app = Flask(__name__, static_folder="static", static_url_path="")

# --- timeframe -> (yfinance interval, fetch period) -------------------------
# Periods respect yfinance's documented limits per interval.
TF_MAP = {
    "1m":  ("1m",  "7d"),
    "5m":  ("5m",  "60d"),
    "15m": ("15m", "60d"),
    "30m": ("30m", "60d"),
    "1h":  ("60m", "729d"),
    "1d":  ("1d",  "2y"),
    "1wk": ("1wk", "10y"),
    "1mo": ("1mo", "max"),
}

CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def resolve_symbol(symbol: str, market: str) -> str:
    s = symbol.strip().upper()
    if market == "IDX" and not s.endswith(".JK"):
        s = f"{s}.JK"
    # US tickers (AAPL) and crypto (BTC-USD) are used as-is.
    return s


def _epoch_seconds(index: pd.DatetimeIndex) -> list[int]:
    out = []
    for t in index:
        ts = pd.Timestamp(t)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")  # daily bars come back tz-naive
        out.append(int(ts.timestamp()))
    return out


def build_payload(df: pd.DataFrame, symbol: str, timeframe: str) -> dict:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(how="all")
    # lightweight-charts needs strictly ascending, unique timestamps.
    df = df[~df.index.duplicated(keep="last")].sort_index()

    times = _epoch_seconds(df.index)
    o = df["Open"].astype(float).tolist()
    h = df["High"].astype(float).tolist()
    l = df["Low"].astype(float).tolist()
    c = df["Close"].astype(float).tolist()
    vol = df["Volume"].astype(float).tolist()

    candles, volume = [], []
    for i, t in enumerate(times):
        candles.append({"time": t, "open": o[i], "high": h[i], "low": l[i], "close": c[i]})
        volume.append({
            "time": t,
            "value": vol[i],
            "color": "rgba(38,166,154,0.5)" if c[i] >= o[i] else "rgba(239,83,80,0.5)",
        })

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(candles),
        "candles": candles,
        "volume": volume,
        "indicators": ind.compute_all(df, times, timeframe),
    }


@app.route("/api/ohlcv")
def api_ohlcv():
    symbol = request.args.get("symbol", "").strip()
    market = request.args.get("market", "US").strip().upper()
    timeframe = request.args.get("timeframe", "1d").strip()

    if not symbol:
        return jsonify({"error": "Missing 'symbol'."}), 400
    if timeframe not in TF_MAP:
        return jsonify({"error": f"Unsupported timeframe '{timeframe}'."}), 400

    yf_symbol = resolve_symbol(symbol, market)
    interval, period = TF_MAP[timeframe]
    key = f"{yf_symbol}|{interval}|{period}"

    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL:
            return jsonify(hit[1])

    try:
        df = yf.download(
            yf_symbol, period=period, interval=interval,
            auto_adjust=False, progress=False, threads=False,
        )
    except Exception as exc:  # network / yfinance failure
        return jsonify({"error": f"Fetch failed for {yf_symbol}: {exc}"}), 502

    if df is None or df.empty:
        return jsonify({
            "error": (
                f"No data for '{yf_symbol}' at {timeframe}. The symbol may be "
                f"invalid, or this timeframe/range is unavailable "
                f"(yfinance limits: 1m≈7d, 5m/15m/30m≈60d)."
            )
        }), 404

    payload = build_payload(df, yf_symbol, timeframe)
    with _lock:
        _cache[key] = (now, payload)
    return jsonify(payload)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "cached_keys": len(_cache)})


if __name__ == "__main__":
    print("Chart viewer on http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
