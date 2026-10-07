# scheduler/jobs.py
import os
import sqlite3
import html
import logging
from datetime import datetime
from typing import Optional
import pytz


WIB = pytz.timezone("Asia/Jakarta")
logger = logging.getLogger(__name__)
from config import DB_PATH as _DEFAULT_DB_PATH  # single path authority (audit, Phase 5)
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB_PATH)

from utils.telegram import send_telegram  # noqa: E402
from utils.logging_config import redact_and_truncate  # noqa: E402
from data.db import connect as db_connect  # noqa: E402
from engine.heartbeat import write_heartbeat  # noqa: E402
from engine.job_status import current_job  # noqa: E402

HEARTBEAT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "logs", "scheduler_heartbeat.txt")


def run_scheduler_heartbeat():
    """Dead-man's-switch writer: stamp the heartbeat file (audit 3.7).

    Fires every 5 min regardless of market hours, so a stale file means the
    scheduler is actually dead — the external watchdog
    (scripts/check_scheduler_heartbeat.py) alarms on staleness.
    """
    from datetime import timezone
    try:
        write_heartbeat(HEARTBEAT_PATH, datetime.now(timezone.utc))
    except Exception as e:  # never let the heartbeat crash the scheduler
        logging.warning(f"[heartbeat] write failed: {e}")
from scheduler.utils import get_all_tickers, _load_ohlcv_bulk  # noqa: E402


def _holiday_skip(fn_name: str) -> bool:
    """Return True when IDX is closed today (holiday or weekend) — caller should return."""
    try:
        from engine.calendar_filter import is_trading_day
        ok, reason = is_trading_day()
        if not ok:
            logging.info(f"[{fn_name}] Non-trading day ({reason}) — skipped")
            return True
    except Exception:
        pass
    return False


# _WF_LOCK_JOB moved to research/jobs.py in M3 (spec §10-M3)


# _pid_alive moved to research/jobs.py in M3 (spec §10-M3)


# _wf_lock_acquire moved to research/jobs.py in M3 (spec §10-M3)


# _wf_lock_release moved to research/jobs.py in M3 (spec §10-M3)


# refresh_wf_scores moved to research/jobs.py in M3 (spec §10-M3)


def run_flow_fetch():
    """Fetch flow data dari Stockbit dan simpan ke DB."""
    if _holiday_skip("run_flow_fetch"):
        return
    from datetime import datetime as dt, date
    import sqlite3
    now_str = dt.now(WIB).strftime('%H:%M')
    is_first_session = dt.now(WIB).hour == 9
    today_str = str(date.today())
    logger.info(f"[{now_str}] Flow fetch dimulai...")
    try:
        from flow_filter import main as flow_main
        import sys as _sys
        _argv = _sys.argv[:]
        _sys.argv = ["flow_filter.py"]
        flow_main()
        _sys.argv = _argv
        # Verifikasi data tersimpan
        conn = db_connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM stockbit_flow WHERE trade_date=?", (today_str,)
        ).fetchone()[0]
        conn.close()
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Flow fetch selesai. {count} tickers tersimpan.")
        # Bootstrap C1: before 16:15 WIB the current day must have no settled
        # (is_final=1) ohlcv bars — same-day finality belongs to the 16:15 EOD
        # authority only (2026-09-15 pre-open defect: 585 such rows). Alert-only.
        fin = check_same_day_finality(DB_PATH, dt.now(WIB))
        if fin["violation"]:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] PIT finality violation: "
                           f"{fin['count']} is_final=1 bars for {fin['date']} before 16:15 WIB")
            send_telegram(
                f"🚨 <b>PIT Finality Violation</b>\n\n"
                f"<code>ohlcv</code> has <b>{fin['count']}</b> is_final=1 bars dated "
                f"{fin['date']} before 16:15 WIB.\n"
                f"Same-day bars are provisional until the EOD scraper runs — "
                f"likely the yfinance gap-filler wrote unsettled data as settled."
            , event="data.pit_finality_violation")
        if is_first_session and count == 0:
            send_telegram(
                f"⚠️ <b>Flow Fetch WARNING</b>\n\n"
                f"Sesi pertama ({now_str}) selesai tapi <b>0 tickers tersimpan</b>.\n"
                f"Kemungkinan: token Stockbit expired.\n\n"
                f"Cek: <code>cat .stockbit_token</code>"
            , event="data.flow_zero_warning")
    except Exception as e:
        logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Flow fetch error: {e}")
        if is_first_session:
            send_telegram(
                f"🔴 <b>Flow Fetch GAGAL</b>\n\n"
                f"Sesi pertama ({now_str}) error:\n"
                f"<code>{redact_and_truncate(str(e), 200)}</code>\n\n"
                f"Signal scan 15:35 akan berjalan <b>tanpa flow data</b>."
            , event="data.flow_fetch_failed")


def check_flow_coverage(db_path: str, trade_date: str, lookback: int = 10,
                        hard_floor: int = 50) -> dict:
    """Assess whether stockbit_flow coverage for trade_date looks healthy.

    Compares the distinct-ticker count for trade_date against the median over
    the prior `lookback` sessions that had data. A coverage outage (e.g. the
    2026-04-22/23 zero-ticker gap) can only be backfilled the same day — the
    Stockbit tradebook API will not serve a historical session — so this exists
    to alert while the data is still fetchable.

    Returns dict: {date, count, baseline, severity, healthy, reason}.
    severity ∈ {'ok', 'warning', 'critical'}.
    """
    conn = db_connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM stockbit_flow WHERE trade_date=?",
            (trade_date,),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT trade_date, COUNT(DISTINCT ticker) c FROM stockbit_flow "
            "WHERE trade_date < ? GROUP BY trade_date HAVING c > 0 "
            "ORDER BY trade_date DESC LIMIT ?",
            (trade_date, lookback),
        ).fetchall()
    finally:
        conn.close()

    counts = sorted(c for _, c in rows)
    baseline = None
    if counts:
        m = len(counts)
        baseline = (counts[m // 2] if m % 2
                    else (counts[m // 2 - 1] + counts[m // 2]) // 2)

    if count == 0:
        severity = "critical"
        reason = ("Tidak ada satu pun ticker tersimpan — kemungkinan fetch "
                  "outage atau token Stockbit expired.")
    else:
        threshold = max(hard_floor, int(0.5 * baseline)) if baseline else hard_floor
        if count < threshold:
            severity = "warning"
            reason = (f"Coverage {count} jauh di bawah ambang {threshold} "
                      f"(baseline {baseline}).")
        else:
            severity = "ok"
            reason = "Coverage normal."

    return {"date": trade_date, "count": count, "baseline": baseline,
            "severity": severity, "healthy": severity == "ok", "reason": reason}


def check_same_day_finality(db_path: str, now_wib: datetime) -> dict:
    """Bootstrap C1 (readiness audit 2026-09-16): count is_final=1 ohlcv bars
    dated the current WIB day and decide whether that violates finality (it
    does any time before the 16:15 EOD authority — the 2026-09-15 pre-open
    defect wrote 585 such rows). Alert-only; reads, never writes."""
    from engine.pipeline_health import same_day_final_bars
    wib_today = now_wib.strftime("%Y-%m-%d")
    conn = db_connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM ohlcv WHERE date=? AND is_final=1",
            (wib_today,)).fetchone()[0]
    finally:
        conn.close()
    s = same_day_final_bars(count, now_wib.hour, now_wib.minute)
    return {"date": wib_today, **s}


def check_prior_session_flow_coverage(db_path: str, today_str: str) -> dict:
    """Bootstrap C2 (readiness audit 2026-09-16): prior expected trading
    session (latest trading_calendar date strictly before today) with ZERO
    stockbit_flow tickers — the 2026-08-25 gap class, which the same-day
    monitor above cannot catch when the outage day's own runs never fire.
    Alert-only; never backfills, never mutates stockbit_flow."""
    from engine.pipeline_health import prior_session_flow_gap
    conn = db_connect(db_path)
    try:
        prev = conn.execute(
            "SELECT MAX(date) FROM trading_calendar WHERE date < ?",
            (today_str,)).fetchone()[0]
        n = None
        if prev:
            n = conn.execute(
                "SELECT COUNT(DISTINCT ticker) FROM stockbit_flow WHERE trade_date=?",
                (prev,)).fetchone()[0]
    except sqlite3.OperationalError:
        # trading_calendar/stockbit_flow absent (pre-migration or fixture DB):
        # nothing evaluable here — schema-level alarms belong to the ohlcv
        # coverage monitor.
        return prior_session_flow_gap(None, None)
    finally:
        conn.close()
    return prior_session_flow_gap(prev, n)


def run_broker_flow_fetch():
    """Fetch broker flow data setelah 20:00 WIB saat Stockbit publish summary harian."""
    if _holiday_skip("run_broker_flow_fetch"):
        return
    from datetime import datetime as dt, date
    import sqlite3
    now_str = dt.now(WIB).strftime('%H:%M')
    today_str = str(date.today())
    logger.info(f"[{now_str}] Broker flow fetch dimulai...")
    try:
        from stockbit_fetcher import extract_token_from_chrome, verify_token, run_flow, get_tickers
        token = extract_token_from_chrome()
        if not token or not verify_token(token):
            send_telegram("🔴 <b>Broker Flow Fetch GAGAL</b>\nToken Stockbit expired atau tidak ditemukan.", event="data.token_expired", subject="broker_flow")
            return
        tickers = get_tickers("ALL")
        # Include open paper trade tickers not already in ALL list
        conn_pt = db_connect(DB_PATH)
        extra = [r[0] for r in conn_pt.execute(
            "SELECT DISTINCT ticker FROM paper_trades WHERE status='OPEN'"
        ).fetchall()]
        conn_pt.close()
        extra_new = [t for t in extra if t not in tickers]
        if extra_new:
            logger.info(f"[{now_str}] + {len(extra_new)} extra tickers from paper trades: {extra_new}")
            tickers = tickers + extra_new
        run_flow(token, tickers)
        conn = db_connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM broker_flow WHERE trade_date=?", (today_str,)
        ).fetchone()[0]
        conn.close()
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Broker flow selesai. {count} tickers untuk {today_str}.")

        # Coverage monitor: alert on a stockbit_flow outage while it can still be
        # re-fetched today (a past session cannot be backfilled later).
        cov = check_flow_coverage(DB_PATH, today_str)
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Flow coverage {today_str}: "
              f"{cov['count']} tickers (baseline {cov['baseline']}) → {cov['severity']}")
        if not cov["healthy"]:
            icon = "🔴" if cov["severity"] == "critical" else "⚠️"
            send_telegram(
                f"{icon} <b>Flow Coverage {cov['severity'].upper()}</b>\n\n"
                f"<code>stockbit_flow</code> untuk {today_str}: "
                f"<b>{cov['count']}</b> tickers (baseline ~{cov['baseline']}).\n"
                f"{cov['reason']}\n\n"
                f"Backfill hanya mungkin selagi sesi masih live — cek token & "
                f"re-run <code>run_broker_flow_fetch</code> hari ini."
            , event="data.flow_coverage")

        # Bootstrap C2: a PRIOR completed session with zero flow tickers is the
        # 2026-08-25 gap class — the same-day monitor above cannot fire when the
        # outage day's own runs never ran. Alert-only; never backfills, never
        # mutates stockbit_flow.
        gap = check_prior_session_flow_coverage(DB_PATH, today_str)
        if gap["alert"]:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] stockbit_flow gap: "
                           f"session {gap['session']} has 0 tickers")
            send_telegram(
                f"🔴 <b>Flow Coverage GAP — {gap['session']}</b>\n\n"
                f"Previous completed session <b>{gap['session']}</b> has <b>0</b> "
                f"tickers in <code>stockbit_flow</code>.\n"
                f"The session cannot be re-fetched historically — record the gap "
                f"for research exclusion "
                f"(see docs/research_programs/P-M/DATA_GAP_AUDIT_2026-09-14.md)."
            , event="data.flow_gap")
    except Exception as e:
        logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Broker flow fetch error: {e}")
        send_telegram(f"🔴 <b>Broker Flow Fetch Error</b>\n<code>{redact_and_truncate(str(e), 200)}</code>", event="data.flow_fetch_failed")


