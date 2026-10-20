"""Global + Indonesian macro series, stored daily in ``macro_daily`` (series, date, value).

Why this exists: the 08:45 premarket briefing (engine/external_macro.py) pulled a handful of
overnight levels into a Telegram block and kept nothing, so after the 2026-10-16 MSCI shock there
was no stored record of VIX, US yields, the rupiah, oil, gold or the regional indices to look back
on. This module keeps one row per series per date so the history is queryable.

Sources, and what is deliberately NOT here:
  - yfinance: world/Asia indices, VIX, US Treasury yields (^TNX etc. are quoted in percent),
    DXY, USD/IDR, USD/CNY, EIDO (US-listed Indonesia ETF: foreign sentiment read overnight),
    WTI/Brent, gold, copper, aluminium, and BTU (Peabody) as an equity-grade coal PROXY.
  - bi.go.id (official): BI-Rate decisions (dated by the board meeting) and CPI inflation YoY
    (dated the first of the month it describes).
  - Newcastle coal, Malaysian CPO, LME nickel, SBN 10Y yield and Indonesia 5Y CDS have no free
    official daily source (Yahoo returns nothing; see docs/research_programs/P-M/data_acquisition/
    04_CROSS_ASSET_SERIES_FEASIBILITY_2026-09-30.md). The sites that show them forbid scraping,
    so they are left out rather than scraped.

Fail-soft by design: one series failing is logged and skipped; nothing here raises into the
scheduler. Rows are upserted, so re-running a window is idempotent.
"""
from __future__ import annotations

import html as _html
import logging
import re
from datetime import datetime, timezone

from data.db import connect

logger = logging.getLogger(__name__)

# (series key, yfinance symbol, group, label)
YAHOO_SERIES: list[tuple[str, str, str, str]] = [
    ("sp500", "^GSPC", "global", "S&P 500"),
    ("nasdaq", "^IXIC", "global", "Nasdaq Composite"),
    ("dow", "^DJI", "global", "Dow Jones"),
    ("vix", "^VIX", "global", "VIX"),
    ("nikkei", "^N225", "asia", "Nikkei 225"),
    ("hangseng", "^HSI", "asia", "Hang Seng"),
    ("kospi", "^KS11", "asia", "KOSPI"),
    ("shanghai", "000001.SS", "asia", "Shanghai Composite"),
    ("sti", "^STI", "asia", "Straits Times"),
    ("ihsg", "^JKSE", "indonesia", "IHSG"),
    ("eido", "EIDO", "indonesia", "iShares MSCI Indonesia ETF (USD)"),
    ("usdidr", "USDIDR=X", "fx", "USD/IDR"),
    ("usdcny", "CNY=X", "fx", "USD/CNY"),
    ("dxy", "DX-Y.NYB", "fx", "US Dollar Index"),
    ("ust3m", "^IRX", "rates", "US 13-week T-bill yield (%)"),
    ("ust5y", "^FVX", "rates", "US 5Y Treasury yield (%)"),
    ("ust10y", "^TNX", "rates", "US 10Y Treasury yield (%)"),
    ("wti", "CL=F", "commodity", "WTI crude (USD/bbl)"),
    ("brent", "BZ=F", "commodity", "Brent crude (USD/bbl)"),
    ("gold", "GC=F", "commodity", "Gold (USD/oz)"),
    ("copper", "HG=F", "commodity", "Copper (USD/lb)"),
    ("aluminium", "ALI=F", "commodity", "Aluminium (USD/t)"),
    ("coal_proxy_btu", "BTU", "commodity", "Peabody Energy (coal equity proxy, not a coal price)"),
]

BI_RATE_URL = "https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx"
BI_INFLATION_URL = "https://www.bi.go.id/id/statistik/indikator/data-inflasi.aspx"

_MONTHS_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
    "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}
_MONTH_RE = "|".join(_MONTHS_ID)


def ensure_macro_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS macro_daily ("
        " series TEXT NOT NULL, date TEXT NOT NULL, value REAL NOT NULL,"
        " source TEXT NOT NULL, fetched_at TEXT NOT NULL,"
        " PRIMARY KEY (series, date))")
    conn.commit()


