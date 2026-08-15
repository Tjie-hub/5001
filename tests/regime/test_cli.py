"""regime CLI smoke test: build+query must persist through the R-5 split
(research.db), not the production DB."""
import sqlite3

import research.db as research_db
from research.regime import cli


def test_build_and_query_persist_through_research_split(tmp_path, monkeypatch):
    prod = tmp_path / "walkforward.db"
    research = tmp_path / "research.db"
    conn = sqlite3.connect(prod)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL, "
                 "high REAL, low REAL, open REAL, volume REAL, is_final INTEGER DEFAULT 1)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(research_db, "RESEARCH_DB_PATH", str(research))
    monkeypatch.setattr(research_db, "PROD_DB_PATH", str(prod))

    def _fake_collect(conn, strategy_fn, cfg):
        return []

    monkeypatch.setattr("research.regime.collect.collect_tagged_trades", _fake_collect)
    monkeypatch.setattr("research.regime.collect.corpus_fingerprint", lambda trades: "fp")

    cli._build("nr7_breakout")

    check = sqlite3.connect(research)
    assert check.execute("SELECT COUNT(*) FROM regime_profiles").fetchone()[0] == 1
    check.close()