def run_broker_period_summary_fetch():
    """Weekly period-aggregated broker summary (LAST_7_DAYS/LAST_1_MONTH/
    LAST_3_MONTHS) — see stockbit_broker_period.py's module docstring for the
    endpoint investigation. Complementary to run_broker_flow_fetch() (daily,
    single-day broker_flow, untouched); this job writes the separate
    broker_period_summary table.

    Cadence: weekly (Friday, after the daily broker flow fetch), not daily.
    Reasoning: a rolling 7-day/1-month/3-month accumulation window shifts by
    only one trading day at a time — a daily refetch would be >95% duplicate
    work for the LAST_1_MONTH/LAST_3_MONTHS windows in particular. Weekly
    keeps total request volume for this job (~universe x 3 periods, once a
    week) in the same order of magnitude as the existing daily broker_flow
    fetch (~universe x 1, five times a week), rather than 3x it every day.

    Reuses the exact token-acquisition and ticker-universe calls
    run_broker_flow_fetch() already uses (extract_token_from_chrome/
    verify_token/get_tickers) rather than reimplementing them. One ticker
    failing (or one period within a ticker) is logged and skipped — every
    other ticker/period combination is still attempted, and this job never
    raises, matching run_broker_flow_fetch()'s contract.
    """
    if _holiday_skip("run_broker_period_summary_fetch"):
        return
    from datetime import datetime as dt
    from stockbit_fetcher import extract_token_from_chrome, verify_token, get_tickers
    from stockbit_broker_period import run_and_persist_broker_period, PERIODS
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Broker period summary fetch dimulai...")

    token = extract_token_from_chrome()
    if not token or not verify_token(token):
        send_telegram("🔴 <b>Broker Period Summary Fetch GAGAL</b>\n"
                      "Token Stockbit expired atau tidak ditemukan.", event="data.token_expired", subject="broker_period")
        return

    tickers = get_tickers("ALL")
    total = 0
    failures = []
    for ticker in tickers:
        for period_name in PERIODS:
            try:
                summary = run_and_persist_broker_period(ticker, period_name, token, db_path=DB_PATH)
                total += summary["count"]
            except Exception as e:
                logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Broker period summary "
                              f"'{ticker}'/'{period_name}' error: {e}")
                failures.append((ticker, period_name, str(e)))

    if failures:
        tickers_failed = sorted({t for t, _, _ in failures})
        detail = "\n".join(f"  {t}/{p}: {err[:120]}" for t, p, err in failures[:10])
        more = f"\n  ... +{len(failures) - 10} more" if len(failures) > 10 else ""
        send_telegram(
            f"🔴 <b>Broker Period Summary Fetch GAGAL (sebagian)</b>\n\n"
            f"{len(failures)} kombinasi ticker/period gagal ({len(tickers_failed)} ticker):\n"
            f"{detail}{more}\n\n"
            f"{total} baris tersimpan dari kombinasi yang berhasil."
        , event="data.broker_period_failed")
    else:
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Broker period summary fetch selesai. "
                   f"{total} baris tersimpan untuk {len(tickers)} tickers x {len(PERIODS)} periods.")


def run_corporate_actions_fetch():
    """Daily corporate-action event history (dividend/rups/stocksplit/bonus/
    warrant/rightissue) — see stockbit_corporate_actions.py's module
    docstring for the endpoint investigation (confirmed + rejected
    candidates). Complementary to the existing yfinance-sourced
    corporate_actions table (dividends/splits only); this job writes the
    separate corporate_action_events table.

    Cadence: daily (not weekly like run_broker_period_summary_fetch()).
    Reasoning is the opposite of that job's: broker_period_summary is a
    slow-moving rolling window that barely changes day to day, so daily
    refetching would be mostly duplicate work. Corporate actions are the
    opposite — they're discrete, sporadically-announced, often
    price-moving catalysts (a new rights issue or dividend announcement),
    and only useful here if caught close to when Stockbit publishes them.
    The endpoint is also cheap: no pagination, and each ticker's full
    history (proven live to be identical regardless of `limit`) is at most
    a few dozen small rows — a daily full-universe pass costs roughly the
    same request volume as one day of run_broker_flow_fetch(), not 3x like
    the period-summary job would if run daily.

    Reuses the exact token-acquisition and ticker-universe calls
    run_broker_flow_fetch()/run_broker_period_summary_fetch() already use.
    One ticker failing is logged and skipped — every other ticker is still
    attempted, and this job never raises.
    """
    if _holiday_skip("run_corporate_actions_fetch"):
        return
    from datetime import datetime as dt
    from stockbit_fetcher import extract_token_from_chrome, verify_token, get_tickers
    from stockbit_corporate_actions import run_and_persist_corporate_actions
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Corporate actions fetch dimulai...")

    token = extract_token_from_chrome()
    if not token or not verify_token(token):
        send_telegram("🔴 <b>Corporate Actions Fetch GAGAL</b>\n"
                      "Token Stockbit expired atau tidak ditemukan.", event="data.token_expired", subject="corporate_actions")
        return

    tickers = get_tickers("ALL")
    total = 0
    failures = []
    for ticker in tickers:
        try:
            summary = run_and_persist_corporate_actions(ticker, token, db_path=DB_PATH)
            total += summary["count"]
        except Exception as e:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Corporate actions "
                          f"'{ticker}' error: {e}")
            failures.append((ticker, str(e)))

    if failures:
        detail = "\n".join(f"  {t}: {err[:150]}" for t, err in failures[:10])
        more = f"\n  ... +{len(failures) - 10} more" if len(failures) > 10 else ""
        send_telegram(
            f"🔴 <b>Corporate Actions Fetch GAGAL (sebagian)</b>\n\n"
            f"{len(failures)}/{len(tickers)} ticker gagal:\n{detail}{more}\n\n"
            f"{total} event tersimpan dari ticker yang berhasil."
        , event="data.corporate_actions_failed")
    else:
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Corporate actions fetch selesai. "
                   f"{total} event tersimpan untuk {len(tickers)} tickers.")


def run_ownership_fetch():
    """Monthly ownership composition/distribution (named major holders +
    investor-type buckets, e.g. "Mutual Funds", "Pension Funds") — see
    stockbit_ownership.py's module docstring for the endpoint investigation.
    Genuinely new dataset: nothing else in this pipeline captures ownership
    structure or float concentration for any ticker.

    Cadence: monthly, not daily/weekly like the other three collectors —
    empirically determined, not assumed. Live-testing the endpoint against
    six unrelated tickers on 2026-08-05 found every one of them reporting
    the IDENTICAL report_date (the last calendar day of the prior month),
    and the endpoint only ever returns a single period (no history). A
    daily or weekly schedule would refetch byte-identical data for ~30/~4
    runs out of every cycle respectively — this is a market-wide monthly
    registry publication (KSEI-style), not a continuously-updated feed, so
    the schedule matches that reality directly: once a month, a few days
    after month-end to give Stockbit time to ingest the new registry.

    Reuses the exact token-acquisition and ticker-universe calls the other
    three collectors already use. One ticker failing is logged and
    skipped — every other ticker is still attempted, and this job never
    raises.
    """
    if _holiday_skip("run_ownership_fetch"):
        return
    from datetime import datetime as dt
    from stockbit_fetcher import extract_token_from_chrome, verify_token, get_tickers
    from stockbit_ownership import run_and_persist_ownership
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Ownership composition fetch dimulai...")

    token = extract_token_from_chrome()
    if not token or not verify_token(token):
        send_telegram("🔴 <b>Ownership Fetch GAGAL</b>\n"
                      "Token Stockbit expired atau tidak ditemukan.", event="data.token_expired", subject="ownership")
        return

    tickers = get_tickers("ALL")
    total = 0
    failures = []
    for ticker in tickers:
        try:
            summary = run_and_persist_ownership(ticker, token, db_path=DB_PATH)
            total += summary["count"]
        except Exception as e:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Ownership "
                          f"'{ticker}' error: {e}")
            failures.append((ticker, str(e)))

    if failures:
        detail = "\n".join(f"  {t}: {err[:150]}" for t, err in failures[:10])
        more = f"\n  ... +{len(failures) - 10} more" if len(failures) > 10 else ""
        send_telegram(
            f"🔴 <b>Ownership Fetch GAGAL (sebagian)</b>\n\n"
            f"{len(failures)}/{len(tickers)} ticker gagal:\n{detail}{more}\n\n"
            f"{total} baris tersimpan dari ticker yang berhasil."
        , event="data.ownership_failed")
    else:
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Ownership fetch selesai. "
                   f"{total} baris tersimpan untuk {len(tickers)} tickers.")


def run_insider_fetch():
    """Daily insider BUY/SELL transaction event log (director/commissioner/
    major-holder share movements) — see stockbit_insider.py's module
    docstring for the endpoint investigation and 2026-09-22 field-name
    verification against a live BBCA response. Genuinely new dataset:
    nothing else in this pipeline captures individual insider transactions
    (stockbit_ownership.py's composition table is a monthly aggregate
    snapshot, not per-transaction).

    Cadence: daily, same reasoning as run_corporate_actions_fetch() —
    insider transactions are discrete, sporadically-disclosed events (an
    insider's BUY is only useful caught close to when Stockbit publishes
    it), not a slow-moving rolling aggregate. Unlike corporate actions,
    this endpoint IS paginated (BBCA: 2 pages, 85 rows total) but each
    ticker's page count is small and bounded (MAX_PAGES=40 as a safety
    valve — see stockbit_insider.py), so a daily full-universe pass is
    still cheap.

    Reuses the exact token-acquisition and ticker-universe calls the other
    collectors already use. One ticker failing is logged and skipped —
    every other ticker is still attempted, and this job never raises.
    """
    if _holiday_skip("run_insider_fetch"):
        return
    from datetime import datetime as dt
    from stockbit_fetcher import extract_token_from_chrome, verify_token, get_tickers
    from stockbit_insider import run_and_persist_insider
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Insider transactions fetch dimulai...")

    token = extract_token_from_chrome()
    if not token or not verify_token(token):
        send_telegram("🔴 <b>Insider Transactions Fetch GAGAL</b>\n"
                      "Token Stockbit expired atau tidak ditemukan.", event="data.token_expired", subject="insider")
        return

    tickers = get_tickers("ALL")
    total = 0
    failures = []
    for ticker in tickers:
        try:
            summary = run_and_persist_insider(ticker, token, db_path=DB_PATH)
            total += summary["count"]
        except Exception as e:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Insider transactions "
                          f"'{ticker}' error: {e}")
            failures.append((ticker, str(e)))

    if failures:
        detail = "\n".join(f"  {t}: {err[:150]}" for t, err in failures[:10])
        more = f"\n  ... +{len(failures) - 10} more" if len(failures) > 10 else ""
        send_telegram(
            f"🔴 <b>Insider Transactions Fetch GAGAL (sebagian)</b>\n\n"
            f"{len(failures)}/{len(tickers)} ticker gagal:\n{detail}{more}\n\n"
            f"{total} transaksi tersimpan dari ticker yang berhasil."
        , event="data.insider_failed")
    else:
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Insider transactions fetch selesai. "
                   f"{total} transaksi tersimpan untuk {len(tickers)} tickers.")


def run_stockbit_screener_fetch():
    """Fetch Stockbit guru-template screener snapshots and persist them.

    Runs the existing on-demand collector (screener/stockbit_screener.py,
    unchanged — only its new save_screener_results()/run_and_persist_screener()
    persistence layer is scheduler-specific) once per trading day for every
    registered GURU_TEMPLATES entry. One template failing (e.g. an expired
    token) does not block the others, and this job never raises — matching
    run_broker_flow_fetch()/run_news_fetch()'s contract so a bad day here
    can't take down the rest of the scheduler run.
    """
    if _holiday_skip("run_stockbit_screener_fetch"):
        return
    from datetime import datetime as dt
    from screener.stockbit_screener import GURU_TEMPLATES, run_and_persist_screener
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Stockbit screener fetch dimulai...")

    total = 0
    failures = []
    for name in GURU_TEMPLATES:
        try:
            summary = run_and_persist_screener(name, db_path=DB_PATH)
            total += summary["count"]
            logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Screener '{name}': "
                       f"{summary['count']} tickers tersimpan.")
        except Exception as e:
            logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] Screener '{name}' error: {e}")
            failures.append((name, str(e)))

    if failures:
        detail = "\n".join(f"  {n}: {err[:150]}" for n, err in failures)
        send_telegram(
            f"🔴 <b>Stockbit Screener Fetch GAGAL (sebagian)</b>\n\n"
            f"{len(failures)}/{len(GURU_TEMPLATES)} template gagal:\n{detail}\n\n"
            f"{total} baris tersimpan dari template yang berhasil."
        , event="data.screener_fetch_failed")
    else:
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Stockbit screener fetch selesai. "
                   f"{total} baris tersimpan.")


