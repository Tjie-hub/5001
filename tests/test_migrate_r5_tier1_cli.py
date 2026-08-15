"""CLI wrapper for research.db_migration.migrate_tier1 -- dry-run by default,
mirrors scripts/db_restore.py's --apply convention."""
import sqlite3

from scripts import migrate_r5_tier1


def _mk_source(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE ohlcv (ticker TEXT);
        CREATE TABLE research_runs (run_id TEXT PRIMARY KEY);
    """)
    conn.execute("INSERT INTO research_runs VALUES ('r1')")
    conn.commit()
    conn.close()


def test_dry_run_does_not_touch_either_file(tmp_path, capsys):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)

    rc = migrate_r5_tier1.main(["--prod-db", str(src), "--research-db", str(dst)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "research_runs" in out
    assert not dst.exists()  # nothing created without --apply

    check = sqlite3.connect(src)
    assert check.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_runs'"
    ).fetchone() is not None
    check.close()


def test_apply_performs_the_migration(tmp_path, capsys):
    src = tmp_path / "walkforward.db"
    dst = tmp_path / "research.db"
    _mk_source(src)

    rc = migrate_r5_tier1.main(["--prod-db", str(src), "--research-db", str(dst), "--apply"])
    assert rc == 0

    check = sqlite3.connect(dst)
    assert check.execute("SELECT run_id FROM research_runs").fetchall() == [("r1",)]
    check.close()

    check2 = sqlite3.connect(src)
    assert check2.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_runs'"
    ).fetchone() is None
    check2.close()
