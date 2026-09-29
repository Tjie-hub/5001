"""Canonical strategy version (blocker #3) and the pre-registered forward-test
window (blocker #5)."""
import json
import sqlite3

import pytest

from engine import strategy_version as sv
from engine import forward_window as fw
from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo


@pytest.fixture()
def db(tmp_path):
    p = str(tmp_path / "ft.db")
    init_ft_tables(p)
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE paper_config (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO paper_config VALUES ('disabled_strategies','momentum,ORB')")
    conn.commit()
    conn.close()
    return p


# ─────────────────── strategy version ───────────────────

class TestStrategyVersion:

    def test_config_spans_backtest_and_live_checker(self):
        """A hash over only one side would let research and production drift
        apart unnoticed — which is exactly finding L-1."""
        cfg = sv.config_for("NR7 Breakout")
        assert cfg["backtest_fn_sha256"] and cfg["live_checker_sha256"]
        assert cfg["backtest_fn_sha256"] != cfg["live_checker_sha256"]

    def test_config_records_the_live_gate_set_and_rule_id(self):
        cfg = sv.config_for("NR7 Breakout")
        assert cfg["live_gates"] == ["weekly_mtf_trend"]
        assert cfg["rule_id"].startswith("NR7 Breakout@weekly_mtf_trend#")
        bypass = sv.config_for("Liquidity Sweep")
        assert bypass["live_gates"] == []

    def test_hash_changes_when_the_gate_set_changes(self, monkeypatch):
        before = sv.config_hash("NR7 Breakout")
        import engine.rule_identity as ri
        monkeypatch.setattr(ri, "live_gates", lambda s: ())
        assert sv.config_hash("NR7 Breakout") != before

    def test_upsert_is_idempotent(self, db):
        conn = sqlite3.connect(db)
        a = sv.upsert(conn, "NR7 Breakout")
        b = sv.upsert(conn, "NR7 Breakout")
        conn.commit()
        assert a == b
        n = conn.execute("SELECT COUNT(*) FROM ft_strategy_version "
                         "WHERE strategy='NR7 Breakout'").fetchone()[0]
        conn.close()
        assert n == 1

    def test_sync_all_covers_every_strategy(self, db):
        from engine.strategies import STRATEGY_FUNCS
        conn = sqlite3.connect(db)
        ids = sv.sync_all(conn)
        conn.close()
        assert set(ids) == set(STRATEGY_FUNCS)
        assert all(v for v in ids.values())

    def test_version_label_carries_the_registry_version(self, db):
        conn = sqlite3.connect(db)
        sv.upsert(conn, "NR7 Breakout", registry_version=2)
        row = conn.execute("SELECT version FROM ft_strategy_version "
                           "WHERE strategy='NR7 Breakout'").fetchone()
        conn.close()
        assert row[0].startswith("v2+")

    def test_resolve_works_for_a_cohort_pseudo_strategy(self, db):
        """'eod'/'premarket' are not STRATEGY_FUNCS keys but their cohorts still
        need pinning to the code that produced them."""
        conn = sqlite3.connect(db)
        vid, h = sv.resolve(conn, "eod")
        conn.close()
        assert vid and h


class TestAdaptersPinVersions:

    def test_watchlist_signals_carry_a_version_and_hash(self, db):
        from engine import watchlist_ledger as wl
        from forward_testing.adapters.watchlist_adapter import WatchlistAdapter
        conn = sqlite3.connect(db)
        wl.ensure_tables(conn)
        wl.append_snapshot(conn, "2026-09-01", "eod",
                           [{"ticker": "AAA", "strategy_fn": "NR7 Breakout",
                             "decision_price": 100.0}])
        conn.close()
        WatchlistAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        vid, ch = conn.execute("SELECT strategy_version_id, config_hash "
                               "FROM ft_signal").fetchone()
        conn.close()
        assert vid is not None and ch

    def test_scanner_signals_carry_a_version_and_hash(self, db):
        from forward_testing.adapters.signal_adapter import SignalAdapter
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE IF NOT EXISTS scheduled_signals ("
                     "id INTEGER PRIMARY KEY, scan_time TEXT, ticker TEXT,"
                     " strategies TEXT, flow_score INT, signal_direction TEXT)")
        conn.execute("INSERT INTO scheduled_signals VALUES "
                     "(1,'2026-09-01 10:05','AAA','NR7 Breakout',3,'BUY')")
        conn.commit(); conn.close()
        SignalAdapter(FTRepo(db), db).ingest("2026-09-01")
        conn = sqlite3.connect(db)
        vid, ch = conn.execute("SELECT strategy_version_id, config_hash "
                               "FROM ft_signal").fetchone()
        conn.close()
        assert vid is not None and ch


# ─────────────────── forward window ───────────────────

class TestForwardWindow:

    def test_opens_and_freezes_a_configuration(self, db):
        conn = sqlite3.connect(db)
        r = fw.check(conn, "eod")
        conn.close()
        assert r["action"] == "opened"
        w = r["window"]
        assert w["status"] == fw.STATUS_OPEN and w["config_hash"]
        assert w["decision_rule"].startswith("Pre-registered")

    def test_unchanged_configuration_keeps_the_window(self, db):
        conn = sqlite3.connect(db)
        fw.check(conn, "eod")
        r = fw.check(conn, "eod")
        conn.close()
        assert r["action"] == "unchanged" and not r["changes"]

    def test_config_change_closes_as_contaminated_and_opens_a_successor(self, db):
        conn = sqlite3.connect(db)
        first = fw.check(conn, "eod")["window"]
        conn.execute("UPDATE paper_config SET value='momentum' "
                     "WHERE key='disabled_strategies'")
        conn.commit()
        r = fw.check(conn, "eod")
        events = [x[0] for x in conn.execute(
            "SELECT event FROM ft_window_event ORDER BY id")]
        conn.close()
        assert r["action"] == "rolled"
        assert any("disabled_strategies" in c for c in r["changes"])
        assert r["window"]["predecessor_id"] == first["window_id"]
        assert events == ["OPEN", fw.EVENT_CLOSE_CONTAMINATED, "OPEN"]

    def test_windows_are_append_only(self, db):
        conn = sqlite3.connect(db)
        fw.check(conn, "eod")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE ft_window SET config_hash='x'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM ft_window")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE ft_window_event SET event='x'")
        conn.close()

    def test_frozen_config_captures_the_levers_that_change_behaviour(self, db):
        conn = sqlite3.connect(db)
        cfg = fw.frozen_config(conn, "eod")
        conn.close()
        for key in ("edge_score_mode", "registry", "paper_config", "scanner",
                    "admission", "veto", "trade_plan", "unified_watchlist",
                    "costs", "strategy_versions", "entry_rule"):
            assert key in cfg, key
        assert cfg["entry_rule"] == "NEXT_SESSION_OPEN"

    def test_stopping_rule_is_preregistered_and_date_based(self, db):
        conn = sqlite3.connect(db)
        w = fw.check(conn, "eod")["window"]
        conn.close()
        assert w["min_sessions"] == fw.MIN_SESSIONS_DECISION == 125
        assert w["min_signals"] == fw.MIN_SIGNALS_DECISION == 100
        assert "per-DATE mean" in w["decision_rule"]
        assert "never pooled" in w["decision_rule"]
        assert "Bonferroni" in w["decision_rule"]

    def test_progress_refuses_to_be_readable_on_an_empty_window(self, db):
        conn = sqlite3.connect(db)
        fw.check(conn, "eod")
        p = fw.progress(conn, "eod")
        conn.close()
        assert p["signals"] == 0 and p["sessions"] == 0
        assert p["readable"] is False and p["decidable"] is False

    def test_all_three_cohorts_get_independent_windows(self, db):
        conn = sqlite3.connect(db)
        out = fw.check_all(conn)
        conn.close()
        assert set(out) == set(fw.COHORTS)
        ids = {r["window"]["window_id"] for r in out.values()}
        assert len(ids) == 3

    def test_cycle_maintains_windows(self):
        import inspect
        from scheduler import jobs
        src = inspect.getsource(jobs.run_forward_test_cycle)
        assert "forward_window" in src and "check_all" in src


