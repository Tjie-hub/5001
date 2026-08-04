"""stockbit_broker_period.py — period-aggregated broker summary collector.

Complementary to broker_flow (stockbit_fetcher.py), which only ever stores a
single trading day's net broker buy/sell. This module answers a different
question: "which brokers have been accumulating/distributing THIS ticker
over the last week/month/quarter" — a rolling-window view broker_flow cannot
answer on its own (reconstructing it from 800+ tickers x N days of broker_flow
rows on every query is exactly the kind of repeated aggregation this table
exists to avoid doing ad hoc).

Endpoint investigation (2026-08-04, live, authenticated):
  Reuses the EXACT SAME endpoint, params, and response shape already used by
  stockbit_fetcher.fetch_broker_flow() — GET {STOCKBIT_BASE}/marketdetectors/
  {ticker} with transaction_type=TRANSACTION_TYPE_NET, market_board=
  MARKET_BOARD_REGULER, investor_type=INVESTOR_TYPE_ALL, limit=25, and a
  `from`/`to` date pair. fetch_broker_flow()'s own docstring already
  documented that from+to together select a historical single day; what
  hadn't been tested before is what happens when from != to. Verified live
  against BBCA: the response genuinely aggregates over the whole window
  (bandar_detector.value scales from ~516B for a single day to ~5.28T for a
  ~1-month window — a ~10x increase matching the ~22 trading days in range,
  not a replay of one day's number) and is stable/reproducible across repeat
  calls. No new endpoint, no undocumented parameter — just a wider,
  already-supported date range on an endpoint already in production use.

Two other candidates were investigated and ruled out:
  - GET order-trade/broker/top (Stockbit's "Top Brokers" widget, reached via
    Redux action GET_TOP_BROKER / financial.order_trade.entity.v1.
    BrokerSummaryPeriod enum in the client bundle): confirmed via live probe
    that its `symbol` query param is silently ignored — it returns the same
    89-row list regardless of ticker (or an invalid one). It's a market-wide
    top-broker leaderboard, not a per-ticker dataset, so it cannot answer
    "which brokers are accumulating THIS ticker" and isn't used here. Its
    numeric `period` values (0-10) WERE empirically decoded (0/1=today,
    2=last 7 days, 3=last 1 month, 4=last 1 year, 5=yesterday, 6=YTD,
    7=month-to-date, 8=last 3 months, 9=last 6 months, 10=previous calendar
    month) in case this endpoint becomes useful for a future market-wide
    broker-leaderboard feature, but they play no part in this collector.
  - GET findata-view/marketdetectors/brokers (Redux action GET_BROKER_LIST):
    a static reference list of all ~120 IDX member brokers (id/code/name/
    group) — not transactional data, not used here.

Periods supported: LAST_7_DAYS / LAST_1_MONTH / LAST_3_MONTHS. Chosen to
match the rolling windows Stockbit's own UI exposes for broker accumulation
analysis, computed client-side as plain calendar-day/month arithmetic against
the already-documented from/to params above (no reliance on the unverified
order-trade/broker/top period enum). Kept to three rather than the full set
Stockbit's UI offers (also 6mo/1yr/YTD/previous-month) to keep weekly request
volume proportionate — see scheduler.jobs.run_broker_period_summary_fetch()
for the cadence reasoning.
"""
import json
import os
import requests
from datetime import date as _date, datetime as _datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

from data.db import connect as db_connect

BASE_DIR = Path(__file__).resolve().parent
STOCKBIT_BASE = "https://exodus.stockbit.com"

PERIODS = {
    "LAST_7_DAYS": lambda today: today - relativedelta(days=6),
    "LAST_1_MONTH": lambda today: today - relativedelta(months=1),
    "LAST_3_MONTHS": lambda today: today - relativedelta(months=3),
}


