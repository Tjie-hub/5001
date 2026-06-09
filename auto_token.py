#!/usr/bin/env python3
"""auto_token.py — Auto-refresh Stockbit JWT token via Playwright headless.

Usage:
  python3 auto_token.py --login    # Pertama kali: login manual di browser (via CRD)
  python3 auto_token.py            # Headless: auto capture token (untuk cron)
  python3 auto_token.py --check    # Cek apakah token masih valid
"""

import sys, os, time, requests, base64, json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Config ──
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN_FILE = BASE_DIR / ".stockbit_token"
STATE_DIR = BASE_DIR / ".playwright_state"
LOG_FILE = BASE_DIR / "logs" / "auto_token.log"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STOCKBIT_USER = os.environ.get("STOCKBIT_USER")
STOCKBIT_PASS = os.environ.get("STOCKBIT_PASS")

STOCKBIT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}

MAX_STATE_MB = 500  # warn if browser state grows past this


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


def jwt_expiry(token):
    """Return remaining hours until JWT expiry, or -1 if unreadable."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return (data.get("exp", 0) - time.time()) / 3600
    except Exception:
        return -1


def _jwt_iat(token):
    """Return issued-at unix timestamp, or 0 if unreadable."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("iat", 0)
    except Exception:
        return 0


def should_skip_refresh():
    """Return True if current token is still fresh — skip Playwright entirely."""
    if not TOKEN_FILE.exists():
        return False
    token = TOKEN_FILE.read_text().strip()
    if not token:
        return False
    remaining = jwt_expiry(token)
    if remaining > 6:
        if verify_token(token):
            log(f"Token still fresh ({remaining:.1f}h remaining), skipping refresh")
            return True
    return False


def cleanup_zombies():
    """Kill orphaned chromium processes older than 5 minutes."""
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "chromium.*--disable-blink-features"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split()
            log(f"Cleaning up {len(pids)} zombie chromium process(es)")
            for pid in pids:
                try:
                    os.kill(int(pid), 9)
                except ProcessLookupError:
                    pass
    except Exception:
        pass


def check_state_size():
    """Log warning if browser state directory is too large."""
    if not STATE_DIR.exists():
        return
    try:
        total = sum(f.stat().st_size for f in STATE_DIR.rglob("*") if f.is_file())
        mb = total / (1024 * 1024)
        if mb > MAX_STATE_MB:
            log(f"⚠ Browser state is {mb:.0f}MB (limit={MAX_STATE_MB}MB) — consider recreating session")
    except Exception:
        pass


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

            # Retry dengan page baru kalau gagal
            if not token:
                log("First attempt failed, retrying with fresh page...")
                try:
                    new_page = context.new_page()
                    token = _capture_from_page(new_page)
                    new_page.close()
                except Exception as e:
                    log(f"Retry error: {e}")
        finally:
            context.close()

    return token


def _capture_from_page(page, navigate=True):
    """Navigate to Stockbit and intercept JWT from network requests."""
    captured_token = None
    deadline = time.time() + 55  # hard timeout — prevent hanging

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
                wait_until="domcontentloaded",
                timeout=30000,
            )
        # Active wait — check token every 1s, bail at deadline
        while not captured_token and time.time() < deadline:
            time.sleep(1)

        if not captured_token:
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(2)

    except Exception as e:
        log(f"Capture error: {e}")

    page.remove_listener("request", on_request)
    return captured_token


