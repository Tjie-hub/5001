"""Fixture market for the tender-offer floor study (tests + --synthetic).

In-memory DB with the ohlcv / corporate_action_events shapes the drivers
expect. PX is the eligible tender target (entry close exactly 100 at session
index 29, exit close 103 at index 34, spread 30%); SP carries a later 1:2
bonus (basis-rule test: raw offer 202 -> adj 101 at entry close 100); GUA
has a rights ex-date inside its window (S9 guard); ZV has zero entry volume
(S5); DV carries three dividends (inside / at-entry / after-exit) for the
add-back test. PX's tender_start/end fall on SATURDAYS (non-session dates).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import tender_floor as TF

N_SESS = 44
E = 32          # entry session index — a FRIDAY (PX close exactly 100.0)
X = 37          # exit session index — the Friday 5 sessions later (close 103.0)


def _sessions(n=N_SESS) -> list[date]:
    out, d = [], date(2025, 1, 1)      # Wednesday
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _sat_after(d: date) -> date:
    return d + timedelta(days=(5 - d.weekday()) % 7 or 7)


def _px_closes() -> list[float]:
    c = [100.0 + 0.3 * ((i % 7) - 3) / 10.0 for i in range(E)]   # wiggle ~ +/-0.15
    c.append(100.0)                                              # index E: entry close
    for i in range(E + 1, X):                                    # ramp to the exit
        c.append(100.0 + (i - E) * 0.75)
    c.append(103.0)                                              # index X: exit close
    while len(c) < N_SESS:
        c.append(103.0)
    return c


def _bx_closes() -> list[float]:
    c = [500.0] * N_SESS
    for i in range(E + 1, X):
        c[i] = 500.0 + (i - E) * 1.25
    c[X] = 505.0
    for i in range(X + 1, N_SESS):
        c[i] = 505.0
    return c


def make_db() -> sqlite3.Connection:
    sess = _sessions()
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL,"
                 " low REAL, close REAL, volume REAL, is_final INTEGER DEFAULT 1)")
    rows = []

    def emit(tk, closes, vol, hl=0.5):
        for i, c in enumerate(closes):
            v = vol(i) if callable(vol) else vol
            rows.append((tk, sess[i].isoformat(), c, c + hl, c - hl, c, v, 1))

    emit("PX", _px_closes(), 5e7)                 # ADV 5e9  (1-10bn tier)
    emit("BX", _bx_closes(), 1e8, hl=1.0)         # ADV 5e10 (book member)
    emit("SP", [100.0] * N_SESS, 1e7)
    emit("GUA", [100.0] * N_SESS, 1e7)
    emit("DV", [200.0] * N_SESS, 1e7)
    emit("ZV", [100.0] * N_SESS, lambda i: 0.0 if i == E else 1e7)
    conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?,?)", rows)

    conn.execute("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT,"
                 " event_id TEXT, event_date TEXT, raw_json TEXT)")
    ca = []

    def tender(tk, eid, price, st, en, pct="22.50"):
        ca.append((tk, "tenderoffer", eid, st.isoformat(), json.dumps({
            "tender_price": str(price), "tender_start": st.isoformat(),
            "tender_end": en.isoformat(), "tender_paydate": en.isoformat(),
            "tender_percentage": pct, "tender_shares": "1000000",
            "tender_created": st.isoformat(), "event_note": ""})))

    px_st, px_en = _sat_after(sess[E]), _sat_after(sess[X])
    tender("PX", "1", 130, px_st, px_en)
    tender("SP", "2", 202, _sat_after(sess[E]), _sat_after(sess[X - 1]))
    tender("GUA", "3", 130, px_st, px_en)
    tender("ZV", "4", 130, px_st, px_en)
    # SP bonus 1:2 with ex-date after the window -> f_cum(entry) = 2
    ca.append(("SP", "bonus", "b1", sess[X + 2].isoformat(), json.dumps({
        "stocksplit_exdate": sess[X + 2].isoformat(), "stocksplit_factor": "2"})))
    # GUA rights ex-date INSIDE (entry, exit]
    ca.append(("GUA", "rightissue", "r1", sess[E + 2].isoformat(), json.dumps({
        "rightissue_exdate": sess[E + 2].isoformat()})))
    # DV dividends: inside / at entry / after exit
    for did, (exd, val) in {"d1": (sess[E + 2], 10.0), "d2": (sess[E], 7.0),
                            "d3": (sess[X + 2], 5.0)}.items():
        ca.append(("DV", "dividend", did, exd.isoformat(), json.dumps({
            "dividend_id": did, "dividend_currency": "CURRENCY_IDR",
            "dividend_value": str(val), "dividend_exdate": exd.isoformat()})))
    conn.executemany("INSERT INTO corporate_action_events VALUES (?,?,?,?,?)", ca)
    return conn


def fixture_events() -> list[dict]:
    return TF.load_tenders(make_db())
