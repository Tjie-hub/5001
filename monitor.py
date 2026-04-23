"""
monitor.py — Intraday open trade monitor.
Checks all open paper trades every 30 min during market hours.
Sends Telegram alerts on: flow reversal, VPIN spike, momentum reversal,
near-SL/TP approach, regime change.
"""
import logging
import os
from datetime import date as dt_date

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10
        )
    except Exception as e:
        logger.error(f"[monitor] Telegram error: {e}")


def _fetch_recent_closes(ticker: str, n: int = 5) -> list:
    """Fetch last N daily closes from walkforward DB."""
    import sqlite3
    import os
    db_path = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            'SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT ?', (ticker, n)
        ).fetchall()
        conn.close()
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []


def _fetch_atr(ticker: str, periods: int = 14) -> float:
    """Compute ATR from recent OHLCV."""
    import sqlite3, os
    db_path = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
    try:
        import pandas as pd
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            'SELECT high, low, close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT ?',
            conn, params=(ticker, periods + 5)
        )
        conn.close()
        if len(df) < periods:
            return None
        df = df.iloc[::-1].reset_index(drop=True)
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low'] - df['close'].shift()).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(periods).mean().iloc[-1])
    except Exception:
        return None


def _detect_momentum_reversal(closes: list, entry_price: float) -> bool:
    """2 consecutive bearish bars after entry price."""
    if len(closes) < 3:
        return False
    above_entry = [c > entry_price for c in closes]
    if not any(above_entry):
        return False
    bearish_streak = closes[-1] < closes[-2] < closes[-3]
    return bearish_streak


