"""Research batch jobs (spec §10-M3) — moved verbatim from scheduler/jobs.py.

These produce research artifacts (wf_scores, wf_edge, backtest_cache) and run
via research/cli.py (cron or manual) — NEVER from the production scheduler.
Bodies unchanged from the pre-move versions; only module plumbing differs.
"""
import os
import sqlite3
import logging
from datetime import datetime

import pytz

from data.db import connect as db_connect
from data.loaders import _load_ohlcv_bulk
from utils.telegram import send_telegram

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "walkforward.db"))


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
    with db_connect(db_path) as g:
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
        with db_connect(db_path) as g:
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
    from research.walkforward_multi import run_walk_forward
    from engine.wf_edge import aggregate_wf_windows, save_wf_edge, ensure_wf_edge_table
    from datetime import datetime as dt

    if not _wf_lock_acquire(DB_PATH):
        print("[WF] refresh_wf_scores: another run is in progress — skipped")
        return
    try:
        # Survivorship (item 2.4): score EVERY ticker in the corpus, not just
        # currently-active idx_tickers — a name that later delists must keep
        # its real (often losing) history in wf_scores. _refresh_backtest_cache
        # already iterates the corpus; this aligns the WF refresh.
        ohlcv_map = _load_ohlcv_bulk(final_only=True)  # research: no partial bars (plan 2A)
        tickers = sorted(ohlcv_map.keys())
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
        conn = db_connect(DB_PATH)
        try:
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


def _refresh_backtest_cache():
    try:
        from research.walkforward_multi import run_all_strategies
        from engine.regime_filter import detect_regime
        from datetime import date
        today = date.today().isoformat()
        conn = db_connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_cache (
                ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
                best_strategy TEXT, best_return REAL, win_rate REAL,
                sharpe REAL, total_trades INTEGER, profitable INTEGER,
                regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date)
            )""")
        ohlcv_map = _load_ohlcv_bulk(final_only=True)  # research: no partial bars (plan 2A)
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


def run_backtest_roller():
    """Monthly backtest window roller — appends new windows, exports JSON."""
    from research.backtest_roller import roll_all, export_meta_dataset
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
