"""Strict 2-invocations-per-trading-day contract — post-close half (Run 1).

Proves, against a real temp SQLite DB (engine.agent_firm_daily's actual
tables, not mocked):
  - selection is capped at MAX_DAILY_TICKERS (3), not the old 8
  - a successful run persists the plan under the NEXT trading session's date
  - a second invocation for the same session never re-bills the firm
  - a holiday never reaches the LLM-invocation guard at all
"""
import sqlite3
from datetime import date, datetime
from unittest.mock import MagicMock, patch
import sys

import scheduler.jobs as jobs_mod
import engine.agent_firm_daily as afd

WIB = jobs_mod.WIB
TODAY = datetime.now(WIB).strftime("%Y-%m-%d")


def _cand(ticker, conviction):
    return {"ticker": ticker, "conviction": conviction, "smart_money": "YES",
            "sources": ["R"], "confluence": 1, "vol_ratio": 1.5, "net_value": 1.0}


def _decision(ticker, decision="approve", confidence=0.8, providers_used=None):
    d = MagicMock(ticker=ticker, decision=decision, confidence=confidence,
                  size_hint=None, size_tier=None, rationale="ok")
    d.providers_used = providers_used or ["zai"]
    return d


def _run(monkeypatch, tmp_path, *, cands, firm_side_effect):
    db = str(tmp_path / "wf.db")
    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "DB_PATH", db)
    monkeypatch.setattr("engine.trade_plan.gather_long_candidates",
                        lambda conn, date_str: cands)
    monkeypatch.setattr("engine.trade_plan.get_regime",
                        lambda conn, date_str: ("BULL", 72.0))
    monkeypatch.setattr("engine.trade_plan.get_vpin_gate", lambda conn, date_str: None)
    monkeypatch.setattr("config.edge_mode", lambda: "off")
    monkeypatch.setattr(jobs_mod, "send_telegram", lambda msg: None)

    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(side_effect=firm_side_effect)
    mock_cfg = MagicMock()
    mock_cfg.is_active = MagicMock(return_value=True)
    mock_cfg.get_enforce = MagicMock(return_value=False)

    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm, create=True), \
         patch.object(_pkg, "config", mock_cfg, create=True), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm": mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }):
        jobs_mod.run_eod_trade_plan()

    return db, mock_firm


def test_selection_capped_at_three_not_eight(monkeypatch, tmp_path):
    cands = [_cand(f"TK{i}", float(i)) for i in range(6)]
    captured = []
    _run(monkeypatch, tmp_path, cands=cands,
        firm_side_effect=lambda c: captured.append(c) or [_decision(x.ticker) for x in c])
    assert len(captured) == 1
    assert len(captured[0]) == 3


def test_plan_persisted_under_next_trading_session(monkeypatch, tmp_path):
    cands = [_cand("BBCA", 90.0)]
    db, _ = _run(monkeypatch, tmp_path, cands=cands,
                firm_side_effect=lambda c: [_decision("BBCA")])

    expected_session = afd.next_trading_session(
        datetime.strptime(TODAY, "%Y-%m-%d").date()).isoformat()
    conn = sqlite3.connect(db)
    plan = afd.load_plan(conn, expected_session)
    run_row = conn.execute(
        "SELECT status, run_type, attempt FROM agent_firm_daily_run"
    ).fetchone()
    conn.close()

    assert [p["ticker"] for p in plan] == ["BBCA"]
    assert run_row == ("success", "post_close", 1)


def test_duplicate_post_close_invocation_is_not_billed_twice(monkeypatch, tmp_path):
    cands = [_cand("BBCA", 90.0)]
    call_count = [0]

    def _side_effect(c):
        call_count[0] += 1
        return [_decision("BBCA")]

    db, _ = _run(monkeypatch, tmp_path, cands=cands, firm_side_effect=_side_effect)
    assert call_count[0] == 1

    # Clear the outer job-level dedup guard so this reaches the LLM guard again
    # (the realistic scenario: a manual/administrative retry of the job body).
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM _job_sentinel WHERE job='eod_trade_plan'")
    conn.commit()
    conn.close()

    _run(monkeypatch, tmp_path, cands=cands, firm_side_effect=_side_effect)
    assert call_count[0] == 1, "a second invocation for the same session must not re-bill the firm"


