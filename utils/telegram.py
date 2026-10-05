import logging
import os
import time

import requests

from utils.logging_config import redact_secrets

logger = logging.getLogger(__name__)

_MIN_INTERVAL = 1.0  # seconds between sends
_last_sent: float = 0.0
_MAX_RETRIES = 2

# ── Temporary report-noise mute (audit window, 2026-09-16) ─────────────────
# Scheduled REPORT sends are tagged with an explicit category= token; listing
# that token in logs/TELEGRAM_MUTE (one per line, '#' comments) silences them
# without touching any job logic. Alert-path sends use the default
# category="alert", which is_muted() refuses to silence — health/heartbeat/
# error, data-coverage and execution/risk alerts are structurally immune.
# The file is re-read on mtime change (no restart needed once loaded); delete
# it to restore every message. Temporary by design — remove after the audit.
_MUTE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "logs", "TELEGRAM_MUTE")
_mute_cache = None  # (st_mtime, frozenset(tokens)) | None

# ── Global outbound kill switch (owner-ordered blackout, 2026-10-05) ────────
# While logs/TELEGRAM_OFF exists, NO outbound notification leaves this repo
# through any sender — including the 'alert' category TELEGRAM_MUTE structurally
# protects. The standalone python senders (stockbit_fetcher.py, auto_token.py,
# routes/telegram.py send_telegram_reply) and the bash wrapper
# scripts/cron_wrap.sh check the same file. Suppressed sends are still logged
# with category + first 80 chars, so the later what-to-send curation has a full
# record: journalctl --user -u idx-walkforward | grep 'global OFF'.
# Restore everything: delete the file. Checked per send, no restart needed.
_OFF_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "logs", "TELEGRAM_OFF")


def is_off() -> bool:
    """True while logs/TELEGRAM_OFF exists (total outbound blackout)."""
    return os.path.exists(_OFF_FILE)


def is_muted(category: str) -> bool:
    """True when `category` is listed in logs/TELEGRAM_MUTE (mtime-cached).

    The default 'alert' category is never mutable — see the module comment."""
    global _mute_cache
    if not category or category == "alert":
        return False
    try:
        mtime = os.stat(_MUTE_FILE).st_mtime
    except OSError:
        _mute_cache = None
        return False
    if _mute_cache is None or _mute_cache[0] != mtime:
        try:
            with open(_MUTE_FILE) as fh:
                toks = frozenset(ln.strip().lower() for ln in fh
                                 if ln.strip() and not ln.lstrip().startswith("#"))
        except OSError:
            toks = frozenset()
        _mute_cache = (mtime, toks)
    return category.lower() in _mute_cache[1]


def send_telegram(msg: str, category: str = "alert") -> None:
    if is_off():
        logger.info("[telegram] suppressed (global OFF): category=%s: %.80s",
                    category, str(msg).replace("\n", " "))
        return
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id or "ISI_" in token:
        return
    if is_muted(category):
        logger.info("[telegram] muted (category=%s): %.80s",
                    category, str(msg).replace("\n", " "))
        return

    # RC1 fix R-4: every outbound alert passes through the same secret-redaction
    # rule as log lines (utils.logging_config.redact_secrets) — e.g. an
    # exception message that happens to embed a token must never ship to
    # Telegram unmasked just because it skipped the logging path.
    msg = redact_secrets(msg)

    global _last_sent
    elapsed = time.time() - _last_sent
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                _last_sent = time.time()
                logger.info(f"[telegram] sent OK ({len(msg)} chars)")
                return
            # 400 often means HTML parse error — strip to plain text and retry
            if resp.status_code == 400 and payload.get("parse_mode") == "HTML":
                logger.warning(f"[telegram] HTML parse error (400), retrying as plain text")
                payload["parse_mode"] = None
                resp2 = requests.post(url, json=payload, timeout=10)
                if resp2.ok:
                    _last_sent = time.time()
                    logger.info(f"[telegram] sent OK as plain text ({len(msg)} chars)")
                    return
                logger.error(f"[telegram] plain-text fallback also failed: {resp2.status_code} {resp2.text[:200]}")
                return
            logger.error(f"[telegram] HTTP {resp.status_code}: {resp.text[:200]}")
            if attempt < _MAX_RETRIES:
                time.sleep(2 ** attempt)
            else:
                return
        except requests.exceptions.RequestException as e:
            if attempt == _MAX_RETRIES:
                logger.error(f"[telegram] send failed after {_MAX_RETRIES + 1} attempts: {e}")
            else:
                time.sleep(2 ** attempt)
