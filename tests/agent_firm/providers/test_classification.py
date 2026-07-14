"""Provider failure classification (RCA 2026-07-10: Claude CLI session-limit
rejections exited 1 with the diagnosis on STDOUT, which the provider
discarded; 'session limit' also matched no quota pattern, so 137 failures
collapsed into ProviderUnavailable("claude CLI exited 1")."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from engine.agent_firm.providers.classification import (
    ClassifiedFailure, classify_cli_failure, failure_to_exception,
    parse_session_reset,
)
from engine.agent_firm.providers.errors import (
    ProviderAuthFailed, ProviderNetworkFailure, ProviderQuotaExceeded,
    ProviderRateLimited, ProviderSessionLimit, ProviderTimeout,
    ProviderUnavailable, ProviderUnexpectedError,
)

_JKT = ZoneInfo("Asia/Jakarta")
_LIMIT_MSG = "You've hit your session limit · resets 6:20pm (Asia/Jakarta)"
# RCA 2026-07-13: Claude's subscription wording changed; this phrasing now
# appears in production logs and previously matched no quota/session pattern.
_OUT_OF_EXTRA_MSG = "You're out of extra usage · resets 12am (Asia/Jakarta)"


# --- parse_session_reset -----------------------------------------------------

def test_parse_reset_pm_time_same_day():
    now = datetime(2026, 7, 10, 14, 35, tzinfo=_JKT)
    reset = parse_session_reset(_LIMIT_MSG, now=now)
    assert reset == datetime(2026, 7, 10, 18, 20, tzinfo=_JKT)


def test_parse_reset_rolls_to_next_day_when_time_already_passed():
    now = datetime(2026, 7, 10, 19, 0, tzinfo=_JKT)
    reset = parse_session_reset(_LIMIT_MSG, now=now)
    assert reset == datetime(2026, 7, 11, 18, 20, tzinfo=_JKT)


def test_parse_reset_am_time_and_no_minutes():
    now = datetime(2026, 7, 10, 3, 0, tzinfo=_JKT)
    reset = parse_session_reset("resets 11am (Asia/Jakarta)", now=now)
    assert reset == datetime(2026, 7, 10, 11, 0, tzinfo=_JKT)


def test_parse_reset_12am_and_12pm_boundaries():
    now = datetime(2026, 7, 10, 1, 0, tzinfo=_JKT)
    assert parse_session_reset("resets 12pm (Asia/Jakarta)", now=now).hour == 12
    reset_midnight = parse_session_reset("resets 12am (Asia/Jakarta)", now=now)
    assert reset_midnight.hour == 0 and reset_midnight.day == 11


def test_parse_reset_unknown_timezone_falls_back_to_jakarta():
    now = datetime(2026, 7, 10, 3, 0, tzinfo=timezone.utc)
    reset = parse_session_reset("resets 6:20pm (Middle/Nowhere)", now=now)
    assert reset is not None
    assert reset.astimezone(_JKT).hour == 18


def test_parse_reset_returns_none_when_absent():
    assert parse_session_reset("some other error") is None
    assert parse_session_reset("") is None


# --- classify_cli_failure ----------------------------------------------------

def test_session_limit_on_stdout_with_empty_stderr():
    """The exact production failure shape from the 2026-07-10 incident."""
    f = classify_cli_failure(1, stdout=_LIMIT_MSG, stderr="")
    assert f.category == "session_limit_exceeded"
    assert f.reset_time is not None
    assert "session limit" in f.message


def test_session_limit_detected_on_stderr_too():
    f = classify_cli_failure(1, stdout="", stderr=_LIMIT_MSG)
    assert f.category == "session_limit_exceeded"


def test_out_of_extra_usage_is_session_limit_with_reset():
    """RCA 2026-07-13: the production message "You're out of extra usage ·
    resets 12am" matched no pattern, so 111+ session-limit rejections
    collapsed into provider_unavailable and Claude was retried every 30s
    instead of being held to midnight."""
    f = classify_cli_failure(1, stdout=_OUT_OF_EXTRA_MSG, stderr="")
    assert f.category == "session_limit_exceeded"
    assert f.reset_time is not None
    # midnight Jakarta → hour 0 of the next day
    assert f.reset_time.astimezone(_JKT).hour == 0


def test_out_of_extra_usage_short_variant_also_session_limit():
    f = classify_cli_failure(1, stdout="You're out of extra", stderr="")
    assert f.category == "session_limit_exceeded"


def test_quota_pattern_still_classified():
    f = classify_cli_failure(1, stdout="", stderr="Error: usage limit reached for this account")
    assert f.category == "quota_exceeded"


def test_rate_limit_pattern():
    f = classify_cli_failure(1, stdout="", stderr="429 too many requests")
    assert f.category == "rate_limited"


def test_authentication_failure():
    f = classify_cli_failure(1, stdout="", stderr="Invalid API key. Please run /login")
    assert f.category == "authentication_failed"


def test_oauth_expiry_is_authentication_failure():
    f = classify_cli_failure(1, stdout="OAuth token has expired", stderr="")
    assert f.category == "authentication_failed"


def test_network_failure():
    f = classify_cli_failure(1, stdout="", stderr="fetch failed: getaddrinfo ENOTFOUND api.anthropic.com")
    assert f.category == "network_failure"


def test_timeout_text_maps_to_timeout():
    f = classify_cli_failure(1, stdout="", stderr="request timed out after 60000ms")
    assert f.category == "timeout"


def test_unmatched_text_is_provider_unavailable():
    f = classify_cli_failure(1, stdout="", stderr="some other CLI error")
    assert f.category == "provider_unavailable"
    assert "some other CLI error" in f.message


def test_no_output_at_all_is_unknown():
    f = classify_cli_failure(1, stdout="", stderr="")
    assert f.category == "unknown"
    assert "exited 1" in f.message


def test_signal_kill_is_unexpected_error():
    f = classify_cli_failure(-9, stdout="", stderr="")
    assert f.category == "unexpected_error"


def test_stdout_json_result_payload_is_parsed_for_message():
    """CLI --output-format json may wrap the diagnosis in a result JSON."""
    payload = '{"type":"result","subtype":"error_during_execution","is_error":true,"result":"%s"}' % _LIMIT_MSG
    f = classify_cli_failure(1, stdout=payload, stderr="")
    assert f.category == "session_limit_exceeded"
    assert f.reset_time is not None


def test_stderr_takes_priority_in_message_but_stdout_still_scanned():
    f = classify_cli_failure(1, stdout=_LIMIT_MSG, stderr="wrapper: child failed")
    assert f.category == "session_limit_exceeded"
    assert "wrapper: child failed" in f.message


def test_message_is_truncated():
    f = classify_cli_failure(1, stdout="", stderr="x" * 5000)
    assert len(f.message) <= 600


# --- failure_to_exception ----------------------------------------------------

def test_exception_mapping_and_categories():
    cases = {
        "session_limit_exceeded": ProviderSessionLimit,
        "quota_exceeded": ProviderQuotaExceeded,
        "rate_limited": ProviderRateLimited,
        "authentication_failed": ProviderAuthFailed,
        "network_failure": ProviderNetworkFailure,
        "timeout": ProviderTimeout,
        "unexpected_error": ProviderUnexpectedError,
        "provider_unavailable": ProviderUnavailable,
        "unknown": ProviderUnavailable,
    }
    for category, exc_type in cases.items():
        err = failure_to_exception(
            ClassifiedFailure(category=category, message="m", reset_time=None)
        )
        assert isinstance(err, exc_type), category
        assert err.category == category


def test_session_limit_exception_carries_reset_time():
    f = classify_cli_failure(1, stdout=_LIMIT_MSG, stderr="")
    err = failure_to_exception(f)
    assert isinstance(err, ProviderSessionLimit)
    assert err.reset_time == f.reset_time
    # Backward compatibility: session limit is a kind of quota exhaustion.
    assert isinstance(err, ProviderQuotaExceeded)


def test_new_exceptions_remain_router_compatible():
    from engine.agent_firm.providers.errors import ProviderException
    for exc in (ProviderSessionLimit("x"), ProviderAuthFailed("x"),
                ProviderNetworkFailure("x"), ProviderUnexpectedError("x")):
        assert isinstance(exc, ProviderException)
