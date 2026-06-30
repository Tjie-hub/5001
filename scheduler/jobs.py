# scheduler/jobs.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
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


_WF_LOCK_JOB = "refresh_wf_scores"


def _pid_alive(pid) -> bool:
    """True if `pid` is a running process. Signal 0 = liveness probe, no-op."""
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _wf_lock_acquire(db_path: str, job: str = _WF_LOCK_JOB) -> bool:
    """Take a pid-aware advisory lock so two heavy refreshes can't run at once.
    A lock held by a dead pid is treated as stale and overwritten (self-healing)."""
    with sqlite3.connect(db_path, timeout=30) as g:
        g.execute("PRAGMA busy_timeout=30000")
        g.execute("CREATE TABLE IF NOT EXISTS _job_lock "
                  "(job TEXT PRIMARY KEY, pid INTEGER, started_at TEXT)")
        row = g.execute("SELECT pid FROM _job_lock WHERE job=?", (job,)).fetchone()
        if row and _pid_alive(row[0]):
            return False
        g.execute("INSERT OR REPLACE INTO _job_lock VALUES (?,?,?)",
                  (job, os.getpid(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return True


def _wf_lock_release(db_path: str, job: str = _WF_LOCK_JOB) -> None:
    try:
        with sqlite3.connect(db_path, timeout=30) as g:
            g.execute("PRAGMA busy_timeout=30000")
            g.execute("DELETE FROM _job_lock WHERE job=? AND pid=?", (job, os.getpid()))
    except Exception as e:
        print(f"[WF] lock release error: {e}")


def refresh_wf_scores():
    """Run walk-forward semua ticker & simpan ke wf_scores table.

    Lock-safe (DB-lock incident 2026-06-25): the long walk-forward compute runs
    with NO db transaction open; all results are written in one short transaction
    at the end (lock held ~seconds, not the ~35 min that used to block EOD scans).
    A pid-aware _job_lock guard prevents concurrent refreshes from stacking.
    """
    from engine.walkforward_multi import run_walk_forward
    from engine.wf_edge import aggregate_wf_windows, save_wf_edge, ensure_wf_edge_table
    from datetime import datetime as dt

    if not _wf_lock_acquire(DB_PATH):
        print("[WF] refresh_wf_scores: another run is in progress — skipped")
        return
    try:
        tickers = get_all_tickers()
        ohlcv_map = _load_ohlcv_bulk()
        now_str = dt.now().strftime("%Y-%m-%d %H:%M")

        # ---- COMPUTE PHASE: no DB write lock held (this is the ~35-min CPU work) ----
        score_rows = []        # tuples ready for wf_scores
        edge_payloads = []     # (ticker, aggregated_rows) for wf_edge
        updated = 0
        for ticker in tickers:
            try:
                df = ohlcv_map.get(ticker)
                if df is None or len(df) < 60:
                    continue
                result = run_walk_forward(df)
                if "error" in result:
                    continue
                ranked = result.get("ranked", [])
                for metrics in ranked:
                    strategy = metrics.get("strategy", "")
                    if not strategy:
                        continue
                    score_rows.append(
                        (ticker, strategy,
                         metrics.get("consistency_pct", 0),
                         float(metrics.get("avg_return_pct", 0)),
                         float(metrics.get("avg_sharpe", 0)),
                         float(metrics.get("score", 0)),
                         metrics.get("windows_tested", 0),
                         now_str))
                edge_payloads.append((ticker, aggregate_wf_windows(ranked)))
                updated += 1
            except Exception as e:
                print(f"[WF] {ticker} error: {e}")

        # ---- WRITE PHASE: one short transaction (lock held ~seconds) ----
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS wf_scores ("
                "ticker TEXT NOT NULL, strategy TEXT NOT NULL, consistency_pct REAL, "
                "avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL, "
                "windows_tested INTEGER, updated_at TEXT, PRIMARY KEY(ticker,strategy))")
            ensure_wf_edge_table(conn)
            conn.executemany(
                "INSERT OR REPLACE INTO wf_scores "
                "(ticker,strategy,consistency_pct,avg_return_pct,avg_sharpe,weighted_score,windows_tested,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)", score_rows)
            for ticker, agg in edge_payloads:
                save_wf_edge(conn, ticker, agg, now_str)
            conn.commit()
            edge_count = conn.execute(
                "SELECT COUNT(*) FROM wf_edge WHERE last_computed=?", (now_str,)
            ).fetchone()[0]
            print(f"[WF] wf_edge updated: {edge_count} rows")

            # Strategy health re-validation: alert when a live-selectable strategy's
            # cross-ticker average walk-forward return is negative. This is how the
            # Jan-2026 regime break should have been caught in days, not months.
            try:
                from scheduler.scanner import _get_disabled_strategies
                disabled = _get_disabled_strategies()
                rows = conn.execute(
                    "SELECT strategy, ROUND(AVG(avg_return_pct),2), COUNT(*) "
                    "FROM wf_scores GROUP BY strategy"
                ).fetchall()
                losing = [(s, r) for s, r, n in rows
                          if s not in disabled and r is not None and r < 0 and n >= 50]
                if losing:
                    msg = "⚠️ <b>WF Re-validation: strategi live dengan avg return negatif</b>\n\n"
                    for s, r in sorted(losing, key=lambda x: x[1]):
                        msg += f"  {s}: {r:+.2f}%/window\n"
                    msg += "\nPertimbangkan menambahkan ke disabled_strategies (paper_config)."
                    send_telegram(msg)
                    print(f"[WF] Re-validation alert: {len(losing)} losing live strategies")
            except Exception as _rv_err:
                print(f"[WF] Re-validation check error: {_rv_err}")
        finally:
            conn.close()
        print(f"[WF] refresh_wf_scores selesai: {updated}/{len(tickers)} ticker diupdate")
    finally:
        _wf_lock_release(DB_PATH)


def run_flow_fetch():
    """Fetch flow data dari Stockbit dan simpan ke DB."""
    if _holiday_skip("run_flow_fetch"):
        return
    from datetime import datetime as dt, date
    import sqlite3
    now_str = dt.now(WIB).strftime('%H:%M')
    is_first_session = dt.now(WIB).hour == 9
    today_str = str(date.today())
    print(f"[{now_str}] Flow fetch dimulai...")
    try:
        from flow_filter import main as flow_main
        import sys as _sys
        _argv = _sys.argv[:]
        _sys.argv = ["flow_filter.py"]
        flow_main()
        _sys.argv = _argv
        # Verifikasi data tersimpan
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(*) FROM stockbit_flow WHERE trade_date=?", (today_str,)
        ).fetchone()[0]
        conn.close()
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Flow fetch selesai. {count} tickers tersimpan.")
        if is_first_session and count == 0:
            send_telegram(
                f"⚠️ <b>Flow Fetch WARNING</b>\n\n"
                f"Sesi pertama ({now_str}) selesai tapi <b>0 tickers tersimpan</b>.\n"
                f"Kemungkinan: token Stockbit expired.\n\n"
                f"Cek: <code>cat .stockbit_token</code>"
            )
    except Exception as e:
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Flow fetch error: {e}")
        if is_first_session:
            send_telegram(
                f"🔴 <b>Flow Fetch GAGAL</b>\n\n"
                f"Sesi pertama ({now_str}) error:\n"
                f"<code>{str(e)[:200]}</code>\n\n"
                f"Signal scan 15:35 akan berjalan <b>tanpa flow data</b>."
            )


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
    conn = sqlite3.connect(db_path)
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


def run_broker_flow_fetch():
    """Fetch broker flow data setelah 20:00 WIB saat Stockbit publish summary harian."""
    if _holiday_skip("run_broker_flow_fetch"):
        return
    from datetime import datetime as dt, date
    import sqlite3
    now_str = dt.now(WIB).strftime('%H:%M')
    today_str = str(date.today())
    print(f"[{now_str}] Broker flow fetch dimulai...")
    try:
        from stockbit_fetcher import extract_token_from_chrome, verify_token, run_flow, get_tickers
        token = extract_token_from_chrome()
        if not token or not verify_token(token):
            send_telegram("🔴 <b>Broker Flow Fetch GAGAL</b>\nToken Stockbit expired atau tidak ditemukan.")
            return
        tickers = get_tickers("ALL")
        # Include open paper trade tickers not already in ALL list
        conn_pt = sqlite3.connect(DB_PATH)
        extra = [r[0] for r in conn_pt.execute(
            "SELECT DISTINCT ticker FROM paper_trades WHERE status='OPEN'"
        ).fetchall()]
        conn_pt.close()
        extra_new = [t for t in extra if t not in tickers]
        if extra_new:
            print(f"[{now_str}] + {len(extra_new)} extra tickers from paper trades: {extra_new}")
            tickers = tickers + extra_new
        run_flow(token, tickers)
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM broker_flow WHERE trade_date=?", (today_str,)
        ).fetchone()[0]
        conn.close()
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Broker flow selesai. {count} tickers untuk {today_str}.")

        # Coverage monitor: alert on a stockbit_flow outage while it can still be
        # re-fetched today (a past session cannot be backfilled later).
        cov = check_flow_coverage(DB_PATH, today_str)
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Flow coverage {today_str}: "
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
            )
    except Exception as e:
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Broker flow fetch error: {e}")
        send_telegram(f"🔴 <b>Broker Flow Fetch Error</b>\n<code>{str(e)[:200]}</code>")


