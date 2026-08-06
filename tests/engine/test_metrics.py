"""Tests for engine/metrics.py -- extracted from app.py's Prometheus
/metrics route as a reusable service function (Production Engine Phase 2,
Workstream 2B Task 2B-2). app.py's route itself is untouched; this covers
only the new service function.
"""
import sqlite3

import pytest

from engine.metrics import get_engine_metrics


def _make_db(tmp_path):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE paper_trades (status TEXT);
        CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT);
        CREATE TABLE agent_decisions (scan_time TEXT);
        CREATE TABLE ohlcv (ticker TEXT, date TEXT);
        CREATE TABLE market_risk_log (score REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE daily_screen (date TEXT, ticker TEXT, vpin REAL);
    """)
    conn.commit()
    conn.close()
    return str(db)


class TestGetEngineMetrics:
    def test_all_zero_on_empty_database(self, tmp_path):
        db = _make_db(tmp_path)
        data = get_engine_metrics(db)
        assert data["open_trades"] == 0
        assert data["signals_today_total"] == 0
        assert data["signals_today_buy"] == 0
        assert data["signals_today_sell"] == 0
        assert data["agent_decisions_today"] == 0
        assert data["ohlcv_tickers_today"] == 0
        assert data["market_risk_score"] is None
        assert data["avg_vpin_today"] is None
        assert data["last_scan_at"] is None

    def test_counts_todays_rows_only(self, tmp_path):
        db = _make_db(tmp_path)
        conn = sqlite3.connect(db)
        today = "2026-08-06"
        conn.execute("INSERT INTO paper_trades VALUES ('OPEN')")
        conn.execute("INSERT INTO paper_trades VALUES ('CLOSED')")
        conn.execute("INSERT INTO scheduled_signals VALUES (?, 'BUY')", (f"{today} 09:00:00",))
        conn.execute("INSERT INTO scheduled_signals VALUES (?, 'SELL')", (f"{today} 10:00:00",))
        conn.execute("INSERT INTO scheduled_signals VALUES ('2020-01-01 09:00:00', 'BUY')")  # not today
        conn.execute("INSERT INTO agent_decisions VALUES (?)", (f"{today} 09:00:00",))
        conn.execute("INSERT INTO ohlcv VALUES ('BBCA', ?)", (today,))
        conn.execute("INSERT INTO ohlcv VALUES ('TLKM', ?)", (today,))
        conn.execute("INSERT INTO daily_screen VALUES (?, 'BBCA', 0.6)", (today,))
        conn.commit()
        conn.close()

        from datetime import date
        import engine.metrics as metrics_mod
        original_today = metrics_mod._today
        metrics_mod._today = lambda: today
        try:
            data = get_engine_metrics(db)
        finally:
            metrics_mod._today = original_today

        assert data["open_trades"] == 1
        assert data["signals_today_total"] == 2
        assert data["signals_today_buy"] == 1
        assert data["signals_today_sell"] == 1
        assert data["agent_decisions_today"] == 1
        assert data["ohlcv_tickers_today"] == 2
        assert data["avg_vpin_today"] == 0.6

    def test_reads_latest_market_risk_score_by_correct_columns(self, tmp_path):
        """Regression guard: app.py's Prometheus route queries the wrong
        columns (risk_score/computed_at, which don't exist -- real schema is
        score/created_at per engine/risk_alert.py) and has always silently
        returned NaN there. This service function must use the real ones."""
        db = _make_db(tmp_path)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO market_risk_log (score, created_at) VALUES (42.5, '2026-08-05 10:00:00')")
        conn.execute("INSERT INTO market_risk_log (score, created_at) VALUES (55.0, '2026-08-06 10:00:00')")
        conn.commit()
        conn.close()

        data = get_engine_metrics(db)
        assert data["market_risk_score"] == 55.0

    def test_last_scan_at_reflects_most_recent_scan(self, tmp_path):
        db = _make_db(tmp_path)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO scheduled_signals VALUES ('2026-08-01T09:00:00', 'BUY')")
        conn.execute("INSERT INTO scheduled_signals VALUES ('2026-08-05T16:00:00', 'SELL')")
        conn.commit()
        conn.close()

        data = get_engine_metrics(db)
        assert data["last_scan_at"] == "2026-08-05T16:00:00"

    def test_bad_db_path_raises(self, tmp_path):
        """No fail-soft at this layer for a totally unreachable DB -- the
        controller lets it hit the existing generic 500 envelope handler,
        same as every other v1 endpoint."""
        with pytest.raises(Exception):
            get_engine_metrics(str(tmp_path / "does" / "not" / "exist.db"))
