#!/usr/bin/env python3
"""
Test Telegram connectivity and diagnose issues.
"""
import os
import requests

# Read .env
with open('.env', 'r') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("╔" + "="*68 + "╗")
print("║ TELEGRAM CONNECTIVITY TEST                                            ║")
print("╚" + "="*68 + "╝")
print()

print(f"Token: {TELEGRAM_TOKEN[:20]}..." if TELEGRAM_TOKEN else "NO TOKEN")
print(f"Chat ID: {TELEGRAM_CHAT_ID}")
print()

# Test 1: Get bot info
print("1️⃣  Testing Bot Info...")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    response = requests.get(url, timeout=10)
    data = response.json()
    if data.get('ok'):
        bot_info = data.get('result', {})
        print(f"   ✅ Bot: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
    else:
        print(f"   ❌ Error: {data.get('description')}")
except Exception as e:
    print(f"   ❌ Connection error: {e}")

print()

# Test 2: Get updates (to verify chat)
print("2️⃣  Checking Recent Messages...")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)
    data = response.json()
    if data.get('ok'):
        updates = data.get('result', [])
        chats = set()
        for update in updates[-5:]:
            msg = update.get('message', {})
            if msg:
                chat_id = msg.get('chat', {}).get('id')
                if chat_id:
                    chats.add(chat_id)
        if chats:
            print(f"   ✅ Found {len(chats)} chat(s): {', '.join(map(str, chats))}")
            if TELEGRAM_CHAT_ID in [str(c) for c in chats]:
                print(f"   ✅ Chat ID {TELEGRAM_CHAT_ID} is active")
            else:
                print(f"   ⚠️  Chat ID {TELEGRAM_CHAT_ID} not found in recent updates")
        else:
            print(f"   ⚠️  No recent messages found")
    else:
        print(f"   ❌ Error: {data.get('description')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 3: Send test message
print("3️⃣  Sending Test Message...")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "✅ <b>Open Trades Report System Activated!</b>\n\nReports will be sent at:\n• 10:30 WIB\n• 12:30 WIB\n• 14:30 WIB\n• 16:30 WIB",
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload, timeout=10)
    data = response.json()
    if data.get('ok'):
        print(f"   ✅ Message sent successfully (ID: {data.get('result', {}).get('message_id')})")
    else:
        print(f"   ❌ Error: {data.get('description')}")
        print(f"   Suggestion: Check if bot is in the chat or if chat ID is correct")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("╔" + "="*68 + "╗")
print("║ DIAGNOSTICS                                                         ║")
print("╚" + "="*68 + "╝")
print()
print("💡 If 'chat not found' error:")
print("   1. Make sure bot is added to your chat/channel")
print("   2. Verify chat ID is correct (should be negative for groups)")
print("   3. Try running: python3 test_telegram.py (from bot chat)")
print()
print("💡 If token error:")
print("   1. Verify TELEGRAM_TOKEN in .env is valid")
print("   2. Check token format: should be like '123:ABC...'")
print()