def run_foreign_snapshot():
    """14:30 WIB — Pre-close foreign accumulation watchlist alert.

    Uses the most recently available broker_flow (Asing) data (fetched nightly at 20:15).
    Sends top 5 buy + top 5 sell tickers ranked by 5-day score_pct.
    """
    if _holiday_skip("run_foreign_snapshot"):
        return
    from datetime import datetime as dt
    now_str = dt.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Foreign snapshot dimulai...")
    try:
        from flow_filter import get_top_foreign_accumulation
        all_results = get_top_foreign_accumulation(top_n=9999)
        top_buy = [r for r in all_results if r["score_pct"] > 0][:5]
        top_sell = sorted(all_results, key=lambda x: x["score_pct"])[:5]
        top_sell = [r for r in top_sell if r["score_pct"] < 0]

        latest = all_results[0]["latest_date"] if all_results else "N/A"
        msg = f"🏛️ <b>Foreign Flow Snapshot — {dt.now(WIB).strftime('%d/%m %H:%M')}</b>\n"
        msg += f"<i>Data: {latest} | 5-day net / avg vol</i>\n\n"

        if top_buy:
            msg += "<b>🟢 Top Foreign Accumulation:</b>\n"
            for r in top_buy:
                msg += f"  {r['ticker']}: {r['score_pct']:+.1f}% ({r['foreign_net_lots']:+,.0f} lots)\n"
        else:
            msg += "<b>🟢 No significant foreign buying</b>\n"

        if top_sell:
            msg += "\n<b>🔴 Top Foreign Distribution:</b>\n"
            for r in top_sell:
                msg += f"  {r['ticker']}: {r['score_pct']:+.1f}% ({r['foreign_net_lots']:+,.0f} lots)\n"
        else:
            msg += "\n<b>🔴 No significant foreign selling</b>\n"

        print(f"[{dt.now(WIB).strftime('%H:%M')}] Foreign snapshot computed ({len(top_buy)} buy, {len(top_sell)} sell) — no alert")
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
    print(f"[{now_str}] News fetch dimulai...")
    try:
        from news_filter import run_news_batch
        saved = run_news_batch()
        print(f"[{dt.now(WIB).strftime('%H:%M')}] News fetch selesai. {saved} tickers tersimpan.")
    except Exception as e:
        print(f"[{dt.now(WIB).strftime('%H:%M')}] News fetch error: {e}")
        send_telegram(
            f"🔴 <b>News Fetch GAGAL</b>\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


def _run_open_trade_monitor():
    try:
        from monitor import check_all_open_trades
        check_all_open_trades()
    except Exception as e:
        print(f"[scheduler] Monitor error: {e}")
    # DD circuit breaker check — cheap, runs each monitor cycle (every 5 min during trading)
    try:
        from paper_trade import check_dd_circuit_breaker
        check_dd_circuit_breaker()
    except Exception as e:
        print(f"[scheduler] DD circuit breaker error: {e}")


def _run_screener_intraday():
    try:
        from screener.screener_jobs import run_intraday
        run_intraday(send_telegram=send_telegram)
    except Exception as e:
        print(f"[scheduler] Screener intraday error: {e}")


def _run_screener_eod():
    try:
        from screener.screener_jobs import run_eod
        run_eod(send_telegram=send_telegram)
    except Exception as e:
        print(f"[scheduler] Screener EOD error: {e}")


def _refresh_backtest_cache():
    try:
        from engine.walkforward_multi import run_all_strategies
        from engine.regime_filter import detect_regime
        from datetime import date
        today = date.today().isoformat()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_cache (
                ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
                best_strategy TEXT, best_return REAL, win_rate REAL,
                sharpe REAL, total_trades INTEGER, profitable INTEGER,
                regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date)
            )""")
        ohlcv_map = _load_ohlcv_bulk()
        computed = 0
        rows_to_insert = []
        for ticker, df in ohlcv_map.items():
            try:
                if len(df) < 60:
                    continue
                strat_results = run_all_strategies(df, capital=50_000_000)
                best = max(strat_results, key=lambda x: x['total_return_pct'])
                try:
                    regime = detect_regime(df)
                except Exception:
                    regime = "UNCERTAIN"
                rows_to_insert.append((
                    ticker, today, best['strategy'], best['total_return_pct'],
                    best['win_rate'], best.get('sharpe', 0), best.get('total_trades', 0),
                    int(best['total_return_pct'] > 0), regime,
                ))
                computed += 1
            except Exception:
                pass
        conn.executemany("""
            INSERT OR REPLACE INTO backtest_cache
            (ticker, computed_date, best_strategy, best_return, win_rate, sharpe,
             total_trades, profitable, regime, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
        """, rows_to_insert)
        conn.commit()
        conn.close()
        print(f"[scheduler] Backtest cache refreshed: {computed} tickers")
    except Exception as e:
        print(f"[scheduler] Cache refresh error: {e}")


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
        print(f"[premover auto] Telegram summary error: {e}")


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
                              open_trade, _log_premover_auto, init_paper_table)
    now_str = datetime.now(WIB).strftime('%H:%M')

    # Circuit breaker gate — block auto-trading when risk = CRITICAL
    _risk = get_market_risk_for_circuit_breaker()
    _cb_state, _cb_reason = check_circuit_breaker(_risk)
    if _cb_state == CircuitBreakerState.OPEN:
        print(f"[{now_str}] Circuit breaker OPEN: {_cb_reason} — premover EOD paused")
        send_telegram(f"⛔ <b>Circuit Breaker Active</b>\n\n{_cb_reason}\n\nAuto-trading paused. Manual override required.")
        return

    print(f"[{now_str}] Pre-mover EOD scan dimulai...")
    try:
        new_setups = run_scan(DB_PATH, send_alert_fn=None)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan selesai. "
              f"{len(new_setups)} new setups.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan error: {e}")
        send_telegram(f"🔴 <b>Pre-mover Scan Error</b>\n<code>{str(e)[:200]}</code>")
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
                close_price = float(s.get('close', 0))
                if close_price > 0:
                    open_trade(ticker, close_price, strategy=None, notify=True)
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern, **ev})
        except Exception as exc:
            print(f"[premover auto] {ticker} error: {exc}")
            summary_rows.append({'ticker': ticker, 'score': score,
                                  'pattern': pattern,
                                  'would_trade': False,
                                  'skip_reason': f'error:{str(exc)[:80]}'})

    # summary_rows available for analysis; Telegram suppressed per config


def run_backtest_roller():
    """Monthly backtest window roller — appends new windows, exports JSON."""
    from engine.backtest_roller import roll_all, export_meta_dataset
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Backtest roller dimulai...")
    try:
        summary = roll_all(include_partial=True)
        n_exported = export_meta_dataset()
        msg = (
            f"🔄 <b>Backtest Roller Selesai</b>\n\n"
            f"New complete windows: <b>{summary['new_complete']}</b>\n"
            f"New partial windows: <b>{summary['new_partial']}</b>\n"
            f"Tickers updated: <b>{summary['tickers_updated']}/{summary['total_tickers']}</b>\n"
            f"JSON exported: <b>{n_exported} records</b>"
        )
        if summary['errors']:
            msg += f"\n⚠️ Errors: {len(summary['errors'])}"
        logging.info(msg)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Backtest roller selesai. "
              f"{summary['new_complete']} complete, {summary['new_partial']} partial")
    except Exception as e:
        logging.error(f"[backtest_roller] {e}")
        print(f"[{now_str}] Backtest roller error: {e}")


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
            fb = conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='BUY' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0] or 0
            fs = conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='SELL' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0] or 0
            foreign_net = fb - fs
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
        send_telegram(msg)
        print(f"[{now.strftime('%H:%M')}] Premarket briefing sent (tier={risk['tier']})")
    except Exception as e:
        logging.error(f"[market_health_report] {e}")
        print(f"[{now.strftime('%H:%M')}] Health report error: {e}")
    finally:
        conn.close()


def _build_premarket_firm_message(decisions: list, rows: list, header: str) -> str:
    """Pure Telegram-message builder for the premarket firm shortlist.

    decisions: list[AgentDecision] from firm.evaluate_staged.
    rows: the unified-watchlist long rows (dicts) used for source/strength lookup.
    header: pre-formatted "dd/mm HH:MM" string.
    Kept import-free (no langgraph) so it's unit-testable on the Windows venv.
    """
    by_ticker = {r["ticker"]: r for r in rows}
    approved = sorted(
        [d for d in decisions if d.decision == "approve"],
        key=lambda d: d.confidence or 0.0, reverse=True,
    )
    vetoed   = [d for d in decisions if d.decision == "veto"]
    passthru = [d for d in decisions if d.decision in ("degraded", "bypassed")]

    msg = f"🌅 <b>Premarket Shortlist — {header}</b>\n"
    msg += f"<i>Unified EOD watchlist → agent firm ({len(decisions)} setups)</i>\n\n"

    if approved:
        msg += "<b>✅ Firm-approved (long):</b>\n"
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

    return msg


def run_premarket_firm_scan():
    """08:35 WIB — premarket agent-firm vetting of last night's unified watchlist.

    Picks the top-15 long-direction setups from build_unified_watchlist (reversal +
    premover + bear-dip, all settled overnight), runs them through the 2-stage agent
    firm, and sends a premarket shortlist heads-up. Informational only — auto-entry
    stays owned by the 16:30 premover EOD path.
    """
    if _holiday_skip("run_premarket_firm_scan"):
        return
    from engine.unified_watchlist import build_unified_watchlist
    from engine.liquidity import select_top_liquid_longs
    from engine.agent_firm import firm as _firm
    from engine.agent_firm.schemas import SignalCandidate as _SC

    now = datetime.now(WIB)
    now_str = now.strftime('%H:%M')
    date_str = now.strftime('%Y-%m-%d')

    # Dedup guard — prevents duplicate sends when two instances briefly overlap
    # (systemd Restart=always can start a new process before the old one fully exits).
    # First instance to INSERT wins; second gets IntegrityError and skips silently.
    with sqlite3.connect(DB_PATH, timeout=5) as _g:
        _g.execute(
            "CREATE TABLE IF NOT EXISTS _job_sentinel "
            "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))"
        )
        try:
            _g.execute("INSERT INTO _job_sentinel VALUES ('premarket_firm', ?)", (date_str,))
        except sqlite3.IntegrityError:
            print(f"[{now_str}] Premarket firm: already sent today — skipped (duplicate guard)")
            return

    print(f"[{now_str}] Premarket agent-firm scan dimulai...")

    try:
        rows = build_unified_watchlist(DB_PATH)
    except Exception as e:
        logging.error(f"[premarket_firm] watchlist build error: {e}")
        print(f"[{now_str}] Premarket firm: watchlist build error: {e}")
        return

    # Value-base liquidity: keep the 3 best long-only setups whose 30d avg daily
    # traded value (close*volume, Rp) clears the turnover floor — drops thin names
    # that a volume/lot count would let through at low price levels.
    conn = sqlite3.connect(DB_PATH)
    try:
        longs = select_top_liquid_longs(rows, conn, date_str, top_n=3)
    finally:
        conn.close()
    if not longs:
        print(f"[{now_str}] Premarket firm: no liquid long setups from unified watchlist — skipped")
        return

    # ── Pre-LLM edge veto (Phase 3, gated by EDGE_SCORE_MODE) ─────────────────
    from config import edge_mode
    if edge_mode() != 'off':
        try:
            from engine.edge_enrich import enrich_candidate, market_regime
            from engine.veto import apply_vetoes
            _c = sqlite3.connect(DB_PATH)
            try:
                _mreg = market_regime(_c)
                _open = _c.execute(
                    "SELECT COUNT(*) FROM paper_trades WHERE status='OPEN'"
                ).fetchone()[0]
                _enr = []
                for r in longs:
                    _rows = _c.execute(
                        "SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 60",
                        (r["ticker"],)).fetchall()
                    _closes = [x[0] for x in _rows][::-1]
                    _enr.append(enrich_candidate(
                        _c, r["ticker"], date_str, closes=_closes,
                        regime=None, sources=r.get("sources", [])))
                _surv = apply_vetoes(_enr, _mreg, _open)
            finally:
                _c.close()
            _keep = {s["ticker"] for s in _surv}
            logging.info(f"[{now_str}] Premarket edge veto ({edge_mode()}, market={_mreg}): "
                         f"{len(_surv)}/{len(longs)} survive")
            if edge_mode() == 'enforce':
                longs = [r for r in longs if r["ticker"] in _keep]
                if not longs:
                    logging.info(f"[{now_str}] Premarket: all candidates failed edge/veto — skipped")
                    return
        except Exception as _ev:
            logging.warning(f"[{now_str}] Premarket edge veto error (fail-open): {_ev}")

    candidates = [
        _SC(
            ticker=r["ticker"],
            strategy="premarket",
            score=float(r.get("strength") or 0.0),
            scan_time=f"{date_str} {now_str}",
            flow_verdict=(r.get("detail", {}).get("reversal") or {}).get("verdict"),
            foreign_score=None,
            indicators={"sources": r.get("sources", []),
                        "confluence": r.get("confluence", False)},
        )
        for r in longs
    ]

    try:
        _firm.reset_market_ctx()
        decisions = _firm.evaluate_staged(candidates)
    except Exception as e:
        logging.error(f"[premarket_firm] firm eval error: {e}")
        print(f"[{now_str}] Premarket firm eval error: {e}")
        return

    try:
        send_telegram(_build_premarket_firm_message(decisions, longs, now.strftime('%d/%m %H:%M')))
    except Exception as e:
        print(f"[premarket firm] Telegram error: {e}")

    n_app = sum(1 for d in decisions if d.decision == "approve")
    n_veto = sum(1 for d in decisions if d.decision == "veto")
    print(f"[{now_str}] Premarket firm: {len(decisions)} evaluated "
          f"({n_app} approve, {n_veto} veto)")


def run_eod_trade_plan():
    """16:40 WIB — single consolidated, agent-ranked trade plan for the next session.

    Merges every long signal source (reversal watchlist + bullish/volume screen +
    today's premarket approvals) into one pool, runs the top-8 by confluence through
    the agent firm, and sends ONE Telegram message with firm-APPROVED longs only.
    Shorts are intentionally excluded — they are exit/SL triggers, not entries.

    Runs after the 16:15 screener EOD (reversal watchlist) and 16:30 premover scan so
    all source tables are settled. Fail-open: if the firm is disabled or errors, falls
    back to deterministic confluence ranking (report flagged ⚠️ Firm offline).
    """
    if _holiday_skip("run_eod_trade_plan"):
        return
    from engine import trade_plan as tp
    from engine.agent_firm import firm as _firm
    from engine.agent_firm.schemas import SignalCandidate as _SC

    now = datetime.now(WIB)
    now_str = now.strftime('%H:%M')
    date_str = now.strftime('%Y-%m-%d')

    # Dedup guard (mirrors premarket firm scan) — first INSERT wins. 30s busy_timeout
    # waits out transient writers (the 16:40 slot can overlap a long EOD write on the
    # 2.5GB WAL db, unlike the quiet 08:35 premarket slot).
    with sqlite3.connect(DB_PATH, timeout=30) as _g:
        _g.execute("PRAGMA busy_timeout=30000")
        _g.execute("CREATE TABLE IF NOT EXISTS _job_sentinel "
                   "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))")
        try:
            _g.execute("INSERT INTO _job_sentinel VALUES ('eod_trade_plan', ?)", (date_str,))
        except sqlite3.IntegrityError:
            print(f"[{now_str}] EOD trade plan: already sent today — skipped (dup guard)")
            return

    from config import edge_mode

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        cands = tp.gather_long_candidates(conn, date_str)
        regime = tp.get_regime(conn, date_str)
        top = tp.select_top(cands, n=8) if cands else []

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

    if not cands:
        print(f"[{now_str}] EOD trade plan: no long candidates — skipped")
        return

    if not top:
        # every candidate failed the directional pre-screen — ship an empty plan
        send_telegram(tp.build_message([], regime, now.strftime('%d/%m'), degraded=False,
                                       vpin_summary=vpin_summary))
        print(f"[{now_str}] EOD trade plan: all candidates vetoed by edge pre-screen — empty plan sent")
        return

    candidates = [
        _SC(ticker=c["ticker"], strategy="eod", score=float(c["conviction"] or 0.0),
            scan_time=f"{date_str} {now_str}", flow_verdict=c.get("smart_money"),
            indicators={"sources": c["sources"], "confluence": c["confluence"],
                        "vol_ratio": c["vol_ratio"], "net_value": c["net_value"]})
        for c in top
    ]

    degraded = False
    try:
        _firm.reset_market_ctx()
        decisions = _firm.evaluate_staged(candidates)
        firm_ran = any(d.decision in ("approve", "veto") for d in decisions)
        if firm_ran:
            ranked = tp.rank_approved(top, decisions)
        else:
            ranked, degraded = tp.fallback_rank(top), True   # firm disabled/bypassed
    except Exception as e:
        logging.error(f"[eod_trade_plan] firm eval error (fail-open): {e}")
        ranked, degraded = tp.fallback_rank(top), True

    try:
        send_telegram(tp.build_message(ranked, regime, now.strftime('%d/%m'),
                                       degraded=degraded, vpin_summary=vpin_summary))
    except Exception as e:
        print(f"[eod_trade_plan] Telegram error: {e}")

    print(f"[{now_str}] EOD trade plan: {len(cands)} candidates, top {len(top)} vetted, "
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
    print(f"[{now_str}] VPIN batch compute starting for {date_str}...")

    tickers = get_all_tickers()
    computed = 0
    errors = 0

    try:
        conn = sqlite3.connect(DB_PATH)
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

    print(f"[{now_str}] VPIN batch done: {computed} computed, {errors} errors")
    return {'computed': computed, 'errors': errors, 'date': date_str}


def run_vpin_backfill(days=90):
    """Backfill vpin_scores for the past N days from existing daily_screen data.

    Skips dates where vpin_scores already has data. Uses dates from
    daily_screen (which has OHLCV and tick coverage), not calendar dates.
    """
    from engine.vpin import calc_vpin as _calc_vpin
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] VPIN backfill starting ({days} days)...")

    try:
        conn = sqlite3.connect(DB_PATH)
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
        print(f"[{now_str}] VPIN backfill done: {total_computed} computed, {total_errors} errors")
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
    from forward_testing.positions.market_data import MarketDataResolver
    from forward_testing.positions.exit_policy import ExitPolicyRegistry
    from forward_testing.positions.shadow_manager import ShadowPositionManager
    from forward_testing.lifecycle.manager import LifecycleManager
    from forward_testing.positions.costs import Costs

    db = db_path or DB_PATH
    rd = run_date or datetime.now(WIB).strftime("%Y-%m-%d")
    try:
        init_ft_tables(db)
        repo = FTRepo(db)

        def _trade_count():
            with sqlite3.connect(db, timeout=30) as c:
                return c.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]

        open_before = len(repo.get_open_shadow_positions())
        trades_before = _trade_count()

        n_ingested = SignalAdapter(repo, db).ingest(rd)
        mgr = ShadowPositionManager(
            repo, MarketDataResolver(db), ExitPolicyRegistry(),
            LifecycleManager(repo), db, costs=Costs(),
        )
        mgr.run(rd)

        open_after = len(repo.get_open_shadow_positions())
        closed = _trade_count() - trades_before
        opened = (open_after - open_before) + closed
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Forward-test cycle {rd}: "
              f"ingested={n_ingested} opened={opened} closed={closed} open_now={open_after}")
    except Exception as e:
        print(f"[scheduler] Forward-test cycle error: {e}")
