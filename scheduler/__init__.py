# scheduler/__init__.py
import os
import sqlite3
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Re-export send_telegram so callers doing `from scheduler import send_telegram` keep working
from utils.telegram import send_telegram  # noqa: F401

# Re-export utils
from scheduler.utils import (  # noqa: F401
    get_all_tickers,
    fetch_latest,
    _load_ohlcv_bulk,
    send_suspension_resume_alerts,
)

# Re-export scanner
from scheduler.scanner import (  # noqa: F401
    calc_votes,
    check_fundamental,
    _detect_price_shock,
    _load_stockbit_token,
    check_keystats_freshness,
    scan_momentum_signals,
    daily_signal_scan,
    scheduled_multi_strategy_scan,
    get_ticker_best_strategies,
)

# Re-export jobs
from scheduler.jobs import (  # noqa: F401
    refresh_wf_scores,
    run_flow_fetch,
    run_broker_flow_fetch,
    run_foreign_snapshot,
    run_news_fetch,
    run_premover_eod,
    run_backtest_roller,
    run_hourly_risk_bundle,
    run_eod_risk_summary,
    run_market_health_report,
    _refresh_backtest_cache,
    _run_open_trade_monitor,
    _run_screener_intraday,
    _run_screener_eod,
)

# Re-export reports
from scheduler.reports import (  # noqa: F401
    daily_fetch_report,
    open_trades_status_report,
    flow_broker_report,
    auto_trade_status_report,
)


