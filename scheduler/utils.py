# scheduler/utils.py
import os
import sqlite3
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

from utils.telegram import send_telegram  # noqa: E402
from data.db import connect as db_connect  # noqa: E402
from engine.indicators import IndicatorCache

# get_all_tickers / _load_ohlcv_bulk moved to data/loaders.py in M2 (data-platform
# shared floor, so research/ can load the corpus without importing scheduler).
# Re-exported here for back-compat with existing callers.
from data.loaders import get_all_tickers, _load_ohlcv_bulk  # noqa: E402,F401

def send_suspension_resume_alerts(
    db_path: str = DB_PATH,
    send_fn=None,
    as_of: str = None,
) -> int:
    """Send Telegram alerts for tickers whose suspension resumed on as_of (default: today).
    Only fires for classification='suspension'; skips data_gap events.
    Returns number of alerts sent.
    """
    if send_fn is None:
        send_fn = send_telegram
    if as_of is None:
        from datetime import date as _date
        as_of = _date.today().isoformat()

    try:
        conn = db_connect(db_path)
        rows = conn.execute(
            "SELECT ticker, missing_td, gap_pct FROM suspension_events "
            "WHERE resume_date = ? AND classification = 'suspension'",
            (as_of,),
        ).fetchall()
        conn.close()
    except Exception as e:
        logging.exception("suspension resume alert query failed: %s", e)
        return 0

    for ticker, missing_td, gap_pct in rows:
        gap_pct_str = f"{gap_pct * 100:.1f}%"
        msg = (
            f"🚨 <b>SUSPENSION RESUME: {ticker}</b>\n\n"
            f"Suspended: <b>{missing_td} trading days</b>\n"
            f"Gap: <b>{gap_pct_str}</b>\n"
            f"Resume date: {as_of}\n\n"
            f"⚠️ CAUTION: crash recovery — high risk. Verify volume and direction before entry."
        )
        send_fn(msg)

    return len(rows)


def fetch_latest():
    """Fetch OHLCV terbaru untuk semua ticker (incremental batch)."""
    from data.fetcher import fetch_all_incremental, load_all_tickers
    now_str = datetime.now(WIB).strftime("%H:%M")
    tickers = load_all_tickers()
    print(f"[{now_str}] Incremental fetch {len(tickers)} tickers...")
    try:
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
        try:
            _cache = IndicatorCache()
            for t in tickers:
                _cache.clear(t)
        except Exception as _ce:
            logging.warning("indicator cache clear failed (non-fatal): %s", _ce)
        try:
            from engine.suspension_detector import scan_all as _scan_suspensions
            n_events = _scan_suspensions()
            print(f"[{datetime.now(WIB).strftime('%H:%M')}] Suspension scan: {n_events} events written.")
            n_alerts = send_suspension_resume_alerts()
            if n_alerts:
                print(f"[{datetime.now(WIB).strftime('%H:%M')}] Suspension resume alerts: {n_alerts} sent.")
        except Exception as _scan_e:
            logging.exception("suspension scan failed (non-fatal): %s", _scan_e)
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch error: {e}")
        send_telegram(
            f"🔴 <b>OHLCV Fetch GAGAL</b>\n\n"
            f"<b>{len(tickers)} tickers</b> @ {now_str}\n"
            f"<code>{str(e)[:150]}</code>"
        )

# _load_ohlcv_bulk moved to data/loaders.py in M2 (re-exported above).
