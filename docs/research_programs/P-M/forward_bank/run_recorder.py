"""FWD-PM-BANK-001 daily recorder (HYP-PM-0014, P-M Price-Reversal {R1,R2}).

Mirrors forward_fade/run_recorder.py: read-only against the production DB
(`data.db.connect(read_only=True)`), run daily after the settled-bar write, append-only
ledger, never back-fills -- an event whose signal_date predates the ledger's `opened_utc`
is refused, because replaying history into this ledger would turn the 2026-09-25 discovery
into an apparent forward record.

Signal (PROTOCOL.md §2, identical to the study and jurnal26/bank_alert.py): close_t is the
lowest close of the last 20 sessions AND close_t <= SMA20_t - 2*ATR14_t; a firing within 10
sessions of the previous firing of the same name is the same event. Entry = open t+1,
exit = close t+10.

An event is written only when its 10-session window has closed and every leg is present
(the ledger is append-only and could not be repaired). It is VOIDED -- not written -- if the
window holds a session with |ret| > 35%, a split, or a rights/bonus/reverse-split event
(price steps that are not returns). Benchmarks: the equal-weight liquid book (ADV20 >= Rp 10 B,
same next-open/h-close convention) and IHSG.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data.db import connect                      # the one sanctioned connection path

HERE = Path(__file__).parent
LEDGER = HERE / "ledger.json"

# ---- frozen constants (PROTOCOL.md §2) ----
TICKERS = ("BBCA", "BBRI", "BMRI", "BBNI")        # BBCA = primary
LOW_N, SMA_N, ATR_N, K_ATR = 20, 20, 14, 2.0
DEDUP = 10
H = 10
COST = 0.006                                      # 0.60% round trip, the repo cost authority
BOOK_ADV = 10e9
CONTAM_MOVE = 0.35
PRICE_STEP_EVENTS = ("stocksplit", "stock_reverse", "rightissue", "bonus")


def signal_index(close, high, low):
    """Positions i (0-based) where the frozen rule fires, after 10-session de-dup. Pure."""
    c, h, l = (np.asarray(x, dtype=float) for x in (close, high, low))
    out, last = [], -10 ** 9
    for i in range(max(LOW_N, ATR_N + 1) - 1, len(c)):
        win = c[i - LOW_N + 1:i + 1]
        tr = [max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1])) for j in range(i - ATR_N + 1, i + 1)]
        atr = sum(tr) / ATR_N
        sma = c[i - SMA_N + 1:i + 1].mean()
        if c[i] <= win.min() and c[i] <= sma - K_ATR * atr and i - last >= DEDUP:
            out.append(i)
            last = i
    return out


def event_row(ticker, dates, opens, closes, i, book, ihsg, void_dates):
    """The ledger row for a firing at position i, or a status string ('pending'/'void'). Pure."""
    if i + H >= len(closes):
        return "pending"
    window = dates[i + 1:i + H + 1]
    rets = np.diff(np.asarray(closes[i:i + H + 1], dtype=float)) / np.asarray(closes[i:i + H], dtype=float)
    if np.any(np.abs(rets) > CONTAM_MOVE) or any(d in void_dates for d in window):
        return "void"
    sd, ed, xd = dates[i], dates[i + 1], dates[i + H]
    bk, ih_o, ih_c = book.get(sd), ihsg.get(("open", ed)), ihsg.get(("close", xd))
    if bk is None or ih_o is None or ih_c is None or np.isnan(bk):
        return "pending"
    gross = closes[i + H] / opens[i + 1] - 1.0
    net = gross - COST
    ih = ih_c / ih_o - 1.0
    return {"ticker": ticker, "signal_date": sd, "entry_date": ed, "entry_open": float(opens[i + 1]),
            "exit_date": xd, "exit_close": float(closes[i + H]),
            "gross_return": round(float(gross), 6), "net_return": round(float(net), 6),
            "ewbook_return": round(float(bk), 6), "excess_ewbook": round(float(net - bk), 6),
            "ihsg_return": round(float(ih), 6), "excess_ihsg": round(float(net - ih), 6),
            "primary": ticker == "BBCA", "censored": False,
            "generated_utc": datetime.now(timezone.utc).isoformat()}


def load(conn):
    d = pd.read_sql("SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                    "WHERE is_final = 1 AND close > 0", conn)
    ihsg = d[d.ticker == "IHSG"].set_index("date")
    d = d[d.ticker != "IHSG"].sort_values(["ticker", "date"])
    # Equal-weight liquid book: next-open in, close h sessions later out, per signal date.
    g = d.groupby("ticker", sort=False)
    adv = (d.close * d.volume).groupby(d.ticker).transform(lambda s: s.rolling(20, min_periods=15).mean().shift(1))
    fwd = g["close"].shift(-H) / g["open"].shift(-1) - 1
    book = fwd[adv >= BOOK_ADV].groupby(d.loc[adv >= BOOK_ADV, "date"]).mean().to_dict()
    ih = {("open", k): v for k, v in ihsg["open"].items()}
    ih.update({("close", k): v for k, v in ihsg["close"].items()})
    ca = pd.read_sql("SELECT ticker, event_date FROM corporate_action_events WHERE action_type IN (%s)"
                     % ",".join("?" * len(PRICE_STEP_EVENTS)), conn, params=PRICE_STEP_EVENTS)
    sp = pd.read_sql("SELECT ticker, date AS event_date FROM corporate_actions WHERE action = 'split'", conn)
    voids = pd.concat([ca, sp]).dropna()
    return d, book, ih, {t: set(v.event_date) for t, v in voids.groupby("ticker")}


def main():
    led = json.loads(LEDGER.read_text())
    if not led.get("opened_utc"):
        sys.exit("ledger not opened: opened_utc is null.")
    opened = led["opened_utc"][:10]
    with connect(read_only=True) as conn:
        d, book, ihsg, voids = load(conn)
    have = {(t["ticker"], t["signal_date"]) for t in led["trades"]}
    new, pending, voided, refused = [], 0, 0, 0
    for t in TICKERS:
        x = d[d.ticker == t]
        dates, opens, closes = list(x.date), list(x.open), list(x.close)
        for i in signal_index(x.close, x.high, x.low):
            if dates[i] < opened:
                refused += 1                               # never back-fill
                continue
            if (t, dates[i]) in have:
                continue
            row = event_row(t, dates, opens, closes, i, book, ihsg, voids.get(t, set()))
            if row == "pending":
                pending += 1
            elif row == "void":
                voided += 1
            else:
                new.append(row)
    print(f"back-fill guard: refused {refused} pre-opened events (opened {opened}); "
          f"voided {voided}; pending {pending}")
    if not new:
        print("no new closed events")
        return
    led["trades"].extend(sorted(new, key=lambda r: (r["signal_date"], r["ticker"])))
    led["fingerprint_sha256"] = hashlib.sha256(json.dumps(led["trades"], sort_keys=True).encode()).hexdigest()
    led["last_append_utc"] = datetime.now(timezone.utc).isoformat()
    LEDGER.write_text(json.dumps(led, indent=2))
    print(f"appended {len(new)}; total {len(led['trades'])}")


if __name__ == "__main__":
    main()
