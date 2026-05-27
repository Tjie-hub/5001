#!/usr/bin/env python3
"""
Sectors Fetcher
===============
Scrapes sectors.app public pages via non-headless Playwright on virtual
display :99. Same architecture as idx_fetcher.py — different target,
no Cloudflare (sectors.app sits behind Vercel which Playwright passes).

Commands:
  python3 sectors_fetcher.py                       # fetch all (indices+sectors+dividends)
  python3 sectors_fetcher.py indices               # IDX index performance only
  python3 sectors_fetcher.py sectors               # sector heatmap only
  python3 sectors_fetcher.py dividends             # upcoming dividend calendar
  python3 sectors_fetcher.py --check               # show cache status
  python3 sectors_fetcher.py --refresh             # force re-fetch

Cron (daily 19:00 WIB, after IDX close + sectors.app digest update):
  0 19 * * 1-5 cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python3 sectors_fetcher.py >> logs/sectors_fetcher.log 2>&1
"""

import os, sys, json, time, sqlite3, re
from datetime import datetime
from pathlib import Path

# ── Config ──
_HERE             = Path(__file__).resolve().parent
DB_PATH           = _HERE / "data" / "walkforward.db"
LOG_FILE          = _HERE / "logs" / "sectors_fetcher.log"
CACHE_FILE        = _HERE / ".sectors_response_cache.json"
PLAYWRIGHT_BROWSERS = Path("/home/tjiesar/DS/.playwright")

SECTORS_BASE = "https://sectors.app"
UA           = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


# ── Logging ──
def log(msg):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── Browser session helper ──
def _browser_session(task_fn):
    """Launch non-headless Chromium, navigate sectors.app, run task_fn(page)."""
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
                locale="en-US",
            )
            await ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await ctx.new_page()
            result = await task_fn(page)
            await browser.close()
            return result

    return asyncio.run(_run())


