#!/usr/bin/env python3
"""Repair OHLCV bars stranded at is_final=0 on a past session.

WHY THIS EXISTS (2026-09-16)
----------------------------
`screener/idx_scraper.save_ohlcv_to_db` writes PROVISIONAL bars (is_final=0)
on intraday runs and FINAL bars (is_final=1) on the 16:15 EOD run — the
scraper is the EOD authority for the current day. When that EOD run does not
complete, the intraday bars stay provisional FOREVER: nothing re-finalises a
past session. `data/fetcher.py` (yfinance, the settled-history authority)
cannot heal them either, because its upsert carries
`WHERE ohlcv.close IS NULL` — a guard that exists so yfinance never clobbers
an authoritative scraper bar, and which also blocks it from replacing a
stranded provisional one.

Every research query filters `is_final=1` (`data/loaders.py`,
`sprint_lib.load_ohlcv`, the discovery harness), so a stranded session is
invisible to research: 2026-09-07 showed 137 of 915 tickers. Five such
sessions existed when this was written; none had ever raised an alert.

The provisional bars are NOT merely incomplete — they are scraper-derived and
differ from settled data in open and volume (measured on 2026-09-07: ASII open
4830 vs 4770, ADRO volume +12%). So they are REPLACED with settled yfinance
data, never just re-flagged.

THE SPLIT-BASIS TRAP (why this script does not write yfinance prices directly)
-----------------------------------------------------------------------------
`ohlcv` is a RAW, as-traded store — the whole `build_adjusted` applied-basis
detector in the research harness exists because of that. yfinance back-adjusts
OHLC for splits even with `auto_adjust=False`. So for any ticker that split
AFTER a stranded session, yfinance's historical price is on a different basis
than the table it is being written into. Measured on the 2026-07-08 session:
MLPT stored 18,000 vs yfinance 716 (25:1 split, ex 2026-07-21), RAJA 4,100 vs
784 (5:1, ex 07-16), RMKE 2,130 vs 444 (5:1, ex 07-17). Writing those would
silently put six dates on a split-adjusted basis inside a raw store — worse
than the gap being repaired.

So the basis is derived EMPIRICALLY, per ticker, and never trusted from a
corporate-actions table (the two such tables disagree: `corporate_actions`
holds none of the 2026-07 splits that `corporate_action_events` records).
For each ticker we take reference sessions either side of the gap that are
already `is_final=1`, compute `factor = stored_close / yfinance_close` on each,
and require the two to agree. That factor converts yfinance's adjusted price
back to the table's own raw basis, whatever that basis happens to be.

SAFETY
------
* Only touches rows where `COALESCE(is_final,1) <> 1`. An authoritative
  is_final=1 bar is never read for writing, only as a basis reference.
* Never touches the current WIB day (those bars are legitimately provisional).
* Dry-run by default; `--apply` is required to write.
* A ticker with no settled data, no usable reference session, or disagreeing
  reference factors is LEFT PROVISIONAL and reported — never repaired on a
  guessed basis.

Usage
-----
    python3 scripts/repair_provisional_bars.py                # dry run
    python3 scripts/repair_provisional_bars.py --apply        # write
    python3 scripts/repair_provisional_bars.py --date 2026-09-07 --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import connect as db_connect  # noqa: E402

WIB = ZoneInfo("Asia/Jakarta")
# A close differing this much from the stored provisional bar is reported
# loudly — it means research had a materially wrong price, not a rounding gap.
MATERIAL_CLOSE_DELTA = 0.005
# Two reference sessions must imply the same raw/adjusted basis factor within
# this tolerance, else the ticker is skipped rather than repaired on a guess.
FACTOR_AGREEMENT = 0.01
# How many sessions either side of the gap to search for a reference bar.
REF_SPAN = 6


def wib_today() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d")


def find_stranded(conn, only_date: str | None) -> dict[str, list[str]]:
    """{date: [ticker, ...]} for past sessions holding provisional bars."""
    q = ("SELECT date, ticker FROM ohlcv "
         "WHERE COALESCE(is_final,1) <> 1 AND date < ? ")
    args = [wib_today()]
    if only_date:
        q += "AND date = ? "
        args.append(only_date)
    q += "ORDER BY date, ticker"
    out: dict[str, list[str]] = defaultdict(list)
    for d, t in conn.execute(q, args):
        out[d].append(t)
    return dict(out)


def fetch_window(tickers: list[str], date: str) -> dict[str, dict[str, dict]]:
    """{ticker: {date: {open,high,low,close,volume}}} spanning +/- REF_SPAN
    calendar days around `date` — the extra days are the basis references."""
    import warnings
    warnings.filterwarnings("ignore")
    import pandas as pd
    import yfinance as yf

    d0 = datetime.strptime(date, "%Y-%m-%d")
    start = (d0 - timedelta(days=REF_SPAN * 2)).strftime("%Y-%m-%d")
    end = (d0 + timedelta(days=REF_SPAN * 2)).strftime("%Y-%m-%d")
    symbols = [t + ".JK" for t in tickers]
    out: dict[str, dict[str, dict]] = {}
    CHUNK = 200
    for i in range(0, len(symbols), CHUNK):
        part = symbols[i:i + CHUNK]
        try:
            df = yf.download(part, start=start, end=end, auto_adjust=False,
                             progress=False, group_by="ticker", threads=True)
        except Exception as e:  # network/vendor failure -> repair nothing
            print(f"    [warn] download failed for chunk {i // CHUNK}: {e}")
            continue
        if df is None or df.empty:
            continue
        for sym in part:
            tk = sym[:-3]
            try:
                # yfinance returns MultiIndex columns with group_by="ticker"
                # even for a single symbol, so keying on len(part) is not safe
                # (it silently skipped the lone BRIS bar on 2026-07-22).
                if isinstance(df.columns, pd.MultiIndex):
                    sub = df[sym] if sym in df.columns.get_level_values(0) else df.xs(
                        sym, axis=1, level=-1, drop_level=True)
                else:
                    sub = df
                sub = sub.dropna(subset=["Close"])
                if sub.empty:
                    continue
                bars = {}
                for ts, row in sub.iterrows():
                    c = float(row["Close"])
                    if c > 0:
                        bars[str(ts)[:10]] = {
                            "open": float(row["Open"]), "high": float(row["High"]),
                            "low": float(row["Low"]), "close": c,
                            "volume": float(row["Volume"])}
                if bars:
                    out[tk] = bars
            except Exception:
                continue
    return out


def basis_factor(conn, ticker: str, date: str, bars: dict[str, dict]):
    """stored_raw / yfinance_adjusted, derived from settled reference sessions.

    Returns (factor, n_refs) or (None, reason). Two independent references must
    agree within FACTOR_AGREEMENT, otherwise we refuse to guess a basis.
    """
    refs = conn.execute(
        "SELECT date, close FROM ohlcv WHERE ticker=? AND is_final=1 "
        "AND date BETWEEN ? AND ? AND date<>? AND close>0 ORDER BY date",
        (ticker,
         (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=REF_SPAN * 2)).strftime("%Y-%m-%d"),
         (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=REF_SPAN * 2)).strftime("%Y-%m-%d"),
         date)).fetchall()
    factors = []
    for rd, rc in refs:
        yb = bars.get(rd)
        if yb and yb["close"] > 0:
            factors.append(float(rc) / yb["close"])
    if not factors:
        return None, "no reference session"
    if len(factors) == 1:
        return None, "only one reference session (cannot confirm basis)"
    # use the tightest-agreeing pair around the median
    factors.sort()
    mid = factors[len(factors) // 2]
    close_enough = [f for f in factors if abs(f / mid - 1) <= FACTOR_AGREEMENT]
    if len(close_enough) < 2:
        return None, f"reference factors disagree ({min(factors):.4f}..{max(factors):.4f})"
    return sum(close_enough) / len(close_enough), len(close_enough)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run)")
    ap.add_argument("--date", help="repair only this session")
    a = ap.parse_args()

    conn = db_connect()
    stranded = find_stranded(conn, a.date)
    if not stranded:
        print("No stranded provisional bars on any past session. Nothing to do.")
        return 0

    total = sum(len(v) for v in stranded.values())
    mode = "APPLY" if a.apply else "DRY RUN"
    print(f"[{mode}] {total} provisional bars across {len(stranded)} past sessions\n")

    repaired = skipped = material = rebased = 0
    reasons: dict[str, int] = defaultdict(int)
    for date in sorted(stranded):
        tickers = stranded[date]
        print(f"{date}: {len(tickers)} provisional")
        window = fetch_window(tickers, date)
        if not window:
            print("    [skip] no settled data returned — leaving provisional\n")
            skipped += len(tickers)
            continue

        writes, big, splits = [], [], []
        for t in tickers:
            bars = window.get(t)
            tgt = bars.get(date) if bars else None
            if not tgt:
                reasons["no settled bar for the session"] += 1
                continue
            f, info = basis_factor(conn, t, date, bars)
            if f is None:
                reasons[info] += 1
                continue
            if abs(f - 1.0) > FACTOR_AGREEMENT:
                splits.append((t, f))
            old = conn.execute("SELECT close FROM ohlcv WHERE ticker=? AND date=?",
                               (t, date)).fetchone()
            new_close = tgt["close"] * f
            if old and old[0]:
                d = abs(new_close / float(old[0]) - 1)
                if d >= MATERIAL_CLOSE_DELTA:
                    big.append((t, float(old[0]), new_close, d))
            writes.append((tgt["open"] * f, tgt["high"] * f, tgt["low"] * f,
                           new_close, tgt["volume"] / f, t, date))

        miss = len(tickers) - len(writes)
        print(f"    repairable {len(writes)}, skipped {miss}")
        if splits:
            rebased += len(splits)
            print(f"    {len(splits)} rebased to the table's raw basis "
                  f"(post-session split); largest:")
            for t, f in sorted(splits, key=lambda x: -abs(x[1]))[:5]:
                print(f"      {t:6s} x{f:,.3f}")
        if big:
            material += len(big)
            print(f"    {len(big)} closes were materially wrong "
                  f"(>= {100*MATERIAL_CLOSE_DELTA:.1f}%); worst:")
            for t, o, n, d in sorted(big, key=lambda x: -x[3])[:5]:
                print(f"      {t:6s} stored {o:>10,.1f} -> settled {n:>10,.1f}  ({100*(o/n-1):+.2f}%)")

        if a.apply and writes:
            with conn:
                conn.executemany(
                    "UPDATE ohlcv SET open=?, high=?, low=?, close=?, volume=?, "
                    "is_final=1 WHERE ticker=? AND date=? AND COALESCE(is_final,1) <> 1",
                    writes)
            left = conn.execute(
                "SELECT COUNT(*) FROM ohlcv WHERE date=? AND COALESCE(is_final,1)<>1",
                (date,)).fetchone()[0]
            print(f"    APPLIED {len(writes)} — {left} still provisional")
        repaired += len(writes)
        skipped += miss
        print()

    print(f"{'Repaired' if a.apply else 'Would repair'}: {repaired} bars"
          f"  |  left provisional: {skipped}"
          f"  |  rebased for a post-session split: {rebased}"
          f"  |  materially wrong closes corrected: {material}")
    if reasons:
        print("Skip reasons:")
        for r, n in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"  {n:5d}  {r}")
    if not a.apply:
        print("\nDry run — nothing written. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
