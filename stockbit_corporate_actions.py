"""stockbit_corporate_actions.py — per-ticker corporate action event history.

Fills a real gap: the existing `corporate_actions` table (data/market_schema.py)
is sourced from yfinance and only ever holds dividends + splits — it has
never touched rights issues, bonus shares, warrants, or shareholder meetings
(RUPS) for IDX names, none of which yfinance carries at all. This module is
additive and does not touch that table, stockbit_fetcher.py, or
stockbit_broker_period.py.

Endpoint investigation (2026-08-05, live, authenticated — see also
docs comment at the bottom of this docstring for the rejected candidates):

  CONFIRMED, USED — GET {STOCKBIT_BASE}/corpaction/{ticker}
  Reverse-engineered from the public Next.js client bundle: the Redux action
  is GET_ALL_CORP_ACTION / `getAllCorpAction(ticker, limit=30)`, which calls
  this exact path with a `limit` query param. Tested live against BBCA,
  BRPT, ANTM, MEDC, GOTO and five more tickers — returns a JSON array under
  `data`, each entry `{"action_type": <str>, "action_info": {<action_type>:
  {...type-specific fields...}}}`. Six action_type values were observed live:
  dividend, rups (shareholder meeting), stocksplit, bonus, warrant,
  rightissue. `limit` is a NO-OP: requesting `limit=1`, `limit=2`, and
  `limit=5` on tickers with 22-26 known events all still returned the FULL
  history — verified by testing successively smaller limits against BRPT
  (22 events) and ANTM (26 events) and getting the full count back every
  time. `page` was also tested and had no effect. So: one call per ticker
  returns everything, no pagination logic is needed or implemented.

  REJECTED — GET {STOCKBIT_BASE}/corpaction/{category}?symbol={ticker}
  (Redux action GET_CORP_ACTION / `getCompanyCorpAction(symbol, category)`).
  Live-tested against BBCA with category=dividend: returned a strict subset
  (2 rows) of what GET /corpaction/BBCA already returns (30 rows, including
  those same 2 dividends). Category-filtering the already-complete per-ticker
  history client-side is simpler than calling this once per category per
  ticker, so this endpoint is not used.

  REJECTED — GET {STOCKBIT_BASE}/corpaction/{category} (no symbol — the
  market-wide "calendar" view backing Stockbit's corporate-action calendar
  UI, `GET_CALENDAR_RIGHTISSUE` etc. action names). Live-tested with
  category=rightissue: returned a market-wide list including a BAJA rights
  issue (rightissue_id=11545). Then called GET /corpaction/BAJA directly —
  the identical rightissue_id=11545 event was already present in BAJA's own
  per-ticker history. Confirmed redundant: looping GET /corpaction/{ticker}
  over the tracked universe (this collector's design, matching broker_flow's
  and broker_period_summary's existing per-ticker loop pattern) already
  surfaces every event this market-wide endpoint would; adding a second,
  differently-shaped fetch (looped over ~10 categories instead of tickers)
  for zero new data isn't worth the complexity. Noted here in case a future
  "what's coming up market-wide this week" feature wants it directly instead
  of deriving it from this table.

Normalization: field NAMING is inconsistent across action_type — most follow
an `{action_type}_id` / `{action_type}_exdate` convention (dividend_id/
dividend_exdate, rightissue_id/rightissue_exdate, stocksplit_id/
stocksplit_exdate, rups_id/rups_date) but two do not: `bonus`'s id field is
`sahambonus_id` (and its date fields are, oddly, `stocksplit_*`, a data
quirk on Stockbit's side, not a bug here) and `warrant`'s id field is
`wrant_id` (no `a`) with no `*_exdate`/`*_date` field at all. See
_extract_event_id()/_extract_event_date() for the generic (suffix-based, not
type-hardcoded) extraction that handles all six observed types plus
degrades safely for any future/unrecognized action_type — the full raw
payload is always preserved in raw_json regardless of whether normalization
succeeds, so nothing is ever lost even when a field name doesn't fit the
pattern.
"""
import json
import os
import requests
from datetime import date as _date, datetime as _datetime
from pathlib import Path

from data.db import connect as db_connect

BASE_DIR = Path(__file__).resolve().parent
STOCKBIT_BASE = "https://exodus.stockbit.com"

# Date-field suffixes, most-preferred first. Not a per-type lookup table —
# a generic priority scan so any future action_type with a reasonably named
# date field is picked up without a code change.
_DATE_SUFFIX_PRIORITY = ["exdate", "_date", "cumdate", "recdate", "trading_from", "created", "lastupdate"]


