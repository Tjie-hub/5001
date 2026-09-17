"""engine/ticker_detail.py — per-ticker production detail read model.

Backs GET /api/v1/tickers/<symbol> (Production Decision OS Ticker workspace,
Workstream D4 slice 1). Pure aggregation over existing production tables and
existing engine logic — no new data source, no new business rule:

  * identity     — idx_tickers (status, index membership) + sector_rotation.
  * price        — latest ohlcv bars, live convention (partial intraday bars
                   ARE the scanner's signal input, so the detail view shows
                   what the scanner sees; data/loaders.py docstring).
  * regime       — engine.regime_filter.detect_regime + engine.indicators.
                   calc_adx, banded with scheduler.scanner's own
                   _BULL_STRONG_ADX threshold (single source of truth).
  * admission    — engine.admission.evaluate over scheduler.scanner's
                   _REGIME_STRATEGY_MAP candidates for the detected band with
                   scanner's disabled-strategy list: the exact composite the
                   live intraday scan applies (audit S-1 made it observable;
                   this surfaces the same verdicts per ticker).
  * market       — engine.dashboard.get_risk_dashboard(), the same aggregator
                   the Market workspace consumes.
  * flow         — stockbit_flow latest row + flow_filter foreign accumulation.
  * timeline     — production events only: scheduled_signals,
                   watchlist_snapshot, agent_decisions, paper_trades.

Fail-soft per section, fail-hard on the core: a ticker with no ohlcv history
and no idx_tickers row returns None (route -> 404); every optional section
degrades to None rather than erroring the whole read model.

Every query is parameter-bound; the connection is opened read-only.
"""
from __future__ import annotations

import logging
import sqlite3
from data.db import connect as db_connect
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")

_TIMELINE_CAP = 20


def _connect_ro(db_path: str) -> sqlite3.Connection:
    conn = db_connect(db_path, read_only=True)
    conn.row_factory = None
    return conn


def _today_wib() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d")


def get_ticker_detail(db_path: str, symbol: str) -> dict | None:
    """Assemble the Ticker workspace detail payload for `symbol`.

    Returns None when the symbol is unknown to production entirely (no
    ohlcv history AND no idx_tickers row) — the route turns that into a
    404 TICKER_NOT_FOUND envelope.
    """
    sym = symbol.strip().upper()
    conn = _connect_ro(db_path)
    try:
        identity = _identity(conn, sym)
        df = _ohlcv_df(conn, sym)
        if df is None and identity is None:
            return None

        detail: dict = {
            "symbol": sym,
            "identity": identity,
            "price": _price(df),
            "regime": _regime(df),
            "production_admission": None,
            "signals": None,
            "flow": None,
            "watchlist_membership": None,
            "agent_decisions": None,
            "position": None,
            "timeline": None,
            "market_context": None,
            "data_freshness": _freshness(conn, sym),
            "as_of": datetime.now(WIB).isoformat(),
        }

        if detail["regime"] is not None:
            detail["production_admission"] = _production_admission(conn, sym, detail["regime"])

        detail["signals"] = _latest_signals(conn, sym)
        detail["flow"] = _flow(db_path, conn, sym)
        detail["watchlist_membership"] = _watchlist_membership(conn, sym)
        detail["agent_decisions"] = _agent_decisions(conn, sym)
        detail["position"] = _open_position(conn, sym)
        detail["timeline"] = _timeline(conn, sym, detail["position"])
        try:
            from engine.dashboard import get_risk_dashboard

            detail["market_context"] = get_risk_dashboard(db_path, _today_wib())
        except Exception:
            logger.exception("[ticker_detail] market context degraded for %s", sym)

        return detail
    finally:
        conn.close()


# ── identity ──────────────────────────────────────────────────────────────

