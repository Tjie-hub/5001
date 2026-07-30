"""Tests for P0.E1.S2.T5 — auto_trade_status_report query scoping + WIB fix.

DEBT-001: the report queried every `paper_trades` row opened in the last
day regardless of which path created it, even though its Telegram header
reads "Auto-Trade Status" — a manual or other-strategy entry would be
misrepresented as auto-trade activity.

DEBT-002: its `yesterday` cutoff used naive, timezone-unaware
`datetime.now()` while every other date reference in this file (and the
function's own display timestamp) uses `datetime.now(WIB)`.

These tests build an isolated DB with the same `paper_trades` +
`premover_auto_log` schema `paper_trade.init_paper_table()` creates, and
assert the report only surfaces rows `run_premover_eod`'s enforce-mode
path actually opened (ticker + entry_date matched against a
`would_trade=1`, `mode='enforce'` `premover_auto_log` row) — not manual
or other-strategy entries that happen to share the table — and that the
cutoff is computed from WIB, not naive/system time.
"""
import sqlite3
from datetime import datetime, timedelta

import pytest
import pytz

WIB = pytz.timezone("Asia/Jakarta")


@pytest.fixture()
def reports_db(tmp_path, monkeypatch):
    """Isolated DB (paper_trades + premover_auto_log) wired into
    scheduler.reports, with send_telegram captured instead of sent and
    the holiday guard bypassed so tests aren't calendar-dependent."""
    import paper_trade as pt
    import scheduler.reports as reports

    db = str(tmp_path / "reports.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    monkeypatch.setattr(reports, "DB_PATH", db)

    sent = []
    monkeypatch.setattr(reports, "send_telegram", lambda msg: sent.append(msg))
    monkeypatch.setattr(reports, "_holiday_skip", lambda name: False)
    return db, sent


def _insert_trade(db, ticker, entry_date, status="OPEN", pnl_rp=None):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO paper_trades (ticker, entry_date, entry_price, status, pnl_rp) "
        "VALUES (?,?,?,?,?)",
        (ticker, entry_date, 1000.0, status, pnl_rp),
    )
    conn.commit()
    conn.close()


def _insert_log(db, ticker, detected_at, mode="enforce", would_trade=1):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO premover_auto_log "
        "(ticker, detected_at, pattern_type, score, mode, would_trade, skip_reason, logged_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (ticker, detected_at, "REVERSAL_BREAKOUT", 55, mode, would_trade, None, detected_at),
    )
    conn.commit()
    conn.close()


def test_includes_enforce_mode_auto_trade(reports_db):
    db, sent = reports_db
    yesterday = (datetime.now(WIB) - timedelta(days=1)).strftime("%Y-%m-%d")
    _insert_trade(db, "BRPT", yesterday)
    _insert_log(db, "BRPT", yesterday, mode="enforce", would_trade=1)

    import scheduler.reports as reports
    reports.auto_trade_status_report()

    assert len(sent) == 1
    assert "BRPT" in sent[0]


def test_excludes_manual_trade_with_no_matching_log_row(reports_db):
    """DEBT-001: a manual/other-strategy paper_trades row must not be
    reported under the 'Auto-Trade Status' header just for sharing the
    table with genuinely auto-traded rows."""
    db, sent = reports_db
    yesterday = (datetime.now(WIB) - timedelta(days=1)).strftime("%Y-%m-%d")
    _insert_trade(db, "MANUAL1", yesterday)  # no premover_auto_log row at all

    import scheduler.reports as reports
    reports.auto_trade_status_report()

    assert len(sent) == 1
    assert "MANUAL1" not in sent[0]
    assert "No auto-trades" in sent[0]


def test_excludes_shadow_mode_log_entry(reports_db):
    """A shadow-mode evaluation never opened a real trade; a paper_trades
    row for the same ticker/date via another path must not be attributed
    to auto-trading just because a shadow log row shares ticker+date."""
    db, sent = reports_db
    yesterday = (datetime.now(WIB) - timedelta(days=1)).strftime("%Y-%m-%d")
    _insert_trade(db, "SHADOW1", yesterday)
    _insert_log(db, "SHADOW1", yesterday, mode="shadow", would_trade=1)

    import scheduler.reports as reports
    reports.auto_trade_status_report()

    assert "SHADOW1" not in sent[0]


def test_excludes_would_trade_false_log_entry(reports_db):
    """An evaluation that was blocked (would_trade=0) never opened a
    trade either, even in enforce mode."""
    db, sent = reports_db
    yesterday = (datetime.now(WIB) - timedelta(days=1)).strftime("%Y-%m-%d")
    _insert_trade(db, "BLOCKED1", yesterday)
    _insert_log(db, "BLOCKED1", yesterday, mode="enforce", would_trade=0)

    import scheduler.reports as reports
    reports.auto_trade_status_report()

    assert "BLOCKED1" not in sent[0]


def test_yesterday_cutoff_uses_wib_not_naive_now(reports_db, monkeypatch):
    """DEBT-002 regression: freeze WIB-now and naive-now to represent the
    same instant but different calendar dates (as a UTC-clocked process
    would produce), and confirm the query cutoff follows WIB.

    A trade dated two days before WIB-now must be excluded under the
    fixed (WIB) cutoff. The pre-fix naive cutoff would have computed one
    calendar day earlier and incorrectly included it."""
    db, sent = reports_db
    frozen_wib_now = WIB.localize(datetime(2026, 7, 30, 1, 0, 0))
    frozen_naive_now = datetime(2026, 7, 29, 18, 0, 0)  # same instant, naive/UTC-style

    import scheduler.reports as reports

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_wib_now if tz is not None else frozen_naive_now

    monkeypatch.setattr(reports, "datetime", _FrozenDatetime)

    # WIB-correct cutoff is 2026-07-29 (frozen_wib_now - 1 day); a trade
    # dated 2026-07-28 is therefore two days old and must be excluded.
    _insert_trade(db, "TOOOLD", "2026-07-28")
    _insert_log(db, "TOOOLD", "2026-07-28", mode="enforce", would_trade=1)

    reports.auto_trade_status_report()

    assert "TOOOLD" not in sent[0]
    assert "No auto-trades" in sent[0]
