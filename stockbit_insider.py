"""stockbit_insider.py — per-ticker insider transaction event log.

Fills the gap flagged in stockbit_ownership.py's own investigation note
(2026-08-05): that module uses `insider/shareholding/composition/companies/
{ticker}` for a monthly point-in-time ownership snapshot, and separately
IDENTIFIED (but did not build a collector for) a second, structurally
different endpoint:

  GET {STOCKBIT_BASE}/insider/company/majorholder?symbol={ticker}&page={page}

  Per that note: live-tested against BBCA on 2026-08-05, genuinely paginated
  (page=1 -> 50 rows, is_more=true; page=2 -> remaining 35 rows, is_more=false;
  85 total), and the data is an individual insider BUY/SELL transaction event
  log — `previous`/`current`/`changes` share counts, `action_type`
  (ACTION_TYPE_BUY/SELL), `date`, `nationality`, director/commissioner
  `badges` — structurally closer to stockbit_corporate_actions.py's event-log
  model than to stockbit_ownership.py's composition/rank/percentage snapshot.
  That's why this is its own module with its own table, not an extension of
  either.

*** VERIFICATION STATUS — VERIFIED against a live response (BBCA,
2026-09-22, via a real bearer token pulled from Chrome DevTools since this
sandbox still can't reach exodus.stockbit.com directly). Three bugs found
and fixed from the originally-guessed field names:

  1. `_extract_page_rows` was looking for data["transactions"/"list"/
     "items"/"majorholders"] — the real key is data["movement"]. Every page
     came back 0 rows (200 OK, silently parsed empty) until this was added.
  2. `_num` unwrapped the {"value": ...} shape correctly but didn't strip
     the comma thousands separators ("193,206") or the leading "+" on
     changes ("+147,933") before float() — previous_shares/current_shares/
     changes_shares were always None. Now stripped.
  3. `date` is "DD Mon YY" (e.g. "25 Mar 26"), not ISO — now parsed with
     strptime instead of a naive str(...)[:10] slice, which stored the
     literal non-ISO string.

  Also: each row carries a real, stable "id" (e.g. "1000000439") that this
  docstring originally assumed didn't exist -- but it identifies the HOLDER
  (shareholder), not the individual transaction: the same id recurs across
  that holder's multiple historical movements on different dates (confirmed
  live: SANTOSO's id 1000000209 appears on both 2025-10-03 and 2026-03-25,
  with different changes_shares). Keying purely on (ticker, event_id) was
  tried first and silently collapsed BBCA's 85 rows down to 17 -- one per
  holder, losing every earlier movement -- before this was caught in
  testing. Adding event_date/action_type/changes_shares to the key wasn't
  enough either: live-tested again, BBCA komisaris JAHJA SETIAATMADJA
  (id 14413) made 4 same-day BUYs on 2025-03-18 that collapse two pairs of
  those columns to identical values (two +60,000 trades, two +118,000
  trades) -- 85 rows still landed as only 82. The table's primary key is
  now (ticker, event_id, event_date, action_type, changes_shares,
  current_shares): current_shares is a running balance, so it's what
  finally distinguishes same-day trades of the same size. Residual risk:
  two movements for the same holder landing on the exact same running
  balance would still collide -- accepted as a known limitation, the same
  tradeoff stockbit_corporate_actions.py's own composite key already makes,
  not a fabricated id.

Additive: does not import or touch stockbit_fetcher.py,
stockbit_broker_period.py, stockbit_corporate_actions.py, or
stockbit_ownership.py.
"""
import json
import os
import requests
from datetime import date as _date, datetime as _datetime
from pathlib import Path

from data.db import connect as db_connect

BASE_DIR = Path(__file__).resolve().parent
STOCKBIT_BASE = "https://exodus.stockbit.com"

# Safety valve against an infinite loop if the pagination-end signal is
# never recognized (wrong is_more key, or a page that echoes the same rows
# back) — 40 pages * 50 rows/page = 2000 transactions, far beyond any single
# ticker's realistic insider history (BBCA, a 50Y-old blue chip, had 85).
MAX_PAGES = 40


