"""Tests for utils/notify_policy.py — the 2026-10-06 curation brief's gate:
tier classification, persistent dedup (once_per_day / on_change / cooldown),
the evening digest buffer + flush, and the global TELEGRAM_OFF blackout.
"""
import json
import os

import pytest

import utils.notify_policy as np
import utils.telegram as tg


@pytest.fixture(autouse=True)
def hermetic(tmp_path, monkeypatch):
    """Point state, digest buffer, and the OFF file at tmp_path, and make the
    telegram sender observable without a network."""
    monkeypatch.setattr(np, "STATE_FILE", str(tmp_path / "notify_state.json"))
    monkeypatch.setattr(np, "DIGEST_DIR", str(tmp_path / "digest_buffer"))
    monkeypatch.setattr(np, "OFF_FILE", str(tmp_path / "TELEGRAM_OFF"))
    sent = []

    def fake_send(msg, event=None, **kw):
        # Mimic the real muscle's contract: the sender runs the gate itself
        # (OFF, classification, dedup) and returns False when suppressed.
        action, _ = np.decide(event, msg=msg)
        if action != "send":
            return False
        sent.append((event, msg))
        return True

    monkeypatch.setattr(tg, "send_telegram", fake_send)
    yield sent


# ── registry integrity ──────────────────────────────────────────────────────

def test_registry_ids_unique_and_tiers_valid():
    tiers = {np.TIER_SEND, np.TIER_DIGEST, np.TIER_LOG}
    for event, (tier, rule) in np.EVENTS.items():
        assert tier in tiers, event
        assert isinstance(rule, tuple) and rule, event


def test_tier1_events_are_send_tier():
    for event in ("risk.circuit_breaker", "data.token_dead_pre_eod",
                  "system.scheduler_dead", "llm.provider_quota",
                  "data.eod_degraded", "trade.paper_closed"):
        assert np.EVENTS[event][0] == np.TIER_SEND, event


def test_ihsg_event_is_digest_on_change():
    assert np.EVENTS["market.ihsg_technical"] == (np.TIER_DIGEST, np.RULE_CHANGE)


# ── global OFF ───────────────────────────────────────────────────────────────

def test_off_blocks_everything_including_alerts(hermetic, tmp_path):
    (tmp_path / "TELEGRAM_OFF").touch()
    for event in ("risk.circuit_breaker", "system.fail_open", "bot.reply"):
        action, reason = np.decide(event, msg="x")
        assert action == "suppress" and reason == "global OFF"


def test_no_off_file_allows_send(hermetic, tmp_path):
    assert not os.path.exists(tmp_path / "TELEGRAM_OFF")
    action, _ = np.decide("risk.circuit_breaker", msg="x")
    assert action == "send"


# ── classification ───────────────────────────────────────────────────────────

def test_unclassified_event_fails_closed_to_suppress():
    action, reason = np.decide(None, msg="x")
    assert action == "suppress" and reason == "unclassified event"
    action, reason = np.decide("no.such.event", msg="x")
    assert action == "suppress" and reason == "unclassified event"


# ── once_per_day ─────────────────────────────────────────────────────────────

def test_once_per_day_blocks_second_send_same_day(hermetic):
    assert np.decide("system.scheduler_dead", msg="a")[0] == "send"
    action, reason = np.decide("system.scheduler_dead", msg="b")
    assert action == "suppress" and "once_per_day" in reason


def test_once_per_day_subject_partitions(hermetic):
    assert np.decide("llm.provider_quota", subject="claude", msg="a")[0] == "send"
    assert np.decide("llm.provider_quota", subject="claude", msg="b")[0] == "suppress"
    assert np.decide("llm.provider_quota", subject="zai", msg="c")[0] == "send"


def test_once_per_day_persists_across_gate_reload(hermetic, tmp_path):
    np.decide("data.eod_degraded", msg="a")
    # A fresh "process": state comes from the same STATE_FILE on disk.
    action, _ = np.decide("data.eod_degraded", msg="b")
    assert action == "suppress"
    assert os.path.exists(tmp_path / "notify_state.json")