def run_ohlcv_reconciliation():
    """21:00 WIB — alert-only comparison of today's scraper-final closes vs
    yfinance raw (Phase 2A, audit C-4). Scraper stays the authority."""
    if _holiday_skip("run_ohlcv_reconciliation"):
        return
    from data.reconcile import reconcile_ohlcv
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    try:
        rep = reconcile_ohlcv(today)
        n = len(rep["mismatches"])
        logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] OHLCV reconcile {today}: "
              f"{rep['compared']} compared, {rep['missing_yf']} missing on yf, {n} mismatches")
        if n:
            top = "\n".join(
                f"  {m['ticker']}: scraper {m['scraper']:,.0f} vs yf {m['yfinance']:,.0f} ({m['diff_pct']}%)"
                for m in rep["mismatches"][:10])
            send_telegram(
                f"\u2696\ufe0f <b>OHLCV Reconciliation {today}</b>\n\n"
                f"{n} mismatch(es) > 0.1% of {rep['compared']} compared "
                f"(alert-only; scraper is authority):\n{top}"
            , event="data.ohlcv_reconcile")
    except Exception as e:
        logger.warning(f"[scheduler] OHLCV reconcile error: {e}")


def run_token_health_check(token_file: str = None):
    """Alert if the Stockbit token is expired or expiring soon (Phase 3A).

    The 24h JWT is refreshed by a morning cron; when that cron fails the token
    dies silently and every fetch 401s (the 2026-07-04 incident). This surfaces
    it. Alert-only — refresh stays owned by auto_token.py."""
    if _holiday_skip("run_token_health_check"):
        return
    import os
    from engine.pipeline_health import token_status
    tf = token_file or os.path.join(os.path.dirname(os.path.dirname(__file__)), ".stockbit_token")
    try:
        tok = open(tf).read().strip()
    except Exception:
        tok = ""
    s = token_status(tok)
    if s["healthy"]:
        logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] Token health OK "
              f"({s['hours_left']:.1f}h left)")
        return
    hl = s["hours_left"]
    left = f"{hl:.1f}h left" if hl is not None else "unreadable"
    icon = "🔴" if s["status"] in ("expired", "invalid") else "⚠️"
    send_telegram(
        f"{icon} <b>Stockbit Token {s['status'].upper()}</b>\n\n"
        f"Token: {left}. Fetching/backfill will 401 until refreshed.\n"
        f"Refresh: <code>python3 auto_token.py</code>"
    , event="data.token_health_warning")
    logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] Token health ALERT: {s['status']} ({left})")


def _stockbit_probe_status(token: str):
    """One live Stockbit call; the HTTP status, or None on a network error.

    The probe must tell a revoked token (401/403) apart from a transient 429/5xx, and only
    the former justifies a re-login. Shared with the EOD finalisation pass."""
    from stockbit_fetcher import token_status
    return token_status(token)


def _run_token_refresh() -> bool:
    """auto_token.py in a subprocess (Playwright never runs inside the web process)."""
    from stockbit_fetcher import refresh_token_subprocess
    return refresh_token_subprocess()


def run_token_live_probe(token_file: str = None):
    """16:05 WIB: verify the Stockbit token against the live API before the 16:15 EOD run.

    Why (2026-09-21, 2026-09-22): the token was revoked server-side mid-afternoon while its
    exp claim still showed ~21h left. run_token_health_check reads only the exp claim, so it
    reported "OK", and the 16:15 EOD scraper got HTTP 401 on all 958 tickers, leaving each
    session provisional with no alert until the next morning.

    401/403 (or no token) -> run auto_token.py once, re-probe, report the outcome.
    Any other failure (429/5xx/network) is reported as inconclusive and does NOT trigger a
    re-login: a new login may itself revoke a working session.
    """
    if _holiday_skip("run_token_live_probe"):
        return
    now = datetime.now(WIB).strftime("%H:%M")
    tf = token_file or os.path.join(os.path.dirname(os.path.dirname(__file__)), ".stockbit_token")
    try:
        tok = open(tf).read().strip()
    except Exception:
        tok = ""
    status = _stockbit_probe_status(tok) if tok else 401
    if status == 200:
        logger.info(f"[{now}] Token live probe OK (HTTP 200)")
        return
    if status not in (401, 403):
        logger.warning(f"[{now}] Token live probe inconclusive (HTTP {status})")
        send_telegram(
            f"⚠️ <b>Stockbit token probe inconclusive</b> ({now})\n\n"
            f"Live check returned {'a network error' if status is None else f'HTTP {status}'}, "
            f"not 401. No re-login attempted (a new login can revoke a working session).\n"
            f"Watch the 16:15 EOD finalisation.", event="data.token_probe_inconclusive")
        return

    what = "missing" if not tok else f"HTTP {status}"
    logger.warning(f"[{now}] Token live probe: {what} — running auto_token refresh")
    refreshed = _run_token_refresh()
    try:
        tok2 = open(tf).read().strip()
    except Exception:
        tok2 = ""
    after = _stockbit_probe_status(tok2) if tok2 else None
    if after == 200:
        send_telegram(
            f"🟡 <b>Stockbit token revoked — recovered</b> ({now})\n\n"
            f"Live probe got {what} although the exp claim looked valid; auto_token refreshed "
            f"it and the new token verifies. 16:15 EOD should finalise normally.", event="data.token_recovered")
    else:
        send_telegram(
            f"🔴 <b>Stockbit token DEAD before EOD</b> ({now})\n\n"
            f"Live probe got {what}; auto_token refresh "
            f"{'ran but the token still fails' if refreshed else 'failed'} "
            f"(re-probe: {after}). The 16:15 EOD finalisation will fail.\n"
            f"Fix: <code>python3 auto_token.py --login</code>, then after 16:30 "
            f"<code>python3 scripts/repair_provisional_bars.py --apply</code>", event="data.token_dead_pre_eod")


def run_ohlcv_coverage_check(date_str: str = None):
    """Alert when a trading day's OHLCV ticker coverage is thin/absent vs the
    active universe (Phase 3A) — catches fetch outages (e.g. token death) and
    scraper failures the reconciliation job (close-value only) misses."""
    if _holiday_skip("run_ohlcv_coverage_check"):
        return
    from engine.pipeline_health import ohlcv_coverage
    day = date_str or datetime.now(WIB).strftime("%Y-%m-%d")
    try:
        conn = db_connect(DB_PATH)
        universe = conn.execute(
            "SELECT COUNT(*) FROM idx_tickers WHERE status='active'").fetchone()[0]
        count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM ohlcv WHERE date=? AND ticker!='IHSG'",
            (day,)).fetchone()[0]
        conn.close()
    except Exception as e:
        logger.warning(f"[coverage] DB error: {e}")
        return
    s = ohlcv_coverage(count, universe)
    logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] OHLCV coverage {day}: "
          f"{count}/{universe} ({s['pct']*100:.0f}%) — {s['severity']}")
    if not s["healthy"]:
        icon = "🔴" if s["severity"] == "critical" else "⚠️"
        send_telegram(
            f"{icon} <b>OHLCV Coverage {s['severity'].upper()} — {day}</b>\n\n"
            f"Only <b>{count}/{universe}</b> tickers ({s['pct']*100:.0f}%) have a bar.\n"
            f"Likely a fetch outage (check token: <code>python3 auto_token.py --check</code>) "
            f"or scraper failure."
        , event="data.ohlcv_coverage")


def run_foreign_snapshot():
    """14:30 WIB — Pre-close foreign-owned-brokerage flow watchlist alert.

    Uses the most recently available broker_flow (investor_type='Asing', i.e. foreign-owned
    brokerage) data (fetched nightly at 20:15). This is brokerage ownership, not end-investor
    identity — it is not evidence of foreign investor buying/selling (D1, see
    docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md). Sends top 5
    buy + top 5 sell tickers ranked by 5-day score_pct.
    """
    if _holiday_skip("run_foreign_snapshot"):
        return
    from datetime import datetime as dt
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] Foreign snapshot dimulai...")
    try:
        from flow_filter import get_top_foreign_accumulation
        all_results = get_top_foreign_accumulation(top_n=9999)
        top_buy = [r for r in all_results if r["score_pct"] > 0][:5]
        top_sell = sorted(all_results, key=lambda x: x["score_pct"])[:5]
        top_sell = [r for r in top_sell if r["score_pct"] < 0]

        latest = all_results[0]["latest_date"] if all_results else "N/A"
        msg = f"🏛️ <b>Foreign-Owned Brokerage Flow Snapshot — {dt.now(WIB).strftime('%d/%m %H:%M')}</b>\n"
        msg += f"<i>Data: {latest} | 5-day net / avg vol</i>\n\n"

        if top_buy:
            msg += "<b>🟢 Top Foreign-Owned Brokerage Accumulation:</b>\n"
            for r in top_buy:
                msg += f"  {r['ticker']}: {r['score_pct']:+.1f}% ({r['foreign_net_lots']:+,.0f} lots)\n"
        else:
            msg += "<b>🟢 No significant foreign-owned brokerage buying</b>\n"

        if top_sell:
            msg += "\n<b>🔴 Top Foreign-Owned Brokerage Distribution:</b>\n"
            for r in top_sell:
                msg += f"  {r['ticker']}: {r['score_pct']:+.1f}% ({r['foreign_net_lots']:+,.0f} lots)\n"
        else:
            msg += "\n<b>🔴 No significant foreign-owned brokerage selling</b>\n"

        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] Foreign snapshot computed ({len(top_buy)} buy, {len(top_sell)} sell) — no alert")
    except Exception as e:
        logging.error(f"run_foreign_snapshot error: {e}")


def run_news_fetch():
    """Fetch Google News headlines per ticker, persist to news_mentions table.

    Spike detection (today_count >= 3× 30d avg) is consumed by flow_broker_report.
    """
    if _holiday_skip("run_news_fetch"):
        return
    from datetime import datetime as dt
    now_str = dt.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] News fetch dimulai...")
    try:
        from news_filter import run_news_batch
        saved = run_news_batch()
        logger.info(f"[{dt.now(WIB).strftime('%H:%M')}] News fetch selesai. {saved} tickers tersimpan.")
    except Exception as e:
        logger.warning(f"[{dt.now(WIB).strftime('%H:%M')}] News fetch error: {e}")
        send_telegram(
            f"🔴 <b>News Fetch GAGAL</b>\n\n"
            f"<code>{redact_and_truncate(str(e), 200)}</code>"
        , event="data.news_fetch_failed")


def _run_open_trade_monitor():
    try:
        from monitor import check_all_open_trades
        check_all_open_trades()
    except Exception as e:
        logger.warning(f"[scheduler] Monitor error: {e}")
    # DD circuit breaker check — cheap, runs each monitor cycle (every 5 min during trading)
    try:
        from paper_trade import check_dd_circuit_breaker
        check_dd_circuit_breaker()
    except Exception as e:
        logger.warning(f"[scheduler] DD circuit breaker error: {e}")


def _run_screener_intraday():
    try:
        from screener.screener_jobs import run_intraday
        run_intraday(send_telegram=send_telegram)
    except Exception as e:
        logger.warning(f"[scheduler] Screener intraday error: {e}")


def _run_screener_eod():
    try:
        from screener.screener_jobs import run_eod
        run_eod(send_telegram=send_telegram)
    except Exception as e:
        logger.warning(f"[scheduler] Screener EOD error: {e}")


def run_eod_retry_job():
    """17:30 WIB: same-day retry of the 16:15 EOD finalisation (screener.run_eod_retry).

    Deduped per day through _job_sentinel (first INSERT wins) so a systemd-restart race never
    scrapes twice; fails open on a lock error like the other sentinel users, skipping the run."""
    if _holiday_skip("run_eod_retry_job"):
        return
    date_str = datetime.now(WIB).strftime("%Y-%m-%d")
    try:
        with db_connect(DB_PATH) as _g:
            _g.execute("CREATE TABLE IF NOT EXISTS _job_sentinel "
                       "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))")
            _g.execute("INSERT INTO _job_sentinel VALUES ('eod_retry', ?)", (date_str,))
    except sqlite3.IntegrityError:
        logger.info(f"[eod-retry] already ran {date_str} — skipped (dup guard)")
        return
    except sqlite3.OperationalError as e:
        logger.warning(f"[eod-retry] dedup guard error — skipped: {e}")
        return
    from screener.screener_jobs import run_eod_retry
    result = run_eod_retry(trade_date=date_str, send_telegram=send_telegram, today=date_str)
    logger.info(f"[eod-retry] {result}")


