"""R-5 physical fence: production code must never reference RESEARCH_DB_PATH or
call connect_research(); and after migration, the Tier-1 tables must not exist
in walkforward.db's schema (the static write-fence in test_research_data_fence.py
covers the write-SQL side; this covers the physical-file side)."""
import re
import sqlite3
from pathlib import Path

import pytest

from research.db import TIER1_TABLES, connect_research

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_SCOPES = ["scheduler", "engine", "forward_testing", "data",
                     "screener", "routes"]
PRODUCTION_FILES = ["monitor.py", "paper_trade.py", "app.py",
                    "news_filter.py", "flow_filter.py", "stockbit_fetcher.py",
                    "routes_backtest_multi.py"]
FORBIDDEN = re.compile(r"research\.db\s+import|research_db\.RESEARCH_DB_PATH|connect_research\(")


def _py_files():
    for scope in PRODUCTION_SCOPES:
        yield from (ROOT / scope).rglob("*.py")
    for f in PRODUCTION_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def test_production_never_imports_connect_research():
    offenders = [p.relative_to(ROOT).as_posix() for p in _py_files()
                 if FORBIDDEN.search(p.read_text(encoding="utf-8"))]
    assert not offenders, f"production references the research-only DB seam: {offenders}"


def test_connect_research_prod_schema_cannot_write_tier1_tables(tmp_path):
    prod = tmp_path / "walkforward.db"
    conn = sqlite3.connect(prod)
    for t in TIER1_TABLES:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (x)")  # simulate a not-yet-migrated prod file
    conn.commit()
    conn.close()

    rconn = connect_research(research_path=str(tmp_path / "research.db"), prod_path=str(prod))
    for t in TIER1_TABLES:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            rconn.execute(f"INSERT INTO prod.{t} DEFAULT VALUES")
    rconn.close()
