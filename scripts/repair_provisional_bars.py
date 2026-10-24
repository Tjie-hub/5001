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

THE IHSG FALLBACK (2026-10-23)
------------------------------
yfinance can lack an index session outright: ^JKSE jumped 2026-10-20 ->
2026-10-22 while every stock carried a final 10-21 bar, so the stranded 10-21
IHSG provisional bar (an ~11:05 intraday snapshot, volume 0) had no settled
value to repair from and the dry run could only say "no settled bar for the
session". When that happens for IHSG, ONE Stockbit historical-summary GET
(the same feed the owner used for the manual 10-21 fix) provides the day's
OHLCV — but only after Stockbit's close is validated against yfinance's on the
nearest session BOTH sources serve (they agreed to 0.001% on 2026-10-22:
5,387.905 vs 5,387.90). Disagreement, no common session, or a rejected read
(401/403/429/5xx) leaves the bar provisional. Stocks NEVER take this path:
their split basis is yfinance-derived (see the trap above), and no Stockbit
price is written for them here.

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
# IDX auto-rejection bands cap a one-session move at 35% (the widest band). A repaired close
# implying more than that per intervening session versus the last settled close is not a price,
# it is a source disagreement (typically a split the two sources date differently) -- refuse it.
MAX_SESSION_MOVE = 0.35
# ohlcv tickers whose yfinance symbol is not "<ticker>.JK". IHSG is stored under its own name
# by data/fetcher.py from ^JKSE; "IHSG.JK" is a 404, which left 2026-09-16..22 stranded.
YF_SYMBOL = {"IHSG": "^JKSE"}
# Indices never split, so the empirical basis factor is pure source noise for them (IHSG measured
# 1.0008-1.0016 on 2026-09-16..22: the stored rows are yfinance's own pre-close 16:00 snapshots).
NO_REBASE = {"IHSG"}
# --- IHSG fallback via Stockbit (2026-10-23) ----------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(REPO, ".stockbit_token")
STOCKBIT_BASE = "https://exodus.stockbit.com"
# Same +/- 12 calendar days the yfinance window spans, so the agreement check
# below always has both feeds over one common window.
FB_WINDOW_DAYS = REF_SPAN * 2
# Stockbit's close must match yfinance's this closely on the nearest session
# both serve before Stockbit is trusted for the session yfinance lacks
# (10-22 measured: 5,387.905 vs 5,387.90 = 0.001%).
FB_AGREEMENT = 0.0005
FB_DISAGREE_REASON = "stockbit fallback disagrees with yfinance"


class StockbitUnavailable(Exception):
    """The Stockbit read was rejected (401/403/429/5xx/network). Never retried."""


