"""Operational alerts for provider quota events (RCA 2026-07-10, Phase 6).
Transition-based with dedupe — no alert spam from 100-request bursts."""
from datetime import datetime, timezone

import pytest

from engine.agent_firm.providers import alerts


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    alerts.reset_state()
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))
    yield sent
    alerts.reset_state()


_RESET_A = datetime(2026, 7, 10, 11, 20, tzinfo=timezone.utc)
_RESET_B = datetime(2026, 7, 10, 16, 20, tzinfo=timezone.utc)


def test_session_limit_alert_sent_once_per_reset_window(_clean):
    assert alerts.session_limit_alert("claude", _RESET_A) is True
    assert alerts.session_limit_alert("claude", _RESET_A) is False
    assert len(_clean) == 1
    assert "claude" in _clean[0].lower() or "Claude" in _clean[0]
    assert "session" in _clean[0].lower()


def test_new_reset_window_alerts_again(_clean):
    alerts.session_limit_alert("claude", _RESET_A)
    assert alerts.session_limit_alert("claude", _RESET_B) is True
    assert len(_clean) == 2


def test_restored_alert_and_count_reset(_clean):
    alerts.session_limit_alert("claude", _RESET_A)
    assert alerts.provider_restored_alert("claude") is True
    assert any("restored" in m.lower() for m in _clean)
    # After restore the same window may alert again (fresh exhaustion cycle).
    assert alerts.session_limit_alert("claude", _RESET_B) is True


def test_repeated_exhaustion_escalates(_clean, monkeypatch):
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_REPEAT_THRESHOLD", 3)
    r1 = datetime(2026, 7, 10, 6, 20, tzinfo=timezone.utc)
    r2 = datetime(2026, 7, 10, 11, 20, tzinfo=timezone.utc)
    r3 = datetime(2026, 7, 10, 16, 20, tzinfo=timezone.utc)
    alerts.session_limit_alert("claude", r1)
    alerts.session_limit_alert("claude", r2)
    alerts.session_limit_alert("claude", r3)
    assert any("repeated" in m.lower() for m in _clean)


def test_all_providers_unavailable_deduped(_clean):
    assert alerts.all_providers_unavailable_alert(["zai", "claude"]) is True
    assert alerts.all_providers_unavailable_alert(["zai", "claude"]) is False
    assert len(_clean) == 1
    assert "zai" in _clean[0] and "claude" in _clean[0]


def test_alerts_disabled_by_config(_clean, monkeypatch):
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_ALERTS_ENABLED", False)
    assert alerts.session_limit_alert("claude", _RESET_A) is False
    assert _clean == []


def test_telegram_failure_never_raises(monkeypatch):
    alerts.reset_state()
    def _boom(msg):
        raise RuntimeError("telegram down")
    monkeypatch.setattr(alerts, "send_telegram", _boom)
    assert alerts.session_limit_alert("claude", _RESET_A) is True  # logged anyway
