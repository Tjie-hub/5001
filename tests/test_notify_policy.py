"""Tests for utils/notify_policy.py — the 2026-10-06 curation brief's gate:
tier classification, persistent dedup (once_per_day / on_change / cooldown),
the evening digest buffer + flush, and the global TELEGRAM_OFF blackout.
"""
import json
import os
import re
from datetime import datetime, timedelta

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

    def fake_send(msg, event=None, subject=None, state=None, **kw):
        # Mimic the real muscle's contract: the sender runs the gate itself
        # (OFF, classification, dedup) and returns False when suppressed.
        action, _ = np.decide(event, subject=subject, state=state, msg=msg)
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


def test_flush_suppressed_by_off_keeps_claimed_items(hermetic, tmp_path):
    """Under the global OFF the flush is suppressed AFTER claiming — the
    claimed .sending files are kept (never dropped) for the next flush."""
    np.decide("report.eod_trade_plan", msg="plan")
    (tmp_path / "TELEGRAM_OFF").touch()
    assert np.flush_digest() is False
    assert hermetic == []
    buf = tmp_path / "digest_buffer"
    assert list(buf.glob("*.jsonl.sending"))
    assert not list(buf.glob("*.jsonl.sent"))


def test_flush_send_failure_keeps_claimed_items(hermetic, tmp_path, monkeypatch):
    np.decide("report.eod_trade_plan", msg="plan")
    monkeypatch.setattr(tg, "send_telegram", lambda msg, event=None, **kw: False)
    assert np.flush_digest() is False
    assert list((tmp_path / "digest_buffer").glob("*.jsonl.sending"))


# ── follow-up brief 2026-10-06: D1–D4, late flush, shared buffer ────────────

def _append_line(tmp_path, day, obj):
    """Simulate an external writer (cron process / jurnal26) appending a line."""
    buf = tmp_path / "digest_buffer"
    buf.mkdir(exist_ok=True)
    with open(buf / f"{day}.jsonl", "a") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def test_d1_item_appended_during_flush_is_not_lost(hermetic, tmp_path):
    """D1: claim-then-read. An item a cron process appends while the flush is
    sending goes to a fresh .jsonl and is sent by the NEXT flush."""
    day = np.wib_today()
    _append_line(tmp_path, day, {"event": "report.eod_trade_plan",
                                 "ts": 1.0, "text": "first item"})

    fired = {"n": 0}

    def sneaky_cron_append(msg, event=None, **kw):
        # fires between the claim and the archive — like a cron appending now
        if fired["n"] == 0:
            fired["n"] += 1
            _append_line(tmp_path, day, {"event": "report.forward_test",
                                         "ts": 2.0, "text": "late arrival"})
        hermetic.append((event, msg))
        return True

    tg.send_telegram = sneaky_cron_append  # fixture already swapped it; restore is monkeypatch's job
    # call through the module indirection flush uses
    assert np.flush_digest() is True
    buf = tmp_path / "digest_buffer"
    live = list(buf.glob("*.jsonl"))
    assert len(live) == 1, "mid-flush append must stay in a live file"
    sent_text = hermetic[0][1]
    assert "first item" in sent_text and "late arrival" not in sent_text
    # next flush picks the late arrival up
    hermetic.clear()
    assert np.flush_digest() is True
    assert "late arrival" in hermetic[0][1]
    assert not list(buf.glob("*.jsonl"))


def test_d2_digest_message_is_html_safe(hermetic, tmp_path):
    """D2: item text is html.escape()d; the raw <event> token is gone."""
    day = np.wib_today()
    _append_line(tmp_path, day, {
        "event": "market.ihsg_technical", "ts": 1.0,
        "text": "<b>IHSG</b> broke 6200 & support <market.ihsg_technical>"})
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "<b>Evening Digest</b>" in msg          # intentional tags survive
    assert "&lt;b&gt;IHSG&lt;/b&gt;" in msg        # item tags escaped
    assert "&amp;" in msg and "&lt;market.ihsg_technical&gt;" in msg
    # no unescaped '<' outside the tags the flush emits on purpose
    leftover = re.sub(r"</?(b|i)>", "", msg)
    assert "<" not in leftover and ">" not in leftover


