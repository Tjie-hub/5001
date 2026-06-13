"""Phase 2.2 — bear watchlist agent ranking digest.

Tests for rank_bear_watchlist_and_notify():
- Sorted by confidence descending
- Skipped when watchlist is empty
- Telegram message contains ranked tickers
"""
import sys
from unittest.mock import MagicMock, patch

import scheduler.scanner  # noqa: F401 — pre-load to keep in sys.modules across patch.dict


def _mock_firm_module(decisions):
    m = MagicMock()
    m.evaluate_staged = MagicMock(return_value=decisions)
    return m


def _mock_config_module(is_active=True):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    return m


def _call_ranking(tickers, mock_firm, mock_cfg):
    sent_messages = []
    # Patch the package attributes too (the lazy ``from engine.agent_firm import
    # firm`` reads those), so the mock holds even after the real submodules are
    # imported by an earlier test in the same session.
    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", mock_cfg), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm":   mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }), patch("scheduler.scanner.send_telegram", side_effect=sent_messages.append):
        from scheduler.scanner import rank_bear_watchlist_and_notify
        rank_bear_watchlist_and_notify(tickers, "2026-06-05", "10:00")
    return sent_messages


def test_ranking_skipped_when_no_tickers():
    """No Telegram sent when watchlist is empty."""
    sent = _call_ranking([], _mock_firm_module([]), _mock_config_module())
    assert sent == []


def test_ranking_skipped_when_firm_disabled():
    """No Telegram sent when agent firm is inactive."""
    decisions = [MagicMock(ticker="BBCA", decision="approve", confidence=0.8, rationale="strong")]
    sent = _call_ranking(["BBCA"], _mock_firm_module(decisions), _mock_config_module(is_active=False))
    assert sent == []


def test_ranking_telegram_message_contains_tickers():
    """Telegram message mentions each ranked ticker."""
    decisions = [
        MagicMock(ticker="BBCA", decision="approve", confidence=0.82, rationale="support holding"),
        MagicMock(ticker="BBRI", decision="approve", confidence=0.71, rationale="accumulation signal"),
    ]
    sent = _call_ranking(["BBCA", "BBRI"], _mock_firm_module(decisions), _mock_config_module())
    assert len(sent) == 1
    msg = sent[0]
    assert "BBCA" in msg
    assert "BBRI" in msg


def test_ranking_sorted_by_confidence_descending():
    """Tickers ranked highest confidence first in the message."""
    decisions = [
        MagicMock(ticker="MDKA", decision="approve", confidence=0.55, rationale="weak"),
        MagicMock(ticker="BBCA", decision="approve", confidence=0.90, rationale="strong"),
        MagicMock(ticker="AMMN", decision="approve", confidence=0.72, rationale="moderate"),
    ]
    sent = _call_ranking(
        ["MDKA", "BBCA", "AMMN"],
        _mock_firm_module(decisions),
        _mock_config_module(),
    )
    assert len(sent) == 1
    msg = sent[0]
    bbca_pos  = msg.index("BBCA")
    ammn_pos  = msg.index("AMMN")
    mdka_pos  = msg.index("MDKA")
    assert bbca_pos < ammn_pos < mdka_pos, "BBCA(0.90) must appear before AMMN(0.72) before MDKA(0.55)"


def test_ranking_excludes_vetoed_tickers():
    """Vetoed tickers are not included in the ranked digest."""
    decisions = [
        MagicMock(ticker="BBCA", decision="approve", confidence=0.80, rationale="ok"),
        MagicMock(ticker="MDKA", decision="veto",    confidence=0.30, rationale="risky"),
    ]
    sent = _call_ranking(
        ["BBCA", "MDKA"],
        _mock_firm_module(decisions),
        _mock_config_module(),
    )
    assert len(sent) == 1
    assert "BBCA" in sent[0]
    assert "MDKA" not in sent[0]


def test_ranking_no_message_when_all_vetoed():
    """No Telegram sent if all watchlist tickers are vetoed."""
    decisions = [
        MagicMock(ticker="BBCA", decision="veto", confidence=0.2, rationale="bad"),
    ]
    sent = _call_ranking(["BBCA"], _mock_firm_module(decisions), _mock_config_module())
    assert sent == []