# _refresh_backtest_cache moved to research/jobs.py in M3 (spec §10-M3)


def _send_premover_auto_summary(rows: list, mode: str, send_fn) -> None:
    """Send Telegram summary of shadow/enforce evaluation results."""
    _LABEL = {'off': 'OFF', 'shadow': 'SHADOW', 'enforce': 'ENFORCE'}
    mode_label = _LABEL.get(mode, mode.upper())
    passed  = [r for r in rows if r.get('would_trade')]
    blocked = [r for r in rows if not r.get('would_trade')]
    msg = f"\U0001f916 <b>Premover {mode_label} — {len(rows)} setups</b>\n\n"
    for r in passed:
        msg += f"✅ <b>{r['ticker']}</b> score={r['score']} → PASS\n"
    for r in blocked:
        reason = r.get('skip_reason', 'unknown')
        msg += f"❌ <b>{r['ticker']}</b> score={r['score']} → {reason}\n"
    if not rows:
        msg += "No new setups to evaluate.\n"
    try:
        send_fn(msg)
    except Exception as e:
        logger.warning(f"[premover auto] Telegram summary error: {e}")


def get_market_risk_for_circuit_breaker() -> dict:
    """Fetch today's composite market risk for the circuit breaker gate."""
    try:
        import sqlite3 as _sql
        from flow_filter import get_market_accdist_summary
        from engine.vpin import get_market_vpin_summary
        from engine.breadth import get_market_breadth
        from engine.technicals import detect_ihsg_technicals
        from engine.risk_score import compute_market_risk_score
        today = datetime.now(WIB).strftime('%Y-%m-%d')
        conn = _sql.connect(DB_PATH)
        try:
            vpin_s = get_market_vpin_summary(conn, today)
            accdist_s = get_market_accdist_summary(today)
            breadth_s = get_market_breadth(conn, today)
            tech_s = detect_ihsg_technicals(conn, today)
            foreign_net = None
            return compute_market_risk_score(vpin_s, accdist_s, breadth_s, tech_s, foreign_net)
        finally:
            conn.close()
    except Exception as _e:
        logging.warning(f"[circuit_breaker] risk fetch error: {_e}")
        return {'tier': 'GREEN', 'score': 0.0}


def run_premover_eod():
    """EOD pre-breakout scan — runs at 16:30 after data fetch."""
    if _holiday_skip("run_premover_eod"):
        return
    from engine.premover_detector import run_scan
    from engine.circuit_breaker import check_circuit_breaker, CircuitBreakerState
    from paper_trade import (get_premover_mode, evaluate_premover_trade,
                             stage_entry, _log_premover_auto, init_paper_table)
    now_str = datetime.now(WIB).strftime('%H:%M')

    # Circuit breaker gate — block auto-trading when risk = CRITICAL
    _risk = get_market_risk_for_circuit_breaker()
    _cb_state, _cb_reason = check_circuit_breaker(_risk)
    if _cb_state == CircuitBreakerState.OPEN:
        logger.info(f"[{now_str}] Circuit breaker OPEN: {_cb_reason} — premover EOD paused")
        send_telegram(f"⛔ <b>Circuit Breaker Active</b>\n\n{_cb_reason}\n\nAuto-trading paused. Manual override required.", event="risk.circuit_breaker")
        return

    logger.info(f"[{now_str}] Pre-mover EOD scan dimulai...")
    try:
        new_setups = run_scan(DB_PATH, send_alert_fn=None)
        logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan selesai. "
              f"{len(new_setups)} new setups.")
    except Exception as e:
        logger.warning(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan error: {e}")
        send_telegram(f"🔴 <b>Pre-mover Scan Error</b>\n<code>{redact_and_truncate(str(e), 200)}</code>", event="data.premover_scan_failed")
        return

    mode = get_premover_mode()
    if mode not in ('shadow', 'enforce') or not new_setups:
        return

    init_paper_table()
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    summary_rows = []
    for s in new_setups:
        ticker  = s['ticker']
        score   = s.get('score', 0)
        pattern = s.get('pattern', 'UNKNOWN')
        try:
            ev = evaluate_premover_trade(ticker, score, pattern)
            _log_premover_auto(ticker, today, pattern, score, mode, ev)
            if mode == 'enforce' and ev['would_trade']:
                decision_price = float(s.get('close', 0))
                if decision_price > 0:
                    # P3-2: never fill at the detection bar's price (at 16:30
                    # it may still be the provisional is_final=0 bar, and even
                    # settled it would be a same-bar fill) — stage for the
                    # next session's open, the validated convention.
                    stage_entry(ticker, decision_price, strategy=None,
                                source='premover_eod',
                                note=f"pattern={pattern} score={score}")
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern, **ev})
        except Exception as exc:
            logger.warning(f"[premover auto] {ticker} error: {exc}")
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern,
                                  'would_trade': False,
                                  'skip_reason': f'error:{redact_and_truncate(str(exc), 80)}'})

    # summary_rows available for analysis; Telegram suppressed per config


def run_staged_entry_fills():
    """P3-2: fill staged entries at the next session's open.

    Staged signals (momentum 16:00 scan, premover EOD) never open_trade() at
    the price they were detected at — that fed the live/backtest execution
    mismatch (TODO.md P3). This job first publishes today's provisional bar
    (the yfinance incremental fetch — ohlcv otherwise has no bar for today
    until the 16:00 fetch), then resolves staged entries at that bar's open,
    the price the validated convention fills at. Two slots (09:10, 10:10):
    the second covers a late-arriving bar; a missed window expires rather
    than fills at a retrospective price.
    """
    if _holiday_skip("run_staged_entry_fills"):
        return
    now_str = datetime.now(WIB).strftime('%H:%M')
    try:
        from data.fetcher import fetch_all_incremental
        fetch_all_incremental(category="ALL")
    except Exception as e:
        # Resolve still runs: already-published bars fill; the rest retry at
        # the next slot or expire at window close.
        logger.warning(f"[{now_str}] staged-fill fetch error: {e}")
    try:
        from paper_trade import resolve_staged_entries
        results = resolve_staged_entries()
    except Exception as e:
        logger.warning(f"[{now_str}] staged-fill resolve error: {e}")
        return
    filled = [r for r in results if r.get("status") == "FILLED"]
    if filled:
        msg = ("📝 <b>Staged Entries Filled — next-session open</b>\n\n"
               + "\n".join(
                   f"🟢 <b>{r['ticker']}</b> @ Rp {r.get('fill_price'):,.0f} "
                   f"(signal {r['signal_date']}, source {r.get('source') or 'n/a'})"
                   for r in filled))
        try:
            send_telegram(msg, event="trade.paper_opened",
                          subject=",".join(r["ticker"] for r in filled[:5]))
        except Exception as e:
            logger.warning(f"[{now_str}] staged-fill notify error: {e}")
    n_expired = sum(1 for r in results if r.get("status") == "EXPIRED")
    n_skipped = sum(1 for r in results if r.get("status") == "SKIPPED")
    n_pending = sum(1 for r in results if r.get("status") == "PENDING")
    logger.info(f"[{now_str}] staged fills: {len(filled)} filled, {n_expired} expired, "
                f"{n_skipped} skipped, {n_pending} pending")


# run_backtest_roller moved to research/jobs.py in M3 (spec §10-M3)


def run_hourly_risk_bundle():
    """Send bundled RED market risk alerts for the past hour."""
    if _holiday_skip("run_hourly_risk_bundle"):
        return
    from engine.risk_alert import send_hourly_risk_bundle
    now = datetime.now(WIB)
    send_hourly_risk_bundle(now.strftime('%Y-%m-%d'), now.strftime('%H:%M'))


def run_eod_risk_summary():
    """Send ORANGE/YELLOW market risk EOD summary."""
    if _holiday_skip("run_eod_risk_summary"):
        return
    from engine.risk_alert import send_eod_risk_summary
    now = datetime.now(WIB)
    send_eod_risk_summary(now.strftime('%Y-%m-%d'))


def run_market_health_report():
    """Daily pre-market health report at 08:45 WIB."""
    if _holiday_skip("run_market_health_report"):
        return
    import sqlite3 as _sql
    from engine.health_report import build_market_health_report
    from flow_filter import get_market_accdist_summary
    from engine.vpin import get_market_vpin_summary
    from engine.breadth import get_market_breadth
    from engine.technicals import detect_ihsg_technicals
    from engine.risk_score import compute_market_risk_score

    now = datetime.now(WIB)
    today_str = now.strftime('%Y-%m-%d')
    conn = _sql.connect(DB_PATH)
    try:
        # Use the latest settled date with actual OHLCV data rather than today,
        # since pre-market runs before today's EOD flow/VPIN data is available.
        settled = conn.execute(
            "SELECT MAX(date) FROM ohlcv WHERE ticker='IHSG' AND date<=?", (today_str,)
        ).fetchone()[0]
        date_str = settled or today_str
        vpin_s = get_market_vpin_summary(conn, date_str)
        accdist_s = get_market_accdist_summary(date_str)
        breadth_s = get_market_breadth(conn, date_str)
        tech_s = detect_ihsg_technicals(conn, date_str)
        try:
            # SUM(value) — value is already signed (BUY positive, SELL negative) and is the
            # only column comparable to _foreign_owned_brokerage_flow_risk()'s IDR-calibrated thresholds.
            # Previously (BUY lot_value) - (SELL lot_value): lot_value is unsigned on both
            # sides and not a Rupiah value at all, a D2 defect (see
            # docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md §C.1).
            # investor_type='Asing' = foreign-owned brokerage, not end-investor identity (D1).
            foreign_net = conn.execute(
                "SELECT SUM(value) FROM broker_flow WHERE investor_type='Asing' "
                "AND trade_date<=? AND trade_date>=date(?,'-7 days')",
                (date_str, date_str),
            ).fetchone()[0] or 0
        except Exception:
            foreign_net = None
        risk = compute_market_risk_score(vpin_s, accdist_s, breadth_s, tech_s, foreign_net)
        health = build_market_health_report(date_str, risk, vpin_s, accdist_s, breadth_s, tech_s, foreign_net)

        # External macro (overnight global) — prepended. Fail-soft.
        ext_block = ""
        try:
            from engine.external_macro import (
                fetch_external_macro, build_external_macro_block, macro_bias)
            ext = fetch_external_macro()
            ext_block = build_external_macro_block(ext) + f"\n  Bias: {macro_bias(ext)}\n\n"
        except Exception as _me:
            logging.warning(f"[market_health_report] external macro skipped: {_me}")

        # News catalysts (today's premarket fetch, real tickers only) — appended. Fail-soft.
        news_block = ""
        try:
            from engine.news_digest import get_ticker_news_digest, build_news_block
            news_block = "\n\n" + build_news_block(
                get_ticker_news_digest(conn, today_str, top_n=5))
        except Exception as _ne:
            logging.warning(f"[market_health_report] news digest skipped: {_ne}")

        msg = ext_block + health + news_block
        send_telegram(msg, event="report.market_health")
        logger.info(f"[{now.strftime('%H:%M')}] Premarket briefing sent (tier={risk['tier']})")
    except Exception as e:
        logging.error(f"[market_health_report] {e}")
        logger.warning(f"[{now.strftime('%H:%M')}] Health report error: {e}")
    finally:
        conn.close()


def _premarket_approved_and_lookup(decisions: list, rows: list) -> tuple[list, dict]:
    """Firm-approved decisions sorted by confidence (desc) + a ticker→row lookup
    for source/strength tags. Shared basis for both the Telegram message and the
    watchlist snapshot so the two never disagree on order (audit 2026-07-28
    Phase 2 — mirrors engine.trade_plan.rank_approved's role for the EOD plan)."""
    by_ticker = {r["ticker"]: r for r in rows}
    approved = sorted(
        [d for d in decisions if d.decision == "approve"],
        key=lambda d: d.confidence or 0.0, reverse=True,
    )
    return approved, by_ticker


def _premarket_ranked_for_snapshot(approved: list, by_ticker: dict) -> list[dict]:
    """Build the engine.trade_plan.record_snapshot/diff_watchlist-compatible ranked
    list from the firm-approved premarket decisions — reuses the same generic
    snapshot/diff infra built for the EOD plan rather than a parallel mechanism."""
    out = []
    for d in approved:
        r = by_ticker.get(d.ticker, {})
        out.append({
            "ticker": d.ticker,
            "confidence": float(d.confidence) if d.confidence is not None else None,
            "conviction": r.get("strength"),
            "confluence": r.get("confluence"),
            "sources": r.get("sources") or [],
        })
    return out


