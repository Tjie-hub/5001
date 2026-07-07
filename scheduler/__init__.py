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
    run_ohlcv_reconciliation,
    run_token_health_check,
    run_ohlcv_coverage_check,
    run_foreign_snapshot,
    run_news_fetch,
    run_premover_eod,
    run_backtest_roller,
    run_hourly_risk_bundle,
    run_eod_risk_summary,
    run_market_health_report,
    run_premarket_firm_scan,
    run_eod_trade_plan,
    run_forward_test_cycle,
    run_scheduler_heartbeat,
    run_vpin_daily_batch,
    run_vpin_backfill,
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

    # Phase 2A: market-data schema (is_final / calendar / corporate_actions)
    try:
        from data.market_schema import ensure_market_data_schema
        ensure_market_data_schema(DB_PATH)
    except Exception as _e:
        print(f"[scheduler] market schema init error: {_e}")

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

    # Flow fetch — hourly 09:30–15:15 WIB, plus a post-close fetch at 16:05
    # (IDX closes 16:00; 16:05 captures the final pre-closing/closing-auction flow
    # so the EOD reversal scan at 16:15 sees the *complete* day's smart-money flow).
    for hour, minute in [(9,30),(10,30),(11,30),(12,30),(13,30),(14,30),(15,15),(16,5)]:
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

    # Screener EOD VPIN batch + reversal watchlist — 16:15 WIB
    # Runs AFTER the 16:00 close (and after the 16:05 flow fetch) so the daily
    # close price, full-day order-flow delta, and smart-money flow are all final.
    # Running before the close used a mid-auction close and an incomplete tape,
    # which silently produced an empty/wrong next-day reversal watchlist.
    scheduler.add_job(_run_screener_eod, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=15, timezone=WIB),
        id="screener_eod", name="Screener EOD 16:15")

    # Open trade monitor — hourly at :05 during market hours (09:05–15:05) = 7×/day
    for hour in range(9, 16):
        scheduler.add_job(_run_open_trade_monitor, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=5, timezone=WIB),
            id=f"trade_monitor_{hour:02d}05")

    # News mentions fetch — pre-market 08:00 WIB
    scheduler.add_job(run_news_fetch, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=0, timezone=WIB),
        id="news_fetch_premarket", name="News Mentions Fetch 08:00 (pre-market)")

    # News mentions fetch — 17:00 WIB
    scheduler.add_job(run_news_fetch, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=0, timezone=WIB),
        id="news_fetch", name="News Mentions Fetch 17:00")

    # Broker flow fetch — 20:15 WIB
    scheduler.add_job(run_broker_flow_fetch, CronTrigger(
        day_of_week="mon-fri", hour=20, minute=15, timezone=WIB),
        id="broker_flow_fetch", name="Broker Flow Fetch 20:15")

    # OHLCV reconciliation — 21:00 WIB (after 20:15 broker flow; alert-only)
    scheduler.add_job(run_ohlcv_reconciliation, CronTrigger(
        day_of_week="mon-fri", hour=21, minute=0, timezone=WIB),
        id="ohlcv_reconciliation", name="OHLCV Reconciliation 21:00")

    # Token health — 08:20 (pre-market, before flow jobs) + 12:00 (mid-session).
    # Alerts if the 24h Stockbit JWT is expired/expiring (2026-07-04 silent-death fix).
    for _h, _m in [(8, 20), (12, 0)]:
        scheduler.add_job(run_token_health_check, CronTrigger(
            day_of_week="mon-fri", hour=_h, minute=_m, timezone=WIB),
            id=f"token_health_{_h:02d}{_m:02d}", name=f"Token Health {_h:02d}:{_m:02d}")

    # OHLCV coverage monitor — 17:00 WIB (after EOD scraper/trade-plan settle)
    scheduler.add_job(run_ohlcv_coverage_check, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=0, timezone=WIB),
        id="ohlcv_coverage_check", name="OHLCV Coverage Check 17:00")

    # Pre-mover EOD scan — 16:30 WIB
    scheduler.add_job(run_premover_eod, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=30, timezone=WIB),
        id="premover_eod", name="Pre-mover EOD Scan 16:30")

    # Backtest roller — 1st Sunday of each month at 10:00 WIB
    scheduler.add_job(run_backtest_roller, CronTrigger(
        day="1-7", day_of_week="sun", hour=10, minute=0, timezone=WIB),
        id="backtest_roller", name="Backtest Roller Sun 10:00")

    # VPIN daily batch — 18:00 WIB
    scheduler.add_job(run_vpin_daily_batch, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=0, timezone=WIB),
        id="vpin_daily_batch", name="VPIN Daily Batch 18:00")

    # Pre-market health report — 08:45 WIB
    scheduler.add_job(run_market_health_report, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=45, timezone=WIB),
        id="market_health_report", name="Market Health Report 08:45")

    # Premarket agent-firm shortlist — 08:35 WIB (vets last night's unified watchlist)
    scheduler.add_job(run_premarket_firm_scan, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=35, timezone=WIB),
        id="premarket_firm_scan", name="Premarket Firm Scan 08:35")

    # EOD consolidated trade plan — 16:40 WIB (after screener EOD 16:15 + premover 16:30)
    # Merges all long sources → agent firm → single ranked Telegram message.
    scheduler.add_job(run_eod_trade_plan, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=40, timezone=WIB),
        id="eod_trade_plan", name="EOD Trade Plan 16:40")

    # Forward-test SHADOW cycle — 18:30 WIB (after 16:00 close, 16:05 flow fetch,
    # 18:00 VPIN batch). Ingests today's scheduled_signals into the ft model and
    # runs the open + exit passes so the shadow-position population grows daily.
    scheduler.add_job(run_forward_test_cycle, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=30, timezone=WIB),
        id="forward_test_cycle", name="Forward-Test Cycle 18:30")

    # Dead-man's-switch — stamp a heartbeat every 5 min (audit item 3.7). An
    # external crontab watchdog (scripts/check_scheduler_heartbeat.py) alarms if
    # this goes stale, catching a dead scheduler/process that would otherwise
    # silently stop trading.
    scheduler.add_job(run_scheduler_heartbeat, CronTrigger(
        minute="*/5", timezone=WIB), id="scheduler_heartbeat",
        name="Scheduler Heartbeat", replace_existing=True)

    scheduler.start()
    print("Scheduler started:")
    print("  💓 SCHEDULER HEARTBEAT: every 5 min (dead-man's-switch)")
    # Edge Registry (M1 inversion): load once, announce what production runs on.
    from engine.registry_loader import announce_registry
    announce_registry()
    print("  📊 SIGNAL REPORT: 16:00")
    print("  📰 NEWS FETCH: 08:00 pre-market, 17:00 EOD")
    print("  🏛️ BROKER FLOW: 20:15 (after Stockbit EOD publish)")
    print("  🔍 PRE-MOVER EOD: 16:30 (setup watchlist scan)")
    print("  🔄 BACKTEST ROLLER: 1st Sun/month 10:00")
    print("  🏥 MARKET HEALTH: 08:45 pre-market")
    print("  🌅 PREMARKET FIRM: 08:35 pre-market (unified watchlist → agent firm)")
    print("  📋 EOD TRADE PLAN: 16:40 (all long sources → agent firm → 1 ranked msg)")
    print("  🧪 FORWARD-TEST CYCLE: 18:30 (ingest signals → open/exit shadow positions)")
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
