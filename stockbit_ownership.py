"""stockbit_ownership.py — monthly per-ticker ownership composition/distribution.

Additive and independent from every other collector in this repo (does not
import or touch stockbit_fetcher.py, stockbit_broker_period.py, or
stockbit_corporate_actions.py). Fills a genuine gap: nothing in the pipeline
today captures ownership structure, float concentration, or major
shareholder identity for any ticker.

Endpoint investigation (2026-08-05, live, authenticated; validation only —
no behavior was inferred from JS/Redux action names alone):

  CONFIRMED, USED — GET {STOCKBIT_BASE}/insider/shareholding/composition/
  companies/{ticker}
  Live-tested against BBCA, BRPT, ANTM, TLKM, GOTO, ASII. Returns
  `data.periods[]`, each period `{report_date, total_shares, compositions:
  [{label, shares, percentage, colors}]}`. `compositions` is a single list
  mixing two conceptually different row kinds with NO field distinguishing
  them — named entities/individuals (e.g. "DWIMURIA INVESTAMA ANDALAN") and
  aggregate investor-type buckets (e.g. "Mutual Funds", "Pension Funds")
  — sorted by percentage descending (verified: BBCA's list runs 54.94% down
  to 0.00% across 37 rows, with named holders interleaved among category
  buckets at their actual rank, not segregated). Only ONE period was ever
  returned by any ticker tested (`len(data.periods) == 1` in all 6 live
  calls) — no historical backfill is available through this endpoint.

  Update cadence, empirically determined (not assumed): all 5 tickers
  independently tested (BBCA/BRPT/ANTM/TLKM/GOTO/ASII) returned the
  IDENTICAL `report_date: "2026-07-31"` on 2026-08-05 — the exact last
  calendar day of the prior month, uniformly across completely unrelated
  companies. That pattern (same date, every ticker, landing precisely on a
  month-end) is the signature of a monthly market-wide registry publication
  (KSEI-style shareholder composition, standard for IDX), not a per-company
  continuously-updated feed. See scheduler.jobs.run_ownership_fetch()'s
  docstring for how this evidence drove the scheduling decision.

  IDENTIFIED, NOT USED (out of scope for this collector, not "redundant/
  incomplete/non-transactional") — GET {STOCKBIT_BASE}/insider/company/
  majorholder?symbol={ticker}&page={page}. Live-tested against BBCA:
  genuinely paginated (page=1 returned 50 rows with is_more=true, page=2
  returned the remaining 35, is_more=false — 85 total), and the data is
  real: individual insider buy/sell transactions over time (`previous`/
  `current`/`changes` share counts, `action_type`: ACTION_TYPE_BUY/SELL,
  `date`, `nationality`, director/commissioner `badges`). This is a
  genuinely different dataset shape — an insider TRANSACTION event log,
  structurally closer to stockbit_corporate_actions.py's event-log model
  than to a point-in-time ownership snapshot — and doesn't fit the
  composition/rank/percentage schema this task specifies. Not rejected as
  bad data; simply a separate "insider trading activity" collector this
  task's schema doesn't cover. Noted here for a possible future task.

Normalization: `holder_category`/`holder_type` is deliberately NOT populated
via a hardcoded label-matching heuristic (e.g. "labels matching a known
category list are buckets, everything else is a named holder") — the API
itself provides no such flag, and guessing one would be exactly the kind of
inferred-not-validated behavior this investigation was told to avoid. Only
`holder_label` (the literal `label` field, whatever it is) is stored;
raw_json preserves the row unmodified for any future reclassification.
"""
import json
import os
import requests
from datetime import date as _date, datetime as _datetime
from pathlib import Path

from data.db import connect as db_connect