def yf_symbol(ticker: str) -> str:
    return YF_SYMBOL.get(ticker, ticker + ".JK")


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
    ticker_of = {yf_symbol(t): t for t in tickers}
    symbols = list(ticker_of)
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
            tk = ticker_of[sym]
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
    factors, all_factors = [], []          # all_factors stays aligned with refs
    for rd, rc in refs:
        yb = bars.get(rd)
        if yb and yb["close"] > 0:
            factors.append(float(rc) / yb["close"])
            all_factors.append(factors[-1])
        else:
            all_factors.append(None)
    if not factors:
        return None, "no reference session"
    # The nearest settled session on EACH side of the target decides first (2026-10-19, AHAP 2026-10-12): a corporate
    # action BEFORE both of them (rights issue ex 10-09, yfinance TERP-adjusted history 1.2194) leaves both at the
    # same basis, so the target shares it -- the median of all references (seven pre-event at 1.2194) outvoted them.
    # If the two disagree, the basis changes between them and the target's side is unknown: refuse.
    usable = [((rd, rc), fx) for (rd, rc), fx in zip(refs, all_factors) if fx is not None]
    before = [fx for (rd, _), fx in usable if rd < date]
    after = [fx for (rd, _), fx in usable if rd > date]
    if before and after:
        b, a = before[-1], after[0]
        if abs(b / a - 1) <= FACTOR_AGREEMENT:
            return (b + a) / 2, 2
        return None, f"basis changes inside the bracket of the session ({b:.4f} before, {a:.4f} after)"
    if len(factors) == 1:
        return None, "only one reference session (cannot confirm basis)"
    # use the tightest-agreeing pair around the median
    factors.sort()
    mid = factors[len(factors) // 2]
    close_enough = [f for f in factors if abs(f / mid - 1) <= FACTOR_AGREEMENT]
    if len(close_enough) < 2:
        return None, f"reference factors disagree ({min(factors):.4f}..{max(factors):.4f})"
    f = sum(close_enough) / len(close_enough)
    # A rebase (f != 1) is only trustworthy when a reference lies AFTER the target session.
    # When every settled reference precedes it -- the normal case for a multi-day stranded gap,
    # whose later sessions are provisional too -- a split falling between the references and the
    # target is invisible: the pre-split factor gets applied to a post-split bar. Found
    # 2026-09-23 on FORU (~20:1 split ex 2026-09-22 inside a 09-18..09-22 gap): the dry run would
    # have written 3,433 over a raw 176. With f ~= 1 the one-sided case stays safe, because a
    # split after the references would itself have moved their factor away from 1.
    if abs(f - 1.0) > FACTOR_AGREEMENT and not any(
            rd > date for (rd, rc), fx in zip(refs, all_factors)
            if fx is not None and abs(fx / mid - 1) <= FACTOR_AGREEMENT):
        return None, "rebase needed but no reference after the session (split may fall in the gap)"
    return f, len(close_enough)


def plausible_move(conn, ticker: str, date: str, new_close: float) -> bool:
    """False if new_close is further from the last settled close than IDX price bands allow.

    Added 2026-09-23: FORU's yfinance bar for 2026-09-18 read 154.3 against a settled 3,540 on
    09-17 and a scraper 3,010 the same day -- yfinance dates a ~20:1 split four sessions before
    the IDX tape does. A -96% session is impossible under the 35% auto-rejection band, so the
    bar is left provisional rather than written. Allows (1+35%)^k over k sessions of gap.
    """
    prev = conn.execute(
        "SELECT date, close FROM ohlcv WHERE ticker=? AND is_final=1 AND date<? AND close>0 "
        "ORDER BY date DESC LIMIT 1", (ticker, date)).fetchone()
    if not prev:
        return True
    k = conn.execute("SELECT COUNT(DISTINCT date) FROM ohlcv WHERE date>? AND date<=?",
                     (prev[0], date)).fetchone()[0] or 1
    bound = (1 + MAX_SESSION_MOVE) ** k
    ratio = new_close / float(prev[1])
    return 1 / bound <= ratio <= bound


def stockbit_ihsg_window(date: str) -> dict[str, dict]:
    """{date: {open,high,low,close,volume}} from ONE Stockbit historical-summary
    GET spanning FB_WINDOW_DAYS around `date` — the feed the owner used for the
    manual 2026-10-21 fix. Reads .stockbit_token only; never logs in; raises
    StockbitUnavailable on any rejection so the caller stops rather than retries.
    """
    import requests
    d0 = datetime.strptime(date, "%Y-%m-%d")
    start = (d0 - timedelta(days=FB_WINDOW_DAYS)).strftime("%Y-%m-%d")
    end = (d0 + timedelta(days=FB_WINDOW_DAYS)).strftime("%Y-%m-%d")
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            token = fh.read().strip()
    except OSError as e:
        raise StockbitUnavailable(f".stockbit_token unreadable ({e})") from e
    url = (f"{STOCKBIT_BASE}/company-price-feed/historical/summary/IHSG"
           f"?period=HS_PERIOD_DAILY&start_date={start}&end_date={end}&limit=30&page=1")
    try:
        r = requests.get(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Origin": "https://stockbit.com", "Referer": "https://stockbit.com/",
            "Accept": "application/json"}, timeout=30)
    except Exception as e:  # requests.RequestException — anything network-side
        raise StockbitUnavailable(f"network error ({type(e).__name__})") from e
    if r.status_code in (401, 403):
        raise StockbitUnavailable(
            f"HTTP {r.status_code} — token rejected; do not re-login from here")
    if r.status_code != 200:
        raise StockbitUnavailable(f"HTTP {r.status_code}")
    try:
        rows = ((r.json() or {}).get("data") or {}).get("result") or []
    except ValueError as e:
        raise StockbitUnavailable("response was not JSON") from e
    out: dict[str, dict] = {}
    for row in rows:
        try:
            d = str(row["date"])[:10]
            close = float(row["close"])
            if close > 0:
                out[d] = {"open": float(row["open"]), "high": float(row["high"]),
                          "low": float(row["low"]), "close": close,
                          "volume": float(row.get("volume") or 0.0)}
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _fb_agrees(yf_bars: dict | None, sb_bars: dict, date: str) -> tuple[bool, str]:
    """True when Stockbit's close matches yfinance's within FB_AGREEMENT on the
    nearest session (other than the stranded one) that both feeds serve."""
    common = sorted(d for d in (yf_bars or {}) if d != date and d in sb_bars)
    if not common:
        return False, "no common session with yfinance to validate the feed against"
    tgt = datetime.strptime(date, "%Y-%m-%d")
    near = min(common, key=lambda d: abs((datetime.strptime(d, "%Y-%m-%d") - tgt).days))
    yf_c, sb_c = yf_bars[near]["close"], sb_bars[near]["close"]
    diff = abs(sb_c / yf_c - 1)
    return diff <= FB_AGREEMENT, (f"nearest common session {near}: stockbit {sb_c:,.2f} "
                                  f"vs yfinance {yf_c:,.2f} ({100 * diff:.3f}% apart)")


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
    stockbit_ok = True                      # flipped off by the first rejected read
    ohlcv_cols = {r[1] for r in conn.execute("PRAGMA table_info(ohlcv)")}
    for date in sorted(stranded):
        tickers = stranded[date]
        print(f"{date}: {len(tickers)} provisional")
        window = fetch_window(tickers, date)
        # An all-empty yfinance window still routes IHSG through the per-ticker
        # loop below: the Stockbit fallback must run (and fail its agreement
        # check loudly) rather than vanish inside this whole-date skip.
        if not window and "IHSG" not in tickers:
            print("    [skip] no settled data returned — leaving provisional\n")
            skipped += len(tickers)
            continue

        writes, big, splits, fb_writes = [], [], [], []
        for t in tickers:
            bars = window.get(t)
            tgt = bars.get(date) if bars else None
            fb = False
            if not tgt and t == "IHSG" and stockbit_ok:
                # yfinance lacks this stranded index session (2026-10-21: ^JKSE
                # jumps 10-20 -> 10-22). One Stockbit GET, written only if the
                # two feeds agree on the nearest session they both serve.
                try:
                    sb = stockbit_ihsg_window(date)
                except StockbitUnavailable as e:
                    stockbit_ok = False   # one token: later GETs would fail the same way
                    print(f"    [stop] Stockbit fallback: {e} — leaving IHSG provisional")
                    reasons["stockbit fallback unavailable"] += 1
                    continue
                tgt = sb.get(date)
                if not tgt:
                    print(f"    [fallback] IHSG {date}: Stockbit has no bar for the session either")
                    reasons["no settled bar for the session"] += 1
                    continue
                ok, detail = _fb_agrees(bars, sb, date)
                if not ok:
                    print(f"    [fallback] IHSG {date}: {detail}")
                    reasons[FB_DISAGREE_REASON] += 1
                    continue
                fb = True
            elif not tgt:
                reasons["no settled bar for the session"] += 1
                continue
            f, info = (1.0, "index") if t in NO_REBASE else basis_factor(conn, t, date, bars)
            if f is None:
                reasons[info] += 1
                continue
            if abs(f - 1.0) > FACTOR_AGREEMENT:
                splits.append((t, f))
            old = conn.execute("SELECT close FROM ohlcv WHERE ticker=? AND date=?",
                               (t, date)).fetchone()
            new_close = tgt["close"] * f
            if not plausible_move(conn, t, date, new_close):
                reasons["implausible move vs last settled close (> IDX 35% band/session)"] += 1
                continue
            if old and old[0]:
                d = abs(new_close / float(old[0]) - 1)
                if d >= MATERIAL_CLOSE_DELTA:
                    big.append((t, float(old[0]), new_close, d))
            writes.append((tgt["open"] * f, tgt["high"] * f, tgt["low"] * f,
                           new_close, tgt["volume"] / f, t, date))
            if fb:
                fb_writes.append((t, date))

        miss = len(tickers) - len(writes)
        print(f"    repairable {len(writes)}, skipped {miss}")
        if fb_writes:
            note = ("" if "source" in ohlcv_cols else
                    "  (ohlcv has no source column — provenance kept in this output only)")
            print(f"    {len(fb_writes)} via the Stockbit fallback (source: stockbit): "
                  f"{', '.join(f'{t} {d}' for t, d in fb_writes)}{note}")
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
                if fb_writes and "source" in ohlcv_cols:
                    conn.executemany(
                        "UPDATE ohlcv SET source='stockbit' WHERE ticker=? AND date=?",
                        fb_writes)
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