def test_state_write_is_atomic_no_tmp_left_behind(hermetic, tmp_path):
    np.decide("data.eod_degraded", msg="a")
    assert not os.path.exists(str(tmp_path / "notify_state.json.tmp"))


# ── on_change (the IHSG refire fix) ─────────────────────────────────────────

def test_on_change_fires_once_then_suppresses_identical_state(hermetic):
    first = np.decide("market.ihsg_technical", state="DOWNTREND", msg="alert")
    assert first[0] == "digest"  # tier-2 → buffered, not sent
    for _ in range(10):  # ten identical scans: all suppressed
        action, reason = np.decide("market.ihsg_technical", state="DOWNTREND", msg="alert")
        assert action == "suppress" and "on_change" in reason


def test_on_change_fires_again_when_state_changes(hermetic):
    assert np.decide("market.ihsg_technical", state="DOWNTREND", msg="1")[0] == "digest"
    assert np.decide("market.ihsg_technical", state="DOWNTREND", msg="1")[0] == "suppress"
    assert np.decide("market.ihsg_technical", state="RECOVERY", msg="2")[0] == "digest"


def test_on_change_defaults_state_to_message_hash(hermetic):
    assert np.decide("report.forward_test", msg="same body")[0] == "digest"
    assert np.decide("report.forward_test", msg="same body")[0] == "suppress"
    assert np.decide("report.forward_test", msg="a NEW trade closed")[0] == "digest"


# ── tier dispatch ────────────────────────────────────────────────────────────

def test_tier3_log_only_never_sends(hermetic):
    action, reason = np.decide("report.daily_signal", msg="0 signals")
    assert action == "suppress" and reason == "tier3 log-only"
    assert hermetic == []


def test_tier2_buffers_to_digest_and_does_not_send(hermetic, tmp_path):
    action, reason = np.decide("report.eod_trade_plan", msg="plan body")
    assert action == "digest" and reason == "tier2 digest"
    assert hermetic == []  # nothing sent yet
    buf = tmp_path / "digest_buffer"
    files = list(buf.glob("*.jsonl"))
    assert len(files) == 1
    item = json.loads(files[0].read_text().splitlines()[0])
    assert item["event"] == "report.eod_trade_plan"
    assert item["text"] == "plan body"


# ── digest flush ─────────────────────────────────────────────────────────────

def test_flush_sends_one_message_and_archives(hermetic, tmp_path):
    np.decide("report.eod_trade_plan", msg="plan")
    np.decide("market.ihsg_technical", state="DOWNTREND", msg="IHSG broke 6200")
    assert len(hermetic) == 0
    result = np.flush_digest()
    assert result is True
    assert len(hermetic) == 1
    event, msg = hermetic[0]
    assert event == "report.evening_digest"
    assert "plan" in msg and "IHSG broke 6200" in msg
    # buffer archived, nothing left to flush
    buf = tmp_path / "digest_buffer"
    assert list(buf.glob("*.jsonl")) == []
    assert list(buf.glob("*.jsonl.sent"))


def test_flush_with_empty_buffer_returns_none(hermetic):
    assert np.flush_digest() is None
    assert hermetic == []


def test_flush_suppressed_by_off_keeps_buffer(hermetic, tmp_path):
    np.decide("report.eod_trade_plan", msg="plan")
    (tmp_path / "TELEGRAM_OFF").touch()
    assert np.flush_digest() is False
    assert hermetic == []
    assert list((tmp_path / "digest_buffer").glob("*.jsonl"))


def test_flush_send_failure_keeps_buffer(hermetic, tmp_path, monkeypatch):
    np.decide("report.eod_trade_plan", msg="plan")
    monkeypatch.setattr(tg, "send_telegram", lambda msg, event=None, **kw: False)
    assert np.flush_digest() is False
    assert list((tmp_path / "digest_buffer").glob("*.jsonl"))
