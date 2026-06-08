import hmac
import hashlib
import threading
import sqlite3
import time
import logging

import requests
from flask import Blueprint, jsonify, request

from config import (
    DB_PATH,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_WEBHOOK_SECRET,
    WEBHOOK_URL,
    WEBHOOK_PATH,
)

telegram_bp = Blueprint("telegram_bot", __name__)

_poller_running = False
_poller_thread = None

# Global polling flag
telegram_polling_active = False
telegram_last_update_id = 0


def handle_telegram_message(message):
    """Process Telegram messages and commands."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').lower().strip()

    if not chat_id:
        return

    # Extract command (text starting with /)
    if text.startswith('/'):
        command = text.split()[0][1:]  # Remove '/'

        if command == 'start':
            send_telegram_reply(chat_id, "🤖 *IDX Walkforward Bot Activated*\n\nAvailable commands:\n/status - Current trading status\n/help - Show help")
        elif command == 'status':
            handle_status_command(chat_id)
        elif command == 'help':
            send_telegram_reply(chat_id,
                "📋 *Available Commands:*\n\n"
                "/status - Get trading status\n"
                "/signals - Recent signals\n"
                "/flow - Flow confirmation status\n"
                "/dashboard - Market risk + top BUY WATCH\n"
                "/help - Show this help message")
        elif command == 'signals':
            handle_signals_command(chat_id)
        elif command == 'flow':
            handle_flow_command(chat_id)
        elif command == 'dashboard':
            handle_dashboard_command(chat_id)
        else:
            send_telegram_reply(chat_id, f"❌ Unknown command: /{command}")
    else:
        # Echo non-command messages
        if text:
            send_telegram_reply(chat_id, f"📝 You said: {text}")

def send_telegram_reply(chat_id, text):
    """Send a reply via Telegram."""
    if "ISI_" in TELEGRAM_TOKEN:
        print(f"[Telegram skip] ChatID:{chat_id} - {text}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram reply error: {e}")

def handle_status_command(chat_id):
    """Get current trading status."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)

        # Get recent trades
        recent = conn.execute(
            "SELECT COUNT(*) FROM ohlcv"
        ).fetchone()[0]

        # Get total tickers
        tickers_count = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM ohlcv"
        ).fetchone()[0]

        conn.close()

        status_msg = f"📊 *Trading Status*\n\nTickers: {tickers_count}\nData points: {recent}\n✅ System Active"
        send_telegram_reply(chat_id, status_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting status: {str(e)}")

def handle_signals_command(chat_id):
    """Get recent signals."""
    try:
        import sqlite3, pandas as pd
        from datetime import datetime, timedelta

        conn = sqlite3.connect(DB_PATH)

        # Get tickers with recent data
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker LIMIT 10"
        ).fetchall()]

        conn.close()

        signals_msg = f"📈 *Recent Signals*\n\nScanned: {len(tickers)} tickers\n✅ Scanning active..."
        send_telegram_reply(chat_id, signals_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting signals: {str(e)}")

def handle_flow_command(chat_id):
    """Get flow confirmation status."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)

        # Get any flow data available
        flow_count = conn.execute(
            "SELECT COUNT(*) FROM broker_flow"
        ).fetchone()[0]

        conn.close()

        flow_msg = f"💰 *Flow Status*\n\nBroker flow records: {flow_count}\n✅ Flow tracking active"
        send_telegram_reply(chat_id, flow_msg)
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Error getting flow: {str(e)}")

def handle_dashboard_command(chat_id):
    """Send compact market dashboard: risk tier + IHSG + top 3 BUY WATCH."""
    try:
        from datetime import date as _date
        from engine.dashboard import get_risk_dashboard, get_watchlist

        today = str(_date.today())
        risk = get_risk_dashboard(DB_PATH, today)
        wl   = get_watchlist(DB_PATH, today)

        score = risk.get('risk_score')
        tier  = risk.get('tier', '—')
        ihsg  = risk.get('ihsg', {})
        flow  = risk.get('foreign_flow', {})

        tier_emoji = {'SAFE': '🟢', 'CAUTION': '🔵', 'WARNING': '⚠️', 'DANGER': '🔴', 'CRITICAL': '🚨'}.get(tier, '❓')

        close = ihsg.get('close')
        ytd   = ihsg.get('ytd_pct')
        ytd_s = f" (YTD {'+' if (ytd or 0)>0 else ''}{ytd:.1f}%)" if ytd is not None else ''

        flow_5d = flow.get('net_5d')
        def _fflow(v):
            if v is None: return '—'
            a, s = abs(v), '+' if v >= 0 else '-'
            if a >= 1e12: return f"{s}Rp{a/1e12:.1f}T"
            if a >= 1e9:  return f"{s}Rp{a/1e9:.1f}B"
            return f"{s}Rp{a/1e6:.0f}M"

        lines = [
            f"📊 *Market Dashboard* — {today}",
            f"",
            f"{tier_emoji} Risk: *{round(score) if score is not None else '—'}/100* — {tier}",
            f"🏦 IHSG: *{f'{close:,.0f}' if close else '—'}*{ytd_s}",
            f"💸 Foreign 5d: {_fflow(flow_5d)} ({flow.get('trend','—')})",
        ]

        buy_watch = wl.get('buy_watch', [])[:3]
        if buy_watch:
            lines += ['', f"🟢 *BUY WATCH* ({len(wl.get('buy_watch',[]))} tickers)"]
            for i, r in enumerate(buy_watch, 1):
                bounce = f"+{r.get('bounce_pct',0):.1f}% bounce" if r.get('bounce_pct') else ''
                fgn    = _fflow(r.get('foreign_net_today'))
                lines.append(f"{i}. *{r['ticker']}* — {bounce}, Fgn {fgn}")
        else:
            lines += ['', '🟢 No BUY WATCH tickers today']

        avoid = wl.get('avoid', [])
        if avoid:
            lines += ['', f"🔴 *AVOID* ({len(avoid)} tickers): {', '.join(r['ticker'] for r in avoid[:5])}"]

        send_telegram_reply(chat_id, '\n'.join(lines))
    except Exception as e:
        send_telegram_reply(chat_id, f"❌ Dashboard error: {e}")


@telegram_bp.route('/telegram/updates', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook updates."""
    if TELEGRAM_WEBHOOK_SECRET:
        incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(incoming, TELEGRAM_WEBHOOK_SECRET):
            return jsonify({'ok': False}), 403
    try:
        data = request.get_json()

        if data and 'message' in data:
            message = data['message']
            handle_telegram_message(message)
        elif data and 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['from']['id']
            send_telegram_reply(chat_id, "Button clicked! Coming soon...")

        return jsonify({'ok': True}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'ok': False}), 500

