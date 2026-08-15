"""Phase E CLI: record-hypothesis, record-failure, orphans, trace, backfill."""
import sqlite3

from data.db import connect
from research.knowledge import cli, storage


def test_cli_record_hypothesis_then_trace(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    storage.ensure_knowledge_tables(conn)
    conn.close()
    rc = cli.main(["--db", db, "record-hypothesis", "--id", "H1", "--title", "a hyp"])
    assert rc == 0
    rc = cli.main(["--db", db, "trace", "--id", "H1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "H1" in out


def test_cli_orphans_runs(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    storage.ensure_knowledge_tables(conn)
    conn.close()
    assert cli.main(["--db", db, "orphans"]) == 0


def test_default_invocation_persists_through_research_split(tmp_path, monkeypatch):
    import research.db as research_db

    # connect_research() always ATTACHes PROD_DB_PATH read-only, even for a
    # command that never touches prod data -- mode=ro can't create a missing
    # file, so a real (even empty) file must exist at that path, and it must
    # be one this test owns rather than the real dev data/walkforward.db.
    prod = tmp_path / "walkforward.db"
    sqlite3.connect(prod).close()
    research = tmp_path / "research.db"
    monkeypatch.setattr(research_db, "RESEARCH_DB_PATH", str(research))
    monkeypatch.setattr(research_db, "PROD_DB_PATH", str(prod))

    rc = cli.main(["record-hypothesis", "--id", "H1", "--title", "a hyp"])
    assert rc == 0 or rc is None

    check = sqlite3.connect(research)
    assert check.execute(
        "SELECT title FROM hypotheses WHERE hypothesis_id='H1'").fetchone() == ("a hyp",)
    check.close()
