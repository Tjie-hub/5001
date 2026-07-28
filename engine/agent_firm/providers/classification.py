"""Provider failure classification (RCA 2026-07-10).

During the 2026-07-10 failover incident every Claude CLI quota rejection
exited 1 with the diagnosis — "You've hit your session limit · resets 6:20pm
(Asia/Jakarta)" — on STDOUT, which the provider discarded, while stderr was
empty; the quota regex also had no "session limit" pattern. All 137 failures
therefore collapsed into ProviderUnavailable("claude CLI exited 1").

This module classifies a failed CLI invocation from BOTH streams into an
explicit category and, for session limits, extracts the advertised reset
time so the Router can hold the provider until the window reopens.
Pure functions — no I/O.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from .errors import (
    ProviderAuthFailed, ProviderException, ProviderNetworkFailure,
    ProviderQuotaExceeded, ProviderRateLimited, ProviderSessionLimit,
    ProviderTimeout, ProviderUnavailable, ProviderUnexpectedError,
)

_MESSAGE_MAX = 400  # keep event `reason` strings readable

_FALLBACK_TZ = ZoneInfo("Asia/Jakarta")

# Ordered: first match wins. Session limit before the generic quota patterns
# so the reset time is not lost to a broader match.
#
# RCA 2026-07-13: Claude's subscription wording changed from "You've hit your
# session limit · resets 6:20pm" to "You're out of extra usage · resets 12am".
# The new phrasing matched neither pattern, so 111+ session-limit rejections
# collapsed into provider_unavailable and Claude was retried every 30s (circuit
# cooldown) instead of being held to the advertised reset time. "out of extra
# usage" is recognized as a session limit because it always carries a reset time.
_SESSION_LIMIT = re.compile(
    r"session limit|hit your.*limit|5.hour limit|out of extra usage|out of extra",
    re.IGNORECASE,
)
_QUOTA = re.compile(r"usage limit|quota|out of credits", re.IGNORECASE)
_RATE_LIMIT = re.compile(r"rate limit|too many requests|429", re.IGNORECASE)
_AUTH = re.compile(
    r"/login|log ?in required|not logged in|authentication|unauthorized"
    r"|invalid api key|credential|oauth token|\b401\b",
    re.IGNORECASE,
)
_NETWORK = re.compile(
    r"enotfound|econnrefused|econnreset|etimedout|epipe|fetch failed"
    r"|network|socket hang up|dns|connection (?:refused|reset|closed|error)",
    re.IGNORECASE,
)
_TIMEOUT = re.compile(r"timed? ?out", re.IGNORECASE)

# "resets 6:20pm (Asia/Jakarta)" / "resets 11am (Asia/Jakarta)" / "resets at 1:20pm"
_RESET = re.compile(
    r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)\b(?:\s*\(([^)]+)\))?",
    re.IGNORECASE,
)


@dataclass
class ClassifiedFailure:
    category: str
    message: str
    reset_time: Optional[datetime] = None


def parse_session_reset(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Extract the advertised reset time ("resets 6:20pm (Asia/Jakarta)") as
    an aware datetime — the NEXT occurrence of that wall-clock time in the
    stated zone. Returns None when no reset phrase is present."""
    if not text:
        return None
    m = _RESET.search(text)
    if m is None:
        return None
    hour, minute, meridiem, tz_name = (
        int(m.group(1)), int(m.group(2) or 0), m.group(3).lower(), m.group(4),
    )
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    try:
        tz = ZoneInfo(tz_name) if tz_name else _FALLBACK_TZ
    except Exception:
        tz = _FALLBACK_TZ
    now = now if now is not None else datetime.now(timezone.utc)
    local_now = now.astimezone(tz)
    candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate


def _extract_json_result(stdout: str) -> str:
    """`claude --output-format json` may wrap the diagnosis in a result
    payload; surface the embedded text so the patterns can see it."""
    s = stdout.strip()
    if not s.startswith("{"):
        return stdout
    try:
        payload = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return stdout
    if isinstance(payload, dict):
        parts = [str(payload.get(k)) for k in ("result", "error", "message")
                 if payload.get(k)]
        if parts:
            return " ".join(parts)
    return stdout


def classify_cli_failure(returncode: int, stdout: str, stderr: str) -> ClassifiedFailure:
    """Classify a failed CLI invocation from both output streams.

    The diagnostic message prefers stderr (when present) but always includes
    an stdout excerpt, and BOTH streams are scanned for patterns — the exact
    gap that hid the 2026-07-10 session-limit failures.
    """
    stdout_text = _extract_json_result(stdout or "").strip()
    stderr_text = (stderr or "").strip()
    scan = f"{stderr_text}\n{stdout_text}"

    parts = [p for p in (stderr_text, stdout_text) if p]
    message = " | ".join(parts) if parts else f"claude CLI exited {returncode} (no output)"
    message = message[:_MESSAGE_MAX]

    if returncode < 0:
        return ClassifiedFailure(
            category="unexpected_error",
            message=f"claude CLI killed by signal {-returncode}: {message}"[:_MESSAGE_MAX],
        )
    if _SESSION_LIMIT.search(scan):
        return ClassifiedFailure(
            category="session_limit_exceeded", message=message,
            reset_time=parse_session_reset(scan),
        )
    if _QUOTA.search(scan):
        return ClassifiedFailure(category="quota_exceeded", message=message)
    if _RATE_LIMIT.search(scan):
        return ClassifiedFailure(category="rate_limited", message=message)
    if _AUTH.search(scan):
        return ClassifiedFailure(category="authentication_failed", message=message)
    if _NETWORK.search(scan):
        return ClassifiedFailure(category="network_failure", message=message)
    if _TIMEOUT.search(scan):
        return ClassifiedFailure(category="timeout", message=message)
    if not parts:
        return ClassifiedFailure(category="unknown", message=message)
    return ClassifiedFailure(category="provider_unavailable", message=message)


_EXCEPTION_BY_CATEGORY = {
    "quota_exceeded": ProviderQuotaExceeded,
    "rate_limited": ProviderRateLimited,
    "authentication_failed": ProviderAuthFailed,
    "network_failure": ProviderNetworkFailure,
    "timeout": ProviderTimeout,
    "unexpected_error": ProviderUnexpectedError,
    "provider_unavailable": ProviderUnavailable,
    "unknown": ProviderUnavailable,
}


def failure_to_exception(failure: ClassifiedFailure) -> ProviderException:
    if failure.category == "session_limit_exceeded":
        return ProviderSessionLimit(failure.message, reset_time=failure.reset_time)
    exc_type = _EXCEPTION_BY_CATEGORY.get(failure.category, ProviderUnavailable)
    return exc_type(failure.message, category=failure.category)
