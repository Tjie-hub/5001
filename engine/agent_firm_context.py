"""engine/agent_firm_context.py — Production-Engine-owned assembly of Agent Firm's Tier 1
context objects.

Ownership (docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md): this module lives outside
engine/agent_firm/ deliberately, so the boundary is visible in the file tree, not just in
documentation. It imports Agent Firm's type definitions (engine.agent_firm.schemas) and
Production Engine's existing, canonical compute functions
(docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md) — it is Production Engine code that
happens to produce Agent-Firm-shaped output, not Agent Firm reaching into Production Engine's
internals. This is the same shape engine/edge_enrich.py already uses for engine/veto.py.

No duplicated deterministic calculations: every builder below either wraps an existing
canonical function (tech_direction, detect_regime, has_catalyst, calc_sma/calc_adx/etc.,
support_resistance/detect_patterns) or performs a small, genuinely new aggregation
(net_foreign_14d's SUM, trend_7d's rolling-sign, mentions_count_7d's COUNT) that has no
existing implementation elsewhere to duplicate.

Status (AF-2 WP1-4, all complete): every builder below is called from all five live
SignalCandidate construction sites — scheduler/scanner.py's run_agent_firm_gate()/
rank_bear_watchlist_and_notify() (AF-2 WP2), scheduler/jobs.py's run_premarket_firm_scan()/
run_eod_trade_plan() and monitor.py's _agent_confirms_exit() (AF-2 WP4) — before
evaluate()/evaluate_staged() runs. Every specialist (engine/agent_firm/agents/technical.py,
flow.py, regime.py, news.py, risk.py) reads its own field directly off the resulting
SignalCandidate (AF-2 WP3) — this is a live, load-bearing pipeline, not producer-only
wiring. See Audit/AF2_WP1_IMPLEMENTATION_REPORT.md through AF2_WP4_FINAL_CERTIFICATION.md
for the full implementation/audit trail.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Callable, Optional

import pandas as pd

from engine.agent_firm.schemas import (
    ExecutionContext,
    FlowContext,
    MarketContext,
    NewsContext,
    PortfolioContext,
    RegimeContext,
    RiskContext,
    SessionContext,
    TechnicalContext,
)

logger = logging.getLogger(__name__)

_OHLCV_COLS = ["date", "open", "high", "low", "close", "volume"]


def _safe(builder: Callable, *args, default_factory: Callable, **kwargs):
    """Fail-soft wrapper (CLAUDE.md convention: registry/metrics-style surfaces degrade
    to sentinels and log, rather than crash). A broken query for one context object must
    never break candidate construction or evaluation — it degrades to that object's empty
    default instead."""
    try:
        return builder(*args, **kwargs)
    except Exception as e:
        logger.warning(f"agent_firm_context: {builder.__name__} failed: {e}")
        return default_factory()


# ── Shared helpers ──────────────────────────────────────────────────────────────────────

def _fetch_ohlcv_df(conn: sqlite3.Connection, ticker: str, limit: int = 60) -> Optional[pd.DataFrame]:
    """Chronological (oldest-first) OHLCV DataFrame — every engine.indicators/
    engine.chart_indicators/engine.technicals function assumes this order (verified
    against their bodies: .rolling()/.diff()/.shift()/.iloc[-1]=latest)."""
    rows = conn.execute(
        f"SELECT {', '.join(_OHLCV_COLS)} FROM ohlcv WHERE ticker=? "
        f"ORDER BY date DESC LIMIT ?",
        (ticker, limit),
    ).fetchall()
    if not rows:
        return None
    df = pd.DataFrame(list(rows)[::-1], columns=_OHLCV_COLS)
    return df


# ── TechnicalContext (ADR-AF-001: mechanical_direction is a tech_direction() passthrough;
#    everything else is engine.indicators/chart_indicators values, not a second classifier) ──

def build_technical_context(
    conn: sqlite3.Connection, ticker: str, ohlcv_df: Optional[pd.DataFrame] = None,
) -> TechnicalContext:
    """`ohlcv_df` may be supplied pre-fetched (e.g. by build_market_context() reusing this
    function for IHSG) to avoid a duplicate query — not a duplicate computation."""
    from engine.chart_indicators import detect_patterns, support_resistance
    from engine.indicators import calc_adx, calc_atr, calc_close_vs_ma, calc_ma_slope, calc_sma, calc_vol_ratio
    from engine.technicals import tech_direction

    df = ohlcv_df if ohlcv_df is not None else _fetch_ohlcv_df(conn, ticker)
    if df is None or len(df) < 2:
        return TechnicalContext()

    closes = df["close"].tolist()
    direction = tech_direction(closes)

    sma20 = calc_sma(df, 20)
    sma50 = calc_sma(df, 50)
    close_vs_ma50 = calc_close_vs_ma(df, 50)
    ma_slope = calc_ma_slope(df)
    adx = calc_adx(df)
    atr = calc_atr(df)
    vol_ratio = calc_vol_ratio(df)

    def _last(series) -> Optional[float]:
        try:
            v = series.iloc[-1]
            return None if pd.isna(v) else round(float(v), 4)
        except Exception:
            return None

    try:
        sr = support_resistance(df)
    except Exception:
        sr = {"support": [], "resistance": []}
    try:
        # detect_patterns() returns one entry per bar across the whole input window;
        # only the last 5 bars are relevant "current" pattern context here.
        recent_dates = set(df["date"].tail(5))
        patterns = [
            f"{p['pattern']}({p['dir']})" for p in detect_patterns(df)
            if p.get("date") in recent_dates
        ]
    except Exception:
        patterns = []

    recent = df.tail(10).to_dict("records")

    return TechnicalContext(
        sma20=_last(sma20),
        sma50=_last(sma50),
        close_vs_sma50_pct=_last(close_vs_ma50),
        ma_slope_20=_last(ma_slope),
        adx=_last(adx),
        atr=_last(atr),
        vol_ratio=_last(vol_ratio),
        support_levels=sr.get("support", []),
        resistance_levels=sr.get("resistance", []),
        pattern_flags=[p for p in patterns if p],
        mechanical_direction=direction,
        ohlcv_recent_10d=recent,
    )


# ── FlowContext (ADR-AF-001: verdict/smart_money/composite_score/foreign_score are
#    passthroughs of stockbit_flow's own columns, already computed by flow_filter.py) ──

def build_flow_context(conn: sqlite3.Connection, ticker: str) -> FlowContext:
    row = conn.execute(
        "SELECT verdict, smart_money, composite_score, foreign_score FROM stockbit_flow "
        "WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    verdict = smart_money = None
    composite_score = foreign_score = None
    if row:
        verdict, smart_money, composite_score, foreign_score = row

    net_foreign_row = conn.execute(
        "SELECT SUM(lot_value) FROM broker_flow WHERE ticker=? AND investor_type='Asing' "
        "AND side='BUY' AND trade_date >= date('now', '-14 days')",
        (ticker,),
    ).fetchone()
    net_buy = net_foreign_row[0] or 0
    net_sell_row = conn.execute(
        "SELECT SUM(lot_value) FROM broker_flow WHERE ticker=? AND investor_type='Asing' "
        "AND side='SELL' AND trade_date >= date('now', '-14 days')",
        (ticker,),
    ).fetchone()
    net_sell = net_sell_row[0] or 0
    net_foreign_14d = int(net_buy - net_sell)

    bar_rows = conn.execute(
        "SELECT trade_date, bar_time, buy_lot, sell_lot, delta, net_value "
        "FROM stockbit_flow_bars WHERE ticker=? AND trade_date >= date('now', '-7 days') "
        "ORDER BY trade_date DESC, bar_time",
        (ticker,),
    ).fetchall()
    bars = [dict(zip(
        ["trade_date", "bar_time", "buy_lot", "sell_lot", "delta", "net_value"], r,
    )) for r in bar_rows]

    trend_7d = "flat"
    if len(bars) >= 4:
        half = len(bars) // 2
        recent_delta = sum((b.get("delta") or 0) for b in bars[:half])
        older_delta = sum((b.get("delta") or 0) for b in bars[half:])
        if recent_delta > older_delta * 1.1:
            trend_7d = "accumulating"
        elif recent_delta < older_delta * 0.9:
            trend_7d = "distributing"

    return FlowContext(
        verdict=verdict,
        smart_money=smart_money,
        composite_score=composite_score,
        foreign_score=foreign_score,
        net_foreign_14d=net_foreign_14d,
        trend_7d=trend_7d,
        flow_bars_recent=bars[:20],
    )


# ── RegimeContext (ADR-AF-001: regime_call is a detect_regime() passthrough for the ticker's
#    own price series; ticker_consistency_pct/sector_tailwind/macro_risk are the genuinely
#    new per-ticker confirmation facts named in the ADR, computed from wf_scores/daily_screen,
#    not a second regime classifier) ──

def build_regime_context(
    conn: sqlite3.Connection, ticker: str, ohlcv_df: Optional[pd.DataFrame] = None,
) -> RegimeContext:
    from engine.regime_filter import detect_regime

    df = ohlcv_df if ohlcv_df is not None else _fetch_ohlcv_df(conn, ticker)
    try:
        regime_call = detect_regime(df) if df is not None and len(df) >= 20 else "UNKNOWN"
    except Exception:
        regime_call = "UNKNOWN"
    if regime_call not in ("BULL", "BEAR", "SIDEWAYS", "VOLATILE", "UNKNOWN"):
        regime_call = "UNKNOWN"

    wf_rows = conn.execute(
        "SELECT strategy, consistency_pct, avg_sharpe FROM wf_scores WHERE ticker=? "
        "ORDER BY weighted_score DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    best_strategy = ticker_consistency_pct = None
    sector_tailwind = False
    if wf_rows:
        best_strategy, ticker_consistency_pct, avg_sharpe = wf_rows
        sector_tailwind = bool(avg_sharpe is not None and avg_sharpe > 0.8)

    screen_rows = conn.execute(
        "SELECT date, signal, vpin_label, vol_ratio FROM daily_screen WHERE ticker=? "
        "ORDER BY date DESC LIMIT 10",
        (ticker,),
    ).fetchall()
    screens = [dict(zip(["date", "signal", "vpin_label", "vol_ratio"], r)) for r in screen_rows]

    macro_risk = "LOW"
    spikes_with_negative = any(
        (s.get("vpin_label") == "EXTREME" or (s.get("vol_ratio") or 0) > 3.0)
        and s.get("signal") in ("BEARISH", "SELL", "NEGATIVE")
        for s in screens
    )
    if spikes_with_negative:
        macro_risk = "HIGH"
    elif any((s.get("vol_ratio") or 0) > 3.0 for s in screens):
        macro_risk = "MEDIUM"

    return RegimeContext(
        regime_call=regime_call,
        sector_tailwind=sector_tailwind,
        macro_risk=macro_risk,
        best_strategy=best_strategy,
        ticker_consistency_pct=ticker_consistency_pct,
        recent_screen_signals=screens,
    )


# ── NewsContext (ADR-AF-001: has_catalyst is a has_catalyst() passthrough, distinct from
#    the News agent's own directional catalyst_sentiment NLU output) ──

def build_news_context(conn: sqlite3.Connection, ticker: str, date_str: str, days: int = 7) -> NewsContext:
    """Reuses engine.agent_firm.tools.news_lookup.lookup() directly — no reimplementation
    of its query — by recovering the connection's own db path via PRAGMA database_list."""
    from engine.catalyst import has_catalyst
    from engine.agent_firm.tools import news_lookup

    try:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        mentions = news_lookup.lookup(db_path, ticker, days=days)
    except Exception:
        mentions = []
    count = sum(int(m.get("count") or 0) for m in mentions) if mentions else 0

    try:
        catalyst = bool(has_catalyst(conn, ticker, date_str))
    except Exception:
        catalyst = False

    return NewsContext(
        mentions_7d=mentions,
        mentions_count_7d=count,
        has_catalyst=catalyst,
        web_search_results=[],
    )


