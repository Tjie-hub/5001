"""Phase 2A one-time corpus rebuild (audit C-4/C-5; owner-approved 2026-07-03).

Builds a clean 5-year RAW price corpus in ohlcv_raw (yfinance auto_adjust=False
= official exchange prices), verifies coverage vs the live ohlcv table, then
swaps: ohlcv -> ohlcv_pre_raw_rebuild (archive), ohlcv_raw -> ohlcv.
Reversible until the archive table is dropped.

Usage (run on the LIVE checkout, app can stay up during --build):
    python -m scripts.rebuild_ohlcv_raw --build            # hours-long fetch, side table
    python -m scripts.rebuild_ohlcv_raw --verify           # prints report JSON
    python -m scripts.rebuild_ohlcv_raw --swap             # requires passing verify
"""
import argparse
import json
import sqlite3
import time

from config import DB_PATH

PERIOD = "5y"
# Verification thresholds: the rebuild must not LOSE coverage.
MAX_LOST_TICKER_FRAC = 0.05    # <=5% of old tickers may be missing (delisted from yf)
MIN_ROW_RATIO = 0.95           # new rows >= 95% of old rows within the old span


def _default_fetch(ticker, period=PERIOD):
    """Raw 5y daily history for one ticker. Returns df[date,open,high,low,close,volume]."""
    import yfinance as yf
    sym = "^JKSE" if ticker == "IHSG" else ticker + ".JK"
    df = yf.download(sym, period=period, auto_adjust=False, actions=True,
                     progress=False)
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume",
                            "Dividends": "dividends", "Stock Splits": "splits"})
    df["date"] = df["date"].astype(str).str[:10]
    return df


def build(db_path=DB_PATH, tickers=None, fetch_fn=_default_fetch,
          period=PERIOD, delay=0.25) -> dict:
    """Fetch raw history per ticker into ohlcv_raw (is_final=1). Also captures
    corporate actions when the frame carries dividends/splits columns.
    Non-destructive; resumable (skips tickers already present)."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("""CREATE TABLE IF NOT EXISTS ohlcv_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL, date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume REAL,
        is_final INTEGER DEFAULT 1, UNIQUE(ticker, date))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_raw_ticker ON ohlcv_raw(ticker)")
    conn.commit()

    if tickers is None:
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker")]
        if "IHSG" not in tickers:
            tickers.append("IHSG")

    done = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM ohlcv_raw")}
    ok = err = skipped = 0
    for i, t in enumerate(tickers):
        if t in done:
            skipped += 1
            continue
        try:
            df = fetch_fn(t, period)
            if df is None or len(df) == 0:
                err += 1
                continue
            rows = [(t, r["date"], r["open"], r["high"], r["low"], r["close"],
                     r["volume"]) for _, r in df.iterrows()
                    if r["close"] == r["close"]]
            conn.executemany(
                "INSERT OR IGNORE INTO ohlcv_raw (ticker,date,open,high,low,close,volume,is_final)"
                " VALUES (?,?,?,?,?,?,?,1)", rows)
            for _, r in df.iterrows():
                for col, action in (("dividends", "dividend"), ("splits", "split")):
                    v = r.get(col)
                    if v is not None and v == v and float(v) != 0.0:
                        conn.execute(
                            "INSERT OR REPLACE INTO corporate_actions"
                            " (ticker,date,action,value,source) VALUES (?,?,?,?,'yfinance')",
                            (t, r["date"], action, float(v)))
            conn.commit()
            ok += 1
        except Exception as e:
            err += 1
            print(f"  [{t}] error: {e}")
        if delay and fetch_fn is _default_fetch:
            time.sleep(delay)
        if (i + 1) % 50 == 0:
            print(f"  progress: {i+1}/{len(tickers)} (ok={ok} err={err} skip={skipped})")
    conn.close()
    return {"tickers_ok": ok, "tickers_err": err, "tickers_skipped": skipped}


