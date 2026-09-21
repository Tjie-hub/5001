"""FWD-PM-FADE-001 daily signal recorder.

Mirrors forward_regime/run_formation.py: read-only against the production DB
(`data.db.connect(read_only=True)`), run daily after the settled-bar write,
append-only ledger, never back-fills — a signal whose signal_date predates the
ledger's `opened_utc` is refused, because replaying the in-sample panel into
this ledger would convert discovery into an apparent forward record.

Ledger discipline (ledger.json `_comment` / PROTOCOL.md §2): one object per
signal, written when its h=20 leg closes.  A signal whose h=20 window has not
closed yet — or whose benchmark legs are not yet complete — is DEFERRED, not
written (the exact analogue of run_formation's "still open" trades).  Rows
with `censored: true` are a study-end close-out operation and are never
produced by this daily recorder.

Contamination guard (PROTOCOL.md §2, the panel.py `bad`/`badh` convention
reused verbatim from the frozen in-sample script): a signal is VOIDED — not
written at all — if any session in [signal+1 .. signal+20] has |ret| > 35% or
a recorded split.  Because the h-windows nest ([i+1..i+5] ⊆ [i+1..i+20]), a
row that passes the h=20 guard has clean 5/10 legs by construction.

Benchmarks, dual and both required per signal (PROTOCOL.md §2): IHSG on the
identical next-open / h-close convention; the equal-weight liquid book = the
per-(date, h) mean forward return of every liq-eligible row under the same
convention.  A partial row is never written.

Signal computation, constants and conventions are reused verbatim from
scripts/fade_failed_breakdown.py (SHA256SUMS-pinned 2026-09-21); this file
adds ONLY the ledger / append / back-fill layer.  It does not modify
PROTOCOL.md, the frozen script, or any other ledger.
"""
import json, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data.db import connect                      # the one sanctioned connection path

HERE = Path(__file__).parent
LEDGER = HERE / "ledger.json"

# ---- frozen constants (PROTOCOL.md section 2 / scripts/fade_failed_breakdown.py) ----
ADV_THRESH = 1e9        # liquid gate: 20-session ADV (Rp)
PRICE_FLOOR = 50        # Rp
MIN_SESSIONS = 25       # minimum prior sessions traded (warm-up)
LOOKBACK = 20           # Donchian-style trailing-low lookback (calendar sessions)
GUARD_WINDOW = 20
GUARD_MIN_TRADED = 18   # of trailing 20 sessions must have volume > 0
HORIZONS = (5, 10, 20)  # holding periods, sessions
COST = 0.006            # 0.60% round trip, the repo cost authority
CONTAM_MOVE = 0.35      # any single-session |return| beyond this inside the
                        # holding window voids that signal (split/suspension guard)


def load(conn):
    d = pd.read_sql(
        "SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
        "WHERE is_final=1 AND close>0 AND volume>=0 AND ticker!='IHSG'", conn)
    ca = pd.read_sql("SELECT ticker,date,action FROM corporate_actions", conn)
    ihsg = pd.read_sql(
        "SELECT date,open,close FROM ohlcv WHERE ticker='IHSG' AND is_final=1", conn)
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    ihsg["date"] = pd.to_datetime(ihsg["date"])
    ihsg = ihsg.sort_values("date").set_index("date")
    splits = ca[ca.action == "split"][["ticker", "date"]].copy()
    splits["date"] = pd.to_datetime(splits["date"])
    splits["is_split"] = 1
    return d, splits, ihsg


def build(d, splits):
    # verbatim from scripts/fade_failed_breakdown.py (frozen 2026-09-20 v1)
    g = d.groupby("ticker", sort=False)
    d["ret"] = g["close"].pct_change()
    d["n"] = g.cumcount()
    dval = d.close * d.volume
    d["adv20"] = dval.groupby(d.ticker).transform(
        lambda s: s.rolling(20, min_periods=15).mean())
    d["adv20"] = d.groupby("ticker", sort=False)["adv20"].shift(1)
    d["lo20"] = g["low"].transform(
        lambda s: s.rolling(LOOKBACK, min_periods=LOOKBACK).min()).groupby(d.ticker).shift(1)
    nz = (d.volume > 0).astype(int)
    d["nz20"] = nz.groupby(d.ticker).transform(
        lambda s: s.shift(1).rolling(GUARD_WINDOW, min_periods=GUARD_WINDOW).sum())
    d = d.merge(splits, on=["ticker", "date"], how="left")
    d["is_split"] = d["is_split"].fillna(0)
    d["bad"] = ((d.ret.abs() > CONTAM_MOVE) | (d.is_split > 0)).astype(int)
    d["liq"] = ((d.adv20 >= ADV_THRESH) & (d.close >= PRICE_FLOOR) &
                (d.n >= MIN_SESSIONS) & (d.volume > 0) & (d.nz20 >= GUARD_MIN_TRADED)
                ).fillna(False).astype(bool)
    # next-session open/date -- the tradeable entry (signal close is not fillable)
    g = d.groupby("ticker", sort=False)
    d["entry_open"] = g["open"].shift(-1)
    d["entry_date"] = g["date"].shift(-1)
    for h in HORIZONS:
        d[f"exit_close_{h}"] = g["close"].shift(-h)
        d[f"exit_date_{h}"] = g["date"].shift(-h)
        # contamination anywhere in [signal+1 .. signal+h]
        d[f"bad_{h}"] = g["bad"].transform(
            lambda s: s.shift(-1).rolling(h, min_periods=1).sum())
        # equal-weight liquid-book forward return under the SAME entry/exit
        # convention (next-open in, h-session close out), for the fair
        # (non-IHSG) benchmark -- computed on every liquid row, not just signals
        d[f"fwd_open_{h}"] = np.where(
            d.liq, d[f"exit_close_{h}"] / d.entry_open - 1, np.nan)
    return d