def _num(v, default=None):
    """Unwrap `{"raw": ...}` / `{"value": ...}` wrapper and parse the
    numeric string. CONFIRMED live (BBCA, 2026-09-22): majorholder wraps
    previous/current/changes as {"value": "193,206", "percentage": ...,
    "formatted_value": ...} -- comma thousands separators throughout, plus a
    leading "+" on changes (e.g. "+147,933"). Both are stripped before
    float() -- without this every previous_shares/current_shares/
    changes_shares came back None (ValueError swallowed by the except
    below)."""
    if isinstance(v, dict):
        v = v.get("raw", v.get("value"))
    if isinstance(v, str):
        v = v.replace(",", "").lstrip("+")
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _first(info: dict, *keys):
    """Return the first present, non-None value among several candidate key
    spellings. Used only for fields whose exact name isn't confirmed yet
    (see module docstring) — confirmed fields (action_type, date) use a
    direct .get()."""
    for k in keys:
        if k in info and info[k] is not None:
            return info[k]
    return None


def _normalize_transaction(ticker: str, raw_row: dict) -> dict | None:
    """One raw majorholder row -> a flat row. Returns None only if the row
    has neither a recognizable date nor action_type (nothing to key it by);
    every other field is best-effort and may be None — raw preserves the
    original regardless, matching stockbit_corporate_actions._normalize_event's
    fail-soft-but-don't-discard contract.

    CONFIRMED live (BBCA, 2026-09-22): action_type/date/name guessed right.
    date is "DD Mon YY" (e.g. "25 Mar 26"), not ISO — parsed here instead of
    the old naive str(...)[:10] slice, which would have stored the literal
    non-ISO string. Each row also carries a real, stable "id" (e.g.
    "1000000439") — but it identifies the HOLDER, not the transaction (see
    module docstring); stored as event_id and combined with event_date/
    action_type/changes_shares in the table's primary key, never used
    alone."""
    action_type = raw_row.get("action_type")
    event_date_raw = _first(raw_row, "date", "transaction_date", "action_date")
    if not action_type and not event_date_raw:
        return None
    event_date = None
    if event_date_raw:
        try:
            event_date = _datetime.strptime(str(event_date_raw), "%d %b %y").date().isoformat()
        except ValueError:
            event_date = str(event_date_raw)[:10]  # unrecognized format -- keep rather than lose
    holder_name = _first(raw_row, "name", "holder_name", "full_name", "insider_name")
    return {
        "ticker": ticker,
        "event_id": raw_row.get("id"),
        "event_date": event_date,
        "holder_name": holder_name,
        "action_type": action_type,
        "previous_shares": _num(raw_row.get("previous")),
        "current_shares": _num(raw_row.get("current")),
        "changes_shares": _num(raw_row.get("changes")),
        "nationality": raw_row.get("nationality"),
        "badges": json.dumps(raw_row.get("badges")) if raw_row.get("badges") is not None else None,
        "raw": raw_row,
    }


def _extract_page_rows(payload: dict) -> tuple[list, bool]:
    """(rows, is_more) from one page's JSON. `data` is either the row list
    directly (corpaction's convention) or a dict wrapping it (ownership's
    convention) — handle both. CONFIRMED live (BBCA, 2026-09-22): the row
    list is under data["movement"] (checked first below) and is_more is
    data["is_more"] -- neither "transactions"/"list"/"items"/"majorholders"
    matched, so before this fix every page came back with 0 rows (200 OK,
    parsed as empty) despite the endpoint returning full data. The other
    guessed keys are kept as fallback in case the shape ever changes."""
    data = payload.get("data")
    if isinstance(data, list):
        rows, is_more = data, payload.get("is_more")
    elif isinstance(data, dict):
        rows = (data.get("movement") or data.get("transactions") or data.get("list")
                or data.get("items") or data.get("majorholders") or [])
        is_more = data.get("is_more", payload.get("is_more"))
    else:
        rows, is_more = [], None
    return rows, bool(is_more) if is_more is not None else None


