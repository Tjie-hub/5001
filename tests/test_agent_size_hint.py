"""Phase 2.1 — agent conviction sizing.

Tests:
- open_trade() respects lots_multiplier parameter
- resolve_agent_size_hints() (engine.position_sizing.resolve_size_hint()'s scanner-side call
  site) is the sole writer of the final agent_size_hint, given an externally-set
  agent_size_tier (run_agent_firm_gate() no longer attaches one itself — see
  tests/test_scheduler_firm_hook.py)
"""
import sqlite3
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with two tickers seeded for comparison tests."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    for t in ("BBCA", "BBRI"):
        conn.execute(
            "INSERT INTO backtest_cache VALUES (?,?,?,?,?,?,?,?,?,?)",
            (t, "2026-01-01", "vol_weighted", 5.0, 60.0, 1.0, 10, 6, "BULL", "2026-01-01"),
        )
    conn.commit()
    conn.close()
    return db


def _make_signal(ticker, score=1.0):
    return {
        "ticker": ticker,
        "strategies": ["vol_weighted"],
        "flow": {"score": score, "verdict": "BULLISH", "confirmed": True},
    }


# ── 2.1a: open_trade lots_multiplier ─────────────────────────────────────────
# ATR=1000 → base_lots = int(500_000 / 100_000) = 5; max_lots=18 (not capped)
# multiplier=0.5 → lots = max(1, int(5*0.5)) = 2
# multiplier=1.5 → lots = max(1, int(5*1.5)) = 7

_SWING = "swing trend"   # skips R/R gate — lets us test lots_multiplier cleanly
# ATR=1000, entry=8000, swing trend:
#   base_lots = int(500_000 / (1000*100)) = 5
#   max_lots  = int(15_000_000 / 800_000) = 18  → NOT capped
#   x0.5 → 2, x1.0 → 5, x1.5 → 7


def test_open_trade_lots_multiplier_half(pt_db, monkeypatch):
    """lots_multiplier=0.5 halves computed lots (BBCA=1.0 vs BBRI=0.5)."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_base = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)
    result_half = pt.open_trade("BBRI", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=0.5)

    assert "error" not in result_base, result_base.get("error")
    assert "error" not in result_half, result_half.get("error")
    assert result_half["lots"] == max(1, int(result_base["lots"] * 0.5))


def test_open_trade_lots_multiplier_default_is_1(pt_db, monkeypatch):
    """Omitting lots_multiplier gives same lots as explicitly passing 1.0."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_default = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False)

    conn = sqlite3.connect(pt_db)
    conn.execute("DELETE FROM paper_trades WHERE ticker='BBCA'")
    conn.commit(); conn.close()

    result_one = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)

    assert "error" not in result_default, result_default.get("error")
    assert "error" not in result_one, result_one.get("error")
    assert result_default["lots"] == result_one["lots"]


def test_open_trade_lots_multiplier_above_1_increases_lots(pt_db, monkeypatch):
    """lots_multiplier=1.5 produces more lots than multiplier=1.0."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_base = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)
    result_up   = pt.open_trade("BBRI", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.5)

    assert "error" not in result_base, result_base.get("error")
    assert "error" not in result_up, result_up.get("error")
    assert result_up["lots"] > result_base["lots"]


# ── 2.1b/2.1c: resolve_agent_size_hints() — the sole writer of the final agent_size_hint ──
# REMOVED 2026-09-15: run_agent_firm_gate() no longer attaches agent_size_tier at
# all (universe-wide per-scan-cycle LLM gating was retired — see
# tests/test_scheduler_firm_hook.py). agent_size_tier is now set directly here
# to keep exercising resolve_agent_size_hints() (the sole writer of the final
# numeric agent_size_hint, ADR-AF-003) independently of how a tier gets there.

def test_resolve_approved_signal_gets_tier_based_size_hint():
    """size_tier='reduce', no edge_score → resolve_size_hint's fixed base (0.5)."""
    from scheduler.scanner import resolve_agent_size_hints
    sig = _make_signal("BBCA")
    sig["agent_size_tier"] = "reduce"
    resolve_agent_size_hints([sig])
    assert sig.get("agent_size_hint") == 0.5


def test_resolve_defaults_to_1_when_no_tier_or_edge_score():
    """No size_tier, no edge_score → resolve_size_hint's neither-present default (1.0)."""
    from scheduler.scanner import resolve_agent_size_hints
    sig = _make_signal("AMMN")
    resolve_agent_size_hints([sig])
    assert sig.get("agent_size_hint") == 1.0