def _identity(conn: sqlite3.Connection, sym: str) -> dict | None:
    try:
        row = conn.execute(
            "SELECT status, in_idx30, in_lq45, in_idx80 FROM idx_tickers "
            "WHERE ticker = ?",
            (sym,),
        ).fetchone()
    except Exception:
        row = None
    if row is None:
        return None
    try:
        from engine.sector_rotation import get_ticker_sector

        sector = get_ticker_sector(sym)
    except Exception:
        sector = None
    return {
        "status": row[0],
        "in_idx30": bool(row[1]),
        "in_lq45": bool(row[2]),
        "in_idx80": bool(row[3]),
        "sector": sector,
    }


# ── price / regime ────────────────────────────────────────────────────────

def _ohlcv_df(conn: sqlite3.Connection, sym: str) -> pd.DataFrame | None:
    """Live-convention OHLCV (partial intraday bars included), like the scan."""
    try:
        df = pd.read_sql(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker = ? ORDER BY date ASC",
            conn,
            params=(sym,),
        )
    except Exception:
        return None
    if df.empty:
        return None
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return df


def _price(df: pd.DataFrame | None) -> dict | None:
    if df is None or len(df) == 0:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    chg = float(latest["close"] - prev["close"])
    chg_pct = chg / float(prev["close"]) * 100 if float(prev["close"]) else 0.0
    return {
        "date": str(latest["date"])[:10],
        "open": float(latest["open"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
        "close": float(latest["close"]),
        "volume": int(latest["volume"]),
        "chg": round(chg, 0),
        "chg_pct": round(chg_pct, 2),
    }


def _adx_band(regime: str, adx_value: float | None) -> str:
    """Same band the live selector routes on (scanner._BULL_STRONG_ADX)."""
    if regime in ("BEAR", "SIDEWAYS", "UNKNOWN"):
        return regime
    if adx_value is None:
        return "BULL_MODERATE"
    from scheduler.scanner import _BULL_STRONG_ADX

    return "BULL_STRONG" if adx_value >= _BULL_STRONG_ADX else "BULL_MODERATE"


def _regime(df: pd.DataFrame | None) -> dict | None:
    if df is None or len(df) == 0:
        return None
    from engine.indicators import calc_adx
    from engine.regime_filter import detect_regime

    try:
        regime = detect_regime(df)
    except Exception:
        regime = "UNKNOWN"
    try:
        adx_value = float(calc_adx(df, 14).iloc[-1])
    except Exception:
        adx_value = None
    return {
        "regime": regime,
        "adx14": round(adx_value, 1) if adx_value is not None else None,
        "band": _adx_band(regime, adx_value),
    }


# ── production admission (the scan's own composite) ───────────────────────

def _production_admission(conn: sqlite3.Connection, sym: str, regime: dict) -> dict:
    """Replay the live scan's admission chain for one ticker.

    Mirrors scheduler.scanner.adaptive_strategy_selector + the 2026-09-02
    audit remediation: every regime-map candidate goes through
    engine.admission.evaluate with the scanner's disabled list, and the
    verdict (admitted + blocking stage + reason) is reported per strategy.
    """
    try:
        from engine import admission
        from scheduler.scanner import (
            _COUNTER_TREND_BOOK,
            _REGIME_STRATEGY_MAP,
            _get_disabled_strategies,
        )

        band = regime["band"]
        candidates = list(_REGIME_STRATEGY_MAP.get(band, []))
        if not candidates:
            return {"band": band, "candidates": [], "admitted": [], "verdicts": []}

        disabled = _get_disabled_strategies()
        manifest = admission.manifest_rule_ids()
        verdicts = []
        for strategy in candidates:
            v = admission.evaluate(conn, sym, strategy, disabled=disabled,
                                   manifest_rule_ids=manifest, require_registry=False)
            verdicts.append({
                "strategy": v.strategy,
                "admitted": v.admitted,
                "stage": v.stage,
                "reason": v.reason,
                "registry_state": v.registry_state,
                "is_counter_trend": strategy in _COUNTER_TREND_BOOK,
            })
        admitted = [v["strategy"] for v in verdicts if v["admitted"]]
        return {"band": band, "candidates": candidates, "admitted": admitted,
                "verdicts": verdicts}
    except Exception:
        logger.exception("[ticker_detail] admission degraded for %s", sym)
        return None


# ── signals / flow / watchlist / decisions / position ─────────────────────

def _latest_signals(conn: sqlite3.Connection, sym: str) -> list[dict]:
    try:
        rows = conn.execute(
            "SELECT scan_time, strategies, signal_direction, flow_score, "
            "flow_verdict, smart_money, signal_reasons "
            "FROM scheduled_signals WHERE ticker = ? "
            "ORDER BY scan_time DESC LIMIT 5",
            (sym,),
        ).fetchall()
    except Exception:
        return []
    return [
        {
            "scan_time": r[0],
            "strategies": r[1],
            "direction": r[2],
            "flow_score": r[3],
            "flow_verdict": r[4],
            "smart_money": r[5],
            "reasons": r[6],
        }
        for r in rows
    ]


def _flow(db_path: str, conn: sqlite3.Connection, sym: str) -> dict | None:
    out: dict = {"latest": None, "foreign_accumulation": None}
    try:
        row = conn.execute(
            "SELECT trade_date, composite_score, verdict, smart_money, "
            "net_value, last_price FROM stockbit_flow "
            "WHERE ticker = ? AND composite_score IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT 1",
            (sym,),
        ).fetchone()
        if row:
            out["latest"] = {
                "trade_date": row[0], "composite_score": row[1],
                "verdict": row[2], "smart_money": row[3],
                "net_value": row[4], "last_price": row[5],
            }
    except Exception:
        logger.exception("[ticker_detail] flow latest degraded for %s", sym)
    try:
        from flow_filter import get_foreign_accumulation

        fa = get_foreign_accumulation(sym, db_path=db_path)
        if fa is not None:
            out["foreign_accumulation"] = {
                "score_pct": fa.get("score_pct"),
                "foreign_net_lots": fa.get("foreign_net_lots"),
                "avg_daily_vol_lots": fa.get("avg_daily_vol_lots"),
                "dates_used": fa.get("dates_used"),
                "latest_date": fa.get("latest_date"),
            }
    except Exception:
        logger.exception("[ticker_detail] foreign accumulation degraded for %s", sym)
    return out


def _watchlist_membership(conn: sqlite3.Connection, sym: str) -> list[dict]:
    try:
        rows = conn.execute(
            "SELECT date, strategy, rank, confidence, conviction, confluence "
            "FROM watchlist_snapshot WHERE ticker = ? "
            "ORDER BY date DESC, strategy ASC LIMIT 10",
            (sym,),
        ).fetchall()
    except Exception:
        return []
    return [
        {"date": r[0], "strategy": r[1], "rank": r[2], "confidence": r[3],
         "conviction": r[4], "confluence": r[5]}
        for r in rows
    ]


def _agent_decisions(conn: sqlite3.Connection, sym: str) -> list[dict]:
    try:
        rows = conn.execute(
            "SELECT scan_time, strategy, decision, confidence, size_hint, "
            "rationale FROM agent_decisions WHERE ticker = ? "
            "ORDER BY scan_time DESC LIMIT 3",
            (sym,),
        ).fetchall()
    except Exception:
        return []
    return [
        {"scan_time": r[0], "strategy": r[1], "decision": r[2],
         "confidence": r[3], "size_hint": r[4], "rationale": r[5]}
        for r in rows
    ]


def _open_position(conn: sqlite3.Connection, sym: str) -> dict | None:
    try:
        row = conn.execute(
            "SELECT strategy, entry_date, entry_price, lots, tp_price, sl_price "
            "FROM paper_trades WHERE ticker = ? AND status = 'OPEN' "
            "ORDER BY entry_date DESC LIMIT 1",
            (sym,),
        ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    return {"strategy": row[0], "entry_date": row[1], "entry_price": row[2],
            "lots": row[3], "tp_price": row[4], "sl_price": row[5]}


# ── activity timeline (production events only) ────────────────────────────

def _timeline(conn: sqlite3.Connection, sym: str, position: dict | None) -> list[dict]:
    events: list[dict] = []
    try:
        for r in conn.execute(
            "SELECT scan_time, strategies, signal_direction, flow_verdict "
            "FROM scheduled_signals WHERE ticker = ? "
            "ORDER BY scan_time DESC LIMIT 10",
            (sym,),
        ):
            events.append({
                "at": str(r[0]), "kind": "scan_signal", "direction": r[2],
                "summary": f"{r[2]} signal ({r[1]}) — flow {r[3] or 'n/a'}",
            })
    except Exception:
        logger.exception("[ticker_detail] timeline signals degraded for %s", sym)
    try:
        for r in conn.execute(
            "SELECT date, strategy, rank, confidence FROM watchlist_snapshot "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 10",
            (sym,),
        ):
            events.append({
                "at": str(r[0]), "kind": "watchlist_membership",
                "summary": f"{r[1]} watchlist — rank {r[2]}, confidence {r[3]}",
            })
    except Exception:
        logger.exception("[ticker_detail] timeline watchlist degraded for %s", sym)
    try:
        for r in conn.execute(
            "SELECT scan_time, strategy, decision, confidence "
            "FROM agent_decisions WHERE ticker = ? "
            "ORDER BY scan_time DESC LIMIT 10",
            (sym,),
        ):
            events.append({
                "at": str(r[0]), "kind": "agent_decision",
                "summary": f"agent firm {r[2]} ({r[1]}, confidence {r[3]})",
            })
    except Exception:
        logger.exception("[ticker_detail] timeline agent decisions degraded for %s", sym)
    try:
        for r in conn.execute(
            "SELECT entry_date, exit_date, strategy, entry_price, exit_price, "
            "exit_reason, pnl_pct, status FROM paper_trades WHERE ticker = ? "
            "ORDER BY COALESCE(entry_date, '0000-00-00') DESC LIMIT 6",
            (sym,),
        ):
            if r[7] == "OPEN":
                events.append({
                    "at": str(r[0]), "kind": "paper_open",
                    "summary": f"paper position opened ({r[2]}) @ {r[3]}",
                })
            else:
                events.append({
                    "at": str(r[1] or r[0]), "kind": "paper_close",
                    "summary": f"paper position closed ({r[5]}, {r[6]}%)",
                })
    except Exception:
        logger.exception("[ticker_detail] timeline paper trades degraded for %s", sym)

    # Sort newest-first by parseable timestamp; production rows with a
    # non-timestamp sentinel in the time column (e.g. instrumentation
    # markers in agent_decisions.scan_time) sort last, never first.
    def _sort_key(event: dict) -> str:
        try:
            datetime.fromisoformat(event["at"])
            return event["at"]
        except (TypeError, ValueError):
            return ""

    events.sort(key=lambda e: _sort_key(e), reverse=True)
    return events[:_TIMELINE_CAP]


# ── freshness ─────────────────────────────────────────────────────────────

def _freshness(conn: sqlite3.Connection, sym: str) -> dict:
    # One explicit query per table — table/column names are module constants,
    # never external input, so nothing but the ticker value is ever bound.
    def _max_ohlcv() -> str | None:
        try:
            row = conn.execute(
                "SELECT MAX(date) FROM ohlcv WHERE ticker = ?", (sym,)
            ).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _max_flow(table_name: str) -> str | None:
        query = {
            "stockbit_flow": "SELECT MAX(trade_date) FROM stockbit_flow WHERE ticker = ?",
            "broker_flow": "SELECT MAX(trade_date) FROM broker_flow WHERE ticker = ?",
        }[table_name]
        try:
            row = conn.execute(query, (sym,)).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    return {
        "ohlcv": _max_ohlcv(),
        "stockbit_flow": _max_flow("stockbit_flow"),
        "broker_flow": _max_flow("broker_flow"),
    }