# ── Parsing helpers ──
def _to_float(s):
    """Parse '1,234.56', '-12.50%', 'IDR 720.05T' → float. None on failure."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or s == "-":
        return None
    # Strip IDR prefix, % suffix, T/B/M multipliers handled separately
    s = re.sub(r"[+]", "", s).replace(",", "")
    s = re.sub(r"^IDR\s*", "", s, flags=re.I)
    s = s.replace("%", "")
    mult = 1.0
    if s.endswith("T"):
        mult, s = 1e12, s[:-1]
    elif s.endswith("B"):
        mult, s = 1e9, s[:-1]
    elif s.endswith("M"):
        mult, s = 1e6, s[:-1]
    try:
        return float(s) * mult
    except Exception:
        return None


def _to_trillion(s):
    """Parse '2,438.26T' → 2438.26 (kept in trillions for readability)."""
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("IDR", "").strip()
    if s.endswith("T"):
        s = s[:-1]
    try:
        return float(s)
    except Exception:
        return None


def _cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    try:
        age = time.time() - json.loads(CACHE_FILE.read_text()).get("_captured_at", 0)
        return age < 3600 * 12
    except Exception:
        return False


# ══════════════════════════════════════════════════════════
# INDICES & SECTORS  (both on /indonesia/indeks)
# ══════════════════════════════════════════════════════════

def fetch_indices_and_sectors() -> dict:
    """
    Scrape /indonesia/indeks. Page contains two tables:
      - IDX Index Performance (Featured, Branded, Sharia categories)
      - Sector Performance Table
    Returns {'indices': [...], 'sectors': [...]}.
    """
    log("Launching browser — fetching indices + sectors...")

    async def task(page):
        await page.goto(
            f"{SECTORS_BASE}/indonesia/indeks",
            wait_until="networkidle",
            timeout=30000,
        )
        # Wait for tables to render
        await page.wait_for_timeout(2500)

        # Extract all tables via JS — each table becomes list[list[str]]
        tables = await page.evaluate("""
            () => {
                const out = [];
                for (const t of document.querySelectorAll('table')) {
                    const rows = [];
                    for (const tr of t.querySelectorAll('tr')) {
                        const cells = [...tr.querySelectorAll('th, td')]
                            .map(c => c.innerText.trim().replace(/\\s+/g, ' '));
                        if (cells.length) rows.push(cells);
                    }
                    out.push(rows);
                }
                return out;
            }
        """)
        log(f"Captured {len(tables)} tables")
        return tables

    tables = _browser_session(task)
    return _parse_indices_and_sectors(tables)


def _parse_indices_and_sectors(tables: list) -> dict:
    """Two relevant tables: index perf and sector perf.
    Heuristic: rows with 'T' suffix on column 2 → sector; else → index.
    Category headers ('Featured Indices', etc.) span the row — detect by
    cells 1+ all being empty/dash."""
    indices, sectors = [], []
    current_cat = "uncategorized"

    def _is_category_header(row):
        if len(row) < 2:
            return True
        return all((not c or c.strip() in ("", "-")) for c in row[1:])

    for tbl in tables:
        for row in tbl:
            # Detect category header (spans whole row, first cell has label)
            if _is_category_header(row):
                hdr = row[0].lower() if row else ""
                if any(k in hdr for k in ("indices", "indeks", "sharia", "branded", "featured", "sector")):
                    current_cat = (
                        row[0]
                        .replace(" Indices", "")
                        .replace(" indices", "")
                        .strip()
                        .lower()
                    )
                continue

            # Skip table header
            if row and row[0].lower() in ("index", "sector", "indeks"):
                continue

            # Expect: [name, value/marketcap, 1d, 7d, 30d, 90d, 1y, YTD]
            if len(row) < 7:
                continue

            name = row[0].strip()
            if not name:
                continue

            # Heuristic: if the value cell ends with 'T' → sector row (market cap in trillions)
            value_cell = row[1].strip()
            is_sector  = value_cell.endswith("T")

            chg = {
                "1d":  _to_float(row[2]) if len(row) > 2 else None,
                "7d":  _to_float(row[3]) if len(row) > 3 else None,
                "30d": _to_float(row[4]) if len(row) > 4 else None,
                "90d": _to_float(row[5]) if len(row) > 5 else None,
                "1y":  _to_float(row[6]) if len(row) > 6 else None,
                "ytd": _to_float(row[7]) if len(row) > 7 else None,
            }

            if is_sector:
                sectors.append({
                    "sector":           name,
                    "market_cap_idr_t": _to_trillion(value_cell),
                    **chg,
                })
            else:
                indices.append({
                    "index_code": name,
                    "level":      _to_float(value_cell),
                    "category":   current_cat,
                    **chg,
                })

    log(f"Parsed {len(indices)} indices, {len(sectors)} sectors")
    return {"indices": indices, "sectors": sectors}


# ══════════════════════════════════════════════════════════
# DIVIDEND CALENDAR  (/indonesia/calendars/dividend-calendar)
# ══════════════════════════════════════════════════════════

def fetch_dividends() -> list[dict]:
    """Scrape upcoming dividends from card-style listings on the calendar page."""
    log("Launching browser — fetching dividend calendar...")

    async def task(page):
        await page.goto(
            f"{SECTORS_BASE}/indonesia/calendars/dividend-calendar",
            wait_until="networkidle",
            timeout=30000,
        )
        await page.wait_for_timeout(2500)

        # Each dividend card has shape: "TICKER\n<pay date>\nIDR <amount>\nEx-Dividend YYYY-MM-DD"
        # Grab text from elements containing all four signals at once.
        cards = await page.evaluate(r"""
            () => {
                const seen = new Set();
                const out = [];
                for (const el of document.querySelectorAll('div, li, article')) {
                    const t = (el.innerText || '').trim();
                    if (t.length > 500 || t.length < 20) continue;
                    if (!/Ex-Dividend\s+\d{4}-\d{2}-\d{2}/.test(t)) continue;
                    if (!/IDR\s+[\d,.]+/.test(t)) continue;
                    if (seen.has(t)) continue;
                    seen.add(t);
                    out.push(t);
                }
                return out;
            }
        """)
        log(f"Captured {len(cards)} dividend cards")
        return cards

    cards = _browser_session(task)
    return _parse_dividend_cards(cards)


def _parse_dividend_cards(cards: list[str]) -> list[dict]:
    """Parse text blocks like:
         GMTD
         22 May
         IDR 4.04
         Ex-Dividend 2026-05-06
    Use innermost (shortest) card per ticker+ex-date to avoid parent duplicates."""
    seen   = {}
    for raw in cards:
        # Pull the structural parts
        m_ex = re.search(r"Ex-Dividend\s+(\d{4}-\d{2}-\d{2})", raw)
        if not m_ex:
            continue
        ex_date = m_ex.group(1)

        m_div = re.search(r"IDR\s+([\d,]+(?:\.\d+)?)", raw)
        div_idr = _to_float(m_div.group(1)) if m_div else None

        m_yield = re.search(r"([\d.]+)%\s*Yield", raw)
        yield_pct = _to_float(m_yield.group(1)) if m_yield else None

        # Ticker is the first 3-5 letter all-caps token
        ticker = None
        for tok in re.findall(r"\b[A-Z]{3,5}\b", raw):
            if tok not in ("IDR",):
                ticker = tok
                break
        if not ticker:
            continue

        m_pay = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\b", raw)
        pay_date = None
        if m_pay:
            day, mon = int(m_pay.group(1)), m_pay.group(2).lower()
            # 3-letter month abbreviations
            mon_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                       "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
            for key, val in mon_map.items():
                if mon.startswith(key):
                    year = int(ex_date[:4])
                    # If payment month < ex month, payment likely in next year
                    if val < int(ex_date[5:7]):
                        year += 1
                    pay_date = f"{year}-{val:02d}-{day:02d}"
                    break

        key = (ticker, ex_date)
        # Prefer shortest source string (innermost element, least duplication)
        if key not in seen or len(raw) < len(seen[key]["_raw"]):
            seen[key] = {
                "ticker":       ticker,
                "ex_date":      ex_date,
                "payment_date": pay_date,
                "dividend_idr": div_idr,
                "yield_pct":    yield_pct,
                "_raw":         raw,
            }

    rows = [{k: v for k, v in r.items() if k != "_raw"} for r in seen.values()]
    log(f"Parsed {len(rows)} unique dividend records")
    return rows


_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June",
     "July","August","September","October","November","December"], start=1)}

def _parse_human_date(s: str) -> str | None:
    """'April 27, 2026' → '2026-04-27'."""
    if not s:
        return None
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", s.strip())
    if not m:
        return None
    mon = _MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"


# ══════════════════════════════════════════════════════════
# DB SCHEMA + WRITERS
# ══════════════════════════════════════════════════════════

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sectors_index_perf (
            fetch_date  TEXT NOT NULL,
            index_code  TEXT NOT NULL,
            level       REAL,
            chg_1d      REAL,
            chg_7d      REAL,
            chg_30d     REAL,
            chg_90d     REAL,
            chg_1y      REAL,
            chg_ytd     REAL,
            category    TEXT,
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (fetch_date, index_code)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sip_date ON sectors_index_perf(fetch_date)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sectors_sector_perf (
            fetch_date       TEXT NOT NULL,
            sector           TEXT NOT NULL,
            market_cap_idr_t REAL,
            chg_1d           REAL,
            chg_7d           REAL,
            chg_30d          REAL,
            chg_90d          REAL,
            chg_1y           REAL,
            chg_ytd          REAL,
            updated_at       TEXT NOT NULL,
            PRIMARY KEY (fetch_date, sector)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ssp_date ON sectors_sector_perf(fetch_date)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sectors_dividend_calendar (
            ticker       TEXT NOT NULL,
            ex_date      TEXT NOT NULL,
            payment_date TEXT,
            dividend_idr REAL,
            yield_pct    REAL,
            updated_at   TEXT NOT NULL,
            PRIMARY KEY (ticker, ex_date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sdc_ex ON sectors_dividend_calendar(ex_date)")
    conn.commit()


def save_indices(conn: sqlite3.Connection, indices: list[dict], fetch_date: str) -> int:
    now = datetime.now().isoformat()
    rows = [(
        fetch_date, r["index_code"], r.get("level"),
        r.get("1d"), r.get("7d"), r.get("30d"),
        r.get("90d"), r.get("1y"), r.get("ytd"),
        r.get("category"), now,
    ) for r in indices if r.get("index_code")]
    conn.executemany(
        """INSERT OR REPLACE INTO sectors_index_perf
           (fetch_date,index_code,level,chg_1d,chg_7d,chg_30d,chg_90d,chg_1y,chg_ytd,category,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def save_sectors(conn: sqlite3.Connection, sectors: list[dict], fetch_date: str) -> int:
    now = datetime.now().isoformat()
    rows = [(
        fetch_date, r["sector"], r.get("market_cap_idr_t"),
        r.get("1d"), r.get("7d"), r.get("30d"),
        r.get("90d"), r.get("1y"), r.get("ytd"),
        now,
    ) for r in sectors if r.get("sector")]
    conn.executemany(
        """INSERT OR REPLACE INTO sectors_sector_perf
           (fetch_date,sector,market_cap_idr_t,chg_1d,chg_7d,chg_30d,chg_90d,chg_1y,chg_ytd,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def save_dividends(conn: sqlite3.Connection, divs: list[dict]) -> int:
    now = datetime.now().isoformat()
    rows = [(
        r["ticker"], r["ex_date"], r.get("payment_date"),
        r.get("dividend_idr"), r.get("yield_pct"), now,
    ) for r in divs if r.get("ticker") and r.get("ex_date")]
    conn.executemany(
        """INSERT OR REPLACE INTO sectors_dividend_calendar
           (ticker,ex_date,payment_date,dividend_idr,yield_pct,updated_at)
           VALUES (?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


# ══════════════════════════════════════════════════════════
# PRINT HELPERS
# ══════════════════════════════════════════════════════════

def _pct(v):
    if v is None:
        return "      -"
    return f"{v:+7.2f}%"


def print_indices(indices: list[dict]):
    if not indices:
        print("No indices parsed")
        return
    hdr = f"{'Index':<14} {'Level':>12}  {'1d':>8} {'7d':>8} {'30d':>8} {'90d':>8} {'1y':>8} {'YTD':>8}  {'Category':<10}"
    print(hdr)
    print("-" * len(hdr))
    for r in indices:
        lvl = r.get("level")
        lvl_s = f"{lvl:>12,.2f}" if lvl is not None else f"{'-':>12}"
        print(f"{r['index_code']:<14} {lvl_s}  "
              f"{_pct(r.get('1d'))} {_pct(r.get('7d'))} {_pct(r.get('30d'))} "
              f"{_pct(r.get('90d'))} {_pct(r.get('1y'))} {_pct(r.get('ytd'))}  "
              f"{r.get('category','-'):<10}")


def print_sectors(sectors: list[dict]):
    if not sectors:
        print("No sectors parsed")
        return
    hdr = f"{'Sector':<32} {'MktCap (T)':>12}  {'1d':>8} {'7d':>8} {'30d':>8} {'90d':>8} {'1y':>8} {'YTD':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in sectors:
        mc = r.get("market_cap_idr_t")
        mc_s = f"{mc:>12,.2f}" if mc is not None else f"{'-':>12}"
        print(f"{r['sector'][:30]:<32} {mc_s}  "
              f"{_pct(r.get('1d'))} {_pct(r.get('7d'))} {_pct(r.get('30d'))} "
              f"{_pct(r.get('90d'))} {_pct(r.get('1y'))} {_pct(r.get('ytd'))}")


def print_dividends(divs: list[dict], limit: int = 30):
    if not divs:
        print("No dividends parsed")
        return
    divs_sorted = sorted(divs, key=lambda r: r.get("ex_date") or "")[:limit]
    hdr = f"{'Ticker':<8} {'Ex-Date':<12} {'Pay-Date':<12} {'Div (IDR)':>12} {'Yield':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in divs_sorted:
        div = r.get("dividend_idr")
        div_s = f"{div:>12,.2f}" if div is not None else f"{'-':>12}"
        yld   = r.get("yield_pct")
        yld_s = f"{yld:>7.2f}%" if yld is not None else f"{'-':>8}"
        print(f"{r['ticker']:<8} {r['ex_date']:<12} {(r.get('payment_date') or '-'):<12} {div_s} {yld_s}")


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def cmd_indices_and_sectors(args: list[str], do_indices=True, do_sectors=True):
    force = "--refresh" in args
    today = datetime.now().strftime("%Y-%m-%d")

    # Cached path
    if not force and _cache_valid():
        cache = json.loads(CACHE_FILE.read_text())
        data  = cache.get("indices_sectors", {})
        log(f"Using cached indices+sectors (age={int(time.time()-cache.get('_captured_at',0))}s)")
    else:
        data = fetch_indices_and_sectors()
        CACHE_FILE.write_text(json.dumps({
            "_captured_at": time.time(),
            "indices_sectors": data,
        }))

    indices = data.get("indices", [])
    sectors = data.get("sectors", [])

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    if do_indices:
        n = save_indices(conn, indices, today)
        log(f"Saved {n} index rows to sectors_index_perf")
    if do_sectors:
        n = save_sectors(conn, sectors, today)
        log(f"Saved {n} sector rows to sectors_sector_perf")
    conn.close()

    if do_indices:
        print("\n── IDX INDICES ──")
        print_indices(indices)
    if do_sectors:
        print("\n── SECTOR HEATMAP ──")
        print_sectors(sectors)


def cmd_dividends(args: list[str]):
    divs = fetch_dividends()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    n = save_dividends(conn, divs)
    log(f"Saved {n} dividend rows to sectors_dividend_calendar")
    conn.close()

    print("\n── UPCOMING DIVIDENDS ──")
    print_dividends(divs)


def cmd_check():
    if _cache_valid():
        cache = json.loads(CACHE_FILE.read_text())
        age   = int(time.time() - cache.get("_captured_at", 0))
        data  = cache.get("indices_sectors", {})
        log(f"Cache valid — indices={len(data.get('indices',[]))} sectors={len(data.get('sectors',[]))} age={age}s")
    else:
        log("Cache missing or expired (>12h)")


def main():
    args = sys.argv[1:]

    if "--check" in args:
        cmd_check()
        return

    if args and args[0] == "indices":
        cmd_indices_and_sectors(args[1:], do_indices=True, do_sectors=False)
    elif args and args[0] == "sectors":
        cmd_indices_and_sectors(args[1:], do_indices=False, do_sectors=True)
    elif args and args[0] == "dividends":
        cmd_dividends(args[1:])
    else:
        # Default: fetch everything
        log("=" * 50)
        log("SECTORS FETCHER — full run")
        log("=" * 50)
        cmd_indices_and_sectors(args, do_indices=True, do_sectors=True)
        cmd_dividends(args)


if __name__ == "__main__":
    main()
