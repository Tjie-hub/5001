#!/usr/bin/env python3
"""Class N signal probe — the brief's ONE permitted network fetch (logged).

Downloads the SIGNAL series only (never IDX outcomes):
  1. Caldara-Iacoviello Geopolitical Risk index (monthly, 1985-) — public CSV,
     matteoiacoviello.com, no auth.
  2. Commodity futures via yfinance (no auth, period=max): GC=F (gold), CL=F
     (WTI), NG=F (natgas), HG=F (copper), NICK.L (nickel ETF proxy), BTU (coal
     equity proxy). Coal INDEX (Newcastle API2) and CPO (FCPO) have no free
     source (broad_search_v2 W2 §2) — not attempted.

Writes raw CSVs + PROBE_LOG_N.json (url, timestamp, sha256, rows, range) and
states the GPR publication lag empirically (file's latest month vs today).
Read-only with respect to the repo's data; no IDX/stock price is downloaded.
"""
import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "probe_n_data"
DATA.mkdir(exist_ok=True)
TICKERS = {"GC=F": "gold", "CL=F": "wti_crude", "NG=F": "natgas",
           "HG=F": "copper", "NICK.L": "nickel_etf_proxy", "BTU": "coal_equity_proxy"}

log = {"probe": "class_N signal series (amendment 1, one-time, no-auth)",
       "utc": datetime.now(timezone.utc).isoformat(), "files": {}, "errors": []}

# ---- GPR (fixed host, fixed path; no eval of remote content beyond the CSV) --
try:
    r = requests.get("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.csv",
                     timeout=60, headers={"User-Agent": "research-probe/1.0"},
                     allow_redirects=False)
    r.raise_for_status()
    raw = r.content
    gpr = pd.read_csv(io.BytesIO(raw))
    month_col = gpr.columns[0]
    gpr = gpr.rename(columns={month_col: "month"})
    last_month = str(gpr["month"].max())
    out = DATA / "data_gpr_export.csv"
    out.write_bytes(raw)
    log["files"]["gpr"] = {
        "url": "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.csv",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rows": int(len(gpr)), "columns": list(gpr.columns),
        "range": [str(gpr["month"].min()), last_month],
        "saved": out.name,
        "pit_lag": f"monthly index; latest month in file = {last_month}; "
                   f"today = {date.today().isoformat()} — the series is published "
                   f"with roughly a one-month lag; a monthly rebalance formed at "
                   f"month-end M can use GPR through M-1 only (verify at G0)",
    }
except Exception as e:
    log["errors"].append(f"gpr: {type(e).__name__}: {e}")

# ---- commodities -----------------------------------------------------------
for sym, name in TICKERS.items():
    try:
        h = yf.Ticker(sym).history(period="max", auto_adjust=False)
        if h is None or h.empty:
            log["errors"].append(f"{sym}: empty")
            continue
        h = h.reset_index()
        h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None)
        p = DATA / f"yf_{sym.replace('=','_').replace('.','_')}.csv"
        h.to_csv(p, index=False)
        log["files"][sym] = {
            "name": name, "rows": int(len(h)),
            "range": [str(h["Date"].min().date()), str(h["Date"].max().date())],
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "saved": p.name,
        }
    except Exception as e:
        log["errors"].append(f"{sym}: {type(e).__name__}: {e}")

log["coal_cpo_note"] = (
    "Newcastle API2 coal index and CPO futures have no free no-auth source "
    "(broad_search_v2 W2 §2: BTU only 2017-04+, KOL/FCPO empty); BTU downloaded "
    "here as the equity proxy for coverage dating only")
(HERE / "PROBE_LOG_N.json").write_text(json.dumps(log, indent=1))
print(json.dumps(log, indent=1)[:3000])