def _extract_event_id(action_type: str, info: dict) -> str | None:
    """Prefer `{action_type}_id`; otherwise the first non-iqp, non-company
    key ending in `_id` (covers bonus's sahambonus_id, warrant's wrant_id,
    and any future type following the same rough convention)."""
    direct = info.get(f"{action_type}_id")
    if direct:
        return str(direct)
    for k, v in info.items():
        if k.endswith("_id") and "iqp" not in k and "company" not in k and v:
            return str(v)
    return None


def _extract_event_date(action_type: str, info: dict) -> str | None:
    for suffix in _DATE_SUFFIX_PRIORITY:
        for k, v in info.items():
            if k.endswith(suffix) and v:
                return str(v)[:10]
    return None


def _normalize_event(ticker: str, raw_event: dict) -> dict | None:
    """One raw {"action_type", "action_info"} entry -> a flat row, or None
    if the entry is malformed (missing action_info for its own action_type —
    skipped rather than raising, so one bad row doesn't lose the rest of a
    ticker's history)."""
    action_type = raw_event.get("action_type")
    if not action_type:
        return None
    info = (raw_event.get("action_info") or {}).get(action_type)
    if not info:
        return None
    return {
        "ticker": ticker,
        "action_type": action_type,
        "event_id": _extract_event_id(action_type, info),
        "event_date": _extract_event_date(action_type, info),
        "raw": info,
    }


def fetch_corporate_actions(token: str, ticker: str):
    """GET corpaction/{ticker} — always the ticker's full history (see
    module docstring: `limit` is a confirmed no-op, not implemented here).
    Returns None on a non-200 response (same fail-soft contract as
    stockbit_fetcher.fetch_broker_flow)."""
    r = requests.get(
        f"{STOCKBIT_BASE}/corpaction/{ticker}",
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
    raw_events = r.json().get("data", []) or []
    rows = [row for row in (_normalize_event(ticker, e) for e in raw_events) if row is not None]
    return rows


# ── Persistence ──────────────────────────────────────────────────────────

def init_db(db_path: str | None = None) -> None:
    """Idempotent table creation — safe on every process start, mirrors
    stockbit_broker_period.init_db(). corporate_actions (yfinance-sourced,
    data/market_schema.py) is a separate, untouched table."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    conn = db_connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_action_events (
            ticker       TEXT NOT NULL,
            action_type  TEXT NOT NULL,
            event_id     TEXT NOT NULL,
            event_date   TEXT,
            raw_json     TEXT NOT NULL,
            fetch_date   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            PRIMARY KEY (ticker, action_type, event_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_corporate_action_events_date "
        "ON corporate_action_events(event_date)"
    )
    conn.commit()
    conn.close()


def save_corporate_actions(conn, ticker: str, fetch_date: str, rows: list[dict]) -> int:
    """Insert or replace one row per event, keyed by (ticker, action_type,
    event_id) — deliberately NOT including fetch_date in the key. Unlike
    broker_period_summary (a dated rolling-window snapshot, where the same
    ticker/period pair legitimately gets a new row every collection date),
    corporate actions are a stable event log: the same dividend_id refetched
    next week is the same event, possibly with updated fields (e.g. a
    provisional date firmed up) — it should overwrite in place, not
    accumulate a new dated copy. `fetch_date`/`updated_at` still track when
    each row was last (re)confirmed present via this collector.

    Events with no resolvable event_id (see _extract_event_id) are skipped,
    not inserted with a NULL primary-key column — silently accepting one
    would silently collide every unresolvable event from the same ticker
    into a single overwritten row.

    Does not commit — caller owns the transaction (matches
    stockbit_broker_period.save_broker_period_summary())."""
    now = _datetime.now().isoformat()
    saved = 0
    for row in rows:
        if not row.get("event_id"):
            continue
        conn.execute(
            "INSERT OR REPLACE INTO corporate_action_events "
            "(ticker, action_type, event_id, event_date, raw_json, fetch_date, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (ticker, row["action_type"], row["event_id"], row.get("event_date"),
             json.dumps(row["raw"]), fetch_date, now),
        )
        saved += 1
    return saved


def run_and_persist_corporate_actions(ticker: str, token: str, db_path: str | None = None,
                                      fetch_date: str | None = None) -> dict:
    """Fetch one ticker's corp-action history and persist it. Per-ticker
    granularity mirrors run_broker_flow_fetch()'s/run_broker_period_summary_
    fetch()'s loops in scheduler.jobs — one unit of work per ticker so one
    failure doesn't require redoing already-succeeded tickers."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    if fetch_date is None:
        fetch_date = _date.today().isoformat()

    rows = fetch_corporate_actions(token, ticker)
    if rows is None:
        raise RuntimeError(f"fetch_corporate_actions failed for {ticker} (non-200 response)")

    conn = db_connect(db_path)
    try:
        saved = save_corporate_actions(conn, ticker, fetch_date, rows)
        conn.commit()
    finally:
        conn.close()

    return {"ticker": ticker, "fetch_date": fetch_date, "count": saved}
