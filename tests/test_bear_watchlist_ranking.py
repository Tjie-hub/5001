"""Phase 2.2 — bear watchlist agent ranking digest.

Tests for rank_bear_watchlist_and_notify():
- Sorted by confidence descending
- Skipped when watchlist is empty / firm disabled / all vetoed
- Ranking is LOGGED, never sent via Telegram (log-only by design since the
  2026-06-16 lean-notification audit, commit 89baa33).
"""
import logging
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

import scheduler.scanner  # noqa: F401 — pre-load to keep in sys.modules across patch.dict


def _mock_firm_module(decisions):
    m = MagicMock()
    m.evaluate_staged = MagicMock(return_value=decisions)
    return m


def _mock_config_module(is_active=True):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    return m


@pytest.fixture
def isolated_db(tmp_path):
    """Temp DB with an empty agent_decisions table, wired into scanner.DB_PATH.

    The ranking fn queries agent_decisions to skip already-approved tickers;
    without this the test would depend on the ambient (gitignored) live DB and
    break in CI. Empty table → no tickers pre-approved → all are ranked.
    """
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE agent_decisions "
        "(ticker TEXT, strategy TEXT, decision TEXT, scan_time TEXT)"
    )
    conn.commit()
    conn.close()
    with patch.object(scheduler.scanner, "DB_PATH", str(db)):
        yield str(db)


def _call_ranking(tickers, mock_firm, mock_cfg, caplog):
    """Run the ranking; return the list of "(no alert)" ranking log messages.

    Asserts the log-only contract: send_telegram is never called.
    """
    sent_messages = []
    # Patch the package attributes too (the lazy ``from engine.agent_firm import
    # firm`` reads those), so the mock holds even after the real submodules are
    # imported by an earlier test in the same session. create=True because the
    # package only gains ``firm``/``config`` attrs once a submodule is imported.
    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm, create=True), \
         patch.object(_pkg, "config", mock_cfg, create=True), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm":   mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }), patch("scheduler.scanner.send_telegram", side_effect=sent_messages.append):
        from scheduler.scanner import rank_bear_watchlist_and_notify
        with caplog.at_level(logging.INFO):
            rank_bear_watchlist_and_notify(tickers, "2026-06-05", "10:00")
    # Log-only by design: this ranking must never fire a Telegram alert.
    assert sent_messages == [], "bear watchlist ranking must not send Telegram"
    return [r.message for r in caplog.records if "(no alert)" in r.message]


def test_ranking_skipped_when_no_tickers(isolated_db, caplog):
    """No ranking logged when watchlist is empty."""
    logs = _call_ranking([], _mock_firm_module([]), _mock_config_module(), caplog)
    assert logs == []


def test_ranking_skipped_when_firm_disabled(isolated_db, caplog):
    """No ranking logged when agent firm is inactive."""
    decisions = [MagicMock(ticker="BBCA", decision="approve", confidence=0.8, rationale="strong")]
    logs = _call_ranking(["BBCA"], _mock_firm_module(decisions), _mock_config_module(is_active=False), caplog)
    assert logs == []


def test_ranking_log_contains_tickers(isolated_db, caplog):
    """Logged ranking mentions each approved ticker."""
    decisions = [
        MagicMock(ticker="BBCA", decision="approve", confidence=0.82, rationale="support holding"),
        MagicMock(ticker="BBRI", decision="approve", confidence=0.71, rationale="accumulation signal"),
    ]
    logs = _call_ranking(["BBCA", "BBRI"], _mock_firm_module(decisions), _mock_config_module(), caplog)
    assert len(logs) == 1
    msg = logs[0]
    assert "BBCA" in msg
    assert "BBRI" in msg


def test_ranking_sorted_by_confidence_descending(isolated_db, caplog):
    """Tickers ranked highest confidence first in the logged ranking."""
    decisions = [
        MagicMock(ticker="MDKA", decision="approve", confidence=0.55, rationale="weak"),
        MagicMock(ticker="BBCA", decision="approve", confidence=0.90, rationale="strong"),
        MagicMock(ticker="AMMN", decision="approve", confidence=0.72, rationale="moderate"),
    ]
    logs = _call_ranking(
        ["MDKA", "BBCA", "AMMN"],
        _mock_firm_module(decisions),
        _mock_config_module(),
        caplog,
    )
    assert len(logs) == 1
    msg = logs[0]
    bbca_pos  = msg.index("BBCA")
    ammn_pos  = msg.index("AMMN")
    mdka_pos  = msg.index("MDKA")
    assert bbca_pos < ammn_pos < mdka_pos, "BBCA(0.90) must appear before AMMN(0.72) before MDKA(0.55)"


def test_ranking_excludes_vetoed_tickers(isolated_db, caplog):
    """Vetoed tickers are not included in the ranked digest."""
    decisions = [
        MagicMock(ticker="BBCA", decision="approve", confidence=0.80, rationale="ok"),
        MagicMock(ticker="MDKA", decision="veto",    confidence=0.30, rationale="risky"),
    ]
    logs = _call_ranking(
        ["BBCA", "MDKA"],
        _mock_firm_module(decisions),
        _mock_config_module(),
        caplog,
    )
    assert len(logs) == 1
    assert "BBCA" in logs[0]
    assert "MDKA" not in logs[0]


def test_ranking_no_message_when_all_vetoed(isolated_db, caplog):
    """No ranking logged if all watchlist tickers are vetoed."""
    decisions = [
        MagicMock(ticker="BBCA", decision="veto", confidence=0.2, rationale="bad"),
    ]
    logs = _call_ranking(["BBCA"], _mock_firm_module(decisions), _mock_config_module(), caplog)
    assert logs == []
