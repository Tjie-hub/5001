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
            requests.post(url, json=payload, timeout=10)
            _last_sent = time.time()
            return
        except requests.exceptions.RequestException as e:
            if attempt == _MAX_RETRIES:
                logger.error(f"[telegram] send failed after {_MAX_RETRIES + 1} attempts: {e}")
            else:
                time.sleep(2 ** attempt)
