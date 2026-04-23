#!/usr/bin/env python3
"""auto_token.py — Auto-refresh Stockbit JWT token via Playwright headless.

Usage:
  python3 auto_token.py --login    # Pertama kali: login manual di browser (via CRD)
  python3 auto_token.py            # Headless: auto capture token (untuk cron)
  python3 auto_token.py --check    # Cek apakah token masih valid
"""

import sys, os, time, requests
from datetime import datetime
from pathlib import Path

# ── Config ──
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / ".stockbit_token"
STATE_DIR = BASE_DIR / ".playwright_state"
LOG_FILE = BASE_DIR / "logs" / "auto_token.log"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STOCKBIT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}


# ── Helpers ──
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log(
            "Telegram not configured (set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID env vars)"
        )
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        log(f"Telegram send failed: {e}")


def verify_token(token):
    """Test token against Stockbit keystats API."""
    headers = {**STOCKBIT_HEADERS, "Authorization": f"Bearer {token}"}
    try:
        r = requests.get(
            "https://exodus.stockbit.com/keystats/BBCA", headers=headers, timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


# ── Mode 1: Initial Login (non-headless, via CRD) ──
def initial_login():
    from playwright.sync_api import sync_playwright

    # CRD biasanya pakai :20, tapi cek DISPLAY yang aktif
    display = os.environ.get("DISPLAY")
    if not display:
        # Coba detect CRD display
        import subprocess

        try:
            result = subprocess.run(
                ["bash", "-c", 'ls /tmp/.X11-unix/ | sed "s/X/:/g" | tail -1'],
                capture_output=True,
                text=True,
            )
            display = result.stdout.strip() or ":20"
        except Exception:
            display = ":20"
        os.environ["DISPLAY"] = display

    log(f"Starting login browser on DISPLAY={display}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(STATE_DIR),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            user_agent=STOCKBIT_HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720},
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://stockbit.com/login", wait_until="domcontentloaded")

            print()
            print("=" * 55)
            print("  LOGIN STOCKBIT DI BROWSER YANG TERBUKA")
            print("  Setelah login berhasil, tekan ENTER di sini")
            print("=" * 55)
            input()

            # Verify: buka halaman saham, capture token
            captured = _capture_from_page(page)
        finally:
            context.close()

    if captured and verify_token(captured):
        TOKEN_FILE.write_text(captured)
        log(f"Initial login OK — token saved (len={len(captured)})")
        print(f"\n✅ Token saved! Auto-refresh siap dipakai.")
    else:
        log("Initial login done — session saved, tapi token belum ter-capture")
        print(f"\n⚠ Session tersimpan. Coba run: python3 auto_token.py")


# ── Mode 2: Auto Refresh (headless, untuk cron) ──
def auto_refresh():
    from playwright.sync_api import sync_playwright

    if not STATE_DIR.exists():
        log("ERROR: No saved session")
        send_telegram(
            "⚠️ <b>Auto Token GAGAL</b>\n"
            "Session belum ada. Login dulu via CRD:\n"
            "<code>python3 auto_token.py --login</code>"
        )
        return None

    log("Auto refresh started (headless)")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(STATE_DIR),
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            user_agent=STOCKBIT_HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720},
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            token = _capture_from_page(page)

            # Kalau gagal, coba sekali lagi dengan navigasi ulang
            # (listener harus aktif SEBELUM page.goto agar tidak miss request)
            if not token:
                log("First attempt failed, retrying...")
                try:
                    token = _capture_from_page(page, navigate=True)
                except Exception as e:
                    log(f"Retry error: {e}")
        finally:
            context.close()

    return token


def _capture_from_page(page, navigate=True):
    """Navigate to Stockbit and intercept JWT from network requests."""
    captured_token = None

    def on_request(request):
        nonlocal captured_token
        url = request.url
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer ") and "exodus.stockbit.com" in url:
            captured_token = auth[7:]

    page.on("request", on_request)

    try:
        if navigate:
            page.goto(
                "https://stockbit.com/symbol/BBCA",
                wait_until="networkidle",
                timeout=45000,
            )
        # Tunggu API calls lazy-load
        time.sleep(5)

        # Scroll untuk trigger lebih banyak API calls kalau belum dapat
        if not captured_token:
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(3)

    except Exception as e:
        log(f"Capture error: {e}")

    page.remove_listener("request", on_request)
    return captured_token


# ── Mode 3: Check existing token ──
def check_token():
    if not TOKEN_FILE.exists():
        print("❌ Token file tidak ada")
        return False

    token = TOKEN_FILE.read_text().strip()
    if not token:
        print("❌ Token file kosong")
        return False

    # Decode JWT expiry (tanpa library)
    try:
        import base64, json

        payload = token.split(".")[1]
        # Fix padding
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = data.get("exp", 0)
        iat = data.get("iat", 0)
        now = time.time()
        remaining_h = (exp - now) / 3600
        print(
            f"Token issued:  {datetime.fromtimestamp(iat).strftime('%Y-%m-%d %H:%M')}"
        )
        print(
            f"Token expires: {datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M')}"
        )
        print(f"Remaining:     {remaining_h:.1f} hours")
    except Exception as e:
        print(f"JWT decode error: {e}")

    valid = verify_token(token)
    print(f"API test:      {'✅ Valid' if valid else '❌ Expired/Invalid'}")
    return valid


# ── Main ──
def main():
    if "--login" in sys.argv:
        initial_login()
        return

    if "--check" in sys.argv:
        check_token()
        return

    # Auto mode (untuk cron)
    log("=" * 40)
    log("STOCKBIT AUTO TOKEN")
    log("=" * 40)

    token = auto_refresh()

    if token and verify_token(token):
        TOKEN_FILE.write_text(token)
        log(f"✅ Token refreshed (len={len(token)})")
        # Silent success — hanya Telegram kalau gagal, supaya tidak spam
        return

    # Gagal capture — cek token lama masih valid?
    if TOKEN_FILE.exists():
        old_token = TOKEN_FILE.read_text().strip()
        if old_token and verify_token(old_token):
            log("⚠ Capture gagal, tapi token lama masih valid")
            # Token lama masih jalan, tidak perlu alert
            return

    # Benar-benar gagal
    log("❌ Token capture GAGAL dan token lama expired")
    send_telegram(
        "⚠️ <b>Stockbit Auto Token GAGAL</b>\n\n"
        "Token expired, auto-refresh gagal.\n"
        "Refresh manual sebelum 08:50:\n"
        "1. CRD → Chrome → stockbit.com/symbol/BBCA\n"
        "2. F12 → Network → Fetch/XHR → refresh\n"
        "3. Copy Bearer token\n"
        "4. <code>echo 'TOKEN' > ~/.stockbit_token</code>\n\n"
        "Atau re-login session:\n"
        "<code>python3 auto_token.py --login</code>"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
