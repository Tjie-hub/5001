#!/usr/bin/env python3
"""
Stockbit Keystats Fetcher (Opsi B)
===================================
- Auto-baca JWT token dari Chrome localStorage (Stockbit session)
- Fetch keystats untuk semua ticker (IDX30 / LQ45 / IDX80)
- Simpan ke walkforward.db

Syarat: Chrome harus buka & login ke stockbit.com di Ubuntu

Usage:
  python3 stockbit_fetcher.py                     # fetch all IDX80
  python3 stockbit_fetcher.py --cat IDX30         # fetch IDX30 only
  python3 stockbit_fetcher.py --cat LQ45          # fetch LQ45 only
  python3 stockbit_fetcher.py BBCA BRPT           # fetch specific tickers
  python3 stockbit_fetcher.py --token XXX         # manual token override

  python3 stockbit_fetcher.py flow                # flow fetch all IDX80
  python3 stockbit_fetcher.py flow --cat IDX30    # flow fetch IDX30 only

Cron (setiap hari 08:50 WIB sebelum market):
  See deploy/crontab (cron_wrap-ed OHLCV fetch at 08:50 Mon-Fri).
"""

import os
import sys
import glob
import re
import json
import time
import sqlite3
from data.db import connect as db_connect
import requests
import base64
from datetime import datetime
from flow_filter import _parse_bars, _analyze

# === CONFIG ===
_HERE = os.path.dirname(os.path.abspath(__file__))
WALKFORWARD_DB = os.path.join(_HERE, "data", "walkforward.db")
CHROME_LOCALSTORAGE = os.path.expanduser(
    "~/.config/google-chrome/Default/Local Storage/leveldb"
)
STOCKBIT_BASE = "https://exodus.stockbit.com"
RATE_LIMIT_DELAY = 1.5  # seconds between requests

from data.fetcher import IDX30, LQ45, IDX80, CATEGORIES, TICKERS


def get_tickers(category: str = None) -> list:
    """Return ticker list for a category, ALL (from DB), or IDX80 by default."""
    if category is None:
        return TICKERS
    cat = category.upper()
    if cat == "ALL":
        try:
            from data.fetcher import load_all_tickers
            tickers = load_all_tickers()
            if tickers:
                return tickers
        except Exception:
            pass
        return IDX80
    if cat not in CATEGORIES:
        raise ValueError(f"Unknown category '{category}'. Use: IDX30, LQ45, IDX80, ALL")
    return CATEGORIES[cat]

