"""B.4 verification helper (brief 2026-10-22): print the day's market-risk scan lines so the
coverage gate's first live pre-open read can be checked — expect a partial-coverage pre-open
scan (vpin/accdist/breadth still missing at 09:05) to read ORANGE with the gate, not CRITICAL.
Read-only; run any time after a scan:  venv/bin/python3 scripts/risk_gate_check.py [DATE]"""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

day = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
con = sqlite3.connect(f"file:{Path(__file__).resolve().parents[1] / 'data' / 'walkforward.db'}?mode=ro",
                      uri=True)
rows = con.execute("SELECT time, score, tier, components FROM market_risk_log WHERE date = ? "
                   "ORDER BY time", (day,)).fetchall()
con.close()
if not rows:
    print(f"{day}: no scans yet")
for t, score, tier, comps in rows:
    c = json.loads(comps) if comps else {}
    live_fb = sum(1 for k in ("vpin", "accdist", "breadth", "foreign_flow") if c.get(k) is not None)
    print(f"{t} {score} {tier} | live flow-breadth {live_fb}/4 | "
          f"ihsg today {c.get('ihsg_move_pct')} prev {c.get('ihsg_prev_move_pct')}")
