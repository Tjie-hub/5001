# scheduler/__init__.py
import os
import sqlite3
import time as _time
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR
import pytz
import logging


WIB = pytz.timezone("Asia/Jakarta")
logger = logging.getLogger(__name__)

# The live BackgroundScheduler instance, reachable from outside start_scheduler()
# -- every caller (app.py's __main__ block, gunicorn.conf.py's post_worker_init
# hook) discards start_scheduler()'s return value, so this is the only handle a
# request (e.g. GET /api/v1/scheduler) has to it. None before start_scheduler()
# has run in this process.
_scheduler_instance = None


def get_scheduler():
    """The live BackgroundScheduler set by start_scheduler(), or None if it
    hasn't run yet in this process."""
    return _scheduler_instance
from config import DB_PATH as _DEFAULT_DB_PATH  # single path authority (audit, Phase 5)
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB_PATH)
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Re-export send_telegram so callers doing `from scheduler import send_telegram` keep working
from utils.telegram import send_telegram  # noqa: F401
from utils.logging_config import redact_and_truncate  # noqa: F401

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
    run_flow_fetch,
    run_broker_flow_fetch,
    run_broker_period_summary_fetch,
    run_corporate_actions_fetch,
    run_insider_fetch,
    run_ownership_fetch,
    run_stockbit_screener_fetch,
    run_ohlcv_reconciliation,
    run_token_health_check,
    run_token_live_probe,
    run_ohlcv_coverage_check,
    run_foreign_snapshot,
    run_news_fetch,
    run_premover_eod,
    run_hourly_risk_bundle,
    run_eod_risk_summary,
    run_market_health_report,
    run_premarket_firm_scan,
    run_eod_trade_plan,
    run_forward_test_cycle,
    run_scheduler_heartbeat,
    run_phase5_bull_watch,
    run_vpin_daily_batch,
    run_vpin_backfill,
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
from engine.job_status import wrap_scheduled


# Cooldown between repeated Telegram alerts for the SAME job_id (RC1 fix R-2,
# 2026-07-28 — scheduler/ is one of the documented exceptions allowed its own
# os.getenv(), per CLAUDE.md). Default 1h: long enough that a job stuck failing
# every 5 min (the shortest cron interval in this file) doesn't spam Telegram,
# short enough that a real, still-unresolved outage gets re-surfaced same-shift.
JOB_ERROR_ALERT_COOLDOWN_S = float(os.getenv("SCHEDULER_JOB_ERROR_COOLDOWN_S", "3600"))


def format_job_error_alert(job_id: str, job_name: Optional[str], exception: BaseException,
                           suppressed: int = 0) -> str:
    """Telegram text for an uncaught APScheduler job exception (audit 2026-07-28).

    Closes a silent-failure gap: the dead-man's-switch heartbeat only proves the
    scheduler *process* is alive, not that any individual job succeeded — several
    jobs (e.g. run_ohlcv_reconciliation, run_phase5_bull_watch) only logged a
    warning on exception with no alert at all. Pure formatter so it's testable
    without a live BackgroundScheduler.

    suppressed: count of further failures of this same job_id that were
    rate-limited (not alerted) since the last alert — surfaced here so a
    quieted repeat failure doesn't look identical to the first occurrence.
    """
    name = job_name or job_id
    tail = (f"\n<i>(+{suppressed} more failure{'s' if suppressed != 1 else ''} "
           f"suppressed since last alert)</i>" if suppressed else "")
    return (f"🔴 <b>Scheduler Job Failed</b>\n\n"
            f"<b>{name}</b> (<code>{job_id}</code>)\n"
            f"<code>{redact_and_truncate(str(exception), 300)}</code>{tail}")


