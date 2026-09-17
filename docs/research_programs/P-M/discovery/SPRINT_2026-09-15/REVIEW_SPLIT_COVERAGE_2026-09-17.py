#!/usr/bin/env python3
"""Does the corporate_actions gap contaminate the research panels? (2026-09-17)

REVIEW_BAND_INDEP_SOURCE_2026-09-16.py reports 101 split ex-dates in
`corporate_actions` against 292 reachable via `corporate_action_events`, and
`sprint_lib.load_corporate_actions` reads ONLY the former. An unadjusted split
is a large fake negative return; `build_adjusted` drops |ret| > 0.9, so a 10:1
split is caught but a 5:1 (-80%) is not.

This measures the RESEARCH impact rather than the table gap: of the missing
ex-dates, how many land on a session with an actual price bar inside the
sprint (in-sample) or pseudo-OOS window, and how many clear the guard.

Answer as of this run: 2 ticker-days in-sample (RAJA, RMKE), 0 OOS.
Pipeline defect, not a results defect.
"""
import json
import sqlite3

DB = "/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db"
con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)

ca = {(t, str(d)[:10]) for t, d in
      con.execute("SELECT ticker,date FROM corporate_actions WHERE action='split'")}
ev = set()
for t, j in con.execute("SELECT ticker,raw_json FROM corporate_action_events "
                        "WHERE action_type IN ('stocksplit','stock_reverse','bonus')"):
    try:
        ex = str(json.loads(j).get("stocksplit_exdate") or "")[:10]
    except Exception:
        continue
    if len(ex) == 10:
        ev.add((t, ex))
missing = ev - ca
print(f"corporate_actions splits={len(ca)}  events splits={len(ev)}  "
      f"MISSING from corporate_actions={len(missing)}")

hits = []
for t, d in missing:
    cur = con.execute("SELECT date, close FROM ohlcv WHERE ticker=? AND is_final=1 "
                      "AND close>0 AND date<=? ORDER BY date DESC LIMIT 2", (t, d)).fetchall()
    if len(cur) < 2 or cur[0][0] != d:
        continue
    hits.append((t, d, cur[0][1] / cur[1][1] - 1.0))

for lo, hi, lab in (("2025-01-01", "2027-01-01", "SPRINT PANEL (in-sample)"),
                    ("2021-07-01", "2025-01-01", "PSEUDO-OOS")):
    sel = [h for h in hits if lo <= h[1] < hi]
    big = [h for h in sel if abs(h[2]) > 0.30]
    surv = [h for h in big if abs(h[2]) <= 0.90]
    print(f"\n{lab}: unadjusted split ex-dates with a price bar = {len(sel)}; "
          f"|move|>30% = {len(big)}; surviving the |ret|>0.9 guard = {len(surv)}")
    for t, d, v in sorted(surv, key=lambda x: x[2]):
        print(f"   {t:6s} {d}  raw ret {100*v:+7.1f}%")
