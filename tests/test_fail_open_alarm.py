"""Tests for engine.fail_open_alarm — surfacing silent fail-open events."""
import logging

import engine.fail_open_alarm as fa


def test_format_is_pure_and_includes_source_detail_count():
    msg = fa.format_fail_open_alarm("agent_firm_enforce", "LLM outage", 3)
    assert "agent_firm_enforce" in msg
    assert "LLM outage" in msg
    assert "3" in msg


def test_alarm_logs_warning(caplog):
    with caplog.at_level(logging.WARNING):
        fa.fail_open_alarm("flow_batch", "flow fetch failed", count=12, notify=False)
    assert any("flow_batch" in r.message and r.levelno == logging.WARNING
               for r in caplog.records)


def test_alarm_notifies_via_telegram_best_effort(monkeypatch):
    sent = []
    monkeypatch.setattr(fa, "send_telegram", lambda m: sent.append(m))
    fa.fail_open_alarm("agent_firm_enforce", "3 degraded", count=3, notify=True)
    assert len(sent) == 1
    assert "agent_firm_enforce" in sent[0]


def test_alarm_swallows_notifier_errors(monkeypatch):
    def _boom(_m):
        raise RuntimeError("telegram down")
    monkeypatch.setattr(fa, "send_telegram", _boom)
    # Must not raise — notification is best-effort.
    fa.fail_open_alarm("x", "y", count=1, notify=True)
