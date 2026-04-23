"""
calculator.py — Compute VWAP, Delta Volume, Vol Ratio, Signal
"""
from __future__ import annotations
import logging
from datetime import date as dt_date

logger = logging.getLogger(__name__)


# ── VWAP ─────────────────────────────────────────────────────────────────────

def calc_vwap(ticks: list[dict]) -> float | None:
    """
    Session VWAP = Σ(price × volume) / Σ(volume)
    ticks: list of {price, volume, ...}
    """
    total_pv = 0.0
    total_v  = 0
    for t in ticks:
        p = t.get('price')
        v = t.get('volume')
        if p and v:
            total_pv += p * v
            total_v  += v
    if total_v == 0:
        return None
    return round(total_pv / total_v, 2)


def calc_vwap_1h(ticks: list[dict]) -> list[dict]:
    """
    Aggregate ticks into 1-hour OHLCV + VWAP bars.
    IDX session: 09:00-11:30, 13:30-15:00 (skip lunch break)
    Returns list of {hour, open, high, low, close, volume, vwap}
    """
    buckets: dict[str, dict] = {}

    for t in ticks:
        raw_time = str(t.get('time', ''))
        hour_key = _hour_bucket(raw_time)
        if hour_key is None:
            continue

        p = t.get('price')
        v = t.get('volume')
        if not p or not v:
            continue

        if hour_key not in buckets:
            buckets[hour_key] = {
                'hour':   hour_key,
                'open':   p,
                'high':   p,
                'low':    p,
                'close':  p,
                'volume': 0,
                '_pv':    0.0,
            }

        b = buckets[hour_key]
        b['high']   = max(b['high'], p)
        b['low']    = min(b['low'],  p)
        b['close']  = p
        b['volume'] += v
        b['_pv']    += p * v

    result = []
    for key in sorted(buckets):
        b = buckets[key]
        vwap = round(b['_pv'] / b['volume'], 2) if b['volume'] else None
        result.append({
            'hour':   b['hour'],
            'open':   b['open'],
            'high':   b['high'],
            'low':    b['low'],
            'close':  b['close'],
            'volume': b['volume'],
            'vwap':   vwap,
        })

    return result


def _hour_bucket(time_str: str) -> str | None:
    """
    '09:32:15' → '09:00'
    Skips 11:30–13:29 (lunch break).
    """
    try:
        parts = time_str.split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        # Lunch break filter
        if h == 11 and m >= 30:
            return None
        if h == 12:
            return None
        if h == 13 and m < 30:
            return None
        return f"{h:02d}:00"
    except (IndexError, ValueError):
        return None


# ── Delta Volume ─────────────────────────────────────────────────────────────

def calc_delta(ticks: list[dict]) -> dict:
    """
    Tick test:
    - price UP   → aggressive buyer  → +volume
    - price DOWN → aggressive seller → -volume
    - unchanged  → ignored

    Returns {delta, cum_delta, buy_vol, sell_vol, neutral_vol}
    """
    buy_vol     = 0
    sell_vol    = 0
    neutral_vol = 0
    cum_delta   = 0

    for t in ticks:
        v         = t.get('volume', 0) or 0
        tick_type = t.get('tick_type', 'unchanged')

        if tick_type == 'up':
            buy_vol   += v
            cum_delta += v
        elif tick_type == 'down':
            sell_vol  += v
            cum_delta -= v
        else:
            neutral_vol += v

    delta = buy_vol - sell_vol
    return {
        'delta':       delta,
        'cum_delta':   cum_delta,
        'buy_vol':     buy_vol,
        'sell_vol':    sell_vol,
        'neutral_vol': neutral_vol,
    }


# ── Volume Ratio ──────────────────────────────────────────────────────────────

def calc_vol_ratio(today_vol: int, avg_vol_20d: int) -> float | None:
    if not avg_vol_20d or avg_vol_20d == 0:
        return None
    return round(today_vol / avg_vol_20d, 2)


def get_avg_vol_20d_yfinance(ticker: str, before_date: str = None) -> int | None:
    """
    Fetch 30-day daily history from Yahoo Finance and compute 20D avg volume.
    ticker: IDX ticker without .JK (will be appended)
    before_date: 'YYYY-MM-DD', defaults to today
    """
    try:
        import yfinance as yf
        yf_ticker = ticker + '.JK'
        hist = yf.Ticker(yf_ticker).history(period='30d')
        if hist.empty or len(hist) < 5:
            logger.warning(f"[calc] yfinance: insufficient data for {ticker}")
            return None
        avg = int(hist['Volume'].tail(20).mean())
        return avg
    except Exception as e:
        logger.error(f"[calc] yfinance error for {ticker}: {e}")
        return None


