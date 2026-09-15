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
            "strategy_fn": None, "wf_flow_score": None,
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

    # ── Validated walk-forward signals (tag W) ──────────────────────────────
    # THE point of the 2026-09-02 rebuild: the EOD plan is the place where a
    # walk-forward-validated signal becomes tomorrow's base plan. These rows are
    # the ONLY ones in this pool with out-of-sample evidence behind them --
    # scheduler/scanner.py wrote them only after the strategy cleared
    # engine.admission (registry + rule parity + positive pooled OOS expectancy
    # + evidence freshness). Every other source here is a heuristic screen.
    #
    # When the admission chain admits nothing, this query returns nothing, and
    # the EOD plan is honestly all-heuristic. That is the current state and it is
    # visible in the source tags rather than hidden.
    try:
        for r in conn.execute(
            "SELECT ticker, strategies, flow_score FROM scheduled_signals "
            "WHERE substr(scan_time,1,10)=? AND signal_direction='BUY'",
            (date_str,)
        ).fetchall():
            c = _slot(r[0])
            if "W" not in c["sources"]:
                c["sources"].append("W")
            first = (r[1] or "").split(",")[0].strip()
            if first:
                c["strategy_fn"] = first
            if r[2] is not None:
                c["wf_flow_score"] = r[2]
    except sqlite3.Error:
        pass    # table absent in a lean fixture -> no W candidates, not an error

    # ── Source tag "P" REMOVED 2026-09-02 (audit finding A-2) ───────────────
    # This block read `agent_decisions WHERE strategy='premarket' AND
    # decision='approve'` for the SAME date and gave it the joint-highest weight
    # in candidate_score (2.0 + 2*confidence). That made the live data flow
    # premarket(D) -> EOD(D): the LLM's morning confidence re-entered the evening
    # ranking as if it were an independent source, and it inverted the intended
    # architecture, in which EOD is the base plan and premarket is the overnight
    # revision of it (see engine/premarket_revision.py).
    #
    # `premkt_conf` stays on the candidate dict (defaulted None by _slot) so
    # candidate_score, rank_approved and every existing reader keep working
    # unchanged; it is simply never populated from the same session any more.

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
        # strategy=None is correct and deliberate (audit L-3): an EOD screen /
        # volume / reversal candidate is not attributed to any walk-forward
        # strategy, so it has no OOS statistics to be judged on. Only Tier A
        # (directional) vetoes are read below, which need none.
        enr = enrich_candidate(conn, c["ticker"], scan_date,
                               closes=closes, regime=None, sources=mr_sources,
                               strategy=None)
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
    if "W" in s:                       # validated walk-forward signal
        # The only source in this pool backed by out-of-sample evidence and a
        # receipt-bound admission decision. It outranks every heuristic screen by
        # construction (audit 2026-09-02): a name that cleared admission is not
        # comparable to a name that merely appeared on a volume screen.
        score += 5.0
    if "R" in s:                       # reversal watchlist (broker-flow confirmed)
        score += 2.0 + (c.get("conviction") or 0.0) / 50.0
    if "P" in s:                       # premarket agent approval (no longer emitted)
        score += 2.0 + (c.get("premkt_conf") or 0.0) * 2.0
    if "S" in s:                       # technical bullish screen
        score += 1.0
    if "V" in s:                       # volume mover (capped, diminishing)
        score += min((c.get("vol_ratio") or 0.0) / 50.0, 1.0)
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


