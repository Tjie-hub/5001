"""R-5 Tier-1 physical split seam (spec: docs/superpowers/specs/2026-07-14-r5-physical-db-split-scope.md).
connect_research() must make the attached production schema physically
read-only and Tier-1 writes must land only in the research (main) schema."""
import os
import sqlite3

import pytest

from research.db import RESEARCH_DB_PATH, TIER1_TABLES, connect_research


def _mk_prod(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
    conn.execute("INSERT INTO ohlcv VALUES ('BBCA','2026-01-01',9000)")
    conn.commit()
    conn.close()


def test_tier1_tables_is_the_eight_named_tables():
    assert TIER1_TABLES == (
        "research_runs", "gate_decisions", "gate_evidence",
        "regime_profiles", "regime_profile_cells",
        "hypotheses", "hypothesis_links", "failure_registry")


def test_default_research_db_path_is_sibling_of_walkforward_db():
    assert os.path.basename(RESEARCH_DB_PATH) == "research.db"
    assert os.path.dirname(RESEARCH_DB_PATH).endswith(os.path.join("idx-walkforward-5001", "data")) \
        or os.path.basename(os.path.dirname(RESEARCH_DB_PATH)) == "data"


def test_unqualified_read_resolves_to_attached_prod_schema(tmp_path):
    prod = tmp_path / "prod.db"
    _mk_prod(prod)
    conn = connect_research(research_path=str(tmp_path / "research.db"), prod_path=str(prod))
    row = conn.execute("SELECT ticker, close FROM ohlcv").fetchone()
    conn.close()
    assert row == ("BBCA", 9000)


def test_write_to_attached_prod_schema_is_blocked(tmp_path):
    prod = tmp_path / "prod.db"
    _mk_prod(prod)
    conn = connect_research(research_path=str(tmp_path / "research.db"), prod_path=str(prod))
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("INSERT INTO prod.ohlcv VALUES ('X','2026-01-02',1)")
    conn.close()


def test_unqualified_write_lands_in_research_main_schema(tmp_path):
    prod = tmp_path / "prod.db"
    _mk_prod(prod)
    research_path = tmp_path / "research.db"
    conn = connect_research(research_path=str(research_path), prod_path=str(prod))
    conn.execute("CREATE TABLE research_runs (run_id TEXT)")
    conn.execute("INSERT INTO research_runs VALUES ('r1')")
    conn.commit()
    conn.close()
    # verify directly against the research.db file, with no prod attached
    check = sqlite3.connect(str(research_path))
    assert check.execute("SELECT run_id FROM research_runs").fetchall() == [("r1",)]
    check.close()


def test_connect_research_sets_busy_timeout_and_wal(tmp_path):
    prod = tmp_path / "prod.db"
    _mk_prod(prod)
    conn = connect_research(research_path=str(tmp_path / "research.db"), prod_path=str(prod))
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()