# ── Signal ────────────────────────────────────────────────────────────────────

def calc_signal(
    vol_ratio: float | None,
    delta: int,
    price: int | None,
    vwap: float | None,
    vol_ratio_threshold: float = 1.5,
) -> str:
    """
    Signal logic:
    🟢 bullish  = vol_ratio > threshold AND delta > 0 AND price > vwap
    🔴 bearish  = vol_ratio > threshold AND delta < 0 AND price < vwap
    🟡 watch    = vol_ratio > threshold but mixed delta/price
    ⚪ neutral  = vol_ratio <= threshold (low activity)
    """
    if vol_ratio is None or vol_ratio < vol_ratio_threshold:
        return 'neutral'

    price_above_vwap = (price and vwap and price > vwap)
    price_below_vwap = (price and vwap and price < vwap)

    if delta > 0 and price_above_vwap:
        return 'bullish'
    if delta < 0 and price_below_vwap:
        return 'bearish'
    return 'watch'


# ── Consecutive Up Days ───────────────────────────────────────────────────────

def calc_consec_up(ticker: str, today_close: int | None) -> int:
    """
    Count consecutive days where close > previous close.
    Uses yfinance 60-day history so it works from day 1
    without needing accumulated SQLite data.
    Returns 0 if today is down, negative if consecutive down days.
    Example: +3 = naik 3 hari berturut, -2 = turun 2 hari berturut
    """
    if today_close is None:
        return 0
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker + '.JK').history(period='60d')
        if hist.empty or len(hist) < 2:
            return 0

        closes = list(hist['Close'])

        # Append today's close if different from last (intraday update)
        if abs(closes[-1] - today_close) > 1:
            closes.append(today_close)

        # Count from most recent day backwards
        count = 0
        direction = None  # 'up' or 'down'

        for i in range(len(closes) - 1, 0, -1):
            diff = closes[i] - closes[i - 1]
            if diff == 0:
                break
            day_dir = 'up' if diff > 0 else 'down'
            if direction is None:
                direction = day_dir
            if day_dir != direction:
                break
            count += 1

        return count if direction == 'up' else -count

    except Exception as e:
        logger.error(f"[calc] consec_up error {ticker}: {e}")
        return 0

def process_ticker(
    ticker: str,
    ticks: list[dict],
    ohlcv: dict,
    avg_vol_20d: int | None,
    trade_date: str = None,
) -> dict:
    """
    Run full calculation pipeline for one ticker.
    Returns a dict ready to be passed to db.upsert_daily_screen()
    """
    if trade_date is None:
        trade_date = dt_date.today().isoformat()

    close    = ohlcv.get('close')
    today_vol = ohlcv.get('volume', 0)

    vwap      = calc_vwap(ticks)
    delta_d   = calc_delta(ticks)
    vol_ratio = calc_vol_ratio(today_vol, avg_vol_20d) if avg_vol_20d else None
    signal    = calc_signal(vol_ratio, delta_d['delta'], close, vwap)
    bars_1h   = calc_vwap_1h(ticks)
    consec_up = calc_consec_up(ticker, close)

    return {
        # DB fields
        'date':        trade_date,
        'ticker':      ticker,
        'close':       close,
        'volume':      today_vol,
        'avg_vol_20d': avg_vol_20d,
        'vol_ratio':   vol_ratio,
        'vwap':        vwap,
        'delta':       delta_d['delta'],
        'cum_delta':   delta_d['cum_delta'],
        'signal':      signal,
        'consec_up':   consec_up,
        # Extra (returned to API but not stored in daily_screen)
        'buy_vol':     delta_d['buy_vol'],
        'sell_vol':    delta_d['sell_vol'],
        'neutral_vol': delta_d['neutral_vol'],
        'bars_1h':     bars_1h,
        'tick_count':  len(ticks),
    }
# ── Cumulative Delta Series & Divergence ──────────────────────────────────────

def calc_cum_delta_series(ticks: list[dict]) -> list[list]:
    """
    Hitung cumulative delta tick-by-tick untuk chart.
    Returns list of [time_str, cum_delta_value]
    """
    cum = 0
    series = []
    for t in sorted(ticks, key=lambda x: x.get('time', '')):
        v         = t.get('volume', 0) or 0
        tick_type = t.get('tick_type', 'unchanged')
        if tick_type == 'up':
            cum += v
        elif tick_type == 'down':
            cum -= v
        series.append([t.get('time', ''), cum])
    return series