# ── MarketContext (ADR-AF-001: regime is a detect_regime() passthrough on IHSG;
#    ihsg_trend reuses build_technical_context() rather than a separate computation;
#    market_risk_score is a dependency-injection point — the caller who already computed
#    it once per scan cycle (scheduler/scanner.py's existing wiring) passes it in, so this
#    module never re-derives the 4-sensor composite itself) ──

def build_market_context(
    conn: sqlite3.Connection, market_risk_score: Optional[float] = None,
) -> MarketContext:
    from engine.regime_filter import detect_regime

    ihsg_df = _fetch_ohlcv_df(conn, "IHSG", limit=120)
    try:
        regime = detect_regime(ihsg_df) if ihsg_df is not None and len(ihsg_df) >= 20 else "UNKNOWN"
    except Exception:
        regime = "UNKNOWN"
    if regime not in ("BULL", "BEAR", "SIDEWAYS", "VOLATILE", "UNKNOWN"):
        regime = "UNKNOWN"

    ihsg_trend = build_technical_context(conn, "IHSG", ohlcv_df=ihsg_df) if ihsg_df is not None else None

    return MarketContext(regime=regime, ihsg_trend=ihsg_trend, market_risk_score=market_risk_score)


# ── PortfolioContext (read-only paper_trades query, same fields already queried by
#    firm.py's _market_ctx today — this closes the delivery gap, not a new computation) ──