class JobErrorRateLimiter:
    """Per-job_id cooldown gate for EVENT_JOB_ERROR alerts (RC1 fix R-2).

    Bounded memory: one (last_alert_time, suppressed_count) pair per distinct
    job_id ever seen — at most ~20 entries for this scheduler, never grows per
    event. Deterministic: the clock is injectable so tests never depend on
    real wall-clock timing. The first failure for a given job_id always
    alerts (nothing to suppress against yet); a repeat failure within
    `cooldown_s` of the last alert is counted but not sent; the next alert
    after cooldown expiry reports how many were suppressed in between.
    """

    def __init__(self, cooldown_s: float = None, clock=_time.monotonic):
        self.cooldown_s = JOB_ERROR_ALERT_COOLDOWN_S if cooldown_s is None else cooldown_s
        self._clock = clock
        self._last_alert: dict[str, float] = {}
        self._suppressed: dict[str, int] = {}

    def should_alert(self, job_id: str) -> tuple[bool, int]:
        """Call exactly once per error event. Returns (should_alert, suppressed_count).
        When True, the suppressed counter for job_id is consumed (returned) and reset."""
        now = self._clock()
        last = self._last_alert.get(job_id)
        if last is not None and (now - last) < self.cooldown_s:
            self._suppressed[job_id] = self._suppressed.get(job_id, 0) + 1
            return False, 0
        suppressed = self._suppressed.pop(job_id, 0)
        self._last_alert[job_id] = now
        return True, suppressed


def _add_job(scheduler, func, trigger, **kwargs):
    """Registers func on scheduler, wrapped so every execution is recorded in
    the Production Status Registry (engine.job_status). job_name is the
    APScheduler job id (kwargs['id']) — unique per registered cron slot, so a
    function registered multiple times at different times of day (e.g.
    run_flow_fetch) gets one row per slot, not one shared row per function.

    P1-1: every one of start_scheduler()'s ~20 registrations funnels through
    this single function, so isolating failures here (rather than at each of
    the ~20 call sites) protects all of them at once. Before this, a bad
    registration (malformed trigger, duplicate id, etc.) raised straight out
    of start_scheduler(), aborting the whole worker boot -- every job after
    the failing one in registration order silently never got registered, and
    the process either crash-looped or came up with an unknown-incomplete
    job set. Now a bad registration is logged loudly, alerted, and skipped;
    every other job still registers.
    """
    job_id = kwargs.get("id") or getattr(func, "__name__", "unnamed_job")
    try:
        scheduler.add_job(wrap_scheduled(func, job_id), trigger, **kwargs)
    except Exception:
        logger.exception(
            f"[scheduler] failed to register job {job_id!r} -- it will NOT "
            f"run until this is fixed and the service is restarted. "
            f"Continuing to register remaining jobs."
        )
        try:
            send_telegram(
                f"🔴 Scheduler failed to register job '{job_id}' at "
                f"startup -- it will NOT run until fixed + restarted. "
                f"Other jobs registered normally. See logs."
            )
        except Exception:
            pass


def _make_job_error_listener(scheduler, rate_limiter: "JobErrorRateLimiter" = None):
    """Bind a job-error listener to `scheduler` for EVENT_JOB_ERROR registration.

    rate_limiter: injectable for tests; production gets one limiter per
    scheduler instance (its lifetime matches the worker process, so cooldown
    state persists for as long as the scheduler runs — exactly the intent).
    """
    limiter = rate_limiter if rate_limiter is not None else JobErrorRateLimiter()

    def _on_job_error(event):
        try:
            job = scheduler.get_job(event.job_id)
            name = job.name if job else None
        except Exception:
            name = None
        should_alert, suppressed = limiter.should_alert(event.job_id)
        if not should_alert:
            logger.warning(f"[scheduler] job {event.job_id} failed (alert on cooldown): "
                          f"{event.exception}")
            return
        try:
            send_telegram(format_job_error_alert(event.job_id, name, event.exception, suppressed))
        except Exception as e:
            logger.warning(f"[scheduler] job-error alert failed: {e}")
    return _on_job_error


