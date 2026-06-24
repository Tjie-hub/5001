"""EOD trade-plan builder — merges every long signal source into one agent-ranked
shortlist for the next session.

Pipeline (driven by scheduler.jobs.run_eod_trade_plan at 16:40 WIB):

    gather_long_candidates  →  select_top(n=8)  →  agent firm evaluate_staged
                                                 →  rank_approved  →  build_message

Sources merged (longs only — shorts are exit/SL triggers, never reported here):
  • reversal_watchlist (direction='long')   tag R
  • daily_screen        (signal='bullish')  tag S
  • daily_screen        (vol_ratio>=5)      tag V   (volume mover)
  • agent_decisions     (premarket approve) tag P

Confluence = number of distinct sources a ticker shows up in. The firm only sees
the top-N by weighted source-quality score (cost cap) — see candidate_score, which
ensures broker-confirmed reversals outrank thin volume spikes. The final report
shows firm-APPROVED names only.

Pure functions here are DB/data-only (no LLM, no network) so they unit-test on the
lean venv. The firm call lives in the scheduler job.
"""
from __future__ import annotations

import html
import json
import sqlite3
from typing import Any, Optional

VOLUME_MOVER_RATIO = 5.0  # vol_ratio at/above this counts as a "volume" source


def _first_reason(reasons_json: Optional[str]) -> str:
    if not reasons_json:
        return ""
    try:
        arr = json.loads(reasons_json)
        return str(arr[0]) if arr else ""
    except (ValueError, TypeError):
        return ""


def gather_long_candidates(conn: sqlite3.Connection, date_str: str) -> list[dict[str, Any]]:
    """Merge all long-side signal sources for `date_str` into one candidate list,
    keyed by ticker, with a confluence count and the evidence needed to rank."""
    cand: dict[str, dict[str, Any]] = {}

    def _slot(ticker: str) -> dict[str, Any]:
        return cand.setdefault(ticker, {
            "ticker": ticker, "close": None, "sources": [],
            "conviction": 0.0, "smart_money": None, "net_value": 0.0,
            "vol_ratio": 0.0, "premkt_conf": None, "reason": "",
        })

    # ── Reversal watchlist (longs) ──────────────────────────────────────────
    for r in conn.execute(
        "SELECT ticker, conviction, close, smart_money, net_value, reasons "
        "FROM reversal_watchlist WHERE scan_date=? AND direction='long'", (date_str,)
    ).fetchall():
        c = _slot(r[0])
        c["sources"].append("R")
        c["conviction"] = float(r[1] or 0)
        c["close"] = c["close"] or r[2]
        c["smart_money"] = r[3]
        c["net_value"] = float(r[4] or 0)
        if not c["reason"]:
            c["reason"] = _first_reason(r[5])

    # ── Daily screen (bullish signal + volume movers) ───────────────────────
    # Exclude bearish rows entirely: a bearish name on a volume spike is distribution
    # (a dump / short signal), never a long entry — it must not enter the long pool.
    for r in conn.execute(
        "SELECT ticker, close, vol_ratio, signal FROM daily_screen "
        "WHERE date=? AND signal!='bearish' AND (signal='bullish' OR vol_ratio>=?)",
        (date_str, VOLUME_MOVER_RATIO)
    ).fetchall():
        c = _slot(r[0])
        c["close"] = c["close"] or r[1]
        c["vol_ratio"] = float(r[2] or 0)
        if r[3] == "bullish" and "S" not in c["sources"]:
            c["sources"].append("S")
        if float(r[2] or 0) >= VOLUME_MOVER_RATIO and "V" not in c["sources"]:
            c["sources"].append("V")

    # ── Premarket agent approvals (already firm-vetted today) ───────────────
    for r in conn.execute(
        "SELECT ticker, confidence FROM agent_decisions "
        "WHERE substr(created_at,1,10)=? AND strategy='premarket' AND decision='approve'",
        (date_str,)
    ).fetchall():
        c = _slot(r[0])
        if "P" not in c["sources"]:
            c["sources"].append("P")
        c["premkt_conf"] = float(r[1]) if r[1] is not None else None

    for c in cand.values():
        c["confluence"] = len(c["sources"])
    return list(cand.values())


def edge_prescreen(conn: sqlite3.Connection, candidates: list[dict[str, Any]],
                   market_regime: str, scan_date: str) -> tuple[list, list]:
    """Tier-A directional pre-screen BEFORE the LLM firm — drops candidates that
    fail directional safety so they never cost an LLM call:
        d1 distributing flow · d2 bearish tech (no MR) · d3 tech/flow disagree (no MR)
        d4 market risk-off (BEAR)
    Tier B statistical gates and the session cap are intentionally NOT applied here
    (those stay the firm's job; applying them would over-veto screen/volume names
    that legitimately lack wf_edge stats).

    Reversal-watchlist longs (tag 'R') are mean-reversion entries, so they get the
    is_mean_reversion carve-out that exempts d2/d3.

    Returns (survivors, vetoed) — survivors are kept candidate dicts; vetoed is a
    list of (ticker, reason)."""
    from engine.edge_enrich import enrich_candidate
    from engine.veto import diagnose

    survivors, vetoed = [], []
    for c in candidates:
        rows = conn.execute(
            "SELECT close FROM ohlcv WHERE ticker=? ORDER BY date DESC LIMIT 60",
            (c["ticker"],),
        ).fetchall()
        closes = [r[0] for r in rows][::-1]
        mr_sources = ["REVERSAL"] if "R" in (c.get("sources") or []) else []
        enr = enrich_candidate(conn, c["ticker"], scan_date,
                               closes=closes, regime=None, sources=mr_sources)
        reason = diagnose(enr, market_regime)[1]
        if reason and reason.startswith("d"):     # Tier A directional veto only
            vetoed.append((c["ticker"], reason))
        else:
            survivors.append(c)
    return survivors, vetoed


