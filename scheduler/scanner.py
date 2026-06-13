# scheduler/scanner.py
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime
import pytz
import pandas as pd

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402
from scheduler.state import _regime_clf_cache  # noqa: E402  — dict; _sector_scores_cache handled inside _get_sector_scores_cached via scheduler.state ref
from scheduler.utils import get_all_tickers, _load_ohlcv_bulk, fetch_latest  # noqa: E402


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

def _detect_price_shock(df, pct: float = 0.20, window: int = 5) -> bool:
    """True if the most-recent close is down >= pct from the close window bars ago.

    Endpoint-only check: intermediate lows are not considered.
    Assumes df is sorted date-ascending (as returned by _load_ohlcv_bulk).
    """
    if df is None or len(df) < window + 1:
        return False
    closes = df['close'].iloc[-(window + 1):]
    base = closes.iloc[0]
    if base <= 0:
        return False
    return bool((closes.iloc[-1] - base) / base <= -pct)


def _load_stockbit_token(_token_file: str = None) -> str:
    """Read Stockbit JWT from .stockbit_token. Returns None if missing, unreadable, or not a 3-segment JWT."""
    if _token_file is None:
        _token_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".stockbit_token")
    try:
        with open(_token_file, 'r') as f:
            t = f.read().strip()
        return t if t.startswith('eyJ') and len(t.split('.')) == 3 else None
    except Exception:
        return None


def check_keystats_freshness(ticker: str, df, stale_threshold: int = 30,
                             _db_path: str = None, _token_file: str = None):
    """
    Returns (ok: bool, reason: str).
    Stale + price shock: attempts re-fetch via Stockbit API.
      - Re-fetch success: (True,  'refreshed:{N}d')
      - No token:         (False, 'stale_shock:{N}d,no_token')
      - API returns None: (False, 'stale_shock:{N}d,fetch_empty')
      - API exception:    (False, 'stale_shock:{N}d,fetch_error')
    Stale + no shock:     (True,  'stale:{N}d')   — allow through
    Fresh:                (True,  'OK')
    No data:              (True,  'no_data')
    """
    db = _db_path or DB_PATH
    try:
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                'SELECT fetch_date FROM stockbit_keystats WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1',
                (ticker,)
            ).fetchone()
    except Exception:
        return True, 'db_error'

    if not row:
        return True, 'no_data'

    from datetime import date as _date
    try:
        fetch_date = _date.fromisoformat(row[0])
    except Exception:
        return True, 'bad_date'

    stale_days = (_date.today() - fetch_date).days

    if stale_days <= stale_threshold:  # inclusive: day 30 is still fresh
        return True, 'OK'

    if not _detect_price_shock(df):
        logging.debug(f"[keystats] {ticker} stale:{stale_days}d, no shock — allow")
        return True, f'stale:{stale_days}d'

    # Stale + price shock — attempt re-fetch
    token = _load_stockbit_token(_token_file)
    if not token:
        logging.info(f"[keystats] {ticker} stale_shock:{stale_days}d — no token, blocking")
        return False, f'stale_shock:{stale_days}d,no_token'

    try:
        from stockbit_fetcher import fetch_keystats, save_keystats
        stats = fetch_keystats(token, ticker)
        if not stats:
            logging.info(f"[keystats] {ticker} stale_shock:{stale_days}d — fetch empty, blocking")
            return False, f'stale_shock:{stale_days}d,fetch_empty'
        with sqlite3.connect(db) as conn2:
            save_keystats(conn2, stats)
            conn2.commit()
        logging.info(
            f"[keystats] {ticker} refreshed after {stale_days}d stale — "
            f"PE={stats.get('pe_ttm')} ROE={stats.get('roe')}"
        )
        return True, f'refreshed:{stale_days}d'
    except Exception as _e:
        logging.warning(f"[keystats] {ticker} re-fetch error: {_e}")
        return False, f'stale_shock:{stale_days}d,fetch_error'


def _get_sector_scores_cached():
    """Return score_sectors() cached for up to 1 hour."""
    import time
    import scheduler.state as _state
    from engine.sector_rotation import score_sectors
    scores, ts = _state._sector_scores_cache
    if scores is not None and (time.time() - ts) < 3600:
        return scores
    scores = score_sectors()
    _state._sector_scores_cache = (scores, time.time())
    return scores


# ── sectors.app overlay (env-gated) ──────────────────────────────────
# SECTORS_APP_MODE: off (default) | shadow | enforce
#   off     → internal sector_rotation only (legacy behavior)
#   shadow  → internal decides; log when sectors.app disagrees
#   enforce → both must agree to greenlight
def _sector_verdict(ticker, scored):
    mode = os.getenv("SECTORS_APP_MODE", "off").strip().lower()
    if mode == "off":
        from engine.sector_rotation import is_sector_tradeable
        return is_sector_tradeable(ticker, scored)

    try:
        from engine.sectors_app_filter import combined_sector_verdict, _lookup_sector
        from engine.sector_rotation import is_sector_tradeable, get_ticker_sector
    except Exception:
        from engine.sector_rotation import is_sector_tradeable
        return is_sector_tradeable(ticker, scored)

    internal_ok, internal_reason = is_sector_tradeable(ticker, scored)

    if mode == "shadow":
        sa = _lookup_sector(get_ticker_sector(ticker))
        sa_chg = sa.get("chg_30d") if sa else None
        if sa_chg is not None:
            sa_ok = sa_chg > -15.0
            if sa_ok != internal_ok:
                logging.info(
                    f"[sectors.app SHADOW] {ticker} disagreement — "
                    f"internal={internal_ok} ({internal_reason}); "
                    f"sectors.app 30d={sa_chg:+.2f}% (ok={sa_ok})"
                )
        return internal_ok, internal_reason

    # enforce
    return combined_sector_verdict(ticker, scored)


