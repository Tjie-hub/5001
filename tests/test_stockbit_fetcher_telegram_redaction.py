"""RC1-C2 regression tests: stockbit_fetcher.send_telegram now redacts
secrets via the shared utils.logging_config.redact_secrets() — same rule
already applied to utils.telegram.send_telegram / routes.telegram.send_telegram_reply
(RC1 fix R-4). No second redaction implementation; existing formatting/
retry/error-handling behaviour is unchanged, only the outbound text is
passed through redact_secrets() first.
"""
from unittest.mock import patch

import pytest

import stockbit_fetcher as sf
import utils.notify_policy as np


@pytest.fixture(autouse=True)
def _hermetic_gate(tmp_path, monkeypatch):
    """Hermetic vs the production box: logs/TELEGRAM_OFF really exists there
    (owner blackout 2026-10-05) and gate state must not touch real files.
    These tests exercise the send path itself, with the switch off."""
    monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
    monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
    monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))


def _sent_text(monkeypatch, msg, secret_env=None):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    for k, v in (secret_env or {}).items():
        monkeypatch.setenv(k, v)
    with patch("stockbit_fetcher.requests.post") as mock_post:
        sf.send_telegram(msg, event="system.test_probe")
    if not mock_post.call_args:
        return None
    return mock_post.call_args.kwargs["json"]["text"]


def test_redacts_a_single_configured_secret(monkeypatch):
    text = _sent_text(monkeypatch, "token leaked: supersecretzaikey",
                      {"ZAI_API_KEY": "supersecretzaikey"})
    assert "supersecretzaikey" not in text
    assert "[REDACTED]" in text


def test_normal_message_is_unchanged(monkeypatch):
    text = _sent_text(monkeypatch, "OHLCV fetch complete: 80 tickers",
                      {"ZAI_API_KEY": "supersecretzaikey"})
    assert text == "OHLCV fetch complete: 80 tickers"


def test_html_formatting_and_newlines_preserved(monkeypatch):
    msg = "<b>Fetch Error</b>\nticker: BBCA\nkey: supersecretzaikey"
    text = _sent_text(monkeypatch, msg, {"ZAI_API_KEY": "supersecretzaikey"})
    assert "<b>Fetch Error</b>" in text
    assert "\nticker: BBCA\n" in text
    assert "supersecretzaikey" not in text


def test_multiple_distinct_secrets_all_redacted(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "zaikeyvalueone")
    monkeypatch.setenv("STOCKBIT_PASS", "stockbitpassone")
    text = _sent_text(monkeypatch, "zaikeyvalueone and stockbitpassone both leaked")
    assert "zaikeyvalueone" not in text and "stockbitpassone" not in text
    assert text.count("[REDACTED]") == 2


def test_already_redacted_message_is_left_alone(monkeypatch):
    text = _sent_text(monkeypatch, "value: [REDACTED] already masked",
                      {"ZAI_API_KEY": "supersecretzaikey"})
    assert text == "value: [REDACTED] already masked"


def test_empty_message_does_not_crash(monkeypatch):
    text = _sent_text(monkeypatch, "", {"ZAI_API_KEY": "supersecretzaikey"})
    assert text == ""


def test_skips_send_when_telegram_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("stockbit_fetcher.requests.post") as mock_post:
        sf.send_telegram("should not send")
    mock_post.assert_not_called()


def test_existing_network_error_handling_preserved(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    with patch("stockbit_fetcher.requests.post", side_effect=Exception("network down")):
        sf.send_telegram("test message")   # must not raise