_MAX_PREMARKET_DIFF_ROWS = 8


def _premarket_factor_note(prior_sources: Optional[list], cur_sources: Optional[list]) -> str:
    """Factual, non-invented explanation derived from the only per-ticker factor
    that actually exists at the premarket stage: which watchlist sources newly
    agree/disagree (REVERSAL/PREMOVER/BEAR_DIP). Never fabricates a momentum/
    liquidity/risk label the engine doesn't compute here."""
    prior_set, cur_set = set(prior_sources or []), set(cur_sources or [])
    gained = sorted(cur_set - prior_set)
    lost = sorted(prior_set - cur_set)
    bits = []
    if gained:
        bits.append("+" + "/".join(gained))
    if lost:
        bits.append("-" + "/".join(lost))
    return " ".join(bits)


def _build_premarket_diff_sections(diff: Optional[dict], approved_by_ticker: dict) -> list[str]:
    """NEW / REMOVED / UPGRADED / DOWNGRADED (+ optional STABLE) lines for the
    premarket shortlist. Consumes engine.trade_plan.diff_watchlist's output as-is
    (the same snapshot/diff infra the EOD plan uses) — reports on rank/confidence
    already decided elsewhere, never recomputes them. The per-move "explanation"
    is the firm's own rationale for that ticker today (already-generated engine
    output) plus the factual source-tag change, not an invented label."""
    if not diff:
        return []
    added, removed, changes = diff["added"], diff["removed"], diff["changes"]
    upgraded = [c for c in changes if c["status"] == "upgraded"]
    downgraded = [c for c in changes if c["status"] == "downgraded"]
    stable = [c for c in changes
              if c["status"] == "unchanged" and (c["confidence"] or 0) >= 0.70]
    if not added and not removed and not upgraded and not downgraded and not stable:
        return []

    L: list[str] = []
    if added:
        L += ["", "<b>📈 NEW</b>"]
        L += [f"  {html.escape(t)}" for t in added[:_MAX_PREMARKET_DIFF_ROWS]]
        if len(added) > _MAX_PREMARKET_DIFF_ROWS:
            L.append(f"  …+{len(added) - _MAX_PREMARKET_DIFF_ROWS} more")
    if removed:
        L += ["", "<b>📉 REMOVED</b>"]
        L += [f"  {html.escape(t)}" for t in removed[:_MAX_PREMARKET_DIFF_ROWS]]
        if len(removed) > _MAX_PREMARKET_DIFF_ROWS:
            L.append(f"  …+{len(removed) - _MAX_PREMARKET_DIFF_ROWS} more")

    def _render_move(c: dict) -> None:
        d = approved_by_ticker.get(c["ticker"])
        rationale = (getattr(d, "rationale", None) or "").replace("\\n", " ").strip() if d else ""
        note = _premarket_factor_note(c.get("prior_sources"), c.get("sources"))
        rank_txt = f" rank {c['prior_rank']}→{c['rank']}" if c.get("rank_change") else ""
        conf_txt = (f" conf {c['prior_confidence']:.2f}→{c['confidence']:.2f} "
                   f"({c['score_delta']:+.2f})" if c["score_delta"] is not None else "")
        line = f"  <b>{html.escape(c['ticker'])}</b>{rank_txt}{conf_txt}"
        if note:
            line += f" [{note}]"
        L.append(line)
        if rationale:
            L.append(f"    <i>{html.escape(rationale[:140])}</i>")

    if upgraded:
        L += ["", "<b>⬆ UPGRADED</b>"]
        for c in upgraded[:_MAX_PREMARKET_DIFF_ROWS]:
            _render_move(c)
    if downgraded:
        L += ["", "<b>⬇ DOWNGRADED</b>"]
        for c in downgraded[:_MAX_PREMARKET_DIFF_ROWS]:
            _render_move(c)
    if stable:
        L += ["", "<b>🟢 STABLE</b> <i>(high-conviction, unchanged)</i>"]
        L += [f"  {html.escape(c['ticker'])} conf {c['confidence']:.2f}"
             for c in stable[:_MAX_PREMARKET_DIFF_ROWS]]
    return L


def _build_premarket_firm_message(decisions: list, rows: list, header: str,
                                  regime: Optional[str] = None,
                                  risk: Optional[dict] = None,
                                  watchlist_total: Optional[int] = None,
                                  diff: Optional[dict] = None) -> str:
    """Pure Telegram-message builder for the premarket firm shortlist.

    decisions: list[AgentDecision] from firm.evaluate_staged.
    rows: the unified-watchlist long rows (dicts) used for source/strength lookup.
    header: pre-formatted "dd/mm HH:MM" string.
    regime/risk/watchlist_total: optional Daily-Summary context (market regime
    label, get_market_risk_for_circuit_breaker() dict, total unified-watchlist
    size) — each line is omitted when its value is None so old callers/tests
    that don't pass them keep getting the same message shape.
    diff: engine.trade_plan.diff_watchlist() output — adds NEW/REMOVED/
    UPGRADED/DOWNGRADED sections when present.
    Kept import-free (no langgraph) so it's unit-testable on the Windows venv.
    """
    from engine import trade_plan as tp

    approved, by_ticker = _premarket_approved_and_lookup(decisions, rows)
    approved_by_ticker = {d.ticker: d for d in approved}
    vetoed   = [d for d in decisions if d.decision == "veto"]
    passthru = [d for d in decisions if d.decision in ("degraded", "bypassed")]

    msg = f"🏁 <b>PREMARKET SUMMARY — {header}</b>\n"
    if regime:
        msg += f"Regime: <b>{html.escape(regime)}</b>\n"
    if risk:
        tier = risk.get("tier")
        score = risk.get("score")
        score_txt = f" ({score:.0f})" if score is not None else ""
        msg += f"Risk: <b>{html.escape(str(tier))}</b>{score_txt}\n"
    if watchlist_total is not None:
        msg += f"Candidates: {watchlist_total} unified → {len(decisions)} evaluated\n"
    if approved:
        top = approved[0]
        conf_txt = f"{top.confidence:.2f}" if top.confidence is not None else "N/A"
        msg += f"Highest conviction: <b>{html.escape(top.ticker)}</b> ({conf_txt})\n"
    msg += "\n"

    if approved:
        msg += "<b>⭐ TOP CONVICTIONS</b>\n"
        for d in approved:
            conf = f"{d.confidence:.2f}" if d.confidence is not None else "N/A"
            size = f" ×{d.size_hint:.2f}" if d.size_hint else ""
            srcs = by_ticker.get(d.ticker, {}).get("sources") or []
            tag = "+".join(s[0] for s in srcs)
            tag = f" [{tag}]" if tag else ""
            msg += f"  <b>{d.ticker}</b> conv {conf}{size}{tag}\n"
            if d.rationale:
                msg += f"     <i>{d.rationale[:140]}</i>\n"
    else:
        msg += "<b>✅ No firm-approved longs this morning</b>\n"

    if passthru:
        msg += "\n<b>➡️ Passed through (firm degraded/off):</b>\n"
        msg += "  " + ", ".join(d.ticker for d in passthru) + "\n"

    if vetoed:
        msg += f"\n<b>⛔ Vetoed ({len(vetoed)}):</b> " + ", ".join(d.ticker for d in vetoed) + "\n"

    p_line = tp.provider_line(decisions)
    if p_line:
        msg += "\n" + p_line + "\n"

    diff_lines = _build_premarket_diff_sections(diff, approved_by_ticker)
    if diff_lines:
        msg += "\n".join(diff_lines) + "\n"

    return msg


def _premarket_revision_section(decisions: list) -> list[str]:
    """Telegram block naming every change made to the frozen EOD base plan and
    the new information that justified it. Reporting only."""
    from engine.watchlist_ledger import (
        ACTION_ADD, ACTION_DOWNGRADE, ACTION_REMOVE, ACTION_RETAIN, ACTION_UPGRADE)
    if not decisions:
        return []
    emoji = {ACTION_RETAIN: "\u2705", ACTION_REMOVE: "\u274c",
             ACTION_ADD: "\U0001f195", ACTION_UPGRADE: "\u2b06",
             ACTION_DOWNGRADE: "\u2b07"}
    changed = [d for d in decisions if d.action != ACTION_RETAIN]
    retained = [d for d in decisions if d.action == ACTION_RETAIN]
    lines = ["", "<b>\U0001f504 REVISION OF THE EOD BASE PLAN</b>"]
    if not changed:
        lines.append(f"  No overnight information changed the plan "
                     f"({len(retained)} retained).")
        return lines
    for d in changed[:10]:
        lines.append(f"  {emoji.get(d.action, '')} <b>{html.escape(d.ticker)}</b> "
                     f"{d.action} — {html.escape(d.reason[:130])}")
    if len(changed) > 10:
        lines.append(f"  … +{len(changed) - 10} more")
    if retained:
        lines.append(f"  \u2705 Retained unchanged: "
                     + ", ".join(html.escape(d.ticker) for d in retained[:12]))
    return lines