# Keystats fields we care about (fitem_id -> column name)
KEYSTATS_MAP = {
    "2891": "pe_ttm",
    "12148": "pe_ann",
    "16577": "pe_forward",
    "2896": "pbv",
    "2893": "ps_ttm",
    "13200": "eps_ttm",
    "15718": "bvps",
    "2898": "earnings_yield",
    "16533": "pcf_ttm",
    "15881": "pfcf_ttm",
    "2897": "ev_ebit",
    "21457": "ev_ebitda",
    "13431": "peg_ratio",
    "15882": "fcf_per_share",
    "15879": "cash_per_share",
    "15880": "revenue_per_share",
    # Profitability (will discover IDs from data)
    "1498": "current_ratio",
    "1500": "quick_ratio",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def send_telegram(msg):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("Telegram not configured")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        log(f"Telegram send failed: {e}")


def extract_token_from_chrome():
    """Scan Chrome LevelDB localStorage files for Stockbit JWT token."""
    # Try read from .stockbit_token file FIRST
    token_file = os.path.join(_HERE, ".stockbit_token")
    if os.path.isfile(token_file):
        try:
            with open(token_file, 'r') as f:
                token = f.read().strip()
            if token and token.startswith('eyJ'):
                log(f"✅ Token loaded from {token_file}")
                return token
        except Exception as e:
            log(f"⚠️ Failed to read token file: {e}")
    
    if not os.path.isdir(CHROME_LOCALSTORAGE):
        log(f"Chrome localStorage not found at {CHROME_LOCALSTORAGE}")
        return None

    log("Scanning Chrome localStorage for Stockbit token...")

    # JWT pattern: starts with eyJ, 3 base64 parts separated by dots
    jwt_pattern = re.compile(
        r'(eyJ[A-Za-z0-9_-]{50,}\.eyJ[A-Za-z0-9_-]{50,}\.[A-Za-z0-9_-]{50,})'
    )

    # Scan all .log and .ldb files in the leveldb directory
    candidates = []
    for ext in ["*.log", "*.ldb"]:
        for fpath in glob.glob(os.path.join(CHROME_LOCALSTORAGE, ext)):
            try:
                with open(fpath, "rb") as f:
                    raw = f.read()
                    # Try to find stockbit-related content
                    if b"stockbit" in raw.lower() or b"exodus" in raw.lower():
                        text = raw.decode("utf-8", errors="ignore")
                        matches = jwt_pattern.findall(text)
                        for m in matches:
                            try:
                                # Decode JWT payload to verify it's Stockbit
                                payload_b64 = m.split(".")[1]
                                # Fix padding
                                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                                payload = json.loads(
                                    base64.urlsafe_b64decode(payload_b64)
                                )
                                if payload.get("iss") == "STOCKBIT":
                                    exp = payload.get("exp", 0)
                                    candidates.append((m, exp))
                            except Exception:
                                pass
            except Exception:
                pass

    if not candidates:
        log("No Stockbit JWT found in Chrome localStorage")
        return None

    # Pick the one with latest expiry
    candidates.sort(key=lambda x: x[1], reverse=True)
    token, exp = candidates[0]
    exp_dt = datetime.fromtimestamp(exp)
    now = datetime.now()

    if exp_dt < now:
        log(f"Token found but EXPIRED at {exp_dt}. Buka Chrome & refresh Stockbit.")
        return None

    remaining = (exp_dt - now).total_seconds() / 3600
    log(f"Token found! Expires: {exp_dt} ({remaining:.1f}h remaining)")
    return token


def verify_token(token):
    """Quick verification that token works."""
    r = requests.get(
        f"{STOCKBIT_BASE}/keystats/BBCA",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36", "Origin": "https://stockbit.com", "Referer": "https://stockbit.com/"},
        timeout=10,
    )
    return r.status_code == 200


def ensure_valid_token(manual_token=None):
    """Return a valid token, running auto_token refresh/login if needed."""
    if manual_token:
        log("Using manual token")
        if verify_token(manual_token):
            return manual_token
        log("ERROR: Manual token invalid")
        return None

    token = extract_token_from_chrome()
    if token and verify_token(token):
        log("Token OK!")
        return token

    log("Token invalid/missing — running auto_token refresh...")
    try:
        import auto_token as at
        new_token = at.auto_refresh()
        if new_token and at.verify_token(new_token):
            token_file = os.path.join(_HERE, ".stockbit_token")
            with open(token_file, "w") as f:
                f.write(new_token)
            log("✅ Token refreshed via auto_token")
            return new_token

        log("Auto refresh failed — trying credential login...")
        new_token = at.credential_login()
        if new_token and at.verify_token(new_token):
            token_file = os.path.join(_HERE, ".stockbit_token")
            with open(token_file, "w") as f:
                f.write(new_token)
            log("✅ Token obtained via credential login")
            return new_token
    except Exception as e:
        log(f"auto_token error: {e}")

    return None


def fetch_keystats(token, ticker):
    """Fetch keystats for a single ticker."""
    r = requests.get(
        f"{STOCKBIT_BASE}/keystats/{ticker}",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Origin": "https://stockbit.com",
            "Referer": "https://stockbit.com/",
        },
        timeout=15,
    )
    if r.status_code != 200:
        return None

    data = r.json()
    result = {"ticker": ticker}

    # Parse the nested structure
    closures = data.get("data", {}).get("closure_fin_items_results", [])
    for group in closures:
        group_name = group.get("keystats_name", "")
        for item in group.get("fin_name_results", []):
            fitem_id = item.get("fitem_id", "")
            fitem_name = item.get("fitem_name", "")
            fitem_value = item.get("fitem_value", "")

            # Map by known ID
            if fitem_id in KEYSTATS_MAP:
                col = KEYSTATS_MAP[fitem_id]
                result[col] = parse_value(fitem_value)

            # All remaining fields by ID
            extra_map = {
                "1461": "roe", "1460": "roa", "1462": "roce",
                "1508": "der", "1573": "liab_equity",
                "1563": "npm", "1561": "gpm", "1562": "opm",
                "2915": "div_yield", "2916": "payout_ratio",
                "1554": "rev_growth", "18214": "earn_growth",
                "13366": "piotroski", "1555": "net_income",
                "2997": "revenue", "1567": "return_1y",
                "1502": "fin_leverage", "13447": "roic",
            }
            if fitem_id in extra_map and extra_map[fitem_id] not in result:
                result[extra_map[fitem_id]] = parse_value(fitem_value)

    return result


