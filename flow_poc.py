#!/usr/bin/env python3
"""
Order Flow POC — Analyze intraday flow patterns
================================================
Fetch hari ini, analisis 5 strategi flow, rank tickers.

Usage:
  python3 flow_poc.py --token "$(cat .stockbit_token)"
  python3 flow_poc.py --token "$(cat .stockbit_token)" BBCA BRPT TLKM
"""

import sys
import json
import time
import requests
from datetime import datetime

STOCKBIT_BASE = "https://exodus.stockbit.com"
HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}

TICKERS = [
    "ACES","ADRO","AKRA","AMMN","AMRT","ANTM","ARTO","ASII",
    "BBCA","BBNI","BBRI","BBTN","BMRI","BREN","BRPT","BRIS",
    "BRMS","BUKA","CPIN","CTRA","EMTK","ERAA","ESSA","EXCL",
    "GGRM","GOTO","HRUM","ICBP","INCO","INDF","INKP","INTP",
    "ISAT","ITMG","JSMR","KLBF","LPPF","LSIP","MAPI","MBMA",
    "MDKA","MEDC","MIKA","MNCN","MTEL","NCKL","NISP","PGAS",
    "PGEO","PNBN","PTBA","PWON","RAJA","SCMA","SIDO","SMGR",
    "SMRA","SRTG","SSMS","TAPG","TBIG","TINS","TKIM","TLKM",
    "TOWR","TPIA","UNTR","UNVR","WIKA","WMUU","WTON",
]


