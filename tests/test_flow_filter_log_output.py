"""2026-10-19 audit: under the service (stdout not a TTY) flow_filter's \\r progress bar joined the whole run into one
journald "[blob data]" line that also swallowed the scheduler's "Flow fetch selesai" log line."""
import io
import sys

import flow_filter


def test_no_carriage_returns_when_stdout_is_not_a_tty(monkeypatch):
    out = io.StringIO()  # isatty() is False
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "argv", ["flow_filter.py", "AAAA", "BBBB"])
    monkeypatch.setattr(flow_filter, "_load_token", lambda: "t")
    monkeypatch.setattr(flow_filter, "_fetch_tradebook", lambda token, t: None)
    monkeypatch.setattr(flow_filter.tradebook_cache, "recent", lambda: None)
    monkeypatch.setattr(flow_filter.tradebook_cache, "get", lambda t, after: None)
    monkeypatch.setattr(flow_filter, "FLOW_PACE", 0)
    flow_filter.main()
    text = out.getvalue()
    assert "\r" not in text and text.endswith("\n") and "Analyzed: 0/2" in text
