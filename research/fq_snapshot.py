"""FQ forward-PIT keystats snapshot — append-only monthly capture via Stockbit exodus.

Spec (feat/fq-keystats-snapshot, 2026-09-30, NOT scheduled, NOT merged):
- Universe: the declared research universe — month-end top-200 by ADV60 among names with a
  real print (volume > 0), ADV60 >= Rp 1bn, close >= Rp 50 (UNIVERSE_BENCHMARK_MEMO_2026-09-30).
  Universe selection reads raw rows with a simple parameterized SELECT and ranks in Python.
- Source: https://exodus.stockbit.com/keystats/<TICKER> with the existing .stockbit_token JWT
  (same access stockbit_fetcher uses). No new credentials.
- Storage: append-only table `fq_keystats_snapshot` in the RESEARCH database. Plain INSERTs
  only — a re-fetch of the same ticker/month appends a new row keyed by fetched_at, so the
  capture history is never overwritten. No UPDATE, no DELETE, no REPLACE anywhere.
- Fields kept: pe_ttm, pbv, roe, eps_ttm, market_cap, shares — plus the RAW response JSON so a
  parsing fix never requires re-fetching history.
- Rate limits: >= REQUEST_INTERVAL_S between requests, hard cap MAX_TICKERS_PER_RUN per run.
- Failure handling: per-ticker try/except — one bad ticker never stops the run; HTTP 401/403
  raises KeystatsAuthError (caller refreshes the token via auto_token.py); failures are
  returned, not written.

CLI (manual, never cron):
    python -m research.fq_snapshot --limit 50
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import requests

from config import DB_PATH
from data.db import connect as db_connect

logger = logging.getLogger(__name__)

RESEARCH_DB = os.getenv("RESEARCH_DB_PATH",
                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "data", "research.db"))
EXODUS_KEYSTATS_URL = "https://exodus.stockbit.com/keystats/{ticker}"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Origin": "https://stockbit.com",
    "Referer": "https://stockbit.com/",
}
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          ".stockbit_token")
REQUEST_INTERVAL_S = 1.5
MAX_TICKERS_PER_RUN = 50
TIMEOUT_S = 10
ADV60_MIN_IDR = 1e9
PRICE_MIN_IDR = 50
_MICROSECOND = __import__("datetime").timedelta(microseconds=1)

# response-key candidates, tried in order (exact shape undocumented; raw_json is authoritative)
_FIELD_KEYS = {
    "pe_ttm": ["pe_ttm", "pe", "per", "price_earnings"],
    "pbv": ["pbv", "pb", "pbr", "price_book"],
    "roe": ["roe", "return_on_equity"],
    "eps_ttm": ["eps_ttm", "eps"],
    "market_cap": ["market_cap", "marketcap", "market_capitalization"],
    "shares": ["shares_outstanding", "shares", "total_shares", "share_outstanding"],
}


class KeystatsAuthError(RuntimeError):
    """Token missing/invalid — refresh via auto_token.py, then retry."""


def init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fq_keystats_snapshot (
            ticker TEXT NOT NULL,
            snapshot_month TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            pe_ttm REAL, pbv REAL, roe REAL, eps_ttm REAL,
            market_cap REAL, shares REAL,
            source TEXT NOT NULL DEFAULT 'exodus_keystats',
            raw_json TEXT,
            PRIMARY KEY (ticker, snapshot_month, fetched_at)
        )
    """)
    conn.commit()


def load_token(token_file: str = TOKEN_FILE) -> str:
    if not os.path.isfile(token_file):
        raise KeystatsAuthError(f"no token file at {token_file} — run auto_token.py")
    with open(token_file, "r", encoding="utf-8") as fh:
        token = fh.read().strip()
    if not token:
        raise KeystatsAuthError("token file empty — run auto_token.py")
    return token


def parse_keystats(payload: Any) -> dict:
    """Extract the FQ fields from an exodus keystats response, defensively.

    Unknown shapes are fine: raw_json always carries the full payload for later re-parsing.
    """
    node = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
    flat: dict = {}

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k not in flat and isinstance(v, (int, float)) and not isinstance(v, bool):
                    flat[str(k).lower()] = float(v)
                elif isinstance(v, dict):
                    walk(v)

    walk(node)
    out = {}
    for field, candidates in _FIELD_KEYS.items():
        out[field] = next((flat[c] for c in candidates if c in flat), None)
    out["raw_json"] = json.dumps(payload)
    return out


def fetch_keystats(ticker: str, token: str, session: requests.Session | None = None) -> dict:
    sess = session or requests
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {token}"}
    try:
        resp = sess.get(EXODUS_KEYSTATS_URL.format(ticker=ticker), headers=headers, timeout=TIMEOUT_S)
    except requests.RequestException as exc:
        raise RuntimeError(f"{ticker}: network error {exc}") from exc
    if resp.status_code in (401, 403):
        raise KeystatsAuthError(f"{ticker}: HTTP {resp.status_code} — refresh token via auto_token.py")
    if resp.status_code != 200:
        raise RuntimeError(f"{ticker}: HTTP {resp.status_code}")
    return parse_keystats(resp.json())


