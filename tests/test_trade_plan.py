"""Tests for engine.trade_plan — the EOD merged/agent-ranked long shortlist.

Pure DB/data functions only (no LLM); runs on the lean venv.
"""
import json
import sqlite3

import pytest

from engine.agent_firm.schemas import AgentDecision
from engine.trade_plan import (
    build_message,
    edge_prescreen,
    fallback_rank,
    gather_long_candidates,
    get_regime,
    rank_approved,
    select_top,
)
from engine.wf_edge import ensure_wf_edge_table, save_wf_edge

DATE = "2026-06-23"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(
        """
        CREATE TABLE reversal_watchlist (scan_date TEXT, ticker TEXT, direction TEXT,
            conviction REAL, close REAL, smart_money TEXT, net_value REAL, reasons TEXT);
        CREATE TABLE daily_screen (date TEXT, ticker TEXT, close REAL,
            vol_ratio REAL, signal TEXT);
        CREATE TABLE agent_decisions (created_at TEXT, ticker TEXT, strategy TEXT,
            decision TEXT, confidence REAL);
        CREATE TABLE market_risk_log (date TEXT, scan_time TEXT, tier TEXT, score REAL);
        """
    )
    # CPIN: reversal long only
    c.execute("INSERT INTO reversal_watchlist VALUES (?,?,?,?,?,?,?,?)",
              (DATE, "CPIN", "long", 78.1, 3150, "ACCUMULATION", 1.1e9,
               json.dumps(["broker ACCUMULATION (strong)", "IDX30"])))
    # AMRT: reversal SHORT — must never appear as a long candidate
    c.execute("INSERT INTO reversal_watchlist VALUES (?,?,?,?,?,?,?,?)",
              (DATE, "AMRT", "short", 62.6, 1440, "STRONG_SELL", -1e10, "[]"))
    # AKRA: reversal long + screen bullish + premarket approve  → confluence 3
    c.execute("INSERT INTO reversal_watchlist VALUES (?,?,?,?,?,?,?,?)",
              (DATE, "AKRA", "long", 40.0, 1275, "ACCUMULATION", 5e8, "[]"))
    c.execute("INSERT INTO daily_screen VALUES (?,?,?,?,?)",
              (DATE, "AKRA", 1275, 1.8, "bullish"))
    c.execute("INSERT INTO agent_decisions VALUES (?,?,?,?,?)",
              (f"{DATE} 08:35", "AKRA", "premarket", "approve", 0.65))
    # SURE: pure volume mover (vol_ratio 138)
    c.execute("INSERT INTO daily_screen VALUES (?,?,?,?,?)",
              (DATE, "SURE", 2770, 138.2, "bullish"))
    # JSMR: screen 'watch' low vol — should NOT be picked up
    c.execute("INSERT INTO daily_screen VALUES (?,?,?,?,?)",
              (DATE, "JSMR", 2850, 1.2, "watch"))
    # BTON: bearish on a huge volume spike (distribution dump) — must NOT be a long
    c.execute("INSERT INTO daily_screen VALUES (?,?,?,?,?)",
              (DATE, "BTON", 342, 35.7, "bearish"))
    c.execute("INSERT INTO market_risk_log VALUES (?,?,?,?)",
              (DATE, "14:35", "YELLOW", 45.0))
    c.commit()
    return c


def _dec(ticker, decision, confidence=None, rationale=None, size_hint=None):
    return AgentDecision(ticker=ticker, strategy="eod", scan_time=f"{DATE} 16:40",
                         quant_score=70.0, decision=decision, confidence=confidence,
                         rationale=rationale, size_hint=size_hint)


def test_gather_excludes_shorts(conn):
    cands = gather_long_candidates(conn, DATE)
    tickers = {c["ticker"] for c in cands}
    assert "AMRT" not in tickers          # short must be dropped
    assert {"CPIN", "AKRA", "SURE"} <= tickers


def test_gather_excludes_low_vol_watch(conn):
    cands = gather_long_candidates(conn, DATE)
    assert "JSMR" not in {c["ticker"] for c in cands}


def test_gather_excludes_bearish_volume_dump(conn):
    # a bearish name on a volume spike is distribution, never a long candidate
    cands = gather_long_candidates(conn, DATE)
    assert "BTON" not in {c["ticker"] for c in cands}


def test_confluence_counts_distinct_sources(conn):
    cands = {c["ticker"]: c for c in gather_long_candidates(conn, DATE)}
    assert cands["AKRA"]["confluence"] == 3          # R + S + P
    assert set(cands["AKRA"]["sources"]) == {"R", "S", "P"}
    assert cands["CPIN"]["confluence"] == 1
    assert cands["SURE"]["sources"] == ["S", "V"]    # bullish + volume mover


def test_select_top_orders_by_confluence(conn):
    cands = gather_long_candidates(conn, DATE)
    top = select_top(cands, n=2)
    assert top[0]["ticker"] == "AKRA"                # highest confluence first
    assert len(top) == 2


def test_rank_approved_drops_vetoes_and_sorts_by_confidence(conn):
    cands = gather_long_candidates(conn, DATE)
    decisions = [_dec("CPIN", "approve", 0.80),
                 _dec("AKRA", "approve", 0.65),
                 _dec("SURE", "veto", 0.20)]
    ranked = rank_approved(cands, decisions)
    assert [c["ticker"] for c in ranked] == ["CPIN", "AKRA"]   # SURE vetoed out
    assert ranked[0]["confidence"] == 0.80


def test_get_regime(conn):
    assert get_regime(conn, DATE) == ("YELLOW", 45.0)
    assert get_regime(conn, "2099-01-01") == ("UNKNOWN", None)