def period_date_range(period_name: str, today=None) -> tuple[str, str]:
    """(from, to) ISO date strings for a named period, anchored to `today`
    (defaults to date.today()). `to` is always `today` itself."""
    if period_name not in PERIODS:
        raise ValueError(f"Unknown period: {period_name!r} (known: {sorted(PERIODS)})")
    if today is None:
        today = _date.today()
    frm = PERIODS[period_name](today)
    return frm.isoformat(), today.isoformat()


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _merge_broker_rows(broker_summary: dict) -> list[dict]:
    """Merge brokers_buy[]/brokers_sell[] (raw marketdetectors field names —
    see module docstring) into one row per broker_code with buy/sell
    volume+value as positive magnitudes (the API returns sell fields
    negative) and net_value = buy_value - sell_value. `rank` is NOT provided
    by the API — it's computed here by |net_value| descending, ties broken
    by broker_code for determinism.
    """
    buys = {}
    for b in broker_summary.get("brokers_buy", []) or []:
        code = b.get("netbs_broker_code")
        if not code:
            continue
        buys[code] = b

    sells = {}
    for s in broker_summary.get("brokers_sell", []) or []:
        code = s.get("netbs_broker_code")
        if not code:
            continue
        sells[code] = s

    rows = []
    for code in sorted(set(buys) | set(sells)):
        b = buys.get(code)
        s = sells.get(code)
        buy_volume = int(_num(b.get("blot"))) if b else 0
        buy_value = int(_num(b.get("bval"))) if b else 0
        sell_volume = abs(int(_num(s.get("slot")))) if s else 0
        sell_value = abs(int(_num(s.get("sval")))) if s else 0
        rows.append({
            "broker_code": code,
            "investor_type": (b or s or {}).get("type", ""),
            "buy_volume": buy_volume,
            "buy_value": buy_value,
            "sell_volume": sell_volume,
            "sell_value": sell_value,
            "net_value": buy_value - sell_value,
            "raw": {"buy": b, "sell": s},
        })

    rows.sort(key=lambda r: (-abs(r["net_value"]), r["broker_code"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def fetch_broker_period_summary(token: str, ticker: str, period_from: str, period_to: str):
    """GET marketdetectors/{ticker} for a period-wide from/to range. Same
    params/headers as stockbit_fetcher.fetch_broker_flow() (not imported —
    this module is deliberately standalone so it never touches that
    function), just a period-wide date range instead of a single day.
    Returns None on a non-200 response (same fail-soft contract as
    fetch_broker_flow).
    """
    params = {
        "transaction_type": "TRANSACTION_TYPE_NET",
        "market_board": "MARKET_BOARD_REGULER",
        "investor_type": "INVESTOR_TYPE_ALL",
        "limit": 25,
        "from": period_from,
        "to": period_to,
    }
    r = requests.get(
        f"{STOCKBIT_BASE}/marketdetectors/{ticker}",
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Origin": "https://stockbit.com",
            "Referer": "https://stockbit.com/",
        },
        timeout=20,
    )
    if r.status_code != 200:
        return None
    d = r.json().get("data", {})
    rows = _merge_broker_rows(d.get("broker_summary", {}))
    return {
        "ticker": ticker,
        "period_from": d.get("from", period_from),
        "period_to": d.get("to", period_to),
        "rows": rows,
    }


# ── Persistence ──────────────────────────────────────────────────────────

def init_db(db_path: str | None = None) -> None:
    """Idempotent table creation — safe on every process start, mirrors
    stockbit_fetcher.init_flow_db() (broker_flow is untouched; this is a new,
    separate table, not an extension of it)."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    conn = db_connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS broker_period_summary (
            ticker        TEXT NOT NULL,
            period        TEXT NOT NULL,
            fetch_date    TEXT NOT NULL,
            period_from   TEXT NOT NULL,
            period_to     TEXT NOT NULL,
            broker_code   TEXT NOT NULL,
            investor_type TEXT,
            buy_volume    INTEGER,
            buy_value     INTEGER,
            sell_volume   INTEGER,
            sell_value    INTEGER,
            net_value     INTEGER,
            rank          INTEGER,
            raw_json      TEXT,
            updated_at    TEXT NOT NULL,
            PRIMARY KEY (ticker, period, fetch_date, broker_code)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_broker_period_summary_lookup "
        "ON broker_period_summary(ticker, period, fetch_date)"
    )
    conn.commit()
    conn.close()


def save_broker_period_summary(conn, ticker: str, period: str, fetch_date: str,
                               period_from: str, period_to: str, rows: list[dict]) -> int:
    """Insert or replace one row per broker for (ticker, period, fetch_date).
    Idempotent: rerunning the same (ticker, period, fetch_date) — e.g. a
    same-week scheduler retry — replaces existing rows rather than
    duplicating them, matching the PRIMARY-KEY-based upsert pattern used by
    broker_flow/stockbit_keystats. Does not commit — caller owns the
    transaction (matches stockbit_fetcher.save_keystats())."""
    now = _datetime.now().isoformat()
    for row in rows:
        conn.execute(
            "INSERT OR REPLACE INTO broker_period_summary "
            "(ticker, period, fetch_date, period_from, period_to, broker_code, "
            "investor_type, buy_volume, buy_value, sell_volume, sell_value, "
            "net_value, rank, raw_json, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticker, period, fetch_date, period_from, period_to, row["broker_code"],
             row.get("investor_type"), row["buy_volume"], row["buy_value"],
             row["sell_volume"], row["sell_value"], row["net_value"], row["rank"],
             json.dumps(row.get("raw", {})), now),
        )
    return len(rows)


def run_and_persist_broker_period(ticker: str, period_name: str, token: str,
                                  db_path: str | None = None,
                                  fetch_date: str | None = None) -> dict:
    """Fetch one (ticker, period) snapshot and persist it. This is the
    per-(ticker, period) unit of work scheduler.jobs.
    run_broker_period_summary_fetch() loops over — mirrors run_flow()'s
    per-ticker granularity in stockbit_fetcher.py so one failure doesn't
    require redoing already-succeeded work.
    """
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    today = _date.fromisoformat(fetch_date) if fetch_date else _date.today()
    period_from, period_to = period_date_range(period_name, today=today)

    result = fetch_broker_period_summary(token, ticker, period_from, period_to)
    if result is None:
        raise RuntimeError(f"fetch_broker_period_summary failed for {ticker}/{period_name} "
                           f"(non-200 response)")

    snapshot_date = fetch_date or today.isoformat()
    conn = db_connect(db_path)
    try:
        saved = save_broker_period_summary(
            conn, ticker, period_name, snapshot_date,
            result["period_from"], result["period_to"], result["rows"],
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ticker": ticker,
        "period": period_name,
        "fetch_date": snapshot_date,
        "period_from": result["period_from"],
        "period_to": result["period_to"],
        "count": saved,
    }
