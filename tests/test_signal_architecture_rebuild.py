"""End-to-end pins for the 2026-09-02 signal-architecture rebuild.

Four groups:
  L-3   wf_edge statistics can never cross strategies
  A-1/2 EOD is the base plan; Premarket revises it; the arrow runs one way
  F-1   EOD/Premarket are forward-tested, append-only, with full provenance
  S-1   the admission chain is replayable and self-reporting
"""
import datetime as dt
import json
import sqlite3

import pytest

from engine import watchlist_ledger as wl
from engine import premarket_revision as rev
from engine.edge_enrich import wf_edge_for, enrich_candidate

FRESH = dt.date.today().isoformat()


def _wf_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
        " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
        " n_trades INT, windows_tested INT, last_computed TEXT,"
        " PRIMARY KEY(ticker,strategy))")
    conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
                 "composite_score INT, verdict TEXT)")
    return conn


def _edge(conn, ticker, strategy, exp, n=60):
    conn.execute("INSERT INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (ticker, strategy, exp, 0.0, 55.0, 40.0, 0.4, n, 15, FRESH))
    conn.commit()


# ───────────────────────── L-3 ─────────────────────────

class TestNoCrossStrategyContamination:

    def test_lookup_is_keyed_on_ticker_and_strategy(self):
        conn = _wf_db()
        _edge(conn, "INCO", "Liquidity Sweep", 7.2)
        _edge(conn, "INCO", "NR7 Breakout", 0.4)
        assert wf_edge_for(conn, "INCO", "NR7 Breakout")["expectancy_pct"] == 0.4
        assert wf_edge_for(conn, "INCO", "Liquidity Sweep")["expectancy_pct"] == 7.2

    def test_a_strategy_with_no_row_never_borrows_the_best_row(self):
        """The exact defect: _best_wf_edge selected ORDER BY expectancy_pct DESC
        LIMIT 1, so a candidate inherited the ticker's strongest unrelated
        strategy's n_trades / win_rate / expectancy — the fields Tier B gates on."""
        conn = _wf_db()
        _edge(conn, "INCO", "Liquidity Sweep", 7.2, n=900)
        assert wf_edge_for(conn, "INCO", "NR7 Breakout") == {}

    def test_unattributed_candidate_carries_no_oos_statistics(self):
        conn = _wf_db()
        _edge(conn, "INCO", "Liquidity Sweep", 7.2, n=900)
        c = enrich_candidate(conn, "INCO", FRESH, closes=[], sources=["REVERSAL"])
        assert c["strategy"] is None
        assert c["expectancy_pct"] is None and c["n_trades"] is None

    def test_unattributed_candidate_is_dropped_by_tier_b(self):
        """Fail-closed: no evidence means it cannot clear a statistical gate."""
        from engine.veto import diagnose
        conn = _wf_db()
        _edge(conn, "INCO", "Liquidity Sweep", 7.2, n=900)
        c = enrich_candidate(conn, "INCO", FRESH, closes=[100] * 60,
                             regime="BULL", sources=["REVERSAL"])
        edge, veto = diagnose(c, "BULL")
        assert veto == "s1:few_trades"

    def test_single_strategy_list_is_inferred(self):
        conn = _wf_db()
        _edge(conn, "INCO", "NR7 Breakout", 1.1)
        c = enrich_candidate(conn, "INCO", FRESH, closes=[],
                             strategies=["NR7 Breakout"])
        assert c["strategy"] == "NR7 Breakout"
        assert c["expectancy_pct"] == 1.1

    def test_scanner_attributes_stats_to_the_traded_strategy(self):
        """scheduler.scanner passes strategies[0] — the same one open_trade
        records as the attributing strategy."""
        import inspect
        from scheduler import scanner
        src = inspect.getsource(scanner.run_edge_veto_stage)
        assert "strategy=(strats[0] if strats else None)" in src


# ───────────────────────── ledger ─────────────────────────

class TestImmutableLedger:

    def test_snapshot_log_is_append_only(self):
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        wl.append_snapshot(conn, "2026-09-01", "eod", [{"ticker": "AAA"}])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE watchlist_snapshot_log SET ticker='ZZZ'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM watchlist_snapshot_log")

    def test_revision_table_is_append_only(self):
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        wl.record_revisions(conn, "2026-09-02", "2026-09-01", [
            {"ticker": "AAA", "action": wl.ACTION_RETAIN,
             "reason_code": "no_new_information", "reason": "r", "evidence": {}}])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE watchlist_revision SET action='REMOVE'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM watchlist_revision")

    def test_a_rerun_appends_a_new_revision_and_preserves_the_old(self):
        """This is the fix for `record_snapshot` silently rewriting history."""
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        r1 = wl.append_snapshot(conn, "2026-09-01", "eod",
                                [{"ticker": "AAA", "confidence": 0.9}])
        r2 = wl.append_snapshot(conn, "2026-09-01", "eod",
                                [{"ticker": "BBB", "confidence": 0.1}])
        assert (r1, r2) == (1, 2)
        assert wl.read_snapshot(conn, "2026-09-01", "eod", revision=1)[0]["ticker"] == "AAA"
        assert wl.read_snapshot(conn, "2026-09-01", "eod")[0]["ticker"] == "BBB"

    def test_empty_plan_is_still_a_recorded_prediction(self):
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        assert wl.append_snapshot(conn, "2026-09-01", "eod", []) == 1

    def test_snapshot_carries_price_rule_strategy_and_evidence(self):
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        wl.append_snapshot(conn, "2026-09-01", "eod", [{
            "ticker": "AAA", "strategy_fn": "NR7 Breakout",
            "rule_id": "NR7 Breakout@bare#abc", "admission_path": "APPROVED_CLEAN",
            "wf_expectancy_pct": 1.63, "wf_n_trades": 1311,
            "decision_price": 1250.0, "decision_price_basis": "last_completed_close",
            "entry_rule": "NEXT_SESSION_OPEN", "sources": ["W"],
            "provenance": {"evidence_backed": True},
        }])
        row = wl.read_snapshot(conn, "2026-09-01", "eod")[0]
        for k in ("strategy_fn", "rule_id", "wf_expectancy_pct", "decision_price",
                  "decision_price_basis", "entry_rule"):
            assert row[k] is not None, k
        assert row["provenance"]["evidence_backed"] is True

    def test_latest_date_before_finds_the_base_plan(self):
        conn = sqlite3.connect(":memory:")
        wl.ensure_tables(conn)
        wl.append_snapshot(conn, "2026-08-31", "eod", [{"ticker": "A"}])
        wl.append_snapshot(conn, "2026-09-01", "eod", [{"ticker": "B"}])
        wl.append_snapshot(conn, "2026-09-02", "eod", [{"ticker": "C"}])
        assert wl.latest_date_before(conn, "eod", "2026-09-02") == "2026-09-01"

    def test_record_snapshot_writes_both_ledger_and_projection(self):
        from engine import trade_plan as tp
        conn = sqlite3.connect(":memory:")
        rev_no = tp.record_snapshot(conn, "2026-09-01", "eod",
                                    [{"ticker": "AAA", "confidence": 0.8,
                                      "sources": ["S"]}])
        assert rev_no == 1
        assert tp.get_snapshot(conn, "2026-09-01", "eod")[0]["ticker"] == "AAA"
        assert wl.read_snapshot(conn, "2026-09-01", "eod")[0]["ticker"] == "AAA"


# ───────────────────────── EOD → Premarket ─────────────────────────

def _rev_db():
    conn = sqlite3.connect(":memory:")
    wl.ensure_tables(conn)
    conn.execute("CREATE TABLE corporate_action_events (ticker TEXT, action_type TEXT,"
                 " event_id TEXT, event_date TEXT, raw_json TEXT, fetch_date TEXT,"
                 " updated_at TEXT)")
    conn.execute("CREATE TABLE suspension_events (ticker TEXT, last_normal_date TEXT,"
                 " resume_date TEXT, missing_td INT, gap_pct REAL,"
                 " classification TEXT, detected_at TEXT)")
    conn.execute("CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INT,"
                 " headlines_json TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT,"
                 " broker_code TEXT, side TEXT, lot INT, lot_value INT,"
                 " investor_type TEXT)")
    conn.execute("CREATE TABLE vpin_scores (ticker TEXT, date TEXT, vpin REAL,"
                 " vpin_label TEXT, bucket_count INT, error TEXT)")
    conn.commit()
    return conn


BASE = [{"ticker": "AAA", "rank": 1, "confidence": 0.8, "sources": ["S", "V"]},
        {"ticker": "BBB", "rank": 2, "confidence": 0.7, "sources": ["R"]}]


class TestPremarketIsARevision:

    def test_no_new_information_retains_everything(self):
        conn = _rev_db()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert [d.action for d in ds] == [wl.ACTION_RETAIN, wl.ACTION_RETAIN]
        assert all(d.reason_code == rev.R_NO_NEW_INFO for d in ds)
        assert [r["ticker"] for r in rev.apply(ds)] == ["AAA", "BBB"]

    def test_corporate_action_removes_and_says_why(self):
        conn = _rev_db()
        conn.execute("INSERT INTO corporate_action_events VALUES "
                     "('AAA','SPLIT','e1','2026-09-02','{}','2026-09-02','x')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        aaa = next(d for d in ds if d.ticker == "AAA")
        assert aaa.action == wl.ACTION_REMOVE
        assert aaa.reason_code == rev.R_CORPORATE_ACTION
        assert aaa.evidence["corporate_action"]["action_type"] == "SPLIT"
        assert [r["ticker"] for r in rev.apply(ds)] == ["BBB"]

    def test_suspension_removes(self):
        conn = _rev_db()
        conn.execute("INSERT INTO suspension_events VALUES "
                     "('BBB','2026-08-20','2026-09-02',5,12.0,'SUSPENSION','x')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert next(d for d in ds if d.ticker == "BBB").reason_code == rev.R_SUSPENDED

    def test_market_risk_off_stands_the_whole_plan_down(self):
        conn = _rev_db()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02",
                        market_risk={"tier": "CRITICAL", "score": 91.0})
        assert all(d.action == wl.ACTION_REMOVE for d in ds)
        assert all(d.reason_code == rev.R_MARKET_RISK_OFF for d in ds)
        assert rev.apply(ds) == []

    def test_overnight_foreign_distribution_downgrades(self):
        conn = _rev_db()
        conn.execute("INSERT INTO broker_flow VALUES "
                     "('AAA','2026-09-01','XX','SELL',1,5000000000,'Asing')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        aaa = next(d for d in ds if d.ticker == "AAA")
        assert aaa.action == wl.ACTION_DOWNGRADE
        assert aaa.reason_code == rev.R_FOREIGN_DISTRIBUTION

    def test_overnight_foreign_accumulation_upgrades_and_reranks(self):
        conn = _rev_db()
        conn.execute("INSERT INTO broker_flow VALUES "
                     "('BBB','2026-09-01','XX','BUY',1,5000000000,'Asing')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert [r["ticker"] for r in rev.apply(ds)] == ["BBB", "AAA"]

    def test_immaterial_foreign_flow_is_not_evidence(self):
        conn = _rev_db()
        conn.execute("INSERT INTO broker_flow VALUES "
                     "('AAA','2026-09-01','XX','SELL',1,1000,'Asing')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert next(d for d in ds if d.ticker == "AAA").action == wl.ACTION_RETAIN

    def test_toxic_order_flow_downgrades(self):
        conn = _rev_db()
        conn.execute("INSERT INTO vpin_scores VALUES ('AAA','2026-09-01',0.97,'EXTREME',10,NULL)")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert next(d for d in ds if d.ticker == "AAA").reason_code == rev.R_VPIN_TOXIC

    def test_overnight_news_downgrades_for_re_read(self):
        conn = _rev_db()
        conn.execute("INSERT INTO news_mentions VALUES "
                     "('AAA','2026-09-02',3,'[\"headline\"]','x')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        aaa = next(d for d in ds if d.ticker == "AAA")
        assert aaa.action == wl.ACTION_DOWNGRADE
        assert aaa.evidence["news"]["mentions"] == 3

    def test_news_dated_before_the_cutoff_is_not_new_information(self):
        conn = _rev_db()
        conn.execute("INSERT INTO news_mentions VALUES "
                     "('AAA','2026-08-30',9,'[]','x')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02")
        assert next(d for d in ds if d.ticker == "AAA").action == wl.ACTION_RETAIN


class TestDiscoveryAddsAreGated:

    DISCO = [{"ticker": "ZZZ", "sources": ["PREMOVER", "BEAR_DIP"]}]

    def test_discovery_is_off_by_default(self):
        conn = _rev_db()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02",
                        discoveries=self.DISCO)
        assert "ZZZ" not in {d.ticker for d in ds}

    def test_discovery_without_new_information_is_refused_even_when_enabled(self):
        """PREMOVER/BEAR_DIP/REVERSAL are all written 16:15-16:30, BEFORE the
        16:40 EOD job — a name found there is yesterday's data re-read, not new
        information (audit A-1)."""
        conn = _rev_db()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02",
                        discoveries=self.DISCO, allow_discovery_adds=True)
        assert "ZZZ" not in {d.ticker for d in ds}

    def test_discovery_with_new_information_is_admitted_and_justified(self):
        conn = _rev_db()
        conn.execute("INSERT INTO news_mentions VALUES "
                     "('ZZZ','2026-09-02',5,'[]','x')")
        conn.commit()
        ds = rev.revise(conn, BASE, base_date="2026-09-01", plan_date="2026-09-02",
                        discoveries=self.DISCO, allow_discovery_adds=True)
        zzz = next(d for d in ds if d.ticker == "ZZZ")
        assert zzz.action == wl.ACTION_ADD
        assert zzz.reason_code == rev.R_DISCOVERY
        assert "news" in zzz.evidence


class TestArrowRunsOneWay:

    def test_eod_no_longer_reads_same_day_premarket_approvals(self):
        """Behavioural: an approved premarket decision on the SAME date must not
        appear as a source, and must not lift the candidate's score."""
        from engine.trade_plan import gather_long_candidates
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE reversal_watchlist (scan_date TEXT, ticker TEXT,"
                     " direction TEXT, conviction REAL, close REAL, smart_money TEXT,"
                     " net_value REAL, reasons TEXT)")
        conn.execute("CREATE TABLE daily_screen (date TEXT, ticker TEXT, close REAL,"
                     " vol_ratio REAL, signal TEXT, delta REAL)")
        conn.execute("CREATE TABLE agent_decisions (ticker TEXT, confidence REAL,"
                     " created_at TEXT, strategy TEXT, decision TEXT)")
        conn.execute("CREATE TABLE scheduled_signals (id INTEGER PRIMARY KEY,"
                     " scan_time TEXT, ticker TEXT, strategies TEXT,"
                     " flow_score INT, signal_direction TEXT)")
        conn.execute("INSERT INTO daily_screen VALUES "
                     "('2026-09-01','PMK',100,1.0,'bullish',0)")
        conn.execute("INSERT INTO agent_decisions VALUES "
                     "('PMK',0.95,'2026-09-01 08:35','premarket','approve')")
        conn.commit()
        cands = {c["ticker"]: c for c in gather_long_candidates(conn, "2026-09-01")}
        assert cands["PMK"]["sources"] == ["S"]
        assert "P" not in cands["PMK"]["sources"]
        assert cands["PMK"]["premkt_conf"] is None

    def test_premarket_consumes_the_eod_ledger(self):
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_premarket_firm_scan)
        assert "base_plan" in src and "STRATEGY_EOD" in src
        assert "premarket_revision" in src

    def test_premarket_does_not_unconditionally_rebuild_a_universe(self):
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_premarket_firm_scan)
        body = src.split('"""', 2)[-1]          # ignore the docstring
        i = body.index("build_unified_watchlist")
        # the only executable reference must sit inside the discovery-adds branch
        assert "if _allow_adds:" in body[:i]

    def test_validated_walkforward_signals_feed_the_eod_pool(self):
        from engine.trade_plan import gather_long_candidates, candidate_score
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE reversal_watchlist (scan_date TEXT, ticker TEXT,"
                     " direction TEXT, conviction REAL, close REAL, smart_money TEXT,"
                     " net_value REAL, reasons TEXT)")
        conn.execute("CREATE TABLE daily_screen (date TEXT, ticker TEXT, close REAL,"
                     " vol_ratio REAL, signal TEXT, delta REAL)")
        conn.execute("CREATE TABLE agent_decisions (ticker TEXT, confidence REAL,"
                     " created_at TEXT, strategy TEXT, decision TEXT)")
        conn.execute("CREATE TABLE scheduled_signals (id INTEGER PRIMARY KEY,"
                     " scan_time TEXT, ticker TEXT, strategies TEXT,"
                     " flow_score INT, signal_direction TEXT)")
        conn.execute("INSERT INTO scheduled_signals VALUES "
                     "(1,'2026-09-01 10:05','WFT','NR7 Breakout',4,'BUY')")
        conn.execute("INSERT INTO daily_screen VALUES "
                     "('2026-09-01','SCR',100,1.0,'bullish',0)")
        conn.commit()
        cands = {c["ticker"]: c for c in gather_long_candidates(conn, "2026-09-01")}
        assert cands["WFT"]["sources"] == ["W"]
        assert cands["WFT"]["strategy_fn"] == "NR7 Breakout"
        # the evidenced source outranks every heuristic screen
        assert candidate_score(cands["WFT"]) > candidate_score(cands["SCR"])


class TestProvenance:

    def test_attach_provenance_records_price_rule_and_evidence(self):
        from engine import trade_plan as tp
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
        conn.execute("INSERT INTO ohlcv VALUES ('AAA','2026-09-01',1250.0)")
        conn.execute(
            "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
            " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
            " n_trades INT, windows_tested INT, last_computed TEXT,"
            " PRIMARY KEY(ticker,strategy))")
        conn.execute("INSERT INTO wf_edge VALUES ('AAA','NR7 Breakout',1.63,0,56,40,0.5,1311,15,?)",
                     (FRESH,))
        conn.commit()
        out = tp.attach_provenance(
            conn, [{"ticker": "AAA", "strategy_fn": "NR7 Breakout",
                    "sources": ["W"], "confluence": 1, "conviction": 0.0}],
            "2026-09-01", plan="eod")[0]
        assert out["decision_price"] == 1250.0
        assert out["decision_price_basis"] == "last_completed_close"
        assert out["entry_rule"] == "NEXT_SESSION_OPEN"
        assert out["wf_expectancy_pct"] == 1.63 and out["wf_n_trades"] == 1311
        assert out["rule_id"].startswith("NR7 Breakout@")
        assert out["provenance"]["evidence_backed"] is True

    def test_heuristic_candidate_is_marked_not_evidence_backed(self):
        from engine import trade_plan as tp
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
        conn.execute("INSERT INTO ohlcv VALUES ('SCR','2026-09-01',500.0)")
        conn.execute(
            "CREATE TABLE wf_edge (ticker TEXT, strategy TEXT, expectancy_pct REAL,"
            " expectancy_rp REAL, win_rate REAL, consistency_pct REAL, sharpe REAL,"
            " n_trades INT, windows_tested INT, last_computed TEXT,"
            " PRIMARY KEY(ticker,strategy))")
        conn.commit()
        out = tp.attach_provenance(
            conn, [{"ticker": "SCR", "sources": ["S", "V"], "confluence": 2}],
            "2026-09-01", plan="eod")[0]
        assert out["strategy_fn"] is None
        assert out["wf_expectancy_pct"] is None
        assert out["provenance"]["evidence_backed"] is False
