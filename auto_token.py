#!/usr/bin/env python3
"""auto_token.py — Auto-refresh Stockbit JWT token via Playwright headless.

Usage:
  python3 auto_token.py --login    # Pertama kali: login manual di browser (via CRD)
  python3 auto_token.py            # Headless: auto capture token (untuk cron)
  python3 auto_token.py --check    # Cek apakah token masih valid
"""

import sys, os, time, requests, base64, json, fcntl, tempfile, contextlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from utils.logging_config import redact_secrets

# ── Config ──
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN_FILE = BASE_DIR / ".stockbit_token"
LOCK_FILE = BASE_DIR / ".stockbit_token.lock"
STATE_DIR = BASE_DIR / ".playwright_state"
LOG_FILE = BASE_DIR / "logs" / "auto_token.log"

# Refresh reliability tuning (incident 2026-07-27 hardening — see
# docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md). The margin must comfortably
# exceed the gap from the 08:40 refresh check to the day's last token
# consumer (20:15 WIB, run_broker_flow_fetch) — 11h35m — not just be a
# round-sounding number (the old flat 6h bar was exactly that mistake).
REFRESH_MARGIN_HOURS = float(os.environ.get("STOCKBIT_TOKEN_REFRESH_MARGIN_HOURS", "14"))
MAX_RETRIES = int(os.environ.get("STOCKBIT_TOKEN_REFRESH_MAX_RETRIES", "2"))
RETRY_BACKOFF_BASE_S = float(os.environ.get("STOCKBIT_TOKEN_REFRESH_BACKOFF_BASE_S", "5"))

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
    msg = redact_secrets(msg)  # RC1-C2 — same shared rule as utils.telegram.send_telegram
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


def should_skip_refresh(margin_hours=None):
    """Return True if current token will comfortably outlive today's last
    consumer — skip Playwright entirely. `margin_hours` must cover the gap to
    that consumer, not just be "some positive number" (incident 2026-07-27:
    a flat 6h bar let an 8.9h-remaining token through, which then expired an
    hour before the 18:30 stockbit_flow cron needed it)."""
    if margin_hours is None:
        margin_hours = REFRESH_MARGIN_HOURS
    if not TOKEN_FILE.exists():
        return False
    token = TOKEN_FILE.read_text().strip()
    if not token:
        return False
    remaining = jwt_expiry(token)
    if remaining <= 0:
        return False
    if remaining > 48:
        # A 24h-TTL token can never legitimately have >48h left — treat as a
        # clock-skew/corruption signal and force a real check instead of
        # trusting it blindly.
        log(f"⚠ Implausible remaining time ({remaining:.1f}h) — possible clock skew, forcing refresh check")
        return False
    if remaining > margin_hours:
        if verify_token(token):
            log(f"Token still fresh ({remaining:.1f}h remaining, margin={margin_hours:.1f}h), skipping refresh")
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


def _write_token_atomic(token, token_file=None):
    """Write the token via tmpfile+rename so a crash mid-write can never
    leave a truncated/partial token on disk — readers always see a complete
    old or complete new token."""
    path = Path(token_file) if token_file is not None else TOKEN_FILE
    fd, tmp_path = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(token)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _retry_with_backoff(fn, max_retries=3, backoff_base=1, label="", sleep_fn=time.sleep):
    """Call fn() up to max_retries times, retrying on exception or a falsy
    result, with exponential backoff between attempts. Returns fn()'s result
    or None if every attempt failed."""
    for attempt in range(1, max_retries + 1):
        try:
            result = fn()
        except Exception as e:
            log(f"  [WARN] {label} attempt {attempt}/{max_retries} error: {e}")
            result = None
        else:
            if result:
                return result
            log(f"  [WARN] {label} attempt {attempt}/{max_retries} returned no result")
        if attempt < max_retries:
            delay = backoff_base * (2 ** (attempt - 1))
            log(f"  retrying {label} in {delay}s (attempt {attempt + 1}/{max_retries})")
            sleep_fn(delay)
    return None


