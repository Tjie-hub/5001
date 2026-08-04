"""Regression tests for the Stockbit token-refresh hardening (incident 2026-07-27).

Root cause: `should_skip_refresh()` used a flat 6h-remaining threshold that did
not account for the gap to the day's last consumer (18:30/20:15 WIB crons). A
token issued off-schedule (2026-07-26 17:31) still had 8.9h remaining at the
next 08:40 check -- past the old 6h bar -- so the proactive refresh was
skipped, and the token expired at 17:31, one hour before the 18:30
`stockbit_flow` cron needed it. See docs/audit/STOCKBIT_TOKEN_REFRESH_HARDENING.md.

These tests exercise the pure logic in auto_token.py with monkeypatched I/O
(no real Playwright browser, no real network, no real files) -- see
tests/test_stockbit_fetcher_ensure_valid_token.py for the companion fix to the
manual-token fallback bypass (the second, compounding root cause).
"""
import base64
import json
import os
import stat
import time
from unittest.mock import patch

import pytest

import auto_token as at

# Captured before the module-level `no_telegram` autouse fixture (below) can
# monkeypatch at.send_telegram to a no-op -- TestSendTelegramRedaction calls
# this directly so it exercises the REAL implementation, not the test-suite's
# safety-net mock.
_real_send_telegram = at.send_telegram


def _make_jwt(iat_offset_h=0.0, exp_offset_h=24.0):
    """Build a syntactically-valid JWT with iat/exp claims offset from now."""
    now = time.time()
    payload = {
        "iat": int(now + iat_offset_h * 3600),
        "exp": int(now + exp_offset_h * 3600),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.fakesignature"


@pytest.fixture
def token_file(tmp_path, monkeypatch):
    f = tmp_path / ".stockbit_token"
    monkeypatch.setattr(at, "TOKEN_FILE", f)
    return f


@pytest.fixture
def lock_file(tmp_path, monkeypatch):
    f = tmp_path / ".stockbit_token.lock"
    monkeypatch.setattr(at, "LOCK_FILE", f)
    return f


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    monkeypatch.setattr(at, "send_telegram", lambda *a, **k: None)


# ── should_skip_refresh: margin threshold (Requirement 2 + 3) ──

def test_skips_when_remaining_exceeds_margin(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=20))  # 20h remaining
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is True


def test_does_not_skip_within_margin_the_2026_07_27_regression(token_file, monkeypatch):
    """Pins the exact incident: 8.9h remaining must NOT be treated as fresh."""
    token_file.write_text(_make_jwt(exp_offset_h=8.9))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=at.REFRESH_MARGIN_HOURS) is False


def test_does_not_skip_when_already_expired(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=-1))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_on_implausible_remaining_clock_skew(token_file, monkeypatch):
    """A token claiming >48h remaining (impossible for a 24h-TTL token) is
    treated as a clock-skew/corruption signal, not as 'very fresh'."""
    token_file.write_text(_make_jwt(exp_offset_h=100))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_when_verify_fails_even_if_time_remains(token_file, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=20))
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    assert at.should_skip_refresh(margin_hours=14) is False


def test_does_not_skip_when_no_token_file(token_file):
    assert at.should_skip_refresh(margin_hours=14) is False


# ── atomic token write (Requirement 3) ──

def test_write_token_atomic_writes_content_and_mode(token_file):
    at._write_token_atomic("abc.def.ghi", token_file=token_file)
    assert token_file.read_text() == "abc.def.ghi"
    mode = stat.S_IMODE(os.stat(token_file).st_mode)
    assert mode == 0o600


def test_write_token_atomic_leaves_no_temp_file_on_success(token_file):
    at._write_token_atomic("abc.def.ghi", token_file=token_file)
    leftovers = list(token_file.parent.glob(".stockbit_token.*.tmp"))
    assert leftovers == []


def test_write_token_atomic_never_leaves_partial_file_on_failure(token_file, monkeypatch):
    token_file.write_text("old-valid-token")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "fdopen", boom)
    with pytest.raises(OSError):
        at._write_token_atomic("new-token", token_file=token_file)

    # original file untouched -- a failed write must never corrupt the
    # existing credential
    assert token_file.read_text() == "old-valid-token"
    leftovers = list(token_file.parent.glob(".stockbit_token.*.tmp"))
    assert leftovers == []


# ── retry with backoff (Requirement 3: transient failures) ──

def test_retry_with_backoff_succeeds_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("transient")
        return "token-value"

    slept = []
    result = at._retry_with_backoff(
        flaky, max_retries=3, backoff_base=1, label="test", sleep_fn=slept.append
    )
    assert result == "token-value"
    assert len(calls) == 3
    assert slept == [1, 2]  # exponential: 1*2^0, 1*2^1


