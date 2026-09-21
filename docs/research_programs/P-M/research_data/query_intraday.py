#!/usr/bin/env python3
"""Read-only accessor for the frozen 1-minute flow-bar store (view E).

The frozen v002 store is NOT copied into views_v1.sqlite (77.5M rows; SQLite
cannot persist a cross-database view). Use this helper instead: it verifies the
frozen file's sha256 against the MANIFEST pin BEFORE opening, opens read-only,
and exposes sequence queries. Fails closed on any identity mismatch.

The session query takes bound parameters only; nothing user-supplied is ever
interpolated into statement text.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
V002 = os.path.normpath(os.path.join(
    HERE, "..", "..", "..", "..", "data", "frozen",
    "stockbit-flow-bars-v002", "stockbit-flow-bars-v002.db"))
MANIFEST = os.path.join(os.path.dirname(V002), "MANIFEST.json")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def connect(verify_sha: bool = True) -> sqlite3.Connection:
    """Open the frozen store read-only after verifying its recorded sha256."""
    if verify_sha:
        recorded = json.load(open(MANIFEST))["database"]["sha256"]
        actual = sha256_file(V002)
        if actual != recorded:
            raise SystemExit("ABORT: frozen flow-bars sha mismatch — refuse to "
                             "serve (see MANIFEST.json pin)")
    c = sqlite3.connect(Path(V002).as_uri() + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def session_sequence(ticker: str, session: str) -> list[dict]:
    """Full 1-minute sequence for one ticker-session (PIT: same-session facts)."""
    c = connect()
    try:
        rows = c.execute("SELECT bar_time, buy_lot, sell_lot, net_value, price, delta FROM stockbit_flow_bars WHERE ticker=? AND trade_date=? ORDER BY bar_time", (ticker, session)).fetchall()  # noqa: E501 — bound parameters only
    finally:
        c.close()
    return [dict(zip(("bar_time", "buy_lot", "sell_lot", "net_value",
                      "price", "delta"), r)) for r in rows]


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit("usage: query_intraday.py <TICKER> <YYYY-MM-DD>")
    rows = session_sequence(sys.argv[1], sys.argv[2])
    print(f"{len(rows)} minute bars for {sys.argv[1]} {sys.argv[2]}")
    sample = rows[:3] + ([{"ellipsis": "…"}] if len(rows) > 6 else []) + rows[-3:]
    for r in sample:
        print(" ", r)
