import os
import csv
import time
from datetime import datetime, timedelta

import yfinance as yf
from data.db import get_db

# ── Index Constituents (preserved for backward compat) ───────────────────────
IDX30 = [
    "AMMN", "AMRT", "ASII", "BBCA", "BBNI", "BBRI", "BBTN",
    "BMRI", "BREN", "BRIS", "BRPT", "CPIN", "EXCL", "GOTO",
    "ICBP", "INCO", "INDF", "ISAT", "ITMG", "KLBF", "MDKA",
    "MEDC", "PGAS", "PGEO", "PTBA", "TBIG", "TLKM", "TOWR",
    "TPIA", "UNTR",
]
_LQ45_EXTRA = [
    "ACES", "ADRO", "AKRA", "ANTM", "BTPS",
    "CTRA", "EMTK", "HRUM", "INKP", "INTP",
    "JSMR", "LPPF", "MAPI", "MIKA", "MTEL",
]
LQ45 = IDX30 + _LQ45_EXTRA

_IDX80_EXTRA = [
    "AALI", "ARTO", "BBYB", "BNGA", "BSDE",
    "BUKA", "CMRY", "DNET", "ERAA", "ESSA",
    "GGRM", "HMSP", "JPFA", "KAEF", "KIJA",
    "LINK", "LSIP", "MBMA", "MNCN",
    "MYOR", "NCKL", "NISP", "PANI", "PNBN",
    "PTPP", "PWON", "RAJA", "SCMA", "SIDO",
    "SMGR", "SMRA", "TINS", "TKIM", "UNVR",
]
IDX80 = LQ45 + _IDX80_EXTRA

CATEGORIES = {"IDX30": IDX30, "LQ45": LQ45, "IDX80": IDX80}
TICKERS = IDX80  # default

_HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(_HERE, "idx_master.csv")
BATCH_SIZE = 50
RATE_DELAY = 0.3


def get_tickers(category: str = None) -> list:
    """Return ticker list for IDX30/LQ45/IDX80 or all active tickers."""
    if category is None:
        return TICKERS
    cat = category.upper()
    if cat == "ALL":
        return load_all_tickers()
    if cat not in CATEGORIES:
        raise ValueError(f"Unknown category '{category}'. Use: IDX30, LQ45, IDX80, ALL")
    return CATEGORIES[cat]


