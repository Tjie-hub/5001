#!/usr/bin/env python3
"""POC fetch — {X} cross-asset series feasibility (data-acquisition scoping, 2026-09-30).

Scoping-only: fetches candidate free series once via yfinance, reports what was
actually obtained (range, rows, gaps, timezone semantics). Does NOT write to any
research DB, does NOT become part of the pipeline, and writes NO files itself —
the sample artifact is captured externally by redirecting stdout:
    python fetch_crossasset_poc.py > SAMPLE_OUTPUT_crossasset_poc.json

Candidate rationale (FAMILY_MAP_v2.md §D):
  TLK        NYSE ADR of Telkom Indonesia — the overnight-US anchor for {X}
  USDIDR=X   USD/IDR FX rate (Yahoo aggregate, not a traded fixing)
  ^JKSE      IHSG — alignment benchmark for any {X} excess computation
  KOL        VanEck Coal ETF — equity-grade coal proxy (physical Newcastle futures
             are not free); accepted only if we label the proxy grade honestly
  BTU        Peabody Energy — second coal equity proxy, US-listed
  FCPO=F     Bursa Malaysia crude palm oil futures — EXPECTED ABSENT on Yahoo;
             probed once to document the negative result rather than assume it
"""
import json
import sys
from datetime import datetime, timezone

import yfinance as yf

CANDIDATES = ["TLK", "USDIDR=X", "^JKSE", "KOL", "BTU", "FCPO=F"]


def probe(ticker: str) -> dict:
    out = {"ticker": ticker}
    try:
        hist = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust=False)
    except Exception as exc:  # network/parse failures are feasibility results too
        out["status"] = f"ERROR: {type(exc).__name__}: {exc}"
        return out
    if hist is None or hist.empty:
        out["status"] = "EMPTY — no data returned"
        return out
    idx = hist.index
    out["status"] = "OK"
    out["first_date"] = str(idx[0].date())
    out["last_date"] = str(idx[-1].date())
    out["n_rows"] = int(len(hist))
    gaps = idx.to_series().diff().dt.days.dropna()
    out["max_gap_days"] = int(gaps.max())
    out["n_gaps_over_7d"] = int((gaps > 7).sum())
    close = hist["Close"].dropna()
    out["last_close"] = round(float(close.iloc[-1]), 4)
    out["currency"] = hist.attrs.get("currency", "unknown")
    # PIT semantics: yfinance daily bars are exchange-local DATES; the close of
    # date t is only observable after that market's close — any signal must use
    # t to act at t+1 of the target market. For TLK (16:00 ET close) that is
    # ~03:00-04:00 WIB the next calendar day, i.e. ~5-6h before the IDX open.
    out["pit_note"] = (
        "daily close known only after own-market close; US closes map to "
        "next-day WIB pre-open"
        if ticker in ("TLK", "KOL", "BTU")
        else "daily close known after own-market close"
    )
    return out


def main() -> int:
    results = [probe(t) for t in CANDIDATES]
    doc = {
        "poc": "cross_asset_fetch_2026-09-30",
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "yfinance_version": yf.__version__,
        "purpose": "scoping only — no DB writes, no pipeline wiring",
        "results": results,
    }
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
