"""Tests for utils/telegram.py — shared Telegram sender with rate-limiting and retry.

2026-10-06: send_telegram is now the muscle behind the curation policy gate
(utils.notify_policy.decide). Send-path tests pass a registered probe event;
the fixture isolates the gate's state files from the production box (where
logs/TELEGRAM_OFF really exists during the owner blackout).
"""
import time
from unittest.mock import MagicMock, patch

import pytest
import requests as req

import utils.notify_policy as np
import utils.telegram as tg

PROBE = "system.test_probe"  # registered tier-send event, tests only


@pytest.fixture(autouse=True)
def reset_state(tmp_path, monkeypatch):
    tg._last_sent = 0.0
    # Hermetic vs the production box: logs/TELEGRAM_OFF exists there (owner
    # blackout 2026-10-05), and gate state must never touch the real files.
    monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
    monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
    monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))
    yield
    tg._last_sent = 0.0


# ── send behaviour ──────────────────────────────────────────────────────────

def test_posts_to_correct_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        assert tg.send_telegram("hello", event=PROBE) is True
    mock_post.assert_called_once_with(
        "https://api.telegram.org/bottok123/sendMessage",
        json={"chat_id": "chat456", "text": "hello", "parse_mode": "HTML"},
        timeout=10,
    )


def test_skips_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello", event=PROBE)
    mock_post.assert_not_called()


def test_skips_when_chat_id_missing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello", event=PROBE)
    mock_post.assert_not_called()


def test_skips_placeholder_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "ISI_TOKEN_DISINI")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello", event=PROBE)
    mock_post.assert_not_called()


# ── curation gate ────────────────────────────────────────────────────────────

def test_unclassified_event_is_suppressed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        assert tg.send_telegram("hello") is False            # no event
        assert tg.send_telegram("hello", event="no.such") is False
    mock_post.assert_not_called()


def test_global_off_suppresses_even_registered_alerts(monkeypatch, tmp_path):
    """logs/TELEGRAM_OFF existing silences EVERYTHING — tier-1 alerts
    included; the gate is the only place the blackout is enforced."""
    (tmp_path / "TELEGRAM_OFF").touch()
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        assert tg.send_telegram("blackout", event="risk.circuit_breaker") is False
    mock_post.assert_not_called()


def test_global_off_removed_restores_sends(monkeypatch, tmp_path):
    """Deleting the file restores sends immediately — no restart, no cache."""
    off = tmp_path / "TELEGRAM_OFF"
    off.touch()
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("silenced", event=PROBE)
        off.unlink()
        assert tg.send_telegram("restored", event=PROBE) is True
    mock_post.assert_called_once()  # only the second call went out


def test_once_per_day_dedup_blocks_second_send(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        assert tg.send_telegram("first", event="system.scheduler_dead") is True
        assert tg.send_telegram("second", event="system.scheduler_dead") is False
    mock_post.assert_called_once()


# ── retry ───────────────────────────────────────────────────────────────────

def test_retries_on_network_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post", side_effect=[
        req.exceptions.ConnectionError("down"),
        req.exceptions.ConnectionError("down"),
        MagicMock(ok=True, status_code=200),
    ]) as mock_post, patch("utils.telegram.time.sleep"):
        assert tg.send_telegram("retry me", event=PROBE) is True
    assert mock_post.call_count == 3


def test_logs_error_after_all_retries_exhausted(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post", side_effect=req.exceptions.ConnectionError("down")), \
         patch("utils.telegram.time.sleep"), \
         patch("utils.telegram.logger.error") as mock_log:
        assert tg.send_telegram("fail forever", event=PROBE) is False
    mock_log.assert_called_once()


# ── rate limiting ────────────────────────────────────────────────────────────

def test_rate_limits_rapid_second_call(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    tg._last_sent = time.time()  # simulate a send that just happened
    with patch("utils.telegram.requests.post"), \
         patch("utils.telegram.time.sleep") as mock_sleep:
        tg.send_telegram("second message", event=PROBE)
    mock_sleep.assert_called_once()


def test_no_rate_limit_sleep_after_interval(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    tg._last_sent = time.time() - tg._MIN_INTERVAL - 0.1  # old enough
    with patch("utils.telegram.requests.post"), \
         patch("utils.telegram.time.sleep") as mock_sleep:
        tg.send_telegram("fine to send", event=PROBE)
    mock_sleep.assert_not_called()


# ── HTTP-level failures (Telegram rejects the request; requests does NOT raise) ─

def test_falls_back_to_plain_text_on_parse_error(monkeypatch):
    """400 with parse_mode=HTML ("can't parse entities") → resend once as plain text."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    bad = MagicMock(ok=False, status_code=400, text="Bad Request: can't parse entities")
    good = MagicMock(ok=True, status_code=200)
    with patch("utils.telegram.requests.post", side_effect=[bad, good]) as mock_post, \
         patch("utils.telegram.time.sleep"):
        assert tg.send_telegram("<b>broken", event=PROBE) is True
    assert mock_post.call_count == 2
    # The retry must have dropped HTML parse mode (payload dict is reused/mutated).
    assert mock_post.call_args_list[1].kwargs["json"]["parse_mode"] is None


def test_logs_error_when_plain_text_fallback_also_fails(monkeypatch):
    """400 → plain-text retry → still 400: log the loss, don't loop forever."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    bad = MagicMock(ok=False, status_code=400, text="Bad Request")
    with patch("utils.telegram.requests.post", side_effect=[bad, bad]) as mock_post, \
         patch("utils.telegram.time.sleep"), \
         patch("utils.telegram.logger.error") as mock_log:
        assert tg.send_telegram("<b>broken", event=PROBE) is False
    assert mock_post.call_count == 2   # no third attempt after fallback fails
    mock_log.assert_called_once()


# ── secret redaction (RC1 fix R-4) ──────────────────────────────────────────

def test_redacts_configured_secret_before_posting(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("job failed: supersecretzaikey leaked in exception text", event=PROBE)
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "supersecretzaikey" not in sent_text
    assert "[REDACTED]" in sent_text


def test_does_not_redact_short_values(monkeypatch):
    """Matches redact_secrets()'s own >=8 char floor -- short/unset secret vars
    must not accidentally mask ordinary short substrings in alert text."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    monkeypatch.setenv("AUTH_TOKEN_VIEWER", "short")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("short circuit detected", event=PROBE)
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert sent_text == "short circuit detected"


def test_retries_on_http_429_then_succeeds(monkeypatch):
    """Non-400 HTTP errors (e.g. 429 rate limit) are logged and retried with backoff."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    limited = MagicMock(ok=False, status_code=429, text="Too Many Requests")
    good = MagicMock(ok=True, status_code=200)
    with patch("utils.telegram.requests.post", side_effect=[limited, good]) as mock_post, \
         patch("utils.telegram.time.sleep") as mock_sleep, \
         patch("utils.telegram.logger.error") as mock_log:
        assert tg.send_telegram("rate limited once", event=PROBE) is True
    assert mock_post.call_count == 2
    mock_log.assert_called_once()      # the 429 was surfaced, not swallowed
    assert mock_sleep.called           # backoff before the retry
