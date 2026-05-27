#!/usr/bin/env python3
"""
IDX Fetcher
============
Bypasses Cloudflare on idx.co.id using non-headless Playwright on virtual
display :99. Intercepts API responses directly inside the browser session.

Commands:
  python3 idx_fetcher.py                          # trading summary, all stocks
  python3 idx_fetcher.py BBCA TLKM BBRI           # filter specific tickers
  python3 idx_fetcher.py --date 2026-05-21        # specific date
  python3 idx_fetcher.py --refresh                # force browser re-launch
  python3 idx_fetcher.py --check                  # check cache status

  python3 idx_fetcher.py reports BBCA             # annual + quarterly reports list
  python3 idx_fetcher.py reports BBCA --year 2024 # specific year
  python3 idx_fetcher.py reports BBCA --download  # download PDFs
  python3 idx_fetcher.py reports BBCA --year 2023 --download

Cron (setiap hari 18:30 WIB):
  30 18 * * 1-5 cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python3 idx_fetcher.py >> logs/idx_fetcher.log 2>&1
"""

import os, sys, json, time, sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Config ──
_HERE             = Path(__file__).resolve().parent
DB_PATH           = _HERE / "data" / "walkforward.db"
REPORTS_DIR       = _HERE / "data" / "reports"
LOG_FILE          = _HERE / "logs" / "idx_fetcher.log"
CACHE_FILE        = _HERE / ".idx_response_cache.json"
PLAYWRIGHT_BROWSERS = Path("/home/tjiesar/DS/.playwright")

IDX_BASE = "https://www.idx.co.id"
UA       = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

REPORT_TYPES = {
    "rdt": "Annual Report",
    "rdf": "Financial Statement",
}
PERIODS = ["tw1", "tw2", "tw3", "tw4", "annual"]


# ── Logging ──
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── Browser helper (shared by all fetch functions) ──
def _browser_session(task_fn):
    """
    Launch non-headless Chromium, pass Cloudflare, run task_fn(page) → result.
    task_fn is an async callable that receives the authenticated page.
    """
    import asyncio
    from playwright.async_api import async_playwright

    os.environ.setdefault("DISPLAY", ":99")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS)

    async def _run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ],
            )
            ctx = await browser.new_context(
                user_agent=UA,
                viewport={"width": 1920, "height": 1080},
                locale="id-ID",
            )
            await ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await ctx.new_page()

            # Pass Cloudflare challenge
            await page.goto(f"{IDX_BASE}/id", wait_until="domcontentloaded", timeout=30000)
            for _ in range(20):
                if "just a moment" not in (await page.title()).lower():
                    break
                await page.wait_for_timeout(1000)
            log(f"CF resolved: {await page.title()}")
            await page.wait_for_timeout(1500)

            result = await task_fn(page)
            await browser.close()
            return result

    return asyncio.run(_run())


# ══════════════════════════════════════════════════════════
# TRADING SUMMARY
# ══════════════════════════════════════════════════════════

def _cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    try:
        age = time.time() - json.loads(CACHE_FILE.read_text()).get("_captured_at", 0)
        return age < 3600 * 12
    except Exception:
        return False


def fetch_trading_summary(date: str | None = None, force: bool = False) -> list[dict]:
    """Fetch full trading summary (~959 stocks). Caches for 12h."""
    if not force and _cache_valid():
        records = json.loads(CACHE_FILE.read_text()).get("records", [])
        log(f"Using cached summary ({len(records)} records)")
        return records

    log("Launching browser — fetching trading summary...")

    async def task(page):
        captured = {}
        done = __import__("asyncio").Event()

        async def on_response(resp):
            if "GetStockSummary" in resp.url:
                try:
                    body = await resp.json()
                    captured["data"] = body
                    done.set()
                    log(f"Intercepted: {resp.url}")
                except Exception as e:
                    log(f"Parse error: {e}")

        page.on("response", on_response)

        target = f"{IDX_BASE}/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/"
        if date:
            target += f"?date={date}"
        await page.goto(target, wait_until="networkidle", timeout=30000)

        import asyncio
        try:
            await asyncio.wait_for(done.wait(), timeout=20)
        except asyncio.TimeoutError:
            log("Timeout waiting for GetStockSummary")

        return captured.get("data", {})

    raw     = _browser_session(task)
    records = raw.get("data", [])
    log(f"Fetched {len(records)} records")
    CACHE_FILE.write_text(json.dumps({"_captured_at": time.time(), "records": records}))
    return records