def test_build_message_longs_only_no_shorts(conn):
    cands = gather_long_candidates(conn, DATE)
    # rationale with a raw '->' (real reversal reasons contain these) must not break HTML
    decisions = [_dec("CPIN", "approve", 0.80, rationale="delta flip -0.01B -> +0.01B")]
    ranked = rank_approved(cands, decisions)
    msg = build_message(ranked, ("YELLOW", 45.0), DATE)
    assert "TRADE PLAN" in msg and DATE in msg
    assert "CPIN" in msg and "0.80" in msg
    assert "AMRT" not in msg                          # never report shorts
    # HTML-parse safety: dynamic content must not carry raw angle/amp chars
    body = msg.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    assert "<" not in body and ">" not in body


def test_select_top_prefers_reversal_over_volume_spike(conn):
    # add a high-conviction reversal large-cap (confluence 1) and a thin volume spike
    conn.execute("INSERT INTO reversal_watchlist VALUES (?,?,?,?,?,?,?,?)",
                 (DATE, "TLKM", "long", 61.0, 2540, "STRONG_BUY", 4e10, "[]"))
    conn.commit()
    cands = gather_long_candidates(conn, DATE)
    top_tickers = [c["ticker"] for c in select_top(cands, n=4)]
    # AKRA (R+S+P) and TLKM (R conv61) must outrank the pure volume spike SURE
    assert top_tickers.index("TLKM") < top_tickers.index("SURE")


def test_build_message_empty_is_graceful(conn):
    msg = build_message([], ("RED", 80.0), DATE)
    assert "No firm-approved" in msg


def test_fallback_rank_synthesizes_confidence_from_score(conn):
    cands = gather_long_candidates(conn, DATE)
    ranked = fallback_rank(cands)
    assert ranked[0]["ticker"] == "AKRA"                  # R+S+P → highest score
    assert ranked[0]["confidence"] == pytest.approx(0.85)  # 0.5 + 0.05*score, capped
    assert all("confidence" in c for c in ranked)


def test_rationale_is_collapsed_to_one_lean_line(conn):
    cands = gather_long_candidates(conn, DATE)
    multiline = "Risk: bearish regime.\nBull/Bear: strong flow.   Extra   spaces."
    decisions = [_dec("CPIN", "approve", 0.7, rationale=multiline)]
    msg = build_message(rank_approved(cands, decisions), ("YELLOW", 45.0), DATE)
    # the rationale line must contain no newline and no double spaces
    rline = [ln for ln in msg.split("\n") if "Risk:" in ln][0]
    assert "  " not in rline.strip()
    assert "Bull/Bear: strong flow. Extra spaces." in rline


def test_degraded_message_is_flagged(conn):
    ranked = fallback_rank(gather_long_candidates(conn, DATE))
    msg = build_message(ranked, ("YELLOW", 45.0), DATE, degraded=True)
    assert "Firm offline" in msg


class TestEdgePrescreen:
    """Tier-A directional pre-screen before the LLM firm."""

    def _db(self):
        from datetime import date, timedelta
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, close REAL)")
        c.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
                  "composite_score INT, verdict TEXT)")
        ensure_wf_edge_table(c)
        self._base = date(2026, 1, 1)
        return c

    def _ohlcv(self, c, ticker, trend):
        from datetime import timedelta
        for i in range(60):
            d = (self._base + timedelta(days=i)).isoformat()
            close = (100 + i) if trend == "up" else (200 - i)
            c.execute("INSERT INTO ohlcv VALUES (?,?,?)", (ticker, d, close))
        c.commit()

    def _cand(self, ticker, sources):
        return {"ticker": ticker, "sources": sources}

    def test_bearish_tech_non_reversal_is_vetoed(self):
        c = self._db(); self._ohlcv(c, "AAAA", "down")
        surv, veto = edge_prescreen(c, [self._cand("AAAA", ["S", "V"])], "SIDEWAYS", "2026-06-23")
        assert surv == [] and veto[0][0] == "AAAA" and veto[0][1].startswith("d2")

    def test_reversal_carveout_survives_bearish_tech(self):
        c = self._db(); self._ohlcv(c, "BBBB", "down")
        # tag R → mean-reversion carve-out exempts d2
        surv, veto = edge_prescreen(c, [self._cand("BBBB", ["R"])], "SIDEWAYS", "2026-06-23")
        assert [x["ticker"] for x in surv] == ["BBBB"] and veto == []

    def test_distributing_flow_vetoed_even_for_reversal(self):
        c = self._db(); self._ohlcv(c, "CCCC", "up")
        c.execute("INSERT INTO stockbit_flow VALUES ('CCCC','2026-06-23',-5,'DISTRIBUTING')"); c.commit()
        surv, veto = edge_prescreen(c, [self._cand("CCCC", ["R"])], "SIDEWAYS", "2026-06-23")
        assert surv == [] and veto[0][1].startswith("d1")   # d1 is not MR-exempt

    def test_tier_b_failure_is_not_prescreened_out(self):
        # bullish tech, neutral flow, no wf_edge → passes Tier A, fails Tier B (s1).
        # pre-screen must KEEP it (only Tier A applies here; firm decides the rest).
        c = self._db(); self._ohlcv(c, "DDDD", "up")
        surv, veto = edge_prescreen(c, [self._cand("DDDD", ["S"])], "SIDEWAYS", "2026-06-23")
        assert [x["ticker"] for x in surv] == ["DDDD"] and veto == []

    def test_market_bear_vetoes_non_catalyst(self):
        c = self._db(); self._ohlcv(c, "EEEE", "up")
        surv, veto = edge_prescreen(c, [self._cand("EEEE", ["R"])], "BEAR", "2026-06-23")
        assert surv == [] and veto[0][1].startswith("d4")   # d4 not MR-exempt
