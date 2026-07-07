"""Phase 5 instrumentation: BULL-entry state-change alerts + NR7 signal alert."""
import engine.phase5_watch as pw


def test_band_changes_only_reports_transitions():
    prev = {"AAAA": "SIDEWAYS", "BBBB": "BULL_MODERATE"}
    cur = {"AAAA": "BULL_MODERATE", "BBBB": "BULL_MODERATE", "CCCC": "BEAR"}
    changes = pw.band_changes(prev, cur, eligible=("BULL_MODERATE", "BULL_STRONG"))
    assert changes == [("AAAA", "SIDEWAYS", "BULL_MODERATE")]   # entered
    # leaving is also a transition
    changes2 = pw.band_changes({"AAAA": "BULL_MODERATE"}, {"AAAA": "BEAR"},
                               eligible=("BULL_MODERATE", "BULL_STRONG"))
    assert changes2 == [("AAAA", "BULL_MODERATE", "BEAR")]


def test_nr7_alert_message_contains_counter():
    msg = pw.nr7_signal_alert_msg("PADI", n_signals_to_date=1)
    assert "PHASE 5" in msg and "PADI" in msg and "#1" in msg