def test_d2_offenders_html_escaped(hermetic, tmp_path):
    day = np.wib_today()
    _append_line(tmp_path, day, {"event": "report.eod_trade_plan", "ts": 1.0,
                                 "text": "a < b and c > d"})
    np.flush_digest()
    leftover = re.sub(r"</?(b|i)>", "", hermetic[0][1])
    assert "<" not in leftover


def test_d3_late_flush_is_not_blocked_by_the_main_flush(hermetic, tmp_path):
    """D3 (chosen: separate event report.late_digest, once_per_day)."""
    _append_line(tmp_path, np.wib_today(),
                 {"event": "report.forward_test", "ts": 1.0, "text": "evening item"})
    assert np.flush_digest(event="report.evening_digest") is True
    assert hermetic[0][0] == "report.evening_digest"
    _append_line(tmp_path, np.wib_today(),
                 {"event": "report.forward_test", "ts": 2.0, "text": "fwd cycle item"})
    assert np.flush_late_digest() is True          # 20:45 flush still allowed
    assert hermetic[1][0] == "report.late_digest"
    assert "fwd cycle item" in hermetic[1][1]
    assert "Evening" in hermetic[0][1] and "Late Digest" in hermetic[1][1]
    assert np.EVENTS["report.late_digest"][0] == np.TIER_SEND


def test_late_flush_silent_when_buffer_empty(hermetic):
    assert np.flush_late_digest() is None
    assert hermetic == []


def test_external_source_lines_accepted_and_sectioned(hermetic, tmp_path):
    """jurnal26 lines: unregistered event + source + own section."""
    day = np.wib_today()
    _append_line(tmp_path, day, {
        "event": "jurnal.positions", "ts": 1.0, "source": "jurnal26",
        "section": "Positions", "text": "BBCA closed +2.1%"})
    _append_line(tmp_path, day, {
        "event": "jurnal.weekly", "ts": 2.0, "source": "jurnal26",
        "section": "Weekly", "text": "weekly journal summary"})
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "<b>Positions</b>" in msg and "BBCA closed +2.1%" in msg
    assert "<b>Weekly</b>" in msg
    assert "(jurnal26)" in msg
    # unregistered event did NOT block the line (gate doesn't apply to buffer)


def test_section_grouping_by_event_prefix(hermetic, tmp_path):
    day = np.wib_today()
    _append_line(tmp_path, day, {"event": "market.ihsg_technical", "ts": 1.0,
                                 "text": "IHSG label change"})
    _append_line(tmp_path, day, {"event": "report.eod_trade_plan", "ts": 2.0,
                                 "text": "3 BUY candidates"})
    _append_line(tmp_path, day, {"event": "weird.nope", "ts": 3.0,
                                 "text": "unknown prefix item"})
    np.flush_digest()
    msg = hermetic[0][1]
    assert msg.index("<b>Market</b>") < msg.index("IHSG label change")
    assert msg.index("<b>Reports</b>") < msg.index("3 BUY candidates")
    assert msg.index("<b>Other</b>") < msg.index("unknown prefix item")
    assert msg.index("<b>Market</b>") < msg.index("<b>Reports</b>") < msg.index("<b>Other</b>")


def _set_flush_today(monkeypatch, today):
    """Pin flush_digest's notion of 'today' so D4 trading-day tests are
    deterministic (no dependence on the weekday the suite runs on). Same
    contract as the real wib_today(): a 'YYYY-MM-DD' string."""
    monkeypatch.setattr(np, "wib_today", lambda: today.isoformat())