def scan_momentum_signals():
    """Scan semua ticker untuk Momentum Following signal hari ini."""
    from engine.indicators import calc_vol_ratio, calc_relative_strength
    from engine.calendar_filter import is_blackout_day, is_trading_day
    from engine.sector_rotation import is_sector_tradeable

    # Market-closed gate — skip entirely on weekends and IDX public holidays
    _open, _closed_reason = is_trading_day()
    if not _open:
        logging.info(f"[scan_momentum] Pasar tutup: {_closed_reason} — scan dilewati.")
        return []

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
    _f_liquidity   = int(_cfg.get("filter_liquidity",   0))

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

    # R16: flush indicator cache at scan start
    from engine.indicators import clear_indicator_cache as _clear_ic_single
    _clear_ic_single()

    # Phase 3: flush agent firm market context cache
    try:
        from engine.agent_firm.firm import reset_market_ctx as _reset_mctx_single
        _reset_mctx_single()
    except Exception:
        pass

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
        df = ohlcv_map.get(ticker)
        # Fundamental filter
        if _f_fundamental:
            freshness_ok, fresh_reason = check_keystats_freshness(ticker, df)
            if not freshness_ok:
                logging.info(f"[scan_momentum] {ticker} blocked: {fresh_reason}")
                continue
            fund_ok, fund_reason = check_fundamental(ticker)
            if not fund_ok:
                continue
        else:
            flow_reason = "fundamental filter OFF"

        # Liquidity + value filter (L3) — blocks illiquid or bottom-quartile tickers
        if _f_liquidity:
            from engine.liquidity import passes_liquidity_gate as _liq_gate, passes_value_gate as _val_gate
            _liq_conn = sqlite3.connect(DB_PATH)
            try:
                _liq_ok, _liq_reason = _liq_gate(_liq_conn, ticker, _today_str)
                _val_ok, _val_reason = _val_gate(_liq_conn, ticker)
            finally:
                _liq_conn.close()
            if not _liq_ok:
                logging.debug(f"[scan_momentum] {ticker} blocked by liquidity: {_liq_reason}")
                continue
            if not _val_ok:
                logging.debug(f"[scan_momentum] {ticker} blocked by value: {_val_reason}")
                continue

        # Sector rotation filter — skip UNDERWEIGHT sectors
        # Routed through _sector_verdict so SECTORS_APP_MODE can layer
        # sectors.app data on top without touching this loop.
        if _f_sector:
            _sec_ok, _sec_reason = _sector_verdict(ticker, _sector_scores)
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
                from engine.vpin import calc_vpin_multi as _calc_vpin_multi
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
            if df is None or len(df) < 25:
                continue
            vr     = calc_vol_ratio(df)
            streak = (df["close"] > df["close"].shift(1)) & (df["close"].shift(1) > df["close"].shift(2))
            # Gap-up after a >1-day calendar break (weekend/holiday) fires even
            # without a 2-bar streak — the streak check fails across the gap. 1%
            # floor keeps tiny weekend drift from triggering false signals.
            _date_diff = pd.to_datetime(df["date"]).diff().dt.days
            _gap_up = (df["close"] > df["close"].shift(1) * 1.01) & (_date_diff > 1)
            sig    = (streak | _gap_up) & (vr > 1.3) & (vr <= 5.0)
            if sig.iloc[-1]:
                # Signal quality gate — block 'watch' (100% loss rate in audit)
                try:
                    _sig_conn = sqlite3.connect(DB_PATH)
                    _sig_row = _sig_conn.execute(
                        "SELECT signal, delta FROM daily_screen WHERE ticker=? AND date=?",
                        (ticker, _today_str)
                    ).fetchone()
                    _sig_conn.close()
                    if _sig_row:
                        _sig_label, _delta = _sig_row
                        if _sig_label == 'watch':
                            logging.debug(f"[scan_momentum] {ticker} blocked by signal=watch (100% loss rate)")
                            continue
                        # Delta confirmation: low delta + non-bullish → skip
                        if _sig_label != 'bullish' and _delta is not None and _delta < 50_000:
                            logging.debug(f"[scan_momentum] {ticker} blocked by low delta ({_delta})")
                            continue
                except Exception:
                    pass  # no screen data today — soft pass

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
    # Momentum-family entries are blocked during macro panic state
    # (Daniel-Moskowitz) and the MSCI event-risk window.
    _guard_on, _guard_mult = _event_guard_active()
    if signals and _macro_panic_state():
        print(f"[AutoTrade] Macro panic state — momentum entries blocked ({len(signals)} signals skipped)")
        signals_to_open = []
    elif signals and _guard_on:
        print(f"[AutoTrade] Event guard active — momentum entries blocked ({len(signals)} signals skipped)")
        signals_to_open = []
    else:
        signals_to_open = signals

    if signals_to_open:
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from paper_trade import open_trade, get_open_trades, get_config, get_backtest_best

            cfg      = get_config()
            max_open = int(cfg["max_open"])
            opened   = get_open_trades()

            auto_opened = []
            for s in signals_to_open:
                if len(opened) >= max_open:
                    print(f"[AutoTrade] Max posisi ({max_open}) tercapai, skip {s['ticker']}")
                    break
                if any(t["ticker"] == s["ticker"] for t in opened):
                    print(f"[AutoTrade] {s['ticker']} sudah ada posisi terbuka, skip")
                    continue

                # Quality gate — skip entries the backtest rates as coin-flips.
                # POWR-class trades (~0.7% predicted return, <40% win rate) bleed capital.
                _bt = get_backtest_best(s["ticker"])
                if _bt is not None:
                    _bt_ret = _bt["best_return"] if _bt["best_return"] is not None else 0.0
                    _bt_wr  = _bt["win_rate"]    if _bt["win_rate"]    is not None else 0.0
                    if _bt_ret < 1.0 or _bt_wr < 40.0:
                        print(f"[AutoTrade] {s['ticker']} skipped — backtest weak "
                              f"(ret={_bt_ret:.2f}%, win={_bt_wr:.0f}%)")
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