def select_universe(conn: sqlite3.Connection, top_n: int = 200) -> list[str]:
    """Month-end top-N by ADV60 among names with a real print, ADV60 >= 1bn, close >= 50 (C1).

    Reads raw rows with a simple parameterized SELECT; ranking happens in Python so the SQL
    stays trivially static (no dynamic SQL anywhere in this module).
    """
    rows = conn.execute(
        "SELECT ticker, date, close, volume FROM ohlcv "
        "WHERE is_final = 1 AND ticker != 'IHSG' AND volume > 0 AND close >= ? "
        "ORDER BY ticker, date",
        (PRICE_MIN_IDR,),
    ).fetchall()
    by_ticker: dict[str, list[tuple[str, float, float]]] = {}
    for tkr, date, close, vol in rows:
        by_ticker.setdefault(tkr, []).append((date, close, vol))
    # last row of each calendar month per ticker (C1: volume>0 already filtered);
    # the snapshot point is the most recent month's last row
    month_end: dict[str, tuple[str, float, float]] = {}
    latest_month: dict[str, str] = {}
    for tkr, series in by_ticker.items():
        per_month: dict[str, tuple[str, float, float]] = {}
        for date, close, vol in series:
            per_month[date[:7]] = (date, close, vol)
        m = max(per_month)
        month_end[tkr] = per_month[m]
        latest_month[tkr] = m
    # ADV60 at each ticker's last month-end
    scored = []
    for tkr, (date, close, _vol) in month_end.items():
        series = by_ticker[tkr]
        idx = next((i for i, d in enumerate(series) if d[0] == date), None)
        if idx is None or idx < 59:
            continue
        window = series[idx - 59: idx + 1]
        adv60 = sum(c * v for _d, c, v in window) / len(window)
        if adv60 >= ADV60_MIN_IDR:
            scored.append((tkr, adv60))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [tkr for tkr, _ in scored[:top_n]]


def insert_snapshot(conn: sqlite3.Connection, ticker: str, stats: dict,
                    snapshot_month: str | None = None) -> None:
    month = snapshot_month or datetime.now().strftime("%Y-%m")
    fetched_at = _utc_timestamp()
    conn.execute(
        "INSERT INTO fq_keystats_snapshot "
        "(ticker, snapshot_month, fetched_at, pe_ttm, pbv, roe, eps_ttm, "
        "market_cap, shares, source, raw_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'exodus_keystats', ?)",
        (ticker, month, fetched_at, stats.get("pe_ttm"), stats.get("pbv"), stats.get("roe"),
         stats.get("eps_ttm"), stats.get("market_cap"), stats.get("shares"),
         stats.get("raw_json")),
    )
    conn.commit()


_last_ts = ""


def _utc_timestamp() -> str:
    """Strictly-increasing ISO timestamp — append-only PK needs uniqueness even when the
    host clock is coarse enough to return the same value twice in a row."""
    global _last_ts
    ts = datetime.now(timezone.utc).isoformat()
    if ts <= _last_ts:
        base = datetime.fromisoformat(_last_ts)
        ts = (base + _MICROSECOND).isoformat()
    _last_ts = ts
    return ts


def run(limit: int = MAX_TICKERS_PER_RUN, universe_size: int = 200,
        token: str | None = None, sleep_fn=time.sleep, session: requests.Session | None = None,
        universe_conn: sqlite3.Connection | None = None,
        research_conn: sqlite3.Connection | None = None) -> dict:
    """Capture one snapshot batch. Manual invocation only — nothing schedules this."""
    token = token if token is not None else load_token()
    uconn = universe_conn or db_connect(DB_PATH)
    rconn = research_conn or sqlite3.connect(RESEARCH_DB)
    init_table(rconn)
    tickers = select_universe(uconn, top_n=universe_size)[:limit]
    ok, failed = [], []
    for i, tkr in enumerate(tickers):
        if i:
            sleep_fn(REQUEST_INTERVAL_S)
        try:
            stats = fetch_keystats(tkr, token, session=session)
            insert_snapshot(rconn, tkr, stats)
            ok.append(tkr)
        except KeystatsAuthError:
            failed.append((tkr, "auth"))  # abort the batch: every further call would 401 too
            break
        except Exception as exc:
            logger.warning("keystats snapshot failed for %s: %s", tkr, exc)
            failed.append((tkr, str(exc)[:120]))
    return {"captured": ok, "failed": failed,
            "universe_size": len(tickers), "at": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="research.fq_snapshot")
    ap.add_argument("--limit", type=int, default=MAX_TICKERS_PER_RUN)
    ap.add_argument("--universe", type=int, default=200)
    args = ap.parse_args()
    result = run(limit=args.limit, universe_size=args.universe)
    print(json.dumps(result, indent=2))
