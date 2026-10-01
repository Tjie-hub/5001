"""Shared helpers for the owner-todo cron jobs (scripts/ops, 2026-10-01).

Stdlib-only at import time on purpose: tests load these modules directly, and
the repo's own Telegram sender (utils.telegram) is imported lazily only when a
message is actually sent.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

# Every ops job message carries this prefix: no ops chat is configured, so the
# single configured TELEGRAM_CHAT_ID receives these alongside trading alerts.
OPS_PREFIX = "[OPS]"


def repo_root() -> Path:
    """Repository root of the tree this file lives in (…/<repo>/scripts/ops/)."""
    return Path(__file__).resolve().parents[2]


def now_wib() -> datetime:
    return datetime.now(WIB)


def today_wib() -> str:
    return now_wib().strftime("%Y-%m-%d")


def send_ops(msg: str, *, dry: bool = False, root: Path | None = None) -> None:
    """Send one ops message through the repo's existing Telegram sender.

    category="alert" deliberately: logs/TELEGRAM_MUTE can silence report
    categories but is structurally unable to silence "alert", and these
    owner-facing messages must survive that mute file. Importing `config`
    loads <root>/.env into os.environ, which is where utils.telegram reads
    TELEGRAM_TOKEN/TELEGRAM_CHAT_ID — the same path every other cron sender
    takes.
    """
    if dry:
        print(msg)
        return
    root = root or repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import config  # noqa: F401  side effect: loads <root>/.env
    from utils.telegram import send_telegram

    send_telegram(msg, category="alert")
