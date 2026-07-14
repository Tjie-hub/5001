"""Phase E CLI: record-hypothesis, record-failure, orphans, trace, backfill."""
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