def test_d4_items_older_than_two_trading_days_are_stale_skipped(hermetic, tmp_path, monkeypatch):
    """D4 (amended 2026-10-06): stale = more than 2 IDX trading days old.
    Wed 2026-09-30 → Mon 2026-10-05 is Thu+Fri+Mon = 3 trading days → stale;
    Fri 2026-10-02 → Mon 2026-10-05 is 1 trading day → kept."""
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 10, 5))
    _append_line(tmp_path, "2026-09-30", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "ancient item"})
    _append_line(tmp_path, "2026-10-02", {"event": "report.eod_trade_plan",
                                          "ts": 2.0, "text": "friday item"})
    _append_line(tmp_path, "2026-10-05", {"event": "report.eod_trade_plan",
                                          "ts": 3.0, "text": "fresh item"})
    buf = tmp_path / "digest_buffer"
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "fresh item" in msg and "friday item" in msg
    assert "ancient item" not in msg
    assert "1 older items skipped (see logs/digest_buffer)" in msg
    assert list(buf.glob("2026-09-30.jsonl.stale"))
    assert not list(buf.glob("2026-09-30.jsonl"))           # live file gone
    assert not list(buf.glob("2026-09-30.jsonl.sending"))   # claimed file archived


def test_d4_only_stale_items_no_send(hermetic, tmp_path, monkeypatch):
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 10, 5))
    _append_line(tmp_path, "2026-09-24", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "ancient"})
    assert np.flush_digest() is None       # nothing fresh → nothing sent
    assert hermetic == []
    assert list((tmp_path / "digest_buffer").glob("*.jsonl.stale"))


def test_d4_friday_flush_failure_survives_monday(hermetic, tmp_path, monkeypatch):
    """The case the calendar-day rule got wrong (its M3/J1 complaint): an item
    written Friday whose flush fails must be sent by Monday's flush — a
    Friday→Monday gap is 1 trading day, not stale."""
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 10, 5))
    _append_line(tmp_path, "2026-10-02", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "friday evening plan"})
    assert np.flush_digest() is True
    assert "friday evening plan" in hermetic[0][1]
    assert "older items skipped" not in hermetic[0][1]


def test_d4_three_trading_days_back_is_skipped(hermetic, tmp_path, monkeypatch):
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 10, 5))
    # Thu 10-01 → Mon 10-05: Fri, Mon = 2 trading days → kept, right on the edge.
    _append_line(tmp_path, "2026-10-01", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "thursday item"})
    # Wed 09-30 → Mon 10-05: Thu, Fri, Mon = 3 trading days → stale.
    _append_line(tmp_path, "2026-09-30", {"event": "report.eod_trade_plan",
                                          "ts": 2.0, "text": "wednesday item"})
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "thursday item" in msg
    assert "wednesday item" not in msg
    assert "1 older items skipped" in msg


def test_d4_holiday_inside_window_is_not_counted(hermetic, tmp_path, monkeypatch):
    """Natal 2026: Thu 12-24 (Cuti Bersama) and Fri 12-25 (Natal) are IDX
    holidays. An item from Wed 12-23 reaches Mon 12-28 across only 1 trading
    day (Mon) → kept, where a naive calendar-day rule would see 5 days."""
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 12, 28))
    _append_line(tmp_path, "2026-12-23", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "pre-holiday item"})
    assert np.flush_digest() is True
    assert "pre-holiday item" in hermetic[0][1]
    assert "older items skipped" not in hermetic[0][1]


def test_d4_calendar_fallback_when_calendar_unreadable(hermetic, tmp_path, monkeypatch):
    """engine.calendar_filter unavailable → fall back to 2 CALENDAR days: the
    Friday item is then 3 calendar days old on Monday and is dropped (the old
    behaviour), while same-day items still go out."""
    import sys
    from datetime import date
    _set_flush_today(monkeypatch, date(2026, 10, 5))
    monkeypatch.setitem(sys.modules, "engine.calendar_filter", None)
    _append_line(tmp_path, "2026-10-02", {"event": "report.eod_trade_plan",
                                          "ts": 1.0, "text": "friday item"})
    _append_line(tmp_path, "2026-10-05", {"event": "report.eod_trade_plan",
                                          "ts": 2.0, "text": "fresh item"})
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "fresh item" in msg
    assert "friday item" not in msg
    assert "1 older items skipped" in msg