def calc_divergence(ticks: list[dict]) -> str:
    """
    Bandingkan arah harga vs arah cumulative delta.
    - Harga naik + cum_delta turun → 'bearish' (seller absorb di atas)
    - Harga turun + cum_delta naik → 'bullish' (buyer absorb di bawah)
    - Searah atau tidak cukup data  → 'none'
    """
    if len(ticks) < 2:
        return 'none'

    sorted_ticks = sorted(ticks, key=lambda x: x.get('time', ''))

    first_price = sorted_ticks[0].get('price', 0) or 0
    last_price  = sorted_ticks[-1].get('price', 0) or 0

    # Hitung cum_delta awal dan akhir
    cum = 0
    first_cd = 0
    for i, t in enumerate(sorted_ticks):
        v = t.get('volume', 0) or 0
        if t.get('tick_type') == 'up':
            cum += v
        elif t.get('tick_type') == 'down':
            cum -= v
        if i == 0:
            first_cd = cum
    last_cd = cum

    price_up  = last_price > first_price
    price_dn  = last_price < first_price
    delta_up  = last_cd > first_cd
    delta_dn  = last_cd < first_cd

    if price_up and delta_dn:
        return 'bearish'
    if price_dn and delta_up:
        return 'bullish'
    return 'none'


def calc_hvn(ticks, bucket_size=10):
    """
    High Volume Node (HVN): price level dengan volume terbesar hari ini.
    bucket_size = pembulatan harga (default: 10 rupiah per bucket).
    Return: list of dict, sorted by volume desc.
    Contoh: [{'price': 1930, 'volume': 5200000}, ...]
    """
    if not ticks:
        return []

    volume_by_price = {}
    for t in ticks:
        price = t.get('price', 0) or 0
        volume = t.get('volume', 0) or 0
        if price <= 0:
            continue
        # Bulatkan ke bucket terdekat (misal: 1923 → 1920, 1937 → 1940)
        bucket = round(price / bucket_size) * bucket_size
        volume_by_price[bucket] = volume_by_price.get(bucket, 0) + volume

    # Sort by volume terbesar, ambil top 5
    sorted_hvn = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
    return [{'price': p, 'volume': v} for p, v in sorted_hvn[:5]]


def calc_absorption(ticks):
    """
    Absorption Detection:
    Volume spike besar tapi harga tidak bergerak jauh = ada penyerapan.
    Return: dict {'score': float, 'flag': bool, 'reason': str}
    """
    if not ticks or len(ticks) < 5:
        return {'score': 0.0, 'flag': False, 'reason': 'not enough data'}

    prices  = [t.get('price', 0) or 0 for t in ticks if t.get('price')]
    volumes = [t.get('volume', 0) or 0 for t in ticks]

    if not prices:
        return {'score': 0.0, 'flag': False, 'reason': 'no price data'}

    total_vol  = sum(volumes)
    avg_vol    = total_vol / len(volumes) if volumes else 0
    price_high = max(prices)
    price_low  = min(prices)
    price_mid  = (price_high + price_low) / 2 if price_mid_safe(price_high, price_low) else prices[0]

    # Price range sebagai persentase dari harga tengah
    price_range_pct = ((price_high - price_low) / price_mid * 100) if price_mid > 0 else 0

    # Cari volume spike: tick dengan volume > 2x rata-rata
    spike_ticks = [t for t in ticks if (t.get('volume') or 0) > avg_vol * 2]
    spike_vol   = sum(t.get('volume', 0) or 0 for t in spike_ticks)

    # Absorption score: semakin tinggi volume spike, semakin kecil range = score makin besar
    if price_range_pct > 0:
        score = round((spike_vol / total_vol * 100) / price_range_pct, 2) if total_vol > 0 else 0
    else:
        score = 0.0

    # Flag jika: ada spike volume DAN range harga sempit (< 0.5%)
    flag   = len(spike_ticks) > 0 and price_range_pct < 0.5
    reason = f"spike_vol={spike_vol:,} range={price_range_pct:.2f}%" if flag else "no absorption"

    return {'score': score, 'flag': flag, 'reason': reason}


def price_mid_safe(high, low):
    return high > 0 and low > 0
