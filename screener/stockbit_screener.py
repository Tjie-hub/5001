"""
screener/stockbit_screener.py — Stockbit screener API integration

Fetches guru template results from exodus.stockbit.com/screener/templates/{id}
and optionally merges them with local keystats from walkforward.db.

Token is captured by intercepting Bearer tokens from the persistent browser
session (DS project's .browser_agent_state, known working).  Falls back to
the cached .stockbit_token file if the browser capture fails.
"""
import asyncio, json, os, time, sqlite3, requests
from datetime import date as _date
from pathlib import Path
from data.db import connect as db_connect

BASE_DIR = Path(__file__).resolve().parent.parent
# DS state is reliable — the walkforward state failed token capture previously
DS_STATE_DIR = Path(os.getenv("DS_STATE_DIR", str(Path.home() / "DS" / ".browser_agent_state")))
TOKEN_FILE    = BASE_DIR / ".stockbit_token"

STOCKBIT_BASE = "https://exodus.stockbit.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

GURU_TEMPLATES = {
    "high_volume_breakout": (63, "TEMPLATE_TYPE_GURU"),
    "foreign_flow_uptrend": (77, "TEMPLATE_TYPE_GURU"),
}

_cache: dict = {"token": None, "expires_at": 0.0}


# ── Token ─────────────────────────────────────────────────────────────────

