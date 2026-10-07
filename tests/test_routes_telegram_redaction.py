"""RC1 fix R-4: routes.telegram.send_telegram_reply must redact secrets the
same way utils.telegram.send_telegram does, reusing the same
utils.logging_config.redact_secrets() rule (not a second implementation)."""
from unittest.mock import patch

import pytest

import routes.telegram as rt
import utils.notify_policy as np


@pytest.fixture(autouse=True)
def _hermetic_gate(tmp_path, monkeypatch):
    """Hermetic vs the production box: logs/TELEGRAM_OFF really exists there
    (owner blackout 2026-10-05). Replies are tier-1 'bot.reply' through the
    gate — these tests exercise the send path with the switch off."""
    monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
    monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
    monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))


def test_send_telegram_reply_redacts_configured_secret(monkeypatch):
    monkeypatch.setattr(rt, "TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey")
    with patch("routes.telegram.requests.post") as mock_post:
        rt.send_telegram_reply("chat1", "error: supersecretzaikey leaked")
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "supersecretzaikey" not in sent_text
    assert "[REDACTED]" in sent_text


def test_send_telegram_reply_leaves_clean_text_unchanged(monkeypatch):
    monkeypatch.setattr(rt, "TELEGRAM_TOKEN", "tok123")
    monkeypatch.setenv("ZAI_API_KEY", "supersecretzaikey")
    with patch("routes.telegram.requests.post") as mock_post:
        rt.send_telegram_reply("chat1", "status: all good")
    assert mock_post.call_args.kwargs["json"]["text"] == "status: all good"


def test_send_telegram_reply_skips_placeholder_token(monkeypatch):
    monkeypatch.setattr(rt, "TELEGRAM_TOKEN", "ISI_TOKEN_DISINI")
    with patch("routes.telegram.requests.post") as mock_post:
        rt.send_telegram_reply("chat1", "should not send")
    mock_post.assert_not_called()