def test_failed_invocation_allows_retry(monkeypatch, tmp_path):
    cands = [_cand("BBCA", 90.0)]
    attempts = [0]

    def _side_effect(c):
        attempts[0] += 1
        if attempts[0] == 1:
            raise RuntimeError("provider timeout")
        return [_decision("BBCA")]

    db, _ = _run(monkeypatch, tmp_path, cands=cands, firm_side_effect=_side_effect)
    assert attempts[0] == 1

    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM _job_sentinel WHERE job='eod_trade_plan'")
    conn.commit()
    conn.close()

    _run(monkeypatch, tmp_path, cands=cands, firm_side_effect=_side_effect)
    assert attempts[0] == 2, "a genuinely failed invocation must allow a retry"

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT status, attempt FROM agent_firm_daily_run ORDER BY attempt"
    ).fetchall()
    conn.close()
    assert rows == [("failed", 1), ("success", 2)]


def test_holiday_never_reaches_the_llm_guard(monkeypatch, tmp_path):
    db = str(tmp_path / "wf.db")
    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: True)
    monkeypatch.setattr(jobs_mod, "DB_PATH", db)

    def _must_not_run(*a, **k):
        raise AssertionError("gather_long_candidates ran despite the holiday guard")

    monkeypatch.setattr("engine.trade_plan.gather_long_candidates", _must_not_run)

    jobs_mod.run_eod_trade_plan()  # must not raise, must not touch agent_firm_daily at all

    import os
    assert not os.path.exists(db), (
        "a holiday run must never even open the DB connection agent_firm_daily needs"
    )


# ── Provider hierarchy (2026-09-15): Claude primary, GLM-5.3 Flash fallback ──
# The firm's provider choice (engine.agent_firm.providers.router) is mocked
# away entirely by _run()'s firm_side_effect — these tests only prove that
# whichever provider the router actually used gets recorded verbatim in
# agent_firm_daily_run.provider, and that the ticker set reaching the firm is
# identical regardless of which provider serves it (see
# tests/agent_firm/providers/test_provider_hierarchy.py for proof that the
# router itself always prefers Claude and falls over to GLM correctly).

def test_provider_recorded_as_claude_when_primary_succeeds(monkeypatch, tmp_path):
    cands = [_cand("BBCA", 90.0)]
    db, _ = _run(monkeypatch, tmp_path, cands=cands,
                firm_side_effect=lambda c: [_decision("BBCA", providers_used=["claude"])])
    conn = sqlite3.connect(db)
    provider = conn.execute("SELECT provider FROM agent_firm_daily_run").fetchone()[0]
    conn.close()
    assert provider == "claude"


def test_provider_recorded_as_glm_after_claude_fallback(monkeypatch, tmp_path):
    cands = [_cand("BBCA", 90.0)]
    db, _ = _run(monkeypatch, tmp_path, cands=cands,
                firm_side_effect=lambda c: [_decision("BBCA", providers_used=["zai"])])
    conn = sqlite3.connect(db)
    provider = conn.execute("SELECT provider FROM agent_firm_daily_run").fetchone()[0]
    conn.close()
    assert provider == "zai"


def test_same_ticker_set_reaches_the_firm_regardless_of_which_provider_serves(monkeypatch, tmp_path):
    """GLM must never see a different (or independently selected) ticker set
    than Claude would have -- both are just legs of the same router call, so
    the candidate list handed to evaluate_staged() is identical either way.
    Runs the SAME job body twice (once "served by claude", once "served by
    glm after fallback") and asserts the captured ticker set is unchanged."""
    cands = [_cand("BBCA", 90.0), _cand("BBRI", 80.0)]
    captured = []

    def _make_side_effect(provider_name):
        def _side_effect(c):
            captured.append(tuple(sorted(x.ticker for x in c)))
            return [_decision(x.ticker, providers_used=[provider_name]) for x in c]
        return _side_effect

    claude_dir = tmp_path / "claude_run"
    glm_dir = tmp_path / "glm_run"
    claude_dir.mkdir()
    glm_dir.mkdir()

    _run(monkeypatch, claude_dir, cands=cands, firm_side_effect=_make_side_effect("claude"))
    _run(monkeypatch, glm_dir, cands=cands, firm_side_effect=_make_side_effect("zai"))

    assert len(captured) == 2
    assert captured[0] == captured[1] == ("BBCA", "BBRI")
