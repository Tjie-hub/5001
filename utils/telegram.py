import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

_MIN_INTERVAL = 1.0  # seconds between sends
_last_sent: float = 0.0
_MAX_RETRIES = 2


def send_telegram(msg: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id or "ISI_" in token:
        return

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
