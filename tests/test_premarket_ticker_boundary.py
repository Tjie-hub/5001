"""Strict 2-invocations-per-trading-day contract — premarket half (Run 2).

Proves, against a real temp SQLite DB (engine.agent_firm_daily's actual tables,
not mocked), the acceptance criteria specific to run_premarket_firm_scan():
  - ticker isolation: only the post-close (Run 1) selected ticker set ever
    reaches the LLM, even if the revision engine's own survivors are wider
  - if Run 1 selected nothing for today, Run 2 makes no LLM call at all
  - duplicate prevention: a second invocation for the same session never
    re-bills the firm
  - plan-preservation: when the revision engine found no material change for
    any selected ticker, plan_changed is recorded False; a material change
    records it True

The heavier deterministic pipeline (base-plan lookup, revision engine,
liquidity filter) is stubbed exactly at its own module boundaries — this test
is about the NEW ticker-boundary/guard wiring added to run_premarket_firm_scan,
not about re-testing engine.premarket_revision or engine.liquidity themselves.
"""
import sqlite3
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import scheduler.jobs as jobs_mod
import engine.agent_firm_daily as afd
from engine.premarket_revision import RevisionDecision
from engine.watchlist_ledger import ACTION_RETAIN, ACTION_UPGRADE, BASE_PLAN

WIB = jobs_mod.WIB
TODAY = datetime.now(WIB).strftime("%Y-%m-%d")


def _base_row(ticker, conviction=70.0):
    return {"ticker": ticker, "close": 1000, "conviction": conviction,
            "sources": ["R"], "confluence": True, "strategy_fn": "reversal"}


def _run(monkeypatch, tmp_path, *, base_rows, revise_decisions, daily_plan_tickers,
        firm_side_effect):
    """Run scheduler.jobs.run_premarket_firm_scan() against a real temp DB with the
    heavy deterministic pipeline (base plan / revision engine / liquidity) stubbed,
    and the firm mocked. Returns (db_path, mock_firm) for post-hoc DB assertions.
    """
    db = str(tmp_path / "wf.db")
    monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
    monkeypatch.setattr(jobs_mod, "DB_PATH", db)
    monkeypatch.setattr(jobs_mod, "get_market_risk_for_circuit_breaker", lambda: None)
    monkeypatch.setattr("engine.watchlist_ledger.base_plan",
                        lambda conn, before, strategy: {
                            "status": BASE_PLAN, "date": TODAY, "rows": base_rows,
                            "revision": 1,
                        })
    monkeypatch.setattr("engine.watchlist_ledger.record_revisions", lambda *a, **k: None)
    monkeypatch.setattr("engine.edge_enrich.market_regime", lambda conn: "BULL")
    monkeypatch.setattr("engine.premarket_revision.revise",
                        lambda conn, rows, **k: revise_decisions)
    monkeypatch.setattr("engine.premarket_revision.apply",
                        lambda decisions: [d.base_row for d in decisions
                                           if d.action != "REMOVE" and d.base_row])
    monkeypatch.setattr("engine.liquidity.select_top_liquid_longs",
                        lambda survivors, conn, date_str, top_n: survivors)
    monkeypatch.setattr(jobs_mod, "send_telegram", lambda msg, **kw: None)

    if daily_plan_tickers is not None:
        conn = sqlite3.connect(db)
        afd.ensure_tables(conn)
        afd.persist_plan(
            conn, TODAY, [{"ticker": t} for t in daily_plan_tickers],
            [], source=afd.RUN_POST_CLOSE,
        )
        conn.close()

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
        jobs_mod.run_premarket_firm_scan()

    return db, mock_firm


def _decision(ticker, decision="approve", confidence=0.8, size_tier=None, providers_used=None):
    d = MagicMock(ticker=ticker, decision=decision, confidence=confidence,
                  size_tier=size_tier, rationale="ok")
    d.providers_used = providers_used or ["zai"]
    return d


def test_only_daily_selected_tickers_reach_the_firm(monkeypatch, tmp_path):
    """EOD survivors include a ticker outside the post-close selected set — it
    must never reach evaluate_staged()."""
    base_rows = [_base_row("BBCA"), _base_row("EXTRA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[0]),
        RevisionDecision("EXTRA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[1]),
    ]
    captured = []
    _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=lambda cands: captured.append(cands) or [_decision("BBCA")],
    )
    assert len(captured) == 1
    assert [c.ticker for c in captured[0]] == ["BBCA"]


def test_no_llm_call_when_post_close_selected_nothing(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[0]),
    ]
    captured = []
    _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=[],  # Run 1 selected nothing today
        firm_side_effect=lambda cands: captured.append(cands) or [],
    )
    assert captured == []


def test_duplicate_premarket_invocation_is_not_billed_twice(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[0]),
    ]
    call_count = [0]

    def _side_effect(cands):
        call_count[0] += 1
        return [_decision("BBCA")]

    db, _ = _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=_side_effect,
    )
    assert call_count[0] == 1

    # Clear the outer job-level dedup guard so this reaches the LLM guard again
    # (the realistic scenario: a manual/administrative retry of the job body).
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM _job_sentinel WHERE job='premarket_firm'")
    conn.commit()
    conn.close()

    _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=_side_effect,
    )
    assert call_count[0] == 1, "a second invocation for the same session must not re-bill the firm"


def test_plan_changed_false_when_all_selected_tickers_retained(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no material overnight change",
                         base_row=base_rows[0]),
    ]
    db, _ = _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=lambda cands: [_decision("BBCA")],
    )
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT plan_changed FROM agent_firm_daily_run WHERE run_type='premarket'"
    ).fetchone()
    conn.close()
    assert row[0] == 0


def test_plan_changed_true_when_a_selected_ticker_was_upgraded(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_UPGRADE, "flow", "foreign accumulation overnight",
                         base_row=base_rows[0]),
    ]
    db, _ = _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=lambda cands: [_decision("BBCA")],
    )
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT plan_changed FROM agent_firm_daily_run WHERE run_type='premarket'"
    ).fetchone()
    conn.close()
    assert row[0] == 1


# ── Provider hierarchy (2026-09-15): Claude primary, GLM-5.3 Flash fallback ──
# See tests/agent_firm/providers/test_provider_hierarchy.py for proof the
# router itself prefers Claude and falls over to GLM correctly; these prove
# whichever provider actually served the call is what gets recorded here.

def test_premarket_provider_recorded_as_claude_when_primary_succeeds(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[0]),
    ]
    db, _ = _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=lambda cands: [_decision("BBCA", providers_used=["claude"])],
    )
    conn = sqlite3.connect(db)
    provider = conn.execute(
        "SELECT provider FROM agent_firm_daily_run WHERE run_type='premarket'"
    ).fetchone()[0]
    conn.close()
    assert provider == "claude"


def test_premarket_provider_recorded_as_glm_after_claude_fallback(monkeypatch, tmp_path):
    base_rows = [_base_row("BBCA")]
    revise_decisions = [
        RevisionDecision("BBCA", ACTION_RETAIN, "ok", "no change", base_row=base_rows[0]),
    ]
    db, _ = _run(
        monkeypatch, tmp_path,
        base_rows=base_rows, revise_decisions=revise_decisions,
        daily_plan_tickers=["BBCA"],
        firm_side_effect=lambda cands: [_decision("BBCA", providers_used=["zai"])],
    )
    conn = sqlite3.connect(db)
    provider = conn.execute(
        "SELECT provider FROM agent_firm_daily_run WHERE run_type='premarket'"
    ).fetchone()[0]
    conn.close()
    assert provider == "zai"
