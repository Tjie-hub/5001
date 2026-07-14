"""Operational alerts for provider quota/availability transitions
(RCA 2026-07-10, Phase 6).

Fires only on state transitions, deduped per key, so a 100-request burst
against an exhausted provider produces ONE alert, not one hundred. Follows
the fail_open_alarm pattern: log at WARNING always, Telegram best-effort,
never raises. Process-local dedupe is deliberate — same lifetime as the
Router whose transitions it reports.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from utils.telegram import send_telegram

from .. import config

logger = logging.getLogger("agent_firm.providers.alerts")

_last_sent: dict[str, float] = {}          # dedupe key -> time.monotonic()
_exhaustion_counts: dict[str, int] = {}    # provider -> limit hits since last recovery


def reset_state() -> None:
    """Test hook: clear dedupe/counter state."""
    _last_sent.clear()
    _exhaustion_counts.clear()


def _emit(key: str, message: str, min_interval_s: Optional[float] = None) -> bool:
    """Log + best-effort Telegram, once per `key` per `min_interval_s`.
    Returns True when the alert was emitted (i.e. not deduped/disabled)."""
    if not config.QUOTA_ALERTS_ENABLED:
        logger.info("provider alert suppressed (disabled): %s", message)
        return False
    interval = min_interval_s if min_interval_s is not None else config.ALERT_MIN_INTERVAL_S
    now = time.monotonic()
    last = _last_sent.get(key)
    if last is not None and now - last < interval:
        return False
    _last_sent[key] = now
    logger.warning(message)
    try:
        send_telegram(message)
    except Exception as err:  # notifier down must not break a provider call
        logger.debug("provider alert notify failed: %s", err)
    return True


def _fmt_reset(reset_time: Optional[datetime]) -> str:
    return reset_time.isoformat() if reset_time is not None else "unknown"


def _audit(provider: str, outcome: str, detail: str) -> None:
    """Best-effort audit-trail record of a provider availability switch
    (security hardening Phase 6). Never raises."""
    try:
        from security.audit_trail import record_audit_event
        record_audit_event("provider_switch", resource=provider,
                           outcome=outcome, detail=detail)
    except Exception as err:
        logger.debug("provider audit record failed: %s", err)


def session_limit_alert(provider: str, reset_time: Optional[datetime],
                        model: Optional[str] = None) -> bool:
    """Provider hit its session/usage window. One alert per reset window."""
    _exhaustion_counts[provider] = _exhaustion_counts.get(provider, 0) + 1
    count = _exhaustion_counts[provider]
    if count >= config.QUOTA_REPEAT_THRESHOLD:
        _emit(
            f"repeat:{provider}",
            f"🔁 PROVIDER QUOTA [{provider}]: repeated session-limit exhaustion "
            f"({count}x without recovery) — consider reducing call volume or "
            f"isolating firm quota",
        )
    emitted = _emit(
        f"limit:{provider}:{_fmt_reset(reset_time)}",
        f"⛔ PROVIDER QUOTA [{provider}"
        + (f"/{model}" if model else "")
        + f"]: session limit reached — held out of rotation, resumes ~{_fmt_reset(reset_time)}",
        min_interval_s=float("inf"),  # key already scopes to the reset window
    )
    if emitted:
        _audit(provider, "held", f"session limit; resumes ~{_fmt_reset(reset_time)}")
    return emitted


def provider_restored_alert(provider: str) -> bool:
    """First successful call after a session-limit hold."""
    _exhaustion_counts.pop(provider, None)
    emitted = _emit(
        f"restored:{provider}",
        f"✅ PROVIDER QUOTA [{provider}]: restored after session-limit hold",
        min_interval_s=60.0,  # a restore is news; only guard against flapping
    )
    if emitted:
        _audit(provider, "restored", "first success after session-limit hold")
    return emitted


def all_providers_unavailable_alert(providers: list[str]) -> bool:
    """Every routed provider is failed/held — the firm is dark."""
    return _emit(
        "all_unavailable",
        f"🚨 PROVIDERS DOWN: all providers unavailable ({', '.join(providers)}) "
        f"— firm requests are failing",
    )
