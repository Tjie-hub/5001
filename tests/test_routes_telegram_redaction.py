"""RC1 fix R-4: routes.telegram.send_telegram_reply must redact secrets the
same way utils.telegram.send_telegram does, reusing the same
utils.logging_config.redact_secrets() rule (not a second implementation)."""
from unittest.mock import patch

import routes.telegram as rt


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