class TestWindowRegistryIdentity:
    """The window must key on what the registry SAYS, not on the git commit.

    Until 2026-09-29 frozen_config used registry_loader's hash, which is
    `git rev-parse HEAD`: every commit + restart closed all three cohorts as
    CONTAMINATED (six false closures 09-15..09-28, zero registry bytes changed),
    so no window could ever reach the 125-session stopping rule.
    """

    @pytest.fixture()
    def reg_dir(self, tmp_path, monkeypatch):
        d = tmp_path / "registry"
        (d / "manifests").mkdir(parents=True)
        (d / "artifacts").mkdir()
        (d / "edge_registry.yaml").write_text("entries: []\n")
        (d / "manifests" / "X_v1.yaml").write_text("id: X\n")
        (d / "artifacts" / "X_tickers.json").write_text('["AAAA"]')
        monkeypatch.setattr(fw, "REGISTRY_DIR", str(d))
        return d

    def _fake_head(self, monkeypatch, sha):
        from engine import registry_loader as rl
        monkeypatch.setattr(rl, "get_registry", lambda: {
            "hash": sha, "entries": [{"status": "SHADOW"}], "skipped": [],
            "debt": [1], "violations": []})

    def test_a_new_commit_alone_does_not_roll_the_window(self, db, reg_dir, monkeypatch):
        conn = sqlite3.connect(db)
        self._fake_head(monkeypatch, "226d405")
        fw.check(conn, "eod")
        self._fake_head(monkeypatch, "f46f33d")
        r = fw.check(conn, "eod")
        conn.close()
        assert r["action"] == "unchanged", r["changes"]

    def test_the_commit_sha_is_not_in_the_frozen_config(self, db, reg_dir, monkeypatch):
        self._fake_head(monkeypatch, "f46f33d")
        conn = sqlite3.connect(db)
        cfg = fw.frozen_config(conn, "eod")
        conn.close()
        assert "f46f33d" not in json.dumps(cfg)

    @pytest.mark.parametrize("rel", ["edge_registry.yaml", "manifests/X_v1.yaml",
                                     "artifacts/X_tickers.json"])
    def test_a_registry_content_change_still_rolls(self, db, reg_dir, monkeypatch, rel):
        self._fake_head(monkeypatch, "226d405")
        conn = sqlite3.connect(db)
        fw.check(conn, "eod")
        (reg_dir / rel).write_text("changed\n")
        r = fw.check(conn, "eod")
        conn.close()
        assert r["action"] == "rolled"
        assert any("registry" in c for c in r["changes"])

    def test_a_new_manifest_file_rolls(self, db, reg_dir, monkeypatch):
        self._fake_head(monkeypatch, "226d405")
        conn = sqlite3.connect(db)
        fw.check(conn, "eod")
        (reg_dir / "manifests" / "X_v2.yaml").write_text("id: X\nversion: 2\n")
        r = fw.check(conn, "eod")
        conn.close()
        assert r["action"] == "rolled"
