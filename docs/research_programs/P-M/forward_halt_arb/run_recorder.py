"""FWD-PM-HALTARB-001 daily recorder (PROTOCOL.md, D-100).

Read-only against the production DB, run each morning after the settled-bar write. For every IHSG halt-threshold
day D on or after the ledger's opening (never back-filled; 2026-10-16, the motivating case, is refused), it writes
one row per liquid ARB-touch name once that name's t+5 leg has closed, plus one row per event day. Nobody reads
the outcome fields before 20 event days (PROTOCOL.md section 5).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data.db import connect  # the one sanctioned connection path

HERE = Path(__file__).parent
LEDGER = HERE / "ledger.json"

# ---- frozen (PROTOCOL.md sections 2-4) ----
HALT_MOVE = -0.08          # IHSG low vs prior close
ARB_PCT = 0.15
ADV_MIN = 1e9              # Rp, mean close*volume over the 20 sessions before D
PRICE_FLOOR = 50
H = 5                      # sessions
CONTAM_MOVE = 0.35
EXCLUDED = {"2026-10-16"}  # the case that suggested the idea


def tick(price):
    return 1 if price < 200 else 2 if price < 500 else 5 if price < 2000 else 10 if price < 5000 else 25


def arb_price(prev_close):
    raw = prev_close * (1 - ARB_PCT)
    t = tick(raw)
    return math.ceil(raw / t - 1e-9) * t


def event_days(ihsg):
    """ihsg: [(date, low, close)] oldest first -> [(date, low_chg, close_chg)] with low_chg <= HALT_MOVE."""
    out = []
    for (d0, _, c0), (d, lo, c) in zip(ihsg, ihsg[1:]):
        if c0 and lo / c0 - 1 <= HALT_MOVE:
            out.append((d, round(lo / c0 - 1, 4), round(c / c0 - 1, 4)))
    return out


def legs(bars, i):
    """bars: [(date, open, high, low, close, volume)] of one ticker; i = index of D. Returns closes or None."""
    if i + H >= len(bars):
        return None
    return {"close_d": bars[i][4], "close_t1": bars[i + 1][4], "close_t5": bars[i + H][4]}


def void_reason(bars, i):
    """A session |return| > CONTAM_MOVE inside D..t+5 (an unadjusted split shows up as one)."""
    for k in range(i, i + H + 1):
        if k and bars[k - 1][4] and abs(bars[k][4] / bars[k - 1][4] - 1) > CONTAM_MOVE:
            return f"|ret| > {CONTAM_MOVE:.0%} on {bars[k][0]}"
    return None


def load_ledger():
    return json.loads(LEDGER.read_text())


def record(conn, ledger):
    opened = ledger["opened_utc"][:10]
    done_days = {e["date"] for e in ledger["event_days"]}
    done_rows = {(r["date"], r["ticker"]) for r in ledger["rows"]}
    ihsg = conn.execute("SELECT date, low, close FROM ohlcv WHERE ticker='IHSG' AND is_final=1 AND close>0 "
                        "ORDER BY date").fetchall()
    days = [e for e in event_days(ihsg) if e[0] >= opened and e[0] not in EXCLUDED]
    added = 0
    for d, lo_chg, cl_chg in days:
        names = conn.execute("SELECT DISTINCT ticker FROM ohlcv WHERE date=? AND is_final=1 AND ticker!='IHSG'",
                             (d,)).fetchall()
        rows, bench = [], []
        for (t,) in names:
            bars = conn.execute("SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker=? AND "
                                "is_final=1 AND close>0 ORDER BY date", (t,)).fetchall()
            idx = {b[0]: k for k, b in enumerate(bars)}
            i = idx.get(d)
            if i is None or i < 21:
                continue
            prev = bars[i - 1][4]
            adv = sum(b[4] * (b[5] or 0) for b in bars[i - 20:i]) / 20
            if prev < PRICE_FLOOR or adv < ADV_MIN:
                continue
            lg = legs(bars, i)
            if lg is None:
                continue  # t+5 not closed yet: deferred, not written
            bench.append(lg)
            arb = arb_price(prev)
            if bars[i][3] <= arb:
                rows.append((t, prev, arb, bars[i][3], lg, void_reason(bars, i)))
        if not bench:
            continue  # nothing matured yet for this day
        mean = lambda xs: sum(xs) / len(xs) if xs else None
        b_t1 = mean([x["close_t1"] / x["close_d"] - 1 for x in bench])
        b_t5 = mean([x["close_t5"] / x["close_d"] - 1 for x in bench])
        if d not in done_days:
            ledger["event_days"].append({"date": d, "ihsg_low_chg": lo_chg, "ihsg_close_chg": cl_chg,
                                         "n_liquid": len(bench), "n_arb_touch": len(rows),
                                         "bench_ew_close_t1": b_t1, "bench_ew_close_t5": b_t5})
        for t, prev, arb, low, lg, void in rows:
            if (d, t) in done_rows:
                continue
            ledger["rows"].append({
                "date": d, "ticker": t, "prev_close": prev, "entry_arb": arb, "low": low, **lg,
                "ret_arb_close": lg["close_d"] / arb - 1, "ret_arb_t1": lg["close_t1"] / arb - 1,
                "ret_arb_t5": lg["close_t5"] / arb - 1, "ret_close_t1": lg["close_t1"] / lg["close_d"] - 1,
                "ret_close_t5": lg["close_t5"] / lg["close_d"] - 1, "void": bool(void), "void_reason": void})
            added += 1
    return added


if __name__ == "__main__":
    ledger = load_ledger()
    conn = connect(read_only=True)
    try:
        n = record(conn, ledger)
    finally:
        conn.close()
    LEDGER.write_text(json.dumps(ledger, indent=1))
    print(f"FWD-PM-HALTARB-001: +{n} rows; {len(ledger['event_days'])} event days of the 20 needed before any read")
