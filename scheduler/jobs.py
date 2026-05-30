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


def refresh_wf_scores():
    """Run walk-forward semua ticker & simpan ke wf_scores table."""
    from engine.walkforward_multi import run_walk_forward
    from datetime import datetime as dt

    tickers = get_all_tickers()
    ohlcv_map = _load_ohlcv_bulk()
    conn = sqlite3.connect(DB_PATH)
    now_str = dt.now().strftime("%Y-%m-%d %H:%M")
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
                conn.execute(
                    "INSERT OR REPLACE INTO wf_scores "
                    "(ticker,strategy,consistency_pct,avg_return_pct,avg_sharpe,weighted_score,windows_tested,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (ticker, strategy,
                     metrics.get("consistency_pct", 0),
                     float(metrics.get("avg_return_pct", 0)),
                     float(metrics.get("avg_sharpe", 0)),
                     float(metrics.get("score", 0)),
                     metrics.get("windows_tested", 0),
                     now_str))
            updated += 1
        except Exception as e:
            print(f"[WF] {ticker} error: {e}")
    conn.commit()
    conn.close()
    print(f"[WF] refresh_wf_scores selesai: {updated}/{len(tickers)} ticker diupdate")


def run_flow_fetch():
    """Fetch flow data dari Stockbit dan simpan ke DB."""
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


def run_broker_flow_fetch():
    """Fetch broker flow data setelah 20:00 WIB saat Stockbit publish summary harian."""
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
    except Exception as e:
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Broker flow fetch error: {e}")
        send_telegram(f"🔴 <b>Broker Flow Fetch Error</b>\n<code>{str(e)[:200]}</code>")


def run_foreign_snapshot():
    """14:30 WIB — Pre-close foreign accumulation watchlist alert.

    Uses the most recently available broker_flow (Asing) data (fetched nightly at 20:15).
    Sends top 5 buy + top 5 sell tickers ranked by 5-day score_pct.
    """
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

        send_telegram(msg)
        print(f"[{dt.now(WIB).strftime('%H:%M')}] Foreign snapshot sent ({len(top_buy)} buy, {len(top_sell)} sell)")
    except Exception as e:
        logging.error(f"run_foreign_snapshot error: {e}")
        send_telegram(f"🔴 <b>Foreign Snapshot Error</b>\n<code>{str(e)[:200]}</code>")


def run_news_fetch():
    """Fetch Google News headlines per ticker, persist to news_mentions table.

    Spike detection (today_count >= 3× 30d avg) is consumed by flow_broker_report.
    """
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


def run_premover_eod():
    """EOD pre-breakout scan — runs at 16:30 after data fetch."""
    from engine.premover_detector import run_scan
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Pre-mover EOD scan dimulai...")
    try:
        new_setups = run_scan(DB_PATH, send_alert_fn=send_telegram)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan selesai. "
              f"{len(new_setups)} new setups.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Pre-mover scan error: {e}")
        send_telegram(f"🔴 <b>Pre-mover Scan Error</b>\n<code>{str(e)[:200]}</code>")