def test_multi_part_split_when_over_limit(hermetic, tmp_path):
    day = np.wib_today()
    for i in range(30):
        _append_line(tmp_path, day, {
            "event": "report.eod_trade_plan", "ts": float(i),
            "text": f"item {i:02d} " + "x" * 180})
    total_chars = sum(len(t) for t in ("x" * 188,) * 30)
    assert total_chars > 3800
    assert np.flush_digest() is True
    assert len(hermetic) >= 2                       # consecutive parts
    assert all(e == "report.evening_digest" for e, _ in hermetic)
    assert any("(1/2)" in m for _, m in hermetic)
    assert any("(2/2)" in m for _, m in hermetic)
    joined = "\n".join(m for _, m in hermetic)
    assert "item 00 " in joined and "item 29 " in joined  # nothing truncated
    assert not list((tmp_path / "digest_buffer").glob("*.jsonl.sending"))
    assert list((tmp_path / "digest_buffer").glob("*.jsonl.sent"))


def test_multi_part_failure_keeps_everything(hermetic, tmp_path, monkeypatch):
    day = np.wib_today()
    for i in range(30):
        _append_line(tmp_path, day, {
            "event": "report.eod_trade_plan", "ts": float(i),
            "text": f"item {i:02d} " + "y" * 180})
    calls = {"n": 0}

    def flaky(msg, event=None, **kw):
        calls["n"] += 1
        return calls["n"] == 1          # part 1 ok, part 2 fails
    monkeypatch.setattr(tg, "send_telegram", flaky)
    assert np.flush_digest() is False
    buf = tmp_path / "digest_buffer"
    assert list(buf.glob("*.jsonl.sending"))     # nothing archived
    assert not list(buf.glob("*.jsonl.sent"))


def test_malformed_buffer_line_skipped_never_fatal(hermetic, tmp_path, caplog):
    day = np.wib_today()
    buf = tmp_path / "digest_buffer"
    buf.mkdir(exist_ok=True)
    with open(buf / f"{day}.jsonl", "a") as fh:
        fh.write("{not json at all\n")
        fh.write(json.dumps({"ts": 1.0, "text": "missing event is fine",
                             "source": "jurnal26"}) + "\n")
        fh.write(json.dumps({"event": "no.text"} ) + "\n")   # no text → malformed
    assert np.flush_digest() is True
    msg = hermetic[0][1]
    assert "missing event is fine" in msg
    assert "no.text" not in msg
    assert any("malformed" in r.message for r in caplog.records)


def test_tier2_items_still_buffer_while_global_off(hermetic, tmp_path):
    """D4 model: OFF blocks sends, not digest buffering — the digest resumes
    cleanly (≤2-day items) when the blackout is lifted."""
    (tmp_path / "TELEGRAM_OFF").touch()
    action, _ = np.decide("report.eod_trade_plan", msg="plan under blackout")
    assert action == "digest"
    assert list((tmp_path / "digest_buffer").glob("*.jsonl"))
    # dedup still applies while OFF: an unchanged on_change state is not buffered
    n_before = len(list((tmp_path / "digest_buffer").glob("*.jsonl")))
    action, reason = np.decide("market.ihsg_technical", state="DOWNTREND",
                               msg="IHSG under blackout")
    assert action == "digest"
    action, reason = np.decide("market.ihsg_technical", state="DOWNTREND",
                               msg="IHSG under blackout (repeat scan)")
    assert action == "suppress" and "on_change" in reason
    assert len(list((tmp_path / "digest_buffer").glob("*.jsonl"))) == n_before