async def _capture_async(state_dir: Path) -> str | None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(state_dir),
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        token = None

        def on_request(req):
            nonlocal token
            auth = req.headers.get("authorization", "")
            if auth.startswith("Bearer ") and "exodus.stockbit.com" in req.url:
                token = auth[7:]

        page.on("request", on_request)
        await page.goto("https://stockbit.com/screener", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        if not token:
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(3000)
        await ctx.close()
        return token


def _validate(token: str) -> bool:
    try:
        r = requests.get(
            f"{STOCKBIT_BASE}/keystats/BBCA",
            headers=_hdrs(token),
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_token() -> str | None:
    # In-memory cache (1 hour), re-validate if close to expiry
    if _cache["token"] and time.time() < _cache["expires_at"]:
        return _cache["token"]

    # Try .stockbit_token file — only if API says it's still valid
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text().strip()
        if t and _validate(t):
            _cache.update(token=t, expires_at=time.time() + 3600)
            return t

    # Capture fresh from browser
    try:
        token = asyncio.run(_capture_async(DS_STATE_DIR))
        if token:
            _cache.update(token=token, expires_at=time.time() + 3600)
            TOKEN_FILE.write_text(token)
            return token
    except Exception:
        pass

    return None


# ── API ───────────────────────────────────────────────────────────────────

def _hdrs(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": UA,
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/screener",
    }


def fetch_favorites(token: str | None = None) -> list[dict]:
    token = token or _get_token()
    if not token:
        return []
    r = requests.get(f"{STOCKBIT_BASE}/screener/favorites", headers=_hdrs(token), timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])


def fetch_template(template_id: int, template_type: str = "TEMPLATE_TYPE_GURU",
                   token: str | None = None) -> list[dict]:
    """
    Run a Stockbit screener template and return flat list of dicts.
    Each dict: {symbol, name, <MetricName>: raw_value, ...}
    """
    token = token or _get_token()
    if not token:
        return []

    url = f"{STOCKBIT_BASE}/screener/templates/{template_id}?type={template_type}"
    r = requests.get(url, headers=_hdrs(token), timeout=20)
    r.raise_for_status()
    calcs = r.json().get("data", {}).get("calcs", [])

    rows = []
    for entry in calcs:
        company = entry.get("company", {})
        row = {"symbol": company.get("symbol", ""), "name": company.get("name", "")}
        for result in entry.get("results", []):
            key = result.get("item", f"metric_{result.get('id')}")
            row[key] = result.get("raw")
            row[f"{key}_display"] = result.get("display")
        rows.append(row)
    return rows


def fetch_template_tickers(template_id: int, template_type: str = "TEMPLATE_TYPE_GURU",
                            token: str | None = None) -> list[str]:
    """Return just the ticker list from a Stockbit template (fast pre-filter)."""
    return [r["symbol"] for r in fetch_template(template_id, template_type, token)]


# ── Keystats join ─────────────────────────────────────────────────────────

_KEYSTATS_COLS = [
    "pe_ttm", "pe_ann", "pbv", "ps_ttm", "eps_ttm", "roe", "roa", "der",
    "npm", "rev_growth", "earn_growth", "div_yield", "ev_ebit", "market_cap",
    "current_ratio",
]


def _fetch_keystats(tickers: list[str], db_path: str) -> dict[str, dict]:
    if not tickers:
        return {}
    try:
        cols = ", ".join(f"k.{c}" for c in _KEYSTATS_COLS)
        placeholders = ",".join("?" * len(tickers))
        conn = db_connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT k.ticker, {cols}
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY fetch_date DESC) AS rn
                    FROM stockbit_keystats
                ) k
                WHERE k.rn = 1 AND k.ticker IN ({placeholders})""",
            tickers,
        ).fetchall()
        conn.close()
        return {r["ticker"]: dict(r) for r in rows}
    except Exception:
        return {}


# ── Combined result ───────────────────────────────────────────────────────

def run_screener(template_id: int, template_type: str = "TEMPLATE_TYPE_GURU",
                 db_path: str | None = None) -> dict:
    """
    Fetch a Stockbit screener template and merge with local keystats.

    Returns:
      { template_id, count, tickers, sb_metrics, results: [{ticker, name, <sb>..., <ks>...}] }
    """
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))

    rows = fetch_template(template_id, template_type)
    if not rows:
        return {"template_id": template_id, "count": 0, "tickers": [], "sb_metrics": [], "results": []}

    symbols = [r["symbol"] for r in rows]
    sb_by_sym = {r["symbol"]: r for r in rows}
    sb_metrics = [k for k in rows[0] if k not in ("symbol", "name") and not k.endswith("_display")]

    local = _fetch_keystats(symbols, db_path)

    results = []
    for sym in symbols:
        sb = sb_by_sym[sym]
        ks = local.get(sym, {})
        row = {"ticker": sym, "name": sb.get("name", "")}
        for m in sb_metrics:
            row[m] = sb.get(m)
            disp = sb.get(f"{m}_display")
            if disp:
                row[f"{m}_display"] = disp
        row.update({k: v for k, v in ks.items() if k != "ticker"})
        results.append(row)

    return {
        "template_id": template_id,
        "count": len(results),
        "tickers": symbols,
        "sb_metrics": sb_metrics,
        "results": results,
    }


# ── Persistence (scheduler integration) ─────────────────────────────────────
# The functions above (fetch_favorites/fetch_template/run_screener) were
# already working and are called on demand by screener/routes.py; nothing
# above this point is touched. These functions just give the scheduler
# somewhere to put the result of run_screener() so guru-template snapshots
# accumulate a history instead of being discarded after each web request.

def init_db(db_path: str | None = None) -> None:
    """Idempotent table creation — safe to call on every process start,
    mirrors stockbit_fetcher.init_flow_db()/init_agent_firm_tables()."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    conn = db_connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stockbit_screener_results (
            template_id   INTEGER NOT NULL,
            template_name TEXT NOT NULL,
            ticker        TEXT NOT NULL,
            fetch_date    TEXT NOT NULL,
            name          TEXT,
            metrics_json  TEXT,
            updated_at    TEXT NOT NULL,
            PRIMARY KEY (template_id, ticker, fetch_date)
        )
    """)
    conn.commit()
    conn.close()


def save_screener_results(conn, template_id: int, template_name: str, fetch_date: str,
                          results: list[dict]) -> int:
    """Insert or replace one row per ticker for (template_id, fetch_date).

    Idempotent: rerunning the same template_id/fetch_date (e.g. a same-day
    scheduler retry) replaces existing rows rather than duplicating them —
    same PRIMARY-KEY-based upsert pattern as stockbit_fetcher.save_keystats().
    Does not commit — caller owns the transaction, matching save_keystats().
    """
    from datetime import datetime as _dt
    now = _dt.now().isoformat()
    for row in results:
        ticker = row.get("symbol") or row.get("ticker")
        if not ticker:
            continue
        metrics = {k: v for k, v in row.items() if k not in ("symbol", "ticker", "name")}
        conn.execute(
            "INSERT OR REPLACE INTO stockbit_screener_results "
            "(template_id, template_name, ticker, fetch_date, name, metrics_json, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (template_id, template_name, ticker, fetch_date, row.get("name"),
             json.dumps(metrics), now),
        )
    return len(results)


def run_and_persist_screener(template_name: str, db_path: str | None = None,
                             fetch_date: str | None = None) -> dict:
    """Run a named GURU_TEMPLATES entry and persist its snapshot.

    This is the single entrypoint scheduler.jobs.run_stockbit_screener_fetch()
    calls — it wraps the existing run_screener()/fetch_template() collector
    (unchanged) with the new save_screener_results() upsert.
    """
    if template_name not in GURU_TEMPLATES:
        raise ValueError(f"Unknown Stockbit guru template: {template_name!r} "
                         f"(known: {sorted(GURU_TEMPLATES)})")
    template_id, template_type = GURU_TEMPLATES[template_name]
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    if fetch_date is None:
        fetch_date = str(_date.today())

    rows = fetch_template(template_id, template_type)

    conn = db_connect(db_path)
    try:
        saved = save_screener_results(conn, template_id, template_name, fetch_date, rows)
        conn.commit()
    finally:
        conn.close()

    return {
        "template_id": template_id,
        "template_name": template_name,
        "fetch_date": fetch_date,
        "count": saved,
    }
