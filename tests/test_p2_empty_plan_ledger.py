"""P-2 regression: an EOD run that approves nobody must still be auditable, and
Premarket must be able to tell EMPTY_PLAN from NO_EOD_SNAPSHOT.

Observed 2026-09-02 in production: the 16:40 job logged
"93 candidates, top 8 vetted, 0 approved", record_snapshot was called with an
empty list, watchlist_snapshot_log stayed empty, and the next morning
latest_date_before() returned None -- so a real prediction ("we approve nobody
today") was indistinguishable from "the job never ran".
"""
import sqlite3

import pytest

from engine import watchlist_ledger as wl
from engine import trade_plan as tp


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    wl.ensure_tables(c)
    return c


ROW = {"ticker": "AAA", "confidence": 0.8, "sources": ["S"], "conviction": 1.0,
       "confluence": 1}


class TestZeroApprovedIsPersisted:

    def test_empty_publication_is_recorded(self, conn):
        rev = wl.append_snapshot(conn, "2026-09-02", "eod", [])
        assert rev == 1
        pub = wl.publication(conn, "2026-09-02", "eod")
        assert pub is not None
        assert pub["n_rows"] == 0 and pub["revision"] == 1
        assert pub["recorded_at"]

    def test_no_ticker_rows_are_fabricated(self, conn):
        wl.append_snapshot(conn, "2026-09-02", "eod", [])
        assert conn.execute(
            "SELECT COUNT(*) FROM watchlist_snapshot_log").fetchone()[0] == 0
        assert wl.read_snapshot(conn, "2026-09-02", "eod") == []

    def test_record_snapshot_persists_the_empty_case(self, conn):
        """The production path, not just the ledger primitive."""
        rev = tp.record_snapshot(conn, "2026-09-02", "eod", [])
        assert rev == 1
        assert wl.publication(conn, "2026-09-02", "eod")["n_rows"] == 0

    def test_revision_numbering_survives_an_empty_publication(self, conn):
        assert wl.append_snapshot(conn, "2026-09-02", "eod", []) == 1
        assert wl.append_snapshot(conn, "2026-09-02", "eod", [ROW]) == 2
        assert wl.append_snapshot(conn, "2026-09-02", "eod", []) == 3
        revs = [r[0] for r in conn.execute(
            "SELECT revision FROM watchlist_publication WHERE date='2026-09-02' "
            "ORDER BY revision")]
        assert revs == [1, 2, 3]
        # the real plan at revision 2 is still exactly retrievable
        got = wl.read_snapshot(conn, "2026-09-02", "eod", revision=2)
        assert [g["ticker"] for g in got] == ["AAA"]

    def test_publication_manifest_is_append_only(self, conn):
        wl.append_snapshot(conn, "2026-09-02", "eod", [])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE watchlist_publication SET n_rows=99")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM watchlist_publication")


class TestRetrieval:

    def test_empty_plan_is_found_as_a_base_plan(self, conn):
        wl.append_snapshot(conn, "2026-09-02", "eod", [])
        assert wl.latest_date_before(conn, "eod", "2026-09-03") == "2026-09-02"

    def test_status_is_empty_plan(self, conn):
        wl.append_snapshot(conn, "2026-09-02", "eod", [])
        b = wl.base_plan(conn, "2026-09-03")
        assert b["status"] == wl.BASE_EMPTY
        assert b["date"] == "2026-09-02" and b["rows"] == []
        assert b["revision"] == 1

    def test_status_is_no_snapshot_when_nothing_published(self, conn):
        b = wl.base_plan(conn, "2026-09-03")
        assert b["status"] == wl.BASE_MISSING
        assert b["date"] is None and b["rows"] == []

    def test_status_is_plan_when_names_were_approved(self, conn):
        wl.append_snapshot(conn, "2026-09-02", "eod", [ROW])
        b = wl.base_plan(conn, "2026-09-03")
        assert b["status"] == wl.BASE_PLAN
        assert [r["ticker"] for r in b["rows"]] == ["AAA"]

    def test_the_three_statuses_are_distinct(self):
        assert len({wl.BASE_PLAN, wl.BASE_EMPTY, wl.BASE_MISSING}) == 3

    def test_legacy_rows_without_a_publication_still_resolve(self, conn):
        """Publications recorded before this table existed left only snapshot
        rows; those must keep working."""
        wl.append_snapshot(conn, "2026-09-01", "eod", [ROW])
        conn.execute("DROP TRIGGER watchlist_publication_no_delete")
        conn.execute("DELETE FROM watchlist_publication")
        conn.commit()
        b = wl.base_plan(conn, "2026-09-03")
        assert b["status"] == wl.BASE_PLAN and b["date"] == "2026-09-01"


class TestPremarketDistinguishes:

    def test_job_reads_base_plan_status(self):
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_premarket_firm_scan)
        assert "_wl.base_plan(" in src
        assert "_wl.BASE_MISSING" in src and "_wl.BASE_EMPTY" in src

    def test_only_missing_aborts_the_job(self):
        """EMPTY_PLAN must fall through to the revision path (an empty plan is a
        prediction and its revision is a prediction too); only NO_EOD_SNAPSHOT
        returns early."""
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_premarket_firm_scan)
        miss = src.index("_wl.BASE_MISSING")
        empty = src.index("_wl.BASE_EMPTY")
        # the early `return` belongs to the MISSING branch, before the EMPTY one
        assert src.index("return", miss) < empty

    def test_reason_codes_are_unchanged(self):
        """P-2 must not disturb revision reason-code semantics."""
        from engine import premarket_revision as rev
        for code in (rev.R_NO_NEW_INFO, rev.R_CORPORATE_ACTION, rev.R_SUSPENDED,
                     rev.R_MARKET_RISK_OFF, rev.R_VPIN_TOXIC,
                     rev.R_FOREIGN_DISTRIBUTION, rev.R_FOREIGN_ACCUMULATION,
                     rev.R_NEGATIVE_NEWS, rev.R_DISCOVERY):
            assert isinstance(code, str) and code

    def test_revising_an_empty_plan_yields_an_empty_plan(self, conn):
        from engine import premarket_revision as rev
        for ddl in ("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT, event_id TEXT, event_date TEXT, raw_json TEXT, fetch_date TEXT, updated_at TEXT)",
                    "CREATE TABLE suspension_events (ticker TEXT, last_normal_date TEXT, resume_date TEXT, missing_td INT, gap_pct REAL, classification TEXT, detected_at TEXT)",
                    "CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INT, headlines_json TEXT, updated_at TEXT)",
                    "CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT, lot INT, lot_value INT, investor_type TEXT)",
                    "CREATE TABLE vpin_scores (ticker TEXT, date TEXT, vpin REAL, vpin_label TEXT, bucket_count INT, error TEXT)"):
            conn.execute(ddl)
        conn.commit()
        wl.append_snapshot(conn, "2026-09-02", "eod", [])
        b = wl.base_plan(conn, "2026-09-03")
        ds = rev.revise(conn, b["rows"], base_date=b["date"],
                        plan_date="2026-09-03")
        assert ds == []
        assert rev.apply(ds) == []
