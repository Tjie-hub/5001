"""Tests for the premarket agent-firm shortlist message builder (08:35 WIB job).

Only the pure Telegram-message builder is exercised here — it imports nothing
beyond pydantic schemas, so it runs on the Windows .winvenv (no langgraph). The
firm wiring in run_premarket_firm_scan is covered by tests/agent_firm/*.
"""
from engine.agent_firm.schemas import AgentDecision
from scheduler.jobs import _build_premarket_firm_message


def _dec(ticker, decision, confidence=None, size_hint=None, rationale=None):
    return AgentDecision(
        ticker=ticker, strategy="premarket", scan_time="2026-06-22 08:35",
        quant_score=70.0, decision=decision, confidence=confidence,
        size_hint=size_hint, rationale=rationale,
    )


def _row(ticker, sources, strength=70.0, direction="long"):
    return {"ticker": ticker, "direction": direction, "strength": strength,
            "sources": sources, "confluence": len(sources) >= 2, "close": 1000,
            "detail": {}}


HEADER = "22/06 08:35"


def test_returns_string_with_header():
    msg = _build_premarket_firm_message([], [], HEADER)
    assert isinstance(msg, str)
    assert HEADER in msg


def test_approved_shown_with_conviction_and_source_tag():
    decisions = [_dec("BBRI", "approve", confidence=0.82, size_hint=1.5,
                      rationale="Reversal + foreign accumulation")]
    rows = [_row("BBRI", ["REVERSAL", "PREMOVER"])]
    msg = _build_premarket_firm_message(decisions, rows, HEADER)
    assert "BBRI" in msg
    assert "0.82" in msg
    assert "×1.50" in msg
    assert "[R+P]" in msg          # source first-letters
    assert "Reversal + foreign accumulation" in msg


def test_no_approved_longs_message():
    decisions = [_dec("ADRO", "veto")]
    msg = _build_premarket_firm_message(decisions, [_row("ADRO", ["PREMOVER"])], HEADER)
    assert "No firm-approved longs" in msg


def test_vetoed_listed():
    decisions = [_dec("GOTO", "veto"), _dec("BBCA", "approve", confidence=0.6)]
    rows = [_row("GOTO", ["PREMOVER"]), _row("BBCA", ["REVERSAL"])]
    msg = _build_premarket_firm_message(decisions, rows, HEADER)
    assert "Vetoed (1)" in msg
    assert "GOTO" in msg


def test_passthrough_when_firm_degraded_or_off():
    decisions = [_dec("TLKM", "bypassed"), _dec("ASII", "degraded")]
    rows = [_row("TLKM", ["REVERSAL"]), _row("ASII", ["BEAR_DIP"])]
    msg = _build_premarket_firm_message(decisions, rows, HEADER)
    assert "Passed through" in msg
    assert "TLKM" in msg and "ASII" in msg


def test_approved_sorted_by_confidence_desc():
    decisions = [
        _dec("LOWC", "approve", confidence=0.50),
        _dec("HIGH", "approve", confidence=0.95),
    ]
    rows = [_row("LOWC", ["REVERSAL"]), _row("HIGH", ["REVERSAL"])]
    msg = _build_premarket_firm_message(decisions, rows, HEADER)
    assert msg.index("HIGH") < msg.index("LOWC")


def test_rationale_truncated_to_140_chars():
    long_rationale = "x" * 300
    decisions = [_dec("BMRI", "approve", confidence=0.7, rationale=long_rationale)]
    rows = [_row("BMRI", ["REVERSAL"])]
    msg = _build_premarket_firm_message(decisions, rows, HEADER)
    assert "x" * 140 in msg
    assert "x" * 141 not in msg


def test_premarket_message_includes_provider_line():
    class _D:
        def __init__(self, ticker, decision, confidence, providers_used):
            self.ticker = ticker
            self.decision = decision
            self.confidence = confidence
            self.rationale = None
            self.size_hint = None
            self.providers_used = providers_used

    from scheduler.jobs import _build_premarket_firm_message
    decisions = [_D("BBRI", "approve", 0.8, ["claude"])]
    msg = _build_premarket_firm_message(decisions, [], "08/07 08:35")
    assert "Firm Provider:\nClaude" in msg


def test_premarket_message_omits_provider_line_when_no_providers_used():
    class _D:
        def __init__(self, ticker, decision):
            self.ticker = ticker
            self.decision = decision
            self.confidence = None
            self.rationale = None
            self.providers_used = []

    from scheduler.jobs import _build_premarket_firm_message
    decisions = [_D("BBRI", "bypassed")]
    msg = _build_premarket_firm_message(decisions, [], "08/07 08:35")
    assert "Firm Provider" not in msg