def parse_value(val):
    """Parse Stockbit formatted value to float."""
    if not val or val == "-" or val == "N/A":
        return None
    try:
        # Remove %, commas, Tn, Bn, etc
        cleaned = val.replace(",", "").replace("%", "").strip()
        # Handle Tn (trillion) / Bn (billion) / Mn (million)
        multiplier = 1
        if cleaned.endswith("Tn"):
            cleaned = cleaned[:-2]
            multiplier = 1e12
        elif cleaned.endswith("Bn"):
            cleaned = cleaned[:-2]
            multiplier = 1e9
        elif cleaned.endswith("Mn"):
            cleaned = cleaned[:-2]
            multiplier = 1e6
        elif cleaned.endswith("T"):
            cleaned = cleaned[:-1]
            multiplier = 1e12
        elif cleaned.endswith("B"):
            cleaned = cleaned[:-1]
            multiplier = 1e9
        elif cleaned.endswith("M"):
            cleaned = cleaned[:-1]
            multiplier = 1e6
        return float(cleaned) * multiplier
    except (ValueError, TypeError):
        return None


def init_db():
    """Create stockbit_keystats table if not exists."""
    conn = db_connect(WALKFORWARD_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stockbit_keystats (
            ticker TEXT NOT NULL,
            fetch_date TEXT NOT NULL,
            pe_ttm REAL, pe_ann REAL, pe_forward REAL,
            pbv REAL, ps_ttm REAL,
            eps_ttm REAL, bvps REAL,
            earnings_yield REAL,
            pcf_ttm REAL, pfcf_ttm REAL,
            ev_ebit REAL, ev_ebitda REAL,
            peg_ratio REAL,
            fcf_per_share REAL, cash_per_share REAL, revenue_per_share REAL,
            current_ratio REAL, quick_ratio REAL,
            roe REAL, roa REAL,
            market_cap REAL, der REAL,
            npm REAL, div_yield REAL,
            rev_growth REAL, earn_growth REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, fetch_date)
        )
    """)
    conn.commit()
    return conn


def save_keystats(conn, stats):
    """Insert or replace keystats for a ticker."""
    now = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    cols = [
        "ticker", "fetch_date",
        "pe_ttm", "pe_ann", "pe_forward", "pbv", "ps_ttm",
        "eps_ttm", "bvps", "earnings_yield",
        "pcf_ttm", "pfcf_ttm", "ev_ebit", "ev_ebitda",
        "peg_ratio", "fcf_per_share", "cash_per_share", "revenue_per_share",
        "current_ratio", "quick_ratio",
        "roe", "roa", "market_cap", "der", "npm", "div_yield",
        "rev_growth", "earn_growth", "updated_at",
    ]

    vals = [
        stats.get("ticker"), today,
        stats.get("pe_ttm"), stats.get("pe_ann"), stats.get("pe_forward"),
        stats.get("pbv"), stats.get("ps_ttm"),
        stats.get("eps_ttm"), stats.get("bvps"), stats.get("earnings_yield"),
        stats.get("pcf_ttm"), stats.get("pfcf_ttm"),
        stats.get("ev_ebit"), stats.get("ev_ebitda"),
        stats.get("peg_ratio"), stats.get("fcf_per_share"),
        stats.get("cash_per_share"), stats.get("revenue_per_share"),
        stats.get("current_ratio"), stats.get("quick_ratio"),
        stats.get("roe"), stats.get("roa"),
        stats.get("market_cap"), stats.get("der"),
        stats.get("npm"), stats.get("div_yield"),
        stats.get("rev_growth"), stats.get("earn_growth"),
        now,
    ]

    placeholders = ",".join(["?"] * len(cols))
    col_str = ",".join(cols)
    conn.execute(
        f"INSERT OR REPLACE INTO stockbit_keystats ({col_str}) VALUES ({placeholders})",
        vals,
    )


def _parse_args(args):
    """Parse common CLI args: --token, --cat, and positional ticker list."""
    manual_token = None
    category = None

    if "--token" in args:
        i = args.index("--token")
        manual_token = args[i + 1]
        args = [a for a in args if a != "--token" and a != manual_token]

    if "--cat" in args:
        i = args.index("--cat")
        category = args[i + 1].upper()
        args = [a for a in args if a != "--cat" and a != args[i + 1] if i + 1 < len(args)]
        # clean up properly
        raw = sys.argv[:]
        idx_c = raw.index("--cat") if "--cat" in raw else -1
        args = [a for j, a in enumerate(args) if a != category]

    return args, manual_token, category


def main():
    log("=" * 50)
    log("STOCKBIT KEYSTATS FETCHER")
    log("=" * 50)

    args = sys.argv[1:]
    manual_token = None
    category = None

    if "--token" in args:
        i = args.index("--token")
        manual_token = args[i + 1]
        args = [a for a in args if a != "--token" and a != manual_token]

    if "--cat" in args:
        i = args.index("--cat")
        category = args[i + 1].upper()
        args = args[:i] + args[i + 2:]

    # Explicit tickers override category
    if args:
        tickers = [t.upper() for t in args]
        label = f"{len(tickers)} custom tickers"
    else:
        tickers = get_tickers(category)
        label = category or "IDX80"

    # Get token — auto-refresh/login if invalid
    token = ensure_valid_token(manual_token)
    if not token:
        log("ERROR: Could not obtain a valid token (auto-refresh and credential login both failed).")
        log("Manual option: run with --token <JWT>")
        sys.exit(1)

    conn = init_db()
    log(f"DB: {WALKFORWARD_DB}")
    log(f"Category: {label} — {len(tickers)} tickers\n")

    success = 0
    failed = []

    for i, ticker in enumerate(tickers, 1):
        log(f"[{i}/{len(tickers)}] {ticker}...")
        try:
            stats = fetch_keystats(token, ticker)
            if stats:
                save_keystats(conn, stats)
                conn.commit()
                pe = stats.get("pe_ttm", "?")
                pbv = stats.get("pbv", "?")
                roe = stats.get("roe", "?")
                log(f"  ✓ PE={pe} PBV={pbv} ROE={roe}")
                success += 1
            else:
                log(f"  ✗ No data")
                failed.append(ticker)
        except Exception as e:
            log(f"  ✗ Error: {e}")
            failed.append(ticker)

        time.sleep(RATE_LIMIT_DELAY)

    conn.close()

    log(f"\n{'='*50}")
    log(f"DONE: {success}/{len(tickers)} success")
    if failed:
        log(f"Failed: {', '.join(failed)}")
    log(f"Data saved to: {WALKFORWARD_DB} (table: stockbit_keystats)")



def fetch_flow(token, ticker, date=None):
    """Fetch tradebook chart, return net flow summary.

    If `date` (YYYY-MM-DD) is given, fetch that historical session instead of the
    current one. The trade-book/chart endpoint accepts a `date` param, so a
    missed session (e.g. a fetch outage) can be backfilled with identical schema.
    """
    params = {"symbol": ticker, "time_interval": "1m"}
    if date:
        params["date"] = date
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/",
    }
    # The endpoint throttles after a burst of requests (HTTP 429). Back off and
    # retry so a full backfill/fetch survives the rate-limit wall instead of
    # silently dropping every ticker past the cap.
    r = None
    for attempt in range(4):
        r = requests.get(
            f"{STOCKBIT_BASE}/order-trade/trade-book/chart",
            params=params, headers=headers, timeout=15,
        )
        if r.status_code == 200:
            break
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 0)) or 20 * (attempt + 1)
            log(f"  [429] rate-limited on {ticker}, backoff {wait}s "
                f"(attempt {attempt + 1}/4)")
            time.sleep(wait)
            continue
        return None
    if r is None or r.status_code != 200:
        return None
    d = r.json().get("data", {})
    buys = d.get("buy", [])
    sells = d.get("sell", [])
    net_vals = d.get("net_values", [])
    prices = d.get("prices", [])

    total_buy_lot = sum(int(b["lot"]["raw"]) for b in buys if b.get("lot") and b["lot"].get("raw"))
    total_sell_lot = sum(int(s["lot"]["raw"]) for s in sells if s.get("lot") and s["lot"].get("raw"))
    total_buy_freq = sum(int(b["frequency"]["raw"]) for b in buys if b.get("frequency") and b["frequency"].get("raw"))
    total_sell_freq = sum(int(s["frequency"]["raw"]) for s in sells if s.get("frequency") and s["frequency"].get("raw"))
    total_net_value = sum(int(nv["value"]["raw"]) for nv in net_vals if nv.get("value") and nv["value"].get("raw"))
    last_price = int(prices[-1]["value"]["raw"]) if prices and prices[-1].get("value") else None
    # Use `or` (not dict-default): the live endpoint returns an EMPTY date
    # pre-/post-session, which previously wrote rows with a blank trade_date.
    trade_date = d.get("date") or date or datetime.now().strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "trade_date": trade_date,
        "buy_lot": total_buy_lot,
        "sell_lot": total_sell_lot,
        "net_lot": total_buy_lot - total_sell_lot,
        "buy_freq": total_buy_freq,
        "sell_freq": total_sell_freq,
        "net_value": total_net_value,
        "last_price": last_price,
        "_raw_data": d,
    }


def init_flow_db():
    conn = db_connect(WALKFORWARD_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stockbit_flow (
            ticker TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            buy_lot INTEGER, sell_lot INTEGER, net_lot INTEGER,
            buy_freq INTEGER, sell_freq INTEGER,
            net_value INTEGER,
            last_price INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stockbit_flow_bars (
            ticker TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            bar_time TEXT NOT NULL,
            buy_lot INTEGER,
            sell_lot INTEGER,
            buy_freq INTEGER,
            sell_freq INTEGER,
            net_value INTEGER,
            price INTEGER,
            delta INTEGER,
            PRIMARY KEY (ticker, trade_date, bar_time)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_flow_bars_date ON stockbit_flow_bars(trade_date)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS broker_flow (
            ticker      TEXT NOT NULL,
            trade_date  TEXT NOT NULL,
            broker_code TEXT NOT NULL,
            side        TEXT NOT NULL,
            lot         INTEGER,
            lot_value   INTEGER,
            value       INTEGER,
            value_total INTEGER,
            avg_price   REAL,
            freq        INTEGER,
            investor_type TEXT,
            PRIMARY KEY (ticker, trade_date, broker_code, side)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_broker_flow_date ON broker_flow(trade_date)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bandar_detector (
            ticker              TEXT NOT NULL,
            trade_date          TEXT NOT NULL,
            avg_price           REAL,
            total_buyer         INTEGER,
            total_seller        INTEGER,
            net_broker_count    INTEGER,
            broker_accdist      TEXT,
            value               INTEGER,
            volume              INTEGER,
            top1_accdist        TEXT,
            top3_accdist        TEXT,
            top5_accdist        TEXT,
            top10_accdist       TEXT,
            avg_accdist         TEXT,
            updated_at          TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_cache (
            ticker      TEXT NOT NULL,
            tf          TEXT NOT NULL,
            fetched_at  REAL NOT NULL,
            data        TEXT NOT NULL,
            PRIMARY KEY (ticker, tf)
        )
    """)
    conn.commit()
    return conn