def upsert(conn, rows: list[tuple[str, str, float, str]]) -> int:
    """rows: (series, date YYYY-MM-DD, value, source). Later fetches overwrite a date's value,
    which is what a provisional last bar (Yahoo's still-trading session) needs."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.executemany(
            "INSERT INTO macro_daily (series, date, value, source, fetched_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(series, date) DO UPDATE SET value=excluded.value, source=excluded.source, "
            "fetched_at=excluded.fetched_at",
            [(s, d, float(v), src, now) for s, d, v, src in rows])
    return len(rows)


def _page_text(raw: str) -> str:
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parse_bi_rate(raw_html: str) -> list[tuple[str, float]]:
    """[(decision date, rate %)] from BI's BI-Rate table ('23 September 2026 5,75 %')."""
    out = {}
    for d, m, y, v in re.findall(rf"\b(\d{{1,2}}) ({_MONTH_RE}) (20\d\d) (\d{{1,2}},\d{{2}}) ?%",
                                 _page_text(raw_html), flags=re.I):
        out[f"{y}-{_MONTHS_ID[m.lower()]:02d}-{int(d):02d}"] = _num(v)
    return sorted(out.items())


def parse_bi_inflation(raw_html: str) -> list[tuple[str, float]]:
    """[(first of month, CPI YoY %)] from BI's inflation table ('Agustus 2026 3,19 %').
    Negative prints (deflation) keep their sign."""
    out = {}
    for m, y, v in re.findall(rf"\b({_MONTH_RE}) (20\d\d) (-?\d{{1,2}},\d{{2}}) ?%",
                              _page_text(raw_html), flags=re.I):
        out.setdefault(f"{y}-{_MONTHS_ID[m.lower()]:02d}-01", _num(v))
    return sorted(out.items())


def fetch_yahoo(period: str = "10d") -> tuple[list, list[str]]:
    import yfinance as yf

    rows, failed = [], []
    for key, sym, _group, _label in YAHOO_SERIES:
        try:
            df = yf.download(sym, period=period, auto_adjust=True, progress=False)
            close = df["Close"].squeeze().dropna() if df is not None and len(df) else []
            if not len(close):
                failed.append(key)
                continue
            rows += [(key, ts.strftime("%Y-%m-%d"), float(v), f"yahoo:{sym}") for ts, v in close.items()]
        except Exception as e:  # network/parse: skip this series, keep the rest
            logger.warning(f"[macro] {key} ({sym}) failed: {e}")
            failed.append(key)
    return rows, failed


# bi.go.id's firewall resets connections that don't look like a browser (a bare
# "Mozilla/5.0" UA was reset on 2026-10-20), and also resets intermittently: hence full
# browser headers and one retry.
_BI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


def _get_bi(url: str) -> str:
    import time

    import requests

    for attempt in (1, 2):
        try:
            r = requests.get(url, timeout=30, headers=_BI_HEADERS)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5)


def fetch_bi() -> tuple[list, list[str]]:
    rows, failed = [], []
    for key, url, parse in (("bi_rate", BI_RATE_URL, parse_bi_rate),
                            ("cpi_yoy", BI_INFLATION_URL, parse_bi_inflation)):
        try:
            got = parse(_get_bi(url))
            if not got:  # page layout changed: say so instead of storing nothing silently
                raise ValueError("no rows parsed")
            rows += [(key, d, v, "bi.go.id") for d, v in got]
        except Exception as e:
            logger.warning(f"[macro] {key} failed: {e}")
            failed.append(key)
    return rows, failed


def run_macro_fetch(db_path=None, period: str = "10d", fetchers=None) -> dict:
    """Fetch every source and upsert. ``fetchers`` is injectable for tests."""
    fetchers = fetchers or (lambda: fetch_yahoo(period), fetch_bi)
    rows, failed = [], []
    for f in fetchers:
        r, bad = f()
        rows += r
        failed += bad
    conn = connect(db_path)
    try:
        ensure_macro_table(conn)
        n = upsert(conn, rows) if rows else 0
    finally:
        conn.close()
    return {"rows": n, "series": len({r[0] for r in rows}), "failed": failed}


if __name__ == "__main__":  # python -m data.macro [--backfill]
    import sys

    logging.basicConfig(level=logging.INFO)
    print(run_macro_fetch(period="10y" if "--backfill" in sys.argv else "10d"))
