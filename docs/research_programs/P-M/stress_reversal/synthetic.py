"""Synthetic in-memory market for the stress-reversal PIT tests and the
g1_run --synthetic dry run. No real data, no outcomes — fixtures only.

Design (E2-style, 160 sessions from 2023-08-01; closes CUMULATE so each
name's day-t return equals its engineered daily return exactly):
- F01..F39 (+ARB0/B15/DIVX at VOL, SPLIT at VOL_SPLIT): identical returns -> r_m equals that return: +0.1% ordinary days,
  -3.0% on sessions 150 and 156 (6 apart => TWO episodes), -0.8% on session
  153 (a near-miss: multiple sits inside [-3.0, -2.0] sigma, not flagged).
- B15: ret_t = 1.5 x r_m,t exactly -> beta_for recovers beta = 1.5 (test (d)).
- ARB0: liquid, volume 0 on session 150, worst day-t return -> excluded from
  the basket (test (c)).
- DIVX: IDR dividend (3) with EX-date on session 150: close nets the dividend
  out so the add-back restores exactly -3% (test (e)); the prior session has
  no add-back.
- SPLIT: stocksplit 1:5 ex-date on session 150 -> day-t return dropped from
  the market and basket there (E2 raw-bar guard); its bars BEFORE the split
  have f_cum = 5 (ADV correction test).
"""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

VOL = 5.0e8                 # members: ADV 5e10, liquid on both ADV definitions
VOL_SPLIT = 5.0e7           # SPLIT: naive ADV 5e9 < 10bn; true ADV (x f=5) 2.5e10 >= 10bn
STRESS_RET = -0.03
NEAR_RET = -0.0072
CYCLE = (0.002, -0.001, 0.003, -0.002, 0.001, -0.003)   # sd ~0.2%: sigma is healthy
S1, S2, NM = 150, 156, 153
DIV = 3.0


def _mkt_ret(i: int) -> float:
    if i in (S1, S2):
        return STRESS_RET
    if i == NM:
        return NEAR_RET
    return CYCLE[i % len(CYCLE)]


def make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY, ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, is_final INTEGER)")
    conn.execute("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT, event_id TEXT, event_date TEXT, raw_json TEXT, fetch_date TEXT, updated_at TEXT)")
    idx = pd.bdate_range("2023-08-01", periods=160)
    dates = [d.strftime("%Y-%m-%d") for d in idx]

    rows = []
    # F01..F39 + ARB0 + B15: cumulative closes
    mkt_close = 100.0
    b15_close = 100.0
    for i in range(len(dates)):
        r = _mkt_ret(i)
        mkt_close *= 1.0 + r
        b15_close *= 1.0 + 1.5 * r
        for k in range(39):
            rows.append((f"F{k:02d}", dates[i], mkt_close, mkt_close, mkt_close, mkt_close, VOL, 1))
        rows.append(("ARB0", dates[i], mkt_close * 0.99, mkt_close, mkt_close * 0.98,
                     mkt_close * ((1.0 + r - 0.02) if i == S1 else 1.0),
                     0.0 if i == S1 else VOL, 1))
        rows.append(("B15", dates[i], b15_close, b15_close, b15_close, b15_close, VOL, 1))
    conn.executemany("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    # DIVX: cumulative with the dividend netted out of the ex-date close
    dx = 100.0
    for i in range(len(dates)):
        r = _mkt_ret(i)
        dx *= 1.0 + r
        close = dx - (DIV if i == S1 else 0.0)
        conn.execute("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("DIVX", dates[i], close, close, close, close, VOL, 1))
    # SPLIT: cumulative; the split-day close is already post-split (/5)
    sp = 100.0
    for i in range(len(dates)):
        r = _mkt_ret(i)
        sp *= 1.0 + r
        close = sp / 5.0 if i == S1 else sp
        conn.execute("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("SPLIT", dates[i], close, close, close, close, VOL_SPLIT, 1))

    def ca(tk, at, eid, d, extra):
        payload = {"stocksplit_exdate": d, "stocksplit_cumdate": d,
                   "dividend_exdate": d, "dividend_cumdate": d,
                   "dividend_currency": "CURRENCY_IDR", "dividend_id": eid,
                   "dividend_value": "3"}
        payload.update(extra)
        conn.execute("INSERT INTO corporate_action_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (tk, at, eid, d, json.dumps(payload), d, d))

    ca("DIVX", "dividend", "d1", dates[S1], {})
    ca("SPLIT", "stocksplit", "sp1", dates[S1], {"stocksplit_old": 1, "stocksplit_new": 5})
    conn.commit()
    return conn