def _get_flow_score(ticker: str) -> dict:
    """Fetch today's cached flow score from DB."""
    import sqlite3, os
    db_path = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        today = dt_date.today().isoformat()
        row = conn.execute(
            'SELECT * FROM stockbit_flow WHERE ticker=? AND date=?', (ticker, today)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def _get_vpin(ticker: str) -> dict:
    """Fetch today's VPIN from daily_screen."""
    import sqlite3, os
    db_path = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        today = dt_date.today().isoformat()
        row = conn.execute(
            'SELECT vpin, vpin_label FROM daily_screen WHERE ticker=? AND date=?', (ticker, today)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def _get_current_price(ticker: str) -> float:
    """Get latest close from OHLCV."""
    closes = _fetch_recent_closes(ticker, 1)
    return closes[0] if closes else None


def _check_trade(trade: dict) -> list:
    """
    Analyse one open trade. Returns list of alert dicts if warnings found.
    Each alert: {ticker, trade_id, alert_type, severity, message}
    """
    ticker      = trade['ticker']
    entry_price = float(trade['entry_price'])
    tp_price    = float(trade['tp_price'])
    sl_price    = float(trade['sl_price'])
    trade_id    = trade['id']

    alerts = []
    current = _get_current_price(ticker)
    if not current:
        return alerts

    pnl_pct = (current - entry_price) / entry_price * 100

    # 1. Near SL (within 0.5% of SL level)
    if current <= sl_price * 1.005:
        alerts.append({
            'ticker': ticker, 'trade_id': trade_id,
            'alert_type': 'NEAR_SL', 'severity': 'HIGH',
            'message': (
                f"⛔ <b>APPROACHING SL</b> — {ticker}\n"
                f"Current: {current:,.0f}  SL: {sl_price:,.0f} ({pnl_pct:+.1f}%)\n"
                f"TP: {tp_price:,.0f}  Entry: {entry_price:,.0f}\n"
                f"<i>Consider cutting loss</i>"
            )
        })

    # 2. Near TP (within 0.5% of TP level)
    if current >= tp_price * 0.995:
        alerts.append({
            'ticker': ticker, 'trade_id': trade_id,
            'alert_type': 'NEAR_TP', 'severity': 'LOW',
            'message': (
                f"✅ <b>APPROACHING TP</b> — {ticker}\n"
                f"Current: {current:,.0f}  TP: {tp_price:,.0f} ({pnl_pct:+.1f}%)\n"
                f"<i>Consider booking profit or trailing SL</i>"
            )
        })

    # 3. Momentum reversal (2 consecutive down bars after entry)
    closes = _fetch_recent_closes(ticker, 5)
    if _detect_momentum_reversal(closes, entry_price):
        alerts.append({
            'ticker': ticker, 'trade_id': trade_id,
            'alert_type': 'MOMENTUM_REVERSAL', 'severity': 'MEDIUM',
            'message': (
                f"⚠️ <b>MOMENTUM FADING</b> — {ticker}\n"
                f"2 consecutive bearish bars after entry\n"
                f"Current: {current:,.0f}  Entry: {entry_price:,.0f} ({pnl_pct:+.1f}%)\n"
                f"<i>Monitor closely — momentum weakening</i>"
            )
        })

    # 4. Flow reversal
    flow = _get_flow_score(ticker)
    if flow:
        flow_verdict = flow.get('verdict', '')
        flow_score   = flow.get('score', 0)
        if flow_verdict in ('BEARISH', 'STRONG_SELL') or (isinstance(flow_score, (int, float)) and flow_score <= -2):
            alerts.append({
                'ticker': ticker, 'trade_id': trade_id,
                'alert_type': 'FLOW_REVERSAL', 'severity': 'HIGH',
                'message': (
                    f"🔴 <b>FLOW REVERSAL</b> — {ticker}\n"
                    f"Entry: {entry_price:,.0f}  Current: {current:,.0f} ({pnl_pct:+.1f}%)\n"
                    f"Flow: {flow_verdict} (score: {flow_score})\n"
                    f"TP: {tp_price:,.0f}  SL: {sl_price:,.0f}\n"
                    f"<i>Smart money turning bearish — consider exit</i>"
                )
            })

    # 5. VPIN spike
    vpin = _get_vpin(ticker)
    if vpin:
        vpin_label = vpin.get('vpin_label', '')
        vpin_score = vpin.get('vpin', 0) or 0
        if vpin_label in ('HIGH', 'TOXIC'):
            alerts.append({
                'ticker': ticker, 'trade_id': trade_id,
                'alert_type': 'VPIN_SPIKE', 'severity': 'HIGH',
                'message': (
                    f"🚨 <b>VPIN SPIKE — INFORMED SELLING</b> — {ticker}\n"
                    f"VPIN: {vpin_score:.3f} ({vpin_label})\n"
                    f"Current: {current:,.0f}  Entry: {entry_price:,.0f} ({pnl_pct:+.1f}%)\n"
                    f"<i>Elevated informed trading detected — high exit risk</i>"
                )
            })

    return alerts


def _evaluate_swing_trend(trade: dict) -> dict:
    """
    Evaluate R1–R7 reverse-trend triggers for an open Swing Trend paper trade.
    Returns {'action': 'CLOSE'|'TRAIL'|'OK', 'reason': <rule>, 'message': <telegram>,
             'new_sl': <float|None>}.
    """
    import sqlite3, os, pandas as pd
    from engine.regime_filter import calc_adx, calc_ma_slope
    from engine.swing_screener import find_swing_points
    from engine.strategies import calc_atr

    ticker      = trade['ticker']
    entry_price = float(trade['entry_price'])
    sl_price    = float(trade['sl_price'])
    adx_peak    = float(trade.get('adx_peak') or 0.0)
    highest     = float(trade.get('highest_seen') or entry_price)

    db_path = os.getenv('DB_PATH', '/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db')
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            'SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? ORDER BY date ASC',
            conn, params=(ticker,)
        )
        conn.close()
    except Exception as e:
        return {'action': 'OK', 'reason': None, 'message': f'data_error: {e}', 'new_sl': None}

    if len(df) < 55:
        return {'action': 'OK', 'reason': None, 'message': 'insufficient_history', 'new_sl': None}

    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)

    cur   = float(df['close'].iloc[-1])
    low   = float(df['low'].iloc[-1])
    ma20_s = df['close'].rolling(20).mean()
    slope  = calc_ma_slope(df, 20, 5)
    adx    = calc_adx(df, 14)
    avg_v  = df['volume'].rolling(20).mean()
    vr     = df['volume'] / avg_v

    ma20_now = float(ma20_s.iloc[-1]) if not pd.isna(ma20_s.iloc[-1]) else None
    slope_now = float(slope.iloc[-1]) if not pd.isna(slope.iloc[-1]) else None
    adx_now = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None

    # Update trailing state
    new_highest = max(highest, float(df['high'].iloc[-1]))
    new_adx_peak = max(adx_peak, adx_now) if adx_now is not None else adx_peak

    # Trailed SL logic: raise to latest higher-low pivot; BE lock after +10%
    _, lows_idx = find_swing_points(df, n=2)
    new_sl = sl_price
    if lows_idx:
        candidate = float(df['low'].iloc[lows_idx[-1]])
        if candidate > new_sl and candidate < cur:
            new_sl = candidate
    if new_highest >= entry_price * 1.10 and new_sl < entry_price:
        new_sl = entry_price

    # R7: trailed SL hit
    if low <= new_sl:
        return {
            'action': 'CLOSE',
            'reason': 'R7_TRAIL_SL',
            'new_sl': new_sl,
            'message': (
                f"⛔ <b>R7 TRAIL-SL HIT</b> — {ticker}\n"
                f"Low {low:,.0f} ≤ SL {new_sl:,.0f}  Entry {entry_price:,.0f}\n"
                f"<i>Auto-close triggered</i>"
            ),
            'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
        }

    # R1: close<MA20 AND slope<0
    if ma20_now and slope_now is not None and cur < ma20_now and slope_now < 0:
        return {
            'action': 'CLOSE', 'reason': 'R1_MA_BREAK', 'new_sl': new_sl,
            'message': (
                f"🔴 <b>R1 MA-BREAK</b> — {ticker}\n"
                f"Close {cur:,.0f} < MA20 {ma20_now:,.0f}; slope {slope_now:+.2f}%\n"
                f"<i>Trend broken — auto-close</i>"
            ),
            'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
        }

    # R2: close < most-recent swing-low pivot
    if lows_idx:
        recent_low = float(df['low'].iloc[lows_idx[-1]])
        if cur < recent_low:
            return {
                'action': 'CLOSE', 'reason': 'R2_LOWER_LOW', 'new_sl': new_sl,
                'message': (
                    f"🔴 <b>R2 LOWER-LOW</b> — {ticker}\n"
                    f"Close {cur:,.0f} < prev swing-low {recent_low:,.0f}\n"
                    f"<i>Structural break — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # R3: ADX peak >25, now <20
    if new_adx_peak > 25 and adx_now is not None and adx_now < 20:
        return {
            'action': 'CLOSE', 'reason': 'R3_ADX_FADE', 'new_sl': new_sl,
            'message': (
                f"⚠️ <b>R3 ADX-FADE</b> — {ticker}\n"
                f"ADX {adx_now:.1f} (peak {new_adx_peak:.1f}) — momentum gone\n"
                f"<i>Trend strength collapsed — auto-close</i>"
            ),
            'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
        }

    # R4: 3 consecutive lower closes on vr>=1.3
    if len(df) >= 4:
        c = df['close'].values
        vr_i = vr.iloc[-1]
        three_down = c[-1] < c[-2] < c[-3] < c[-4]
        if three_down and not pd.isna(vr_i) and vr_i >= 1.3:
            return {
                'action': 'CLOSE', 'reason': 'R4_DISTRIBUTION', 'new_sl': new_sl,
                'message': (
                    f"⚠️ <b>R4 DISTRIBUTION</b> — {ticker}\n"
                    f"3 lower closes, VR {vr_i:.1f}×\n"
                    f"<i>Distribution detected — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # R5: flow bearish 2d
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            'SELECT composite_score FROM stockbit_flow WHERE ticker=? ORDER BY trade_date DESC LIMIT 2',
            (ticker,)
        ).fetchall()
        conn.close()
        if len(rows) == 2 and all((r[0] is not None) and float(r[0]) <= -2 for r in rows):
            return {
                'action': 'CLOSE', 'reason': 'R5_FLOW_FLIP', 'new_sl': new_sl,
                'message': (
                    f"🔴 <b>R5 FLOW-FLIP</b> — {ticker}\n"
                    f"Flow composite ≤ −2 two days running\n"
                    f"<i>Smart money exiting — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }
    except Exception:
        pass

    # R6: bearish engulfing on vr>1.8
    if len(df) >= 2:
        prev = df.iloc[-2]
        cur_bar = df.iloc[-1]
        prev_bull = prev['close'] > prev['open']
        cur_bear  = cur_bar['close'] < cur_bar['open']
        engulf = cur_bar['open'] >= prev['close'] and cur_bar['close'] <= prev['open']
        vr_i = vr.iloc[-1]
        if prev_bull and cur_bear and engulf and not pd.isna(vr_i) and vr_i > 1.8:
            return {
                'action': 'CLOSE', 'reason': 'R6_BEAR_ENGULF', 'new_sl': new_sl,
                'message': (
                    f"🔴 <b>R6 BEARISH ENGULFING</b> — {ticker}\n"
                    f"High-volume engulf (VR {vr_i:.1f}×)\n"
                    f"<i>Sharp reversal — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # No exit — just persist trail updates
    return {
        'action': 'TRAIL' if new_sl > sl_price or new_highest > highest else 'OK',
        'reason': None,
        'new_sl': new_sl,
        'new_highest': new_highest,
        'new_adx_peak': new_adx_peak,
        'message': None,
    }


def check_all_open_trades():
    """Main entry: check all open paper trades, send Telegram on any alert.
    For Swing Trend trades, also auto-close on R1–R7 triggers."""
    from paper_trade import get_open_trades, close_trade, get_db
    from screener.db import log_trade_alert

    open_trades = get_open_trades()
    if not open_trades:
        logger.info("[monitor] No open trades to monitor.")
        return

    logger.info(f"[monitor] Checking {len(open_trades)} open trade(s)...")
    total_alerts = 0

    for trade in open_trades:
        strategy = (trade.get('strategy') or '').strip().lower()

        if strategy == 'swing trend':
            result = _evaluate_swing_trend(trade)
            # Persist trailing state even when not closing
            if result.get('new_sl') or result.get('new_highest') or result.get('new_adx_peak'):
                try:
                    conn = get_db()
                    conn.execute(
                        "UPDATE paper_trades SET sl_price=?, highest_seen=?, adx_peak=? WHERE id=?",
                        (result.get('new_sl') or trade['sl_price'],
                         result.get('new_highest') or trade.get('highest_seen'),
                         result.get('new_adx_peak') or trade.get('adx_peak'),
                         trade['id'])
                    )
                    conn.commit(); conn.close()
                except Exception as e:
                    logger.error(f"[monitor] trail update failed: {e}")

            if result['action'] == 'CLOSE':
                cur = _get_current_price(trade['ticker']) or float(trade['entry_price'])
                try:
                    close_trade(int(trade['id']), float(cur), result['reason'], notify=False)
                    logger.info(f"[monitor] Auto-closed {trade['ticker']} ({result['reason']})")
                except Exception as e:
                    logger.error(f"[monitor] close_trade failed: {e}")
                if result.get('message'):
                    send_telegram(result['message'])
                    try:
                        log_trade_alert(trade['ticker'], trade['id'], result['reason'], result['message'])
                    except Exception:
                        pass
                    total_alerts += 1
            continue

        # Non-swing: existing alert flow (no auto-close)
        alerts = _check_trade(trade)
        for alert in alerts:
            logger.info(f"[monitor] Alert {alert['alert_type']} for {alert['ticker']}")
            try:
                log_trade_alert(
                    alert['ticker'], alert['trade_id'],
                    alert['alert_type'], alert['message']
                )
            except Exception:
                pass
            send_telegram(alert['message'])
            total_alerts += 1

    logger.info(f"[monitor] Done. {total_alerts} alert(s) sent.")
    return total_alerts