def get_ticker_best_strategies(ticker: str, min_consistency: float = 50.0):
    """
    Get best strategies for ticker from WF scores.
    Returns list of strategies with consistency >= min_consistency AND a
    positive walk-forward return. No fallback: a ticker with no profitable
    strategy generates no BUY signal (2026-06-13 audit — the old
    vol_weighted/vwap_reversion fallback routed money-losing strategies).
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT strategy, consistency_pct, weighted_score
            FROM wf_scores
            WHERE ticker = ? AND consistency_pct >= ?
              AND avg_return_pct > 0 AND weighted_score > 0
            ORDER BY weighted_score DESC
        """, (ticker, min_consistency)).fetchall()
        conn.close()
        disabled = _get_disabled_strategies()
        return [r[0] for r in rows if r[0] not in disabled]
    except Exception as e:
        print(f"[get_best_strategies] {ticker} error: {e}")
        return []


# Regime → preferred strategy candidates.
# Keys: BULL_MODERATE (ADX 25-45), BULL_STRONG (ADX >=45), BEAR, SIDEWAYS.
# Strategy names match STRATEGY_FUNCS keys in engine/walkforward_multi.py.
# 2026-06-13 audit: SIDEWAYS used to route vwap_reversion/vol_weighted —
# both lose money in every regime bucket. BEAR now allows Crash Recovery
# (+3.3%/window in the 2026 bear) instead of nothing. Panic Rebound trades
# single-stock washouts in BEAR/SIDEWAYS tickers but is stripped whenever
# the MACRO panic state is on (its walkforward edge inverts in market-wide
# panics — see the v1-v4 history above strategy_panic_rebound).
_REGIME_STRATEGY_MAP = {
    'BULL_MODERATE': ['Trend Following Breakout', 'momentum',
                      'Inside Bar Breakout', 'NR7 Breakout'],
    'BULL_STRONG':   ['conservative', 'momentum', 'Trend Following Breakout'],
    'BEAR':          ['Crash Recovery', 'Panic Rebound'],
    'SIDEWAYS':      ['Panic Rebound'],
}
_BULL_STRONG_ADX = 45.0

# Counter-trend strategies: event-driven, gated by their own signal checkers.
# They bypass the wf_scores consistency gate (too few historical windows) and
# survive the macro panic gate — they are the panic-state book.
_COUNTER_TREND_BOOK = {'Crash Recovery', 'Panic Rebound'}

# Momentum/trend family — blocked in macro panic state (Daniel-Moskowitz:
# momentum crashes concentrate in post-decline high-vol rebounds) and during
# binary event-risk windows (MSCI review).
_MOMENTUM_FAMILY = {
    'momentum', 'Trend Following Breakout', 'Inside Bar Breakout',
    'NR7 Breakout', 'ORB', 'orb_intraday', 'ORB_intraday',
    'Swing Trend', 'conservative', 'Momentum Following',
}

_DEFAULT_DISABLED = 'vwap_reversion,vol_weighted,conservative'


def _get_disabled_strategies() -> set:
    """Strategies suppressed from live BUY signal generation (paper_config
    key 'disabled_strategies', csv). Default: the three strategies with
    negative walk-forward returns in every regime (2026-06-13 audit)."""
    try:
        from paper_trade import get_config
        raw = str(get_config().get('disabled_strategies', _DEFAULT_DISABLED))
    except Exception:
        raw = _DEFAULT_DISABLED
    return {s.strip() for s in raw.split(',') if s.strip()}


_macro_panic_cache = {}


def _macro_panic_state() -> bool:
    """Daniel-Moskowitz panic-state gate: IHSG below its 200-day MA AND 20-day
    realized vol above the 75th percentile of the trailing year. Cached per day."""
    import datetime as _dtm
    today = str(_dtm.date.today())
    if today in _macro_panic_cache:
        return _macro_panic_cache[today]
    panic = False
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT close FROM ohlcv WHERE ticker='IHSG' "
            "ORDER BY date DESC LIMIT 260"
        ).fetchall()
        conn.close()
        closes = pd.Series([r[0] for r in reversed(rows)], dtype=float)
        if len(closes) >= 210:
            below_ma = closes.iloc[-1] < closes.rolling(200).mean().iloc[-1]
            rets = closes.pct_change().dropna()
            vol20 = rets.rolling(20).std().dropna()
            high_vol = vol20.iloc[-1] > vol20.quantile(0.75)
            panic = bool(below_ma and high_vol)
    except Exception as e:
        logging.warning(f"[panic_state] error: {e}")
    _macro_panic_cache.clear()
    _macro_panic_cache[today] = panic
    return panic


