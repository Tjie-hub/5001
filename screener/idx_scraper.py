"""
idx_scraper.py — Fetch IDX data via yfinance (primary source)
IDX endpoints (403 blocked) replaced with yfinance .JK tickers.

Data coverage:
  OHLCV daily       → yfinance batch download (fast, 1 request)
  Intraday 1m bars  → yfinance per ticker (simulate ticks for VWAP/Delta)
  Avg Vol 20D       → yfinance 30d history
  Broker Summary    → NOT available (no free public source)
"""
import time
import logging
import pandas as pd
import yfinance as yf
from datetime import date as dt_date

logger = logging.getLogger(__name__)

DELAY = 0.3   # seconds between per-ticker intraday requests

# LQ45 constituents (update manually after BEI rebalancing, Feb & Aug)
LQ45 = [
    'AALI','ACES','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO',
    'ASII','BBCA','BBNI','BBRI','BBTN','BMRI','BRIS','BRPT',
    'BUKA','CPIN','EMTK','EXCL','GGRM','GOTO','HRUM','ICBP',
    'INCO','INDF','INDY','INKP','INTP','ISAT','ITMG','JPFA',
    'KLBF','MAPI','MDKA','MEDC','MIKA','MNCN','PGAS','PTBA',
    'SMGR','TBIG','TLKM','TOWR','UNTR','UNVR',
]


def _jk(ticker: str) -> str:
    return ticker + '.JK'


# ── 1. OHLCV Batch (daily) ────────────────────────────────────────────────────

def fetch_lq45_ohlcv(tickers: list = None) -> dict:
    """
    Fetch today's OHLCV for all LQ45 tickers in one batch.
    Returns: {ticker: {close, open, high, low, volume}}
    """
    if tickers is None:
        tickers = LQ45

    logger.info(f"[scraper] Fetching OHLCV batch for {len(tickers)} tickers...")
    try:
        jk_tickers = [_jk(t) for t in tickers]
        df = yf.download(
            tickers=' '.join(jk_tickers),
            period='2d',
            interval='1d',
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        result = {}
        for ticker in tickers:
            jk = _jk(ticker)
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    # Multiple tickers — columns are (field, ticker)
                    closes = df['Close'][jk].dropna()
                    opens  = df['Open'][jk].dropna()
                    highs  = df['High'][jk].dropna()
                    lows   = df['Low'][jk].dropna()
                    vols   = df['Volume'][jk].dropna()
                else:
                    # Single ticker fallback
                    closes = df['Close'].dropna()
                    opens  = df['Open'].dropna()
                    highs  = df['High'].dropna()
                    lows   = df['Low'].dropna()
                    vols   = df['Volume'].dropna()

                if closes.empty:
                    result[ticker] = _empty_ohlcv()
                    continue

                result[ticker] = {
                    'close':  _safe_int(closes.iloc[-1]),
                    'open':   _safe_int(opens.iloc[-1])  if not opens.empty  else None,
                    'high':   _safe_int(highs.iloc[-1])  if not highs.empty  else None,
                    'low':    _safe_int(lows.iloc[-1])   if not lows.empty   else None,
                    'volume': _safe_int(vols.iloc[-1])   if not vols.empty   else 0,
                }
            except Exception as e:
                logger.warning(f"[scraper] OHLCV parse {ticker}: {e}")
                result[ticker] = _empty_ohlcv()

        filled = sum(1 for v in result.values() if v.get('close'))
        logger.info(f"[scraper] OHLCV: {filled}/{len(tickers)} tickers with data")
        return result

    except Exception as e:
        logger.error(f"[scraper] OHLCV batch error: {e}")
        return {t: _empty_ohlcv() for t in tickers}


def _empty_ohlcv() -> dict:
    return {'close': None, 'open': None, 'high': None, 'low': None, 'volume': 0}


# ── 2. Intraday 1m → Simulated Ticks ─────────────────────────────────────────

def fetch_running_trade(ticker: str, trade_date: str = None) -> list:
    """
    Fetch 1-minute intraday bars and convert to tick-like records.
    Each 1m bar → one tick using close-to-close tick test.
    Returns list of {date, ticker, time, price, volume, tick_type}
    """
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    try:
        hist = yf.Ticker(_jk(ticker)).history(
            interval='1m',
            period='1d',
            auto_adjust=True,
        )

        if hist.empty:
            logger.info(f"[scraper] No intraday data for {ticker}")
            return []

        ticks      = []
        prev_close = None

        for ts, row in hist.iterrows():
            price  = _safe_int(row.get('Close'))
            volume = _safe_int(row.get('Volume'))

            if price is None or volume is None or volume == 0:
                continue

            # Convert timestamp to WIB string
            try:
                t_local = ts.tz_convert('Asia/Jakarta')
                t_str   = t_local.strftime('%H:%M:%S')
            except Exception:
                t_str = str(ts)

            # Tick test
            if prev_close is None:
                tick_type = 'unchanged'
            elif price > prev_close:
                tick_type = 'up'
            elif price < prev_close:
                tick_type = 'down'
            else:
                tick_type = 'unchanged'

            ticks.append({
                'date':      trade_date,
                'ticker':    ticker,
                'time':      t_str,
                'price':     price,
                'volume':    volume,
                'tick_type': tick_type,
            })
            prev_close = price

        logger.info(f"[scraper] {ticker}: {len(ticks)} 1m bars")
        return ticks

    except Exception as e:
        logger.error(f"[scraper] Intraday error {ticker}: {e}")
        return []


def fetch_all_running_trades(
    tickers: list = None,
    trade_date: str = None,
    delay: float = DELAY,
    progress_cb=None,
) -> dict:
    """Sequential fetch intraday 1m bars for all tickers."""
    if tickers is None:
        tickers = LQ45
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    result = {}
    total  = len(tickers)

    for i, ticker in enumerate(tickers):
        logger.info(f"[scraper] Intraday {ticker} ({i+1}/{total})")
        ticks = fetch_running_trade(ticker, trade_date)
        result[ticker] = ticks
        if progress_cb:
            progress_cb(ticker, i + 1, total)
        if i < total - 1:
            time.sleep(delay)

    return result


# ── 3. Broker Summary (not available) ────────────────────────────────────────

def fetch_broker_summary(ticker: str, trade_date: str = None) -> list:
    """Broker summary not available via yfinance. Returns empty list."""
    return []


def fetch_all_broker_summaries(
    tickers: list = None,
    trade_date: str = None,
    delay: float = 0,
    progress_cb=None,
) -> dict:
    """Returns empty dict — broker data not available."""
    if tickers is None:
        tickers = LQ45
    return {t: [] for t in tickers}


# ── 4. Avg Volume 20D ─────────────────────────────────────────────────────────

def fetch_avg_vol_20d(ticker: str) -> int | None:
    """Fetch 30-day daily history and compute 20D avg volume."""
    try:
        hist = yf.Ticker(_jk(ticker)).history(period='30d', auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None
        return int(hist['Volume'].tail(20).mean())
    except Exception as e:
        logger.error(f"[scraper] avg_vol error {ticker}: {e}")
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(val) -> int | None:
    try:
        if val is None:
            return None
        if isinstance(val, float) and pd.isna(val):
            return None
        return int(float(val))
    except (TypeError, ValueError):
        return None
