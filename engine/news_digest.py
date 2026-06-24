"""Premarket news digest — top genuine-IDX-ticker catalysts for the session.

news_mentions counts keyword matches, so raw top hits are word-noise (PADA, LABA,
BELI = Indonesian words). We join against idx_tickers to keep only real listed
stocks, then surface the most-covered names with one headline each.
"""
from __future__ import annotations

import html
import json
import sqlite3
from typing import Any


# Ticker codes that are also common Indonesian/market words. They exist in
# idx_tickers (so the join can't drop them), but their high mention counts come from
# the word appearing in unrelated headlines ("pada"=at, "laba"=profit, "beli"=buy,
# "emas"=gold), not genuine company coverage. Excluded from the catalyst digest.
NOISE_TICKERS = {
    "PADA", "LABA", "BELI", "JUAL", "NAIK", "TURUN", "PASAR", "SAHAM",
    "BISA", "INFO", "EMAS", "BANK", "DETIK", "IPO", "BEST", "GOLD",
}


def _first_headline(headlines_json: str) -> str:
    try:
        arr = json.loads(headlines_json or "[]")
        return str(arr[0]) if arr else ""
    except (ValueError, TypeError):
        return ""


def get_ticker_news_digest(conn: sqlite3.Connection, date_str: str,
                           top_n: int = 5) -> list[dict[str, Any]]:
    """Top real-ticker catalysts for date_str. Filters news_mentions to tickers that
    exist in idx_tickers (drops word-noise), ranked by mention count."""
    # over-fetch, then drop word-collision noise, then take top_n
    rows = conn.execute(
        "SELECT n.ticker, n.count, n.headlines_json "
        "FROM news_mentions n JOIN idx_tickers t ON t.ticker = n.ticker "
        "WHERE n.date = ? ORDER BY n.count DESC LIMIT ?",
        (date_str, top_n + len(NOISE_TICKERS)),
    ).fetchall()
    out = [{"ticker": r[0], "count": r[1], "headline": _first_headline(r[2])}
           for r in rows if r[0] not in NOISE_TICKERS]
    return out[:top_n]


def build_news_block(digest: list[dict[str, Any]], headline_limit: int = 90) -> str:
    """Pure: render the news-catalyst lines for the Telegram briefing."""
    if not digest:
        return "📰 <b>News Catalysts</b>\n  None for real tickers today."
    lines = ["📰 <b>News Catalysts</b> (top stocks)"]
    for d in digest:
        hl = d["headline"]
        if len(hl) > headline_limit:
            hl = hl[: headline_limit - 1].rstrip() + "…"
        line = f"  <b>{html.escape(d['ticker'])}</b> ({d['count']})"
        if hl:
            line += f" — {html.escape(hl)}"
        lines.append(line)
    return "\n".join(lines)