def run_premarket_firm_scan():
    """08:35 WIB — REVISE the frozen EOD base plan using overnight information.

    REBUILT 2026-09-02 (audit findings A-1 / A-2). This job used to call
    build_unified_watchlist() and construct an entirely separate candidate
    universe from REVERSAL / PREMOVER / BEAR_DIP, while the EOD plan merged
    R / S / V / P. The two vocabularies are disjoint; across 17 consecutive
    EOD -> premarket transitions only four tickers ever carried over. Two
    independent samples cannot answer "did the premarket revision improve the
    EOD plan?" -- the question was unanswerable by construction.

    The job is now a revision operator:

        frozen EOD plan (previous session)
          + information that did not exist at 16:40  (news, settled broker flow,
            corporate actions, VPIN, reconciled prices, market risk tier)
          -> RETAIN / REMOVE / UPGRADE / DOWNGRADE / ADD, each with a recorded
             reason and its evidence
          -> Agent Firm vetting of the survivors
          -> frozen premarket plan

    The Agent Firm vets; it never promotes. LLM approval is not evidence of
    alpha and does not change a candidate's strategy attribution or its OOS
    record.

    This is Run 2 of the strict 2-invocations-per-trading-day Agent Firm
    contract (engine.agent_firm_daily, 2026-09-15): before vetting, survivors
    are intersected with the EXACT ticker set run_eod_trade_plan() selected
    and persisted the previous evening (engine.agent_firm_daily.load_plan()) —
    this job never re-selects or widens that set. Vetting is EXACTLY ONE agent-
    firm evaluation of that (already-intersected) survivor set; if the intersection
    is empty (nothing selected last night, or every selected ticker was removed
    by the revision engine), no LLM call is made at all.
    engine.agent_firm_daily.begin_run()/finish_run() make a same-session retry
    never re-bill the firm, and record whether the revision engine found a
    material change for any selected ticker (plan_changed).
    """
    if _holiday_skip("run_premarket_firm_scan"):
        handle = current_job()
        if handle:
            handle.mark_skipped("holiday")
        return
    from engine.liquidity import select_top_liquid_longs
    from engine.agent_firm import firm as _firm
    from engine.agent_firm.schemas import SignalCandidate as _SC
    from engine import premarket_revision as _rev
    from engine import trade_plan as tp
    from engine import watchlist_ledger as _wl

    now = datetime.now(WIB)
    now_str = now.strftime('%H:%M')
    date_str = now.strftime('%Y-%m-%d')

    # Dedup guard — first INSERT wins; a systemd restart race never double-sends.
    with db_connect(DB_PATH, timeout=5) as _g:
        _g.execute(
            "CREATE TABLE IF NOT EXISTS _job_sentinel "
            "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))"
        )
        try:
            _g.execute("INSERT INTO _job_sentinel VALUES ('premarket_firm', ?)", (date_str,))
        except sqlite3.IntegrityError:
            logger.info(f"[{now_str}] Premarket firm: already sent today — skipped (duplicate guard)")
            handle = current_job()
            if handle:
                handle.mark_skipped("duplicate_run")
            return
        except sqlite3.OperationalError as e:
            logger.warning(f"[{now_str}] Premarket firm: dedup guard error (fail-open): {e}")
            handle = current_job()
            if handle:
                handle.mark_skipped(f"dedup_guard_error: {e}")
            return

    logger.info(f"[{now_str}] Premarket revision of the EOD base plan starting...")

    # Long-lived process: drop admission's rule-study cache so evidence written
    # since the last cycle is visible (see scheduler/scanner.py for the rationale).
    try:
        from engine.admission import reset_evidence_cache as _reset_adm_cache
        _reset_adm_cache()
    except Exception:
        pass

    # ── 1. Load the frozen EOD base plan ─────────────────────────────────────
    conn = db_connect(DB_PATH)
    try:
        base = _wl.base_plan(conn, date_str, _wl.STRATEGY_EOD)
    finally:
        conn.close()
    base_status, base_date, base_rows = base["status"], base["date"], base["rows"]

    # P-2: EMPTY_PLAN and NO_EOD_SNAPSHOT are different facts and must not be
    # collapsed. EMPTY_PLAN is a real prediction the engine made -- it ran and
    # deliberately approved nobody -- and revising it correctly yields an empty
    # premarket plan. NO_EOD_SNAPSHOT is an operational fault (job never ran, DB
    # restored, first day) and is reported as one.
    if base_status == _wl.BASE_MISSING:
        logger.warning(f"[{now_str}] Premarket: NO_EOD_SNAPSHOT — no EOD publication "
                       f"exists at all. This is an operational fault, not an empty "
                       f"plan; premarket is a revision of EOD by design.")
        send_telegram(
            f"\u26a0\ufe0f <b>PREMARKET — {now.strftime('%d/%m %H:%M')}</b>\n\n"
            f"<b>NO_EOD_SNAPSHOT</b> — no EOD publication found in "
            f"<code>watchlist_publication</code>, so there is nothing to revise.\n\n"
            f"This is not the same as an empty plan: the EOD job appears not to "
            f"have published at all. Check the 16:40 job."
        , event="data.premarket_no_snapshot")
        return

    if base_status == _wl.BASE_EMPTY:
        logger.info(f"[{now_str}] Premarket: EMPTY_PLAN — EOD {base_date} "
                    f"(revision {base['revision']}) published zero approved "
                    f"candidates. Revising an empty plan yields an empty plan.")
    else:
        logger.info(f"[{now_str}] Base plan {base_date}: {len(base_rows)} candidate(s)")

    # ── 2. Market context that is itself new information ─────────────────────
    _risk = None
    try:
        _risk = get_market_risk_for_circuit_breaker()
    except Exception as e:
        logging.warning(f"[premarket_firm] risk lookup error (fail-soft): {e}")

    regime = None
    try:
        from engine.edge_enrich import market_regime as _market_regime
        _rconn = db_connect(DB_PATH)
        try:
            regime = _market_regime(_rconn)
        finally:
            _rconn.close()
    except Exception as e:
        logging.warning(f"[premarket_firm] regime lookup error (fail-soft): {e}")

    # ── 3. Revise ────────────────────────────────────────────────────────────
    # Discovery-sourced ADDs are OFF by default: REVERSAL / PREMOVER / BEAR_DIP
    # are all written at 16:15-16:30, BEFORE the EOD job ran, so a name found
    # there is not new information -- it is the same evening's data re-read.
    _allow_adds = os.getenv("PREMARKET_ALLOW_DISCOVERY_ADDS", "false").strip().lower() in ("1", "true", "yes")
    discoveries = []
    if _allow_adds:
        try:
            from engine.unified_watchlist import build_unified_watchlist
            discoveries = [r for r in build_unified_watchlist(DB_PATH)
                           if (r.get("direction") or "long").lower() == "long"]
        except Exception as e:
            logging.warning(f"[premarket_firm] discovery source error (fail-soft): {e}")

    conn = db_connect(DB_PATH)
    try:
        decisions_rev = _rev.revise(
            conn, base_rows, base_date=base_date, plan_date=date_str,
            market_risk=_risk, market_regime=regime,
            discoveries=discoveries, allow_discovery_adds=_allow_adds)
        survivors = _rev.apply(decisions_rev)

        # ── 4. Liquidity is an execution constraint, and a RECORDED one ──────
        # It used to silently discard everything outside the top 3, which made
        # the surviving cohort conditioned on an unobservable filter (audit,
        # question 10). Every drop is now a REMOVE decision with a reason.
        if survivors:
            liquid = select_top_liquid_longs(survivors, conn, date_str,
                                             top_n=max(3, len(survivors)))
            keep = {r["ticker"] for r in liquid}
            for r in survivors:
                if r["ticker"] not in keep:
                    decisions_rev.append(_rev.RevisionDecision(
                        r["ticker"], _wl.ACTION_REMOVE, "illiquid",
                        "below the 30d average-daily-traded-value floor at "
                        "premarket", {"filter": "select_top_liquid_longs"}, r))
            survivors = [r for r in survivors if r["ticker"] in keep]

        _wl.record_revisions(conn, date_str, base_date, [d.as_dict() for d in decisions_rev])
    finally:
        conn.close()

    n_removed = sum(1 for d in decisions_rev if d.action == _wl.ACTION_REMOVE)
    logger.info(f"[{now_str}] Revision: {len(survivors)} survive of {len(base_rows)} "
                f"base candidates ({n_removed} removed)")

    # ── 4b. Enforce the strict daily ticker boundary ─────────────────────────
    # Run 2 targets ONLY the ticker set Run 1 (post_close) selected and stored —
    # it never re-selects or widens the pool (engine.agent_firm_daily contract).
    from engine import agent_firm_daily as _afd
    with db_connect(DB_PATH) as _plan_conn:
        _daily_plan = _afd.load_plan(_plan_conn, date_str)
    _selected_tickers = {p["ticker"] for p in _daily_plan}
    if not _selected_tickers:
        logger.info(f"[{now_str}] Premarket firm: no post-close plan found for {date_str} "
                    f"— nothing to adjust, skipping LLM review")
        survivors = []
    else:
        _outside = [r["ticker"] for r in survivors if r["ticker"] not in _selected_tickers]
        if _outside:
            logger.info(f"[{now_str}] Premarket firm: {len(_outside)} EOD survivor(s) outside "
                        f"the post-close selected set excluded from LLM review: {_outside}")
        survivors = [r for r in survivors if r["ticker"] in _selected_tickers]

    # ── 5. Agent Firm vetting of the survivors (vetting, never promotion) ────
    from engine.agent_firm_context import build_candidate_context, reset_batch_context
    _firm.reset_market_ctx()
    reset_batch_context()
    _ctx_by_ticker = {}
    if survivors:
        try:
            _ctx_conn = db_connect(DB_PATH)
            try:
                for r in survivors:
                    _ctx_by_ticker[r["ticker"]] = build_candidate_context(
                        _ctx_conn, r["ticker"], date_str,
                        market_risk_score=(_risk or {}).get("score"),
                    )
            finally:
                _ctx_conn.close()
        except Exception as _ctx_err:
            logging.warning(f"[premarket_firm] context build error (fail-open, "
                            f"candidates proceed without Tier 1 context): {_ctx_err}")

    candidates = [
        _SC(
            ticker=r["ticker"],
            strategy="premarket",
            score=float(r.get("conviction") or r.get("confidence") or 0.0),
            scan_time=f"{date_str} {now_str}",
            flow_verdict=None,
            foreign_score=None,
            indicators={"sources": r.get("sources", []),
                        "confluence": r.get("confluence", False),
                        "revision_action": r.get("revision_action"),
                        "revision_reason": r.get("revision_reason"),
                        "base_strategy": r.get("strategy_fn")},
            **_ctx_by_ticker.get(r["ticker"], {}),
        )
        for r in survivors
    ]

    decisions = []
    if candidates:
        # Strict 2-invocations-per-trading-day contract: this is Run 2
        # (premarket). session_date matches Run 1's — the plan Run 1 produced
        # FOR today is exactly what this run adjusts.
        _tickers = [c.ticker for c in candidates]
        with db_connect(DB_PATH) as _guard_conn:
            _guard = _afd.begin_run(_guard_conn, date_str, _afd.RUN_PREMARKET, _tickers)
        if not _guard.should_call:
            # A SUCCESS already exists for this session (defense-in-depth backstop
            # — the _job_sentinel dedup guard above normally catches this first).
            # Never re-bill the firm for the same session.
            logger.info(f"[{now_str}] Premarket firm: LLM already ran for session "
                        f"{date_str} — skipping duplicate invocation")
            return
        try:
            decisions = _firm.evaluate_staged(candidates)
            # plan_changed: did the pre-firm revision engine find any material
            # change for a selected ticker (anything but RETAIN)? This is the
            # same materiality signal engine.premarket_revision already computed
            # from overnight news/flow/corp-actions — reused, not recomputed.
            _changed_tickers = {
                d.ticker for d in decisions_rev
                if d.ticker in _selected_tickers and d.action != _wl.ACTION_RETAIN
            }
            with db_connect(DB_PATH) as _guard_conn:
                _afd.finish_run(
                    _guard_conn, _guard.run_id, status="success",
                    provider=",".join(sorted({p for d in decisions for p in d.providers_used})) or None,
                    reason=f"{len(_tickers)} candidate(s) reviewed",
                    result={d.ticker: d.decision for d in decisions},
                    plan_changed=bool(_changed_tickers),
                )
                _afd.persist_plan(_guard_conn, date_str, survivors, decisions,
                                  source=_afd.RUN_PREMARKET)
        except Exception as e:
            logging.error(f"[premarket_firm] firm eval error: {e}")
            logger.warning(f"[{now_str}] Premarket firm eval error: {e}")
            with db_connect(DB_PATH) as _guard_conn:
                _afd.finish_run(_guard_conn, _guard.run_id, status="failed", reason=str(e))
            return

    # ── 6. Publish the revised, frozen premarket plan ────────────────────────
    approved, by_ticker = _premarket_approved_and_lookup(decisions, survivors)
    ranked = _premarket_ranked_for_snapshot(approved, by_ticker)
    # carry the base plan's attribution and evidence forward onto the published
    # rows so the premarket record is traceable to the EOD row it revised
    _base_by_ticker = {r["ticker"]: r for r in survivors}
    for row in ranked:
        src = _base_by_ticker.get(row["ticker"], {})
        for k in ("strategy_fn", "provenance", "revision_action",
                  "revision_reason_code", "revision_reason"):
            if src.get(k) is not None:
                row[k] = src[k]
        prov = dict(row.get("provenance") or {})
        prov["base_plan_date"] = base_date
        row["provenance"] = prov

    diff = None
    with db_connect(DB_PATH) as _snap_conn:
        try:
            ranked = tp.attach_provenance(_snap_conn, ranked, date_str,
                                          plan="premarket")
        except Exception as e:
            logging.warning(f"[premarket_firm] provenance stamp failed (fail-soft): {e}")
        try:
            diff = tp.diff_watchlist(_snap_conn, date_str, "premarket", ranked)
            tp.record_snapshot(_snap_conn, date_str, "premarket", ranked)
        except Exception as e:
            logging.warning(f"[premarket_firm] watchlist snapshot/diff error (fail-soft): {e}")

    try:
        msg = _build_premarket_firm_message(
            decisions, survivors, now.strftime('%d/%m %H:%M'),
            regime=regime, risk=_risk, watchlist_total=len(base_rows), diff=diff)
        msg += "\n".join(_premarket_revision_section(decisions_rev)) + "\n"
        msg += (f"\n<i>Base plan: EOD {base_date} [{base_status}] "
                f"({len(base_rows)} candidates) \u2192 {len(survivors)} after "
                f"revision. Discovery adds: "
                f"{'on' if _allow_adds else 'off'}.</i>")
        send_telegram(msg, event="report.premarket_summary")
    except Exception as e:
        logger.warning(f"[premarket firm] Telegram error: {e}")

    n_app = sum(1 for d in decisions if d.decision == "approve")
    n_veto = sum(1 for d in decisions if d.decision == "veto")
    logger.info(f"[{now_str}] Premarket revision: base={len(base_rows)} "
                f"survivors={len(survivors)} evaluated={len(decisions)} "
                f"({n_app} approve, {n_veto} veto)")


