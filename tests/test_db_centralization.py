"""Guard: production modules must not open raw sqlite3 connections.

Every connection must come through data.db.connect()/get_db() so
timeout/busy_timeout/WAL hardening lives in one place (audit item 3.3; six
historical "database is locked" incidents were all missing-pragma variants
of the same defect). If this test fails, replace `sqlite3.connect(...)`
with `from data.db import connect as db_connect` + `db_connect(...)`.

Hardening Phase 6 (2026-07-10): widened from a 12-file hot list to every
production scope — 31 more modules migrated, allowlist is data/db.py itself.
research/ and scripts/ are deliberately out of scope (offline tooling).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes", "utils"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py", "wsgi.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py",
                    "routes_backtest_multi.py", "auto_token.py"]

# The one place allowed to call sqlite3.connect — the wrapper itself.
ALLOWLIST = {"data/db.py"}

RAW_CONNECT = re.compile(r"\bsqlite3\s*\.\s*connect\s*\(")


def _py_files():
    for scope in PRODUCTION_SCOPES:
        yield from (ROOT / scope).rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def test_no_raw_sqlite_connect_in_production():
    offenders = []
    for p in _py_files():
        rel = str(p.relative_to(ROOT))
        if rel in ALLOWLIST or "__pycache__" in rel:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if RAW_CONNECT.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "Raw sqlite3.connect() in production modules — use data.db.connect():\n"
        + "\n".join(offenders)
    )


def test_allowlist_shrinks_only():
    assert ALLOWLIST == {"data/db.py"}