def attach_provenance(conn: sqlite3.Connection, ranked: list[dict[str, Any]],
                      date_str: str, *, plan: str) -> list[dict[str, Any]]:
    """Stamp each published row with everything needed to answer, later:

        why was this ticker here, which validated strategy produced it, what OOS
        evidence backed it, what price and rule were available at decision time?

    Without this the snapshot was a bare (date, ticker, rank) triple and outcomes
    had to be reconstructed from a separate price table after the fact — the gap
    that made "EOD prediction quality" uncomputable (audit 2026-09-02, F-1).

    Decision price is the last settled close for `date_str`: it is what the
    engine could actually see at 16:40. The entry rule is the validated
    next-session-open convention (engine/entry_convention.py), the same one every
    walk-forward strategy fills on — so an outcome is reproducible without any
    retrospective price selection.
    """
    from engine import entry_convention as ec
    from engine.edge_enrich import wf_edge_for
    from engine import rule_identity

    out = []
    for c in ranked:
        c = dict(c)
        ticker = c["ticker"]
        strategy_fn = c.get("strategy_fn")
        c["strategy_fn"] = strategy_fn      # always present on a published row

        close = c.get("close")
        if close is None:
            row = conn.execute(
                "SELECT close, date FROM ohlcv WHERE ticker=? AND date<=? "
                "ORDER BY date DESC LIMIT 1", (ticker, date_str)).fetchone()
            if row:
                close, c["decision_bar_date"] = row[0], row[1]
        c["decision_price"] = float(close) if close is not None else None
        c["decision_price_basis"] = ec.BASIS_LAST_CLOSE
        c["entry_rule"] = ec.ENTRY_RULE_NEXT_OPEN

        if strategy_fn:
            c["rule_id"] = rule_identity.live_rule_id(strategy_fn)
            try:
                from engine.registry_loader import admission_path
                c["admission_path"] = admission_path(strategy_fn)
            except Exception:
                c["admission_path"] = None
            wf = wf_edge_for(conn, ticker, strategy_fn)
            c["wf_expectancy_pct"] = wf.get("expectancy_pct")
            c["wf_n_trades"] = wf.get("n_trades")
            c["wf_last_computed"] = wf.get("last_computed")
        else:
            # Honest null: a heuristic screen hit is attributed to no validated
            # strategy and therefore carries no OOS evidence. Never borrow
            # another strategy's numbers to fill this in (audit L-3).
            c["rule_id"] = None
            c["admission_path"] = None
            c["wf_expectancy_pct"] = None
            c["wf_n_trades"] = None
            c["wf_last_computed"] = None

        prov = dict(c.get("provenance") or {})
        prov.update({
            "plan": plan,
            "sources": c.get("sources") or [],
            "confluence": c.get("confluence"),
            "candidate_score": round(candidate_score(c), 4)
            if plan == "eod" else None,
            "conviction": c.get("conviction"),
            "vol_ratio": c.get("vol_ratio"),
            "agent_confidence": c.get("confidence"),
            "agent_rationale": (c.get("rationale") or "")[:400] or None,
            "evidence_backed": bool(strategy_fn),
        })
        c["provenance"] = prov
        out.append(c)
    return out