def run_eod_trade_plan():
    """16:40 WIB — single consolidated, agent-ranked trade plan for the next session.

    This is Run 1 of the strict 2-invocations-per-trading-day Agent Firm contract
    (engine.agent_firm_daily, 2026-09-15): merges every long signal source
    (reversal watchlist + bullish/volume screen + today's premarket approvals)
    into one pool, caps it at MAX_DAILY_TICKERS (3, or fewer if fewer qualify —
    was 8 before this change) by confluence, sends that set through EXACTLY ONE
    agent-firm evaluation, and persists the result as the canonical plan for the
    next trading session — engine.agent_firm_daily.begin_run()/finish_run() make
    a same-session retry never re-bill the firm. run_premarket_firm_scan() reads
    this SAME ticker set back the next morning; it never re-selects. Sends ONE
    Telegram message with firm-APPROVED longs only. Shorts are intentionally
    excluded — they are exit/SL triggers, not entries.

    Runs after the 16:15 screener EOD (reversal watchlist) and 16:30 premover scan so
    all source tables are settled. Fail-open: if the firm is disabled or errors, falls
    back to deterministic confluence ranking (report flagged ⚠️ Firm offline).
    """
    if _holiday_skip("run_eod_trade_plan"):
        handle = current_job()
        if handle:
            handle.mark_skipped("holiday")
        return
    from engine import trade_plan as tp
    from engine import agent_firm_daily as _afd
    from engine.agent_firm import firm as _firm
    from engine.agent_firm.schemas import SignalCandidate as _SC

    now = datetime.now(WIB)
    now_str = now.strftime('%H:%M')
    date_str = now.strftime('%Y-%m-%d')

    # Dedup guard (mirrors premarket firm scan) — first INSERT wins. 30s busy_timeout
    # waits out transient writers (the 16:40 slot can overlap a long EOD write on the
    # 2.5GB WAL db, unlike the quiet 08:35 premarket slot). Also fails open on
    # OperationalError (RC1 F-3, 2026-07-28) — the 16:40 slot is more exposed to
    # exactly the lock-contention window that caused the 2026-07-24 08:35:30
    # premarket crash, so it gets the same guard premarket was patched with.
    with db_connect(DB_PATH) as _g:
        _g.execute("CREATE TABLE IF NOT EXISTS _job_sentinel "
                   "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))")
        try:
            _g.execute("INSERT INTO _job_sentinel VALUES ('eod_trade_plan', ?)", (date_str,))
        except sqlite3.IntegrityError:
            logger.info(f"[{now_str}] EOD trade plan: already sent today — skipped (dup guard)")
            handle = current_job()
            if handle:
                handle.mark_skipped("duplicate_run")
            return
        except sqlite3.OperationalError as e:
            logger.warning(f"[{now_str}] EOD trade plan: dedup guard error (fail-open): {e}")
            handle = current_job()
            if handle:
                handle.mark_skipped(f"dedup_guard_error: {e}")
            return

    from config import edge_mode

    conn = db_connect(DB_PATH)
    try:
        cands = tp.gather_long_candidates(conn, date_str)
        regime = tp.get_regime(conn, date_str)
        # 2026-09-15: capped at MAX_DAILY_TICKERS (3), not 8 — the strict
        # 2-invocations-per-trading-day contract (engine.agent_firm_daily) sends
        # this SAME ticker set to exactly one post-close and one premarket LLM
        # call; it does not re-rank or widen the pool itself.
        top = tp.select_top(cands, n=_afd.MAX_DAILY_TICKERS) if cands else []

        # Tier A directional pre-screen BEFORE the firm (gated by EDGE_SCORE_MODE):
        # drops directionally-dead candidates so they never cost an LLM call.
        # shadow → log only; enforce → actually filter; off → skip.
        if top and edge_mode() != 'off':
            from engine.edge_enrich import market_regime as _market_regime
            _mreg = _market_regime(conn)
            survivors, vetoed = tp.edge_prescreen(conn, top, _mreg, date_str)
            logging.info(f"[{now_str}] EOD edge pre-screen ({edge_mode()}, market={_mreg}): "
                         f"{len(survivors)}/{len(top)} survive; vetoed={vetoed}")
            if edge_mode() == 'enforce':
                top = survivors

        # VPIN gate: fetch most recently settled market VPIN summary (VPIN batch runs
        # at 18:00, after this job at 16:40, so today's data may not exist yet).
        vpin_summary = tp.get_vpin_gate(conn, date_str)
        if vpin_summary:
            logging.info(f"[{now_str}] EOD VPIN gate: {vpin_summary['label']} "
                         f"(avg={vpin_summary.get('avg_vpin')}, date={vpin_summary.get('date')})")
    finally:
        conn.close()

    # Additive: standalone pre-firm candidate Watchlist Update report. Snapshots
    # `cands` — the full merged long-candidate universe BEFORE select_top/firm
    # review — distinct from tp.record_snapshot's post-approval "eod" strategy
    # snapshot below. Reporting-only: reads already-computed candidates/regime,
    # never feeds back into candidate generation or firm evaluation. Rides the
    # dedup guard above (one run per calendar day), so it's restart-safe and
    # never double-sends.
    try:
        from engine import watchlist_report as wr
        reasons = {c["ticker"]: c["reason"] for c in cands if c.get("reason")}
        with db_connect(DB_PATH) as _wl_conn:
            wl_diff = wr.diff_snapshot(_wl_conn, date_str, cands)
            wr.record_snapshot(_wl_conn, date_str, cands, regime=regime[0])
        send_telegram(wr.build_message(date_str, wl_diff, len(cands), reasons=reasons),
                      event="report.watchlist_update")
    except Exception as e:
        logging.warning(f"[eod_trade_plan] watchlist update report error (fail-soft): {e}")

    if not cands:
        logger.info(f"[{now_str}] EOD trade plan: no long candidates — skipped")
        return

    if not top:
        # every candidate failed the directional pre-screen — ship an empty plan
        diff = None
        with db_connect(DB_PATH) as _snap_conn:
            try:
                diff = tp.diff_watchlist(_snap_conn, date_str, "eod", [])
                # An empty plan is still a published prediction and must be
                # recorded as a revision in the append-only ledger (audit F-1).
                tp.record_snapshot(_snap_conn, date_str, "eod", [])
            except Exception as e:
                logging.warning(f"[eod_trade_plan] watchlist snapshot/diff error (fail-soft): {e}")

        # Additive: persistent multi-day active-watchlist section, appended to
        # the SAME message below (never a second send_telegram call) -- see
        # the identical hook in the main path further down for the full
        # rationale. Own connection + own try/except so a bug here can never
        # block the existing empty-plan message.
        pw_section = ""
        try:
            from engine import persistent_watchlist as pw
            with db_connect(DB_PATH) as _pw_conn:
                pw_result = pw.update_watchlist(_pw_conn, date_str, set())
            pw_section = "\n\n" + pw.build_message(date_str, pw_result)
        except Exception as e:
            logging.warning(f"[eod_trade_plan] persistent watchlist error (fail-soft): {e}")

        send_telegram(tp.build_message([], regime, now.strftime('%d/%m'), degraded=False,
                                       vpin_summary=vpin_summary, diff=diff,
                                       watchlist_size=len(cands)) + pw_section,
                      event="report.eod_trade_plan_empty")
        logger.info(f"[{now_str}] EOD trade plan: all candidates vetoed by edge pre-screen — empty plan sent")
        return

    # AF-2 WP4: this job's own run is its "scan cycle" for Tier 1 context purposes —
    # see run_premarket_firm_scan()'s identical comment for why both caches are
    # flushed here rather than relying on scheduled_multi_strategy_scan()'s reset.
    _risk = None
    try:
        _risk = get_market_risk_for_circuit_breaker()
    except Exception as e:
        logging.warning(f"[eod_trade_plan] risk lookup error (fail-soft): {e}")

    from engine.agent_firm_context import build_candidate_context, reset_batch_context
    _firm.reset_market_ctx()
    reset_batch_context()
    _ctx_by_ticker = {}
    try:
        _ctx_conn = db_connect(DB_PATH)
        try:
            for c in top:
                _ctx_by_ticker[c["ticker"]] = build_candidate_context(
                    _ctx_conn, c["ticker"], date_str,
                    market_risk_score=(_risk or {}).get("score"),
                )
        finally:
            _ctx_conn.close()
    except Exception as _ctx_err:
        logging.warning(f"[eod_trade_plan] context build error (fail-open, "
                        f"candidates proceed without Tier 1 context): {_ctx_err}")

    candidates = [
        _SC(ticker=c["ticker"], strategy="eod", score=float(c["conviction"] or 0.0),
            scan_time=f"{date_str} {now_str}", flow_verdict=c.get("smart_money"),
            indicators={"sources": c["sources"], "confluence": c["confluence"],
                        "vol_ratio": c["vol_ratio"], "net_value": c["net_value"]},
            **_ctx_by_ticker.get(c["ticker"], {}))
        for c in top
    ]

    # Strict 2-invocations-per-trading-day contract: this is Run 1 (post_close).
    # session_date is the NEXT trading session — the plan this run produces is
    # FOR that session, and Run 2 (premarket, run_premarket_firm_scan) looks up
    # its ticker set under that same session_date the following morning.
    session_date = _afd.next_trading_session(now.date()).isoformat()
    _tickers = [c["ticker"] for c in top]
    with db_connect(DB_PATH) as _guard_conn:
        _guard = _afd.begin_run(_guard_conn, session_date, _afd.RUN_POST_CLOSE, _tickers)

    degraded = False
    if not _guard.should_call:
        # A SUCCESS already exists for this session (defense-in-depth backstop —
        # the _job_sentinel dedup guard above normally catches this first). Never
        # re-bill the firm for the same session; skip straight to reporting with
        # a deterministic fallback rank, exactly like a firm-disabled run.
        logger.info(f"[{now_str}] EOD trade plan: post-close LLM already ran for "
                    f"session {session_date} — skipping duplicate invocation")
        decisions = []
        ranked, degraded = tp.fallback_rank(top), True
    else:
        try:
            decisions = _firm.evaluate_staged(candidates)
            firm_ran = any(d.decision in ("approve", "veto") for d in decisions)
            if firm_ran:
                ranked = tp.rank_approved(top, decisions)
            else:
                ranked, degraded = tp.fallback_rank(top), True   # firm disabled/bypassed
            with db_connect(DB_PATH) as _guard_conn:
                _afd.finish_run(
                    _guard_conn, _guard.run_id, status="success",
                    provider=",".join(sorted({p for d in decisions for p in d.providers_used})) or None,
                    reason=f"{len(_tickers)} candidate(s) selected",
                    result={d.ticker: d.decision for d in decisions},
                )
                _afd.persist_plan(_guard_conn, session_date, top, decisions,
                                  source=_afd.RUN_POST_CLOSE)
        except Exception as e:
            logging.error(f"[eod_trade_plan] firm eval error (fail-open): {e}")
            ranked, degraded = tp.fallback_rank(top), True
            with db_connect(DB_PATH) as _guard_conn:
                _afd.finish_run(_guard_conn, _guard.run_id, status="failed", reason=str(e))

    # `degraded=True` on every path where `decisions` could be unbound (the
    # except block above never assigns it) — this guard also avoids
    # UnboundLocalError, not just suppressing a stale provider line.
    p_line = None if degraded else tp.provider_line(decisions)

    # Persist today's ranked watchlist + diff against the prior snapshot so the
    # report can show added/removed/upgraded/downgraded/rank+score deltas.
    # Reporting only — never feeds back into ranking/decisions.
    diff = None
    with db_connect(DB_PATH) as _snap_conn:
        try:
            # Stamp strategy attribution, OOS evidence, decision price and
            # entry rule before publishing, so the frozen base plan can be
            # forward-tested and explained without retrospective price lookup
            # (audit F-1). Fail-soft: provenance must never block the report.
            try:
                ranked = tp.attach_provenance(_snap_conn, ranked, date_str,
                                              plan="eod")
            except Exception as _pe:
                logging.warning(f"[eod_trade_plan] provenance stamp failed "
                                f"(fail-soft): {_pe}")
            diff = tp.diff_watchlist(_snap_conn, date_str, "eod", ranked)
            tp.record_snapshot(_snap_conn, date_str, "eod", ranked)
        except Exception as e:
            logging.warning(f"[eod_trade_plan] watchlist snapshot/diff error (fail-soft): {e}")

    # Additive: persistent multi-day active-watchlist section (engine.
    # persistent_watchlist), appended to the END of the SAME Trade Plan
    # message below -- distinct from the standalone pre-firm
    # watchlist_report message above (that one is its OWN send_telegram
    # call); this one is text concatenated onto tp.build_message()'s
    # existing output, per spec: "Do not remove or reorder the existing
    # Trade Plan section." Own connection + own try/except so a bug here
    # can never block the existing Trade Plan message; today's APPROVED
    # tickers (`ranked`) are exactly what drives the persistent state.
    pw_section = ""
    try:
        from engine import persistent_watchlist as pw
        with db_connect(DB_PATH) as _pw_conn:
            pw_result = pw.update_watchlist(
                _pw_conn, date_str, {c["ticker"] for c in ranked})
        pw_section = "\n\n" + pw.build_message(date_str, pw_result)
    except Exception as e:
        logging.warning(f"[eod_trade_plan] persistent watchlist error (fail-soft): {e}")

    try:
        send_telegram(tp.build_message(ranked, regime, now.strftime('%d/%m'),
                                       degraded=degraded, vpin_summary=vpin_summary,
                                       provider_line=p_line, diff=diff,
                                       watchlist_size=len(cands)) + pw_section,
                      event="report.eod_trade_plan")
    except Exception as e:
        logger.warning(f"[eod_trade_plan] Telegram error: {e}")

    logger.info(f"[{now_str}] EOD trade plan: {len(cands)} candidates, top {len(top)} vetted, "
          f"{len(ranked)} approved{' (degraded)' if degraded else ''}")