def test_retry_with_backoff_returns_none_after_exhausting_all_attempts():
    def always_fails():
        raise ConnectionError("permanent-ish")

    result = at._retry_with_backoff(
        always_fails, max_retries=3, backoff_base=0, label="test", sleep_fn=lambda s: None
    )
    assert result is None


def test_retry_with_backoff_treats_falsy_result_as_failure_and_retries():
    calls = []

    def returns_none_then_value():
        calls.append(1)
        return None if len(calls) < 2 else "ok"

    result = at._retry_with_backoff(
        returns_none_then_value, max_retries=3, backoff_base=0, label="test", sleep_fn=lambda s: None
    )
    assert result == "ok"
    assert len(calls) == 2


# ── concurrency lock (Requirement 3 + 5: prevent concurrent refreshes) ──

def test_refresh_lock_blocks_a_second_concurrent_acquire(lock_file):
    with at._refresh_lock(lock_path=lock_file) as first_acquired:
        assert first_acquired is True
        with at._refresh_lock(lock_path=lock_file) as second_acquired:
            assert second_acquired is False


def test_refresh_lock_is_released_after_context_exits(lock_file):
    with at._refresh_lock(lock_path=lock_file) as acquired:
        assert acquired is True
    with at._refresh_lock(lock_path=lock_file) as acquired_again:
        assert acquired_again is True


# ── preserve existing token on refresh failure (Requirement 4) ──

def test_old_token_still_safe_true_when_valid_and_recent(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-5))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is True


def test_old_token_still_safe_false_when_too_old(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-21))
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


def test_old_token_still_safe_false_when_verify_fails(token_file, monkeypatch):
    token_file.write_text(_make_jwt(iat_offset_h=-1))
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


def test_old_token_still_safe_false_when_no_file(token_file):
    assert at._old_token_still_safe(max_age_hours=20, token_file=token_file) is False


# ── end-to-end main() behavior (mocked I/O) ──

@pytest.fixture
def no_state_dir(monkeypatch, tmp_path):
    # keep check_state_size/cleanup_zombies inert -- not under test here
    monkeypatch.setattr(at, "check_state_size", lambda: None)
    monkeypatch.setattr(at, "cleanup_zombies", lambda: None)