def candidate_score(c: dict[str, Any]) -> float:
    """Weighted strength score for ordering. Source quality matters more than raw
    count: broker-confirmed reversals and agent-approved premarket names dominate
    thin volume spikes (S and V both fire on the same screen row, so they are NOT
    independent confirmation and must not out-rank an institutional reversal)."""
    s = c.get("sources", [])
    score = 0.0
    if "R" in s:                       # reversal watchlist (broker-flow confirmed)
        score += 2.0 + c["conviction"] / 50.0
    if "P" in s:                       # premarket agent approval
        score += 2.0 + (c.get("premkt_conf") or 0.0) * 2.0
    if "S" in s:                       # technical bullish screen
        score += 1.0
    if "V" in s:                       # volume mover (capped, diminishing)
        score += min(c["vol_ratio"] / 50.0, 1.0)
    return score


def _rank_key(c: dict[str, Any]) -> tuple:
    return (candidate_score(c), c["conviction"], c["net_value"])


def select_top(cands: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
    """Strongest candidates to hand to the firm (caps token cost). Ranked by weighted
    source-quality score so institutional reversals are never crowded out by spikes."""
    return sorted(cands, key=_rank_key, reverse=True)[:n]


def rank_approved(cands: list[dict[str, Any]],
                  decisions: list) -> list[dict[str, Any]]:
    """Keep only firm-APPROVED tickers, attach the firm's confidence/rationale,
    and rank by (confidence, confluence, conviction)."""
    by_ticker = {c["ticker"]: c for c in cands}
    out = []
    for d in decisions:
        if d.decision != "approve":
            continue
        c = dict(by_ticker.get(d.ticker, {"ticker": d.ticker, "close": None,
                                          "sources": [], "confluence": 0,
                                          "conviction": 0.0, "vol_ratio": 0.0,
                                          "reason": ""}))
        c["confidence"] = float(d.confidence) if d.confidence is not None else 0.0
        c["size_hint"] = float(d.size_hint) if d.size_hint is not None else None
        c["rationale"] = (d.rationale or "").replace("\\n", " ").strip()
        out.append(c)
    out.sort(key=lambda c: (c["confidence"], c["confluence"], c["conviction"]),
             reverse=True)
    return out


def fallback_rank(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic ranking used when the agent firm is disabled or errors, so the
    plan still ships. Confidence is synthesized from the weighted candidate_score
    (0.5 + 0.05·score, capped 0.85) and the report is flagged degraded by the caller."""
    out = []
    for c in sorted(cands, key=_rank_key, reverse=True):
        c = dict(c)
        c["confidence"] = min(0.5 + 0.05 * candidate_score(c), 0.85)
        c["size_hint"] = None
        c["rationale"] = c.get("reason", "")
        out.append(c)
    return out


def get_regime(conn: sqlite3.Connection, date_str: str) -> tuple[str, Optional[float]]:
    """Latest market-risk tier/score for the day (for the report header)."""
    row = conn.execute(
        "SELECT tier, score FROM market_risk_log WHERE date=? "
        "ORDER BY scan_time DESC LIMIT 1", (date_str,)
    ).fetchone()
    if not row:
        return ("UNKNOWN", None)
    return (row[0], float(row[1]) if row[1] is not None else None)


_REGIME_EMOJI = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}


def _lean(text: str, limit: int = 150) -> str:
    """Collapse whitespace/newlines to a single clean line and truncate, so each
    pick is one tidy row (firm rationales can be multi-sentence with newlines)."""
    one = " ".join((text or "").split())
    return one if len(one) <= limit else one[: limit - 1].rstrip() + "…"


def _stars(conf: float) -> str:
    if conf >= 0.70:
        return "⭐⭐⭐"
    if conf >= 0.55:
        return "⭐⭐"
    return "⭐"


def build_message(ranked: list[dict[str, Any]],
                  regime: tuple[str, Optional[float]],
                  date_str: str,
                  degraded: bool = False) -> str:
    """Single Telegram HTML message. No raw <,>,& in dynamic text (tickers/numbers
    only), so HTML parse_mode is safe."""
    tier, score = regime
    emoji = _REGIME_EMOJI.get(tier, "⚪")
    score_txt = f"{score:.0f}/100" if score is not None else "n/a"
    subtitle = ("⚠️ Firm offline — confluence-ranked · longs only" if degraded
                else "Agent-firm ranked · 4 sources merged · longs only")

    L = [f"<b>📊 IDX TRADE PLAN — {date_str}</b>",
         f"{emoji} Regime <b>{tier}</b> ({score_txt}) — next-session longs",
         f"<i>{subtitle}</i>", ""]

    if not ranked:
        L.append("No firm-approved long setups today.")
        L.append("")
        L.append("<i>broker_flow/VPIN settle ~20:15; flow on last settled day.</i>")
        return "\n".join(L)

    L.append("<b>🏆 TOP LONGS</b>")
    for i, c in enumerate(ranked, 1):
        px = f"{int(c['close']):,}" if c.get("close") else "—"
        tags = "".join(c.get("sources", [])) or "—"
        L.append(f"<b>{i}. {html.escape(c['ticker'])}</b> {px}  {_stars(c['confidence'])}  "
                 f"conf {c['confidence']:.2f}  [{tags}]")
        line = c.get("rationale") or c.get("reason") or ""
        if line:
            L.append(f"   {html.escape(_lean(line))}")  # escape: reasons contain '->' etc.
    L.append("")
    L.append("<i>R=reversal S=screen V=volume P=premarket · "
             "broker_flow/VPIN settle ~20:15.</i>")
    return "\n".join(L)
