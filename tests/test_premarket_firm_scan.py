"""Tests for the premarket agent-firm shortlist message builder (08:35 WIB job).

Most of this file exercises the pure Telegram-message builder — it imports
nothing beyond pydantic schemas, so it runs on the Windows .winvenv (no
langgraph). The firm wiring in run_premarket_firm_scan is covered by
tests/agent_firm/*, except for the dedup-guard lock-handling test below,
which only needs scheduler.jobs.
"""
import sqlite3

from engine.agent_firm.schemas import AgentDecision
from engine.trade_plan import diff_watchlist, record_snapshot
from scheduler.jobs import (
    _build_premarket_firm_message,
    _premarket_approved_and_lookup,
    _premarket_factor_note,
    _premarket_ranked_for_snapshot,
)


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


class _LockedSentinelConn:
    """Fake db_connect() return whose dedup-guard INSERT always finds the DB locked.

    Mirrors a real write-contention window (e.g. run_news_fetch holding an open
    write transaction) outlasting the connection's busy_timeout.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("INSERT"):
            raise sqlite3.OperationalError("database is locked")
        return None


class TestPremarketSummaryHeader:
    """Daily-Summary lines are optional/omitted-when-None, so old call sites
    (and the tests above) keep getting the same message shape."""

    def test_summary_lines_omitted_when_not_given(self):
        msg = _build_premarket_firm_message([], [], HEADER)
        assert "Regime:" not in msg and "Risk:" not in msg and "Candidates:" not in msg

    def test_summary_lines_rendered_when_given(self):
        decisions = [_dec("BBRI", "approve", confidence=0.82)]
        rows = [_row("BBRI", ["REVERSAL"])]
        msg = _build_premarket_firm_message(
            decisions, rows, HEADER, regime="SIDEWAYS",
            risk={"tier": "YELLOW", "score": 42.0}, watchlist_total=18)
        assert "Regime: <b>SIDEWAYS</b>" in msg
        assert "Risk: <b>YELLOW</b> (42)" in msg
        assert "Candidates: 18 unified → 1 evaluated" in msg
        assert "Highest conviction: <b>BBRI</b> (0.82)" in msg

    def test_no_highest_conviction_line_when_nothing_approved(self):
        msg = _build_premarket_firm_message([_dec("ADRO", "veto")], [_row("ADRO", ["PREMOVER"])], HEADER)
        assert "Highest conviction" not in msg

    def test_header_uses_premarket_summary_title(self):
        msg = _build_premarket_firm_message([], [], HEADER)
        assert "PREMARKET SUMMARY" in msg
        assert "TOP CONVICTIONS" not in msg   # nothing approved -> no such section


class TestPremarketRankedForSnapshot:
    """Pure helpers shared by the message and the snapshot writer."""

    def test_approved_and_lookup_sorts_by_confidence_desc(self):
        decisions = [_dec("LOWC", "approve", confidence=0.50),
                    _dec("HIGH", "approve", confidence=0.95),
                    _dec("VETO", "veto", confidence=0.99)]
        rows = [_row("LOWC", ["R"]), _row("HIGH", ["R"]), _row("VETO", ["R"])]
        approved, by_ticker = _premarket_approved_and_lookup(decisions, rows)
        assert [d.ticker for d in approved] == ["HIGH", "LOWC"]
        assert set(by_ticker) == {"LOWC", "HIGH", "VETO"}

    def test_ranked_for_snapshot_carries_confidence_conviction_sources(self):
        decisions = [_dec("BBRI", "approve", confidence=0.82)]
        rows = [_row("BBRI", ["REVERSAL", "PREMOVER"], strength=61.0)]
        approved, by_ticker = _premarket_approved_and_lookup(decisions, rows)
        ranked = _premarket_ranked_for_snapshot(approved, by_ticker)
        assert ranked == [{"ticker": "BBRI", "confidence": 0.82, "conviction": 61.0,
                          "confluence": True, "sources": ["REVERSAL", "PREMOVER"]}]

    def test_ranked_for_snapshot_empty_when_nothing_approved(self):
        approved, by_ticker = _premarket_approved_and_lookup([_dec("X", "veto")], [_row("X", ["R"])])
        assert _premarket_ranked_for_snapshot(approved, by_ticker) == []


class TestPremarketFactorNote:
    def test_gained_source_is_reported(self):
        assert _premarket_factor_note(["PREMOVER"], ["PREMOVER", "REVERSAL"]) == "+REVERSAL"

    def test_lost_source_is_reported(self):
        assert _premarket_factor_note(["PREMOVER", "REVERSAL"], ["PREMOVER"]) == "-REVERSAL"

    def test_no_change_is_empty_string(self):
        assert _premarket_factor_note(["REVERSAL"], ["REVERSAL"]) == ""

    def test_none_sources_do_not_crash(self):
        assert _premarket_factor_note(None, None) == ""


class TestPremarketLifecycleReporting:
    """Full Added/Removed/Upgraded/Downgraded/Stable coverage via the real
    diff_watchlist()/record_snapshot() infra (strategy='premarket'), exactly
    per the Phase 2 validation checklist: no changes, additions, removals,
    upgrades, downgrades, empty shortlist, first execution.
    """

    DATE1, DATE2 = "2026-07-27", "2026-07-28"

    def _db(self):
        return sqlite3.connect(":memory:")

    def _snap(self, ticker, confidence, conviction, sources):
        return {"ticker": ticker, "confidence": confidence, "conviction": conviction,
               "confluence": len(sources) >= 2, "sources": sources}

    def test_first_execution_has_no_prior_snapshot(self):
        c = self._db()
        ranked = [self._snap("BBRI", 0.80, 70.0, ["REVERSAL"])]
        diff = diff_watchlist(c, self.DATE1, "premarket", ranked)
        assert diff is None
        # message must render gracefully with diff=None (no NEW/REMOVED sections)
        decisions = [_dec("BBRI", "approve", confidence=0.80)]
        msg = _build_premarket_firm_message(decisions, [_row("BBRI", ["REVERSAL"])], HEADER, diff=diff)
        assert "NEW" not in msg and "REMOVED" not in msg and "UPGRADED" not in msg

    def test_no_changes_renders_no_lifecycle_sections(self):
        c = self._db()
        same = [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"])]
        record_snapshot(c, self.DATE1, "premarket", same)
        diff = diff_watchlist(c, self.DATE2, "premarket", same)
        decisions = [_dec("BBRI", "approve", confidence=0.60)]
        msg = _build_premarket_firm_message(decisions, [_row("BBRI", ["REVERSAL"])], HEADER, diff=diff)
        assert "📈 NEW" not in msg and "📉 REMOVED" not in msg
        assert "⬆ UPGRADED" not in msg and "⬇ DOWNGRADED" not in msg

    def test_addition_is_reported(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket", [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"])])
        today = [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"]),
                self._snap("GOTO", 0.55, 60.0, ["PREMOVER"])]
        diff = diff_watchlist(c, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", 0.60), _dec("GOTO", "approve", 0.55)]
        rows = [_row("BBRI", ["REVERSAL"]), _row("GOTO", ["PREMOVER"])]
        msg = _build_premarket_firm_message(decisions, rows, HEADER, diff=diff)
        assert "📈 NEW" in msg and "GOTO" in msg.split("📈 NEW")[1]

    def test_removal_is_reported(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket",
                        [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"]),
                         self._snap("GOTO", 0.55, 60.0, ["PREMOVER"])])
        today = [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"])]   # GOTO dropped
        diff = diff_watchlist(c, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", 0.60)]
        msg = _build_premarket_firm_message(decisions, [_row("BBRI", ["REVERSAL"])], HEADER, diff=diff)
        assert "📉 REMOVED" in msg and "GOTO" in msg.split("📉 REMOVED")[1]

    def test_upgrade_is_reported_with_rationale_and_factor_note(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket", [self._snap("BBRI", 0.55, 70.0, ["PREMOVER"])])
        today = [self._snap("BBRI", 0.75, 70.0, ["PREMOVER", "REVERSAL"])]   # confidence + new source
        diff = diff_watchlist(c, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", confidence=0.75, rationale="Broker flow confirms reversal")]
        rows = [_row("BBRI", ["PREMOVER", "REVERSAL"])]
        msg = _build_premarket_firm_message(decisions, rows, HEADER, diff=diff)
        assert "⬆ UPGRADED" in msg
        section = msg.split("⬆ UPGRADED")[1]
        assert "BBRI" in section
        assert "conf 0.55→0.75 (+0.20)" in section
        assert "+REVERSAL" in section
        assert "Broker flow confirms reversal" in section

    def test_downgrade_is_reported(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket", [self._snap("BBRI", 0.80, 70.0, ["REVERSAL"])])
        today = [self._snap("BBRI", 0.55, 70.0, ["REVERSAL"])]
        diff = diff_watchlist(c, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", confidence=0.55)]
        msg = _build_premarket_firm_message(decisions, [_row("BBRI", ["REVERSAL"])], HEADER, diff=diff)
        assert "⬇ DOWNGRADED" in msg
        assert "conf 0.80→0.55 (-0.25)" in msg.split("⬇ DOWNGRADED")[1]

    def test_stable_high_conviction_is_optionally_reported(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket", [self._snap("BBRI", 0.75, 70.0, ["REVERSAL"])])
        today = [self._snap("BBRI", 0.76, 70.0, ["REVERSAL"])]   # tiny delta -> unchanged, high conviction
        diff = diff_watchlist(c, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", confidence=0.76)]
        msg = _build_premarket_firm_message(decisions, [_row("BBRI", ["REVERSAL"])], HEADER, diff=diff)
        assert "🟢 STABLE" in msg and "BBRI" in msg.split("🟢 STABLE")[1]

    def test_empty_shortlist_with_prior_snapshot_reports_all_removed(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "premarket",
                        [self._snap("BBRI", 0.60, 70.0, ["REVERSAL"]),
                         self._snap("GOTO", 0.55, 60.0, ["PREMOVER"])])
        diff = diff_watchlist(c, self.DATE2, "premarket", [])   # nothing approved today
        msg = _build_premarket_firm_message([], [], HEADER, diff=diff)
        assert "No firm-approved longs" in msg
        assert "📉 REMOVED" in msg
        section = msg.split("📉 REMOVED")[1]
        assert "BBRI" in section and "GOTO" in section

    def test_premarket_and_eod_snapshots_are_isolated(self):
        c = self._db()
        record_snapshot(c, self.DATE1, "eod", [self._snap("BBRI", 0.60, 70.0, ["R"])])
        # no prior 'premarket' snapshot exists even though 'eod' has one for the same date
        assert diff_watchlist(c, self.DATE2, "premarket",
                              [self._snap("BBRI", 0.60, 70.0, ["R"])]) is None

    def test_deterministic_output_for_same_inputs(self):
        c1, c2 = self._db(), self._db()
        prior = [self._snap("BBRI", 0.55, 70.0, ["PREMOVER"])]
        today = [self._snap("BBRI", 0.80, 70.0, ["PREMOVER", "REVERSAL"])]
        record_snapshot(c1, self.DATE1, "premarket", prior)
        record_snapshot(c2, self.DATE1, "premarket", prior)
        diff1 = diff_watchlist(c1, self.DATE2, "premarket", today)
        diff2 = diff_watchlist(c2, self.DATE2, "premarket", today)
        decisions = [_dec("BBRI", "approve", confidence=0.80, rationale="Flow accelerating")]
        rows = [_row("BBRI", ["PREMOVER", "REVERSAL"])]
        msg1 = _build_premarket_firm_message(decisions, rows, HEADER, diff=diff1)
        msg2 = _build_premarket_firm_message(decisions, rows, HEADER, diff=diff2)
        assert msg1 == msg2


def test_run_premarket_firm_scan_fails_open_on_sentinel_db_lock(monkeypatch, caplog):
    """A locked DB on the dedup-guard insert must degrade the job, not crash it.

    Reproduces the 2026-07-24 08:35:30 production crash: run_premarket_firm_scan
    let sqlite3.OperationalError propagate out of the scheduler job instead of
    failing open like the bear-watchlist code path a few lines away.
    """
    import scheduler.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "db_connect", lambda *a, **k: _LockedSentinelConn())

    def _must_not_run(*a, **k):
        raise AssertionError(
            "build_unified_watchlist ran despite the dedup guard being locked out"
        )

    monkeypatch.setattr("engine.unified_watchlist.build_unified_watchlist", _must_not_run)

    with caplog.at_level("WARNING"):
        jobs_mod.run_premarket_firm_scan()  # must not raise

    assert any("database is locked" in r.message for r in caplog.records)