def fetch_broker_flow(token, ticker):
    """Fetch broker net buy/sell summary from marketdetectors endpoint."""
    r = requests.get(
        f"{STOCKBIT_BASE}/marketdetectors/{ticker}",
        params={
            "transaction_type": "TRANSACTION_TYPE_NET",
            "market_board": "MARKET_BOARD_REGULER",
            "investor_type": "INVESTOR_TYPE_ALL",
            "limit": 25,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Origin": "https://stockbit.com",
            "Referer": "https://stockbit.com/",
        },
        timeout=15,
    )
    if r.status_code != 200:
        return None
    d = r.json().get("data", {})
    bs = d.get("broker_summary", {})
    bd = d.get("bandar_detector", {})
    date_str = d.get("to", datetime.now().strftime("%Y%m%d"))
    if len(date_str) == 8:
        trade_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        trade_date = date_str

    rows = []
    for b in bs.get("brokers_buy", []):
        rows.append({
            "ticker": ticker, "trade_date": trade_date,
            "broker_code": b.get("netbs_broker_code", ""),
            "side": "BUY",
            "lot": int(float(b.get("blot", 0))),
            "lot_value": int(float(b.get("blotv", 0))),
            "value": int(float(b.get("bval", 0))),
            "value_total": int(float(b.get("bvalv", 0))),
            "avg_price": float(b.get("netbs_buy_avg_price", 0)),
            "freq": int(b.get("freq", 0)),
            "investor_type": b.get("type", ""),
        })
    for b in bs.get("brokers_sell", []):
        rows.append({
            "ticker": ticker, "trade_date": trade_date,
            "broker_code": b.get("netbs_broker_code", ""),
            "side": "SELL",
            "lot": int(float(b.get("slot", 0))),
            "lot_value": int(float(b.get("slotv", 0))),
            "value": int(float(b.get("sval", 0))),
            "value_total": int(float(b.get("svalv", 0))),
            "avg_price": float(b.get("netbs_sell_avg_price", 0)),
            "freq": int(b.get("freq", 0)),
            "investor_type": b.get("type", ""),
        })

    bandar = {
        "ticker": ticker,
        "trade_date": trade_date,
        "avg_price": bd.get("average"),
        "total_buyer": bd.get("total_buyer"),
        "total_seller": bd.get("total_seller"),
        "net_broker_count": bd.get("number_broker_buysell"),
        "broker_accdist": bd.get("broker_accdist"),
        "value": bd.get("value"),
        "volume": bd.get("volume"),
        "top1_accdist": bd.get("top1", {}).get("accdist"),
        "top3_accdist": bd.get("top3", {}).get("accdist"),
        "top5_accdist": bd.get("top5", {}).get("accdist"),
        "top10_accdist": bd.get("top10", {}).get("accdist"),
        "avg_accdist": bd.get("avg", {}).get("accdist"),
        "updated_at": datetime.now().isoformat(),
    }
    return {"broker_rows": rows, "bandar": bandar, "trade_date": trade_date}


