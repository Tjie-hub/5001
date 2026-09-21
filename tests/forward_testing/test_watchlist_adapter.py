"""F-1: the EOD and Premarket plans are under forward test, append-only, with
enough provenance to reconstruct an outcome without retrospective price lookup.
"""
import sqlite3

import pytest

from engine import watchlist_ledger as wl
from forward_testing.adapters.watchlist_adapter import WatchlistAdapter, ensure_meta_table
from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo


ROW = {
    "ticker": "AAA", "confidence": 0.82, "conviction": 12.0, "confluence": 2,
    "sources": ["W"], "strategy_fn": "NR7 Breakout",
    "rule_id": "NR7 Breakout@bare#abc123", "admission_path": "APPROVED_CLEAN",
    "wf_expectancy_pct": 1.63, "wf_n_trades": 1311, "wf_last_computed": "2026-08-28",
    "decision_price": 1250.0, "decision_price_basis": "last_completed_close",
    "entry_rule": "NEXT_SESSION_OPEN",
    "provenance": {"evidence_backed": True, "market_regime": "BULL",
                   "premarket_revision": {"action": "RETAIN",
                                          "reason_code": "no_new_information",
                                          "reason": "nothing arrived",
                                          "evidence": {}}},
}


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "ft.db")
    init_ft_tables(path)
    conn = sqlite3.connect(path)
    wl.ensure_tables(conn)
    conn.close()
    return path


def _publish(db, date, strategy, rows):
    conn = sqlite3.connect(db)
    try:
        wl.append_snapshot(conn, date, strategy, rows)
    finally:
        conn.close()


class TestIngest:

    def test_ingests_both_cohorts_separately(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        _publish(db, "2026-09-01", "premarket", [dict(ROW, ticker="BBB")])
        n = WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        assert n == 2
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT ticker, strategy, track, direction "
                            "FROM ft_signal ORDER BY strategy").fetchall()
        conn.close()
        assert rows == [("AAA", "eod", "SHADOW", "LONG"),
                        ("BBB", "premarket", "SHADOW", "LONG")]

    def test_cohorts_are_never_pooled(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        _publish(db, "2026-09-01", "premarket", [ROW])
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(DISTINCT strategy) FROM ft_signal").fetchone()[0]
        conn.close()
        assert n == 2       # same ticker, two cohorts, two rows

    def test_is_idempotent(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        a = WatchlistAdapter(FTRepo(db), db)
        assert a.ingest("2026-09-01") == 1
        assert a.ingest("2026-09-01") == 0

    def test_only_the_latest_revision_is_ingested(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        _publish(db, "2026-09-01", "eod", [dict(ROW, ticker="CCC")])
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        got = [r[0] for r in conn.execute("SELECT ticker FROM ft_signal")]
        conn.close()
        assert got == ["CCC"]

    def test_missing_ledger_is_not_an_error(self, tmp_path):
        path = str(tmp_path / "bare.db")
        init_ft_tables(path)
        assert WatchlistAdapter(FTRepo(path), path).ingest("2026-09-01") == 0

    def test_empty_plan_ingests_nothing_without_failing(self, db):
        _publish(db, "2026-09-01", "eod", [])
        assert WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01") == 0


class TestMeta:

    def _meta(self, db):
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            return dict(conn.execute("SELECT * FROM ft_signal_meta").fetchone())
        finally:
            conn.close()

    def test_records_every_provenance_field(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        m = self._meta(db)
        assert m["cohort"] == "eod"
        assert m["strategy_fn"] == "NR7 Breakout"
        assert m["rule_id"] == "NR7 Breakout@bare#abc123"
        assert m["admission_path"] == "APPROVED_CLEAN"
        assert m["wf_expectancy_pct"] == 1.63
        assert m["wf_n_trades"] == 1311
        assert m["decision_price"] == 1250.0
        assert m["decision_price_basis"] == "last_completed_close"
        assert m["entry_rule"] == "NEXT_SESSION_OPEN"
        assert m["agent_confidence"] == 0.82
        assert m["market_regime"] == "BULL"
        assert m["revision_action"] == "RETAIN"
        assert m["revision_reason_code"] == "no_new_information"
        assert "W" in m["source_tags"]

    def test_meta_is_append_only(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("UPDATE ft_signal_meta SET wf_expectancy_pct=9.9")
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM ft_signal_meta")
        finally:
            conn.close()

    def test_ensure_meta_table_is_idempotent(self, db):
        ensure_meta_table(db)
        ensure_meta_table(db)

    def test_entry_price_intent_is_the_decision_price_not_a_future_one(self, db):
        _publish(db, "2026-09-01", "eod", [ROW])
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        intent = conn.execute("SELECT entry_price_intent FROM ft_signal").fetchone()[0]
        conn.close()
        assert intent == 1250.0


class TestCycleWiring:

    def test_forward_test_cycle_ingests_watchlists(self):
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_forward_test_cycle)
        assert "WatchlistAdapter" in src
        assert "SignalAdapter" in src