def fetch_insider_transactions(token: str, ticker: str):
    """GET insider/company/majorholder?symbol={ticker}, paginated. Returns
    a list of fetch_insider_transactions-shaped dicts (via
    _normalize_transaction), or None on a non-200 first-page response (same
    fail-soft contract as the other collectors' fetch_*() functions). A
    failure on a page AFTER the first returns what was collected so far
    rather than discarding it — one bad page shouldn't lose an otherwise-
    complete history."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Origin": "https://stockbit.com",
        "Referer": "https://stockbit.com/",
    }
    all_rows = []
    prev_page_len = None
    for page in range(1, MAX_PAGES + 1):
        r = requests.get(
            f"{STOCKBIT_BASE}/insider/company/majorholder",
            params={"symbol": ticker, "page": page},
            headers=headers,
            timeout=20,
        )
        if r.status_code != 200:
            if page == 1:
                return None
            break
        page_rows, is_more = _extract_page_rows(r.json())
        if not page_rows:
            break
        all_rows.extend(page_rows)
        if is_more is False:
            break
        if is_more is None and prev_page_len is not None and len(page_rows) < prev_page_len:
            # No is_more signal recognized; a shorter-than-previous page is
            # the same "last page" signature documented for BBCA (50 then 35).
            break
        prev_page_len = len(page_rows)

    rows = [row for row in (_normalize_transaction(ticker, r) for r in all_rows) if row is not None]
    return rows


# ── Persistence ──────────────────────────────────────────────────────────

def init_db(db_path: str | None = None) -> None:
    """Idempotent table creation — mirrors stockbit_corporate_actions.init_db()
    (this is a stable transaction event log, same reasoning as
    corporate_action_events, not a dated rolling snapshot like
    broker_period_summary/ownership_composition). Table not yet created in
    production as of 2026-09-22, so this schema ships clean -- no migration
    from an older version needed. Primary key is (ticker, event_id,
    event_date, action_type, changes_shares, current_shares) -- NOT
    event_id alone, which identifies the holder, not the transaction (see
    module docstring). current_shares (the running balance after the
    transaction) is included because a single active holder can make
    several same-day trades of the identical share size: confirmed live,
    BBCA komisaris JAHJA SETIAATMADJA (id 14413) made 4 same-day BUYs on
    2025-03-18, two of them both +60,000 shares and two both +118,000 --
    identical on every other column, but current_shares (the running
    balance: ...35,449,144 -> 35,567,144 -> 35,685,144 -> 35,745,144 ->
    35,805,144) is different for each and makes each row unique."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    conn = db_connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS insider_transactions (
            ticker           TEXT NOT NULL,
            event_id         TEXT,
            event_date       TEXT,
            holder_name      TEXT,
            action_type      TEXT,
            previous_shares  REAL,
            current_shares   REAL,
            changes_shares   REAL,
            nationality      TEXT,
            badges           TEXT,
            raw_json         TEXT NOT NULL,
            fetch_date       TEXT NOT NULL,
            updated_at       TEXT NOT NULL,
            PRIMARY KEY (ticker, event_id, event_date, action_type, changes_shares, current_shares)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_insider_transactions_lookup "
        "ON insider_transactions(ticker, event_date)"
    )
    conn.commit()
    conn.close()


def save_insider_transactions(conn, ticker: str, fetch_date: str, rows: list[dict]) -> int:
    """Insert or replace one row per transaction, keyed by (ticker,
    event_id, event_date, action_type, changes_shares, current_shares).
    event_id alone is NOT unique per transaction -- it identifies the
    holder and recurs across that holder's separate movements; nor is
    (event_id, event_date, action_type, changes_shares) enough on its own
    -- one active holder can make several same-day trades of the identical
    share size (confirmed live 2026-09-22, see module docstring).
    current_shares (a running balance) is what finally makes each row
    unique. Does not commit — caller owns the transaction."""
    now = _datetime.now().isoformat()
    saved = 0
    for row in rows:
        conn.execute(
            "INSERT OR REPLACE INTO insider_transactions "
            "(ticker, event_id, event_date, holder_name, action_type, previous_shares, "
            "current_shares, changes_shares, nationality, badges, raw_json, "
            "fetch_date, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row["ticker"], row["event_id"], row["event_date"], row["holder_name"], row["action_type"],
             row["previous_shares"], row["current_shares"], row["changes_shares"],
             row["nationality"], row["badges"], json.dumps(row["raw"]), fetch_date, now),
        )
        saved += 1
    return saved


def run_and_persist_insider(ticker: str, token: str, db_path: str | None = None,
                            fetch_date: str | None = None) -> dict:
    """Fetch one ticker's insider transaction history and persist it.
    Per-ticker granularity mirrors the other four collectors' scheduler
    loops."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    if fetch_date is None:
        fetch_date = _date.today().isoformat()

    rows = fetch_insider_transactions(token, ticker)
    if rows is None:
        raise RuntimeError(f"fetch_insider_transactions failed for {ticker} "
                           f"(non-200 response on first page)")

    conn = db_connect(db_path)
    try:
        saved = save_insider_transactions(conn, ticker, fetch_date, rows)
        conn.commit()
    finally:
        conn.close()

    return {"ticker": ticker, "fetch_date": fetch_date, "count": saved}
