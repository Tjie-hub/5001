"""D-064 §D: the monitor detects recorded forward windows spanning an issuance
ex-date (it never edits a ledger)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ciw", Path(__file__).resolve().parents[1] / "scripts" / "check_issuance_windows.py")
ciw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ciw)

LEDGERS = {
    "REGIME-002": {"trades": [{"ticker": "AAAA", "entry_date": "2026-09-01",
                               "exit_date": "2026-09-20"}]},
    "FADE-001": {"trades": [{"ticker": "BBBB", "entry_date": "2026-09-22",
                             "horizons": {"20": {"exit_date": "2026-10-20"}}}]},
    "VOLEX-001": {"entries": [{"formation_date": "2026-09-15", "held": ["CCCC"],
                               "excluded": [{"ticker": "DDDD"}]}]},
}


def test_windows_cover_all_three_ledgers():
    w = ciw.windows_from_ledgers(LEDGERS)
    assert {x[0] for x in w} == {"REGIME-002", "FADE-001", "VOLEX-001"}
    assert ("VOLEX-001", "DDDD", "2026-06-15", "2026-09-15", "lookback") in w
    assert ("VOLEX-001", "DDDD", "2026-09-15", "2026-10-16", "hold") in w


def test_hit_only_inside_the_window():
    w = ciw.windows_from_ledgers(LEDGERS)
    ev = {"AAAA": [("2026-09-10", 2.0, 40.0, "rightissue"),     # inside -> hit
                   ("2026-09-01", 2.0, 40.0, "rightissue")],    # entry day: exclusive
          "BBBB": [("2026-11-01", 1.3, 0.0, "bonus")],          # after exit
          "DDDD": [("2026-07-01", 0.1, 0.0, "stock_reverse")]}  # inside vol lookback
    hits = ciw.find_hits(w, ev)
    assert {(h["test"], h["ticker"], h["ex_date"], h["window_kind"]) for h in hits} == {
        ("REGIME-002", "AAAA", "2026-09-10", "hold"),
        ("VOLEX-001", "DDDD", "2026-07-01", "lookback")}


def test_monitor_never_writes_a_ledger():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "check_issuance_windows.py").read_text()
    assert "write_text" in src and src.count("write_text") == 1 and "SEEN.write_text" in src
