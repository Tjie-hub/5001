"""Re-execution of the 2026-09-30 cross-asset POC (memo 04 in this directory).

The original fetch_crossasset_poc.py + SAMPLE_OUTPUT_crossasset_poc.json ran once on
2026-09-30 (yfinance 1.7.0) but were never committed and did not survive the sync to
this host (tjiejet). This file re-creates the POC from memo 04's recorded scope so the
pair is committed next to the memo (D-063 F-1 rule: a driver is committed with its
result). Memo 04's table remains the record of the ORIGINAL run; every output of this
file is labeled RE-EXECUTION and the two are compared in the commit message.

Scope (memo 04 table): TLK, USDIDR=X, ^JKSE, KOL, BTU, FCPO=F -- status, range, rows,
max calendar-day gap, count of gaps > 7d. Scoping only: no DB writes, no screens.
"""
import json
import sys
from datetime import datetime, timezone

import yfinance as yf

SERIES = ["TLK", "USDIDR=X", "^JKSE", "KOL", "BTU", "FCPO=F"]


def probe(ticker: str) -> dict:
    try:
        h = yf.Ticker(ticker).history(period="max", auto_adjust=False)
    except Exception as e:  # noqa: BLE001 -- probe must report, not crash
        return {"status": "ERROR", "error": f"{type(e).__name__}: {e}"[:200]}
    if h is None or h.empty:
        return {"status": "EMPTY", "rows": 0}
    idx = h.index.tz_localize(None) if getattr(h.index, "tz", None) is not None else h.index
    dates = idx.normalize()
    diffs = dates.to_series().diff().dt.days.dropna()
    return {
        "status": "OK",
        "start": str(dates.min().date()),
        "end": str(dates.max().date()),
        "rows": int(len(h)),
        "max_gap_days": float(diffs.max()),
        "n_gaps_gt_7d": int((diffs > 7).sum()),
    }


def main() -> None:
    out = {
        "label": ("RE-EXECUTION 2026-10-05 of the 2026-09-30 cross-asset POC "
                  "(original artifacts never committed; see memo 04 for the original run)"),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "yfinance_version": yf.__version__,
        "auto_adjust": False,
        "series": {t: probe(t) for t in SERIES},
    }
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
