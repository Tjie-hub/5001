"""
monitor.py — Intraday open trade monitor.
Checks all open paper trades every 30 min during market hours.
Sends Telegram alerts on: flow reversal, VPIN spike, momentum reversal,
near-SL/TP approach, regime change.
"""
import logging
import sqlite3
from data.db import connect as db_connect
from datetime import date as dt_date

from config import DB_PATH
from engine.freshness import is_fresh

logger = logging.getLogger(__name__)

from utils.telegram import send_telegram


def _agent_confirms_exit(trade: dict, result: dict) -> bool:
    """Ask agent firm whether to confirm a probabilistic exit (R3_ADX_FADE / R4_DISTRIBUTION).

    Returns True  → proceed with close (agent approved or firm disabled/error).
    Returns False → hold (agent explicitly vetoed).
    Fail-open: any exception returns True so the close proceeds.
    """
    try:
        from engine.agent_firm import config as _cfg
        from engine.agent_firm import firm as _firm
        from engine.agent_firm.schemas import SignalCandidate as _SC

        if not _cfg.is_active():
            return True

        _candidate = _SC(
            ticker=trade["ticker"],
            strategy=trade.get("strategy") or "swing trend",
            score=0.0,
            scan_time=result.get("reason", "exit_review"),
            flow_verdict=None,
            foreign_score=None,
            indicators={},
        )
        _decisions = _firm.evaluate([_candidate])
        if not _decisions:
            return True
        return _decisions[0].decision != "veto"
    except Exception:
        return True  # fail-open: close proceeds


def _fetch_recent_closes(ticker: str, n: int = 5) -> list:
    """Fetch last N daily closes from walkforward DB."""
    try:
        conn = db_connect(DB_PATH)
        rows = conn.execute(
            'SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT ?', (ticker, n)
        ).fetchall()
        conn.close()
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []


