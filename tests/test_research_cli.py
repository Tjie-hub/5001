"""research CLI dispatch (M3): each command maps to its moved job."""
import sqlite3

import research.cli as cli


def test_cli_dispatches_each_job(monkeypatch):
    calls = []
    import research.jobs as rj
    monkeypatch.setattr(rj, "refresh_wf_scores", lambda: calls.append("wf"))
    monkeypatch.setattr(rj, "_refresh_backtest_cache", lambda: calls.append("cache"))
    monkeypatch.setattr(rj, "run_backtest_roller", lambda: calls.append("roll"))
    assert cli.main(["wf-refresh"]) == 0
    assert cli.main(["backtest-cache"]) == 0
    assert cli.main(["roller"]) == 0
    assert calls == ["wf", "cache", "roll"]


def test_refresh_wf_scores_writes_research_runs_via_the_split(tmp_path, monkeypatch):
    import research.db as research_db
    import research.jobs as jobs

    prod = tmp_path / "walkforward.db"
    research = tmp_path / "research.db"
    # build a minimal prod DB: idx_tickers empty is fine, ohlcv empty is fine --
    # this only asserts routing, not full job correctness (covered elsewhere).
    conn = sqlite3.connect(prod)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL, is_final INTEGER DEFAULT 1)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(jobs, "DB_PATH", str(prod))
    monkeypatch.setattr(research_db, "RESEARCH_DB_PATH", str(research))
    monkeypatch.setattr(research_db, "PROD_DB_PATH", str(prod))
    monkeypatch.setattr(jobs, "_wf_lock_acquire", lambda db_path: True)
    monkeypatch.setattr(jobs, "_load_ohlcv_bulk", lambda final_only=True: {})

    jobs.refresh_wf_scores()

    check = sqlite3.connect(research)
    assert check.execute("SELECT kind FROM research_runs").fetchall() == [("wf-refresh",)]
    check.close()
