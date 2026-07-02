"""Tests for utils/telegram.py — shared Telegram sender with rate-limiting and retry."""
import time
from unittest.mock import MagicMock, patch

import pytest
import requests as req

import utils.telegram as tg


@pytest.fixture(autouse=True)
def reset_state():
    tg._last_sent = 0.0
    yield
    tg._last_sent = 0.0


# ── send behaviour ──────────────────────────────────────────────────────────

def test_posts_to_correct_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello")
    mock_post.assert_called_once_with(
        "https://api.telegram.org/bottok123/sendMessage",
        json={"chat_id": "chat456", "text": "hello", "parse_mode": "HTML"},
        timeout=10,
    )


def test_skips_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello")
    mock_post.assert_not_called()


def test_skips_when_chat_id_missing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello")
    mock_post.assert_not_called()


def test_skips_placeholder_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "ISI_TOKEN_DISINI")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post") as mock_post:
        tg.send_telegram("hello")
    mock_post.assert_not_called()


# ── retry ───────────────────────────────────────────────────────────────────

def test_retries_on_network_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post", side_effect=[
        req.exceptions.ConnectionError("down"),
        req.exceptions.ConnectionError("down"),
        MagicMock(status_code=200),
    ]) as mock_post, patch("utils.telegram.time.sleep"):
        tg.send_telegram("retry me")
    assert mock_post.call_count == 3


def test_logs_error_after_all_retries_exhausted(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("utils.telegram.requests.post", side_effect=req.exceptions.ConnectionError("down")), \
         patch("utils.telegram.time.sleep"), \
         patch("utils.telegram.logger.error") as mock_log:
        tg.send_telegram("fail forever")
    mock_log.assert_called_once()


# ── rate limiting ────────────────────────────────────────────────────────────

def test_rate_limits_rapid_second_call(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    tg._last_sent = time.time()  # simulate a send that just happened
    with patch("utils.telegram.requests.post"), \
         patch("utils.telegram.time.sleep") as mock_sleep:
        tg.send_telegram("second message")
    mock_sleep.assert_called_once()


def test_no_rate_limit_sleep_after_interval(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    tg._last_sent = time.time() - tg._MIN_INTERVAL - 0.1  # old enough
    with patch("utils.telegram.requests.post"), \
         patch("utils.telegram.time.sleep") as mock_sleep:
        tg.send_telegram("fine to send")
    mock_sleep.assert_not_called()


# ── HTTP-level failures (Telegram rejects the request; requests does NOT raise) ─

def test_falls_back_to_plain_text_on_parse_error(monkeypatch):
    """400 with parse_mode=HTML (\"can't parse entities\") → resend once as plain text."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    bad = MagicMock(ok=False, status_code=400, text="Bad Request: can't parse entities")
    good = MagicMock(ok=True, status_code=200)
    with patch("utils.telegram.requests.post", side_effect=[bad, good]) as mock_post, \
         patch("utils.telegram.time.sleep"):
        tg.send_telegram("<b>broken")
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
        tg.send_telegram("<b>broken")
    assert mock_post.call_count == 2   # no third attempt after fallback fails
    mock_log.assert_called_once()


def test_retries_on_http_429_then_succeeds(monkeypatch):
    """Non-400 HTTP errors (e.g. 429 rate limit) are logged and retried with backoff."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    limited = MagicMock(ok=False, status_code=429, text="Too Many Requests")
    good = MagicMock(ok=True, status_code=200)
    with patch("utils.telegram.requests.post", side_effect=[limited, good]) as mock_post, \
         patch("utils.telegram.time.sleep") as mock_sleep, \
         patch("utils.telegram.logger.error") as mock_log:
        tg.send_telegram("rate limited once")
    assert mock_post.call_count == 2
    mock_log.assert_called_once()      # the 429 was surfaced, not swallowed
    assert mock_sleep.called           # backoff before the retry