# ── Mode 2b: Credential Login (headless, auto fallback) ──
def credential_login():
    """Auto-fill login form headlessly using credentials from .env."""
    if not STOCKBIT_USER or not STOCKBIT_PASS:
        log("ERROR: STOCKBIT_USER / STOCKBIT_PASS not set in .env")
        return None

    if STOCKBIT_USER == "your_email@example.com":
        log("ERROR: STOCKBIT_USER is still placeholder — update .env first")
        return None

    from playwright.sync_api import sync_playwright

    log(f"Credential login started (headless) for {STOCKBIT_USER}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

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

        token = None
        try:
            page = context.pages[0] if context.pages else context.new_page()

            captured_token = None

            def on_request(request):
                nonlocal captured_token
                auth = request.headers.get("authorization", "")
                if auth.startswith("Bearer ") and "exodus.stockbit.com" in request.url:
                    captured_token = auth[7:]

            page.on("request", on_request)

            page.goto("https://stockbit.com/login", wait_until="domcontentloaded", timeout=45000)

            # Detect session redirect: still logged in → logout first to force fresh JWT
            if "login" not in page.url:
                log("Session masih valid — logout dulu agar dapat fresh JWT")
                try:
                    page.goto("https://stockbit.com/logout", wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)
                page.goto("https://stockbit.com/login", wait_until="domcontentloaded", timeout=45000)
                # If still not on login page after logout, clear storage manually
                if "login" not in page.url:
                    context.clear_cookies()
                    page.goto("https://stockbit.com/login", wait_until="domcontentloaded", timeout=45000)

            # Actually on login page — fill credentials
            page.wait_for_selector("input[type='email'], input[name='username'], input[placeholder*='Email' i]", timeout=15000)
            email_input = page.locator("input[type='email'], input[name='username'], input[placeholder*='Email' i]").first
            email_input.fill(STOCKBIT_USER)

            page.wait_for_selector("input[type='password']", timeout=10000)
            page.locator("input[type='password']").first.fill(STOCKBIT_PASS)

            # Submit
            page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Masuk')").first.click()

            # Wait for redirect away from login page
            try:
                page.wait_for_url(lambda url: "login" not in url, timeout=20000)
                log("Login redirect detected")
            except Exception:
                log("No redirect detected — checking for errors")
                if page.locator("text=Invalid, text=salah, text=incorrect").count() > 0:
                    log("ERROR: Wrong credentials")
                    page.remove_listener("request", on_request)
                    return None

            # Navigate to symbol page to capture token
            time.sleep(3)
            page.goto("https://stockbit.com/symbol/BBCA", wait_until="domcontentloaded", timeout=45000)
            time.sleep(8)

            if not captured_token:
                page.evaluate("window.scrollBy(0, 300)")
                time.sleep(2)

            page.remove_listener("request", on_request)
            token = captured_token

        except Exception as e:
            log(f"Credential login error: {e}")
        finally:
            context.close()

    return token


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

    # Hardening: skip if token is still fresh
    if should_skip_refresh():
        return

    check_state_size()
    cleanup_zombies()

    token = auto_refresh()

    if token and verify_token(token):
        # Reject stale re-capture: if token was issued >20h ago it will expire
        # before the next cron run — force fresh credential login instead.
        hours_old = (time.time() - _jwt_iat(token)) / 3600
        if hours_old < 20:
            TOKEN_FILE.write_text(token)
            log(f"✅ Token refreshed (len={len(token)}, age={hours_old:.1f}h)")
            return
        log(f"⚠ Captured token is {hours_old:.1f}h old — forcing credential re-login")

    # Gagal capture — cek token lama masih valid?
    if TOKEN_FILE.exists():
        old_token = TOKEN_FILE.read_text().strip()
        if old_token and verify_token(old_token):
            hours_old = (time.time() - _jwt_iat(old_token)) / 3600
            if hours_old < 20:
                log("⚠ Capture gagal, tapi token lama masih valid")
                return

    # Coba credential login sebagai last resort
    log("Trying credential login as fallback...")
    send_telegram("⚠️ <b>Auto Token</b>: session expired, mencoba credential login...")

    token = credential_login()
    if token and verify_token(token):
        TOKEN_FILE.write_text(token)
        log("✅ Credential login berhasil — token saved")
        send_telegram("✅ <b>Auto Token</b>: credential login berhasil, token diperbarui.")
        cleanup_zombies()
        return

    # Benar-benar gagal
    log("❌ Token capture GAGAL dan credential login juga gagal")
    send_telegram(
        "⚠️ <b>Stockbit Auto Token GAGAL</b>\n\n"
        "Session expired + credential login gagal.\n"
        "Kemungkinan: password berubah atau ada CAPTCHA.\n\n"
        "Refresh manual sebelum 08:50:\n"
        "1. CRD → Chrome → stockbit.com/symbol/BBCA\n"
        "2. F12 → Network → Fetch/XHR → refresh\n"
        "3. Copy Bearer token\n"
        "4. <code>echo 'TOKEN' > ~/.stockbit_token</code>\n\n"
        "Atau re-login:\n"
        "<code>python3 auto_token.py --login</code>"
    )
    cleanup_zombies()
    sys.exit(1)


if __name__ == "__main__":
    main()
