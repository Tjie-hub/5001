"""Synthetic in-memory market for the dividend-clientele PIT tests and the
g1_run --synthetic dry run. No real data, no outcomes — fixtures only.

Layout (sessions are business days from 2024-01-01):
- 41 tickers: EVT (the D2-exact event stock), EVT2 (AGM at cum-3 -> short
  window), EVT3 (split ex-date inside the window -> excluded), F01..F38
  fillers. All fillers: close/open 100 flat, volume 2e8 (ADV = 2e10 >= 10bn).
- EVT: cum close 1000 (constant 1000 around cum), ex open 960 -> the D2
  synthetic outcome is exactly -0.001 with a flat book.
- F01 carries a 5-unit dividend with cum at session 30, ex at 31 (add-back
  test). All prices flat, so the add-back is visible in the book return.
"""
from __future__ import annotations

import json
import sqlite3
import pandas as pd

ADV_FILL = 2.0e8   # volume at close 100 -> ADV 2e10


def make_db(f01_div: bool = False, extra_events: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (id INTEGER PRIMARY KEY, ticker TEXT, date TEXT, "
                 "open REAL, high REAL, low REAL, close REAL, volume REAL, is_final INTEGER)")
    conn.execute("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT, "
                 "event_id TEXT, event_date TEXT, raw_json TEXT, fetch_date TEXT, updated_at TEXT)")
    idx = pd.bdate_range("2023-08-01", periods=130)
    dates = [d.strftime("%Y-%m-%d") for d in idx]
    cum_i, ex_i = 110, 111                    # cum 2024-02-13, ex 2024-02-14

    def ins(tk, i, o, h, l, c, v=ADV_FILL):
        conn.execute("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume, is_final) "
                     "VALUES (?,?,?,?,?,?,?,1)", (tk, dates[i], o, h, l, c, v))

    for i in range(len(dates)):
        for k in range(38):
            tk = f"F{k:02d}"
            ins(tk, i, 100, 100, 100, 100)
        # EVT: 1000 everywhere except the ex open 960 (and its day range widened)
        ins("EVT", i, 1000 if i != ex_i else 960, 1000 if i != ex_i else 965,
            1000 if i != ex_i else 955, 1000)
        if extra_events:
            # EVT2/EVT4: flat 1000
            ins("EVT2", i, 1000, 1000, 1000, 1000)
            ins("EVT4", i, 1000, 1000, 1000, 1000)
            # EVT3: flat, carries the in-window split
            ins("EVT3", i, 1000, 1000, 1000, 1000)

    def div_ev(tk, did, val, cum, ex, created):
        conn.execute("INSERT INTO corporate_action_events VALUES (?,?,?,?,?,?,?)",
                     (tk, "dividend", did, ex, json.dumps({
                         "dividend_id": did, "dividend_value": str(val),
                         "dividend_currency": "CURRENCY_IDR",
                         "dividend_cumdate": dates[cum], "dividend_exdate": dates[ex],
                         "dividend_created": dates[created] if created is not None else None,
                         "dividend_paydate": dates[ex]}), dates[ex], dates[ex]))

    div_ev("EVT", "1", 50, cum_i, ex_i, cum_i - 25)     # created early: earlier-of vs rups
    if extra_events:
        div_ev("EVT2", "2", 50, cum_i, ex_i, None)          # no created; gets rups anchor (a)
        div_ev("EVT3", "3", 50, cum_i, ex_i, cum_i - 5)
        div_ev("EVT4", "5", 50, cum_i, ex_i, cum_i - 5)     # created-only anchor, late -> window 4
    if f01_div:
        div_ev("F01", "4", 5, cum_i, ex_i, None)        # add-back test member

    def rups_ev(tk, rid, d_i):
        conn.execute("INSERT INTO corporate_action_events VALUES (?,?,?,?,?,?,?)",
                     (tk, "rups", rid, dates[d_i], json.dumps({
                         "rups_id": rid, "rups_date": dates[d_i]}), dates[d_i], dates[d_i]))

    rups_ev("EVT", "r2", cum_i - 20)    # both anchors exist; created (cum-25) wins
    if extra_events:
        rups_ev("EVT2", "r1", cum_i - 3)    # AGM at cum-3 sessions -> window 2 -> dropped

        # EVT3 carries a split whose ex-date is inside the event window -> excluded
        conn.execute("INSERT INTO corporate_action_events VALUES (?,?,?,?,?,?,?)",
                     ("EVT3", "stocksplit", "s1", dates[ex_i + 1], json.dumps({
                         "stocksplit_id": "s1", "stocksplit_exdate": dates[ex_i + 1],
                         "stocksplit_cumdate": dates[cum_i]}), dates[cum_i], dates[cum_i]))
    conn.commit()
    return conn


if __name__ == "__main__":
    c = make_db()
    print(c.execute("SELECT COUNT(*) FROM ohlcv").fetchone())
