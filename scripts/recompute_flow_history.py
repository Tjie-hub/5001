"""One-off: recompute pre-2026-10-09 stockbit_flow rows from the stored minute bars.

Until fix 47ff225 the daily row's buy_lot/sell_lot/net_lot/buy_freq/sell_freq were SUMS of the
cumulative trade-book counters and composite_score/verdict/smart_money came from _analyze reading
running totals as per-minute flow (D-089). The bars in stockbit_flow_bars are stored exactly as the
vendor sends them, so the correct row is recomputable: totals = last cumulative value (MAX), labels =
the fixed _analyze. net_value and last_price were always correct and are left alone, as is
updated_at (the row's fetch time).

Rows without bars are left untouched (still old definition; TRADE_BOOK_SEMANTIC_REGISTER_v1).
Before any write the affected rows are copied to --backup (a separate SQLite file).

    python scripts/recompute_flow_history.py                 # dry run: counts + label changes
    python scripts/recompute_flow_history.py --write --backup PATH
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402
from data.db import connect  # noqa: E402
from flow_filter import _analyze  # noqa: E402

FIX_DATE = "2026-10-09"
COLS = ("buy_lot", "sell_lot", "net_lot", "buy_freq", "sell_freq", "composite_score", "verdict", "smart_money")


def _bars(con, ticker, day):
    rows = con.execute(
        "SELECT bar_time, buy_lot, sell_lot, buy_freq, sell_freq, net_value, price, delta "
        "FROM stockbit_flow_bars WHERE ticker=? AND trade_date=? ORDER BY bar_time", (ticker, day)).fetchall()
    return [{"time": r[0], "buy_lot": r[1] or 0, "sell_lot": r[2] or 0, "buy_freq": r[3] or 0,
             "sell_freq": r[4] or 0, "net_value": r[5] or 0, "price": r[6] or 0, "delta": r[7] or 0}
            for r in rows]


def recompute(con, ticker, day):
    bars = _bars(con, ticker, day)
    if not bars:
        return None
    b, s = max(x["buy_lot"] for x in bars), max(x["sell_lot"] for x in bars)
    a = _analyze(ticker, bars) or {}
    return {"buy_lot": b, "sell_lot": s, "net_lot": b - s,
            "buy_freq": max(x["buy_freq"] for x in bars), "sell_freq": max(x["sell_freq"] for x in bars),
            "composite_score": a.get("score"), "verdict": a.get("verdict"), "smart_money": a.get("smart_money")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--backup")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--batch", type=int, default=500)
    args = ap.parse_args()
    if args.write and not args.backup:
        raise SystemExit("--write needs --backup")

    con = connect(DB_PATH)
    keys = con.execute("SELECT ticker, trade_date FROM stockbit_flow WHERE trade_date < ? "
                       "ORDER BY trade_date, ticker", (FIX_DATE,)).fetchall()
    if args.limit:
        keys = keys[:args.limit]
    if args.write:
        bk = sqlite3.connect(args.backup)
        cols = [r[1] for r in con.execute("PRAGMA table_info(stockbit_flow)")]
        bk.execute(f"CREATE TABLE stockbit_flow_pre_d089 ({', '.join(cols)})")
        q = ", ".join("?" * len(cols))
        bk.executemany(f"INSERT INTO stockbit_flow_pre_d089 VALUES ({q})",
                       con.execute(f"SELECT {', '.join(cols)} FROM stockbit_flow WHERE trade_date < ?", (FIX_DATE,)))
        bk.commit()
        n_bk = bk.execute("SELECT COUNT(*) FROM stockbit_flow_pre_d089").fetchone()[0]
        bk.close()
        print(f"backup: {n_bk} rows -> {args.backup}", flush=True)

    st = Counter()
    pending = []
    for i, (t, d) in enumerate(keys, 1):
        old = con.execute(f"SELECT {', '.join(COLS)} FROM stockbit_flow WHERE ticker=? AND trade_date=?",
                          (t, d)).fetchone()
        new = recompute(con, t, d)
        if new is None:
            st["no_bars"] += 1
            continue
        st["recomputed"] += 1
        st["verdict_changed"] += old[6] != new["verdict"]
        st["smart_money_changed"] += old[7] != new["smart_money"]
        pending.append(tuple(new[c] for c in COLS) + (t, d))
        if args.write and len(pending) >= args.batch:
            con.executemany(f"UPDATE stockbit_flow SET {', '.join(c + '=?' for c in COLS)} "
                            "WHERE ticker=? AND trade_date=?", pending)
            con.commit()
            pending = []
        if i % 20000 == 0:
            print(f"{i}/{len(keys)} {dict(st)}", flush=True)
    if args.write and pending:
        con.executemany(f"UPDATE stockbit_flow SET {', '.join(c + '=?' for c in COLS)} "
                        "WHERE ticker=? AND trade_date=?", pending)
        con.commit()
    con.close()
    print(json.dumps({"rows": len(keys), "written": bool(args.write), **st}))


if __name__ == "__main__":
    main()
