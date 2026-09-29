"""Alert when a recorded forward-test window spans an issuance ex-date (D-064 §D).

WHY: research prices were split-adjusted only, so a rights issue / bonus / reverse
split ex-date prints a mechanical price step (median rights ~-30%). Inside a
forward-test window that step is arithmetic, not signal: it can fake a FADE
breakdown, collapse a REGIME ATR trail, or inflate VOLEX trailing volatility.
The in-flight protocols are frozen, so nothing here censors or edits a ledger; it
only detects, and a hit becomes a dated deviation decision under the protocol.
The broad-search audit (2026-09-29) found zero such windows so far.

Windows checked (from the ledgers each recorder already writes):
  REGIME-002  closed trades                 (entry_date, exit_date]
  FADE-001    closed trades, h=20 leg       (entry_date, h20 exit_date]
  VOLEX-001   formations, held + excluded   hold (formation, formation + 31d] ALERTS;
              the 92d vol lookback is reported as info only -- Parkinson-60 is a
              high/low range estimator, so a close-to-close gap barely moves it
FADE's open signals are recomputed by its recorder and never stored, so recent
issuance ex-dates are also listed as a heads-up (informational, exit 0).

Exit 1 only on a NEW hit (seen hits persist in logs/issuance_windows_seen.json),
so cron_wrap alerts once per hit rather than daily.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PM = ROOT / "docs" / "research_programs" / "P-M"
LEDGERS = {
    "REGIME-002": PM / "forward_regime" / "ledger.json",
    "FADE-001": PM / "forward_fade" / "ledger.json",
    "VOLEX-001": PM / "forward_exclusion" / "ledger.json",
}
SEEN = ROOT / "logs" / "issuance_windows_seen.json"
VOL_LOOKBACK_DAYS = 92      # ~60 sessions of trailing Parkinson vol
VOLEX_HOLD_DAYS = 31        # enter close(t+1), hold 21 sessions (PROTOCOL.md)
HEADS_UP_DAYS = 30


def windows_from_ledgers(ledgers: dict) -> list[tuple[str, str, str, str, str]]:
    """[(test, ticker, start_exclusive, end_inclusive, kind)]; kind = hold | lookback."""
    out = []
    for t in ledgers.get("REGIME-002", {}).get("trades", []):
        out.append(("REGIME-002", t["ticker"], t["entry_date"], t["exit_date"], "hold"))
    for t in ledgers.get("FADE-001", {}).get("trades", []):
        h20 = (t.get("horizons") or {}).get("20") or {}
        if h20.get("exit_date"):
            out.append(("FADE-001", t["ticker"], t["entry_date"], h20["exit_date"], "hold"))
    for e in ledgers.get("VOLEX-001", {}).get("entries", []):
        f = date.fromisoformat(e["formation_date"])
        lo = str(f - timedelta(days=VOL_LOOKBACK_DAYS))
        hi = str(f + timedelta(days=VOLEX_HOLD_DAYS))
        names = list(e.get("held", [])) + [x["ticker"] for x in e.get("excluded", [])]
        out += [("VOLEX-001", tk, str(f), hi, "hold") for tk in names]
        out += [("VOLEX-001", tk, lo, str(f), "lookback") for tk in names]
    return out


def find_hits(windows, events) -> list[dict]:
    """Every window whose ticker has an issuance ex-date in (start, end]."""
    hits = []
    for test, tk, start, end, wkind in windows:
        for ex, m, c, kind in events.get(tk, []):
            if start < ex <= end:
                hits.append({"test": test, "ticker": tk, "window": [start, end],
                             "window_kind": wkind, "ex_date": ex, "type": kind,
                             "m": m, "c": c})
    return hits


def main() -> int:
    from data.adjustments import load_issuance_events
    from data.db import connect
    ledgers = {}
    for name, p in LEDGERS.items():
        try:
            ledgers[name] = json.loads(p.read_text())
        except (OSError, ValueError) as e:
            print(f"WARN {name}: ledger unreadable ({e}) -- skipped")
    with connect(read_only=True) as c:
        events = load_issuance_events(c)
    hits = find_hits(windows_from_ledgers(ledgers), events)

    try:
        seen = set(json.loads(SEEN.read_text()))
    except (OSError, ValueError):
        seen = set()
    key = lambda h: f"{h['test']}|{h['ticker']}|{h['ex_date']}|{h['window'][0]}"
    info = [h for h in hits if h["window_kind"] == "lookback"]
    new = [h for h in hits if h["window_kind"] == "hold" and key(h) not in seen]

    today = date.today()
    recent = sorted((ex, tk, kind) for tk, evs in events.items() for ex, _, _, kind in evs
                    if str(today - timedelta(days=HEADS_UP_DAYS)) < ex <= str(today))
    print(f"windows checked: {len(windows_from_ledgers(ledgers))} | hits: {len(hits)} "
          f"| new: {len(new)}")
    for ex, tk, kind in recent:
        print(f"  heads-up (FADE open windows): {tk} {kind} ex {ex}")
    for h in info:
        print(f"  info (VOLEX vol lookback, range estimator): {h['ticker']} {h['type']} "
              f"ex {h['ex_date']}")
    if not new:
        return 0
    print("⚠️ Forward-test window spans an issuance ex-date (mechanical price step)")
    for h in new:
        print(f"  {h['test']}: {h['ticker']} {h['type']} ex {h['ex_date']} inside "
              f"({h['window'][0]}, {h['window'][1]}]  m={h['m']:.4g} c={h['c']:.4g}")
    print("Decide under the protocol's deviation log; the ledger is never edited.")
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen | {key(h) for h in new}), indent=1))
    return 1


if __name__ == "__main__":
    sys.exit(main())
