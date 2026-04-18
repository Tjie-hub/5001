"""
Flow Filter — Confirmation layer for walkforward signals.
==========================================================
Extract from flow_poc.py, callable from scheduler.py.

Usage in scheduler:
    from flow_filter import get_flow_confirmation
    flow = get_flow_confirmation("BRPT")
    # Returns: {"score": +4, "verdict": "BULLISH", "smart_money": "STRONG_BUY", ...}
    # Or None if data unavailable / token expired

Standalone test:
    python3 flow_filter.py BBCA BRPT TLKM
"""

import os
import sys
import time
import requests
from datetime import datetime

STOCKBIT_BASE = "https://exodus.stockbit.com"
HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".stockbit_token")


def _load_token():
    """Load token from .stockbit_token file."""
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    except Exception:
        return None


def _fetch_tradebook(token, ticker):
    """Fetch 1-minute tradebook chart from Stockbit."""
    try:
        r = requests.get(
            f"{STOCKBIT_BASE}/order-trade/trade-book/chart",
            params={"symbol": ticker, "time_interval": "1m"},
            headers={**HEADERS_BASE, "Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        return r.json().get("data")
    except Exception:
        return None


def _parse_bars(data):
    """Parse tradebook response into minute bars."""
    bars = []
    buys = data.get("buy", [])
    sells = data.get("sell", [])
    net_vals = data.get("net_values", [])
    prices = data.get("prices", [])

    n = min(len(buys), len(sells), len(prices))
    for i in range(n):
        bl = int(buys[i]["lot"]["raw"]) if buys[i].get("lot") and buys[i]["lot"].get("raw") else 0
        sl = int(sells[i]["lot"]["raw"]) if sells[i].get("lot") and sells[i]["lot"].get("raw") else 0
        bf = int(buys[i]["frequency"]["raw"]) if buys[i].get("frequency") and buys[i]["frequency"].get("raw") else 0
        sf = int(sells[i]["frequency"]["raw"]) if sells[i].get("frequency") and sells[i]["frequency"].get("raw") else 0
        nv = int(net_vals[i]["value"]["raw"]) if i < len(net_vals) and net_vals[i].get("value") and net_vals[i]["value"].get("raw") else 0
        px = int(prices[i]["value"]["raw"]) if i < len(prices) and prices[i].get("value") and prices[i]["value"].get("raw") else 0
        t = buys[i].get("time", "")

        bars.append({
            "time": t, "buy_lot": bl, "sell_lot": sl,
            "buy_freq": bf, "sell_freq": sf,
            "net_value": nv, "price": px,
            "delta": bl - sl,
        })
    return bars


def _analyze(ticker, bars):
    """Run 5 flow strategies, return dict with score & verdict."""
    if not bars or len(bars) < 30:
        return None

    market_bars = [b for b in bars if "09:" <= b["time"] <= "16:"]
    if len(market_bars) < 20:
        return None

    result = {"ticker": ticker, "bars": len(market_bars)}

    # 1. Volume Imbalance (15-min buckets)
    buckets = {}
    for b in market_bars:
        hh, mm = b["time"].split(":")
        key = f"{hh}:{int(mm)//15*15:02d}"
        if key not in buckets:
            buckets[key] = {"buy": 0, "sell": 0}
        buckets[key]["buy"] += b["buy_lot"]
        buckets[key]["sell"] += b["sell_lot"]

    strong_buy = sum(1 for v in buckets.values() if v["buy"] / max(v["sell"], 1) > 1.5)
    strong_sell = sum(1 for v in buckets.values() if v["buy"] / max(v["sell"], 1) < 0.67)
    imbalance = "BUY" if strong_buy > strong_sell + 2 else \
                "SELL" if strong_sell > strong_buy + 2 else "NEUTRAL"

    # 2. Cumulative Delta + Price Divergence
    cum_delta = 0
    for b in market_bars:
        cum_delta += b["delta"]

    first_price = market_bars[0]["price"]
    last_price = market_bars[-1]["price"]
    price_chg = round((last_price - first_price) / max(first_price, 1) * 100, 2)
    delta_up = cum_delta > 0
    price_up = last_price > first_price

    divergence_type = ""
    if delta_up and not price_up:
        divergence_type = "BULLISH_DIV"
    elif not delta_up and price_up:
        divergence_type = "BEARISH_DIV"

    # 3. Absorption Detection
    absorption = 0
    distribution = 0
    window = 15
    for i in range(window, len(market_bars)):
        win = market_bars[i-window:i]
        wb = sum(b["buy_lot"] for b in win)
        ws = sum(b["sell_lot"] for b in win)
        p0, p1 = win[0]["price"], win[-1]["price"]
        if ws > wb * 1.5 and p1 >= p0:
            absorption += 1
        if wb > ws * 1.5 and p1 <= p0:
            distribution += 1

    # 4. Session Flow (Opening vs Closing)
    opening_net = sum(b["delta"] for b in market_bars if "09:00" <= b["time"] <= "09:30")
    closing_net = sum(b["delta"] for b in market_bars if "14:30" <= b["time"] <= "15:00")

    if opening_net > 0 and closing_net > 0:
        smart_money = "STRONG_BUY"
    elif opening_net < 0 and closing_net < 0:
        smart_money = "STRONG_SELL"
    elif opening_net > 0 and closing_net < 0:
        smart_money = "MORNING_TRAP"
    elif opening_net < 0 and closing_net > 0:
        smart_money = "ACCUMULATION"
    else:
        smart_money = "NEUTRAL"

    # 5. Flow Acceleration (first 30m vs last 30m)
    first_30 = sum(b["delta"] for b in market_bars[:30])
    last_30 = sum(b["delta"] for b in market_bars[-30:])
    accelerating = last_30 > first_30

    # Composite Score (same as flow_poc.py)
    score = 0
    if imbalance == "BUY": score += 2
    elif imbalance == "SELL": score -= 2
    if divergence_type == "BULLISH_DIV": score += 2
    elif divergence_type == "BEARISH_DIV": score -= 2
    if absorption > 3: score += 1
    if distribution > 3: score -= 1
    if smart_money == "STRONG_BUY": score += 2
    elif smart_money == "ACCUMULATION": score += 1
    elif smart_money == "STRONG_SELL": score -= 2
    elif smart_money == "MORNING_TRAP": score -= 1
    if accelerating: score += 1
    else: score -= 1

    verdict = "BULLISH" if score >= 3 else "BEARISH" if score <= -3 else "NEUTRAL"

    return {
        "ticker": ticker,
        "score": score,
        "verdict": verdict,
        "smart_money": smart_money,
        "imbalance": imbalance,
        "divergence": divergence_type,
        "cum_delta": cum_delta,
        "price_chg_pct": price_chg,
        "absorption": absorption,
        "distribution": distribution,
        "accelerating": accelerating,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# DB lookup

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "walkforward.db")


def get_flow_from_db(ticker, trade_date=None):
    """Baca flow result dari stockbit_flow DB. Fallback None kalau tidak ada."""
    if trade_date is None:
        from datetime import date
        trade_date = str(date.today())
    try:
        conn = sqlite3.connect(_DB_PATH)
        row = conn.execute(
            """SELECT composite_score, verdict, smart_money,
                      buy_lot, sell_lot, net_lot, net_value, last_price
               FROM stockbit_flow
               WHERE ticker=? AND trade_date=?
               AND composite_score IS NOT NULL""",
            (ticker, trade_date)
        ).fetchone()
        conn.close()
        if not row:
            return None
        score, verdict, smart_money, buy_lot, sell_lot, net_lot, net_value, last_price = row
        verdict_clean = verdict.replace("🟢 ","").replace("🔴 ","").replace("🟡 ","")
        return {
            "ticker": ticker, "score": score,
            "verdict": verdict_clean, "smart_money": smart_money,
            "buy_lot": buy_lot, "sell_lot": sell_lot,
            "net_lot": net_lot, "net_value": net_value,
            "last_price": last_price, "source": "db",
        }
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API — call these from scheduler.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_flow_confirmation(ticker, token=None):
    """
    Get flow score for a single ticker.

    Returns dict with score/verdict/smart_money, or None if unavailable.
    Score >= 3: BULLISH, <= -3: BEARISH, else NEUTRAL.
    """
    if not token:
        token = _load_token()
    if not token:
        return None

    data = _fetch_tradebook(token, ticker)
    if not data:
        return None

    bars = _parse_bars(data)
    return _analyze(ticker, bars)


def get_flow_batch(tickers, token=None, delay=1.2):
    """
    Get flow scores for multiple tickers.

    Returns dict: {ticker: flow_result, ...}
    Tickers with no data are omitted.
    """
    if not token:
        token = _load_token()
    if not token:
        return {}

    results = {}
    for ticker in tickers:
        data = _fetch_tradebook(token, ticker)
        if data:
            bars = _parse_bars(data)
            analysis = _analyze(ticker, bars)
            if analysis:
                results[ticker] = analysis
        time.sleep(delay)
    return results


def flow_confirms_signal(ticker, signal_direction="BUY", token=None):
    """
    Quick boolean check: does flow confirm a trade signal?

    Rules:
      BUY signal confirmed if:
        - flow score >= 1 (not necessarily full BULLISH)
        - smart_money NOT in [STRONG_SELL, MORNING_TRAP]

      SELL/SHORT signal confirmed if:
        - flow score <= -1
        - smart_money NOT in [STRONG_BUY, ACCUMULATION]

    Returns: (confirmed: bool, reason: str, flow_data: dict|None)
    """
    # DB-first: cek apakah hari ini sudah ada computed score
    flow = get_flow_from_db(ticker)
    if flow is None:
        flow = get_flow_confirmation(ticker, token)
    if flow is None:
        return True, "FLOW_UNAVAILABLE", None

    score = flow["score"]
    sm = flow["smart_money"]

    if signal_direction == "BUY":
        # Hard reject: bearish flow
        if score <= -3:
            return False, f"FLOW_BEARISH (score={score})", flow
        # Hard reject: smart money selling
        if sm in ("STRONG_SELL",):
            return False, f"SMART_MONEY_SELL (sm={sm}, score={score})", flow
        # Soft reject: morning trap with negative score
        if sm == "MORNING_TRAP" and score < 0:
            return False, f"MORNING_TRAP (sm={sm}, score={score})", flow
        # Weak but not blocking
        if score < 0:
            return True, f"FLOW_WEAK (score={score}, sm={sm})", flow
        # Confirmed
        return True, f"FLOW_OK (score={score}, sm={sm})", flow

    else:  # SELL
        if score >= 3:
            return False, f"FLOW_BULLISH (score={score})", flow
        if sm in ("STRONG_BUY",):
            return False, f"SMART_MONEY_BUY (sm={sm}, score={score})", flow
        if sm == "ACCUMULATION" and score > 0:
            return False, f"ACCUMULATION (sm={sm}, score={score})", flow
        if score > 0:
            return True, f"FLOW_WEAK (score={score}, sm={sm})", flow
        return True, f"FLOW_OK (score={score}, sm={sm})", flow


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Standalone test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    tickers = [t.upper() for t in sys.argv[1:]] or ["BBCA", "BRPT", "BRIS"]
    token = _load_token()
    if not token:
        print("ERROR: no .stockbit_token found")
        sys.exit(1)

    print(f"Testing flow filter for: {', '.join(tickers)}\n")
    for t in tickers:
        flow = get_flow_confirmation(t, token)
        if flow:
            print(f"  {t}: score={flow['score']:+d}  verdict={flow['verdict']}  "
                  f"sm={flow['smart_money']}  delta={flow['cum_delta']:+,}")
            confirmed, reason, _ = flow_confirms_signal(t, "BUY", token)
            print(f"    BUY confirmed={confirmed}  reason={reason}")
        else:
            print(f"  {t}: no data")
        time.sleep(1.2)
