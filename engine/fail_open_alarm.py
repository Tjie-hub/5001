"""Make silent fail-open events visible.

A "fail-open" is any point where a safety gate, on error/outage, lets signals
through (or falls back) rather than blocking. Historically these were logged at
best and never surfaced, so an LLM / flow / data outage silently degraded the
pipeline. This module records each fail-open at WARNING and best-effort notifies,
so an outage alarms instead of hiding. Import is side-effect free; call
``fail_open_alarm(...)`` at the fail-open site.
"""
import logging

from utils.telegram import send_telegram

logger = logging.getLogger(__name__)


def format_fail_open_alarm(source: str, detail: str, count: int) -> str:
    """Pure: build the human-readable alarm line (no side effects)."""
    return f"⚠️ FAIL-OPEN [{source}]: {detail} ({count} affected)"


def fail_open_alarm(source: str, detail: str, count: int = 0,
                    notify: bool = True) -> str:
    """Record a fail-open: log at WARNING and best-effort Telegram.

    Returns the formatted message. Never raises — a fail-open alarm must not
    itself break the pipeline.
    """
    msg = format_fail_open_alarm(source, detail, count)
    logger.warning(msg)
    if notify:
        try:
            send_telegram(msg)
        except Exception as _e:  # best-effort: notifier down must not raise
            logger.debug("fail_open_alarm notify failed: %s", _e)
    return msg


def format_fail_closed_alarm(source: str, detail: str, count: int) -> str:
    """Pure: build the human-readable alarm line for a fail-closed block (no side effects)."""
    return f"🛑 FAIL-CLOSED [{source}]: {detail} ({count} affected)"


def fail_closed_alarm(source: str, detail: str, count: int = 0,
                      notify: bool = True) -> str:
    """Record a fail-closed block: log at WARNING and best-effort Telegram.

    Companion to fail_open_alarm for entry gates that must block (not pass)
    a candidate when they cannot evaluate (AN-5). Same plumbing, opposite
    polarity — the message must say FAIL-CLOSED, not FAIL-OPEN, so an
    operator reading the alert knows the candidate was blocked, not admitted.

    Returns the formatted message. Never raises — an alarm must not itself
    break the pipeline.
    """
    msg = format_fail_closed_alarm(source, detail, count)
    logger.warning(msg)
    if notify:
        try:
            send_telegram(msg)
        except Exception as _e:  # best-effort: notifier down must not raise
            logger.debug("fail_closed_alarm notify failed: %s", _e)
    return msg