def build_portfolio_context(conn: sqlite3.Connection) -> PortfolioContext:
    rows = conn.execute(
        "SELECT ticker, entry_price, lots, tp_price, sl_price, capital_used "
        "FROM paper_trades WHERE status='OPEN'",
    ).fetchall()
    cols = ["ticker", "entry_price", "lots", "tp_price", "sl_price", "capital_used"]
    trades = [dict(zip(cols, r)) for r in rows]
    return PortfolioContext(open_trades=trades, open_position_count=len(trades))


# ── RiskContext (paper_trade.py's existing, read-only is_entries_blocked()/
#    compute_drawdown(); security.auth's existing auth_mode() — no os.getenv() call added,
#    per CLAUDE.md's "config.py is the single reader of .env" convention) ──

def build_risk_context() -> RiskContext:
    from paper_trade import compute_drawdown, is_entries_blocked
    from security.auth import auth_mode

    try:
        blocked = bool(is_entries_blocked())
    except Exception:
        blocked = False
    try:
        drawdown_pct = float(compute_drawdown(days=30)["dd_pct"])
    except Exception:
        drawdown_pct = None
    try:
        mode = auth_mode()
    except Exception:
        mode = "off"

    return RiskContext(entries_blocked=blocked, drawdown_pct=drawdown_pct, auth_mode=mode)