@telegram_bp.route('/telegram/setup', methods=['GET'])
def setup_telegram_webhook():
    """Setup Telegram in polling mode (local development friendly)."""
    try:
        # Switch to polling mode (doesn't require HTTPS)
        remove_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        response = requests.post(remove_url, json={"drop_pending_updates": True}, timeout=10)

        result = response.json()

        if result.get('ok'):
            global telegram_polling_active
            telegram_polling_active = True
            from scheduler import send_telegram
            msg = f"✅ Telegram polling mode activated!\n\nPolling updates at /telegram/start-polling"
            send_telegram(msg)
            return jsonify({
                'success': True,
                'message': 'Telegram polling mode activated',
                'mode': 'polling',
                'instructions': 'Polling is now active and running in background',
                'webhook_url': None
            }), 200
        else:
            error = result.get('description', 'Unknown error')
            return jsonify({
                'success': False,
                'error': error
            }), 400
    except Exception as e:
        logging.exception("api error")
        return jsonify({
            'success': False,
            'error': 'internal error'
        }), 500


def poll_telegram_updates_once():
    """Fetch and process new Telegram updates once."""
    global telegram_last_update_id

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {
        'offset': telegram_last_update_id + 1,
        'timeout': 2,
        'allowed_updates': ['message', 'callback_query']
    }
    response = requests.get(url, params=params, timeout=10)
    result = response.json()

    updates = []
    if result.get('ok'):
        updates = result.get('result', [])
        for update in updates:
            update_id = update.get('update_id')
            if update_id > telegram_last_update_id:
                telegram_last_update_id = update_id

            if 'message' in update:
                handle_telegram_message(update['message'])
            elif 'callback_query' in update:
                callback = update['callback_query']
                chat_id = callback['from']['id']
                send_telegram_reply(chat_id, "Button clicked! Coming soon...")

    return updates