def verify(db_path=DB_PATH) -> dict:
    """Coverage + basis report: old ohlcv vs ohlcv_raw. Sets report['ok']."""
    conn = sqlite3.connect(db_path)
    old_t = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM ohlcv")}
    new_t = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM ohlcv_raw")}
    old_span = conn.execute("SELECT MIN(date), MAX(date) FROM ohlcv").fetchone()
    old_rows = conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
    new_rows_in_span = conn.execute(
        "SELECT COUNT(*) FROM ohlcv_raw WHERE date BETWEEN ? AND ?", old_span).fetchone()[0]
    restored = conn.execute("""
        SELECT COUNT(*) FROM ohlcv_raw r WHERE date BETWEEN ? AND ?
        AND NOT EXISTS (SELECT 1 FROM ohlcv o WHERE o.ticker=r.ticker AND o.date=r.date)
    """, old_span).fetchone()[0]
    lost = conn.execute("""
        SELECT COUNT(*) FROM ohlcv o WHERE o.close IS NOT NULL
        AND o.ticker IN (SELECT DISTINCT ticker FROM ohlcv_raw)
        AND NOT EXISTS (SELECT 1 FROM ohlcv_raw r WHERE r.ticker=o.ticker AND r.date=o.date)
    """).fetchone()[0]
    # basis check: big deltas on OLD dates = the adjusted history; recent
    # dates (scraper vs yf raw, both raw) should broadly agree.
    mismatches = [
        {"ticker": t, "date": d, "old": o, "new": n,
         "diff_pct": round(abs(o - n) / n * 100, 2)}
        for t, d, o, n in conn.execute("""
            SELECT o.ticker, o.date, o.close, r.close FROM ohlcv o
            JOIN ohlcv_raw r ON r.ticker=o.ticker AND r.date=o.date
            WHERE o.close IS NOT NULL AND r.close > 0
              AND ABS(o.close - r.close) / r.close > 0.005
            ORDER BY o.date DESC LIMIT 200""")
    ]
    conn.close()
    lost_frac = len(old_t - new_t - {"IHSG"}) / max(len(old_t), 1)
    row_ratio = new_rows_in_span / max(old_rows, 1)
    report = {
        "tickers_old": len(old_t), "tickers_new": len(new_t),
        "tickers_lost": sorted(old_t - new_t)[:20], "lost_ticker_frac": round(lost_frac, 4),
        "old_rows": old_rows, "new_rows_in_old_span": new_rows_in_span,
        "row_ratio": round(row_ratio, 4),
        "restored_rows": restored, "lost_rows": lost,
        "close_mismatches": mismatches[:50], "n_close_mismatches": len(mismatches),
        "ok": lost_frac <= MAX_LOST_TICKER_FRAC and row_ratio >= MIN_ROW_RATIO,
    }
    return report


def swap(db_path=DB_PATH, report=None) -> None:
    """Archive ohlcv -> ohlcv_pre_raw_rebuild; promote ohlcv_raw -> ohlcv.
    Refuses without a passing verification report."""
    if not report or not report.get("ok"):
        raise RuntimeError("swap refused: verification report missing or ok=False")
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    try:
        conn.execute("DROP INDEX IF EXISTS idx_ohlcv_ticker")
        conn.execute("ALTER TABLE ohlcv RENAME TO ohlcv_pre_raw_rebuild")
        conn.execute("ALTER TABLE ohlcv_raw RENAME TO ohlcv")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON ohlcv(ticker)")
        conn.commit()
        print("swap complete: ohlcv is now the raw corpus; archive = ohlcv_pre_raw_rebuild")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--swap", action="store_true")
    args = ap.parse_args()
    if args.build:
        print(json.dumps(build(), indent=2))
    if args.verify or args.swap:
        rep = verify()
        print(json.dumps(rep, indent=2))
        if args.swap:
            swap(DB_PATH, rep)