def load_all_tickers() -> list:
    """Load all active tickers from idx_tickers DB table, falling back to idx_master.csv, then IDX80."""
    # 1. Try DB
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT ticker FROM idx_tickers WHERE status='active' ORDER BY ticker"
        ).fetchall()
        conn.close()
        if rows:
            return [r["ticker"] for r in rows]
    except Exception:
        pass

    # 2. Try CSV
    if os.path.exists(MASTER_CSV):
        tickers = []
        with open(MASTER_CSV, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("status", "active") == "active":
                    tickers.append(row["ticker"])
        if tickers:
            return sorted(tickers)

    # 3. Fallback to IDX80
    return IDX80


# ── Single ticker (original API preserved) ───────────────────────────────────

def fetch_ticker(ticker, period="2y"):
    symbol = ticker + ".JK"
    print(f"Fetching {symbol}...")
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
    if df.empty:
        print(f"  WARNING: no data for {symbol}")
        return 0
    return _save_df(ticker, df)


# ── Batch helpers ─────────────────────────────────────────────────────────────

def _save_df(ticker, df) -> int:
    df = df.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    df["date"] = df["date"].astype(str).str[:10]
    import math
    conn = get_db()
    saved = 0
    for _, row in df.iterrows():
        close_val = row["close"]
        if close_val is None or (isinstance(close_val, float) and math.isnan(close_val)):
            continue  # skip incomplete intraday rows
        try:
            conn.execute(
                """INSERT INTO ohlcv (ticker,date,open,high,low,close,volume)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(ticker,date) DO UPDATE SET
                     open=excluded.open, high=excluded.high, low=excluded.low,
                     close=excluded.close, volume=excluded.volume
                   WHERE ohlcv.close IS NULL""",
                (ticker, row["date"], row["open"], row["high"], row["low"], close_val, row["volume"]),
            )
            saved += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return saved


def _fetch_batch(tickers: list, period: str = None, start: str = None) -> dict[str, int]:
    """
    Download OHLCV for a batch of tickers in one yfinance call.
    Returns {ticker: bars_saved}.
    """
    symbols = [t + ".JK" for t in tickers]
    try:
        kwargs = dict(auto_adjust=True, progress=False, threads=True)
        if start:
            kwargs["start"] = start
        elif period:
            kwargs["period"] = period
        else:
            kwargs["period"] = "2y"

        df = yf.download(symbols, **kwargs)
        if df.empty:
            return {t: 0 for t in tickers}
    except Exception as e:
        print(f"  [batch error] {e}")
        return {t: 0 for t in tickers}

    results = {}
    if len(symbols) == 1:
        saved = _save_df(tickers[0], df) if not df.empty else 0
        results[tickers[0]] = saved
    else:
        cols = df.columns
        # Determine column layout
        if hasattr(cols, "levels"):
            level_vals_1 = [str(c) for c in cols.get_level_values(1)]
            sym_in_level1 = any(".JK" in v for v in level_vals_1)

        for t, sym in zip(tickers, symbols):
            try:
                if hasattr(cols, "levels"):
                    if sym_in_level1:
                        sub = df.xs(sym, axis=1, level=1)
                    else:
                        sub = df[sym]
                else:
                    sub = df[[c for c in df.columns if sym in str(c)]]
                if sub.empty or sub["Close"].isna().all():
                    results[t] = 0
                else:
                    results[t] = _save_df(t, sub)
            except Exception:
                results[t] = 0
    return results


def _batches(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


# ── Public fetch functions ────────────────────────────────────────────────────

def fetch_all(period="2y", category: str = None):
    """Fetch OHLCV for a category (IDX30/LQ45/IDX80/ALL) or IDX80 by default."""
    tickers = get_tickers(category)
    label = (category.upper() if category else "IDX80")
    print(f"Fetching {len(tickers)} tickers [{label}] in batches of {BATCH_SIZE}...")

    total_saved = 0
    failed = []
    for i, batch in enumerate(_batches(tickers, BATCH_SIZE), 1):
        print(f"  Batch {i}/{-(-len(tickers)//BATCH_SIZE)}: {batch[0]}…{batch[-1]}")
        results = _fetch_batch(batch, period=period)
        for t, saved in results.items():
            if saved == 0:
                failed.append(t)
            total_saved += saved
        time.sleep(RATE_DELAY)

    print(f"\nDone: {total_saved} bars saved, {len(failed)} tickers with no data")
    if failed:
        print(f"No data: {', '.join(failed)}")
    return total_saved


def fetch_ihsg(period: str = "2y"):
    """Fetch IHSG (^JKSE) OHLCV and store as ticker='IHSG' in ohlcv table."""
    symbol = "^JKSE"
    print(f"Fetching {symbol} (IHSG)...")
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
    if df.empty:
        print(f"  WARNING: no data for {symbol}")
        return 0
    return _save_df("IHSG", df)


def fetch_all_incremental(category: str = None):
    """
    Delta-only fetch: only pull bars newer than each ticker's MAX(date) in DB.
    Much faster for daily updates — skips already-current tickers.
    """
    tickers = get_tickers(category)
    label = category.upper() if category else "IDX80"
    print(f"Incremental fetch [{label}]: {len(tickers)} tickers...")

    conn = get_db()
    rows = conn.execute(
        "SELECT ticker, MAX(date) as max_date FROM ohlcv WHERE ticker IN ({}) GROUP BY ticker".format(
            ",".join("?" * len(tickers))
        ),
        tickers,
    ).fetchall()
    conn.close()

    today = datetime.now().strftime("%Y-%m-%d")
    max_dates = {r["ticker"]: r["max_date"] for r in rows}

    # Group tickers by their latest date so we can batch together
    groups: dict[str, list] = {}
    new_tickers = []
    skipped = 0
    for t in tickers:
        md = max_dates.get(t)
        if md is None:
            new_tickers.append(t)
        elif md >= today:
            skipped += 1
        else:
            groups.setdefault(md, []).append(t)

    print(f"  {skipped} already current, {len(new_tickers)} new, {sum(len(v) for v in groups.values())} to update")

    total_saved = 0

    # New tickers: full 2y fetch
    if new_tickers:
        print(f"  Bulk backfill {len(new_tickers)} new tickers (2y)...")
        for batch in _batches(new_tickers, BATCH_SIZE):
            results = _fetch_batch(batch, period="2y")
            total_saved += sum(results.values())
            time.sleep(RATE_DELAY)

    # Existing tickers: fetch from day after last known date
    for max_date, batch_tickers in groups.items():
        start_date = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        for batch in _batches(batch_tickers, BATCH_SIZE):
            results = _fetch_batch(batch, start=start_date)
            total_saved += sum(results.values())
            time.sleep(RATE_DELAY)

    # Always refresh IHSG incrementally
    conn_ihsg = get_db()
    ihsg_row = conn_ihsg.execute("SELECT MAX(date) as md FROM ohlcv WHERE ticker='IHSG'").fetchone()
    conn_ihsg.close()
    ihsg_max = ihsg_row["md"] if ihsg_row else None
    if ihsg_max is None:
        total_saved += fetch_ihsg(period="2y")
    elif ihsg_max < today:
        ihsg_start = (datetime.strptime(ihsg_max, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        df_ihsg = yf.download("^JKSE", start=ihsg_start, auto_adjust=True, progress=False)
        if not df_ihsg.empty:
            total_saved += _save_df("IHSG", df_ihsg)

    print(f"Done: {total_saved} new bars saved")
    return total_saved


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IDX OHLCV fetcher")
    parser.add_argument("--cat", default=None, help="IDX30 / LQ45 / IDX80 / ALL")
    parser.add_argument("--period", default="2y", help="yfinance period (default: 2y)")
    parser.add_argument("--incremental", action="store_true", help="Only fetch new bars (delta update)")
    args = parser.parse_args()

    if args.incremental:
        fetch_all_incremental(category=args.cat)
    else:
        fetch_all(period=args.period, category=args.cat)
