
import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "REDACTED_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5919142813")

DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

def send_telegram(msg: str):
    if "ISI_" in TELEGRAM_TOKEN:
        print(f"[Telegram skip] {msg}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_all_tickers():
    """Return all active tickers: idx_tickers table first, fallback to ohlcv."""
    conn = sqlite3.connect(DB_PATH)
    # Prefer the master list (populated after discovery)
    try:
        rows = conn.execute(
            "SELECT ticker FROM idx_tickers WHERE status='active' ORDER BY ticker"
        ).fetchall()
        if rows:
            conn.close()
            return [r[0] for r in rows]
    except Exception:
        pass
    # Fallback: tickers already in ohlcv
    tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker").fetchall()]
    conn.close()
    return tickers

def fetch_latest():
    """Fetch OHLCV terbaru untuk semua ticker (incremental batch)."""
    from data.fetcher import fetch_all_incremental, load_all_tickers
    now_str = datetime.now(WIB).strftime("%H:%M")
    tickers = load_all_tickers()
    print(f"[{now_str}] Incremental fetch {len(tickers)} tickers...")
    try:
        saved = fetch_all_incremental(category="ALL")
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch selesai. {saved} bars saved.")
    except Exception as e:
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Fetch error: {e}")
        send_telegram(
            f"🔴 <b>OHLCV Fetch GAGAL</b>\n\n"
            f"<b>{len(tickers)} tickers</b> @ {now_str}\n"
            f"<code>{str(e)[:150]}</code>"
        )

def _load_ohlcv_bulk() -> dict:
    """Load all OHLCV in one query. Returns {ticker: DataFrame}."""
    conn = sqlite3.connect(DB_PATH)
    all_df = pd.read_sql('SELECT * FROM ohlcv ORDER BY ticker, date ASC', conn)
    conn.close()
    for c in ["open", "high", "low", "close", "volume"]:
        all_df[c] = all_df[c].astype(float)
    return {t: grp.reset_index(drop=True) for t, grp in all_df.groupby("ticker")}


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


def calc_votes(df):
    last = df.iloc[-1]
    votes = 1
    labels = ["MOM"]
    try:
        tp_vol = (df["close"].tail(20) * df["volume"].tail(20)).sum()
        tot_vol = df["volume"].tail(20).sum()
        vwma20 = tp_vol / tot_vol if tot_vol > 0 else 0
        if last["close"] > vwma20:
            votes += 1
            labels.append("VWMA")
    except Exception as _e:
        logging.debug(f"calc_votes VWMA: {_e}")
    try:
        avg5 = df["volume"].tail(6).iloc[:-1].mean()
        if last["volume"] > avg5 * 1.5:
            votes += 1
            labels.append("VOL5")
    except Exception as _e:
        logging.debug(f"calc_votes VOL5: {_e}")
    try:
        ma20 = df["close"].tail(20).mean()
        if last["close"] > ma20:
            votes += 1
            labels.append("MA20")
    except Exception as _e:
        logging.debug(f"calc_votes MA20: {_e}")
    return votes, labels


def check_fundamental(ticker):
    """Check stockbit_keystats: PE>0, ROE>5, PBV<5. Returns (pass, reason)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            'SELECT pe_ttm, pbv, roe FROM stockbit_keystats WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1',
            (ticker,)
        ).fetchone()
        conn.close()
        if not row:
            return True, 'no_data'  # no keystats = allow (don't block)
        pe, pbv, roe = row
        if pe is not None and pe <= 0:
            return False, f'PE={pe}'
        if roe is not None and roe < 5:
            return False, f'ROE={roe}'
        if pbv is not None and pbv > 5:
            return False, f'PBV={pbv}'
        return True, 'OK'
    except Exception as _e:
        logging.warning(f"check_fundamental error: {_e}")
        return True, 'db_error'

# Module-level regime classifier cache: {ticker: (date_str, RegimeClassifier)}
_regime_clf_cache: dict = {}

# Sector scores cache: (scores_list, epoch_timestamp)
_sector_scores_cache: tuple = (None, 0.0)

def _get_sector_scores_cached():
    """Return score_sectors() cached for up to 1 hour."""
    import time
    from engine.sector_rotation import score_sectors
    global _sector_scores_cache
    scores, ts = _sector_scores_cache
    if scores is not None and (time.time() - ts) < 3600:
        return scores
    scores = score_sectors()
    _sector_scores_cache = (scores, time.time())
    return scores

# Open-trade status cache: {trade_id: {"pnl_pct": float, "status": str}}
_last_trades_state: dict = {}

def scan_momentum_signals():
    """Scan semua ticker untuk Momentum Following signal hari ini."""
    from engine.strategies import calc_vol_ratio, calc_relative_strength
    from engine.calendar_filter import is_blackout_day
    from engine.sector_rotation import is_sector_tradeable

    # Calendar blackout gate — pause new entries on BI Rate / FOMC event days
    _blackout, _bl_reason = is_blackout_day()
    if _blackout:
        logging.warning(f"[scan_momentum] BLACKOUT aktif: {_bl_reason} — scan dilewati.")
        send_telegram(f"⛔ <b>Scan Paused — Blackout</b>\n\n{_bl_reason}\n\nNo new entries today.")
        return []

    # Pre-compute sector scores once for entire scan (1-hour TTL cache)
    _sector_scores = _get_sector_scores_cached()

    STRATEGY    = "Momentum Following"
    MIN_CONSIST = 50.0
    BLACKLIST   = 33.0

    # Load filter toggles from config (1=on, 0=off)
    try:
        from paper_trade import get_config as _get_cfg
        _cfg = _get_cfg()
    except Exception:
        _cfg = {}
    _f_fundamental = int(_cfg.get("filter_fundamental", 1))
    _f_sector      = int(_cfg.get("filter_sector",      1))
    _f_flow        = int(_cfg.get("filter_flow",        1))
    _f_rs          = int(_cfg.get("filter_rs",          1))
    _f_regime      = int(_cfg.get("filter_regime",      1))
    _f_vpin        = int(_cfg.get("filter_vpin",        0))

    tickers = get_all_tickers()
    wf_map = {}
    try:
        conn_wf = sqlite3.connect(DB_PATH)
        rows = conn_wf.execute(
            "SELECT ticker, consistency_pct, weighted_score FROM wf_scores WHERE strategy=?",
            (STRATEGY,)
        ).fetchall()
        conn_wf.close()
        wf_map = {r[0]: {"consistency_pct": r[1], "weighted_score": r[2]} for r in rows}
    except Exception as _e:
        logging.warning(f"wf_map load error: {_e}")

    signals = []
    ohlcv_map = _load_ohlcv_bulk()
    ihsg_df = ohlcv_map.get("IHSG")
    # Regime classifier — import sekali, cache per ticker per hari
    from engine.regime_filter import RegimeClassifier
    import datetime as _dt
    _today_str = str(_dt.date.today())
    # Macro overlay — fetch sekali sebelum loop
    try:
        from engine.regime_filter import get_macro_overlay, apply_macro_overlay
        macro_data = get_macro_overlay()
    except Exception as _e:
        macro_data = {"idr_weakening": 0.0, "bi_rate": 6.25, "source": "fallback", "error": str(_e)}
    for ticker in tickers:
        wf = wf_map.get(ticker)
        if wf and wf["consistency_pct"] < BLACKLIST:
            continue
        # Fundamental filter
        if _f_fundamental:
            fund_ok, fund_reason = check_fundamental(ticker)
            if not fund_ok:
                continue
        else:
            flow_reason = "fundamental filter OFF"

        # Sector rotation filter — skip UNDERWEIGHT sectors
        if _f_sector:
            _sec_ok, _sec_reason = is_sector_tradeable(ticker, _sector_scores)
            if not _sec_ok:
                logging.debug(f"[scan_momentum] {ticker} blocked by sector: {_sec_reason}")
                continue
        else:
            _sec_reason = "sector filter OFF"

        # Flow confirmation filter
        from flow_filter import flow_confirms_signal
        if _f_flow:
            flow_ok, flow_reason, flow_data = flow_confirms_signal(ticker, "BUY")
            if not flow_ok:
                continue
        else:
            flow_ok, flow_reason, flow_data = True, "flow filter OFF", None

        # VPIN filter — require BUY-side multi-day VPIN signal
        _vpin_signal = "N/A"
        if _f_vpin:
            try:
                import sqlite3 as _sqlite3
                from screener.vpin_multi import calc_vpin_multi as _calc_vpin_multi
                _vpin_conn = _sqlite3.connect(DB_PATH)
                _vpin_multi = _calc_vpin_multi(_vpin_conn, ticker, _today_str)
                _vpin_conn.close()
                _vpin_signal = _vpin_multi['signal'] if _vpin_multi else 'NO_SIGNAL'
                if _vpin_signal not in ('STRONG_BUY', 'BUY', 'ACCUMULATION'):
                    logging.debug(f"[scan_momentum] {ticker} blocked by VPIN: {_vpin_signal}")
                    continue
            except Exception as _ve:
                logging.warning(f"[scan_momentum] VPIN filter error [{ticker}]: {_ve}")

        try:
            df = ohlcv_map.get(ticker)
            if df is None or len(df) < 25:
                continue
            vr     = calc_vol_ratio(df)
            streak = (df["close"] > df["close"].shift(1)) & (df["close"].shift(1) > df["close"].shift(2))
            sig    = streak & (vr > 1.3)
            if sig.iloc[-1]:
                # Relative Strength filter — skip laggards vs IHSG
                rs = calc_relative_strength(df, ihsg_df, period=20)
                if _f_rs and rs < 1.0:
                    logging.debug(f"[scan_momentum] {ticker} skipped — RS={rs:.2f} < 1.0 (laggard)")
                    continue

                last  = df.iloc[-1]
                prev  = df.iloc[-2]
                chg   = (last["close"] - prev["close"]) / prev["close"] * 100
                consistency = wf["consistency_pct"] if wf else None
                weighted    = wf["weighted_score"]   if wf else 0
                if wf and consistency < MIN_CONSIST:
                    continue
                votes, vote_labels = calc_votes(df)
                try:
                    _cached = _regime_clf_cache.get(ticker)
                    if _cached and _cached[0] == _today_str:
                        # Pakai cached classifier — skip retrain
                        regime_info = _cached[1].predict(df)
                    else:
                        # Train baru, simpan ke cache
                        _clf = RegimeClassifier()
                        _clf.train(df)
                        regime_info = _clf.predict(df)
                        _regime_clf_cache[ticker] = (_today_str, _clf)
                except Exception as _re:
                    logging.warning(f"RegimeClassifier error [{ticker}]: {_re}")
                    regime_info = None
                # Macro overlay: downgrade TRENDING→UNCERTAIN kalau IDR melemah >1%
                macro_reason = "macro OK"
                if regime_info:
                    try:
                        adj_regime, macro_reason = apply_macro_overlay(regime_info[0], macro_data)
                        regime_info = (adj_regime, regime_info[1])
                    except Exception as _me:
                        logging.warning(f"macro overlay error [{ticker}]: {_me}")
                # Regime filter: skip UNCERTAIN
                if _f_regime and regime_info and regime_info[0] == "UNCERTAIN":
                    continue
                from engine.sector_rotation import get_ticker_sector
                _sector_entry = next((s for s in _sector_scores if s["sector"] == get_ticker_sector(ticker)), None)
                signals.append({
                    "ticker":        ticker,
                    "close":         round(last["close"]),
                    "vol_ratio":     round(float(vr.iloc[-1]), 2),
                    "chg_pct":       round(chg, 2),
                    "date":          str(last["date"])[:10],
                    "consistency":   consistency,
                    "wf_score":      weighted,
                    "votes":         votes,
                    "vote_labels":   vote_labels,
                    "rs":            round(rs, 2),
                    "flow_score":    flow_data["score"] if flow_data else None,
                    "flow_sm":       flow_data["smart_money"] if flow_data else None,
                    "flow_reason":   flow_reason,
                    "macro_reason":  macro_reason,
                    "regime":        regime_info[0] if regime_info else "N/A",
                    "regime_conf":   regime_info[1] if regime_info else 0,
                    "sector":        _sec_reason.split(" ")[0] if _sec_reason else "Unknown",
                    "sector_weight": _sector_entry["weight"] if _sector_entry else "NEUTRAL",
                    "sector_score":  _sector_entry["score"] if _sector_entry else 0,
                    "vpin_signal":   _vpin_signal if _f_vpin else "filter OFF",
                })
        except Exception as _te:
            logging.exception(f"scan error [{ticker}]: {_te}")

    signals.sort(key=lambda x: x["wf_score"], reverse=True)
    return signals

def daily_signal_scan():
    """Job harian: fetch data lalu scan signal."""
    print(f"[{datetime.now(WIB).strftime('%H:%M')}] Daily scan dimulai...")
    
    # 1. Fetch data terbaru
    fetch_latest()
    
    # 2. Scan signal
    signals = scan_momentum_signals()
    
    # 3. Kirim Telegram
    now = datetime.now(WIB).strftime("%d/%m/%Y %H:%M")
    if signals:
        msg = f"📊 <b>Momentum Signal — {now}</b>\n\n"
        from paper_trade import calc_swing_tp
        for s in signals:
            tp = calc_swing_tp(s['ticker'], s['close'])
            sl = round(s['close'] * 0.975)
            tp_pct = round((tp / s['close'] - 1) * 100, 1)
            star = '⭐ ' if s.get('votes', 0) >= 4 else ''
            vlbl = '+'.join(s.get('vote_labels', []))
            msg += f"{star}🟢 <b>{s['ticker']}</b> — Rp {s['close']:,}\n"
            msg += f"   📈 TP: Rp {tp:,} (+{tp_pct}%)\n"
            msg += f"   🛑 SL: Rp {sl:,} (-2.5%)\n"
            rs_val = s.get('rs', 1.0)
            rs_emoji = '💪' if rs_val >= 1.2 else '✅' if rs_val >= 1.0 else '⚠️'
            msg += f"   Vol: {s['vol_ratio']}x | Chg: {s['chg_pct']:+.2f}% | {rs_emoji} RS: {rs_val:.2f}\n"
            flow_emoji = chr(0x1F7E2) if (s.get("flow_score") or 0) >= 3 else chr(0x1F7E1) if (s.get("flow_score") or 0) >= 0 else chr(0x1F534)
            msg += f"   {flow_emoji} Flow: {s.get('flow_reason','N/A')}\n"
            regime = s.get('regime', 'N/A')
            regime_conf = s.get('regime_conf', 0)
            regime_emoji = '📈' if regime == 'TRENDING' else '📉' if regime == 'SIDEWAYS' else '❓'
            msg += f"   {regime_emoji} Regime: {regime} ({regime_conf:.0%})"
            _mr = s.get('macro_reason', 'macro OK')
            if _mr and _mr != 'macro OK':
                msg += f" ⚠️ {_mr}"
            msg += "\n"
            msg += f"   🗳 Votes: {s.get('votes',0)}/4 [{vlbl}]\n"
            _vs = s.get('vpin_signal', 'filter OFF')
            if _vs not in ('filter OFF', 'N/A'):
                _ve = '🔥🔥' if _vs == 'STRONG_BUY' else '🔥' if _vs == 'BUY' else '🟡'
                msg += f"   {_ve} VPIN: {_vs}\n"
            msg += "\n"
        msg += f"Total: {len(signals)} sinyal hari ini"
    else:
        msg = f"📊 <b>Momentum Signal — {now}</b>\n\nTidak ada sinyal Momentum hari ini."
    
    send_telegram(msg)
    print(f"[{datetime.now(WIB).strftime('%H:%M')}] Scan selesai. {len(signals)} signals ditemukan.")

    # ── AUTO-OPEN PAPER TRADE ──
    if signals:
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from paper_trade import open_trade, get_open_trades, get_config

            cfg      = get_config()
            max_open = int(cfg["max_open"])
            opened   = get_open_trades()

            auto_opened = []
            for s in signals:
                if len(opened) >= max_open:
                    print(f"[AutoTrade] Max posisi ({max_open}) tercapai, skip {s['ticker']}")
                    break
                if any(t["ticker"] == s["ticker"] for t in opened):
                    print(f"[AutoTrade] {s['ticker']} sudah ada posisi terbuka, skip")
                    continue

                result = open_trade(s["ticker"], s["close"], notify=False)
                if "error" in result:
                    print(f"[AutoTrade] {s['ticker']} error: {result['error']}")
                else:
                    auto_opened.append(result)
                    opened.append(result)  # update local list
                    notif = (
                        f"📝 <b>Auto Paper Trade Opened</b>\n\n"
                        f"🟢 <b>{result['ticker']}</b> @ Rp {result['entry_price']:,}\n"
                        f"   📈 TP: Rp {result['tp_price']:,}\n"
                        f"   🛑 SL: Rp {result['sl_price']:,}\n"
                        f"   Lot: {result['lots']} | Modal: Rp {result['capital_used']:,.0f}"
                    )
                    send_telegram(notif)
                    print(f"[AutoTrade] Opened: {result['ticker']} @ {result['entry_price']}")

            if auto_opened:
                print(f"[AutoTrade] {len(auto_opened)} trade dibuka otomatis.")
            else:
                print(f"[AutoTrade] Tidak ada trade baru dibuka.")
        except Exception as e:
            print(f"[AutoTrade] Error: {e}")

    return signals


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
        import logging
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


def get_ticker_best_strategies(ticker: str, min_consistency: float = 50.0):
    """
    Get best strategies for ticker from WF scores.
    Returns list of strategies with consistency >= min_consistency.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT strategy, consistency_pct, weighted_score
            FROM wf_scores
            WHERE ticker = ? AND consistency_pct >= ?
            ORDER BY weighted_score DESC
        """, (ticker, min_consistency)).fetchall()
        conn.close()
        
        if not rows:
            # Fallback: use default strategies
            return ["vol_weighted", "vwap_reversion"]
        
        return [r[0] for r in rows]
    except Exception as e:
        print(f"[get_best_strategies] {ticker} error: {e}")
        return ["vol_weighted", "vwap_reversion"]  # Fallback


def scheduled_multi_strategy_scan():
    """Multi-strategy signal scanner dengan flow filter."""
    from engine.strategies import check_current_entry_signal
    from engine.calendar_filter import is_blackout_day
    from engine.sector_rotation import is_sector_tradeable, get_ticker_sector
    from flow_filter import get_flow_batch

    now = datetime.now(WIB)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    # Calendar blackout gate
    _blackout, _bl_reason = is_blackout_day()
    if _blackout:
        print(f"[{time_str}] BLACKOUT: {_bl_reason} — scan skipped.")
        send_telegram(f"⛔ <b>Multi-Scan Paused — Blackout</b>\n\n{_bl_reason}")
        return

    print(f"[{time_str}] Starting multi-strategy scan...")

    # Pre-compute sector scores once (1-hour TTL cache)
    _sector_scores = _get_sector_scores_cached()

    strategies = ["vol_weighted", "vwap_reversion"]
    flow_threshold = 2
    min_wf_consistency = 50.0

    # Get all tickers
    tickers = get_all_tickers()
    ohlcv_map = _load_ohlcv_bulk()

    # Step 1: Adaptive strategy selection per ticker
    intersection_results = []

    for ticker in tickers:
        try:
            # Sector rotation filter
            _sec_ok, _sec_reason = is_sector_tradeable(ticker, _sector_scores)
            if not _sec_ok:
                continue

            df = ohlcv_map.get(ticker)
            if df is None or len(df) < 20:
                continue

            # Get best strategies for this ticker from WF scores
            best_strategies = get_ticker_best_strategies(ticker, min_wf_consistency)
            
            # Check signals for best strategies
            passing_strategies = []
            combined_reasons = []
            combined_details = {}
            
            for strategy in best_strategies:
                signal_check = check_current_entry_signal(ticker, strategy, df=df)
                
                if signal_check['has_signal']:
                    passing_strategies.append(strategy)
                    combined_reasons.append(f"{strategy}: {signal_check['reason']}")
                    combined_details[strategy] = signal_check['details']
            
            # If ANY best strategy has signal → add to results
            if len(passing_strategies) > 0:
                _sec_entry = next((s for s in _sector_scores if s["sector"] == get_ticker_sector(ticker)), None)
                intersection_results.append({
                    'ticker':         ticker,
                    'strategies':     passing_strategies,
                    'has_signal':     True,
                    'signal_reasons': combined_reasons,
                    'signal_details': combined_details,
                    'sector':         get_ticker_sector(ticker),
                    'sector_weight':  _sec_entry["weight"] if _sec_entry else "NEUTRAL",
                    'sector_score':   _sec_entry["score"]  if _sec_entry else 0,
                })
                
        except Exception as e:
            print(f"[Scan] {ticker} error: {e}")
            continue
    print(f"[{time_str}] Adaptive strategy signals: {len(intersection_results)} tickers")
    
    if len(intersection_results) > 0:
        result_tickers = [r['ticker'] for r in intersection_results]
        try:
            flow_data = get_flow_batch(result_tickers, token=None, delay=0.8)
            for r in intersection_results:
                ticker = r['ticker']
                if ticker in flow_data:
                    flow = flow_data[ticker]
                    r['flow'] = {
                        'score': flow['score'],
                        'verdict': flow['verdict'],
                        'smart_money': flow['smart_money'],
                        'confirmed': flow['score'] >= flow_threshold,
                        'cum_delta': flow['cum_delta'],
                        'price_chg_pct': flow['price_chg_pct']
                    }
                else:
                    r['flow'] = {'score': None, 'verdict': 'UNAVAILABLE', 'confirmed': False}
        except Exception as e:
            print(f"[{time_str}] Flow fetch error: {e}")
            for r in intersection_results:
                r['flow'] = {'score': None, 'verdict': 'UNAVAILABLE', 'confirmed': False}
    
    flow_confirmed = [r for r in intersection_results if r.get('flow', {}).get('confirmed', False)]
    print(f"[{time_str}] Flow confirmed (>= +{flow_threshold}): {len(flow_confirmed)} tickers")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, scan_time TEXT, ticker TEXT,
            strategies TEXT, flow_score INTEGER, flow_verdict TEXT,
            smart_money TEXT, signal_reasons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        for r in flow_confirmed:
            flow = r.get('flow', {})
            conn.execute("INSERT INTO scheduled_signals (scan_time,ticker,strategies,flow_score,flow_verdict,smart_money,signal_reasons) VALUES (?,?,?,?,?,?,?)",
                (f"{date_str} {time_str}", r['ticker'], ",".join(r['strategies']), flow['score'], flow['verdict'], flow['smart_money'], " | ".join(r['signal_reasons'])))
        conn.commit()
        conn.close()
        print(f"[{time_str}] Saved {len(flow_confirmed)} signals to DB")
    except Exception as e:
        print(f"[{time_str}] DB save error: {e}")
    
    # Step 7: Auto-open paper trades for flow-confirmed signals
    auto_trade_results = []
    if len(flow_confirmed) > 0:
        from paper_trade import open_trade
        
        for r in flow_confirmed:
            ticker = r['ticker']
            try:
                # Get latest price from signal details
                signal_details = r.get('signal_details', {})
                first_strategy = r['strategies'][0]
                entry_price = signal_details.get(first_strategy, {}).get('price')
                
                if not entry_price:
                    print(f"[{time_str}] {ticker}: No price found, skipping")
                    continue
                
                # Check trend filter
                from paper_trade import check_trend
                trend = check_trend(ticker)
                
                if trend != 'UPTREND':
                    print(f"[{time_str}] {ticker}: Trend={trend}, skipping (not UPTREND)")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': False,
                        'reason': f'Trend: {trend}'
                    })
                    continue
                
                # Open paper trade
                trade_result = open_trade(ticker, float(entry_price), notify=False)
                
                if 'error' in trade_result:
                    print(f"[{time_str}] {ticker}: {trade_result['error']}")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': False,
                        'reason': trade_result['error']
                    })
                else:
                    print(f"[{time_str}] {ticker}: Paper trade opened - ID {trade_result['id']}, {trade_result['lots']} lots @ {entry_price}")
                    auto_trade_results.append({
                        'ticker': ticker,
                        'success': True,
                        'trade_id': trade_result['id'],
                        'entry_price': entry_price,
                        'lots': trade_result['lots'],
                        'tp_price': trade_result['tp_price'],
                        'sl_price': trade_result['sl_price'],
                        'capital_used': trade_result['capital_used']
                    })
            except Exception as e:
                print(f"[{time_str}] {ticker}: Trade open error: {e}")
                auto_trade_results.append({
                    'ticker': ticker,
                    'success': False,
                    'reason': str(e)
                })
    
    # Step 8: Send enhanced Telegram notification
    trades_opened = [t for t in auto_trade_results if t['success']]
    trades_failed = [t for t in auto_trade_results if not t['success']]
    
    if len(flow_confirmed) > 0:
        msg = f"<b>🎯 Multi-Strategy Scan @ {time_str}</b>\n\n"
        msg += f"📊 Total scanned: {len(tickers)}\n"
        msg += f"✅ Pass strategies: {len(intersection_results)}\n"
        msg += f"🟢 Flow confirmed: {len(flow_confirmed)}\n"
        msg += f"📈 Trades opened: {len(trades_opened)}\n\n"
        
        if len(trades_opened) > 0:
            msg += "<b>✅ Paper Trades Opened:</b>\n"
            for t in trades_opened[:5]:
                msg += f"\n<b>{t['ticker']}</b>\n"
                msg += f"  Entry: Rp {t['entry_price']:,.0f} x {t['lots']} lots\n"
                msg += f"  TP: Rp {t['tp_price']:,.0f} (+{((t['tp_price']/t['entry_price']-1)*100):.1f}%)\n"
                msg += f"  SL: Rp {t['sl_price']:,.0f} ({((t['sl_price']/t['entry_price']-1)*100):.1f}%)\n"
                msg += f"  Capital: Rp {t['capital_used']:,.0f}\n"
            if len(trades_opened) > 5:
                msg += f"\n... +{len(trades_opened) - 5} more trades\n"
        
        if len(trades_failed) > 0:
            msg += f"\n<b>⚠️ Failed ({len(trades_failed)}):</b>\n"
            for t in trades_failed[:3]:
                msg += f"  • {t['ticker']}: {t['reason'][:40]}\n"
        
        # Add signals without trades
        no_trade = [r for r in flow_confirmed if r['ticker'] not in [t['ticker'] for t in auto_trade_results]]
        if len(no_trade) > 0:
            msg += f"\n<b>📊 Other Signals ({len(no_trade)}):</b>\n"
            for r in no_trade[:3]:
                flow = r.get('flow', {})
                msg += f"  • {r['ticker']}: Flow {flow['score']:+d}\n"
        
        send_telegram(msg)
    else:
        print(f"[{time_str}] No flow-confirmed signals (strategy pass: {len(intersection_results)}). Telegram suppressed.")
    print(f"[{time_str}] Multi-strategy scan complete.\n")

def _run_open_trade_monitor():
    try:
        from monitor import check_all_open_trades
        check_all_open_trades()
    except Exception as e:
        print(f"[scheduler] Monitor error: {e}")


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


def daily_fetch_report():
    """Generate daily OHLCV fetch report and send to Telegram."""
    try:
        from datetime import datetime as dt, timedelta
        import sqlite3

        now = dt.now(WIB)
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d/%m/%Y")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Count total tickers
        total_tickers = cursor.execute(
            "SELECT COUNT(DISTINCT ticker) FROM ohlcv"
        ).fetchone()[0]

        # Get latest date in database
        latest_date = cursor.execute(
            "SELECT MAX(date) FROM ohlcv"
        ).fetchone()[0]

        # Count records for latest date
        latest_count = cursor.execute(
            "SELECT COUNT(*) FROM ohlcv WHERE date = ?", (latest_date,)
        ).fetchone()[0]

        # Get tickers without recent data (older than 3 days)
        three_days_ago = (dt.now(WIB) - timedelta(days=3)).strftime("%Y-%m-%d")
        stale_tickers = cursor.execute(
            f"SELECT DISTINCT ticker FROM ohlcv WHERE ticker NOT IN (SELECT DISTINCT ticker FROM ohlcv WHERE date > '{three_days_ago}') ORDER BY ticker"
        ).fetchall()
        stale_count = len(stale_tickers)

        # Get average records per ticker
        avg_records = cursor.execute(
            "SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM ohlcv GROUP BY ticker)"
        ).fetchone()[0]

        # Get data completeness for last 5 days
        five_days_ago = (dt.now(WIB) - timedelta(days=5)).strftime("%Y-%m-%d")
        complete_tickers = cursor.execute(
            f"SELECT COUNT(DISTINCT ticker) FROM (SELECT ticker, COUNT(DISTINCT date) as cnt FROM ohlcv WHERE date >= '{five_days_ago}' GROUP BY ticker HAVING cnt >= 4)"
        ).fetchone()[0]

        # Flow fetch counts for today
        today_str = now.strftime("%Y-%m-%d")
        try:
            flow_conn = sqlite3.connect(DB_PATH)
            flow_ticker_count = flow_conn.execute(
                "SELECT COUNT(DISTINCT ticker) FROM stockbit_flow WHERE trade_date=?", (today_str,)
            ).fetchone()[0]
            broker_ticker_count = flow_conn.execute(
                "SELECT COUNT(DISTINCT ticker) FROM broker_flow WHERE trade_date=?", (today_str,)
            ).fetchone()[0]
            flow_conn.close()
        except Exception:
            flow_ticker_count = 0
            broker_ticker_count = 0

        conn.close()

        flow_ok = flow_ticker_count > 0
        broker_ok = broker_ticker_count > 0

        # Build report message
        msg = f"📊 <b>Daily Fetch Report — {date_str} {time_str}</b>\n\n"
        msg += f"<b>OHLCV:</b>\n"
        msg += f"  • Total tickers: <b>{total_tickers}</b>\n"
        msg += f"  • Latest date: <b>{latest_date}</b>\n"
        msg += f"  • Updated today: <b>{latest_count}/{total_tickers}</b>\n"
        msg += f"  • Complete (5-day): <b>{complete_tickers}/{total_tickers}</b>\n"
        msg += f"  • Avg records/ticker: <b>{avg_records:.0f}</b>\n"

        msg += f"\n<b>Flow:</b>\n"
        flow_emoji = "✅" if flow_ok else "❌"
        msg += f"  {flow_emoji} Stockbit flow: <b>{flow_ticker_count} tickers</b>\n"
        broker_emoji = "✅" if broker_ok else "❌"
        msg += f"  {broker_emoji} Broker flow: <b>{broker_ticker_count} tickers</b>\n"

        if stale_count > 0:
            msg += f"\n⚠️ <b>Stale Data ({stale_count} tickers):</b>\n"
            stale_list = [t[0] for t in stale_tickers[:10]]
            msg += f"  {', '.join(stale_list)}"
            if stale_count > 10:
                msg += f", +{stale_count - 10} more"
            msg += "\n"

        send_telegram(msg)
        print(f"[{time_str}] Daily fetch report sent ({total_tickers} tickers, latest: {latest_date})")

    except Exception as e:
        print(f"[daily_fetch_report] Error: {e}")
        send_telegram(f"🔴 <b>Fetch Report Error</b>\n\n<code>{str(e)[:150]}</code>")


def open_trades_status_report():
    """Send open trades status only when PnL changes ≥1% or trade count/status changes."""
    global _last_trades_state
    try:
        from datetime import datetime as dt
        from paper_trade import get_open_trades

        now = dt.now(WIB)
        time_str = now.strftime("%H:%M")

        trades = get_open_trades()

        # Detect trade-count change vs last run
        prev_ids = set(_last_trades_state.keys())
        cur_ids  = {str(t['id']) for t in trades} if trades else set()
        count_changed = prev_ids != cur_ids

        if not trades:
            if count_changed:
                msg = f"📊 <b>Open Trades Report — {time_str}</b>\n\n"
                msg += "✅ No open trades."
                send_telegram(msg)
                print(f"[{time_str}] Open trades report sent (0 trades)")
                _last_trades_state = {}
            else:
                print(f"[{time_str}] No trades, no change — report suppressed.")
            return

        # Get current prices
        conn = sqlite3.connect(DB_PATH)

        msg = f"📊 <b>Open Trades Report — {time_str}</b>\n\n"

        total_capital = 0
        total_pnl_rp = 0
        total_pnl_pct = 0
        trades_by_status = {'PROFIT': [], 'LOSS': [], 'BREAKEVEN': []}
        current_state = {}  # {trade_id: {"pnl_pct": float, "status_key": str}}

        for i, trade in enumerate(trades, 1):
            ticker = trade['ticker']
            trade_id = str(trade['id'])
            entry_price = trade['entry_price']
            tp_price = trade['tp_price']
            sl_price = trade['sl_price']
            lots = trade['lots']
            capital = trade['capital_used']

            # Get latest price
            latest = conn.execute(
                'SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 1',
                (ticker,)
            ).fetchone()

            if not latest:
                continue

            current_price = latest[0]

            # Calculate metrics
            price_change = current_price - entry_price
            price_change_pct = (price_change / entry_price * 100) if entry_price > 0 else 0

            # % to TP and SL (guard against NULL tp_price / sl_price in DB)
            tp_distance = (tp_price - entry_price) if tp_price is not None else 0
            sl_distance = (entry_price - sl_price) if sl_price is not None else 0
            pct_to_tp = (price_change / tp_distance * 100) if tp_distance > 0 else 0
            pct_to_sl = ((entry_price - current_price) / sl_distance * 100) if sl_distance > 0 else 0
            remaining_to_tp_pct = ((tp_price - current_price) / current_price * 100) if (tp_price is not None and current_price > 0) else 0

            # P&L calculation
            pnl_rp = price_change * lots * 100
            pnl_pct = (price_change / entry_price * 100) if entry_price > 0 else 0

            # Check if trade is at risk
            is_past_sl = (sl_price is not None) and (current_price < sl_price)
            is_at_sl = (sl_price is not None) and (abs(current_price - sl_price) < 1)

            # Emoji based on status
            if is_past_sl:
                emoji = "🚨"  # Critical - past SL
                status_key = 'LOSS'
            elif is_at_sl:
                emoji = "⚠️"  # At SL
                status_key = 'LOSS'
            elif pnl_rp > 0:
                emoji = "🟢"
                status_key = 'PROFIT'
            elif pnl_rp < 0:
                emoji = "🔴"
                status_key = 'LOSS'
            else:
                emoji = "⚪"
                status_key = 'BREAKEVEN'

            current_state[trade_id] = {"pnl_pct": round(pnl_pct, 2), "status_key": status_key}

            # Trade details
            trade_msg = f"{emoji} <b>{ticker}</b> @ Rp {current_price:,.0f}\n"
            trade_msg += f"   Entry: Rp {entry_price:,.0f} | Change: {price_change_pct:+.2f}% ({price_change:+.0f})\n"
            if tp_price is not None:
                trade_msg += f"   📈 TP: Rp {tp_price:,.0f} (+{remaining_to_tp_pct:.1f}% to reach | {pct_to_tp:.1f}% covered)\n"
            else:
                trade_msg += f"   📈 TP: N/A\n"
            if sl_price is not None:
                trade_msg += f"   🛑 SL: Rp {sl_price:,.0f}"
            else:
                trade_msg += f"   🛑 SL: N/A"

            if is_past_sl:
                trade_msg += f" ⚠️ <b>PAST SL by {(sl_price - current_price):,.0f}</b>"
            elif is_at_sl:
                trade_msg += f" ⚠️ <b>AT SL</b>"
            elif sl_price is not None:
                risk_remaining = max(0.0, ((entry_price - current_price) / sl_distance * 100) if sl_distance > 0 else 0)
                trade_msg += f" ({risk_remaining:.1f}% risk used)"

            trade_msg += f"\n   💰 P&L: Rp {pnl_rp:+,.0f} ({pnl_pct:+.2f}%)\n"

            msg += trade_msg

            total_capital += (capital or 0)
            total_pnl_rp += pnl_rp
            trades_by_status[status_key].append((ticker, pnl_rp))

        conn.close()

        # Check whether anything meaningful changed vs last report
        def _should_send():
            if count_changed:
                return True, "trade count changed"
            for tid, cur in current_state.items():
                prev = _last_trades_state.get(tid)
                if prev is None:
                    return True, f"new trade {tid}"
                if cur["status_key"] != prev["status_key"]:
                    return True, f"status change on {tid}"
                if abs(cur["pnl_pct"] - prev["pnl_pct"]) >= 1.0:
                    return True, f"PnL moved ≥1% on {tid}"
            return False, "no significant change"

        should_send, change_reason = _should_send()
        if not should_send:
            print(f"[{time_str}] Open trades report suppressed ({change_reason}, {len(trades)} trades)")
            return

        # Summary
        msg += f"\n<b>📈 Summary ({len(trades)} trades):</b>\n"
        msg += f"   Total Capital: Rp {total_capital:,.0f}\n"
        msg += f"   Total P&L: Rp {total_pnl_rp:+,.0f}\n"

        if total_capital > 0:
            total_pnl_pct = (total_pnl_rp / total_capital * 100)
            msg += f"   Total Return: {total_pnl_pct:+.2f}%\n"

        # Breakdown
        msg += f"\n   ✅ Profit: {len(trades_by_status['PROFIT'])} | "
        msg += f"❌ Loss: {len(trades_by_status['LOSS'])} | "
        msg += f"⚪ Breakeven: {len(trades_by_status['BREAKEVEN'])}\n"

        send_telegram(msg)
        _last_trades_state.update(current_state)
        print(f"[{time_str}] Open trades report sent ({len(trades)} trades, P&L: {total_pnl_rp:+,.0f}, reason: {change_reason})")

    except Exception as e:
        print(f"[open_trades_status_report] Error: {e}")
        send_telegram(f"🔴 <b>Open Trades Report Error</b>\n\n<code>{str(e)[:150]}</code>")


def flow_broker_report():
    """Report at 17:15 — Flow sentiment summary with actionable trades."""
    now = datetime.now(WIB).strftime("%d/%m/%Y %H:%M")
    try:
        from flow_filter import get_flow_batch
        try:
            from news_filter import has_news_spike, get_spiking_tickers, get_today_headlines
        except Exception as _ne:
            logging.warning(f"news_filter import failed: {_ne}")
            has_news_spike = lambda *a, **kw: None
            get_spiking_tickers = lambda *a, **kw: []
            get_today_headlines = lambda *a, **kw: []

        # Get today's signals (from 16:00 scan)
        conn = sqlite3.connect(DB_PATH)
        signals = pd.read_sql(
            'SELECT ticker FROM daily_screen WHERE date = date("now") AND signal IS NOT NULL ORDER BY ticker',
            conn
        )
        conn.close()

        if signals.empty:
            msg = f"📊 <b>Market Flow Sentiment — {now}</b>\n\nNo signals today."
            send_telegram(msg)
            return

        tickers = signals['ticker'].tolist()

        # Fetch flow data for all tickers
        try:
            flow_data = get_flow_batch(tickers, token=None, delay=0.8)
        except Exception as e:
            send_telegram(f"🔴 <b>Flow Report Error</b>\n\n<code>{str(e)[:150]}</code>")
            return

        # News-spike lookup for the signal tickers (built by 17:00 news fetch)
        spike_map = {}
        for t in tickers:
            sp = has_news_spike(t)
            if sp and sp["is_spike"]:
                spike_map[t] = sp

        # Categorize by sentiment
        bullish = []
        neutral_buy = []
        bearish = []
        divergence_bullish = []  # bearish flow with price up
        divergence_bearish = []  # bullish flow with price down

        for ticker, f in flow_data.items():
            verdict = f.get('verdict', 'N/A')
            score = f.get('score', 0)
            smart = f.get('smart_money', 'N/A')
            value_smart = f.get('value_smart_money', 'N/A')
            divergence = f.get('divergence', '')
            price_chg = f.get('price_chg_pct', 0)

            # Detect divergence opportunities
            if divergence == 'BEARISH_DIV':
                # Delta up but price down — bullish setup
                divergence_bullish.append((ticker, score, smart, value_smart, price_chg))
            elif divergence == 'BULLISH_DIV':
                # Delta down but price up — bearish setup
                divergence_bearish.append((ticker, score, smart, value_smart, price_chg))

            # Regular categorization
            if verdict == 'BULLISH':
                bullish.append((ticker, score, smart, value_smart))
            elif verdict == 'NEUTRAL' and ('BUY' in smart or score >= 1):
                neutral_buy.append((ticker, score, smart, value_smart))
            else:
                bearish.append((ticker, score, smart, value_smart))

        msg = f"📊 <b>Market Flow Sentiment — {now}</b>\n\n"

        # Summary
        msg += f"<b>Sentiment:</b> "
        msg += f"🟢 {len(bullish)} bullish | "
        msg += f"🟡 {len(neutral_buy)} neutral (buy) | "
        msg += f"🔴 {len(bearish)} bearish"
        if divergence_bullish or divergence_bearish:
            msg += f" | ⚡ {len(divergence_bullish) + len(divergence_bearish)} divergence"
        if spike_map:
            msg += f" | 📰 {len(spike_map)} news-spike"
        msg += "\n\n"

        def _spike_tag(tk):
            sp = spike_map.get(tk)
            return f" 📰×{sp['ratio']}" if sp else ""

        def _smart_tag(lot_sm, val_sm):
            """Show value_smart_money in brackets when it differs from lot-based."""
            if val_sm and val_sm != 'N/A' and val_sm != lot_sm:
                return f"{lot_sm} [💰{val_sm}]"
            return lot_sm

        # Show bullish/neutral opportunities
        if bullish or neutral_buy:
            msg += "<b>🟢 BUY SIGNALS:</b>\n"
            for t, s, m, vm in (bullish + neutral_buy)[:5]:
                msg += f"  {t}{_spike_tag(t)}: Smart={_smart_tag(m, vm)} (score {s:+.0f})\n"
        else:
            msg += "⚠️ <b>No bullish signals today</b>\n"
            if neutral_buy or len(neutral_buy) == 0:
                msg += "Market showing strong selling pressure\n"

        # Show divergence opportunities
        if divergence_bullish or divergence_bearish:
            msg += "\n<b>⚡ DIVERGENCE ALERTS:</b>\n"
            if divergence_bullish:
                msg += "  <b>🟢 Bullish Divergence (flow up, price down):</b>\n"
                for t, s, m, vm, pc in divergence_bullish[:3]:
                    msg += f"    {t}{_spike_tag(t)}: {pc:+.1f}% Smart={_smart_tag(m, vm)} (score {s:+.0f})\n"
            if divergence_bearish:
                msg += "  <b>🔴 Bearish Divergence (flow down, price up):</b>\n"
                for t, s, m, vm, pc in divergence_bearish[:3]:
                    msg += f"    {t}{_spike_tag(t)}: {pc:+.1f}% Smart={_smart_tag(m, vm)} (score {s:+.0f})\n"

        # News-spike attention alerts — show top ratio with first headline
        if spike_map:
            ranked = sorted(spike_map.values(), key=lambda x: x["ratio"], reverse=True)
            msg += "\n<b>📰 NEWS-SPIKE ATTENTION (today vs 30d avg):</b>\n"
            for sp in ranked[:5]:
                t = sp["ticker"]
                heads = get_today_headlines(t)
                first = heads[0][:80] if heads else ""
                msg += f"  ⚡ {t}: {sp['today_count']} today vs {sp['avg_30d']:.1f} avg ({sp['ratio']}×)\n"
                if first:
                    msg += f"      └ {first}\n"

        send_telegram(msg)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Flow report sent "
              f"({len(bullish)} bullish, {len(neutral_buy)} neutral, "
              f"{len(divergence_bullish)+len(divergence_bearish)} divergence, "
              f"{len(spike_map)} news-spike)")
    except Exception as e:
        logging.error(f"flow_broker_report error: {e}")
        send_telegram(f"🔴 <b>Flow Report Error</b>\n\n<code>{str(e)[:150]}</code>")


def auto_trade_status_report():
    """Report at 09:00 — Auto-trading status (success/failed) from previous day."""
    now = datetime.now(WIB).strftime("%d/%m/%Y %H:%M")
    try:
        conn = sqlite3.connect(DB_PATH)

        # Get last auto-trade results from yesterday
        yesterday = (datetime.now() - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")

        cursor = conn.execute('''
            SELECT ticker, status, entry_price, entry_date, tp_price, sl_price, pnl_rp
            FROM paper_trades
            WHERE entry_date >= ?
            ORDER BY entry_date DESC
            LIMIT 10
        ''', (yesterday,))

        trades = cursor.fetchall()
        conn.close()

        msg = f"🤖 <b>Auto-Trade Status — {now}</b>\n\n"

        if not trades:
            msg += "No auto-trades from previous day.\n\n"
        else:
            open_count = sum(1 for t in trades if t[1] == 'OPEN')
            closed_count = sum(1 for t in trades if t[1] == 'CLOSED')
            total_pnl = sum(t[6] if t[6] else 0 for t in trades if t[1] == 'CLOSED')

            msg += f"<b>Summary:</b>\n"
            msg += f"  ✅ Opened: {open_count} trades\n"
            msg += f"  ✓ Closed: {closed_count} trades\n"
            msg += f"  💰 P&L: Rp {total_pnl:+,.0f}\n\n"

            msg += f"<b>Details:</b>\n"
            for t in trades[:5]:
                ticker, status, entry, entry_date, tp, sl, pnl = t
                emoji = "🟢" if status == "OPEN" else "✓" if pnl and pnl > 0 else "❌"
                msg += f"{emoji} {ticker}: {status} @ Rp {entry:,.0f}\n"

        send_telegram(msg)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Auto-trade status report sent")
    except Exception as e:
        logging.error(f"auto_trade_status_report error: {e}")
        send_telegram(f"🔴 <b>Auto-Trade Status Error</b>\n\n<code>{str(e)[:150]}</code>")


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


def start_scheduler():
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
