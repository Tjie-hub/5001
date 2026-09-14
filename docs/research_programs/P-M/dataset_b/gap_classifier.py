#!/usr/bin/env python3
"""Suspension vs scraper/data gap. READ-ONLY.

WHY THE EXISTING DETECTOR CANNOT BE USED
----------------------------------------
engine/suspension_detector.py classifies a gap as 'suspension' when
abs(gap_pct)*100 >= 10, a PER-TICKER price-jump rule that never asks whether
other tickers share the same gap. Measured consequence: all 81 events touching
the Dataset A window cluster on 2026-05-14 -> 05-25 (a market-wide IHSG
closure) and 21 of them are labelled 'suspension'. July 2026's 82 events are
the same story against the EOD scraper failures. The table therefore cannot
certify suspension cleanliness in either direction.

THE DISCRIMINATOR IS BREADTH, NOT PRICE
---------------------------------------
A genuine single-name halt leaves its peers trading. A capture failure removes
many names at once. So the test is: on the sessions a ticker is missing, what
share of its PIT peers is ALSO missing? Near 1.0 is infrastructure; near 0.0 is
a ticker-specific event. This never infers a suspension from a scraper failure
because a scraper failure cannot produce a low peer-absence ratio.

The classifier deliberately returns UNVERIFIED rather than SUSPENSION for the
ticker-specific case: IDX publishes suspension notices, and this repository
holds none. Absence of a bar is consistent with a halt but does not establish
one, and Dataset B declares no suspension exclusion on that basis.
"""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import foundation as F

HERE = Path(__file__).resolve().parent
# Share of PIT peers also missing, above which the absence is infrastructure.
MARKET_GAP_THRESHOLD = 0.50


def classify(conn, roster, cal, candidate_sessions=None):
    sessions = candidate_sessions or cal.sessions
    ph = ",".join("?" * len(roster.universe))
    present = defaultdict(set)
    for tk, d in conn.execute(
            f"SELECT ticker,date FROM ohlcv WHERE ticker IN ({ph}) AND date >= ? AND date <= ? "
            f"AND close IS NOT NULL", sorted(roster.universe) + [sessions[0], sessions[-1]]):
        present[d].add(tk)

    events = []
    for d in sessions:
        members = set(roster.members_by_period(d))
        if not members:
            continue
        missing = members - present.get(d, set())
        if not missing:
            continue
        peer_absent = len(missing) / len(members)
        for tk in sorted(missing):
            if peer_absent >= MARKET_GAP_THRESHOLD:
                verdict, why = "MARKET_GAP", (
                    f"{len(missing)}/{len(members)} PIT peers also absent "
                    f"({peer_absent:.0%}) — infrastructure, not a per-name event")
            else:
                verdict, why = "TICKER_ABSENCE_UNVERIFIED", (
                    f"only {len(missing)}/{len(members)} peers absent ({peer_absent:.0%}) — "
                    f"ticker-specific, but no IDX suspension notice exists in this "
                    f"repository to confirm a halt")
            events.append({"ticker": tk, "session": d, "peers_absent": len(missing),
                           "peers_total": len(members), "peer_absent_ratio": round(peer_absent, 4),
                           "verdict": verdict, "reason": why})
    return events


def main(write=False):
    conn = F.ro_connect()
    cal = F.SessionCalendar.load("v2"); ros = F.PitRoster.load("v1")
    a = F.load_artifact("SESSION_CALENDAR", "v2")
    candidates = sorted(set(cal.sessions) | {e["date"] for e in a["excluded"]})
    ev = classify(conn, ros, cal, candidates)
    by = defaultdict(int)
    for e in ev:
        by[e["verdict"]] += 1
    print("=== absence classification over admitted + excluded sessions ===")
    print(f"  ticker-session absences examined: {len(ev):,}")
    for k, v in sorted(by.items()):
        print(f"    {k:28s} {v:,}")
    sess = defaultdict(lambda: [0, 0])
    for e in ev:
        sess[e["session"]][0 if e["verdict"] == "MARKET_GAP" else 1] += 1
    print("\n  sessions carrying absences:")
    for d in sorted(sess):
        m, t = sess[d]
        print(f"    {d}  market_gap={m:<4d} ticker_specific={t:<4d} "
              f"{'(EXCLUDED from calendar)' if d not in cal else '(admitted)'}")
    print("\n  legacy engine/suspension_detector.py comparison over the same window:")
    rows = conn.execute(
        "SELECT classification, COUNT(*) FROM suspension_events "
        "WHERE last_normal_date >= ? AND resume_date <= ? GROUP BY 1",
        (cal.sessions[0], cal.sessions[-1])).fetchall()
    for cls, n in rows:
        print(f"    legacy '{cls}': {n}")
    print("    -> legacy labels are per-ticker price-jump verdicts and are NOT used by Dataset B")
    out = {"threshold": MARKET_GAP_THRESHOLD, "events": ev,
           "counts": dict(by),
           "policy": "Dataset B declares NO suspension-based exclusion. Sessions are "
                     "excluded by the market-wide completeness predicate only. Ticker-specific "
                     "absences are recorded as UNVERIFIED and drop out naturally because a "
                     "forward return requires both endpoint bars."}
    if write:
        p = HERE / "artifacts" / "GAP_CLASSIFICATION_v1.json"
        p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        print(f"\nwrote {p.name}")
    conn.close(); return out


if __name__ == "__main__":
    main(write="--write" in sys.argv)
