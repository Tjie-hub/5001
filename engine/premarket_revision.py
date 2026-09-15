"""engine/premarket_revision.py — Premarket as a REVISION of the frozen EOD base
plan, not a second discovery engine.

WHY THIS EXISTS (audit 2026-09-02, findings A-1, A-2)
------------------------------------------------------
`run_premarket_firm_scan` called `build_unified_watchlist()` and rebuilt an
entirely separate candidate universe from REVERSAL / PREMOVER / BEAR_DIP, while
EOD merged R / S / V / P. The vocabularies are disjoint; across 17 consecutive
EOD -> premarket transitions only FOUR tickers carried over and thirteen shared
none. Worse, the one real coupling ran backwards: EOD read *that morning's*
premarket approvals as source tag `P`, weighted joint-highest.

Two independent samples cannot answer "did the premarket revision improve or
worsen the EOD plan?" -- the question is unanswerable by construction, not
merely unanswered.

This module implements the intended operator:

    frozen EOD plan (session D)
        + information that did not exist at 16:40 on D
        -> RETAIN / REMOVE / UPGRADE / DOWNGRADE / ADD, each with a reason
        -> frozen Premarket plan (session D+1)

WHAT COUNTS AS NEW INFORMATION
------------------------------
Only data that lands AFTER the 16:40 EOD job. From `scheduler/__init__.py`'s
cron table that is: VPIN batch (18:00), news (17:00 and 08:00), Stockbit screener
(17:05), broker_flow (20:15), corporate actions (20:20), OHLCV reconciliation
(21:00), plus the market risk score computed at 08:35 itself.

It explicitly does NOT include `reversal_watchlist`, `watchlist_premover` or
`regime_watchlist`: all three are written at 16:15-16:30, BEFORE the EOD plan
ran. A premarket "discovery" from those tables is not new information, it is the
same evening's data re-read -- which is exactly the duplicated-generator defect
this module removes. Discovery-sourced ADDs are therefore off by default and,
when enabled, must carry an independent new-information justification.

Every decision is recorded in `watchlist_revision` (append-only) so the audit
questions are answerable from the database alone:
  why was this ticker in EOD, why was it kept/dropped/added at premarket, which
  validated strategy produced it, what OOS evidence backed it, what new
  information caused the change.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from engine.watchlist_ledger import (
    ACTION_ADD, ACTION_DOWNGRADE, ACTION_REMOVE, ACTION_RETAIN, ACTION_UPGRADE,
)

logger = logging.getLogger(__name__)

# Reason codes are a closed set so the ledger stays queryable.
R_NO_NEW_INFO = "no_new_information"
R_CORPORATE_ACTION = "corporate_action"
R_SUSPENDED = "suspension_or_stale_price"
R_MARKET_RISK_OFF = "market_risk_off"
R_NEGATIVE_NEWS = "negative_overnight_news"
R_POSITIVE_NEWS = "positive_overnight_news"
R_FOREIGN_DISTRIBUTION = "overnight_foreign_distribution"
R_FOREIGN_ACCUMULATION = "overnight_foreign_accumulation"
R_VPIN_TOXIC = "toxic_order_flow"
R_DISCOVERY = "discovery_with_new_information"

# Market-risk tiers at which the whole plan stands down. Mirrors the engine's
# existing risk vocabulary (engine/risk_score.py).
RISK_OFF_TIERS = frozenset({"CRITICAL", "RED"})

VPIN_TOXIC_LABELS = frozenset({"EXTREME", "CRITICAL"})

# A single session's foreign net turning sharply negative is evidence; noise is
# not. Expressed in rupiah of net lot value over the settled overnight session.
FOREIGN_NET_MATERIAL = 1_000_000_000


@dataclass
class RevisionDecision:
    ticker: str
    action: str
    reason_code: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    base_row: Optional[dict[str, Any]] = None

    def as_dict(self) -> dict[str, Any]:
        return {"ticker": self.ticker, "action": self.action,
                "reason_code": self.reason_code, "reason": self.reason,
                "evidence": self.evidence}


# ── overnight evidence gathering ──────────────────────────────────────────────

def _corporate_action(conn, ticker, since_date, upto_date):
    try:
        row = conn.execute(
            "SELECT action_type, event_date FROM corporate_action_events "
            "WHERE ticker=? AND event_date > ? AND event_date <= ? LIMIT 1",
            (ticker, since_date, upto_date)).fetchone()
    except Exception:
        return None
    return {"action_type": row[0], "event_date": row[1]} if row else None


def _suspension(conn, ticker, since_date):
    try:
        row = conn.execute(
            "SELECT classification, resume_date, gap_pct FROM suspension_events "
            "WHERE ticker=? AND resume_date > ? ORDER BY resume_date DESC LIMIT 1",
            (ticker, since_date)).fetchone()
    except Exception:
        return None
    return ({"classification": row[0], "resume_date": row[1], "gap_pct": row[2]}
            if row else None)


def _overnight_news(conn, ticker, since_date):
    """News rows dated after the EOD cutoff. Count + headlines only -- this
    module does not attempt sentiment it cannot justify; a material news event on
    a planned entry is grounds to downgrade and re-read, not to invent a sign."""
    try:
        rows = conn.execute(
            "SELECT date, count, headlines_json FROM news_mentions "
            "WHERE ticker=? AND date > ? ORDER BY date DESC", (ticker, since_date)
        ).fetchall()
    except Exception:
        return None
    if not rows:
        return None
    total = sum(int(r[1] or 0) for r in rows)
    if total <= 0:
        return None
    heads = []
    for r in rows:
        try:
            heads.extend(json.loads(r[2] or "[]")[:3])
        except (ValueError, TypeError):
            pass
    return {"mentions": total, "headlines": heads[:3], "since": since_date}


def _overnight_foreign_net(conn, ticker, session_date):
    try:
        buy = conn.execute(
            "SELECT SUM(lot_value) FROM broker_flow WHERE ticker=? AND "
            "investor_type='Asing' AND side='BUY' AND trade_date=?",
            (ticker, session_date)).fetchone()[0] or 0
        sell = conn.execute(
            "SELECT SUM(lot_value) FROM broker_flow WHERE ticker=? AND "
            "investor_type='Asing' AND side='SELL' AND trade_date=?",
            (ticker, session_date)).fetchone()[0] or 0
    except Exception:
        return None
    net = int(buy) - int(sell)
    if abs(net) < FOREIGN_NET_MATERIAL:
        return None
    return {"net_lot_value": net, "trade_date": session_date}


def _vpin(conn, ticker, since_date):
    try:
        row = conn.execute(
            "SELECT date, vpin, vpin_label FROM vpin_scores "
            "WHERE ticker=? AND date >= ? ORDER BY date DESC LIMIT 1",
            (ticker, since_date)).fetchone()
    except Exception:
        return None
    if not row or row[2] not in VPIN_TOXIC_LABELS:
        return None
    return {"date": row[0], "vpin": row[1], "label": row[2]}


def gather_overnight_evidence(conn, ticker: str, base_date: str,
                              plan_date: str) -> dict[str, Any]:
    """Everything about `ticker` that became knowable after the EOD cutoff."""
    ev: dict[str, Any] = {}
    ca = _corporate_action(conn, ticker, base_date, plan_date)
    if ca:
        ev["corporate_action"] = ca
    susp = _suspension(conn, ticker, base_date)
    if susp:
        ev["suspension"] = susp
    news = _overnight_news(conn, ticker, base_date)
    if news:
        ev["news"] = news
    foreign = _overnight_foreign_net(conn, ticker, base_date)
    if foreign:
        ev["foreign_flow"] = foreign
    vpin = _vpin(conn, ticker, base_date)
    if vpin:
        ev["vpin"] = vpin
    return ev


# ── the revision operator ─────────────────────────────────────────────────────

def revise(conn, base_rows: list[dict[str, Any]], *, base_date: str,
           plan_date: str, market_risk: Optional[dict] = None,
           market_regime: Optional[str] = None,
           discoveries: Optional[list[dict]] = None,
           allow_discovery_adds: bool = False) -> list[RevisionDecision]:
    """Revise the frozen EOD base plan into today's actionable plan.

    `base_rows` is the EOD snapshot (engine.watchlist_ledger.read_snapshot).
    `discoveries` are premarket-only candidates; they are IGNORED unless
    `allow_discovery_adds` is True AND the candidate carries genuinely new
    overnight evidence. Absent that, a discovery name is not new information --
    it is the previous evening's data re-read, and admitting it would recreate
    the parallel generator this module exists to remove.

    Returns one decision per base row, plus any admitted ADDs. Order is preserved
    so the caller can re-rank deterministically.
    """
    tier = str((market_risk or {}).get("tier") or "").upper()
    risk_off = tier in RISK_OFF_TIERS
    decisions: list[RevisionDecision] = []

    for row in base_rows:
        ticker = row["ticker"]
        ev = gather_overnight_evidence(conn, ticker, base_date, plan_date)
        ev_full = dict(ev)
        if market_regime:
            ev_full["market_regime"] = market_regime
        if tier:
            ev_full["market_risk_tier"] = tier

        if "corporate_action" in ev:
            decisions.append(RevisionDecision(
                ticker, ACTION_REMOVE, R_CORPORATE_ACTION,
                f"corporate action ({ev['corporate_action']['action_type']}) dated "
                f"{ev['corporate_action']['event_date']} invalidates the EOD "
                f"decision price", ev_full, row))
            continue

        if "suspension" in ev:
            decisions.append(RevisionDecision(
                ticker, ACTION_REMOVE, R_SUSPENDED,
                f"price series interrupted ({ev['suspension']['classification']}, "
                f"resume {ev['suspension']['resume_date']})", ev_full, row))
            continue

        if risk_off:
            decisions.append(RevisionDecision(
                ticker, ACTION_REMOVE, R_MARKET_RISK_OFF,
                f"market risk tier {tier} at premarket; plan stands down",
                ev_full, row))
            continue

        if "vpin" in ev:
            decisions.append(RevisionDecision(
                ticker, ACTION_DOWNGRADE, R_VPIN_TOXIC,
                f"order flow toxicity {ev['vpin']['label']} "
                f"(vpin={ev['vpin']['vpin']})", ev_full, row))
            continue

        foreign = ev.get("foreign_flow")
        if foreign and foreign["net_lot_value"] < 0:
            decisions.append(RevisionDecision(
                ticker, ACTION_DOWNGRADE, R_FOREIGN_DISTRIBUTION,
                f"settled overnight foreign net {foreign['net_lot_value']:,} on "
                f"{foreign['trade_date']}", ev_full, row))
            continue
        if foreign and foreign["net_lot_value"] > 0:
            decisions.append(RevisionDecision(
                ticker, ACTION_UPGRADE, R_FOREIGN_ACCUMULATION,
                f"settled overnight foreign net +{foreign['net_lot_value']:,} on "
                f"{foreign['trade_date']}", ev_full, row))
            continue

        if "news" in ev:
            decisions.append(RevisionDecision(
                ticker, ACTION_DOWNGRADE, R_NEGATIVE_NEWS,
                f"{ev['news']['mentions']} overnight news mention(s) not present "
                f"at EOD; re-read before acting", ev_full, row))
            continue

        decisions.append(RevisionDecision(
            ticker, ACTION_RETAIN, R_NO_NEW_INFO,
            "no information arrived after the EOD cutoff that bears on this "
            "candidate", ev_full, row))

    if allow_discovery_adds and discoveries and not risk_off:
        base_tickers = {r["ticker"] for r in base_rows}
        for d in discoveries:
            t = d.get("ticker")
            if not t or t in base_tickers:
                continue
            ev = gather_overnight_evidence(conn, t, base_date, plan_date)
            if not ev:
                # No new information -> this is yesterday's data re-read, not a
                # discovery. Refused by design (finding A-1).
                continue
            ev["discovery_sources"] = d.get("sources") or []
            decisions.append(RevisionDecision(
                t, ACTION_ADD, R_DISCOVERY,
                f"not in the EOD plan, admitted on new overnight evidence "
                f"({', '.join(sorted(ev.keys() - {'discovery_sources'}))})",
                ev, dict(d)))

    return decisions


def apply(decisions: list[RevisionDecision]) -> list[dict[str, Any]]:
    """Project revision decisions into the surviving, re-ranked plan.

    REMOVE drops the row. DOWNGRADE / UPGRADE keep it and adjust the ordering
    key; the *reason* is what matters and is preserved on the row so the report
    and the forward-test ledger can both cite it.
    """
    weight = {ACTION_UPGRADE: 0, ACTION_RETAIN: 1, ACTION_ADD: 2,
              ACTION_DOWNGRADE: 3}
    kept = []
    for d in decisions:
        if d.action == ACTION_REMOVE:
            continue
        row = dict(d.base_row or {"ticker": d.ticker})
        row["ticker"] = d.ticker
        row["revision_action"] = d.action
        row["revision_reason_code"] = d.reason_code
        row["revision_reason"] = d.reason
        prov = dict(row.get("provenance") or {})
        prov["premarket_revision"] = d.as_dict()
        row["provenance"] = prov
        row["_w"] = weight.get(d.action, 9)
        kept.append(row)
    kept.sort(key=lambda r: (r["_w"], r.get("rank") or 999))
    for r in kept:
        r.pop("_w", None)
    return kept
