"""
Flow Filter — Order flow analysis & signal confirmation.
==========================================================
Tradebook fetch, 5-strategy analysis, DB persistence, and signal-confirmation API.

Library usage:
    from flow_filter import get_flow_confirmation, get_flow_batch, flow_confirms_signal

CLI usage:
    python3 flow_filter.py                       # batch all tickers, save to DB, print report
    python3 flow_filter.py BBCA BRPT TLKM        # quick test, no DB write
    python3 flow_filter.py --token "$TOKEN" ...  # explicit token
"""

import os
import sys
import time
import sqlite3
import requests
from datetime import datetime, date

STOCKBIT_BASE = "https://exodus.stockbit.com"
HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".stockbit_token")
from config import DB_PATH as _DB_PATH

try:
    from data.fetcher import IDX80 as _TICKERS_FALLBACK
except Exception:
    _TICKERS_FALLBACK = []


def _load_token():
    """Load token from .stockbit_token file."""
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    except Exception:
        return None


def _load_tickers():
    """Load all active tickers from idx_tickers DB, fallback to hardcoded list."""
    try:
        from data.fetcher import load_all_tickers
        tickers = load_all_tickers()
        if tickers:
            return tickers
    except Exception:
        pass
    return _TICKERS_FALLBACK


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
    """Run 5 flow strategies, return rich result dict.

    Canonical keys: score, verdict (no emoji), smart_money, imbalance,
    divergence_type, cum_delta, price_chg_pct, absorption, distribution,
    accelerating, plus aggregate fields used for DB save / report rendering.
    """
    if not bars or len(bars) < 30:
        return None

    market_bars = [b for b in bars if "09:" <= b["time"] <= "16:"]
    if len(market_bars) < 20:
        return None

    # 1. Volume Imbalance (15-min buckets)
    buckets = {}
    for b in market_bars:
        hh, mm = b["time"].split(":")
        key = f"{hh}:{int(mm)//15*15:02d}"
        if key not in buckets:
            buckets[key] = {"buy": 0, "sell": 0}
        buckets[key]["buy"] += b["buy_lot"]
        buckets[key]["sell"] += b["sell_lot"]

    imbalances = []
    for t, v in sorted(buckets.items()):
        ratio = v["buy"] / max(v["sell"], 1)
        imbalances.append({"time": t, "ratio": round(ratio, 2), "buy": v["buy"], "sell": v["sell"]})

    strong_buy = sum(1 for x in imbalances if x["ratio"] > 1.5)
    strong_sell = sum(1 for x in imbalances if x["ratio"] < 0.67)
    imbalance = "BUY" if strong_buy > strong_sell + 2 else \
                "SELL" if strong_sell > strong_buy + 2 else "NEUTRAL"

    # 2. Cumulative Delta + Price Divergence
    cum_delta = sum(b["delta"] for b in market_bars)
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

    # 6. Value-Weighted Flow (IDR) — detects institutional smart money
    # net_value is in raw IDR from Stockbit (positive=net buy, negative=net sell)
    total_net_value = sum(b["net_value"] for b in market_bars)
    opening_net_value = sum(b["net_value"] for b in market_bars if "09:00" <= b["time"] <= "09:30")
    closing_net_value = sum(b["net_value"] for b in market_bars if "14:30" <= b["time"] <= "15:00")

    if opening_net_value > 0 and closing_net_value > 0:
        value_smart_money = "STRONG_BUY"
    elif opening_net_value < 0 and closing_net_value < 0:
        value_smart_money = "STRONG_SELL"
    elif opening_net_value > 0 and closing_net_value < 0:
        value_smart_money = "MORNING_TRAP"
    elif opening_net_value < 0 and closing_net_value > 0:
        value_smart_money = "ACCUMULATION"
    else:
        value_smart_money = "NEUTRAL"

    # Composite Score
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
    # Value confirmation: +1/-1 when IDR flow agrees with lot flow (stronger institutional signal)
    if value_smart_money in ("STRONG_BUY", "ACCUMULATION"): score += 1
    elif value_smart_money in ("STRONG_SELL", "MORNING_TRAP"): score -= 1

    verdict = "BULLISH" if score >= 3 else "BEARISH" if score <= -3 else "NEUTRAL"

    return {
        "ticker": ticker,
        "bars": len(market_bars),
        "score": score,
        "verdict": verdict,
        "smart_money": smart_money,
        "imbalance": imbalance,
        "imbalance_buy_count": strong_buy,
        "imbalance_sell_count": strong_sell,
        "divergence_type": divergence_type,
        "cum_delta": cum_delta,
        "price_chg_pct": price_chg,
        "absorption": absorption,
        "distribution": distribution,
        "opening_net": opening_net,
        "closing_net": closing_net,
        "first_30m_net": first_30,
        "last_30m_net": last_30,
        "accelerating": accelerating,
        "total_buy_lot": sum(b["buy_lot"] for b in market_bars),
        "total_sell_lot": sum(b["sell_lot"] for b in market_bars),
        "top_imbalance": sorted(imbalances, key=lambda x: x["ratio"], reverse=True)[:3],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        # Value-weighted (IDR) fields
        "total_net_value": total_net_value,
        "opening_net_value": opening_net_value,
        "closing_net_value": closing_net_value,
        "value_smart_money": value_smart_money,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB I/O
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_flow_from_db(ticker, trade_date=None):
    """Read flow result from stockbit_flow DB. Returns None if absent."""
    if trade_date is None:
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


def get_foreign_accumulation(ticker, days=5, db_path=None):
    """Net foreign (Asing) flow score over last N trading dates.

    Returns dict or None if fewer than `days` dates exist for this ticker.
    Keys: ticker, foreign_net_lots, avg_daily_vol_lots, score_pct, dates_used, latest_date
    score_pct = (foreign_net_5d / avg_daily_vol) x 100  -- positive = net buy
    """
    if db_path is None:
        db_path = _DB_PATH
    try:
        conn = sqlite3.connect(db_path)
        dates = [r[0] for r in conn.execute(
            """SELECT DISTINCT trade_date FROM broker_flow
               WHERE investor_type='Asing' AND ticker=?
               ORDER BY trade_date DESC LIMIT ?""",
            (ticker, days)
        ).fetchall()]

        if len(dates) < days:
            conn.close()
            return None

        placeholders = ",".join("?" * len(dates))
        net_lots = conn.execute(
            f"SELECT SUM(lot) FROM broker_flow"
            f" WHERE investor_type='Asing' AND ticker=? AND trade_date IN ({placeholders})",
            [ticker] + dates
        ).fetchone()[0] or 0

        ohlcv_row = conn.execute(
            f"SELECT AVG(volume), COUNT(*) FROM ohlcv WHERE ticker=? AND date IN ({placeholders})",
            [ticker] + dates
        ).fetchone()
        avg_vol = ohlcv_row[0]
        ohlcv_count = ohlcv_row[1]
        conn.close()

        avg_vol_lots = (avg_vol / 100) if avg_vol else 0
        # Use actual ohlcv count (not days) to normalise — avoids inflated scores when dates are missing
        score_pct = round((net_lots / avg_vol_lots * 100), 2) if avg_vol_lots > 0 else 0.0

        return {
            "ticker": ticker,
            "foreign_net_lots": net_lots,
            "avg_daily_vol_lots": round(avg_vol_lots),
            "score_pct": score_pct,
            "dates_used": len(dates),
            "ohlcv_dates": ohlcv_count,
            "latest_date": dates[0],
        }
    except Exception as e:
        print(f"[ForeignFlow] get_foreign_accumulation({ticker}) failed: {e}")
        return None


def get_top_foreign_accumulation(tickers=None, days=5, top_n=10, db_path=None):
    """Return top N tickers ranked by foreign accumulation score_pct.

    If tickers is None, queries all tickers that have Asing data.
    Returns list of dicts (same shape as get_foreign_accumulation), sorted desc by score_pct.
    """
    if db_path is None:
        db_path = _DB_PATH
    if tickers is None:
        try:
            conn = sqlite3.connect(db_path)
            tickers = [r[0] for r in conn.execute(
                "SELECT DISTINCT ticker FROM broker_flow WHERE investor_type='Asing'"
            ).fetchall()]
            conn.close()
        except Exception as e:
            print(f"[ForeignFlow] get_top_foreign_accumulation ticker query failed: {e}")
            return []

    results = []
    for t in tickers:
        r = get_foreign_accumulation(t, days=days, db_path=db_path)
        if r is not None:
            results.append(r)

    results.sort(key=lambda x: x["score_pct"], reverse=True)
    return results[:top_n]


def save_results_to_db(results, db_path=None):
    """Persist analyze() results into stockbit_flow table."""
    if db_path is None:
        db_path = _DB_PATH
    trade_date = str(date.today())
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stockbit_flow (
            ticker TEXT, trade_date TEXT, composite_score INTEGER,
            verdict TEXT, smart_money TEXT, buy_lot INTEGER,
            sell_lot INTEGER, net_lot INTEGER, net_value INTEGER,
            last_price INTEGER, updated_at TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(stockbit_flow)").fetchall()}
    if "foreign_score" not in existing_cols:
        conn.execute("ALTER TABLE stockbit_flow ADD COLUMN foreign_score REAL")
        conn.commit()
    saved = 0
    for r in results:
        # Re-emoji verdict for DB consistency with legacy rows
        verdict_emoji = {"BULLISH": "🟢 BULLISH", "BEARISH": "🔴 BEARISH", "NEUTRAL": "🟡 NEUTRAL"}.get(r["verdict"], r["verdict"])
        fa = get_foreign_accumulation(r["ticker"], db_path=db_path)
        foreign_score = fa["score_pct"] if fa else None
        conn.execute("""
            INSERT OR REPLACE INTO stockbit_flow
            (ticker, trade_date, composite_score, verdict, smart_money,
             buy_lot, sell_lot, net_lot, net_value, last_price, updated_at, foreign_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["ticker"], trade_date,
            r["score"], verdict_emoji, r["smart_money"],
            r.get("total_buy_lot", 0), r.get("total_sell_lot", 0),
            r.get("cum_delta", 0),
            r.get("total_net_value", 0), 0,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            foreign_score,
        ))
        saved += 1
    conn.commit()
    conn.close()
    print(f"[FlowDB] {saved} tickers saved for {trade_date}")
    return saved


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BANDAR DETECTOR — numeric accdist pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ACCDIST_SCORE_MAP = {
    'Big Acc':    3,
    'Normal Acc': 2,
    'Small Acc':  1,
    'Neutral':    0,
    'Small Dist': -1,
    'Normal Dist': -2,
    'Big Dist':   -3,
    'Acc':        1,   # top-level broker_accdist short label
    'Dist':       -1,  # top-level broker_accdist short label
}


def accdist_label_to_score(label):
    """Convert bandar_detector text label to integer score.

    Stockbit stores labels like 'Big Acc', 'Normal Dist', 'Acc', 'Dist'.
    SQLite CAST of these to REAL returns 0.0, causing 100% accumulation bias
    in any query that treats broker_accdist as numeric. Use this instead.
    """
    if not label:
        return 0
    return _ACCDIST_SCORE_MAP.get(str(label).strip(), 0)


def get_market_accdist_summary(date=None):
    """Compute market-wide accumulation/distribution score from bandar_detector.

    Returns a dict with numeric fields so callers don't need to handle
    text labels. All values are 0 / 'NEUTRAL' when no data exists.
    """
    from datetime import date as _date
    if date is None:
        date = str(_date.today())

    empty = {
        'date': date, 'total': 0,
        'dist_count': 0, 'acc_count': 0, 'neutral_count': 0,
        'dist_pct': 0.0, 'acc_pct': 0.0,
        'avg_numeric_score': 0.0,
        'label': 'NEUTRAL',
    }
    try:
        conn = sqlite3.connect(_DB_PATH)
        rows = conn.execute(
            "SELECT broker_accdist FROM bandar_detector WHERE trade_date=?",
            (date,),
        ).fetchall()
        conn.close()
    except Exception:
        return empty

    if not rows:
        return empty

    scores = [accdist_label_to_score(r[0]) for r in rows]
    total = len(scores)
    dist_count = sum(1 for s in scores if s < 0)
    acc_count = sum(1 for s in scores if s > 0)
    neutral_count = total - dist_count - acc_count
    dist_pct = round(dist_count / total * 100, 1)
    acc_pct = round(acc_count / total * 100, 1)
    avg_score = round(sum(scores) / total, 3)

    if dist_pct >= 65:
        label = 'STRONG_DISTRIBUTION' if dist_pct >= 75 else 'DISTRIBUTION'
    elif acc_pct >= 65:
        label = 'STRONG_ACCUMULATION' if acc_pct >= 75 else 'ACCUMULATION'
    else:
        label = 'NEUTRAL'

    return {
        'date': date,
        'total': total,
        'dist_count': dist_count,
        'acc_count': acc_count,
        'neutral_count': neutral_count,
        'dist_pct': dist_pct,
        'acc_pct': acc_pct,
        'avg_numeric_score': avg_score,
        'label': label,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API — call these from scheduler.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_flow_confirmation(ticker, token=None):
    """Get flow score for a single ticker. Returns dict or None."""
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
    """Get flow scores for multiple tickers. Returns {ticker: result}."""
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
    """Boolean check: does flow confirm a trade signal?

    Returns: (confirmed: bool, reason: str, flow_data: dict|None)
    """
    flow = get_flow_from_db(ticker)
    if flow is None:
        flow = get_flow_confirmation(ticker, token)
    if flow is None:
        return True, "FLOW_UNAVAILABLE", None

    score = flow["score"]
    sm = flow["smart_money"]

    # Foreign accumulation adjustment (±1 when Asing net flow > 2% of avg daily vol)
    fa = get_foreign_accumulation(ticker)
    if fa is not None:
        if fa["score_pct"] > 2:
            score += 1
        elif fa["score_pct"] < -2:
            score -= 1

    if signal_direction == "BUY":
        if score <= -3:
            return False, f"FLOW_BEARISH (score={score})", flow
        if sm in ("STRONG_SELL",):
            return False, f"SMART_MONEY_SELL (sm={sm}, score={score})", flow
        if sm == "MORNING_TRAP" and score < 0:
            return False, f"MORNING_TRAP (sm={sm}, score={score})", flow
        if score < 0:
            return True, f"FLOW_WEAK (score={score}, sm={sm})", flow
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
# CLI: report renderer + entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def print_report(results):
    """Print formatted analysis report sorted by score."""
    print("\n" + "=" * 70)
    print(f"  ORDER FLOW REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results.sort(key=lambda x: x["score"], reverse=True)
    bullish = [r for r in results if r["score"] >= 3]
    bearish = [r for r in results if r["score"] <= -3]
    neutral = [r for r in results if -3 < r["score"] < 3]

    def line(r):
        div = f"DIV:{r['divergence_type']}" if r["divergence_type"] else ""
        return (f"  {r['ticker']:6} Score={r['score']:+d}  "
                f"Delta={r['cum_delta']:+,}  Price={r['price_chg_pct']:+.1f}%  "
                f"SM={r['smart_money']:15} {div}")

    print(f"\n🟢 BULLISH ({len(bullish)}):")
    print("-" * 70)
    for r in bullish:
        print(line(r))

    print(f"\n🔴 BEARISH ({len(bearish)}):")
    print("-" * 70)
    for r in bearish:
        print(line(r))

    print(f"\n🟡 NEUTRAL ({len(neutral)}):")
    print("-" * 70)
    for r in sorted(neutral, key=lambda x: x["score"], reverse=True):
        print(f"  {r['ticker']:6} Score={r['score']:+d}  "
              f"Delta={r['cum_delta']:+,}  Price={r['price_chg_pct']:+.1f}%  "
              f"SM={r['smart_money']}")

    top5 = results[:5]
    print(f"\n{'='*70}")
    print("  TOP 5 DETAIL")
    print(f"{'='*70}")
    for r in top5:
        div = f"  ⚠️ DIVERGENCE: {r['divergence_type']}" if r["divergence_type"] else ""
        accel = "📈 Accelerating" if r["accelerating"] else "📉 Decelerating"
        print(f"\n  {r['ticker']} — {r['verdict']} (Score: {r['score']:+d})")
        print(f"  ├─ Imbalance: {r['imbalance']} "
              f"(Buy buckets: {r['imbalance_buy_count']}, Sell: {r['imbalance_sell_count']})")
        print(f"  ├─ Cum Delta: {r['cum_delta']:+,} lots  |  Price: {r['price_chg_pct']:+.1f}%{div}")
        print(f"  ├─ Absorption: {r['absorption']}  |  Distribution: {r['distribution']}")
        print(f"  ├─ Session: Opening={r['opening_net']:+,}  Closing={r['closing_net']:+,}  → {r['smart_money']}")
        print(f"  └─ Flow: First30m={r['first_30m_net']:+,}  Last30m={r['last_30m_net']:+,}  {accel}")


def main():
    args = sys.argv[1:]
    token = None
    if "--token" in args:
        idx = args.index("--token")
        token = args[idx + 1]
        args = [a for a in args if a != "--token" and a != token]

    if not token:
        token = _load_token()
    if not token:
        print("ERROR: --token required or .stockbit_token file")
        sys.exit(1)

    explicit = bool(args)
    tickers = [t.upper() for t in args] if explicit else _load_tickers()

    print(f"Fetching & analyzing {len(tickers)} tickers...")
    results = []
    for i, ticker in enumerate(tickers, 1):
        sys.stdout.write(f"\r  [{i}/{len(tickers)}] {ticker}...      ")
        sys.stdout.flush()
        try:
            data = _fetch_tradebook(token, ticker)
            if data:
                bars = _parse_bars(data)
                analysis = _analyze(ticker, bars)
                if analysis:
                    results.append(analysis)
        except Exception:
            pass
        time.sleep(1.2)

    print(f"\r  Analyzed: {len(results)}/{len(tickers)} tickers")

    if results:
        # Save to DB only in batch (no-arg) mode — quick tests stay read-only
        if not explicit:
            save_results_to_db(results)
        print_report(results)


if __name__ == "__main__":
    main()
