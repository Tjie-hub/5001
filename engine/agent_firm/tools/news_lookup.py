"""Structured news_mentions table reader for the News agent."""

import json
import sqlite3
from typing import Any
from data.db import connect as db_connect


def lookup(db_path: str, ticker: str, days: int = 7) -> list[dict[str, Any]]:
    conn = db_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT ticker, date, count, headlines_json FROM news_mentions "
            "WHERE ticker = ? AND date >= date('now', ? || ' days') "
            "ORDER BY date DESC LIMIT 20",
            (ticker, f"-{days}"),
        ).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            try:
                row["headlines"] = json.loads(row.pop("headlines_json") or "[]")
            except (json.JSONDecodeError, TypeError):
                row["headlines"] = []
            result.append(row)
        return result
    finally:
        conn.close()