# ── ExecutionContext (read-only: paper_trade.py's existing get_config()/get_open_trades(),
#    never open_trade()'s own inline computation — see ADR-AF-002/WP9 sequencing note: the
#    open_trade() extraction itself is explicitly deferred to a later, separately-reviewed
#    work package, not performed here) ──

def build_execution_context() -> ExecutionContext:
    from paper_trade import get_config, get_open_trades

    try:
        cfg = get_config()
        capital = float(cfg.get("capital")) if cfg.get("capital") is not None else None
        risk_pct = float(cfg.get("risk_pct")) if cfg.get("risk_pct") is not None else None
    except Exception:
        capital = risk_pct = None

    aggregate_open_exposure_pct = None
    if capital:
        try:
            open_trades = get_open_trades()
            open_capital = sum(float(t.get("capital_used") or 0) for t in open_trades)
            aggregate_open_exposure_pct = round(open_capital / capital * 100, 2)
        except Exception:
            aggregate_open_exposure_pct = None

    return ExecutionContext(
        capital=capital,
        aggregate_open_exposure_pct=aggregate_open_exposure_pct,
        risk_pct_config=risk_pct,
        max_position_pct_config=0.30,  # mirrors paper_trade.py:410's literal; not a named
        # constant there today — duplicated as a literal here deliberately rather than
        # refactoring paper_trade.py, which is out of WP1's scope.
    )


# ── SessionContext (trivial derivation, no external dependency) ──