BASE_DIR = Path(__file__).resolve().parent
STOCKBIT_BASE = "https://exodus.stockbit.com"


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _normalize_composition(ticker: str, period: dict) -> list[dict]:
    """One `data.periods[0]` dict -> a list of flat rows, one per holder/
    category entry. Entries with no `label` are skipped (nothing to key
    them by) — rank counts only the rows actually kept, so ranks stay
    contiguous starting at 1."""
    report_date = period.get("report_date")
    total_shares_raw = (period.get("total_shares") or {}).get("raw")
    total_shares = int(_num(total_shares_raw)) if _num(total_shares_raw) is not None else None

    rows = []
    for entry in period.get("compositions", []) or []:
        label = entry.get("label")
        if not label:
            continue
        shares_val = _num((entry.get("shares") or {}).get("raw"))
        pct_val = _num((entry.get("percentage") or {}).get("raw"))
        rows.append({
            "ticker": ticker,
            "report_date": report_date,
            "holder_label": label,
            "rank": len(rows) + 1,
            "shares": int(shares_val) if shares_val is not None else None,
            "percentage": pct_val,
            "total_shares": total_shares,
            "raw": entry,
        })
    return rows


def fetch_ownership_composition(token: str, ticker: str):
    """GET insider/shareholding/composition/companies/{ticker}. Returns
    None on a non-200 response or when the API returns zero periods (same
    fail-soft contract as the other collectors' fetch_*() functions)."""
    r = requests.get(
        f"{STOCKBIT_BASE}/insider/shareholding/composition/companies/{ticker}",
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
    periods = r.json().get("data", {}).get("periods", []) or []
    if not periods:
        return None
    return _normalize_composition(ticker, periods[0])


# ── Persistence ──────────────────────────────────────────────────────────

def init_db(db_path: str | None = None) -> None:
    """Idempotent table creation — safe on every process start, mirrors
    stockbit_corporate_actions.init_db()."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    conn = db_connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ownership_composition (
            ticker        TEXT NOT NULL,
            report_date   TEXT NOT NULL,
            holder_label  TEXT NOT NULL,
            rank          INTEGER NOT NULL,
            shares        INTEGER,
            percentage    REAL,
            total_shares  INTEGER,
            raw_json      TEXT NOT NULL,
            fetch_date    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            PRIMARY KEY (ticker, report_date, holder_label)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ownership_composition_lookup "
        "ON ownership_composition(ticker, report_date)"
    )
    conn.commit()
    conn.close()


def save_ownership_composition(conn, fetch_date: str, rows: list[dict]) -> int:
    """Insert or replace one row per (ticker, report_date, holder_label).
    Idempotent: rerunning the same ticker for the same report_date (e.g. a
    same-month scheduler retry) replaces existing rows rather than
    duplicating them. Keyed BY report_date (unlike corporate_action_events'
    stable event log) because a new report_date is genuinely new
    information — next month's composition snapshot must not overwrite
    this month's, matching broker_period_summary's dated-snapshot model.
    Does not commit — caller owns the transaction."""
    now = _datetime.now().isoformat()
    saved = 0
    for row in rows:
        conn.execute(
            "INSERT OR REPLACE INTO ownership_composition "
            "(ticker, report_date, holder_label, rank, shares, percentage, "
            "total_shares, raw_json, fetch_date, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (row["ticker"], row["report_date"], row["holder_label"], row["rank"],
             row["shares"], row["percentage"], row["total_shares"],
             json.dumps(row["raw"]), fetch_date, now),
        )
        saved += 1
    return saved


def run_and_persist_ownership(ticker: str, token: str, db_path: str | None = None,
                              fetch_date: str | None = None) -> dict:
    """Fetch one ticker's ownership composition and persist it. Per-ticker
    granularity mirrors the other three collectors' scheduler loops."""
    if db_path is None:
        db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "walkforward.db"))
    if fetch_date is None:
        fetch_date = _date.today().isoformat()

    rows = fetch_ownership_composition(token, ticker)
    if rows is None:
        raise RuntimeError(f"fetch_ownership_composition failed for {ticker} "
                           f"(non-200 response or no periods returned)")

    conn = db_connect(db_path)
    try:
        saved = save_ownership_composition(conn, fetch_date, rows)
        conn.commit()
    finally:
        conn.close()

    report_date = rows[0]["report_date"] if rows else None
    return {"ticker": ticker, "fetch_date": fetch_date, "report_date": report_date, "count": saved}
