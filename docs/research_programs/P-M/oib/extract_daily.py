"""Extract the session's final cumulative aggressor lots per ticker-day from the pinned snapshot.

B = MAX(buy_lot), S = MAX(sell_lot) over a ticker-day's bars (the counters are cumulative; fix
47ff225), plus the bar count. Month by month via the trade_date index. Output is a cache keyed by the
snapshot's sha256: ~/scratch/oib_daily_2026-10-08.json. Pre-outcome: no price after any date is read.
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import ownership as OW  # noqa: E402
from data.db import connect  # noqa: E402

OUT = Path.home() / "scratch" / "oib_daily_2026-10-08.json"


def main():
    con = connect(path=OW.WF_SNAPSHOT, read_only=True)
    rows = []
    y, m = 2025, 1
    while (y, m) <= (2026, 10):
        lo = date(y, m, 1).isoformat()
        hi = (date(y + (m == 12), m % 12 + 1, 1)).isoformat()
        part = con.execute("SELECT ticker, trade_date, MAX(buy_lot), MAX(sell_lot), COUNT(*) FROM stockbit_flow_bars "
                           "WHERE trade_date >= ? AND trade_date < ? GROUP BY ticker, trade_date", (lo, hi)).fetchall()
        rows += [list(r) for r in part]
        print(lo, len(part), flush=True)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    OUT.write_text(json.dumps({"wf_sha256": OW.WF_SHA256, "rows": rows}))
    print("rows", len(rows))


if __name__ == "__main__":
    main()