_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def build_session_context(scan_time: str) -> SessionContext:
    """IDX market hours are 09:00-15:30 WIB (CLAUDE.md) — the boundary is minute-aware,
    not hour-aware: 15:29 is still 'regular', 15:30 is 'post-close'."""
    wib_session: str = "regular"
    m = _TIME_RE.search(scan_time or "")
    if m:
        minutes = int(m.group(1)) * 60 + int(m.group(2))
        if minutes < 9 * 60:
            wib_session = "premarket"
        elif minutes >= 15 * 60 + 30:
            wib_session = "post-close"
        else:
            wib_session = "regular"
    return SessionContext(scan_time=scan_time, wib_session=wib_session)


# ── WP2: batch-level cache + per-candidate assembly ─────────────────────────────────────
#
# ADR-AF-002's lifecycle rule: "Tier 1 batch-level objects (MarketContext, PortfolioContext,
# RiskContext, ExecutionContext) — Production Engine, cached once per scan cycle by
# engine/agent_firm_context.py, matching firm.py's existing _market_ctx/reset_market_ctx()
# cache lifecycle exactly (that cache's location moves to the new module; its behavior —
# reset once per scan batch — is unchanged)." This section is that cache, scoped to this
# module rather than firm.py — firm.py's own _market_ctx/reset_market_ctx() (the legacy
# context path) is untouched, per WP2's mission (populate Tier 1 objects without migrating
# consumption yet).
#
# Known, documented scope boundary (not a WP2 defect): SessionContext has a builder
# (build_session_context, above) but no attach point — SignalCandidate's frozen field set
# (ADR-AF-004: exactly technical/flow/regime_context/news/market/portfolio/risk_limits/
# execution) never included a `session` field, and adding one is a schema change beyond
# WP2's "implement ONLY the wiring" mandate. Not wired here; would need its own ADR.

_batch_ctx: Optional[dict] = None


def reset_batch_context() -> None:
    """Call once per scan cycle (mirrors engine.agent_firm.firm.reset_market_ctx's cache
    lifecycle) to flush the cached batch-level Tier 1 objects."""
    global _batch_ctx
    _batch_ctx = None


def get_batch_context(conn: sqlite3.Connection, market_risk_score: Optional[float] = None) -> dict:
    """The four batch-level Tier 1 objects, computed once per scan cycle and cached.

    `market_risk_score` is honored only on the cache-filling call (matches
    build_market_context's own dependency-injection design — the caller who already
    computed the 4-sensor composite once per scan cycle passes it in once).
    """
    global _batch_ctx
    if _batch_ctx is None:
        _batch_ctx = {
            "market": _safe(build_market_context, conn, market_risk_score=market_risk_score,
                             default_factory=MarketContext),
            "portfolio": _safe(build_portfolio_context, conn, default_factory=PortfolioContext),
            "risk_limits": _safe(build_risk_context, default_factory=RiskContext),
            "execution": _safe(build_execution_context, default_factory=ExecutionContext),
        }
    return _batch_ctx


def build_candidate_context(
    conn: sqlite3.Connection,
    ticker: str,
    date_str: str,
    market_risk_score: Optional[float] = None,
) -> dict:
    """Assemble every Tier 1 field for one candidate, keyed to match SignalCandidate's new
    optional fields exactly (ADR-AF-004) — callers attach via
    ``SignalCandidate(**base_fields, **build_candidate_context(conn, ticker, date_str))``.

    Fail-soft per field (see _safe, above): a broken query for one context object degrades
    to that object's empty default and is logged, never raises into the caller.
    """
    try:
        ohlcv_df = _fetch_ohlcv_df(conn, ticker)
    except Exception as e:
        logger.warning(f"agent_firm_context: _fetch_ohlcv_df({ticker}) failed: {e}")
        ohlcv_df = None

    return {
        "technical": _safe(build_technical_context, conn, ticker, ohlcv_df=ohlcv_df,
                            default_factory=TechnicalContext),
        "flow": _safe(build_flow_context, conn, ticker, default_factory=FlowContext),
        "regime_context": _safe(build_regime_context, conn, ticker, ohlcv_df=ohlcv_df,
                                 default_factory=RegimeContext),
        "news": _safe(build_news_context, conn, ticker, date_str, default_factory=NewsContext),
        **get_batch_context(conn, market_risk_score=market_risk_score),
    }
