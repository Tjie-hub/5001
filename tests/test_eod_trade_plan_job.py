"""Tests for the EOD trade plan job's dedup guard (16:40 WIB job, scheduler.jobs).

Only covers the dedup-guard lock-handling path — the message-building logic
lives in engine.trade_plan and is covered by tests/test_trade_plan.py. Mirrors
tests/test_premarket_firm_scan.py::test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock
(RC1 F-3, 2026-07-28): run_eod_trade_plan's dedup insert now fails open on
sqlite3.OperationalError the same way run_premarket_firm_scan's does.

TestPersistentActiveWatchlistWiring covers the persistent multi-day
accumulated watchlist (engine.persistent_watchlist), appended to the END of
the SAME Trade Plan message (not a separate send_telegram call, unlike the
pre-firm watchlist_report hook above) — see tests/test_persistent_watchlist.py
for the module's own pure-function coverage.
"""
import sqlite3
from unittest.mock import MagicMock, patch


class _LockedSentinelConn:
    """Fake db_connect() return whose dedup-guard INSERT always finds the DB locked.

    Mirrors a real write-contention window (e.g. a long EOD write on the WAL db)
    outlasting the connection's busy_timeout. Identical to the fixture in
    tests/test_premarket_firm_scan.py, duplicated locally to keep this file
    independent of that one.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("INSERT"):
            raise sqlite3.OperationalError("database is locked")
        return None


def test_run_eod_trade_plan_fails_open_on_sentinel_db_lock(monkeypatch, caplog):
    """A locked DB on the dedup-guard insert must degrade the job, not crash it.

    EOD's own code comment states its 16:40 slot is more exposed to write
    contention than premarket's quiet 08:35 slot (it can overlap a long EOD
    write on the 2.5GB WAL db) — before RC1 F-3 it had no OperationalError
    handler at all, unlike premarket, which was patched for this exact failure
    mode after the 2026-07-24 08:35:30 production crash.
    """
    import scheduler.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "db_connect", lambda *a, **k: _LockedSentinelConn())

    def _must_not_run(*a, **k):
        raise AssertionError(
            "gather_long_candidates ran despite the dedup guard being locked out"
        )

    monkeypatch.setattr("engine.trade_plan.gather_long_candidates", _must_not_run)

    with caplog.at_level("WARNING"):
        jobs_mod.run_eod_trade_plan()  # must not raise

    assert any("database is locked" in r.message for r in caplog.records)


def _mock_firm_and_config(is_active=True):
    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(return_value=[])
    mock_cfg = MagicMock()
    mock_cfg.is_active = MagicMock(return_value=is_active)
    mock_cfg.get_enforce = MagicMock(return_value=False)
    return mock_firm, mock_cfg


class TestPersistentActiveWatchlistWiring:
    """The 16:40 job must append a '📋 ACTIVE WATCHLIST' section to the END of
    the EXISTING Trade Plan message (same send_telegram call — not a second,
    standalone message like watchlist_report's) and update the persistent
    multi-day persistent_watchlist table with today's approved tickers."""

    def _run(self, tmp_path, monkeypatch, cands, select_top=None):
        import scheduler.jobs as jobs_mod

        db = str(tmp_path / "wf.db")
        sent = []

        monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
        monkeypatch.setattr(jobs_mod, "DB_PATH", db)
        monkeypatch.setattr("engine.trade_plan.gather_long_candidates",
                            lambda conn, date_str: cands)
        monkeypatch.setattr("engine.trade_plan.get_regime",
                            lambda conn, date_str: ("BULL", 72.0))
        monkeypatch.setattr("engine.trade_plan.select_top",
                            select_top or (lambda c, n=8: c))
        monkeypatch.setattr("engine.trade_plan.get_vpin_gate", lambda conn, date_str: None)
        monkeypatch.setattr("config.edge_mode", lambda: "off")
        monkeypatch.setattr(jobs_mod, "send_telegram", lambda msg: sent.append(msg))

        mock_firm, mock_cfg = _mock_firm_and_config()
        import engine.agent_firm as _pkg
        import sys
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }):
            jobs_mod.run_eod_trade_plan()

        return db, sent

    def test_active_watchlist_section_appended_to_trade_plan_message(self, tmp_path, monkeypatch):
        db, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])

        trade_plan_msgs = [m for m in sent if "TRADE PLAN" in m]
        assert len(trade_plan_msgs) == 1
        assert "📋 ACTIVE WATCHLIST" in trade_plan_msgs[0]
        # Not a separate message — same send_telegram call as the Trade Plan.
        assert not any("📋 ACTIVE WATCHLIST" in m and "TRADE PLAN" not in m for m in sent)

    def test_updates_persistent_watchlist_table(self, tmp_path, monkeypatch):
        db, _ = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])

        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ticker, status, consecutive_days FROM persistent_watchlist"
        ).fetchall()
        conn.close()
        assert row == [("MDKA", "ACTIVE", 1)]

    def test_second_day_shows_two_day_streak(self, tmp_path, monkeypatch):
        db, _ = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])

        # Backdate + clear the dedup sentinel so the second run isn't skipped
        # as a same-day rerun (both calls share the same tmp db + real today).
        conn = sqlite3.connect(db)
        conn.execute("UPDATE persistent_watchlist SET last_seen_date='2020-01-01'")
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()

        _, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])

        trade_plan_msgs = [m for m in sent if "TRADE PLAN" in m]
        assert "MDKA (2d)" in trade_plan_msgs[0]

    def test_active_watchlist_section_appended_on_empty_top_path(self, tmp_path, monkeypatch):
        """When every candidate is filtered out before the firm (top=[] while
        cands is non-empty), the existing 'empty plan' message still ships —
        and the persistent watchlist must still update (everyone previously
        active gets marked REMOVED, since nothing was approved today)."""
        db, _ = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])
        conn = sqlite3.connect(db)
        conn.execute("UPDATE persistent_watchlist SET last_seen_date='2020-01-01'")
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()

        _, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ], select_top=lambda c, n=8: [])

        trade_plan_msgs = [m for m in sent if "TRADE PLAN" in m]
        assert len(trade_plan_msgs) == 1
        assert "📋 ACTIVE WATCHLIST" in trade_plan_msgs[0]
        assert "👋 Removed Today" in trade_plan_msgs[0]
        assert "MDKA" in trade_plan_msgs[0]

        conn = sqlite3.connect(db)
        status = conn.execute(
            "SELECT status FROM persistent_watchlist WHERE ticker='MDKA'"
        ).fetchone()[0]
        conn.close()
        assert status == "REMOVED"

    def test_persistent_watchlist_error_does_not_block_trade_plan(self, tmp_path, monkeypatch):
        """Fail-soft: a broken persistent_watchlist module must not prevent
        the existing Trade Plan message from shipping."""
        db, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()
        monkeypatch.setattr(
            "engine.persistent_watchlist.update_watchlist",
            lambda conn, date_str, tickers: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        _, sent2 = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])
        trade_plan_msgs = [m for m in sent2 if "TRADE PLAN" in m]
        assert len(trade_plan_msgs) == 1
        assert "📋 ACTIVE WATCHLIST" not in trade_plan_msgs[0]