def init_summary_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idx_trading_summary (
            trade_date    TEXT NOT NULL,
            stock_code    TEXT NOT NULL,
            stock_name    TEXT,
            previous      REAL,
            open_price    REAL,
            high          REAL,
            low           REAL,
            close         REAL,
            change        REAL,
            pct_change    REAL,
            volume        REAL,
            value         REAL,
            frequency     REAL,
            foreign_buy   REAL,
            foreign_sell  REAL,
            net_foreign   REAL,
            offer         REAL,
            bid           REAL,
            listed_shares REAL,
            updated_at    TEXT NOT NULL,
            PRIMARY KEY (trade_date, stock_code)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_its_date ON idx_trading_summary(trade_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_its_code ON idx_trading_summary(stock_code)")
    conn.commit()


def save_summary(conn: sqlite3.Connection, records: list[dict]) -> int:
    now, rows = datetime.now().isoformat(), []
    for r in records:
        code = r.get("StockCode", "").strip()
        if not code:
            continue
        raw_date   = r.get("Date", "")
        trade_date = raw_date[:10] if raw_date else datetime.now().strftime("%Y-%m-%d")
        fb = float(r.get("ForeignBuy") or 0)
        fs = float(r.get("ForeignSell") or 0)
        rows.append((
            trade_date, code, r.get("StockName", ""),
            r.get("Previous"), r.get("OpenPrice"), r.get("High"), r.get("Low"),
            r.get("Close"), r.get("Change"), r.get("persen") or r.get("percentage"),
            r.get("Volume"), r.get("Value"), r.get("Frequency"),
            fb, fs, fb - fs,
            r.get("Offer"), r.get("Bid"), r.get("ListedShares"), now,
        ))
    conn.executemany(
        """INSERT OR REPLACE INTO idx_trading_summary
           (trade_date,stock_code,stock_name,previous,open_price,high,low,close,
            change,pct_change,volume,value,frequency,foreign_buy,foreign_sell,
            net_foreign,offer,bid,listed_shares,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def _fmt(v, fmt="{:,.0f}"):
    try:
        return fmt.format(float(v)) if v not in (None, "") else "-"
    except Exception:
        return str(v)


def print_summary(records: list[dict], filter_codes: list[str] | None = None):
    if filter_codes:
        records = [r for r in records if r.get("StockCode", "").upper() in filter_codes]
    if not records:
        print("No matching records")
        return
    hdr = f"{'Code':<8} {'Name':<32} {'Close':>8} {'Chg%':>7} {'Volume':>14} {'NetForeign':>14}"
    print(hdr)
    print("-" * len(hdr))
    for r in records:
        pct = r.get("persen") or r.get("percentage") or 0
        fb  = float(r.get("ForeignBuy") or 0)
        fs  = float(r.get("ForeignSell") or 0)
        try:
            pct_s = f"{float(pct):+.2f}%"
        except Exception:
            pct_s = str(pct)
        print(
            f"{r.get('StockCode','?'):<8} "
            f"{(r.get('StockName') or '')[:30]:<32} "
            f"{_fmt(r.get('Close')):>8} {pct_s:>7} "
            f"{_fmt(r.get('Volume')):>14} "
            f"{_fmt(fb - fs):>14}"
        )


# ══════════════════════════════════════════════════════════
# ANNUAL REPORT & FINANCIAL STATEMENTS
# ══════════════════════════════════════════════════════════

def fetch_reports(ticker: str, year: int | None = None) -> dict:
    """
    Fetch annual reports (rdt) and financial statements (rdf) for a ticker.
    Returns dict keyed by (report_type, period) → list of attachment dicts.
    """
    ticker = ticker.upper()
    years  = [year] if year else list(range(datetime.now().year, 2018, -1))

    log(f"Fetching reports for {ticker} — years: {years}")

    async def task(page):
        results = {}
        for yr in years:
            for rtype in ["rdt", "rdf"]:
                for period in (["annual"] if rtype == "rdt" else PERIODS):
                    ep = (
                        f"/primary/ListedCompany/GetFinancialReport"
                        f"?indexFrom=1&pageSize=20&year={yr}"
                        f"&reportType={rtype}&EmitenType=s"
                        f"&periode={period}&kodeEmiten={ticker}"
                        f"&SortColumn=File_Modified&SortOrder=desc"
                    )
                    data = await page.evaluate(f'''async () => {{
                        const r = await fetch("{ep}", {{
                            headers: {{"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}}
                        }});
                        return await r.json();
                    }}''')
                    hits = data.get("Results") or []
                    if hits:
                        key = f"{rtype}_{yr}_{period}"
                        results[key] = hits[0].get("Attachments", [])
                        label = REPORT_TYPES.get(rtype, rtype)
                        log(f"  {label} {yr} {period}: {len(results[key])} files")
        return results

    return _browser_session(task)


def init_reports_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idx_reports (
            ticker       TEXT NOT NULL,
            year         INTEGER NOT NULL,
            period       TEXT NOT NULL,
            report_type  TEXT NOT NULL,
            file_name    TEXT NOT NULL,
            file_path    TEXT NOT NULL,
            file_id      TEXT,
            modified_at  TEXT,
            downloaded   INTEGER DEFAULT 0,
            local_path   TEXT,
            updated_at   TEXT NOT NULL,
            PRIMARY KEY (ticker, year, period, report_type, file_name)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rpt_ticker ON idx_reports(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rpt_year   ON idx_reports(year)")
    conn.commit()


def save_reports(conn: sqlite3.Connection, ticker: str, report_data: dict) -> int:
    now, rows = datetime.now().isoformat(), []
    for key, attachments in report_data.items():
        parts = key.split("_", 2)          # rdt_2024_annual
        rtype, yr, period = parts[0], int(parts[1]), parts[2]
        for att in attachments:
            rows.append((
                ticker, yr, period, rtype,
                att.get("File_Name", ""),
                att.get("File_Path", ""),
                att.get("File_ID", ""),
                (att.get("File_Modified") or "")[:19],
                0, None, now,
            ))
    if rows:
        conn.executemany(
            """INSERT OR REPLACE INTO idx_reports
               (ticker,year,period,report_type,file_name,file_path,
                file_id,modified_at,downloaded,local_path,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
    return len(rows)


def download_reports(conn: sqlite3.Connection, ticker: str, year: int | None = None):
    """Download all PDFs not yet downloaded. Saves to data/reports/<TICKER>/<year>/"""
    query = "SELECT ticker,year,period,report_type,file_name,file_path FROM idx_reports WHERE ticker=? AND downloaded=0"
    params = [ticker]
    if year:
        query += " AND year=?"
        params.append(year)

    rows = conn.execute(query, params).fetchall()
    if not rows:
        log("Nothing to download (all already downloaded or no records)")
        return

    log(f"Downloading {len(rows)} files for {ticker}...")
    for tkr, yr, period, rtype, fname, fpath in rows:
        if not fpath or not fname.endswith(".pdf"):
            continue
        dest_dir = REPORTS_DIR / tkr / str(yr)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fname

        if dest.exists():
            log(f"  Skip (exists): {fname}")
            conn.execute(
                "UPDATE idx_reports SET downloaded=1, local_path=? WHERE ticker=? AND year=? AND file_name=?",
                (str(dest), tkr, yr, fname),
            )
            conn.commit()
            continue

        try:
            # URL-encode path segments (handles spaces in IDX file paths)
            encoded_path = "/".join(urllib.parse.quote(seg, safe="") for seg in fpath.split("/"))
            url = f"{IDX_BASE}{encoded_path}"
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": f"{IDX_BASE}/"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            size_kb = dest.stat().st_size // 1024
            log(f"  ✓ {fname} ({size_kb:,} KB)")
            conn.execute(
                "UPDATE idx_reports SET downloaded=1, local_path=? WHERE ticker=? AND year=? AND file_name=?",
                (str(dest), tkr, yr, fname),
            )
            conn.commit()
        except Exception as e:
            log(f"  ✗ {fname}: {e}")


def print_reports(report_data: dict, ticker: str):
    if not report_data:
        print(f"No reports found for {ticker}")
        return
    for key, attachments in sorted(report_data.items()):
        parts = key.split("_", 2)
        rtype, yr, period = parts[0], parts[1], parts[2]
        label = REPORT_TYPES.get(rtype, rtype)
        print(f"\n  {label} {yr} [{period}]")
        for att in attachments:
            fname = att.get("File_Name", "?")
            mod   = (att.get("File_Modified") or "")[:10]
            print(f"    {fname:<55} {mod}")


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def cmd_summary(args: list[str]):
    force      = "--refresh" in args
    check_only = "--check" in args
    date_arg   = None

    if "--date" in args:
        i = args.index("--date")
        date_arg = args[i + 1]
        args = args[:i] + args[i + 2:]

    filter_codes = [a.upper() for a in args if not a.startswith("--")]

    log("=" * 50)
    log("IDX TRADING SUMMARY")
    log("=" * 50)

    if check_only:
        if _cache_valid():
            data = json.loads(CACHE_FILE.read_text())
            age  = int(time.time() - data.get("_captured_at", 0))
            log(f"Cache valid — {len(data.get('records',[]))} records, age={age}s")
        else:
            log("Cache missing or expired (>12h)")
        return

    records = fetch_trading_summary(date=date_arg, force=force)
    if not records:
        log("No data returned")
        sys.exit(1)

    raw_date   = records[0].get("Date", "")
    trade_date = raw_date[:10] if raw_date else (date_arg or datetime.now().strftime("%Y-%m-%d"))
    log(f"Trade date: {trade_date} | Records: {len(records)}")

    conn = sqlite3.connect(DB_PATH)
    init_summary_db(conn)
    saved = save_summary(conn, records)
    conn.close()
    log(f"Saved {saved} records to idx_trading_summary")

    if filter_codes:
        print()
        print_summary(records, filter_codes)
    else:
        with_net = [
            {**r, "_nf": float(r.get("ForeignBuy") or 0) - float(r.get("ForeignSell") or 0)}
            for r in records if r.get("Close")
        ]
        top_buy  = sorted(with_net, key=lambda x: x["_nf"], reverse=True)[:10]
        top_sell = sorted(with_net, key=lambda x: x["_nf"])[:10]
        print(f"\n{'='*60}\n  TOP 10 FOREIGN NET BUY  ({trade_date})\n{'='*60}")
        print_summary(top_buy)
        print(f"\n{'='*60}\n  TOP 10 FOREIGN NET SELL  ({trade_date})\n{'='*60}")
        print_summary(top_sell)


def cmd_reports(args: list[str]):
    if not args or args[0].startswith("--"):
        print("Usage: idx_fetcher.py reports <TICKER> [--year 2024] [--download]")
        sys.exit(1)

    ticker   = args[0].upper()
    download = "--download" in args
    year_arg = None

    if "--year" in args:
        i = args.index("--year")
        year_arg = int(args[i + 1])

    log("=" * 50)
    log(f"IDX REPORTS — {ticker}")
    log("=" * 50)

    report_data = fetch_reports(ticker, year=year_arg)

    conn = sqlite3.connect(DB_PATH)
    init_reports_db(conn)
    saved = save_reports(conn, ticker, report_data)
    log(f"Saved {saved} report file records to idx_reports")

    print_reports(report_data, ticker)

    if download:
        print()
        download_reports(conn, ticker, year=year_arg)

    conn.close()


def main():
    args = sys.argv[1:]

    if args and args[0] == "reports":
        cmd_reports(args[1:])
    else:
        cmd_summary(args)


if __name__ == "__main__":
    main()
