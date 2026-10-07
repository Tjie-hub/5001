#!/usr/bin/env python3
"""POC — OHLCV pre-2021 feasibility (data-acquisition scoping item 07, 2026-09-30).

Scoping-only probe behind memo 07_OHLCV_PRE2021_FEASIBILITY_2026-09-30.md: tests whether
yfinance serves (A) long daily-depth history for still-listed .JK names and (B) ANY history for
delisted/inactive names taken from the corpus's own idx_tickers status table. No DB writes, no
pipeline wiring. Sample artifact captured in the memo by redirecting stdout:
    python poc_ohlcv_pre2021_yfinance.py
"""
import sys

import yfinance as yf

LISTED_PROBES = ["BBRI.JK", "UNTR.JK", "HMSP.JK"]
# names the corpus itself flags inactive (idx_tickers.status='inactive')
INACTIVE_PROBES = ["ZEUS.JK", "TURI.JK", "BSMT.JK", "FINN.JK"]


def probe(ticker: str) -> str:
    try:
        h = yf.Ticker(ticker).history(period="max", interval="1mo", auto_adjust=False)
    except Exception as exc:
        return f"{ticker:9s} ERROR {type(exc).__name__}: {str(exc)[:80]}"
    if h is None or h.empty:
        return f"{ticker:9s} EMPTY (no data served)"
    return f"{ticker:9s} rows={len(h):5d} first={h.index[0].date()} last={h.index[-1].date()}"


def main() -> int:
    print("=== A. depth for still-listed long-history names ===")
    for t in LISTED_PROBES:
        print(probe(t))
    print("\n=== B. delisted/inactive-name availability (survivorship probe) ===")
    for t in INACTIVE_PROBES:
        print(probe(t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