def _event_guard_active():
    """Binary event-risk window (default: MSCI accessibility review Jun 18 +
    classification decision Jun 23, 2026, with buffer). During the window all
    new momentum-family entries are blocked and position size is multiplied
    by event_guard_size_mult. Configurable via paper_config."""
    import datetime as _dtm
    try:
        from paper_trade import get_config
        cfg = get_config()
    except Exception:
        cfg = {}
    start = str(cfg.get('event_guard_start', '2026-06-15'))
    end = str(cfg.get('event_guard_end', '2026-06-24'))
    try:
        mult = float(cfg.get('event_guard_size_mult', 0.5))
    except Exception:
        mult = 0.5
    today = str(_dtm.date.today())
    return (start <= today <= end), mult


def adaptive_strategy_selector(ticker: str, df: pd.DataFrame,
                                min_consistency: float = 50.0) -> list:
    """
    Select strategies for ticker based on current regime and WF consistency.

    1. Detect regime (BULL/BEAR/SIDEWAYS) via detect_regime(df).
    2. For BULL, compute ADX to pick MODERATE vs STRONG sub-band.
    3. Look up preferred strategies for the sub-band.
    4. Counter-trend book (Crash Recovery, Panic Rebound) passes straight
       through — event-driven, own signal checkers gate hard, and too few
       wf windows exist to demand consistency history.
    5. Other candidates must exist in wf_scores with consistency >=
       min_consistency AND positive walk-forward return.
    6. Macro panic state / event guard strip the momentum family.
    7. Disabled strategies (paper_config) are always stripped.
    """
    from engine.regime_filter import detect_regime
    from engine.indicators import calc_adx

    try:
        regime = detect_regime(df)
    except Exception:
        regime = 'SIDEWAYS'

    if regime == 'BULL':
        try:
            adx_val = float(calc_adx(df, 14).iloc[-1])
        except Exception:
            adx_val = 0.0
        sub_band = 'BULL_STRONG' if adx_val >= _BULL_STRONG_ADX else 'BULL_MODERATE'
    elif regime == 'BEAR':
        sub_band = 'BEAR'
    else:
        sub_band = 'SIDEWAYS'

    candidates = list(_REGIME_STRATEGY_MAP.get(sub_band, []))

    counter_trend = [c for c in candidates if c in _COUNTER_TREND_BOOK]
    wf_candidates = [c for c in candidates if c not in _COUNTER_TREND_BOOK]

    selected = []
    if wf_candidates:
        try:
            conn = sqlite3.connect(DB_PATH)
            placeholders = ','.join('?' * len(wf_candidates))
            rows = conn.execute(f"""
                SELECT strategy, weighted_score
                FROM wf_scores
                WHERE ticker = ?
                  AND strategy IN ({placeholders})
                  AND consistency_pct >= ?
                  AND avg_return_pct > 0 AND weighted_score > 0
                ORDER BY weighted_score DESC
            """, [ticker, *wf_candidates, min_consistency]).fetchall()
            conn.close()
            selected = [r[0] for r in rows]
        except Exception:
            selected = []

    if not selected and not counter_trend:
        selected = get_ticker_best_strategies(ticker, min_consistency)

    result = selected + [c for c in counter_trend if c not in selected]

    disabled = _get_disabled_strategies()
    result = [s for s in result if s not in disabled]

    # Daniel-Moskowitz panic gate + binary event-risk guard: no new
    # momentum-family entries. In macro panic, Panic Rebound is also
    # stripped — providing liquidity to single-stock crashes only pays
    # when the market itself is calm; Crash Recovery alone stays live.
    guard_on, _ = _event_guard_active()
    panic_on = _macro_panic_state()
    if panic_on or guard_on:
        result = [s for s in result if s not in _MOMENTUM_FAMILY]
    if panic_on:
        result = [s for s in result if s != 'Panic Rebound']

    return result


def _safe_regime(df: pd.DataFrame) -> str:
    try:
        from engine.regime_filter import detect_regime
        return detect_regime(df)
    except Exception:
        return 'UNKNOWN'


def run_agent_firm_gate(intersection_results, flow_confirmed, date_str, time_str):
    """Evaluate intersection_results through the agent firm gate.

    Candidates are taken from intersection_results (all strategy signals), not
    flow_confirmed. This lets the agent run in bear markets where the flow gate
    produces zero confirmed tickers.

    Returns updated flow_confirmed:
    - firm disabled → flow_confirmed unchanged
    - active + no signals → idle-log, flow_confirmed unchanged
    - shadow mode → flow_confirmed unchanged (agent evaluates, doesn't filter)
    - enforce mode → agent-approved tickers from intersection_results[:20]
    """
    try:
        from engine.agent_firm import config as _firm_cfg
        from engine.agent_firm import firm as _firm
        from engine.agent_firm.schemas import SignalCandidate as _SC

        if not _firm_cfg.is_active():
            return flow_confirmed

        if not intersection_results:
            print(f"[{time_str}] Agent firm: idle (no strategy signals generated)")
            return flow_confirmed

        _candidates = [
            _SC(
                ticker=r["ticker"],
                strategy=(r["strategies"][0] if r.get("strategies") else "multi"),
                score=float((r.get("flow") or {}).get("score") or 0),
                scan_time=f"{date_str} {time_str}",
                flow_verdict=(r.get("flow") or {}).get("verdict"),
                foreign_score=None,
                indicators={},
            )
            for r in intersection_results[:20]
        ]
        _decisions = _firm.evaluate_staged(_candidates)
        print(f"[{time_str}] Agent firm: {len(_decisions)} evaluated"
              f" ({sum(1 for d in _decisions if d.decision == 'approve')} approved"
              f", {sum(1 for d in _decisions if d.decision == 'veto')} vetoed)")

        # Build size-hint map and attach to every intersection result
        _size_map = {d.ticker: d.size_hint or 1.0
                     for d in _decisions if d.decision == "approve"}
        for r in intersection_results:
            r["agent_size_hint"] = _size_map.get(r["ticker"], 1.0)

        if _firm_cfg.get_enforce():
            return [r for r in intersection_results if r["ticker"] in _size_map]

        return flow_confirmed
    except Exception as _err:
        print(f"[{time_str}] Agent firm error (fail-open): {_err}")
        return flow_confirmed


