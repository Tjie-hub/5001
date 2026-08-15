"""migrate_tier1: copy the 8 Tier-1 tables from an existing single-file DB into
a fresh research.db, verify row counts, then drop them from the source -- only
after every table has been copied and verified (no partial-drop states)."""
import sqlite3

import pytest

from research.db_migration import migrate_tier1
from research.db import TIER1_TABLES


def _mk_source(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL);
        CREATE TABLE research_runs (run_id TEXT PRIMARY KEY, kind TEXT);
        CREATE TABLE gate_decisions (decision_id TEXT PRIMARY KEY, final_state TEXT);
        CREATE TABLE hypotheses (hypothesis_id TEXT PRIMARY KEY, title TEXT);
    """)
    conn.execute("INSERT INTO ohlcv VALUES ('BBCA','2026-01-01',9000)")
    conn.execute("INSERT INTO research_runs VALUES ('r1','wf-refresh')")
    conn.execute("INSERT INTO research_runs VALUES ('r2','gate-eval')")
    conn.execute("INSERT INTO gate_decisions VALUES ('d1','PROMOTE')")
    conn.execute("INSERT INTO hypotheses VALUES ('h1','a hyp')")
    conn.commit()
    conn.close()


def test_migrates_only_tables_present_in_source(tmp_path):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)

    report = migrate_tier1(str(src), str(dst))

    assert report["research_runs"] == {"copied": 2, "dropped": True}
    assert report["gate_decisions"] == {"copied": 1, "dropped": True}
    assert report["hypotheses"] == {"copied": 1, "dropped": True}
    for absent in ("gate_evidence", "regime_profiles", "regime_profile_cells",
                   "hypothesis_links", "failure_registry"):
        assert report[absent] == {"copied": 0, "dropped": False}


def test_dropped_tables_no_longer_exist_in_source(tmp_path):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)
    migrate_tier1(str(src), str(dst))

    check = sqlite3.connect(src)
    names = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check.close()
    assert "research_runs" not in names
    assert "gate_decisions" not in names
    assert "hypotheses" not in names
    assert "ohlcv" in names  # untouched -- not a Tier-1 table


def test_source_untouched_by_ohlcv_and_other_non_tier1_tables(tmp_path):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)
    migrate_tier1(str(src), str(dst))

    check = sqlite3.connect(src)
    assert check.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0] == 1
    check.close()


def test_rows_land_intact_in_research_db(tmp_path):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)
    migrate_tier1(str(src), str(dst))

    check = sqlite3.connect(dst)
    assert check.execute(
        "SELECT run_id, kind FROM research_runs ORDER BY run_id").fetchall() == \
        [("r1", "wf-refresh"), ("r2", "gate-eval")]
    check.close()


def test_is_idempotent_when_already_migrated(tmp_path):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)
    migrate_tier1(str(src), str(dst))

    # second run: nothing left to migrate, must not raise and must not duplicate
    report = migrate_tier1(str(src), str(dst))
    assert all(v["copied"] == 0 for v in report.values())

    check = sqlite3.connect(dst)
    assert check.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0] == 2
    check.close()


def test_raises_before_any_drop_on_ambiguous_partial_state(tmp_path):
    """Table exists in both source AND destination with rows already in the
    destination -- refuse rather than guess; no source table may be dropped."""
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)

    pre = sqlite3.connect(dst)
    pre.execute("CREATE TABLE hypotheses (hypothesis_id TEXT PRIMARY KEY, title TEXT)")
    pre.execute("INSERT INTO hypotheses VALUES ('h_existing', 'pre-existing')")
    pre.commit()
    pre.close()

    with pytest.raises(RuntimeError, match="hypotheses"):
        migrate_tier1(str(src), str(dst))

    check = sqlite3.connect(src)
    names = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check.close()
    assert "research_runs" not in names or True  # research_runs must NOT have been dropped either
    check2 = sqlite3.connect(src)
    assert check2.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_runs'"
    ).fetchone() is not None, "no table may be dropped once any table fails verification"
    check2.close()