WATCHLIST_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS watchlist_snapshot (
    date TEXT NOT NULL,
    strategy TEXT NOT NULL,
    ticker TEXT NOT NULL,
    rank INTEGER NOT NULL,
    confidence REAL,
    conviction REAL,
    confluence INTEGER,
    sources TEXT,
    PRIMARY KEY (date, strategy, ticker)
)
"""

UPGRADE_DELTA = 0.05  # confidence-delta threshold for "upgraded"/"downgraded" vs noise


def ensure_watchlist_snapshot_table(conn: sqlite3.Connection) -> None:
    conn.execute(WATCHLIST_SNAPSHOT_DDL)
    conn.commit()


def record_snapshot(conn: sqlite3.Connection, date_str: str, strategy: str,
                    ranked: list[dict[str, Any]]) -> int:
    """Publish a watchlist: append it to the immutable ledger, then refresh the
    current-state projection.

    `watchlist_snapshot` stays INSERT OR REPLACE — it is the "what is current"
    view the Telegram diff and the dashboards read, and rewriting it on a
    same-day re-run is correct for that role. What was WRONG (audit 2026-09-02)
    is that it was the ONLY record, so a re-run silently erased what had actually
    been published, and it carried no price, no strategy attribution and no
    evidence.

    engine.watchlist_ledger.append_snapshot() now writes an append-only,
    revision-numbered row first — protected by BEFORE UPDATE/DELETE triggers —
    carrying the decision price, the entry rule, the attributing walk-forward
    strategy and its OOS evidence as of this moment. Returns the revision number.
    """
    from engine import watchlist_ledger as _wl
    revision = _wl.append_snapshot(conn, date_str, strategy, ranked)
    ensure_watchlist_snapshot_table(conn)
    for i, c in enumerate(ranked, 1):
        conn.execute(
            "INSERT OR REPLACE INTO watchlist_snapshot "
            "(date, strategy, ticker, rank, confidence, conviction, confluence, sources) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (date_str, strategy, c["ticker"], i,
             c.get("confidence"), c.get("conviction"), c.get("confluence"),
             json.dumps(c.get("sources") or [])),
        )
    conn.commit()
    return revision


def get_snapshot(conn: sqlite3.Connection, date_str: str, strategy: str) -> list[dict[str, Any]]:
    """The persisted watchlist_snapshot rows for one (date, strategy), rank
    order, sources JSON-decoded. Read-only counterpart to record_snapshot --
    added for the API v1 Watchlist endpoints (Workstream 2C Task 2C-1); no
    new business rule, a straight SELECT over the same table."""
    ensure_watchlist_snapshot_table(conn)
    rows = conn.execute(
        "SELECT ticker, rank, confidence, conviction, confluence, sources "
        "FROM watchlist_snapshot WHERE strategy=? AND date=? ORDER BY rank",
        (strategy, date_str),
    ).fetchall()
    out = []
    for ticker, rank, confidence, conviction, confluence, sources_json in rows:
        try:
            sources = json.loads(sources_json) if sources_json else []
        except (ValueError, TypeError):
            sources = []
        out.append({"ticker": ticker, "rank": rank, "confidence": confidence,
                    "conviction": conviction, "confluence": confluence, "sources": sources})
    return out


def list_snapshot_dates(conn: sqlite3.Connection, strategy: str) -> list[str]:
    """Every date with a persisted watchlist_snapshot row for `strategy`,
    newest first. Enumeration only, same table -- added alongside
    get_snapshot for the API v1 Watchlist endpoints."""
    ensure_watchlist_snapshot_table(conn)
    rows = conn.execute(
        "SELECT DISTINCT date FROM watchlist_snapshot WHERE strategy=? ORDER BY date DESC",
        (strategy,),
    ).fetchall()
    return [r[0] for r in rows]


def list_snapshot_inventory(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Ticker count per (strategy, date), every strategy, newest date first
    -- the metadata layer for the API v1 Snapshot endpoints (Workstream 2C
    Task 2C-2). A GROUP BY over the same table get_snapshot/record_snapshot
    already own; no new business rule."""
    ensure_watchlist_snapshot_table(conn)
    rows = conn.execute(
        "SELECT strategy, date, COUNT(*) FROM watchlist_snapshot "
        "GROUP BY strategy, date ORDER BY date DESC, strategy"
    ).fetchall()
    return [{"strategy": s, "date": d, "ticker_count": n} for s, d, n in rows]


