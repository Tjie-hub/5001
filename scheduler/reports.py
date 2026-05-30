# scheduler/reports.py
import os
import sqlite3
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

WIB = pytz.timezone("Asia/Jakarta")
DB_PATH = os.getenv("DB_PATH", "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

from utils.telegram import send_telegram  # noqa: E402


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
    import scheduler.state as _state
    try:
        from datetime import datetime as dt
        from paper_trade import get_open_trades

        now = dt.now(WIB)
        time_str = now.strftime("%H:%M")

        trades = get_open_trades()

        # Detect trade-count change vs last run
        prev_ids = set(_state._last_trades_state.keys())
        cur_ids  = {str(t['id']) for t in trades} if trades else set()
        count_changed = prev_ids != cur_ids

        if not trades:
            if count_changed:
                msg = f"📊 <b>Open Trades Report — {time_str}</b>\n\n"
                msg += "✅ No open trades."
                send_telegram(msg)
                print(f"[{time_str}] Open trades report sent (0 trades)")
                _state._last_trades_state = {}
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
                prev = _state._last_trades_state.get(tid)
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
        _state._last_trades_state.update(current_state)
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

        # Foreign accumulation top 5 — appended to evening report
        try:
            from flow_filter import get_top_foreign_accumulation
            fa_all = get_top_foreign_accumulation(top_n=9999)
            fa_buy = [r for r in fa_all if r["score_pct"] > 0][:5]
            fa_sell = sorted(fa_all, key=lambda x: x["score_pct"])[:5]
            fa_sell = [r for r in fa_sell if r["score_pct"] < 0]
            if fa_buy or fa_sell:
                fa_date = fa_all[0]["latest_date"] if fa_all else "N/A"
                msg += f"\n<b>🏛️ Foreign Flow (5d, data: {fa_date}):</b>\n"
                if fa_buy:
                    msg += "  <b>Buy:</b> "
                    msg += " | ".join(f"{r['ticker']} {r['score_pct']:+.1f}%" for r in fa_buy)
                    msg += "\n"
                if fa_sell:
                    msg += "  <b>Sell:</b> "
                    msg += " | ".join(f"{r['ticker']} {r['score_pct']:+.1f}%" for r in fa_sell)
                    msg += "\n"
        except Exception as _fa_err:
            pass  # non-critical — don't break the main report

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
