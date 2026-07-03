"""Phase 2A — nightly OHLCV reconciliation (alert-only, audit C-4).

Compares the scraper-final closes for a date against yfinance RAW closes.
The scraper stays the authority (owner's decision); disagreements are
reported, never auto-corrected. Consumed by scheduler.jobs.run_ohlcv_reconciliation.
"""
import sqlite3

from config import DB_PATH

TOLERANCE = 0.001   # 0.1% — beyond this, flag


def _yf_closes(tickers, date):
    """Default price_fetcher: batched raw yfinance downloads for `date`."""
    import yfinance as yf
    from datetime import datetime, timedelta
    end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    out = {}
    BATCH = 100
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        symbols = [t + ".JK" for t in batch]
        try:
            df = yf.download(symbols, start=date, end=end,
                             auto_adjust=False, progress=False, threads=True)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        for t, sym in zip(batch, symbols):
            try:
                close = df["Close"][sym].iloc[-1] if len(symbols) > 1 else df["Close"].iloc[-1]
                if close == close:          # not NaN
                    out[t] = float(close)
            except Exception:
                continue
    return out


def reconcile_ohlcv(date: str, db_path: str = DB_PATH,
                    price_fetcher=None, tolerance: float = TOLERANCE) -> dict:
    """Returns {date, compared, missing_yf, mismatches: [{ticker, scraper,
    yfinance, diff_pct}]}. Read-only on ohlcv."""
    fetch = price_fetcher or _yf_closes
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT ticker, close FROM ohlcv WHERE date=? AND close IS NOT NULL "
        "AND ticker != 'IHSG'", (date,)).fetchall()
    conn.close()

    scraper = {t: c for t, c in rows}
    yf_map = fetch(sorted(scraper), date)

    mismatches, compared, missing = [], 0, 0
    for t, c in sorted(scraper.items()):
        y = yf_map.get(t)
        if y is None or y <= 0:
            missing += 1
            continue
        compared += 1
        diff = abs(c - y) / y
        if diff > tolerance:
            mismatches.append({"ticker": t, "scraper": c, "yfinance": y,
                               "diff_pct": round(diff * 100, 2)})
    mismatches.sort(key=lambda m: -m["diff_pct"])
    return {"date": date, "compared": compared, "missing_yf": missing,
            "mismatches": mismatches}
