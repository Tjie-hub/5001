"""R-5 Tier-1 physical split seam (spec: docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md).

connect_research() opens data/research.db as the connection's main schema —
the sole physical home of the 8 Tier-1 (pure-discovery) research tables — and
ATTACHes the production DB read-only as schema `prod`. SQLite resolves an
unqualified table name against main first, then attached databases in attach
order, so existing unqualified ohlcv/corporate_actions reads throughout
research/ keep working unmodified against the attached prod schema, while
every unqualified write lands in research.db by construction: the attached
prod connection physically rejects writes (mode=ro), so there is no writable
path to production data through this seam at all.
"""
from __future__ import annotations

import os
import sqlite3

from data.db import DB_PATH as PROD_DB_PATH

RESEARCH_DB_PATH = os.getenv(
    "RESEARCH_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "research.db"))

# The 8 pure-discovery tables scoped by R-5 (scoping note §2, Tier 1). wf_scores/
# wf_edge/backtest_cache are Tier 2 (shared research<->production contract) and
# are explicitly out of scope for this split (scoping note §5).
TIER1_TABLES = (
    "research_runs", "gate_decisions", "gate_evidence",
    "regime_profiles", "regime_profile_cells",
    "hypotheses", "hypothesis_links", "failure_registry",
)


def connect_research(research_path: str | None = None, prod_path: str | None = None,
                      timeout: int = 30) -> sqlite3.Connection:
    """The one entry point for Tier-1 research tables. Returns a connection
    whose main schema is research.db (writable) and whose `prod` schema is
    the production DB, attached read-only, for the ohlcv/corporate_actions
    reads research still needs. Mirrors data.db.connect()'s WAL + busy_timeout
    hardening for the main schema.
    """
    research_path = research_path or RESEARCH_DB_PATH
    prod_path = prod_path or PROD_DB_PATH
    conn = sqlite3.connect(f"file:{research_path}", uri=True, timeout=timeout)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # :memory:/read-only paths may reject WAL -- timeout still applies
    conn.execute(f"ATTACH DATABASE 'file:{prod_path}?mode=ro' AS prod")
    return conn
