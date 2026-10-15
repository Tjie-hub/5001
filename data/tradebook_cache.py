"""Shared on-disk cache of Stockbit trade-book/chart responses (today's session only).

Why (2026-10-15): three jobs swept the same endpoint for all ~958 tickers — the flow fetch (flow_filter),
the screener scrape (screener/idx_scraper) and the 18:30 cron (stockbit_fetcher flow) — so the post-close
day was downloaded three times and intraday sweeps ran back to back on one token. Every fetch now writes
its payload here; a later consumer reads a copy fresh enough for its purpose instead of re-requesting.

On disk (not in memory) because the 18:30 cron is a separate process. One gzip JSON per ticker
(~50 KB, ~48 MB a day); days older than KEEP_DAYS are pruned. Fail-soft: any cache error is a miss.
"""
import gzip
import json
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / "tradebook_cache"
KEEP_DAYS = 2
# IDX post-trading (run-off at the closing price) ends 16:15 WIB; a payload fetched at or after it is the
# day's complete tape (the screener's 16:15 EOD sweep, the authority for final bars).
POST_CLOSE_FINAL = "16:15"
# Intraday consumers accept a payload this recent: covers one sweep (~7 min at 0.3 s) plus a wait on the
# scheduler's sweep lock (13:30 flow fetch -> 13:35 scrape).
REUSE_WINDOW = timedelta(minutes=15)


def _path(ticker, day):
    return CACHE_DIR / day / f"{ticker.upper()}.json.gz"


def put(ticker, data, now=None):
    """Store today's payload for `ticker` (atomic replace, so a concurrent reader never sees half a file)."""
    if not data:
        return
    now = now or datetime.now()
    try:
        p = _path(ticker, now.date().isoformat())
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".{os.getpid()}.tmp")
        with gzip.open(tmp, "wt", compresslevel=6) as f:
            json.dump({"fetched_at": now.isoformat(timespec="seconds"), "data": data}, f)
        os.replace(tmp, p)
    except Exception:
        pass


def get(ticker, not_before, now=None):
    """Today's cached payload for `ticker` if it was fetched at or after `not_before` (a datetime), else None."""
    now = now or datetime.now()
    p = _path(ticker, now.date().isoformat())
    try:
        with gzip.open(p, "rt") as f:
            rec = json.load(f)
        if datetime.fromisoformat(rec["fetched_at"]) >= not_before:
            return rec["data"] or None
    except Exception:
        pass
    return None


def recent(now=None):
    """The intraday reuse bound: payloads fetched within REUSE_WINDOW."""
    return (now or datetime.now()) - REUSE_WINDOW


def post_close(now=None):
    """Today's POST_CLOSE_FINAL as a datetime: payloads at or after it are the complete session."""
    now = now or datetime.now()
    h, m = map(int, POST_CLOSE_FINAL.split(":"))
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def prune(today=None):
    """Delete day directories older than KEEP_DAYS. Returns the number removed."""
    cutoff = ((today or date.today()) - timedelta(days=KEEP_DAYS - 1)).isoformat()
    n = 0
    try:
        for d in CACHE_DIR.iterdir():
            if d.is_dir() and d.name < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                n += 1
    except FileNotFoundError:
        pass
    return n