def rank_bear_watchlist_and_notify(watchlist_tickers, date_str, time_str):
    """Rank active BEAR watchlist tickers via agent firm; send Telegram digest.

    Called after the bear watchlist scout so the agent can surface which
    oversold bear names have the strongest bull case when regime flips.
    Fail-silent: any error is logged and swallowed.
    """
    if not watchlist_tickers:
        return
    try:
        from engine.agent_firm import config as _firm_cfg
        from engine.agent_firm import firm as _firm
        from engine.agent_firm.schemas import SignalCandidate as _SC

        if not _firm_cfg.is_active():
            return

        # Skip tickers already approved today — avoids redundant LLM calls
        _conn = sqlite3.connect(DB_PATH)
        try:
            _already = {
                row[0] for row in _conn.execute(
                    "SELECT ticker FROM agent_decisions "
                    "WHERE strategy='watchlist' AND decision='approve' "
                    "AND date(scan_time)=?",
                    (date_str,),
                )
            }
        finally:
            _conn.close()

        _fresh = [t for t in list(watchlist_tickers)[:20] if t not in _already]
        if not _fresh:
            print(f"[{time_str}] Bear watchlist ranking: all tickers already approved today, skipping")
            return

        _candidates = [
            _SC(
                ticker=t,
                strategy="watchlist",
                score=0.0,
                scan_time=f"{date_str} {time_str}",
                flow_verdict=None,
                foreign_score=None,
                indicators={},
            )
            for t in _fresh
        ]
        _decisions = _firm.evaluate_staged(_candidates)
        _approved = [d for d in _decisions if d.decision == "approve"]
        if not _approved:
            return

        _approved.sort(key=lambda d: d.confidence or 0.0, reverse=True)

        msg = "🐻 <b>Bear Watchlist — Agent Ranking</b>\n\n"
        for i, d in enumerate(_approved, 1):
            conf_str = f"{d.confidence:.2f}" if d.confidence is not None else "N/A"
            rationale = d.rationale or "N/A"
            msg += f"{i}. {d.ticker} (conviction {conf_str}): {rationale}\n"

        send_telegram(msg)
        print(f"[{time_str}] Bear watchlist ranking sent: {[d.ticker for d in _approved]}")
    except Exception as _err:
        print(f"[{time_str}] Bear watchlist ranking error (fail-silent): {_err}")


def _ensure_scheduled_signals_table(conn):
    """Create scheduled_signals table with signal_direction column; migrate if needed."""
    conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, scan_time TEXT, ticker TEXT,
        strategies TEXT, flow_score INTEGER, flow_verdict TEXT,
        smart_money TEXT, signal_reasons TEXT, signal_direction TEXT DEFAULT 'BUY',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)").fetchall()}
    if 'signal_direction' not in existing_cols:
        conn.execute("ALTER TABLE scheduled_signals ADD COLUMN signal_direction TEXT DEFAULT 'BUY'")
    conn.commit()


def _save_signals_to_db(conn, signals, date_str, time_str):
    """Insert signals into scheduled_signals. Each signal dict must have signal_direction."""
    for r in signals:
        flow = r.get('flow') or {}
        score = r.get('flow_score') if r.get('flow_score') is not None else flow.get('score')
        verdict = r.get('flow_verdict') or flow.get('verdict', '')
        sm = r.get('smart_money') or flow.get('smart_money', '')
        direction = r.get('signal_direction', 'BUY')
        conn.execute(
            "INSERT INTO scheduled_signals "
            "(scan_time,ticker,strategies,flow_score,flow_verdict,smart_money,signal_reasons,signal_direction) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                f"{date_str} {time_str}",
                r['ticker'],
                ",".join(r['strategies']),
                score,
                verdict,
                sm,
                " | ".join(r['signal_reasons']),
                direction,
            ),
        )


def scan_distribution_signals(ohlcv_map, date_str, time_str):
    """Scan stockbit_flow DB for BEARISH tickers to generate SELL signals.

    Criteria (all must hold):
      - composite_score <= -3 (strong distribution)
      - verdict contains BEARISH
      - regime is BEAR or SIDEWAYS (never short BULL)
      - close[-1] < close[-5] (price declining, confirming distribution)
    """
    results = []
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """SELECT ticker, composite_score, smart_money
               FROM stockbit_flow
               WHERE trade_date = ?
                 AND composite_score <= -3
                 AND verdict LIKE '%BEARISH%'""",
            (date_str,),
        ).fetchall()
        conn.close()
    except Exception as _e:
        logging.warning(f"[scan_distribution] DB query error: {_e}")
        return []

    for ticker, score, smart_money in rows:
        df = ohlcv_map.get(ticker)
        if df is None or len(df) < 10:
            continue

        regime = _safe_regime(df)
        if regime == 'BULL':
            continue

        if float(df['close'].iloc[-1]) >= float(df['close'].iloc[-5]):
            continue

        results.append({
            'ticker': ticker,
            'strategies': ['distribution'],
            'signal_direction': 'SELL',
            'flow_score': score,
            'flow_verdict': 'BEARISH',
            'smart_money': smart_money or '',
            'signal_reasons': [
                f'BEARISH flow (score={score}), declining price, regime={regime}'
            ],
        })

    return results