def _fetch_atr(ticker: str, periods: int = 14) -> float:
    """Compute ATR from recent OHLCV."""
    try:
        import pandas as pd
        conn = db_connect(DB_PATH)
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
    try:
        conn = db_connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        today = dt_date.today().isoformat()
        # Column is trade_date; the old 'date=?' predicate raised
        # OperationalError, silently killing this alert since inception (H-1).
        row = conn.execute(
            'SELECT * FROM stockbit_flow WHERE ticker=? AND trade_date=?', (ticker, today)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def _get_vpin(ticker: str) -> dict:
    """Fetch today's VPIN from daily_screen."""
    try:
        conn = db_connect(DB_PATH)
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


def _latest_bar(ticker: str):
    """(date, open, high, low, close) of the most recent OHLCV bar, or None."""
    try:
        conn = db_connect(DB_PATH)
        row = conn.execute(
            'SELECT date, open, high, low, close FROM ohlcv '
            'WHERE ticker=? ORDER BY date DESC LIMIT 1', (ticker,)).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def _bars_held(ticker: str, entry_date) -> int:
    """Completed OHLCV bars strictly after entry_date — the kernel's hold_days
    unit is BARS (backtest parity), not calendar days."""
    try:
        conn = db_connect(DB_PATH)
        n = conn.execute('SELECT COUNT(*) FROM ohlcv WHERE ticker=? AND date>?',
                         (ticker, str(entry_date)[:10])).fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def _sma(ticker: str, period: int):
    try:
        conn = db_connect(DB_PATH)
        row = conn.execute(
            'SELECT AVG(close), COUNT(*) FROM (SELECT close FROM ohlcv '
            'WHERE ticker=? ORDER BY date DESC LIMIT ?)', (ticker, period)).fetchone()
        conn.close()
        if row and row[1] == period:
            return float(row[0])
        return None
    except Exception:
        return None


# R8 dead-capital cap: applied only to fixed-target policies without their own
# hold_days. Trailing policies (TFB) self-terminate via the trail/MA-break.
TIME_STOP_DEFAULT_BARS = 14


def _check_trade(trade: dict) -> dict:
    """
    Analyse one open trade via the strategy's OWN exit policy (shared kernel,
    plan 1B / audit C-3). Returns dict with keys:
      - should_close: bool
      - exit_reason / exit_price: kernel decision when should_close
      - alerts: list of alert dicts if warnings found
      - trail_update: dict {new_sl, new_highest} if trailing state changed, else None
      Each alert: {ticker, trade_id, alert_type, severity, message}
    """
    ticker      = trade['ticker']
    entry_price = float(trade['entry_price'])
    tp_price    = float(trade['tp_price']) if trade.get('tp_price') else None
    sl_price    = float(trade.get('sl_price') or 0)
    trade_id    = trade['id']

    alerts = []
    from dataclasses import replace as _dc_replace
    from engine.exits import PositionView, Bar, evaluate_exit, get_policy

    policy = get_policy(trade.get('strategy') or '')

    bar_row = _latest_bar(ticker)
    if bar_row is None:
        return {'should_close': False, 'alerts': alerts, 'trail_update': None,
                'exit_reason': None, 'exit_price': None}
    # H-3 minimal freshness guard (P0.E2.S1.T2): don't re-evaluate SL/TP off a
    # stale last bar (feed gap, suspension, token death) — skip this cycle
    # instead. Full Certifier-based freshness flag is Phase 1 scope.
    if not is_fresh(bar_row[0]):
        return {'should_close': False, 'alerts': alerts, 'trail_update': None,
                'exit_reason': None, 'exit_price': None, 'stale': True}
    bar = Bar(date=str(bar_row[0]), open=float(bar_row[1]), high=float(bar_row[2]),
              low=float(bar_row[3]), close=float(bar_row[4]))
    current = bar.close

    atr14 = float(trade.get('atr14') or 0) or _fetch_atr(ticker) or 0.0
    highest = float(trade.get('highest_seen') or entry_price)
    bars_held = _bars_held(ticker, trade.get('entry_date'))

    # Default time cap only for fixed-target policies without their own.
    eff_policy = policy
    if policy.hold_days is None and not (policy.trail_enable or policy.trail_atr_mult):
        eff_policy = _dc_replace(policy, hold_days=TIME_STOP_DEFAULT_BARS)

    view = PositionView(
        policy=eff_policy, direction='LONG', entry=entry_price,
        atr=atr14 if atr14 > 0 else max(entry_price * 0.015, 1.0),
        highest_seen=highest, lowest_seen=entry_price, hold_days=bars_held,
        sl_price=(sl_price if sl_price > 0 else None),
        tp_price=(tp_price if tp_price and tp_price > 0 else None),
    )
    decision = evaluate_exit(view, bar)

    exit_reason = exit_price = None
    if decision is not None:
        exit_reason, exit_price = decision.reason, float(decision.fill_price)
    elif eff_policy.ma_break_period:
        ma = _sma(ticker, eff_policy.ma_break_period)
        if ma is not None and bar.close < ma:
            exit_reason, exit_price = 'MA_BREAK', bar.close

    # Persist trail progress for trailing policies (display + next-run anchor).
    trail_update = None
    new_highest = max(highest, bar.high)
    if (eff_policy.trail_enable or eff_policy.trail_atr_mult) and atr14 > 0:
        lv = eff_policy.initial_levels('LONG', entry_price, atr14)
        if lv.trailing:
            cur_stop = round(highest - lv.trail_mult * atr14)
            if cur_stop > sl_price or new_highest > highest:
                trail_update = {'new_sl': max(cur_stop, int(sl_price)),
                                'new_highest': new_highest}
                sl_price = max(cur_stop, sl_price)
    elif new_highest > highest:
        trail_update = {'new_sl': sl_price, 'new_highest': new_highest}

    pnl_pct = (current - entry_price) / entry_price * 100

    if exit_reason:
        _emoji = {'TP': '✅', 'TRAIL': '📉', 'SL': '🚨',
                  'TIME': '⏱', 'MA_BREAK': '🔻'}.get(exit_reason, '🔔')
        return {
            'should_close': True,
            'exit_reason': exit_reason,
            'exit_price': exit_price,
            'trail_update': trail_update,
            'alerts': [{
                'ticker': ticker, 'trade_id': trade_id,
                'alert_type': exit_reason,
                'severity': 'CRITICAL' if exit_reason in ('SL', 'TRAIL') else 'INFO',
                'message': (
                    f"{_emoji} <b>{exit_reason} — AUTO-CLOSED</b> — {ticker}\n"
                    f"Fill: {exit_price:,.0f}  Entry: {entry_price:,.0f}\n"
                    f"Policy: {trade.get('strategy')}  Held: {bars_held} bars\n"
                    f"P&L: {pnl_pct:+.2f}%"
                )
            }]
        }

    # 1. Near SL (within 0.5% of SL level) — skipped for no_sl policies
    if not eff_policy.no_sl and sl_price > 0 and current <= sl_price * 1.005:
        alerts.append({
            'ticker': ticker, 'trade_id': trade_id,
            'alert_type': 'NEAR_SL', 'severity': 'HIGH',
            'message': (
                f"⛔ <b>APPROACHING SL</b> — {ticker}\n"
                f"Current: {current:,.0f}  SL: {sl_price:,.0f} ({pnl_pct:+.1f}%)\n"
                f"TP: {'{:,.0f}'.format(tp_price) if tp_price else 'trail'}  Entry: {entry_price:,.0f}\n"
                f"<i>Consider cutting loss</i>"
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
                    f"TP: {'{:,.0f}'.format(tp_price) if tp_price else 'trail'}  SL: {sl_price:,.0f}\n"
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

    return {'should_close': False, 'alerts': alerts, 'trail_update': trail_update,
            'exit_reason': None, 'exit_price': None}


def _evaluate_swing_trend(trade: dict) -> dict:
    """
    Evaluate R1–R7 reverse-trend triggers for an open Swing Trend paper trade.
    Returns {'action': 'CLOSE'|'TRAIL'|'OK', 'reason': <rule>, 'message': <telegram>,
             'new_sl': <float|None>}.
    """
    import pandas as pd
    from engine.regime_filter import calc_adx, calc_ma_slope
    from engine.swing_screener import find_swing_points
    from engine.indicators import calc_atr

    ticker      = trade['ticker']
    entry_price = float(trade['entry_price'])
    sl_price    = float(trade['sl_price'])
    adx_peak    = float(trade.get('adx_peak') or 0.0)
    highest     = float(trade.get('highest_seen') or entry_price)

    try:
        conn = db_connect(DB_PATH)
        df = pd.read_sql(
            'SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? ORDER BY date ASC',
            conn, params=(ticker,)
        )
        conn.close()
    except Exception as e:
        return {'action': 'OK', 'reason': None, 'message': f'data_error: {e}', 'new_sl': None}

    if len(df) < 55:
        return {'action': 'OK', 'reason': None, 'message': 'insufficient_history', 'new_sl': None}

    # H-3 minimal freshness guard (P0.E2.S1.T2) — see _check_trade
    if not is_fresh(df['date'].iloc[-1]):
        return {'action': 'OK', 'reason': None, 'message': 'stale_bar', 'new_sl': None, 'stale': True}

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

    # Trailed SL logic: raise to latest higher-low pivot (only after 1 ATR)
    _, lows_idx = find_swing_points(df, n=2)
    new_sl = sl_price
    if lows_idx:
        candidate = float(df['low'].iloc[lows_idx[-1]])
        atr_ok = (new_highest - entry_price) > (calc_atr(df, 14).iloc[-1] if len(df) >= 14 else 0)
        if candidate > new_sl and candidate < cur and atr_ok:
            new_sl = candidate
    # BE lock after +8%
    if new_highest >= entry_price * 1.08 and new_sl < entry_price:
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

    # R1: close<MA20, slope neg 2 days, volume confirmation
    if ma20_now and slope_now is not None:
        slope_prev = float(slope.iloc[-2]) if len(slope) >= 2 and not pd.isna(slope.iloc[-2]) else 0
        slope_neg_2d = slope_now < 0 and slope_prev < 0
        vr_i = vr.iloc[-1] if not pd.isna(vr.iloc[-1]) else 0
        if cur < ma20_now and slope_neg_2d and vr_i >= 1.3:
            return {
                'action': 'CLOSE', 'reason': 'R1_MA_BREAK', 'new_sl': new_sl,
                'message': (
                    f"🔴 <b>R1 MA-BREAK</b> — {ticker}\n"
                    f"Close {cur:,.0f} < MA20 {ma20_now:,.0f}; slope 2d neg, VR {vr_i:.1f}x\n"
                    f"<i>Trend broken — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # R3: ADX collapse (percentage drop from peak)
    if new_adx_peak > 25 and adx_now is not None:
        adx_drop_pct = (new_adx_peak - adx_now) / new_adx_peak
        if adx_drop_pct > 0.20:
            return {
                'action': 'CLOSE', 'reason': 'R3_ADX_FADE', 'new_sl': new_sl,
                'message': (
                    f"⚠️ <b>R3 ADX-FADE</b> — {ticker}\n"
                    f"ADX {adx_now:.1f} (peak {new_adx_peak:.1f}, drop {adx_drop_pct:.0%})\n"
                    f"<i>Momentum collapsed — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # R4: 3-of-4 lower closes on vr>=1.8
    if len(df) >= 5:
        c = df['close'].values
        vr_i = vr.iloc[-1] if not pd.isna(vr.iloc[-1]) else 0
        three_of_four = sum([c[-1] < c[-2], c[-2] < c[-3], c[-3] < c[-4], c[-4] < c[-5]]) >= 3
        if three_of_four and vr_i >= 1.8:
            return {
                'action': 'CLOSE', 'reason': 'R4_DISTRIBUTION', 'new_sl': new_sl,
                'message': (
                    f"⚠️ <b>R4 DISTRIBUTION</b> — {ticker}\n"
                    f"3/4 lower closes, VR {vr_i:.1f}x\n"
                    f"<i>Distribution detected — auto-close</i>"
                ),
                'new_highest': new_highest, 'new_adx_peak': new_adx_peak,
            }

    # R5: flow bearish 2d
    try:
        conn = db_connect(DB_PATH)
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
    stale_skipped = 0

    for trade in open_trades:
        strategy = (trade.get('strategy') or '').strip().lower()

        if strategy == 'swing trend':
            result = _evaluate_swing_trend(trade)
            if result.get('stale'):
                stale_skipped += 1
                continue
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

            # Agent exit review: probabilistic closes give agent a veto
            if (result['action'] == 'CLOSE'
                    and result.get('reason') in ('R3_ADX_FADE', 'R4_DISTRIBUTION')
                    and not _agent_confirms_exit(trade, result)):
                logger.info(
                    f"[monitor] Agent overrode {result['reason']} exit for "
                    f"{trade['ticker']} — holding position"
                )
                result = {**result, 'action': 'HOLD'}

            if result['action'] == 'CLOSE':
                cur = _get_current_price(trade['ticker']) or float(trade.get('sl_price') or trade['entry_price'])
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

        # Non-swing: check for stop loss / TP, alerts, and trailing stop
        result = _check_trade(trade)
        if result.get('stale'):
            stale_skipped += 1
            continue

        # Persist trailing stop update if SL or highest_seen changed
        if result.get('trail_update'):
            tu = result['trail_update']
            try:
                conn = get_db()
                conn.execute(
                    "UPDATE paper_trades SET sl_price=?, highest_seen=? WHERE id=?",
                    (tu['new_sl'], tu['new_highest'], trade['id'])
                )
                conn.commit(); conn.close()
            except Exception as e:
                logger.error(f"[monitor] trail update failed: {e}")

        # Auto-close at the kernel's decision: reason and gap-aware fill come
        # straight from evaluate_exit (plan 1B — unified taxonomy, item 1.9).
        if result['should_close']:
            _reason = result.get('exit_reason') or 'STOPPED_OUT'
            cur = (result.get('exit_price')
                   or _get_current_price(trade['ticker'])
                   or float(trade.get('sl_price') or trade['entry_price']))
            try:
                close_trade(int(trade['id']), float(cur), _reason, notify=False)
                logger.info(f"[monitor] Auto-closed {trade['ticker']} ({_reason})")
            except Exception as e:
                logger.error(f"[monitor] close_trade failed: {e}")

        # Process all alerts (including stop loss alert)
        for alert in result['alerts']:
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

    if stale_skipped:
        logger.warning(f"[monitor] {stale_skipped}/{len(open_trades)} open trade(s) skipped this cycle (stale last bar)")
    logger.info(f"[monitor] Done. {total_alerts} alert(s) sent.")
    return total_alerts