def start_scheduler():
    # Ensure regime_watchlist table exists (safe to run every start)
    try:
        import sqlite3 as _sql
        from engine.watchlist import ensure_table as _ensure_watchlist
        _wl_conn = _sql.connect(DB_PATH)
        _ensure_watchlist(_wl_conn)
        _wl_conn.close()
    except Exception as _e:
        logger.warning(f"[scheduler] watchlist table init error: {_e}")

    # Phase 2A: market-data schema (is_final / calendar / corporate_actions)
    try:
        from data.market_schema import ensure_market_data_schema
        ensure_market_data_schema(DB_PATH)
    except Exception as _e:
        logger.warning(f"[scheduler] market schema init error: {_e}")

    scheduler = BackgroundScheduler(timezone=WIB)

    # Daily signal scan — Mon-Fri 16:00 WIB (market close, always send even if no signals)
    _add_job(scheduler, daily_signal_scan, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=0, timezone=WIB
    ), id="daily_scan", name="Signal Report 16:00")

    # WF score refresh / backtest cache / roller moved OFF the production
    # scheduler in M3 (spec §10-M3) — run via `python -m research.cli`.

    # Flow fetch — hourly 09:30–15:15 WIB, plus a post-close fetch at 16:05
    # (IDX closes 16:00; 16:05 captures the final pre-closing/closing-auction flow
    # so the EOD reversal scan at 16:15 sees the *complete* day's smart-money flow).
    for hour, minute in [(9,30),(10,30),(11,30),(12,30),(13,30),(14,30),(15,15),(16,5)]:
        _add_job(scheduler, run_flow_fetch, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=minute, timezone=WIB),
            id=f"flow_fetch_{hour:02d}{minute:02d}")

    # Multi-strategy scanner — 5x per day
    scan_times = [(9,5,"post-open"),(10,5,"mid-morning"),(11,5,"pre-lunch"),(13,35,"post-lunch"),(14,35,"near-close")]
    for hour, minute, label in scan_times:
        _add_job(scheduler, scheduled_multi_strategy_scan, CronTrigger(
            hour=hour, minute=minute, timezone=WIB, day_of_week="mon-fri"),
            id=f"multi_strategy_scan_{hour:02d}{minute:02d}", name=f"Multi-Strategy Scan {label}")
        logger.info(f"  ✓ Multi-strategy scan @ {hour:02d}:{minute:02d} ({label})")

    # Screener intraday — registered at the same times as multi-strategy scan so they run in parallel
    for hour, minute, label in scan_times:
        _add_job(scheduler, _run_screener_intraday, CronTrigger(
            hour=hour, minute=minute,
            timezone=WIB, day_of_week="mon-fri"),
            id=f"screener_intraday_{hour:02d}{minute:02d}", name=f"Screener Intraday {label}")

    # Screener EOD VPIN batch + reversal watchlist — 16:15 WIB
    # Runs AFTER the 16:00 close (and after the 16:05 flow fetch) so the daily
    # close price, full-day order-flow delta, and smart-money flow are all final.
    # Running before the close used a mid-auction close and an incomplete tape,
    # which silently produced an empty/wrong next-day reversal watchlist.
    _add_job(scheduler, _run_screener_eod, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=15, timezone=WIB),
        id="screener_eod", name="Screener EOD 16:15")

    # Open trade monitor — hourly at :05 during market hours (09:05–15:05) = 7×/day
    for hour in range(9, 16):
        _add_job(scheduler, _run_open_trade_monitor, CronTrigger(
            day_of_week="mon-fri", hour=hour, minute=5, timezone=WIB),
            id=f"trade_monitor_{hour:02d}05")

    # News mentions fetch — pre-market 08:00 WIB
    _add_job(scheduler, run_news_fetch, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=0, timezone=WIB),
        id="news_fetch_premarket", name="News Mentions Fetch 08:00 (pre-market)")

    # News mentions fetch — 17:00 WIB
    _add_job(scheduler, run_news_fetch, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=0, timezone=WIB),
        id="news_fetch", name="News Mentions Fetch 17:00")

    # Broker flow fetch — 20:15 WIB
    _add_job(scheduler, run_broker_flow_fetch, CronTrigger(
        day_of_week="mon-fri", hour=20, minute=15, timezone=WIB),
        id="broker_flow_fetch", name="Broker Flow Fetch 20:15")

    # Corporate actions (dividend/rups/stocksplit/bonus/warrant/rightissue)
    # — daily, 20:20 WIB, after the daily broker flow fetch (20:15). Daily,
    # unlike the period-summary job below: corp actions are discrete,
    # sporadically-announced catalysts (a new rights issue announcement is
    # only useful caught promptly), not a slow-moving rolling aggregate —
    # see run_corporate_actions_fetch()'s own docstring.
    _add_job(scheduler, run_corporate_actions_fetch, CronTrigger(
        day_of_week="mon-fri", hour=20, minute=20, timezone=WIB),
        id="corporate_actions_fetch", name="Corporate Actions Fetch 20:20")

    # Insider transactions (director/commissioner/major-holder BUY/SELL) —
    # daily, 20:25 WIB, after corporate actions (20:20). Same discrete-event
    # reasoning as corporate_actions_fetch above: insider disclosures are
    # sporadic and only useful caught close to when Stockbit publishes them,
    # not a slow-moving rolling aggregate — see run_insider_fetch()'s own
    # docstring.
    _add_job(scheduler, run_insider_fetch, CronTrigger(
        day_of_week="mon-fri", hour=20, minute=25, timezone=WIB),
        id="insider_fetch", name="Insider Transactions Fetch 20:25")

    # Ownership composition (named major holders + investor-type buckets) —
    # monthly, day 5 at 09:00 WIB. Monthly, not daily/weekly: live-testing
    # found every ticker reporting the identical report_date (last day of
    # the prior month) with no history behind it — a market-wide monthly
    # registry publication, not a continuously-updated feed. Day 5 (not day
    # 1) gives Stockbit a few days to ingest the new month-end registry
    # before this job runs — see run_ownership_fetch()'s own docstring.
    _add_job(scheduler, run_ownership_fetch, CronTrigger(
        day="5", hour=9, minute=0, timezone=WIB),
        id="ownership_fetch", name="Ownership Composition Fetch (monthly, day 5)")

    # Broker period summary (LAST_7_DAYS/LAST_1_MONTH/LAST_3_MONTHS) — weekly,
    # Friday 20:30 WIB, after the daily broker flow fetch (20:15). Weekly, not
    # daily: a rolling accumulation window only shifts by one trading day at a
    # time, so a daily refetch across the whole universe would be mostly
    # duplicate work — see run_broker_period_summary_fetch()'s own docstring.
    _add_job(scheduler, run_broker_period_summary_fetch, CronTrigger(
        day_of_week="fri", hour=20, minute=30, timezone=WIB),
        id="broker_period_summary_fetch", name="Broker Period Summary Fetch 20:30 (Fri)")

    # OHLCV reconciliation — 21:00 WIB (after 20:15 broker flow; alert-only)
    _add_job(scheduler, run_ohlcv_reconciliation, CronTrigger(
        day_of_week="mon-fri", hour=21, minute=0, timezone=WIB),
        id="ohlcv_reconciliation", name="OHLCV Reconciliation 21:00")

    # Token health — 08:20 (pre-market, before flow jobs) + 12:00 (mid-session).
    # Alerts if the 24h Stockbit JWT is expired/expiring (2026-07-04 silent-death fix).
    for _h, _m in [(8, 20), (12, 0)]:
        _add_job(scheduler, run_token_health_check, CronTrigger(
            day_of_week="mon-fri", hour=_h, minute=_m, timezone=WIB),
            id=f"token_health_{_h:02d}{_m:02d}", name=f"Token Health {_h:02d}:{_m:02d}")

    # Live token probe — 16:10 WIB, 5 min before the 16:15 EOD finalisation. The exp-based
    # health check above cannot see a server-side revocation (2026-09-21/22: "OK, 21.2h left",
    # then 401 on all 958 tickers at 16:15); this one calls the API and refreshes on 401/403.
    _add_job(scheduler, run_token_live_probe, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=10, timezone=WIB),
        id="token_live_probe_1610", name="Token Live Probe 16:10")

    # OHLCV coverage monitor — 17:00 WIB (after EOD scraper/trade-plan settle)
    _add_job(scheduler, run_ohlcv_coverage_check, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=0, timezone=WIB),
        id="ohlcv_coverage_check", name="OHLCV Coverage Check 17:00")

    # Stockbit guru-template screener fetch — 17:05 WIB (after the 17:00 OHLCV
    # coverage check, once the day's price action has settled). Schedules the
    # existing on-demand collector (screener/stockbit_screener.py) so guru
    # template snapshots (incl. Big Money %) accumulate a daily history
    # instead of only existing on-demand via the /api/screener route.
    _add_job(scheduler, run_stockbit_screener_fetch, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=5, timezone=WIB),
        id="stockbit_screener_fetch", name="Stockbit Screener Fetch 17:05")

    # Pre-mover EOD scan — 16:30 WIB
    _add_job(scheduler, run_premover_eod, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=30, timezone=WIB),
        id="premover_eod", name="Pre-mover EOD Scan 16:30")

    # VPIN daily batch — 18:00 WIB
    _add_job(scheduler, run_vpin_daily_batch, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=0, timezone=WIB),
        id="vpin_daily_batch", name="VPIN Daily Batch 18:00")

    # Pre-market health report — 08:45 WIB
    _add_job(scheduler, run_market_health_report, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=45, timezone=WIB),
        id="market_health_report", name="Market Health Report 08:45")

    # Premarket agent-firm shortlist — 08:35 WIB (vets last night's unified watchlist)
    _add_job(scheduler, run_premarket_firm_scan, CronTrigger(
        day_of_week="mon-fri", hour=8, minute=35, timezone=WIB),
        id="premarket_firm_scan", name="Premarket Firm Scan 08:35")

    # EOD consolidated trade plan — 16:40 WIB (after screener EOD 16:15 + premover 16:30)
    # Merges all long sources → agent firm → single ranked Telegram message.
    _add_job(scheduler, run_eod_trade_plan, CronTrigger(
        day_of_week="mon-fri", hour=16, minute=40, timezone=WIB),
        id="eod_trade_plan", name="EOD Trade Plan 16:40")

    # Forward-test SHADOW cycle — 18:30 WIB (after 16:00 close, 16:05 flow fetch,
    # 18:00 VPIN batch). Ingests today's scheduled_signals into the ft model and
    # runs the open + exit passes so the shadow-position population grows daily.
    _add_job(scheduler, run_forward_test_cycle, CronTrigger(
        day_of_week="mon-fri", hour=18, minute=30, timezone=WIB),
        id="forward_test_cycle", name="Forward-Test Cycle 18:30")

    # Phase 5 (spec 2026-07-08) — daily BULL-watch on the NR7 governed universe;
    # alerts only on band transitions, so the moment NR7 becomes eligible is loud.
    _add_job(scheduler, run_phase5_bull_watch, CronTrigger(
        day_of_week="mon-fri", hour=17, minute=10, timezone=WIB),
        id="phase5_bull_watch", name="Phase 5 BULL-watch 17:10",
        replace_existing=True)

    # Dead-man's-switch — stamp a heartbeat every 5 min (audit item 3.7). An
    # external crontab watchdog (scripts/check_scheduler_heartbeat.py) alarms if
    # this goes stale, catching a dead scheduler/process that would otherwise
    # silently stop trading.
    _add_job(scheduler, run_scheduler_heartbeat, CronTrigger(
        minute="*/5", timezone=WIB), id="scheduler_heartbeat",
        name="Scheduler Heartbeat", replace_existing=True)

    # Alert on ANY uncaught in-process job exception — one shared contract for
    # all ~20 APScheduler jobs instead of each hand-rolling its own alert-or-not
    # try/except (audit 2026-07-28).
    scheduler.add_listener(_make_job_error_listener(scheduler), EVENT_JOB_ERROR)

    scheduler.start()
    logger.info("Scheduler started:")
    logger.info("  💓 SCHEDULER HEARTBEAT: every 5 min (dead-man's-switch)")
    logger.info("  📡 PHASE 5 BULL-WATCH: 17:10 (NR7 universe band transitions)")
    # Edge Registry (M1 inversion): load once, announce what production runs on.
    from engine.registry_loader import announce_registry
    announce_registry()
    logger.info("  📊 SIGNAL REPORT: 16:00")
    logger.info("  📰 NEWS FETCH: 08:00 pre-market, 17:00 EOD")
    logger.info("  🏛️ BROKER FLOW: 20:15 (after Stockbit EOD publish)")
    logger.info("  🧾 OWNERSHIP COMPOSITION: monthly, day 5 09:00 (major holders + investor buckets)")
    logger.info("  🏢 CORPORATE ACTIONS: 20:20 (dividend/rups/split/bonus/warrant/rightissue)")
    logger.info("  📅 BROKER PERIOD SUMMARY: 20:30 Fri only (7d/1mo/3mo accumulation)")
    logger.info("  📈 STOCKBIT SCREENER: 17:05 (guru templates → stockbit_screener_results)")
    logger.info("  🔍 PRE-MOVER EOD: 16:30 (setup watchlist scan)")
    logger.info("  🏥 MARKET HEALTH: 08:45 pre-market")
    logger.info("  🌅 PREMARKET FIRM: 08:35 pre-market (unified watchlist → agent firm)")
    logger.info("  📋 EOD TRADE PLAN: 16:40 (all long sources → agent firm → 1 ranked msg)")
    logger.info("  🧪 FORWARD-TEST CYCLE: 18:30 (ingest signals → open/exit shadow positions)")
    global _scheduler_instance
    _scheduler_instance = scheduler
    return scheduler


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        logger.info("Running daily_signal_scan once...")
        daily_signal_scan()
    else:
        sched = start_scheduler()
        import time
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            sched.shutdown()
            logger.info("Scheduler stopped.")
