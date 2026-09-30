"""P3-2 regression: a same-day forming-bar price can never reach a fill.

TODO.md P3: live scans read is_final=0 bars and fed that price straight into
paper_trade.open_trade() — paper-trade P&L was evidence for an execution model
the backtests never validated. The fix stages every live auto-entry
(paper_trade.stage_entry) and fills it at the NEXT session's open
(paper_trade.resolve_staged_entries, driven by
scheduler.jobs.run_staged_entry_fills) — the convention
engine/entry_convention.py documents and every walk-forward strategy uses.

These tests pin that contract: the fill price equals the next bar's OPEN
(the bar that is provisional, is_final=0, at fill time), never the forming
bar's close, never the decision price, and never a later session's price
(a missed window expires instead).
"""
import sqlite3

import pytest


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with an ohlcv table (is_final-aware schema)."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
        "low REAL, close REAL, volume REAL, is_final INTEGER)")
    conn.commit()
    conn.close()
    return db


def _add_bar(db, ticker, date, o, h, l, c, is_final=1, v=1_000_000):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?,?)",
                 (ticker, date, o, h, l, c, v, is_final))
    conn.commit()
    conn.close()


def _staged_rows(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM staged_entries").fetchall()]
    conn.close()
    return rows


def _paper_trades(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM paper_trades").fetchall()]
    conn.close()
    return rows


class TestNextSessionOpenFill:

    def test_fill_price_is_next_bar_open_not_forming_close(self, pt_db):
        """The core P3 contract: signal bar D1 final, D2 provisional (is_final=0).

        The fill must be D2's OPEN (what a market-on-open order transacts at),
        never D2's forming close (the old bug's price) and never D1's close
        (the decision price).
        """
        from paper_trade import resolve_staged_entries, stage_entry
        # Signal bar: closed at 1050 (this was the old fill price).
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, source="daily_signal_scan",
                    signal_date="2026-06-01")
        # Next session's bar, still provisional at fill time: opened 1010,
        # currently trading at 1080.
        _add_bar(pt_db, "TEST", "2026-06-02", o=1010, h=1090, l=1000, c=1080,
                 is_final=0)

        results = resolve_staged_entries("2026-06-02")

        assert len(results) == 1
        assert results[0]["status"] == "FILLED"
        trades = _paper_trades(pt_db)
        assert len(trades) == 1
        assert trades[0]["entry_price"] == 1010.0
        assert trades[0]["entry_price"] != 1080.0   # forming close — never a fill
        assert trades[0]["entry_price"] != 1050.0   # decision price — never a fill

    def test_decision_price_kept_for_audit_trail(self, pt_db):
        from paper_trade import stage_entry
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, source="daily_signal_scan",
                    signal_date="2026-06-01")
        rows = _staged_rows(pt_db)
        assert rows[0]["decision_price"] == 1050.0
        assert rows[0]["status"] == "PENDING"

    def test_same_day_signal_never_fills(self, pt_db):
        """A signal staged today must not fill from today's forming bar."""
        from paper_trade import resolve_staged_entries, stage_entry
        _add_bar(pt_db, "TEST", "2026-06-02", o=1010, h=1090, l=1000, c=1080,
                 is_final=0)
        stage_entry("TEST", 1080.0, source="daily_signal_scan",
                    signal_date="2026-06-02")

        results = resolve_staged_entries("2026-06-02")

        assert results == []
        assert _paper_trades(pt_db) == []
        assert _staged_rows(pt_db)[0]["status"] == "PENDING"

    def test_missing_next_bar_stays_pending(self, pt_db):
        """No bar for the fill session yet (fetch not run) → retry later."""
        from paper_trade import resolve_staged_entries, stage_entry
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, signal_date="2026-06-01")

        results = resolve_staged_entries("2026-06-02")

        assert results[0]["status"] == "PENDING"
        assert _paper_trades(pt_db) == []


class TestFillWindow:

    def test_window_expires_after_missed_session(self, pt_db):
        """A full session passed unfilled → EXPIRED, never a late open fill."""
        from paper_trade import resolve_staged_entries, stage_entry
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, signal_date="2026-06-01")
        # 06-02's session came and went without a resolve; now it's 06-03.
        _add_bar(pt_db, "TEST", "2026-06-02", o=1010, h=1090, l=1000, c=1080)
        _add_bar(pt_db, "TEST", "2026-06-03", o=1100, h=1150, l=1090, c=1140)

        results = resolve_staged_entries("2026-06-03")

        assert results[0]["status"] == "EXPIRED"
        assert _paper_trades(pt_db) == []

    def test_suspension_resume_fills_at_first_traded_open(self, pt_db):
        """Weekend/holiday/suspension gap: fill at the first bar after the
        signal bar — the next session the ticker actually traded."""
        from paper_trade import resolve_staged_entries, stage_entry
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, signal_date="2026-06-01")
        # Ticker suspended 06-02..06-04; first bar back is 06-05.
        _add_bar(pt_db, "TEST", "2026-06-05", o=990, h=1010, l=950, c=1000,
                 is_final=0)

        results = resolve_staged_entries("2026-06-05")

        assert results[0]["status"] == "FILLED"
        assert _paper_trades(pt_db)[0]["entry_price"] == 990.0


class TestFillTimeGuards:

    def test_duplicate_open_position_skips_fill(self, pt_db):
        from paper_trade import open_trade, resolve_staged_entries, stage_entry
        for i in range(1, 15):
            _add_bar(pt_db, "TEST", f"2026-05-{i+10:02d}", o=1000, h=1010,
                     l=990, c=1000)
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        assert "id" in open_trade("TEST", 1000.0, notify=False)
        stage_entry("TEST", 1050.0, signal_date="2026-06-01")
        _add_bar(pt_db, "TEST", "2026-06-02", o=1010, h=1090, l=1000, c=1080,
                 is_final=0)

        results = resolve_staged_entries("2026-06-02")

        assert results[0]["status"] == "SKIPPED"
        assert len(_paper_trades(pt_db)) == 1

    def test_max_open_cap_skips_fill(self, pt_db):
        from paper_trade import resolve_staged_entries, stage_entry
        conn = sqlite3.connect(pt_db)
        conn.execute("INSERT OR REPLACE INTO paper_config VALUES ('max_open','0')")
        conn.commit()
        conn.close()
        _add_bar(pt_db, "TEST", "2026-06-01", o=1000, h=1060, l=990, c=1050)
        stage_entry("TEST", 1050.0, signal_date="2026-06-01")
        _add_bar(pt_db, "TEST", "2026-06-02", o=1010, h=1090, l=1000, c=1080,
                 is_final=0)

        results = resolve_staged_entries("2026-06-02")

        assert results[0]["status"] == "SKIPPED"
        assert "Max" in results[0]["note"]
        assert _paper_trades(pt_db) == []
