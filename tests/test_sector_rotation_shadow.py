"""Sector rotation is observe-only by default (owner 2026-10-16, after the D-101 G0 stop)."""
import scheduler.scanner as sc


def _blocked(monkeypatch):
    monkeypatch.setattr(sc, "_sector_verdict_raw", lambda t, s: (False, "Energy UNDERWEIGHT (score -3.00%)"))


def test_shadow_by_default_logs_and_passes(monkeypatch, caplog):
    _blocked(monkeypatch)
    monkeypatch.delenv("SECTOR_ROTATION_MODE", raising=False)
    with caplog.at_level("INFO"):
        ok, reason = sc._sector_verdict("ADRO", [])
    assert ok and "observe-only" in reason and "would be blocked" in caplog.text


def test_enforce_restores_the_block(monkeypatch):
    _blocked(monkeypatch)
    monkeypatch.setenv("SECTOR_ROTATION_MODE", "enforce")
    assert sc._sector_verdict("ADRO", []) == (False, "Energy UNDERWEIGHT (score -3.00%)")


def test_a_pass_is_unchanged(monkeypatch):
    monkeypatch.setattr(sc, "_sector_verdict_raw", lambda t, s: (True, "Financials OVERWEIGHT (score +2.00%)"))
    assert sc._sector_verdict("BBCA", []) == (True, "Financials OVERWEIGHT (score +2.00%)")