def fetch_tradebook(token, ticker):
    """Fetch 1-minute tradebook chart."""
    r = requests.get(
        f"{STOCKBIT_BASE}/order-trade/trade-book/chart",
        params={"symbol": ticker, "time_interval": "1m"},
        headers={**HEADERS_BASE, "Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    return r.json().get("data")


def parse_bars(data):
    """Parse tradebook data into minute-by-minute arrays."""
    bars = []
    buys = data.get("buy", [])
    sells = data.get("sell", [])
    net_vals = data.get("net_values", [])
    prices = data.get("prices", [])

    n = min(len(buys), len(sells), len(prices))
    for i in range(n):
        t = buys[i].get("time", "")
        bl = int(buys[i]["lot"]["raw"]) if buys[i].get("lot") and buys[i]["lot"].get("raw") else 0
        sl = int(sells[i]["lot"]["raw"]) if sells[i].get("lot") and sells[i]["lot"].get("raw") else 0
        bf = int(buys[i]["frequency"]["raw"]) if buys[i].get("frequency") and buys[i]["frequency"].get("raw") else 0
        sf = int(sells[i]["frequency"]["raw"]) if sells[i].get("frequency") and sells[i]["frequency"].get("raw") else 0
        nv = int(net_vals[i]["value"]["raw"]) if i < len(net_vals) and net_vals[i].get("value") and net_vals[i]["value"].get("raw") else 0
        px = int(prices[i]["value"]["raw"]) if i < len(prices) and prices[i].get("value") and prices[i]["value"].get("raw") else 0

        bars.append({
            "time": t, "buy_lot": bl, "sell_lot": sl,
            "buy_freq": bf, "sell_freq": sf,
            "net_value": nv, "price": px,
            "delta": bl - sl,
        })
    return bars


def analyze_flow(ticker, bars):
    """Run all 5 flow analysis strategies on minute bars."""
    if not bars or len(bars) < 30:
        return None

    result = {"ticker": ticker, "bars": len(bars)}

    # Filter market hours only (09:00 - 16:15)
    market_bars = [b for b in bars if "09:" <= b["time"] <= "16:"]
    if len(market_bars) < 20:
        return None

    # ── 1. Volume Imbalance ──
    # Split into 15-min buckets, calc buy/sell ratio
    buckets_15m = {}
    for b in market_bars:
        hh, mm = b["time"].split(":")
        bucket = f"{hh}:{int(mm)//15*15:02d}"
        if bucket not in buckets_15m:
            buckets_15m[bucket] = {"buy": 0, "sell": 0}
        buckets_15m[bucket]["buy"] += b["buy_lot"]
        buckets_15m[bucket]["sell"] += b["sell_lot"]

    imbalances = []
    for t, v in sorted(buckets_15m.items()):
        ratio = v["buy"] / max(v["sell"], 1)
        imbalances.append({"time": t, "ratio": round(ratio, 2), "buy": v["buy"], "sell": v["sell"]})

    # Count strong buy/sell imbalances
    strong_buy_buckets = [x for x in imbalances if x["ratio"] > 1.5]
    strong_sell_buckets = [x for x in imbalances if x["ratio"] < 0.67]
    result["imbalance_buy_count"] = len(strong_buy_buckets)
    result["imbalance_sell_count"] = len(strong_sell_buckets)
    result["imbalance_signal"] = "BUY" if len(strong_buy_buckets) > len(strong_sell_buckets) + 2 else \
                                  "SELL" if len(strong_sell_buckets) > len(strong_buy_buckets) + 2 else "NEUTRAL"

    # ── 2. Cumulative Delta + Price Divergence ──
    cum_delta = []
    running = 0
    for b in market_bars:
        running += b["delta"]
        cum_delta.append(running)

    # Compare first half vs second half
    mid = len(cum_delta) // 2
    first_half_delta = cum_delta[mid] - cum_delta[0]
    second_half_delta = cum_delta[-1] - cum_delta[mid]

    first_price = market_bars[0]["price"]
    mid_price = market_bars[mid]["price"]
    last_price = market_bars[-1]["price"]
    first_half_price_chg = (mid_price - first_price) / max(first_price, 1)
    second_half_price_chg = (last_price - mid_price) / max(mid_price, 1)

    # Divergence: delta direction != price direction
    result["cum_delta_total"] = cum_delta[-1]
    result["price_chg_pct"] = round((last_price - first_price) / max(first_price, 1) * 100, 2)
    result["total_buy_lot"] = sum(b["buy_lot"] for b in market_bars)
    result["total_sell_lot"] = sum(b["sell_lot"] for b in market_bars)

    delta_up = cum_delta[-1] > 0
    price_up = last_price > first_price
    result["divergence"] = (delta_up and not price_up) or (not delta_up and price_up)
    result["divergence_type"] = ""
    if delta_up and not price_up:
        result["divergence_type"] = "BULLISH_DIV"  # buying but price down = accumulation
    elif not delta_up and price_up:
        result["divergence_type"] = "BEARISH_DIV"  # selling but price up = distribution

    # ── 3. Absorption Detection ──
    # Windows where sell >> buy but price holds or rises
    absorption_count = 0
    distribution_count = 0
    window = 15
    for i in range(window, len(market_bars)):
        win_bars = market_bars[i-window:i]
        win_buy = sum(b["buy_lot"] for b in win_bars)
        win_sell = sum(b["sell_lot"] for b in win_bars)
        win_price_start = win_bars[0]["price"]
        win_price_end = win_bars[-1]["price"]

        if win_sell > win_buy * 1.5 and win_price_end >= win_price_start:
            absorption_count += 1  # big selling absorbed
        if win_buy > win_sell * 1.5 and win_price_end <= win_price_start:
            distribution_count += 1  # big buying but no price rise

    result["absorption_count"] = absorption_count
    result["distribution_count"] = distribution_count

    # ── 4. Session Flow (Opening vs Closing) ──
    opening = [b for b in market_bars if "09:00" <= b["time"] <= "09:30"]
    closing = [b for b in market_bars if "14:30" <= b["time"] <= "15:00"]
    lunch_pre = [b for b in market_bars if "11:00" <= b["time"] <= "11:30"]
    lunch_post = [b for b in market_bars if "13:30" <= b["time"] <= "14:00"]

    def session_net(session_bars):
        if not session_bars:
            return 0
        return sum(b["delta"] for b in session_bars)

    result["opening_net"] = session_net(opening)
    result["closing_net"] = session_net(closing)
    result["smart_money_signal"] = ""
    if result["opening_net"] > 0 and result["closing_net"] > 0:
        result["smart_money_signal"] = "STRONG_BUY"
    elif result["opening_net"] < 0 and result["closing_net"] < 0:
        result["smart_money_signal"] = "STRONG_SELL"
    elif result["opening_net"] > 0 and result["closing_net"] < 0:
        result["smart_money_signal"] = "MORNING_TRAP"  # retail buy morning, smart sell afternoon
    elif result["opening_net"] < 0 and result["closing_net"] > 0:
        result["smart_money_signal"] = "ACCUMULATION"  # smart buy quietly in afternoon

    # ── 5. Flow Acceleration ──
    # Last 30 min net vs first 30 min net
    first_30 = market_bars[:30]
    last_30 = market_bars[-30:]
    result["first_30m_net"] = sum(b["delta"] for b in first_30)
    result["last_30m_net"] = sum(b["delta"] for b in last_30)
    result["flow_accelerating"] = result["last_30m_net"] > result["first_30m_net"]

    # ── Composite Score ──
    score = 0
    if result["imbalance_signal"] == "BUY": score += 2
    elif result["imbalance_signal"] == "SELL": score -= 2
    if result["divergence_type"] == "BULLISH_DIV": score += 2
    elif result["divergence_type"] == "BEARISH_DIV": score -= 2
    if result["absorption_count"] > 3: score += 1
    if result["distribution_count"] > 3: score -= 1
    if result["smart_money_signal"] == "STRONG_BUY": score += 2
    elif result["smart_money_signal"] == "ACCUMULATION": score += 1
    elif result["smart_money_signal"] == "STRONG_SELL": score -= 2
    elif result["smart_money_signal"] == "MORNING_TRAP": score -= 1
    if result["flow_accelerating"]: score += 1
    else: score -= 1

    result["composite_score"] = score
    result["verdict"] = "🟢 BULLISH" if score >= 3 else "🔴 BEARISH" if score <= -3 else "🟡 NEUTRAL"

    # Top imbalance buckets for display
    result["top_imbalance"] = sorted(imbalances, key=lambda x: x["ratio"], reverse=True)[:3]

    return result


def print_report(results):
    """Print formatted analysis report."""
    print("\n" + "=" * 70)
    print(f"  ORDER FLOW POC — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Sort by composite score
    results.sort(key=lambda x: x["composite_score"], reverse=True)

    # Top Bullish
    bullish = [r for r in results if r["composite_score"] >= 3]
    bearish = [r for r in results if r["composite_score"] <= -3]
    neutral = [r for r in results if -3 < r["composite_score"] < 3]

    print(f"\n🟢 BULLISH ({len(bullish)}):")
    print("-" * 70)
    for r in bullish:
        print(f"  {r['ticker']:6} Score={r['composite_score']:+d}  "
              f"Delta={r['cum_delta_total']:+,}  Price={r['price_chg_pct']:+.1f}%  "
              f"SM={r['smart_money_signal']:15} "
              f"{'DIV:'+r['divergence_type'] if r['divergence'] else ''}")

    print(f"\n🔴 BEARISH ({len(bearish)}):")
    print("-" * 70)
    for r in bearish:
        print(f"  {r['ticker']:6} Score={r['composite_score']:+d}  "
              f"Delta={r['cum_delta_total']:+,}  Price={r['price_chg_pct']:+.1f}%  "
              f"SM={r['smart_money_signal']:15} "
              f"{'DIV:'+r['divergence_type'] if r['divergence'] else ''}")

    print(f"\n🟡 NEUTRAL ({len(neutral)}):")
    print("-" * 70)
    for r in sorted(neutral, key=lambda x: x["composite_score"], reverse=True):
        print(f"  {r['ticker']:6} Score={r['composite_score']:+d}  "
              f"Delta={r['cum_delta_total']:+,}  Price={r['price_chg_pct']:+.1f}%  "
              f"SM={r['smart_money_signal']}")

    # Detailed view for top 5
    top5 = results[:5]
    print(f"\n{'='*70}")
    print("  TOP 5 DETAIL")
    print(f"{'='*70}")
    for r in top5:
        print(f"\n  {r['ticker']} — {r['verdict']} (Score: {r['composite_score']:+d})")
        print(f"  ├─ Imbalance: {r['imbalance_signal']} "
              f"(Buy buckets: {r['imbalance_buy_count']}, Sell: {r['imbalance_sell_count']})")
        print(f"  ├─ Cum Delta: {r['cum_delta_total']:+,} lots  |  Price: {r['price_chg_pct']:+.1f}%"
              f"{'  ⚠️ DIVERGENCE: '+r['divergence_type'] if r['divergence'] else ''}")
        print(f"  ├─ Absorption: {r['absorption_count']}  |  Distribution: {r['distribution_count']}")
        print(f"  ├─ Session: Opening={r['opening_net']:+,}  Closing={r['closing_net']:+,}  → {r['smart_money_signal']}")
        print(f"  └─ Flow: First30m={r['first_30m_net']:+,}  Last30m={r['last_30m_net']:+,}  "
              f"{'📈 Accelerating' if r['flow_accelerating'] else '📉 Decelerating'}")



def save_results_to_db(results, db_path=None):
    """Save flow analysis results ke stockbit_flow table."""
    import sqlite3
    from datetime import date
    if db_path is None:
        import os
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "walkforward.db")
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
    saved = 0
    for r in results:
        conn.execute("""
            INSERT OR REPLACE INTO stockbit_flow
            (ticker, trade_date, composite_score, verdict, smart_money,
             buy_lot, sell_lot, net_lot, net_value, last_price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["ticker"], trade_date,
            r["composite_score"], r["verdict"],
            r.get("smart_money_signal", ""),
            r.get("total_buy_lot", r.get("imbalance_buy_count", 0)),
            r.get("total_sell_lot", r.get("imbalance_sell_count", 0)),
            r.get("cum_delta_total", 0),
            0, 0,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        saved += 1
    conn.commit()
    conn.close()
    print(f"[FlowDB] {saved} tickers saved for {trade_date}")
    return saved

def main():
    args = sys.argv[1:]
    token = None
    if "--token" in args:
        idx = args.index("--token")
        token = args[idx + 1]
        args = [a for a in args if a != "--token" and a != token]

    tickers = [t.upper() for t in args] if args else TICKERS

    if not token:
        try:
            token = open(".stockbit_token").read().strip()
        except Exception:
            pass

    if not token:
        print("ERROR: --token required or .stockbit_token file")
        sys.exit(1)

    print(f"Fetching & analyzing {len(tickers)} tickers...")
    results = []
    for i, ticker in enumerate(tickers, 1):
        sys.stdout.write(f"\r  [{i}/{len(tickers)}] {ticker}...      ")
        sys.stdout.flush()
        try:
            data = fetch_tradebook(token, ticker)
            if data:
                bars = parse_bars(data)
                analysis = analyze_flow(ticker, bars)
                if analysis:
                    results.append(analysis)
        except Exception as e:
            pass
        time.sleep(1.2)

    print(f"\r  Analyzed: {len(results)}/{len(tickers)} tickers")

    if results:
        save_results_to_db(results)
        print_report(results)


if __name__ == "__main__":
    main()