def diff_watchlist(conn: sqlite3.Connection, date_str: str, strategy: str,
                   ranked: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Diff today's ranked watchlist against the most recent prior `strategy`
    snapshot. Returns None when there's no prior snapshot (first run ever, or
    after a gap). Pure function over persisted + in-memory data — never
    recomputes scores/ranks, only compares numbers already decided elsewhere."""
    ensure_watchlist_snapshot_table(conn)
    row = conn.execute(
        "SELECT MAX(date) FROM watchlist_snapshot WHERE strategy=? AND date<?",
        (strategy, date_str),
    ).fetchone()
    prior_date = row[0] if row else None
    if not prior_date:
        return None

    prior = {}
    for t, rank, confidence, sources_json in conn.execute(
        "SELECT ticker, rank, confidence, sources FROM watchlist_snapshot "
        "WHERE strategy=? AND date=?", (strategy, prior_date)).fetchall():
        try:
            src = json.loads(sources_json) if sources_json else []
        except (ValueError, TypeError):
            src = []
        prior[t] = {"rank": rank, "confidence": confidence, "sources": src}

    current = {c["ticker"]: {"rank": i, "confidence": c.get("confidence"),
                             "sources": c.get("sources") or []}
              for i, c in enumerate(ranked, 1)}

    added = sorted(t for t in current if t not in prior)
    removed = sorted(t for t in prior if t not in current)

    changes = []
    for t, cur in current.items():
        if t not in prior:
            continue
        p = prior[t]
        rank_change = (p["rank"] - cur["rank"]) if p["rank"] is not None else None
        score_delta = None
        if p["confidence"] is not None and cur["confidence"] is not None:
            score_delta = cur["confidence"] - p["confidence"]
        status = "unchanged"
        if score_delta is not None:
            if score_delta >= UPGRADE_DELTA:
                status = "upgraded"
            elif score_delta <= -UPGRADE_DELTA:
                status = "downgraded"
        changes.append({
            "ticker": t, "prior_rank": p["rank"], "rank": cur["rank"],
            "rank_change": rank_change, "prior_confidence": p["confidence"],
            "confidence": cur["confidence"], "score_delta": score_delta,
            "status": status, "prior_sources": p["sources"], "sources": cur["sources"],
        })
    changes.sort(key=lambda c: abs(c["score_delta"] or 0), reverse=True)

    return {"prior_date": prior_date, "added": added, "removed": removed,
            "changes": changes}


_MAX_DIFF_ROWS = 10


def _build_diff_section(diff: Optional[dict[str, Any]]) -> list[str]:
    """Telegram-text lines for the Watchlist Changes section. Empty when there's
    no prior snapshot or nothing changed."""
    if not diff:
        return []
    added, removed, changes = diff["added"], diff["removed"], diff["changes"]
    moved = [c for c in changes if c["status"] != "unchanged"]
    if not added and not removed and not moved:
        return []

    L = ["", f"<b>📈 WATCHLIST CHANGES</b> <i>(vs {diff['prior_date']})</i>"]
    if added:
        shown = ", ".join(html.escape(t) for t in added[:_MAX_DIFF_ROWS])
        extra = f" (+{len(added) - _MAX_DIFF_ROWS} more)" if len(added) > _MAX_DIFF_ROWS else ""
        L.append(f"🆕 Added: {shown}{extra}")
    if removed:
        shown = ", ".join(html.escape(t) for t in removed[:_MAX_DIFF_ROWS])
        extra = f" (+{len(removed) - _MAX_DIFF_ROWS} more)" if len(removed) > _MAX_DIFF_ROWS else ""
        L.append(f"👋 Removed: {shown}{extra}")
    for c in moved[:_MAX_DIFF_ROWS]:
        arrow = "🔼" if c["status"] == "upgraded" else "🔽"
        rank_txt = (f" rank {c['prior_rank']}→{c['rank']}"
                   if c["rank_change"] else "")
        delta_txt = (f" conf {c['prior_confidence']:.2f}→{c['confidence']:.2f} "
                    f"({c['score_delta']:+.2f})" if c["score_delta"] is not None else "")
        L.append(f"{arrow} <b>{html.escape(c['ticker'])}</b>{rank_txt}{delta_txt}")
    if len(moved) > _MAX_DIFF_ROWS:
        L.append(f"…+{len(moved) - _MAX_DIFF_ROWS} more moves")
    return L


def get_vpin_gate(conn: sqlite3.Connection, date_str: str) -> Optional[dict]:
    """Return market VPIN summary for the most recently settled date (≤ date_str).

    The VPIN batch runs at 18:00 — after the 16:40 EOD trade plan — so today's
    data may not exist yet.  We use the most recently computed date instead, which
    is always yesterday or earlier.  Returns None when no VPIN data is available.
    """
    from engine.vpin import get_market_vpin_summary
    row = conn.execute(
        "SELECT MAX(date) FROM daily_screen WHERE date <= ? AND vpin IS NOT NULL",
        (date_str,),
    ).fetchone()
    if not row or not row[0]:
        return None
    return get_market_vpin_summary(conn, row[0])


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


_VPIN_GATE_LABELS = ('CRITICAL', 'RED')  # labels that trigger the VPIN warning banner

_VPIN_LABEL_EMOJI = {'CRITICAL': '🔴', 'RED': '🟠', 'ORANGE': '🟡',
                     'YELLOW': '🟡', 'GREEN': '🟢'}


def provider_line(decisions: list) -> Optional[str]:
    """Firm-provider summary line for the Telegram footer, derived from the
    batch's AgentDecision.providers_used. Duck-typed (no agent_firm import)
    to preserve this module's lean-venv, LLM-import-free contract. None
    when the firm didn't actually run — callers should pass provider_line=
    None for degraded/bypassed batches rather than calling this at all."""
    used: set[str] = set()
    for d in decisions:
        used.update(getattr(d, "providers_used", None) or [])
    if not used:
        return None
    if used == {"claude"}:
        return "Firm Provider:\nClaude"
    if used == {"zai"}:
        return "Firm Provider:\nZ.ai"
    if "claude" in used and "zai" in used:
        return "Firm Provider:\nClaude → Z.ai (Auto Failover)"
    return "Firm Provider:\n" + ", ".join(sorted(used))


def build_message(ranked: list[dict[str, Any]],
                  regime: tuple[str, Optional[float]],
                  date_str: str,
                  degraded: bool = False,
                  vpin_summary: Optional[dict] = None,
                  provider_line: Optional[str] = None,
                  diff: Optional[dict[str, Any]] = None,
                  watchlist_size: Optional[int] = None) -> str:
    """Single Telegram HTML message. No raw <,>,& in dynamic text (tickers/numbers
    only), so HTML parse_mode is safe.

    vpin_summary: result of get_vpin_gate() — adds a VPIN warning banner when
    market microstructure is RED or CRITICAL.
    diff: result of diff_watchlist() — adds a Watchlist Changes section
    (added/removed/upgraded/downgraded/rank+score deltas) when present.
    watchlist_size: total candidate pool size before firm filtering, for the
    Daily Summary line (distinct from len(ranked), the firm-approved count).
    """
    tier, score = regime
    emoji = _REGIME_EMOJI.get(tier, "⚪")
    score_txt = f"{score:.0f}/100" if score is not None else "n/a"
    subtitle = ("⚠️ Firm offline — confluence-ranked · longs only" if degraded
                else "Agent-firm ranked · 4 sources merged · longs only")

    L = [f"<b>📊 IDX TRADE PLAN — {date_str}</b>",
         f"{emoji} Regime <b>{tier}</b> ({score_txt}) — next-session longs",
         f"<i>{subtitle}</i>"]
    if watchlist_size is not None:
        L.append(f"Watchlist: {watchlist_size} candidates → {len(ranked)} approved")

    vpin_lbl = (vpin_summary or {}).get('label')
    if vpin_lbl in _VPIN_GATE_LABELS:
        ve = _VPIN_LABEL_EMOJI.get(vpin_lbl, '⚠️')
        avg = vpin_summary.get('avg_vpin')
        avg_txt = f"{avg:.3f}" if avg is not None else "n/a"
        vpin_date = vpin_summary.get('date', '')
        L.append(f"<b>{ve} VPIN {vpin_lbl}</b> — market microstructure elevated "
                 f"(avg {avg_txt}, settled {vpin_date}); execute with extra caution")

    L.append("")

    if not ranked:
        L.append("No firm-approved long setups today.")
        L.append("")
        L.append("<i>broker_flow/VPIN settle ~20:15; flow on last settled day.</i>")
        L.extend(_build_diff_section(diff))
        if provider_line:
            L.append("")
            L.append(provider_line)
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
    L.extend(_build_diff_section(diff))
    if provider_line:
        L.append("")
        L.append(provider_line)
    return "\n".join(L)
