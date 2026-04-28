"""
News Filter — Daily news mentions per ticker via Google News RSS.
================================================================
Builds an attention baseline; spike = today_count >= 3x trailing-30d average
(with a small floor so tickers with quiet baselines don't trip on a single
headline).

Library usage:
    from news_filter import has_news_spike, get_spiking_tickers, run_news_batch

CLI usage:
    python3 news_filter.py                 # batch all tickers, save to DB
    python3 news_filter.py BBCA BRPT       # quick test for specific tickers, no DB write
"""

import os
import sys
import time
import json
import sqlite3
import logging
import feedparser
from datetime import datetime, date, timedelta
from urllib.parse import quote_plus

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "walkforward.db")

# Indonesian locale + " saham" qualifier reduces off-topic hits (e.g. ASII as a name match)
_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"

# Some publishers block the default feedparser UA
feedparser.USER_AGENT = "Mozilla/5.0 (compatible; idx-walkforward/1.0)"

SPIKE_MULTIPLIER = 3.0  # today_count >= MULTIPLIER × avg_30d
SPIKE_FLOOR = 3         # today_count must also clear this absolute floor


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_mentions (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER NOT NULL,
            headlines_json TEXT,
            updated_at TEXT,
            PRIMARY KEY (ticker, date)
        )
    """)


def _load_tickers():
    try:
        from data.fetcher import load_all_tickers
        return load_all_tickers() or []
    except Exception:
        return []


def fetch_news_for_ticker(ticker, today=None):
    """Fetch Google News RSS for `<ticker> saham` and return (count, headlines).

    `count` and `headlines` only include entries published on `today` (local date).
    """
    if today is None:
        today = date.today()
    query = quote_plus(f"{ticker} saham")
    url = _RSS_URL.format(query=query)
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logging.warning(f"[news] {ticker} RSS parse error: {e}")
        return 0, []

    headlines = []
    for entry in feed.entries:
        pub = getattr(entry, "published_parsed", None)
        if not pub:
            continue
        pub_date = date(pub.tm_year, pub.tm_mon, pub.tm_mday)
        if pub_date == today:
            title = entry.get("title", "")
            if title:
                headlines.append(title)
    return len(headlines), headlines


def save_news_count(ticker, count, headlines, trade_date=None, conn=None):
    if trade_date is None:
        trade_date = str(date.today())
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        conn.execute("""
            INSERT OR REPLACE INTO news_mentions
            (ticker, date, count, headlines_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            ticker, trade_date, count,
            json.dumps(headlines[:20], ensure_ascii=False),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def get_30d_avg(ticker, conn=None):
    """Average news count over the trailing 30 days, excluding today."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        today_str = str(date.today())
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        row = conn.execute("""
            SELECT AVG(count) FROM news_mentions
            WHERE ticker = ? AND date >= ? AND date < ?
        """, (ticker, cutoff, today_str)).fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0
    finally:
        if own_conn:
            conn.close()


def has_news_spike(ticker, today_count=None, conn=None):
    """Returns spike-info dict, or None if no news data for today.

    Result keys: ticker, today_count, avg_30d, is_spike, ratio.
    """
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        today_str = str(date.today())
        if today_count is None:
            row = conn.execute(
                "SELECT count FROM news_mentions WHERE ticker=? AND date=?",
                (ticker, today_str)
            ).fetchone()
            if not row:
                return None
            today_count = row[0]
        avg_30d = get_30d_avg(ticker, conn)
        is_spike = (
            today_count >= SPIKE_FLOOR
            and avg_30d > 0
            and today_count >= SPIKE_MULTIPLIER * avg_30d
        )
        ratio = round(today_count / max(avg_30d, 0.5), 2)
        return {
            "ticker": ticker,
            "today_count": today_count,
            "avg_30d": round(avg_30d, 2),
            "is_spike": is_spike,
            "ratio": ratio,
        }
    finally:
        if own_conn:
            conn.close()


def get_today_headlines(ticker, conn=None):
    """Return today's saved headlines list for a ticker, or []."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        today_str = str(date.today())
        row = conn.execute(
            "SELECT headlines_json FROM news_mentions WHERE ticker=? AND date=?",
            (ticker, today_str)
        ).fetchone()
        if not row or not row[0]:
            return []
        try:
            return json.loads(row[0])
        except Exception:
            return []
    finally:
        if own_conn:
            conn.close()


def get_spiking_tickers(conn=None):
    """Return spike-info dicts for every ticker with a news spike today, sorted by ratio desc."""
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        today_str = str(date.today())
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM news_mentions WHERE date=?",
            (today_str,)
        ).fetchall()
        out = []
        for (t,) in rows:
            sp = has_news_spike(t, conn=conn)
            if sp and sp["is_spike"]:
                out.append(sp)
        out.sort(key=lambda x: x["ratio"], reverse=True)
        return out
    finally:
        if own_conn:
            conn.close()


def run_news_batch(tickers=None, delay=1.0):
    """Fetch news for all tickers, persist counts. Returns rows-saved count."""
    if tickers is None:
        tickers = _load_tickers()
    if not tickers:
        print("[News] No tickers to fetch")
        return 0
    conn = sqlite3.connect(_DB_PATH)
    _ensure_table(conn)
    today_str = str(date.today())
    today_obj = date.today()
    saved = 0
    for i, ticker in enumerate(tickers, 1):
        try:
            count, headlines = fetch_news_for_ticker(ticker, today=today_obj)
            save_news_count(ticker, count, headlines, trade_date=today_str, conn=conn)
            saved += 1
            if i % 20 == 0:
                conn.commit()
                sys.stdout.write(f"\r  [{i}/{len(tickers)}] {ticker} ({count} hits)      ")
                sys.stdout.flush()
        except Exception as e:
            logging.warning(f"[news] {ticker} error: {e}")
        time.sleep(delay)
    conn.commit()
    conn.close()
    print(f"\n[News] {saved}/{len(tickers)} tickers saved for {today_str}")
    return saved


def main():
    args = sys.argv[1:]
    if args:
        tickers = [a.upper() for a in args]
        print(f"Fetching news for {len(tickers)} tickers (read-only test, no DB write)...")
        for t in tickers:
            count, headlines = fetch_news_for_ticker(t)
            print(f"\n{t}: {count} headlines today")
            for h in headlines[:5]:
                print(f"  - {h[:100]}")
            time.sleep(1.0)
    else:
        run_news_batch()


if __name__ == "__main__":
    main()