def run_flow(token, tickers, date=None):
    log("=" * 50)
    log("STOCKBIT FLOW FETCHER" + (f" — BACKFILL {date}" if date else ""))
    log("=" * 50)
    conn = init_flow_db()
    log(f"Fetching flow for {len(tickers)} tickers...\n")
    success = 0
    for i, ticker in enumerate(tickers, 1):
        log(f"[{i}/{len(tickers)}] {ticker}...")
        try:
            flow = fetch_flow(token, ticker, date)
            if flow:
                now = datetime.now().isoformat()
                comp_score, verdict, smart_money = None, None, None
                bars = []
                if flow.get("_raw_data"):
                    try:
                        bars = _parse_bars(flow["_raw_data"])
                        analysis = _analyze(flow["ticker"], bars)
                        if analysis:
                            comp_score = analysis.get("score")
                            verdict = analysis.get("verdict")
                            smart_money = analysis.get("smart_money")
                    except Exception as ae:
                        log(f"  [WARN] score compute error: {ae}")
                if bars:
                    try:
                        bar_rows = [
                            (flow["ticker"], flow["trade_date"], b["time"],
                             b["buy_lot"], b["sell_lot"], b["buy_freq"], b["sell_freq"],
                             b["net_value"], b["price"], b["delta"])
                            for b in bars if b.get("time")
                        ]
                        conn.executemany(
                            """INSERT OR REPLACE INTO stockbit_flow_bars
                            (ticker,trade_date,bar_time,buy_lot,sell_lot,buy_freq,sell_freq,
                             net_value,price,delta)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            bar_rows,
                        )
                    except Exception as be:
                        log(f"  [WARN] bars insert error: {be}")
                conn.execute(
                    """INSERT OR REPLACE INTO stockbit_flow
                    (ticker,trade_date,buy_lot,sell_lot,net_lot,buy_freq,sell_freq,
                     net_value,last_price,composite_score,verdict,smart_money,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (flow["ticker"], flow["trade_date"], flow["buy_lot"], flow["sell_lot"],
                     flow["net_lot"], flow["buy_freq"], flow["sell_freq"],
                     flow["net_value"], flow["last_price"],
                     comp_score, verdict, smart_money, now)
                )
                conn.commit()
                nv = flow["net_value"]
                nl = flow["net_lot"]
                sign = "+" if nv >= 0 else ""
                log(f"  ✓ NetLot={nl:+,} NetVal={sign}{nv:,}")
                success += 1

                # Broker flow — only for live (current-session) fetches.
                # marketdetectors has no historical date param, so in backfill
                # mode it would tag today's broker data to a past date. bf=None
                # makes the block below a no-op (it already guards on falsy bf).
                try:
                    bf = fetch_broker_flow(token, ticker) if not date else None
                    # Skip only if data for this trade_date already exists in DB.
                    # This allows saving prior trading days that were missed.
                    _bf_existing = 0
                    if bf and bf.get("broker_rows"):
                        _bf_existing = conn.execute(
                            "SELECT COUNT(*) FROM broker_flow WHERE ticker=? AND trade_date=?",
                            (ticker, bf["trade_date"])
                        ).fetchone()[0]
                    if bf and bf.get("broker_rows") and _bf_existing > 0:
                        log(f"  [SKIP] Broker {bf['trade_date']} already in DB")
                    elif bf and bf.get("broker_rows"):
                        conn.executemany(
                            """INSERT OR REPLACE INTO broker_flow
                            (ticker,trade_date,broker_code,side,lot,lot_value,value,
                             value_total,avg_price,freq,investor_type)
                            VALUES (:ticker,:trade_date,:broker_code,:side,:lot,:lot_value,
                                    :value,:value_total,:avg_price,:freq,:investor_type)""",
                            bf["broker_rows"],
                        )
                        b = bf["bandar"]
                        conn.execute(
                            """INSERT OR REPLACE INTO bandar_detector
                            (ticker,trade_date,avg_price,total_buyer,total_seller,
                             net_broker_count,broker_accdist,value,volume,
                             top1_accdist,top3_accdist,top5_accdist,top10_accdist,
                             avg_accdist,updated_at)
                            VALUES (:ticker,:trade_date,:avg_price,:total_buyer,:total_seller,
                                    :net_broker_count,:broker_accdist,:value,:volume,
                                    :top1_accdist,:top3_accdist,:top5_accdist,:top10_accdist,
                                    :avg_accdist,:updated_at)""",
                            b,
                        )
                        conn.commit()
                        n_buy = sum(1 for r in bf["broker_rows"] if r["side"] == "BUY")
                        n_sell = sum(1 for r in bf["broker_rows"] if r["side"] == "SELL")
                        log(f"  ✓ Broker: {n_buy}B/{n_sell}S | {b['broker_accdist']} | top5={b['top5_accdist']}")
                except Exception as be:
                    log(f"  [WARN] broker flow error: {be}")
            else:
                log(f"  ✗ No data")
        except Exception as e:
            log(f"  ✗ {e}")
        time.sleep(RATE_LIMIT_DELAY)
    conn.close()
    log(f"\nDONE: {success}/{len(tickers)} success")
    if success == len(tickers):
        send_telegram(
            f"✅ <b>Flow & Broker Fetch DONE</b>\n"
            f"Sukses: {success}/{len(tickers)} tickers\n"
            f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        send_telegram(
            f"⚠️ <b>Flow & Broker Fetch SELESAI (ada gagal)</b>\n"
            f"Sukses: {success}/{len(tickers)} tickers\n"
            f"Gagal: {len(tickers) - success} tickers\n"
            f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

def _run_flow_cmd(args):
    """Handle 'flow' subcommand with --token and --cat support."""
    manual_token = None
    category = None

    if "--token" in args:
        i = args.index("--token")
        manual_token = args[i + 1]
        args = args[:i] + args[i + 2:]

    if "--cat" in args:
        i = args.index("--cat")
        category = args[i + 1].upper()
        args = args[:i] + args[i + 2:]

    date = None
    if "--date" in args:
        i = args.index("--date")
        date = args[i + 1]
        args = args[:i] + args[i + 2:]

    if args:
        tickers = [t.upper() for t in args]
    else:
        tickers = get_tickers(category or "ALL")

    # Get token — auto-refresh/login if invalid
    token = ensure_valid_token(manual_token)
    if not token:
        log("ERROR: Could not obtain a valid token")
        send_telegram("❌ <b>Flow Fetch GAGAL</b>\nToken tidak ditemukan/expired. Auto-login juga gagal.")
        sys.exit(1)

    label = category or ("custom" if args else "ALL")
    log(f"Flow category: {label} — {len(tickers)} tickers" + (f" — BACKFILL {date}" if date else ""))
    run_flow(token, tickers, date)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "flow":
        _run_flow_cmd(sys.argv[2:])
    else:
        main()


# ============================================================
# FLOW FETCHER — Fetch tradebook net flow untuk semua ticker
# Usage:
#   python3 stockbit_fetcher.py flow              # ALL tickers
#   python3 stockbit_fetcher.py flow --cat IDX30  # IDX30 only
#   python3 stockbit_fetcher.py flow --cat LQ45   # LQ45 only
#   python3 stockbit_fetcher.py flow --cat IDX80  # IDX80 only
# ============================================================