def ensure_vpin_scores_table(conn):
    """Create vpin_scores table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vpin_scores (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            vpin REAL,
            vpin_label TEXT,
            bucket_count INTEGER,
            error TEXT,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.commit()


def run_vpin_daily_batch(date_str=None):
    """Compute VPIN for all tickers on a given date and persist to vpin_scores.

    Runs independently of screener_jobs.py. Also updates daily_screen.vpin
    for any tickers that don't yet have a value.
    Returns {'computed': int, 'errors': int, 'date': str}.
    """
    from engine.vpin import calc_vpin as _calc_vpin
    if date_str is None:
        date_str = datetime.now(WIB).strftime('%Y-%m-%d')

    now_str = datetime.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] VPIN batch compute starting for {date_str}...")

    tickers = get_all_tickers()
    computed = 0
    errors = 0

    try:
        conn = db_connect(DB_PATH)
        ensure_vpin_scores_table(conn)
    except Exception as _e:
        logging.error(f"[vpin_batch] DB init error: {_e}")
        return {'computed': 0, 'errors': 0, 'date': date_str}

    for ticker in tickers:
        try:
            r = _calc_vpin(conn, ticker, date_str)
            conn.execute(
                "INSERT OR REPLACE INTO vpin_scores "
                "(ticker, date, vpin, vpin_label, bucket_count, error) VALUES (?,?,?,?,?,?)",
                (ticker, date_str, r.get('vpin'), r.get('vpin_label', 'N/A'),
                 r.get('bucket_count', 0), r.get('error')),
            )
            if r.get('vpin') is not None:
                conn.execute(
                    "UPDATE daily_screen SET vpin=?, vpin_label=? WHERE date=? AND ticker=?",
                    (r['vpin'], r.get('vpin_label', ''), date_str, ticker),
                )
                computed += 1
        except Exception as _e:
            logging.warning(f"[vpin_batch] {ticker} error: {_e}")
            errors += 1

    conn.commit()
    conn.close()

    logger.warning(f"[{now_str}] VPIN batch done: {computed} computed, {errors} errors")
    return {'computed': computed, 'errors': errors, 'date': date_str}


def run_vpin_backfill(days=90):
    """Backfill vpin_scores for the past N days from existing daily_screen data.

    Skips dates where vpin_scores already has data. Uses dates from
    daily_screen (which has OHLCV and tick coverage), not calendar dates.
    """
    from engine.vpin import calc_vpin as _calc_vpin
    now_str = datetime.now(WIB).strftime('%H:%M')
    logger.info(f"[{now_str}] VPIN backfill starting ({days} days)...")

    try:
        conn = db_connect(DB_PATH)
        ensure_vpin_scores_table(conn)

        # Get dates that have daily_screen data but may not have vpin_scores
        cutoff = datetime.now(WIB).strftime('%Y-%m-%d')
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT date FROM daily_screen "
            "WHERE date <= ? ORDER BY date ASC",
            (cutoff,),
        ).fetchall()][-days:]

        tickers = get_all_tickers()
        total_computed = 0
        total_errors = 0

        for date_str in dates:
            already = {r[0] for r in conn.execute(
                "SELECT ticker FROM vpin_scores WHERE date=? AND vpin IS NOT NULL",
                (date_str,),
            ).fetchall()}
            remaining = [t for t in tickers if t not in already]
            if not remaining:
                continue

            for ticker in remaining:
                try:
                    r = _calc_vpin(conn, ticker, date_str)
                    conn.execute(
                        "INSERT OR IGNORE INTO vpin_scores "
                        "(ticker, date, vpin, vpin_label, bucket_count, error) VALUES (?,?,?,?,?,?)",
                        (ticker, date_str, r.get('vpin'), r.get('vpin_label', 'N/A'),
                         r.get('bucket_count', 0), r.get('error')),
                    )
                    if r.get('vpin') is not None:
                        total_computed += 1
                except Exception:
                    total_errors += 1

            conn.commit()

        conn.close()
        logger.warning(f"[{now_str}] VPIN backfill done: {total_computed} computed, {total_errors} errors")
        return {'computed': total_computed, 'errors': total_errors, 'dates': len(dates)}
    except Exception as _e:
        logging.error(f"[vpin_backfill] error: {_e}")
        return {'computed': 0, 'errors': 0, 'dates': 0}


def run_forward_test_cycle(db_path=None, run_date=None):
    """Nightly SHADOW forward-test cycle: ingest today's signals + exit-pass open positions.

    Fail-soft: logs and returns on any error so a bad cycle never takes down the
    scheduler. db_path / run_date are injectable for tests; in production both
    default (DB_PATH and today in WIB).
    """
    from forward_testing.storage.db import init_ft_tables
    from forward_testing.storage.repo import FTRepo
    from forward_testing.adapters.signal_adapter import SignalAdapter
    from forward_testing.adapters.watchlist_adapter import WatchlistAdapter
    from forward_testing.positions.market_data import MarketDataResolver
    from forward_testing.positions.exit_policy import ExitPolicyRegistry
    from forward_testing.positions.shadow_manager import ShadowPositionManager
    from forward_testing.lifecycle.manager import LifecycleManager
    from forward_testing.positions.costs import Costs

    db = db_path or DB_PATH
    rd = run_date or datetime.now(WIB).strftime("%Y-%m-%d")
    try:
        # Dedup guard (mirrors premarket/EOD) — first INSERT wins, so a systemd
        # restart racing APScheduler never sends the Telegram report twice for
        # the same run_date. Placed inside this function's own try/except
        # (unlike the other two jobs) because run_forward_test_cycle's contract
        # is to never raise on any error, including a broken db_path.
        with db_connect(db) as _g:
            _g.execute("CREATE TABLE IF NOT EXISTS _job_sentinel "
                       "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))")
            try:
                _g.execute("INSERT INTO _job_sentinel VALUES ('forward_test_cycle', ?)", (rd,))
            except sqlite3.IntegrityError:
                logger.info(f"[forward_test] {rd}: already ran — skipped (dedup guard)")
                handle = current_job()
                if handle:
                    handle.mark_skipped("duplicate_run")
                return

        init_ft_tables(db)
        repo = FTRepo(db)

        # Pre-registered forward-test windows (audit blocker #5). Verifies the
        # frozen configuration each cohort is being measured under still holds;
        # a change closes the window as CONTAMINATED and opens a successor, so
        # results either side are never pooled. Fail-soft: window bookkeeping
        # must never take down the cycle.
        try:
            from engine import forward_window as _fw
            with db_connect(db) as _wc:
                _win = _fw.check_all(_wc, event_date=rd)
            for _c, _r in _win.items():
                if _r["action"] == "rolled":
                    logger.warning(
                        f"[forward_test] {_c}: configuration changed mid-window — "
                        f"cohort closed as CONTAMINATED, successor opened. "
                        f"Changes: {_r['changes'][:5]}")
                elif _r["action"] == "opened":
                    logger.info(f"[forward_test] {_c}: forward-test window opened "
                                f"{_r['window']['window_id'][:8]} "
                                f"@{_r['window']['config_hash']}")
        except Exception as _fw_err:
            logger.warning(f"[forward_test] window check error (fail-soft): {_fw_err}")

        def _trade_count():
            with db_connect(db) as c:
                return c.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]

        open_before = len(repo.get_open_shadow_positions())
        trades_before = _trade_count()

        n_ingested = SignalAdapter(repo, db).ingest(rd)
        # AUDIT F-1: the EOD and Premarket plans are what the operator actually
        # acts on, and until 2026-09-02 neither was forward-tested at all. They
        # ingest as their own cohorts ('eod', 'premarket') and are never pooled
        # with the scanner's — the whole point is to compare them.
        try:
            n_ingested += WatchlistAdapter(repo, db).ingest(rd)
        except Exception as _wa_err:
            logger.warning(f"[forward_test] watchlist ingest error (fail-soft): {_wa_err}")
        mgr = ShadowPositionManager(
            repo, MarketDataResolver(db), ExitPolicyRegistry(),
            LifecycleManager(repo), db, costs=Costs(),
        )
        mgr.run(rd)

        open_after = len(repo.get_open_shadow_positions())
        closed = _trade_count() - trades_before
        opened = (open_after - open_before) + closed
        logger.info(f"[{datetime.now(WIB).strftime('%H:%M')}] Forward-test cycle {rd}: "
              f"ingested={n_ingested} opened={opened} closed={closed} open_now={open_after}")

        # Telegram reporting layer — reads back what the cycle above just wrote/
        # already held; never recomputes a decision or exit level. Reporting
        # errors must not mask a successful cycle, so this is its own try/except.
        try:
            from forward_testing.reporting import build_forward_test_report
            _ft_msg = build_forward_test_report(db, rd, repo=repo)
            send_telegram(_ft_msg, event="report.forward_test",
                          state=_ft_msg[:150])
        except Exception as e:
            logger.warning(f"[forward_test] Telegram report error: {e}")
    except Exception as e:
        logger.warning(f"[scheduler] Forward-test cycle error: {e}")


def run_phase5_bull_watch():
    """Phase 5 (spec 2026-07-08): daily post-EOD regime-band check for the NR7
    governed universe; Telegram on band TRANSITIONS only (state persisted in
    phase5_regime_state) so the moment the market lets NR7 trade is loud."""
    import pandas as pd
    from engine.registry_loader import approved_universe
    from engine.phase5_watch import band_changes
    from engine.regime_filter import detect_regime
    from engine.indicators import calc_adx
    from scheduler.scanner import _BULL_STRONG_ADX
    universe = approved_universe("NR7 Breakout") or set()
    if not universe:
        return
    conn = db_connect(DB_PATH)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS phase5_regime_state "
                     "(ticker TEXT PRIMARY KEY, band TEXT, updated TEXT)")
        prev = {r[0]: r[1] for r in conn.execute(
            "SELECT ticker, band FROM phase5_regime_state")}
        cur = {}
        for t in sorted(universe):
            df = pd.read_sql("SELECT date, open, high, low, close, volume FROM ohlcv "
                             "WHERE ticker=? ORDER BY date DESC LIMIT 250",
                             conn, params=(t,)).iloc[::-1].reset_index(drop=True)
            if len(df) < 30:
                continue
            reg = detect_regime(df)
            if reg == 'BULL':
                try:
                    adx = float(calc_adx(df, 14).iloc[-1])
                except Exception:
                    adx = 0.0
                reg = 'BULL_STRONG' if adx >= _BULL_STRONG_ADX else 'BULL_MODERATE'
            cur[t] = reg
        changes = band_changes(prev, cur)
        now_s = datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
        for t, band in cur.items():
            conn.execute("INSERT OR REPLACE INTO phase5_regime_state VALUES (?,?,?)",
                         (t, band, now_s))
        conn.commit()
    finally:
        conn.close()
    if changes:
        eligible_n = sum(1 for b in cur.values()
                         if b in ("BULL_MODERATE", "BULL_STRONG"))
        lines = [f"{'🟢' if new in ('BULL_MODERATE','BULL_STRONG') else '⚪'} "
                 f"{t}: {old} → {new}" for t, old, new in changes]
        send_telegram("📡 <b>PHASE 5 BULL-watch</b>\n" + "\n".join(lines)
                      + f"\nNR7-eligible now: {eligible_n}/{len(cur)}", event="report.bull_watch")