@contextlib.contextmanager
def _refresh_lock(lock_path=None):
    """Non-blocking exclusive lock so a second concurrent invocation (manual
    run racing the cron, or a scheduler restart) never launches a second
    Playwright instance against the same .playwright_state profile. Yields
    True if the lock was acquired, False if another refresh already holds it
    — the caller should treat False as a normal, idempotent no-op, not an
    error."""
    path = Path(lock_path) if lock_path is not None else LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "w")
    acquired = False
    try:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def _old_token_still_safe(max_age_hours=20, token_file=None):
    """Return True if the existing on-disk token is still API-valid and not
    old enough to expire before it can next be refreshed."""
    path = Path(token_file) if token_file is not None else TOKEN_FILE
    if not path.exists():
        return False
    token = path.read_text().strip()
    if not token:
        return False
    if not verify_token(token):
        return False
    age_h = (time.time() - _jwt_iat(token)) / 3600
    return age_h < max_age_hours


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

            # Force-clear stale session before navigating to login
            try:
                context.clear_cookies()
                page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e) {} }")
            except Exception:
                pass

            page.goto("https://stockbit.com/login", wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)  # let React render login form

            # If session somehow survived, force logout then re-navigate
            if "login" not in page.url:
                log("Session masih redirect — force clear + re-navigate")
                context.clear_cookies()
                page.goto("https://stockbit.com/login", wait_until="domcontentloaded", timeout=45000)
                time.sleep(3)

            # Stockbit login: id='username' (type=text), id='password'
            EMAIL_SEL = "#username, input[id='username'], input[placeholder*='Email' i], input[placeholder*='username' i]"
            page.wait_for_selector(EMAIL_SEL, state="visible", timeout=20000)
            email_input = page.locator(EMAIL_SEL).first
            email_input.fill(STOCKBIT_USER)

            page.wait_for_selector("input[type='password']", timeout=10000)
            page.locator("input[type='password']").first.fill(STOCKBIT_PASS)

            # Submit — use keyboard Enter (more natural, avoids bot detection on click)
            page.locator("input[type='password']").first.press("Enter")

            # Wait for redirect away from login page
            redirect_ok = False
            try:
                page.wait_for_url(lambda url: "login" not in url, timeout=20000)
                log("Login redirect detected")
                redirect_ok = True
            except Exception:
                cur_url = page.url
                cur_title = page.title()
                log(f"No redirect detected — url={cur_url} title={cur_title}")
                # Save screenshot for diagnosis
                try:
                    ss_path = str(LOG_FILE.parent / "login_debug.png")
                    page.screenshot(path=ss_path)
                    log(f"Screenshot saved: {ss_path}")
                except Exception as ss_err:
                    log(f"Screenshot failed: {ss_err}")
                # Check for error messages (check each selector separately)
                err_texts = ["Invalid", "salah", "incorrect", "captcha", "Captcha", "CAPTCHA", "verifikasi", "robot"]
                for err in err_texts:
                    if page.locator(f"text={err}").count() > 0:
                        log(f"ERROR page text found: '{err}'")
                        break

            if not redirect_ok:
                log("Credential login: no redirect — aborting, session not established")
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

    # Hardening: skip if token will comfortably survive to today's last consumer
    if should_skip_refresh():
        return

    with _refresh_lock() as acquired:
        if not acquired:
            log("Another refresh is already in progress — skipping (idempotent, not an error)")
            return

        check_state_size()
        cleanup_zombies()

        token = _retry_with_backoff(
            auto_refresh, max_retries=MAX_RETRIES, backoff_base=RETRY_BACKOFF_BASE_S,
            label="auto_refresh",
        )

        if token and verify_token(token):
            # Reject stale re-capture: if token was issued >20h ago it will expire
            # before the next cron run — force fresh credential login instead.
            hours_old = (time.time() - _jwt_iat(token)) / 3600
            if hours_old < 20:
                _write_token_atomic(token)
                log(f"✅ Token refreshed (len={len(token)}, age={hours_old:.1f}h)")
                return
            log(f"⚠ Captured token is {hours_old:.1f}h old — forcing credential re-login")

        # Gagal capture — cek token lama masih valid?
        if _old_token_still_safe(max_age_hours=20):
            log("⚠ Capture gagal, tapi token lama masih valid")
            return

        # Coba credential login sebagai last resort (deliberately not
        # auto-retried — a failure here is more likely a hard failure, bad
        # password/CAPTCHA, where blind retries risk tripping bot detection)
        log("Trying credential login as fallback...")
        send_telegram("⚠️ <b>Auto Token</b>: session expired, mencoba credential login...")

        token = credential_login()
        if token and verify_token(token):
            _write_token_atomic(token)
            log("✅ Credential login berhasil — token saved")
            send_telegram("✅ <b>Auto Token</b>: credential login berhasil, token diperbarui.")
            cleanup_zombies()
            return

        # Benar-benar gagal
        old_safe = _old_token_still_safe(max_age_hours=20)
        log(f"REFRESH_FAILED old_token_still_safe={old_safe} action=manual_intervention_required")
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