def horizon_legs(r, ihsg_open, ihsg_close, ewb):
    """All three horizon legs with both benchmarks, or None if any required
    leg is missing (the signal is then deferred — a partial row is never
    written, because the ledger is append-only and could not be repaired)."""
    legs = {}
    for h in HORIZONS:
        ec = getattr(r, f"exit_close_{h}")
        ed = getattr(r, f"exit_date_{h}")
        if pd.isna(ec) or pd.isna(ed) or pd.isna(r.entry_open):
            return None
        ih_o = ihsg_open.get(pd.Timestamp(r.entry_date))
        ih_c = ihsg_close.get(pd.Timestamp(ed))
        ew = ewb[h].get(pd.Timestamp(r.date), np.nan)
        if pd.isna(ih_o) or pd.isna(ih_c) or pd.isna(ew):
            return None
        gross = ec / r.entry_open - 1.0
        net = gross - COST
        ih = ih_c / ih_o - 1.0
        legs[str(h)] = {
            "exit_date": str(pd.Timestamp(ed).date()),
            "exit_close": float(ec),
            "gross_return": round(float(gross), 6),
            "net_return": round(float(net), 6),
            "ihsg_return": round(float(ih), 6),
            "excess_ihsg": round(float(net - ih), 6),
            "ewbook_return": round(float(ew), 6),
            "excess_ewbook": round(float(net - ew), 6),
        }
    return legs


def main():
    led = json.loads(LEDGER.read_text())
    if not led.get("opened_utc"):
        sys.exit("ledger not opened: opened_utc is null. Set it and `family` before running.")
    opened = pd.Timestamp(led["opened_utc"][:10])
    with connect(read_only=True) as conn:
        d, splits, ihsg = load(conn)
    d = build(d, splits)

    sig = d[d.liq & (d.low < d.lo20) & (d.close > d.lo20) & d.entry_open.notna()]
    sig_dates = pd.to_datetime(sig["date"])
    refused = int((sig_dates < opened).sum())          # never back-fill
    sig = sig[sig_dates >= opened]

    ihsg_open, ihsg_close = ihsg["open"], ihsg["close"]
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in HORIZONS}
    have = {(t["ticker"], t["signal_date"]) for t in led["trades"]}

    new, pending, voided = [], [], 0
    for r in sig.itertuples(index=False):
        key = (r.ticker, str(pd.Timestamp(r.date).date()))
        if key in have:
            continue
        b20 = getattr(r, "bad_20")
        if pd.isna(r.exit_close_20) or pd.isna(r.exit_date_20) or pd.isna(b20):
            pending.append(r.date)                     # h=20 window still open
            continue
        if b20 != 0:
            voided += 1                                # contamination guard
            continue
        legs = horizon_legs(r, ihsg_open, ihsg_close, ewb)
        if legs is None:
            pending.append(r.date)                     # benchmark leg incomplete
            continue
        new.append(dict(
            ticker=r.ticker, signal_date=key[1],
            entry_date=str(pd.Timestamp(r.entry_date).date()),
            entry_open=float(r.entry_open),
            horizons=legs, censored=False,
            generated_utc=datetime.now(timezone.utc).isoformat()))

    print(f"back-fill guard: refused {refused} pre-opened signals "
          f"(opened {opened.date()})")
    print(f"voided (contamination): {voided}")
    if pending:
        ps = pd.to_datetime(sorted(pending))
        print(f"pending: {len(ps)} signals on {ps.normalize().nunique()} dates "
              f"({ps[0].date()} .. {ps[-1].date()}) awaiting h=20 close / "
              f"benchmark completion")
    if not new:
        print("no new closed signals")
        return
    led["trades"].extend(sorted(new, key=lambda t: (t["signal_date"], t["ticker"])))
    body = json.dumps(led["trades"], sort_keys=True).encode()
    led["fingerprint_sha256"] = hashlib.sha256(body).hexdigest()
    led["last_append_utc"] = datetime.now(timezone.utc).isoformat()
    LEDGER.write_text(json.dumps(led, indent=2))
    print(f"appended {len(new)} closed signals; total {len(led['trades'])}; "
          f"fingerprint {led['fingerprint_sha256'][:12]}…")


if __name__ == "__main__":
    main()