def scheduled_multi_strategy_scan():
    """Multi-strategy signal scanner dengan flow filter."""
    from engine.strategies import check_current_entry_signal
    from engine.calendar_filter import is_blackout_day, is_trading_day
    from engine.sector_rotation import is_sector_tradeable, get_ticker_sector
    from flow_filter import get_flow_batch

    now = datetime.now(WIB)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    # Market-closed gate — skip entirely on weekends and IDX public holidays
    _open, _closed_reason = is_trading_day()
    if not _open:
        print(f"[{time_str}] Pasar tutup: {_closed_reason} — scan skipped.")
        return

    # Calendar blackout gate
    _blackout, _bl_reason = is_blackout_day()
    if _blackout:
        print(f"[{time_str}] BLACKOUT: {_bl_reason} — scan skipped.")
        send_telegram(f"⛔ <b>Multi-Scan Paused — Blackout</b>\n\n{_bl_reason}")
        return

    print(f"[{time_str}] Starting multi-strategy scan...")

    # ── Composite market risk score ───────────────────────────────────────────
    _market_risk = None
    try:
        from flow_filter import get_market_accdist_summary as _get_accdist_rs
        from engine.vpin import get_market_vpin_summary as _get_vpin_rs
        from engine.breadth import get_market_breadth as _get_breadth_rs
        from engine.technicals import detect_ihsg_technicals as _detect_tech_rs
        from engine.risk_score import compute_market_risk_score as _compute_risk
        _rs_conn = sqlite3.connect(DB_PATH)
        _rs_vpin = _get_vpin_rs(_rs_conn, date_str)
        _rs_accdist = _get_accdist_rs(date_str)
        _rs_breadth = _get_breadth_rs(_rs_conn, date_str)
        _rs_tech = _detect_tech_rs(_rs_conn, date_str)
        try:
            _fb = _rs_conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='BUY' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0] or 0
            _fs = _rs_conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='SELL' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0] or 0
            _rs_foreign = _fb - _fs
        except Exception:
            _rs_foreign = None
        _rs_conn.close()
        _market_risk = _compute_risk(_rs_vpin, _rs_accdist, _rs_breadth, _rs_tech, _rs_foreign)
        print(f"[{time_str}] Market risk score: {_market_risk['score']:.1f}/100 — {_market_risk['tier']}")
        # Route alert based on tier
        try:
            from engine.risk_alert import route_risk_alert as _route_alert
            _alert_conn = sqlite3.connect(DB_PATH)
            _route_alert(_alert_conn, _market_risk, date_str, time_str)
            _alert_conn.close()
        except Exception as _ra_err:
            logging.warning(f"[scan] risk alert routing error: {_ra_err}")
    except Exception as _rse:
        logging.warning(f"[scan] risk score error: {_rse}")

    # Market-wide sensors — log before scan so visible even on zero-signal days
    try:
        from flow_filter import get_market_accdist_summary as _get_accdist
        _accdist = _get_accdist(date_str)
        if _accdist['total'] > 0:
            print(f"[{time_str}] Market accdist: {_accdist['label']} "
                  f"(dist={_accdist['dist_pct']}% acc={_accdist['acc_pct']}% "
                  f"score={_accdist['avg_numeric_score']:+.3f})")
    except Exception as _ae:
        logging.warning(f"[scan] accdist summary error: {_ae}")

    try:
        from engine.technicals import detect_ihsg_technicals as _detect_tech
        _tech_conn = sqlite3.connect(DB_PATH)
        _tech = _detect_tech(_tech_conn, date_str)
        _tech_conn.close()
        if _tech['close'] is not None:
            flags = []
            if _tech['death_cross']:
                flags.append('DEATH_CROSS')
            if _tech['lower_high']:
                flags.append('LOWER_HIGH')
            if _tech['support_breaks']:
                flags.append(f"BROKE {','.join(_tech['support_breaks'])}")
            print(f"[{time_str}] IHSG technicals: {_tech['label']} "
                  f"({', '.join(flags) if flags else 'no flags'}) "
                  f"close={_tech['close']:,.0f} MA5={_tech['ma5']:,.0f} MA20={_tech.get('ma20', 0) or 0:,.0f}")
            if _tech['label'] in ('BEARISH_TREND', 'DOWNTREND') and _tech['death_cross']:
                send_telegram(
                    f"⚠️ <b>IHSG Technical Alert: {_tech['label']}</b>\n\n"
                    f"Close: {_tech['close']:,.0f}\n"
                    f"MA5: {_tech['ma5']:,.0f} | MA20: {_tech.get('ma20') or 0:,.0f}\n"
                    f"Death Cross: {'YES ❌' if _tech['death_cross'] else 'NO'}\n"
                    f"Lower High: {'YES ❌' if _tech['lower_high'] else 'NO'}\n"
                    + (f"Support Broken: {', '.join(_tech['support_breaks'])}\n" if _tech['support_breaks'] else "")
                )
    except Exception as _te:
        logging.warning(f"[scan] IHSG technicals error: {_te}")

    try:
        from engine.breadth import get_market_breadth as _get_breadth
        _breadth_conn = sqlite3.connect(DB_PATH)
        _breadth = _get_breadth(_breadth_conn, date_str)
        _breadth_conn.close()
        if _breadth['total'] > 0:
            print(f"[{time_str}] Market breadth: {_breadth['label']} "
                  f"(adv={_breadth['pct_advancing']}% dec={100-_breadth['pct_advancing']-(_breadth['unchanged']/_breadth['total']*100):.1f}% "
                  f"above_ma20={_breadth['pct_above_ma20']}%)")
    except Exception as _be:
        logging.warning(f"[scan] breadth summary error: {_be}")

    try:
        from engine.vpin import get_market_vpin_summary as _get_vpin
        _vpin_conn = sqlite3.connect(DB_PATH)
        _vpin_summary = _get_vpin(_vpin_conn, date_str)
        _vpin_conn.close()
        if _vpin_summary['tickers_with_vpin'] > 0:
            print(f"[{time_str}] Market VPIN: {_vpin_summary['label']} "
                  f"(avg={_vpin_summary['avg_vpin']:.4f} "
                  f">0.8={_vpin_summary['pct_above_08']}% "
                  f">0.95={_vpin_summary['pct_above_095']}%)")
            if _vpin_summary['label'] in ('CRITICAL', 'RED'):
                send_telegram(
                    f"🚨 <b>VPIN Alert: {_vpin_summary['label']}</b>\n\n"
                    f"avg VPIN = {_vpin_summary['avg_vpin']:.4f}\n"
                    f"Tickers >0.80: {_vpin_summary['pct_above_08']}% "
                    f"({_vpin_summary['count_above_08']})\n"
                    f"Tickers >0.95: {_vpin_summary['pct_above_095']}% "
                    f"({_vpin_summary['count_above_095']})\n\n"
                    f"<i>High VPIN = informed trading / toxicity spike.</i>"
                )
    except Exception as _ve:
        logging.warning(f"[scan] VPIN summary error: {_ve}")

    # Pre-compute sector scores once (1-hour TTL cache)
    _sector_scores = _get_sector_scores_cached()

    strategies = ["vol_weighted", "vwap_reversion"]
    flow_threshold = 2
    min_wf_consistency = 50.0

    # Get all tickers
    tickers = get_all_tickers()
    ohlcv_map = _load_ohlcv_bulk()

    # R16: flush indicator cache so each scan session recomputes from fresh data
    from engine.indicators import clear_indicator_cache as _clear_ic
    _cleared = _clear_ic()
    if _cleared:
        logging.debug(f"[scan] indicator cache cleared ({_cleared} stale entries)")

    # Phase 3: flush agent firm market context cache (open_trades/IHSG fetched once per scan)
    try:
        from engine.agent_firm.firm import reset_market_ctx as _reset_mctx
        _reset_mctx()
    except Exception:
        pass

    # Step 1: Adaptive strategy selection per ticker
    intersection_results = []

    for ticker in tickers:
        try:
            # Sector rotation filter — routed through _sector_verdict
            # to allow optional sectors.app overlay (env: SECTORS_APP_MODE)
            _sec_ok, _sec_reason = _sector_verdict(ticker, _sector_scores)
            if not _sec_ok:
                continue

            df = ohlcv_map.get(ticker)
            if df is None or len(df) < 20:
                continue

            # Get best strategies for this ticker — regime-aware selection
            best_strategies = adaptive_strategy_selector(ticker, df, min_wf_consistency)

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
                    'ticker':           ticker,
                    'strategies':       passing_strategies,
                    'has_signal':       True,
                    'signal_reasons':   combined_reasons,
                    'signal_details':   combined_details,
                    'sector':           get_ticker_sector(ticker),
                    'sector_weight':    _sec_entry["weight"] if _sec_entry else "NEUTRAL",
                    'sector_score':     _sec_entry["score"]  if _sec_entry else 0,
                    'adaptive_regime':  _safe_regime(df),
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
        _ensure_scheduled_signals_table(conn)
        for r in flow_confirmed:
            r.setdefault('signal_direction', 'BUY')
        _save_signals_to_db(conn, flow_confirmed, date_str, time_str)

        # ── SELL/BEARISH signal path ──────────────────────────────────────────
        sell_signals = scan_distribution_signals(ohlcv_map, date_str, time_str)
        if sell_signals:
            _save_signals_to_db(conn, sell_signals, date_str, time_str)
            print(f"[{time_str}] SELL signals (distribution): {len(sell_signals)} tickers")
        # ─────────────────────────────────────────────────────────────────────

        conn.commit()
        conn.close()
        print(f"[{time_str}] Saved {len(flow_confirmed)} BUY + {len(sell_signals)} SELL signals to DB")
    except Exception as e:
        print(f"[{time_str}] DB save error: {e}")

    # ── Bear dip-scout watchlist ──────────────────────────────────────────────
    # Scan the FULL universe (not just signal-producing tickers — bears don't
    # generate entry signals) for oversold BEAR names, and promote any
    # watchlisted name that has since turned BULL. Uses real OHLCV from
    # ohlcv_map so detect_regime's ADX is meaningful. Fail-open.
    try:
        import sqlite3 as _sql
        from engine.regime_filter import detect_regime as _detect_regime
        from engine.watchlist import (
            ensure_table as _wl_ensure,
            add_to_watchlist as _wl_add,
            promote_watchlist as _wl_promote,
            expire_stale as _wl_expire,
            priority_tickers as _wl_priority,
            passes_quality_gate as _wl_quality,
            compute_rsi as _compute_rsi,
            RSI_THRESHOLD as _RSI_THR,
        )

        _wl_conn = _sql.connect(DB_PATH)
        _wl_ensure(_wl_conn)

        # Expire stale active entries at the start of each scan (60d: median
        # BEAR->BULL recovery on IDX is ~59 cal days; 30d expired ~80% unpromoted)
        _expired = _wl_expire(_wl_conn, scan_date=date_str, max_calendar_days=60)
        if _expired:
            print(f"[{time_str}] Watchlist expired: {_expired}")

        _bear_added = []
        _bull_tickers = []
        for _tk, _df_wl in ohlcv_map.items():
            if _tk == "IHSG" or _df_wl is None or len(_df_wl) < 50:
                continue
            try:
                _regime_wl = _detect_regime(_df_wl)
                if _regime_wl == 'BEAR':
                    _rsi_wl = _compute_rsi(_df_wl['close'])
                    if _rsi_wl != _rsi_wl or _rsi_wl >= _RSI_THR:   # NaN or not oversold
                        continue
                    _q_ok, _q_wr, _q_ret = _wl_quality(_wl_conn, _tk)
                    if not _q_ok:
                        continue
                    _ma50 = _df_wl['close'].rolling(50).mean().iloc[-1]
                    _vs_ma = ((_df_wl['close'].iloc[-1] - _ma50) / _ma50 * 100
                              if _ma50 and _ma50 == _ma50 else None)
                    if _wl_add(_wl_conn, _tk, rsi=_rsi_wl, close_vs_ma50_pct=_vs_ma,
                               win_rate=_q_wr, best_return=_q_ret, scan_date=date_str):
                        _bear_added.append(_tk)
                elif _regime_wl == 'BULL':
                    _bull_tickers.append(_tk)
            except Exception:
                continue

        # Promote active watchlist entries that have since turned BULL
        _promoted = _wl_promote(_wl_conn, _bull_tickers, scan_date=date_str)

        # Give promoted names priority at the front of the entry candidate list
        _priority = set(_wl_priority(_wl_conn))
        if _priority:
            _pri_fc  = [r for r in flow_confirmed if r['ticker'] in _priority]
            _rest_fc = [r for r in flow_confirmed if r['ticker'] not in _priority]
            flow_confirmed = _pri_fc + _rest_fc

        if _bear_added:
            print(f"[{time_str}] Watchlist added (BEAR oversold): {_bear_added}")
        if _promoted:
            print(f"[{time_str}] Watchlist promoted (→BULL): {_promoted}")

        _wl_conn.close()

        # Rank active watchlist via agent firm and send Telegram digest
        rank_bear_watchlist_and_notify(list(_priority), date_str, time_str)
    except Exception as _wl_err:
        print(f"[{time_str}] Bear watchlist error (fail-open): {_wl_err}")
    # ── End bear watchlist ────────────────────────────────────────────────────

    # ── Agent Firm evaluation ─────────────────────────────────────────────────
    flow_confirmed = run_agent_firm_gate(
        intersection_results, flow_confirmed, date_str, time_str
    )
    # ── End agent firm ────────────────────────────────────────────────────────

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

                # Check trend filter — counter-trend strategies (Crash
                # Recovery, Panic Rebound) buy INTO downtrends by design.
                _is_counter_trend = any(s in _COUNTER_TREND_BOOK for s in r['strategies'])
                if not _is_counter_trend:
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

                # Open paper trade — apply agent size hint if present,
                # halved during the event-risk guard window.
                _size_mult = r.get("agent_size_hint", 1.0)
                _eg_on, _eg_mult = _event_guard_active()
                if _eg_on:
                    _size_mult *= _eg_mult
                # Record the strategy whose signal triggered this trade —
                # accurate per-strategy P&L attribution depends on it.
                _ot_kwargs = {'strategy': first_strategy}
                if _is_counter_trend:
                    # Use the strategy's own levels: SL = signal/resume low,
                    # TP = retracement target. Generic ATR levels misprice
                    # counter-trend setups (ATR is inflated by the crash bars).
                    _d = signal_details.get(first_strategy, {})
                    if _d.get('sl'):
                        _ot_kwargs['sl_price'] = float(_d['sl'])
                    if _d.get('tp'):
                        _ot_kwargs['tp_price'] = float(_d['tp'])
                    _ot_kwargs['min_rr'] = 1.2
                trade_result = open_trade(ticker, float(entry_price), notify=False,
                                          lots_multiplier=_size_mult, **_ot_kwargs)

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
        print(f"[{time_str}] No flow-confirmed signals (strategy pass: {len(intersection_results)}). Sending heartbeat.")
        send_telegram(
            f"📡 <b>Scan @ {time_str}</b> — tidak ada sinyal\n\n"
            f"🔍 Scanned: {len(tickers)} tickers\n"
            f"📊 Lolos strategi: {len(intersection_results)}\n"
            f"❌ Lolos flow (≥+2): 0\n\n"
            f"<i>Market sedang BEAR, scanner tetap jalan.</i>"
        )
    print(f"[{time_str}] Multi-strategy scan complete.\n")
