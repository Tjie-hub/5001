#!/usr/bin/env python3
"""One-off M1 freeze: snapshot today's live NR7 eligibility (wf_edge>0) into the
registry artifact, so production can stop querying wf_edge (spec §10-M1)."""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db import connect as db_connect

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data', 'walkforward.db'))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'registry', 'artifacts', 'NR7_BULL_v1_tickers.json')

conn = db_connect(DB_PATH)
tickers = sorted(r[0] for r in conn.execute(
    "SELECT ticker FROM wf_edge WHERE strategy='NR7 Breakout' AND expectancy_pct>0"))
conn.close()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f:
    json.dump({'strategy': 'NR7 Breakout', 'frozen_at': str(date.today()),
               'source': "wf_edge WHERE strategy='NR7 Breakout' AND expectancy_pct>0",
               'tickers': tickers}, f, indent=2)
print(f"froze {len(tickers)} tickers -> {OUT}")
