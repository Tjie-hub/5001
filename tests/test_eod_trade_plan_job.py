"""Tests for the EOD trade plan job's dedup guard (16:40 WIB job, scheduler.jobs).

Only covers the dedup-guard lock-handling path — the message-building logic
lives in engine.trade_plan and is covered by tests/test_trade_plan.py. Mirrors
tests/test_premarket_firm_scan.py::test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock
(RC1 F-3, 2026-07-28): run_eod_trade_plan's dedup insert now fails open on
sqlite3.OperationalError the same way run_premarket_firm_scan's does.

TestWatchlistUpdateReportWiring covers the pre-firm candidate Watchlist
Update report hook (engine.watchlist_report), added as a standalone second
Telegram message inside this job — see tests/test_watchlist_report.py for
the module's own pure-function coverage.

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


class TestWatchlistUpdateReportWiring:
    """The 16:40 job must send a second, standalone Telegram message with the
    pre-firm candidate watchlist (engine.watchlist_report) — distinct from the
    Trade Plan message — and persist a row per candidate to
    candidate_watchlist_snapshot, on every run (approved, degraded, or vetoed)."""

    def _run(self, tmp_path, monkeypatch, cands):
        import scheduler.jobs as jobs_mod

        db = str(tmp_path / "wf.db")
        sent = []

        monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
        monkeypatch.setattr(jobs_mod, "DB_PATH", db)
        monkeypatch.setattr("engine.trade_plan.gather_long_candidates",
                            lambda conn, date_str: cands)
        monkeypatch.setattr("engine.trade_plan.get_regime",
                            lambda conn, date_str: ("BULL", 72.0))
        monkeypatch.setattr("engine.trade_plan.select_top", lambda c, n=8: c)
        monkeypatch.setattr("engine.trade_plan.get_vpin_gate", lambda conn, date_str: None)
        monkeypatch.setattr("config.edge_mode", lambda: "off")
        monkeypatch.setattr(jobs_mod, "send_telegram",
                            lambda msg, **kw: sent.append(msg))   # real fn takes category=

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

    def test_sends_standalone_watchlist_update_message(self, tmp_path, monkeypatch):
        db, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5,
             "net_value": 1e9, "reason": "broker ACCUMULATION"},
        ])

        watchlist_msgs = [m for m in sent if "WATCHLIST UPDATE" in m]
        assert len(watchlist_msgs) == 1
        # First run ever for this DB — no prior snapshot to diff against.
        assert "Current Watchlist: 1" in watchlist_msgs[0]

        # A separate message (the Trade Plan) must also have been sent.
        assert len(sent) == 2

    def test_persists_snapshot_row_per_candidate(self, tmp_path, monkeypatch):
        db, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
            {"ticker": "BBRI", "conviction": 55.0, "smart_money": None,
             "sources": ["S"], "confluence": 1, "vol_ratio": 3.0, "net_value": 0.0},
        ])

        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT ticker FROM candidate_watchlist_snapshot ORDER BY ticker"
        ).fetchall()
        conn.close()
        assert [r[0] for r in rows] == ["BBRI", "MDKA"]

    def test_second_day_reports_added_ticker(self, tmp_path, monkeypatch):
        db, _ = self._run(tmp_path, monkeypatch, [{
            "ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
            "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9,
        }])

        # Backdate today's just-written snapshot to "yesterday" so the second
        # run below has a real prior day to diff against, and clear the job's
        # dedup-guard sentinel so the second call isn't skipped as a same-day
        # rerun (both calls otherwise share the same tmp db + real today's date).
        conn = sqlite3.connect(db)
        conn.execute("UPDATE candidate_watchlist_snapshot SET date='2020-01-01'")
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()

        _, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
            {"ticker": "GPSO", "conviction": 60.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.0, "net_value": 5e8},
        ])

        watchlist_msgs = [m for m in sent if "WATCHLIST UPDATE" in m]
        assert len(watchlist_msgs) == 1
        assert "Added (1)" in watchlist_msgs[0]
        assert "+ GPSO" in watchlist_msgs[0]

    def test_watchlist_report_error_does_not_block_trade_plan(self, tmp_path, monkeypatch):
        """Fail-soft: if the watchlist report hook raises, the existing Trade
        Plan message must still ship (matches the fail-soft posture already
        used for the VPIN/context/edge-prescreen paths in this job)."""
        import scheduler.jobs as jobs_mod

        db, sent = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])
        # Sanity baseline already proved 2 messages ship; now prove a broken
        # watchlist_report module still leaves the Trade Plan message intact.
        # Clear the dedup-guard sentinel first — both calls share the same tmp
        # db + real today's date, so without this the second run would be
        # skipped outright as a same-day rerun (not what this test is about).
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()
        monkeypatch.setattr("engine.watchlist_report.diff_snapshot",
                            lambda conn, date_str: (_ for _ in ()).throw(RuntimeError("boom")))
        db2, sent2 = self._run(tmp_path, monkeypatch, [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ])
        assert any("TRADE PLAN" in m for m in sent2)
        assert not any("WATCHLIST UPDATE" in m for m in sent2)

    def test_empty_watchlist_still_sends_update_message(self, tmp_path, monkeypatch):
        """cands=[] must still reach and fire the watchlist_report hook (it
        sits BEFORE the `if not cands: return` early exit) — no crash, and
        the Trade Plan message never ships since the job returns right after."""
        db, sent = self._run(tmp_path, monkeypatch, [])

        watchlist_msgs = [m for m in sent if "WATCHLIST UPDATE" in m]
        assert len(watchlist_msgs) == 1
        assert "Current Watchlist: 0" in watchlist_msgs[0]
        assert len(sent) == 1  # no candidates -> job exits, no Trade Plan message

        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM candidate_watchlist_snapshot"
        ).fetchone()[0]
        conn.close()
        assert count == 0

    def test_duplicate_daily_run_does_not_duplicate_snapshot_rows(self, tmp_path, monkeypatch):
        """A second run_eod_trade_plan() call on the SAME day (real dedup
        guard, sentinel not cleared) must be skipped outright — no second
        watchlist message, no duplicate/altered candidate_watchlist_snapshot
        row."""
        cands = [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ]
        db, sent1 = self._run(tmp_path, monkeypatch, cands)
        assert len(sent1) == 2  # baseline: watchlist update + trade plan

        _, sent2 = self._run(tmp_path, monkeypatch, cands)  # dup run, same day
        assert sent2 == []  # dedup guard skips the whole job body

        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT ticker FROM candidate_watchlist_snapshot"
        ).fetchall()
        conn.close()
        assert [r[0] for r in rows] == ["MDKA"]  # exactly one row, not duplicated

    def test_no_changes_message_shown_on_identical_second_day(self, tmp_path, monkeypatch):
        """An unchanged candidate set across two real trading days must render
        the module's own 'No watchlist changes today.' copy end-to-end."""
        cands = [
            {"ticker": "MDKA", "conviction": 70.0, "smart_money": "YES",
             "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1e9},
        ]
        db, _ = self._run(tmp_path, monkeypatch, cands)

        conn = sqlite3.connect(db)
        conn.execute("UPDATE candidate_watchlist_snapshot SET date='2020-01-01'")
        conn.execute("DELETE FROM _job_sentinel")
        conn.commit()
        conn.close()

        _, sent = self._run(tmp_path, monkeypatch, cands)  # identical set, "next day"

        watchlist_msgs = [m for m in sent if "WATCHLIST UPDATE" in m]
        assert len(watchlist_msgs) == 1
        assert "No watchlist changes today." in watchlist_msgs[0]


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
        monkeypatch.setattr(jobs_mod, "send_telegram",
                            lambda msg, **kw: sent.append(msg))   # real fn takes category=

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


class _DuplicateSentinelConn:
    """Fake db_connect() return whose dedup-guard INSERT always finds a
    duplicate row already present — mirrors _LockedSentinelConn but for the
    IntegrityError branch. Duplicated locally per this file's own convention
    (see module docstring) of keeping fixtures independent of sibling test
    files."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("INSERT"):
            raise sqlite3.IntegrityError("UNIQUE constraint failed")
        return None


def test_run_eod_trade_plan_marks_skipped_on_holiday(monkeypatch):
    import scheduler.jobs as jobs_mod
    from unittest.mock import MagicMock

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: True)
    fake_handle = MagicMock()
    monkeypatch.setattr(jobs_mod, "current_job", lambda: fake_handle)

    jobs_mod.run_eod_trade_plan()

    fake_handle.mark_skipped.assert_called_once_with("holiday")


def test_run_eod_trade_plan_marks_skipped_on_duplicate_run(monkeypatch):
    import scheduler.jobs as jobs_mod
    from unittest.mock import MagicMock

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "db_connect", lambda *a, **k: _DuplicateSentinelConn())
    fake_handle = MagicMock()
    monkeypatch.setattr(jobs_mod, "current_job", lambda: fake_handle)

    jobs_mod.run_eod_trade_plan()

    fake_handle.mark_skipped.assert_called_once_with("duplicate_run")


def test_run_eod_trade_plan_marks_skipped_on_dedup_guard_error(monkeypatch, caplog):
    import scheduler.jobs as jobs_mod
    from unittest.mock import MagicMock

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "db_connect", lambda *a, **k: _LockedSentinelConn())
    fake_handle = MagicMock()
    monkeypatch.setattr(jobs_mod, "current_job", lambda: fake_handle)

    with caplog.at_level("WARNING"):
        jobs_mod.run_eod_trade_plan()

    fake_handle.mark_skipped.assert_called_once()
    reason = fake_handle.mark_skipped.call_args[0][0]
    assert reason.startswith("dedup_guard_error:")