def test_normal_refresh_writes_fresh_token(token_file, lock_file, no_state_dir, monkeypatch):
    fresh = _make_jwt(iat_offset_h=0, exp_offset_h=24)
    monkeypatch.setattr(at, "auto_refresh", lambda: fresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    monkeypatch.setattr(at, "credential_login", lambda: (_ for _ in ()).throw(AssertionError("should not be called")))

    at.main()

    assert token_file.read_text() == fresh


def test_expired_token_triggers_refresh(token_file, lock_file, no_state_dir, monkeypatch):
    token_file.write_text(_make_jwt(exp_offset_h=-2))  # already expired
    fresh = _make_jwt(exp_offset_h=24)
    monkeypatch.setattr(at, "auto_refresh", lambda: fresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    at.main()

    assert token_file.read_text() == fresh


def test_transient_auto_refresh_failure_recovers_via_retry(token_file, lock_file, no_state_dir, monkeypatch):
    fresh = _make_jwt(exp_offset_h=24)
    attempts = []

    def flaky_refresh():
        attempts.append(1)
        if len(attempts) < 2:
            raise TimeoutError("network blip")
        return fresh

    monkeypatch.setattr(at, "auto_refresh", flaky_refresh)
    monkeypatch.setattr(at, "verify_token", lambda t: True)
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    at.main()

    assert len(attempts) == 2
    assert token_file.read_text() == fresh


def test_total_refresh_failure_preserves_old_token_and_alerts(token_file, lock_file, no_state_dir, monkeypatch):
    old_valid = _make_jwt(iat_offset_h=-2, exp_offset_h=22)
    token_file.write_text(old_valid)

    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)
    monkeypatch.setattr(at, "verify_token", lambda t: t == old_valid)  # only the old token verifies
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    at.main()  # should NOT raise / NOT sys.exit since old token is still safe

    # fail-safe: existing valid credential must not be touched/corrupted
    assert token_file.read_text() == old_valid


def test_total_refresh_failure_with_no_safe_fallback_exits_nonzero_and_alerts(
    token_file, lock_file, no_state_dir, monkeypatch
):
    stale = _make_jwt(exp_offset_h=-5)
    token_file.write_text(stale)

    monkeypatch.setattr(at, "auto_refresh", lambda: None)
    monkeypatch.setattr(at, "credential_login", lambda: None)
    monkeypatch.setattr(at, "verify_token", lambda t: False)
    monkeypatch.setattr(at, "RETRY_BACKOFF_BASE_S", 0)

    alerts = []
    monkeypatch.setattr(at, "send_telegram", lambda msg: alerts.append(msg))

    with pytest.raises(SystemExit) as exc:
        at.main()

    assert exc.value.code == 1
    assert any("GAGAL" in m for m in alerts)
    # the stale token on disk must not be silently replaced with garbage
    assert token_file.read_text() == stale


def test_idempotent_repeated_execution_does_not_double_refresh(token_file, lock_file, no_state_dir, monkeypatch):
    """Scheduler-restart scenario: main() invoked twice back to back must not
    re-run the (expensive, rate-limited) browser refresh the second time."""
    fresh = _make_jwt(exp_offset_h=24)
    calls = []

    def refresh_once():
        calls.append(1)
        return fresh

    monkeypatch.setattr(at, "auto_refresh", refresh_once)
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    at.main()
    at.main()

    assert len(calls) == 1, "second invocation should have skipped via should_skip_refresh"
    assert token_file.read_text() == fresh


def test_concurrent_invocation_finds_lock_held_and_exits_cleanly(token_file, lock_file, no_state_dir, monkeypatch):
    """Simulates a second cron/manual invocation firing while a refresh is
    already in flight -- must not double-launch a browser, must not error."""
    calls = []
    monkeypatch.setattr(at, "auto_refresh", lambda: calls.append(1) or _make_jwt())
    monkeypatch.setattr(at, "verify_token", lambda t: True)

    with at._refresh_lock(lock_path=lock_file):
        # a concurrent main() call should observe the lock is held
        at.main()  # must return quietly, not raise, not call auto_refresh

    assert calls == []


class TestSendTelegramRedaction:
    """RC1-C2 regression tests: auto_token.send_telegram now redacts secrets
    via the shared utils.logging_config.redact_secrets() — same rule already
    applied to utils.telegram.send_telegram / routes.telegram.send_telegram_reply
    (RC1 fix R-4). Calls _real_send_telegram directly to bypass the module's
    own `no_telegram` autouse mock (see top of file) and exercise the actual
    implementation.
    """

    def _sent_text(self, monkeypatch, msg, secret_env=None):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", "tok123")
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", "chat456")
        for k, v in (secret_env or {}).items():
            monkeypatch.setenv(k, v)
        with patch("auto_token.requests.post") as mock_post:
            _real_send_telegram(msg)
        if not mock_post.call_args:
            return None
        return mock_post.call_args.kwargs["json"]["text"]

    def test_redacts_a_single_configured_secret(self, monkeypatch):
        text = self._sent_text(monkeypatch, "token leaked: supersecretzaikey",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert "supersecretzaikey" not in text
        assert "[REDACTED]" in text

    def test_normal_message_is_unchanged(self, monkeypatch):
        text = self._sent_text(monkeypatch, "Token refreshed OK, 20h remaining",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == "Token refreshed OK, 20h remaining"

    def test_html_formatting_and_newlines_preserved(self, monkeypatch):
        msg = "<b>Token Refresh FAILED</b>\nreason: supersecretzaikey"
        text = self._sent_text(monkeypatch, msg, {"ZAI_API_KEY": "supersecretzaikey"})
        assert "<b>Token Refresh FAILED</b>" in text
        assert "\nreason:" in text
        assert "supersecretzaikey" not in text

    def test_multiple_distinct_secrets_all_redacted(self, monkeypatch):
        text = self._sent_text(
            monkeypatch, "zaikeyvalueone and stockbitpassone both leaked",
            {"ZAI_API_KEY": "zaikeyvalueone", "STOCKBIT_PASS": "stockbitpassone"})
        assert "zaikeyvalueone" not in text and "stockbitpassone" not in text
        assert text.count("[REDACTED]") == 2

    def test_already_redacted_message_is_left_alone(self, monkeypatch):
        text = self._sent_text(monkeypatch, "value: [REDACTED] already masked",
                               {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == "value: [REDACTED] already masked"

    def test_empty_message_does_not_crash(self, monkeypatch):
        text = self._sent_text(monkeypatch, "", {"ZAI_API_KEY": "supersecretzaikey"})
        assert text == ""

    def test_skips_send_when_telegram_not_configured(self, monkeypatch):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", None)
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", None)
        with patch("auto_token.requests.post") as mock_post:
            _real_send_telegram("should not send")
        mock_post.assert_not_called()

    def test_existing_network_error_handling_preserved(self, monkeypatch):
        monkeypatch.setattr(at, "TELEGRAM_TOKEN", "tok123")
        monkeypatch.setattr(at, "TELEGRAM_CHAT_ID", "chat456")
        with patch("auto_token.requests.post", side_effect=Exception("network down")):
            _real_send_telegram("test message")   # must not raise