def start_scheduler():
    # Ensure regime_watchlist table exists (safe to run every start)
    try:
        import sqlite3 as _sql
        from engine.watchlist import ensure_table as _ensure_watchlist
        _wl_conn = _sql.connect(DB_PATH)
        _ensure_watchlist(_wl_conn)
        _wl_conn.close()
    except Exception as _e:
        print(f"[scheduler] watchlist table init error: {_e}")

    scheduler = BackgroundScheduler(timezone=WIB)

    # Daily signal scan — Mon-Fri 16:00 WIB (market close, always send even if no signals)
    scheduler.add_job(daily_signal_scan, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=0, timezone=WIB
    ), id="daily_scan", name="Signal Report 16:00")

    # WF score refresh — Fri 16:00 WIB
    scheduler.add_job(refresh_wf_scores, CronTrigger(
        day_of_week="fri", hour=16, minute=0, timezone=WIB))

    # Backtest cache pre-compute — daily at 08:30 WIB (before market open)
    scheduler.add_job(_refresh_backtest_cache, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=30, timezone=WIB),
        id="backtest_cache_refresh", name="Backtest Cache 08:30")

    # Flow fetch — hourly 09:30–15:15 WIB
    for hour, minute in [(9,30),(10,30),(11,30),(12,30),(13,30),(14,30),(15,15)]:
        scheduler.add_job(run_flow_fetch, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=minute, timezone=WIB),
            id=f"flow_fetch_{hour:02d}{minute:02d}")

    # Multi-strategy scanner — 5x per day
    scan_times = [(9,5,"post-open"),(10,5,"mid-morning"),(11,5,"pre-lunch"),(13,35,"post-lunch"),(14,35,"near-close")]
    for hour, minute, label in scan_times:
        scheduler.add_job(scheduled_multi_strategy_scan, CronTrigger(
            hour=hour, minute=minute, timezone=WIB, day_of_week="mon-fri"),
            id=f"multi_strategy_scan_{hour:02d}{minute:02d}", name=f"Multi-Strategy Scan {label}")
        print(f"  ✓ Multi-strategy scan @ {hour:02d}:{minute:02d} ({label})")

    # Screener intraday — registered at the same times as multi-strategy scan so they run in parallel
    for hour, minute, label in scan_times:
        scheduler.add_job(_run_screener_intraday, CronTrigger(
            hour=hour, minute=minute,
            timezone=WIB, day_of_week="mon-fri"),
            id=f"screener_intraday_{hour:02d}{minute:02d}", name=f"Screener Intraday {label}")

    # Screener EOD VPIN batch — 15:30 WIB
    scheduler.add_job(_run_screener_eod, CronTrigger(
        day_of_week="mon-fri", hour=15, minute=30, timezone=WIB),
        id="screener_eod", name="Screener EOD 15:30")

    # Daily fetch report — 17:30 WIB
    scheduler.add_job(daily_fetch_report, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=30, timezone=WIB),
        id="daily_fetch_report", name="Daily Fetch Report 17:30")

    # Open trades status report — 4x per day: 10:30, 12:30, 14:30, 16:30
    for hour, minute in [(10, 30), (12, 30), (14, 30), (16, 30)]:
        scheduler.add_job(open_trades_status_report, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=minute, timezone=WIB),
            id=f"open_trades_report_{hour:02d}{minute:02d}", name=f"Open Trades Report {hour:02d}:{minute:02d}")

    # Foreign accumulation snapshot — 14:30 WIB (pre-close watchlist)
    scheduler.add_job(run_foreign_snapshot, CronTrigger(
        day_of_week="mon-fri", hour=14, minute=30, timezone=WIB),
        id="foreign_snapshot", name="Foreign Snapshot 14:30")

    # Open trade monitor — hourly at :05 during market hours (09:05–15:05) = 7×/day
    for hour in range(9, 16):
        scheduler.add_job(_run_open_trade_monitor, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=5, timezone=WIB),
            id=f"trade_monitor_{hour:02d}05")

    # Auto-trading status — 09:00 WIB (morning check)
    scheduler.add_job(auto_trade_status_report, CronTrigger(
        day_of_week="mon-fri", hour=9, minute=0, timezone=WIB),
        id="auto_trade_status", name="Auto-Trade Status 09:00")

    # News mentions fetch — 17:00 WIB (before flow report at 17:15)
    scheduler.add_job(run_news_fetch, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=0, timezone=WIB),
        id="news_fetch", name="News Mentions Fetch 17:00")

    # Flow & Broker report — 17:15 WIB (after 17:00 fetch)
    scheduler.add_job(flow_broker_report, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=15, timezone=WIB),
        id="flow_broker_report", name="Flow & Broker Report 17:15")

    # Broker flow fetch — 20:15 WIB (Stockbit publish summary setelah ~20:00 WIB)
    scheduler.add_job(run_broker_flow_fetch, CronTrigger(
        day_of_week="mon-fri", hour=20, minute=15, timezone=WIB),
        id="broker_flow_fetch", name="Broker Flow Fetch 20:15")

    # Pre-mover EOD scan — 16:30 WIB (after data fetch + signal scan at 16:00)
    scheduler.add_job(run_premover_eod, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=30, timezone=WIB),
        id="premover_eod", name="Pre-mover EOD Scan 16:30")

    # Backtest roller — 1st Sunday of each month at 10:00 WIB
    scheduler.add_job(run_backtest_roller, CronTrigger(
        day="1-7", day_of_week="sun", hour=10, minute=0, timezone=WIB),
        id="backtest_roller", name="Backtest Roller Sun 10:00")

    # Daily market health report — 08:45 WIB (pre-market)
    scheduler.add_job(run_market_health_report, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=45, timezone=WIB),
        id="market_health_report", name="Market Health Report 08:45")

    # Market risk alert routing — hourly RED bundle at :30, EOD summary at 16:00
    scheduler.add_job(run_hourly_risk_bundle, CronTrigger(
        day_of_week="mon-fri", minute=30, timezone=WIB),
        id="risk_bundle_hourly", name="Risk Bundle Hourly :30")
    scheduler.add_job(run_eod_risk_summary, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=0, timezone=WIB),
        id="risk_eod_summary", name="Risk EOD Summary 16:00")

    scheduler.start()
    print("Scheduler started:")
    print("  🤖 AUTO-TRADING STATUS: 09:00 (success/failed check)")
    print("  📊 SIGNAL REPORT: 16:00 (even if no signals)")
    print("  📰 NEWS FETCH: 17:00 (Google News RSS, all tickers)")
    print("  📈 FLOW & BROKER: 17:15 (after 17:00 fetch, with news-spike tags)")
    print("  🏦 OPEN TRADES: 10:30, 12:30, 14:30, 16:30")
    print("  🏛️ FOREIGN SNAPSHOT: 14:30 (pre-close foreign accumulation watchlist)")
    print("  🔄 DAILY FETCH: 17:30")
    print("  🏛️ BROKER FLOW: 20:15 (after Stockbit EOD publish)")
    print("  🔍 PRE-MOVER EOD: 16:30 (setup watchlist scan)")
    print("  🔄 BACKTEST ROLLER: 1st Sun/month 10:00 (rolling WF windows)")
    return scheduler


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        print("Running daily_signal_scan once...")
        daily_signal_scan()
    else:
        sched = start_scheduler()
        import time
        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            sched.shutdown()
            print("Scheduler stopped.")
