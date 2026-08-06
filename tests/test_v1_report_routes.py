"""Tests for routes/v1/reports.py -- /api/v1/reports, /api/v1/reports/{date}
(Production Engine Phase 2, Workstream 2C Task 2C-3).

Seeds via the real forward_testing.storage.repo.FTRepo writer methods and
the same _job_sentinel row scheduler.jobs.run_forward_test_cycle writes,
not raw INSERTs against derived state.
"""
import sqlite3

import pytest

from forward_testing.storage.db import init_ft_tables
from forward_testing.storage.repo import FTRepo
from routes.v1 import api_v1_bp


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    init_ft_tables(str(db))

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client(), str(db)


@pytest.fixture
def client(env):
    c, _ = env
    return c


def _mark_report_ran(db, run_date):
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS _job_sentinel "
                 "(job TEXT, run_date TEXT, PRIMARY KEY(job, run_date))")
    conn.execute("INSERT INTO _job_sentinel VALUES ('forward_test_cycle', ?)", (run_date,))
    conn.commit()
    conn.close()


def _open_and_close(db, ticker, entry_date, exit_date, entry_price, exit_price, exit_reason):
    repo = FTRepo(db)
    sid = repo.insert_signal(entry_date, ticker, "TFB", "SHADOW")
    repo.open_shadow_position(
        signal_id=sid, ticker=ticker, strategy="TFB", direction="LONG",
        entry_date=entry_date, entry_price=entry_price, atr14=1.0,
        sl_price=entry_price - 3, tp_price=entry_price + 6,
        trail_atr_mult=3.0, trail_anchor=entry_price,
        highest_seen=entry_price, lowest_seen=entry_price,
        signal_date=entry_date, raw_entry_price=entry_price,
    )
    pnl = (exit_price - entry_price) / entry_price
    repo.insert_shadow_trade(
        signal_id=sid, ticker=ticker, strategy="TFB", direction="LONG",
        signal_date=entry_date, entry_date=entry_date, entry_price=entry_price,
        exit_date=exit_date, exit_price=exit_price, exit_reason=exit_reason,
        pnl_pct=pnl, r_multiple=pnl / 0.03, hold_days=1,
        mae_pct=min(0.0, pnl), mfe_pct=max(0.0, pnl),
    )


class TestReportByDate:
    def test_returns_structured_report_for_that_date(self, env):
        c, db = env
        _mark_report_ran(db, "2026-08-05")
        _open_and_close(db, "BBCA", "2026-08-04", "2026-08-05", 100.0, 106.0, "TP")

        resp = c.get("/api/v1/reports/2026-08-05")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["date"] == "2026-08-05"
        assert [t["ticker"] for t in data["closed_trades"]] == ["BBCA"]
        assert data["win_loss"]["wins"] == 1

    def test_zero_activity_day_still_returns_200_when_report_ran(self, env):
        c, db = env
        _mark_report_ran(db, "2026-08-05")

        resp = c.get("/api/v1/reports/2026-08-05")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["new_positions"] == []
        assert data["win_loss"] is None

    def test_404_when_report_never_ran_that_date(self, client):
        resp = client.get("/api/v1/reports/2020-01-01")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_REPORT_DATA"


class TestReportsLatest:
    def test_returns_most_recent_report_not_necessarily_today(self, env):
        c, db = env
        _mark_report_ran(db, "2026-08-01")
        _mark_report_ran(db, "2026-08-05")

        resp = c.get("/api/v1/reports")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["date"] == "2026-08-05"

    def test_404_when_no_report_has_ever_run(self, client):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_REPORT_DATA"


class TestNoPresentationFormatting:
    def test_response_has_no_html_or_emoji_markup(self, env):
        c, db = env
        _mark_report_ran(db, "2026-08-05")
        _open_and_close(db, "BBCA", "2026-08-04", "2026-08-05", 100.0, 106.0, "TP")
        body = c.get("/api/v1/reports/2026-08-05").get_data(as_text=True)
        assert "<b>" not in body and "📊" not in body
