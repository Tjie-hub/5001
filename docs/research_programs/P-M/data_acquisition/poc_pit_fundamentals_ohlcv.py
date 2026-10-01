#!/usr/bin/env python3
"""POC for the PIT feasibility memos (planner tasks 3A/3B, 2026-09-30).

One ticker, one fiscal year -- what a free source can actually prove about
filing dates vs period ends -- plus a delisted-OHLCV survivorship probe.
No backfill, no DB writes, no logins, no bot-block circumvention: any source
that blocks the request is REPORTED and dropped.

Probe 1 (fundamentals): yfinance annual income statement for BBCA.JK --
report the statement's period-end dates and headline numbers for the latest
fiscal year, and whether ANY filing/publication timestamp exists in the
payload (expected: none -- Yahoo statements carry period ends only).

Probe 2 (OHLCV depth incl. delisted): yfinance daily bars for three known
IDX delisting/suspension casualties (BTEL.JK, ELTY.JK, Kiwoom-probe KIWI? no
-- third probe is DUTI.JK) -- row counts and last bar dates show how far back
delisted names survive on Yahoo.

Probe 3 (IDX disclosure reachability): ONE unauthenticated GET against the
public announcement search endpoint the idx.co.id website uses, browser UA,
5s timeout. Status code + content-type recorded; on non-200 the source is
flagged blocked and nothing further is attempted.

    python docs/research_programs/P-M/data_acquisition/poc_pit_fundamentals_ohlcv.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf

OUT = {}


def main():
    t0 = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---- Probe 1: fundamentals with (missing) filing timestamps ----
    tk = yf.Ticker("BBCA.JK")
    inc = tk.get_income_stmt(freq="yearly")
    probe1 = {"source": "yfinance get_income_stmt(BBCA.JK, yearly)"}
    if inc is None or inc.empty:
        probe1["status"] = "EMPTY"
    else:
        latest_col = inc.columns.max()
        rows = {}
        for field in ("TotalRevenue", "NetIncomeContinuousOperations",
                      "OperatingIncome"):
            if field in inc.index:
                rows[field] = None if pd.isna(inc.loc[field, latest_col]) \
                    else int(inc.loc[field, latest_col])
        probe1.update({
            "status": "OK",
            "period_end": str(pd.Timestamp(latest_col).date()),
            "fiscal_year_fields_in_payload": sorted(
                str(c) for c in inc.columns)[:6],
            "headline_fields": rows,
            "filing_timestamp_present": False,
            "note": "Yahoo statements carry period-end columns only; no "
                    "filing/publication timestamp exists anywhere in the "
                    "payload -- PIT from this source is construction, not "
                    "observation"})
    OUT["probe1_fundamentals"] = probe1

    # ---- Probe 2: delisted-OHLCV survivorship ----
    probe2 = []
    for sym in ("BTEL.JK", "ELTY.JK", "DUTI.JK"):
        try:
            h = yf.Ticker(sym).history(period="max", interval="1d",
                                       auto_adjust=False)
            if h.empty:
                probe2.append({"symbol": sym, "rows": 0, "status": "EMPTY"})
                continue
            probe2.append({
                "symbol": sym, "rows": int(len(h)),
                "first": str(h.index.min().date()),
                "last": str(h.index.max().date()),
                "status": "OK"})
        except Exception as e:
            probe2.append({"symbol": sym, "status": f"ERROR {type(e).__name__}"})
    OUT["probe2_delisted_ohlcv"] = probe2

    # ---- Probe 3: IDX disclosure reachability (one request, no bypass) ----
    probe3 = {"endpoint": "https://www.idx.co.id/primary/Announcement/GetAnnouncement",
              "method": "single unauthenticated GET, browser UA, 5s timeout"}
    try:
        r = requests.get(
            probe3["endpoint"],
            params={"start": 0, "length": 1, "language": "en-us"},
            headers={"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/126.0 Safari/537.36")},
            timeout=5)
        probe3["http_status"] = int(r.status_code)
        probe3["content_type"] = r.headers.get("content-type", "")
        probe3["body_prefix"] = r.text[:120]
    except Exception as e:
        probe3["http_status"] = None
        probe3["error"] = f"{type(e).__name__} (source flagged blocked; dropped)"
    OUT["probe3_idx_disclosure"] = probe3

    OUT["generated_utc"] = t0
    print(json.dumps(OUT, indent=1, default=str))


if __name__ == "__main__":
    main()
