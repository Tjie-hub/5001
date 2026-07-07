"""Guard: hot production modules must not open raw sqlite3 connections.

Every connection must come through data.db.connect()/get_db() so
timeout/busy_timeout/WAL hardening lives in one place (audit item 3.3).
If this test fails, replace `sqlite3.connect(...)` with
`from data.db import connect as db_connect` + `db_connect(...)`.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOT_MODULES = [
    "scheduler/scanner.py",
    "scheduler/jobs.py",
    "scheduler/reports.py",
    "scheduler/utils.py",
    "monitor.py",
    "news_filter.py",
    "flow_filter.py",
    "paper_trade.py",
    "app.py",
    "engine/premover_detector.py",
    "stockbit_fetcher.py",
    "screener/idx_scraper.py",
]

RAW_CONNECT = re.compile(r"sqlite3\s*\.\s*connect\s*\(")


def test_no_raw_sqlite_connect_in_hot_modules():
    offenders = []
    for rel in HOT_MODULES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), 1):
            if RAW_CONNECT.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "Raw sqlite3.connect() in hot modules — use data.db.connect():\n"
        + "\n".join(offenders)
    )
