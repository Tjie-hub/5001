"""
idx_scraper.py — Fetch IDX data via Stockbit tradebook

Data coverage:
  OHLCV daily       → derived from Stockbit 1m tradebook bars (O/H/L/C/V)
  Intraday 1m bars  → Stockbit tradebook (actual buy/sell lots per minute)
  Avg Vol 20D       → ohlcv DB table (populated from tradebook saves)
"""
import os
import time
import logging
import sqlite3
import requests
from datetime import date as dt_date
from data.fetcher import load_all_tickers

logger = logging.getLogger(__name__)

DELAY = 0.3   # seconds between requests

STOCKBIT_BASE = "https://exodus.stockbit.com"
_SB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}

_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'walkforward.db')


# ── Core tradebook fetch ──────────────────────────────────────────────────────

def _fetch_tradebook_raw(ticker: str, token: str) -> dict | None:
    """Fetch raw 1m tradebook data from Stockbit. Returns data dict or None."""
    try:
        r = requests.get(
            f"{STOCKBIT_BASE}/order-trade/trade-book/chart",
            params={"symbol": ticker, "time_interval": "1m"},
            headers={**_SB_HEADERS, "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code != 200:
            logger.info(f"[scraper] {ticker}: HTTP {r.status_code}")
            return None
        return r.json().get("data") or None
    except Exception as e:
        logger.error(f"[scraper] tradebook error {ticker}: {e}")
        return None


def _ticks_from_raw(ticker: str, data: dict, trade_date: str) -> list:
    """
    Parse tradebook response into tick records.
    tick_type: 'up' if buy_lot > sell_lot, 'down' if sell_lot > buy_lot.
    volume: (buy_lot + sell_lot) * 100 shares.
    """
    buys   = data.get("buy", [])
    sells  = data.get("sell", [])
    prices = data.get("prices", [])
    if not buys or not prices:
        return []

    ticks = []
    n = min(len(buys), len(sells), len(prices))
    for i in range(n):
        bl = int(buys[i]["lot"]["raw"])     if buys[i].get("lot")    and buys[i]["lot"].get("raw")    else 0
        sl = int(sells[i]["lot"]["raw"])    if sells[i].get("lot")   and sells[i]["lot"].get("raw")   else 0
        px = int(prices[i]["value"]["raw"]) if prices[i].get("value") and prices[i]["value"].get("raw") else 0
        t_str = buys[i].get("time", "")
        if not px or not t_str:
            continue
        total_lot = bl + sl
        if total_lot == 0:
            continue
        if bl > sl:
            tick_type = 'up'
        elif sl > bl:
            tick_type = 'down'
        else:
            tick_type = 'unchanged'
        ticks.append({
            'date':      trade_date,
            'ticker':    ticker,
            'time':      t_str + ':00',   # "HH:MM" → "HH:MM:00"
            'price':     px,
            'volume':    total_lot,       # lot.raw is already in shares
            'tick_type': tick_type,
        })
    return ticks


def _ohlcv_from_ticks(ticks: list) -> dict:
    """Derive OHLCV from a list of tick records."""
    if not ticks:
        return _empty_ohlcv()
    prices  = [t['price']  for t in ticks if t.get('price')]
    volumes = [t['volume'] for t in ticks if t.get('volume')]
    if not prices:
        return _empty_ohlcv()
    return {
        'open':   prices[0],
        'high':   max(prices),
        'low':    min(prices),
        'close':  prices[-1],
        'volume': sum(volumes),
    }


def _empty_ohlcv() -> dict:
    return {'close': None, 'open': None, 'high': None, 'low': None, 'volume': 0}


# ── Combined fetch (one API call per ticker) ──────────────────────────────────

def fetch_all_stockbit(
    tickers: list,
    token: str,
    trade_date: str = None,
    delay: float = DELAY,
    progress_cb=None,
) -> tuple[dict, dict]:
    """
    Fetch tradebook for all tickers in one pass.
    Returns: (ohlcv_all, ticks_all)
      ohlcv_all: {ticker: {open, high, low, close, volume}}
      ticks_all: {ticker: [tick, ...]}
    """
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    ohlcv_all = {}
    ticks_all = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        logger.info(f"[scraper] {ticker} ({i+1}/{total})")
        data = _fetch_tradebook_raw(ticker, token)
        if data:
            ticks = _ticks_from_raw(ticker, data, trade_date)
        else:
            ticks = []
        ticks_all[ticker] = ticks
        ohlcv_all[ticker] = _ohlcv_from_ticks(ticks)
        if progress_cb:
            progress_cb(ticker, i + 1, total)
        if i < total - 1:
            time.sleep(delay)

    filled = sum(1 for v in ohlcv_all.values() if v.get('close'))
    logger.info(f"[scraper] Done: {filled}/{total} tickers with data")
    return ohlcv_all, ticks_all


# ── OHLCV DB persistence ──────────────────────────────────────────────────────

def save_ohlcv_to_db(ohlcv_all: dict, trade_date: str) -> int:
    """
    Save derived OHLCV to the ohlcv table so historical data stays current.
    Returns number of rows saved.
    """
    rows = [
        (ticker, trade_date, v['open'], v['high'], v['low'], v['close'], v['volume'])
        for ticker, v in ohlcv_all.items()
        if v.get('close')
    ]
    if not rows:
        return 0
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.executemany(
            """INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        conn.close()
        logger.info(f"[scraper] Saved {len(rows)} OHLCV rows to DB ({trade_date})")
        return len(rows)
    except Exception as e:
        logger.error(f"[scraper] save_ohlcv_to_db error: {e}")
        return 0


# ── Avg Vol 20D from DB ───────────────────────────────────────────────────────

def get_avg_vol_20d_from_db(ticker: str, before_date: str = None) -> int | None:
    """Compute 20-day avg volume from ohlcv table."""
    if before_date is None:
        before_date = dt_date.today().isoformat()
    try:
        conn = sqlite3.connect(_DB_PATH)
        row = conn.execute(
            """SELECT AVG(volume) FROM (
                 SELECT volume FROM ohlcv
                 WHERE ticker=? AND date < ? AND volume > 0
                 ORDER BY date DESC LIMIT 20
               )""",
            (ticker, before_date),
        ).fetchone()
        conn.close()
        return int(row[0]) if row and row[0] else None
    except Exception as e:
        logger.error(f"[scraper] avg_vol DB error {ticker}: {e}")
        return None


# ── Legacy: keep signature compatibility for any external callers ─────────────

def fetch_lq45_ohlcv(tickers: list = None, token: str = None) -> dict:
    """
    Compat wrapper. If token provided, derives OHLCV from Stockbit tradebook.
    Without token returns empty dict — callers should use fetch_all_stockbit().
    """
    if not token or not tickers:
        return {t: _empty_ohlcv() for t in (tickers or [])}
    ohlcv_all, _ = fetch_all_stockbit(tickers, token)
    return ohlcv_all


def fetch_avg_vol_20d(ticker: str, trade_date: str = None) -> int | None:
    """Query ohlcv DB table for 20D avg volume."""
    return get_avg_vol_20d_from_db(ticker, trade_date)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(val) -> int | None:
    try:
        if val is None:
            return None
        return int(float(val))
    except (TypeError, ValueError):
        return None