def telegram_poller_loop():
    """Continuously poll Telegram for new updates when polling is active."""
    while True:
        if telegram_polling_active:
            try:
                updates = poll_telegram_updates_once()
                if updates:
                    print(f"[Telegram poll] {len(updates)} new updates processed")
            except Exception as e:
                print(f"[Telegram poll error] {e}")
        time.sleep(3)


@telegram_bp.route('/telegram/start-polling', methods=['GET'])
def start_telegram_polling():
    """Start polling for Telegram updates."""
    global telegram_polling_active

    telegram_polling_active = True

    return jsonify({
        'success': True,
        'message': 'Telegram polling started',
        'status': 'polling',
        'note': 'Polling will run in the background and process updates automatically'
    }), 200

@telegram_bp.route('/telegram/stop-polling', methods=['GET'])
def stop_telegram_polling():
    """Stop polling for Telegram updates."""
    global telegram_polling_active

    telegram_polling_active = False

    return jsonify({
        'success': True,
        'message': 'Telegram polling stopped'
    }), 200

@telegram_bp.route('/telegram/poll-updates', methods=['GET'])
def telegram_poll_updates():
    """Poll for new Telegram updates."""
    global telegram_last_update_id

    try:
        if not telegram_polling_active:
            return jsonify({
                'success': True,
                'updates': [],
                'note': 'Polling not active. Call /telegram/start-polling first'
            }), 200

        # Get updates
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {
            'offset': telegram_last_update_id + 1,
            'timeout': 2,
            'allowed_updates': ['message', 'callback_query']
        }
        response = requests.get(url, params=params, timeout=10)
        result = response.json()

        updates = []
        if result.get('ok'):
            updates = result.get('result', [])

            # Process each update
            for update in updates:
                update_id = update.get('update_id')
                if update_id > telegram_last_update_id:
                    telegram_last_update_id = update_id

                # Handle message
                if 'message' in update:
                    message = update['message']
                    handle_telegram_message(message)

                # Handle callback query
                elif 'callback_query' in update:
                    callback = update['callback_query']
                    chat_id = callback['from']['id']
                    send_telegram_reply(chat_id, "Button clicked! Coming soon...")

        return jsonify({
            'success': True,
            'updates_received': len(updates),
            'last_update_id': telegram_last_update_id,
            'updates': updates
        }), 200
    except Exception as e:
        logging.exception("api error")
        return jsonify({
            'success': False,
            'error': 'internal error'
        }), 500

@telegram_bp.route('/telegram/status', methods=['GET'])
def telegram_webhook_status():
    """Check Telegram polling status."""
    try:
        get_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo"
        response = requests.post(get_url, timeout=10)
        info = response.json()

        if info.get('ok'):
            webhook_info = info.get('result', {})
            return jsonify({
                'success': True,
                'mode': 'polling',
                'polling_active': telegram_polling_active,
                'last_update_id': telegram_last_update_id,
                'webhook_url': webhook_info.get('url', 'Not set (using polling)'),
                'webhook_active': webhook_info.get('url') != '',
                'pending_update_count': webhook_info.get('pending_update_count', 0),
                'endpoints': {
                    'setup': 'GET /telegram/setup',
                    'start_polling': 'GET /telegram/start-polling',
                    'stop_polling': 'GET /telegram/stop-polling',
                    'poll': 'GET /telegram/poll-updates',
                    'status': 'GET /telegram/status'
                }
            }), 200
        else:
            return jsonify({'success': False, 'error': info.get('description')}), 400
    except Exception as e:
        logging.exception("telegram status error")
        return jsonify({'success': False, 'error': 'internal error'}), 500
