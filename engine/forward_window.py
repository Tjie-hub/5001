"""engine/forward_window.py — pre-registration of a clean forward-test window.

WHY THIS EXISTS (audit 2026-09-02, remaining blocker #5)
---------------------------------------------------------
The audit's Part 10 discipline says: fix the horizon and the decision rule
BEFORE the window opens, and if the system is tuned mid-window, close the cohort
and open a new one. Neither was enforceable, because nothing recorded what
"the system" was at the moment the window opened. A quiet change to
`disabled_strategies`, an `EDGE_SCORE_MODE` flip, a new veto threshold or a
re-ranked `candidate_score` would silently change what the cohort measures while
the numbers kept accumulating in the same bucket.

This module freezes that configuration, hashes it, and re-checks the hash on
every cycle. A change does not fail the run and does not stop trading: it CLOSES
the window as contaminated and opens a successor. Results before and after are
never pooled, which is the only honest way to keep a live system under test
while still being allowed to fix it.

Both tables are append-only (BEFORE UPDATE/DELETE triggers). A window is never
edited; closure is a new event row. Status is derived, never stored mutable.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import date, datetime
from typing import Any, Optional

COHORT_SCANNER = "scanner"
COHORT_EOD = "eod"
COHORT_PREMARKET = "premarket"
COHORTS = (COHORT_SCANNER, COHORT_EOD, COHORT_PREMARKET)

STATUS_OPEN = "OPEN"
STATUS_CONTAMINATED = "CLOSED_CONTAMINATED"
STATUS_COMPLETE = "CLOSED_COMPLETE"

EVENT_CLOSE_CONTAMINATED = "CLOSE_CONTAMINATED"
EVENT_CLOSE_COMPLETE = "CLOSE_COMPLETE"

# Pre-registered stopping rule. From the audit's answer to "minimum observations
# before judging the system": count independent DATES, not signals; 60 sessions
# can only rule out a large negative; 125 sessions AND >=100 signals is the first
# defensible GO/NO-GO; a full verdict needs >=2 market regimes.
MIN_SESSIONS_FIRST_READ = 60
MIN_SESSIONS_DECISION = 125
MIN_SIGNALS_DECISION = 100
HORIZON_SESSIONS = 5

DECISION_RULE = (
    "Pre-registered before the window opened and frozen for its duration. "
    "Primary statistic: mean NET return per signal at a 5-session horizon, "
    "entry at the next session open after the signal date, both legs through "
    "engine.exits.costs, benchmarked against IHSG over the identical window. "
    "Report the per-DATE mean alongside the per-signal mean and bootstrap the "
    "confidence interval blocked by date -- overlapping holds on one name are "
    "not independent draws. No read before 60 sessions. No GO/NO-GO before 125 "
    "sessions AND 100 signals in the cohort. GO requires the per-date mean "
    "excess over IHSG to be positive with a 95% bootstrap CI excluding zero. "
    "Multiple-testing family: 3 cohorts x 1 horizon; a per-cohort claim carries "
    "a Bonferroni-adjusted alpha of 0.0167. Cohorts are never pooled."
)

WINDOW_DDL = """
CREATE TABLE IF NOT EXISTS ft_window (
    window_id       TEXT PRIMARY KEY,
    cohort          TEXT NOT NULL,
    opened_at       TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    min_sessions    INTEGER NOT NULL,
    min_signals     INTEGER NOT NULL,
    horizon_sessions INTEGER NOT NULL,
    decision_rule   TEXT NOT NULL,
    frozen_config   TEXT NOT NULL,
    config_hash     TEXT NOT NULL,
    predecessor_id  TEXT
)
"""

WINDOW_EVENT_DDL = """
CREATE TABLE IF NOT EXISTS ft_window_event (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id   TEXT NOT NULL,
    event       TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    event_date  TEXT,
    detail      TEXT
)
"""

_TRIGGERS = (
    ("ft_window_no_update", "ft_window", "UPDATE"),
    ("ft_window_no_delete", "ft_window", "DELETE"),
    ("ft_window_event_no_update", "ft_window_event", "UPDATE"),
    ("ft_window_event_no_delete", "ft_window_event", "DELETE"),
)


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(WINDOW_DDL)
    conn.execute(WINDOW_EVENT_DDL)
    for name, table, event in _TRIGGERS:
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {event} ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only: a forward-test "
            f"window is pre-registered and cannot be revised'); END")
    conn.commit()


# ── the frozen configuration ─────────────────────────────────────────────────

def _paper_config(conn) -> dict:
    try:
        rows = conn.execute("SELECT key, value FROM paper_config").fetchall()
    except sqlite3.Error:
        return {}
    keep = {"disabled_strategies", "event_guard_start", "event_guard_end",
            "event_guard_size_mult"}
    return {k: v for k, v in rows if k in keep}


def frozen_config(conn, cohort: str) -> dict[str, Any]:
    """Everything that can change what this cohort trades.

    Anything omitted here can drift mid-window without being noticed, so the
    bias is deliberately toward including too much: a spurious contamination
    (window closed, successor opened) costs a restart; a missed one silently
    corrupts the result.
    """
    from engine import veto, trade_plan, unified_watchlist, admission
    from engine.exits.costs import DEFAULT_COSTS
    from engine.entry_convention import ENTRY_RULE_NEXT_OPEN
    from engine import strategy_version as sv
    import config as cfg

    try:
        from engine.registry_loader import get_registry, startup_summary
        reg = {"hash": get_registry()["hash"], "summary": startup_summary()}
    except Exception:
        reg = {"hash": None, "summary": None}

    try:
        from scheduler.scanner import (_REGIME_STRATEGY_MAP, _COUNTER_TREND_BOOK,
                                       _DEFAULT_DISABLED, _MOMENTUM_FAMILY)
        scanner_cfg = {
            "regime_map": {k: list(v) for k, v in sorted(_REGIME_STRATEGY_MAP.items())},
            "counter_trend": sorted(_COUNTER_TREND_BOOK),
            "default_disabled": _DEFAULT_DISABLED,
            "momentum_family": sorted(_MOMENTUM_FAMILY),
        }
    except Exception:
        scanner_cfg = {}

    try:
        strategies = {name: sv.config_hash(name)
                      for name in __import__("engine.strategies",
                                             fromlist=["STRATEGY_FUNCS"]).STRATEGY_FUNCS}
    except Exception:
        strategies = {}

    return {
        "cohort": cohort,
        "entry_rule": ENTRY_RULE_NEXT_OPEN,
        "horizon_sessions": HORIZON_SESSIONS,
        "edge_score_mode": cfg.edge_mode(),
        "registry": reg,
        "paper_config": _paper_config(conn),
        "scanner": scanner_cfg,
        "admission": {
            "wf_edge_max_age_days": admission.WF_EDGE_MAX_AGE_DAYS,
            "n_min_trades": admission.N_MIN_TRADES,
        },
        "veto": {
            "n_min_trades": veto.N_MIN_TRADES,
            "min_consistency": veto.MIN_CONSISTENCY,
            "min_win_rate": veto.MIN_WIN_RATE,
            "flow_distrib_cut": veto.FLOW_DISTRIB_CUT,
            "edge_floor": dict(sorted(veto.EDGE_FLOOR.items())),
            "n_max": dict(sorted(veto.N_MAX.items())),
        },
        "trade_plan": {"volume_mover_ratio": trade_plan.VOLUME_MOVER_RATIO,
                       "upgrade_delta": trade_plan.UPGRADE_DELTA},
        "unified_watchlist": {
            "premover_floor": unified_watchlist.PREMOVER_FLOOR,
            "confluence_bonus": unified_watchlist.CONFLUENCE_BONUS,
            "bear_base": unified_watchlist.BEAR_BASE,
            "bear_promoted_bonus": unified_watchlist.BEAR_PROMOTED_BONUS,
            "max_rows": unified_watchlist.MAX_ROWS,
        },
        "costs": {"buy_bps": getattr(DEFAULT_COSTS, "buy_bps", None),
                  "sell_bps": getattr(DEFAULT_COSTS, "sell_bps", None),
                  "repr": repr(DEFAULT_COSTS)},
        "strategy_versions": dict(sorted(strategies.items())),
    }


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(
        json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ── lifecycle ────────────────────────────────────────────────────────────────

def current(conn, cohort: str) -> Optional[dict]:
    """The open window for `cohort`, or None."""
    ensure_tables(conn)
    row = conn.execute(
        "SELECT window_id, cohort, opened_at, start_date, min_sessions, "
        "       min_signals, horizon_sessions, decision_rule, frozen_config, "
        "       config_hash, predecessor_id "
        "FROM ft_window WHERE cohort=? ORDER BY opened_at DESC, rowid DESC LIMIT 1",
        (cohort,)).fetchone()
    if not row:
        return None
    cols = ["window_id", "cohort", "opened_at", "start_date", "min_sessions",
            "min_signals", "horizon_sessions", "decision_rule", "frozen_config",
            "config_hash", "predecessor_id"]
    w = dict(zip(cols, row))
    closed = conn.execute(
        "SELECT event, occurred_at, detail FROM ft_window_event "
        "WHERE window_id=? AND event LIKE 'CLOSE%' ORDER BY id DESC LIMIT 1",
        (w["window_id"],)).fetchone()
    w["status"] = STATUS_OPEN if not closed else (
        STATUS_CONTAMINATED if closed[0] == EVENT_CLOSE_CONTAMINATED
        else STATUS_COMPLETE)
    w["closed"] = dict(zip(["event", "occurred_at", "detail"], closed)) if closed else None
    w["frozen_config"] = json.loads(w["frozen_config"])
    return w


def open_window(conn, cohort: str, start_date: str = None,
                predecessor_id: str = None) -> dict:
    """Pre-register a new window against the CURRENT configuration."""
    ensure_tables(conn)
    cfg = frozen_config(conn, cohort)
    h = config_hash(cfg)
    wid = uuid.uuid4().hex
    sd = start_date or date.today().isoformat()
    conn.execute(
        "INSERT INTO ft_window (window_id, cohort, opened_at, start_date, "
        " min_sessions, min_signals, horizon_sessions, decision_rule, "
        " frozen_config, config_hash, predecessor_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (wid, cohort, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sd,
         MIN_SESSIONS_DECISION, MIN_SIGNALS_DECISION, HORIZON_SESSIONS,
         DECISION_RULE, json.dumps(cfg, sort_keys=True, default=str), h,
         predecessor_id))
    conn.execute(
        "INSERT INTO ft_window_event (window_id, event, occurred_at, event_date, detail) "
        "VALUES (?,?,?,?,?)",
        (wid, "OPEN", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sd,
         json.dumps({"config_hash": h, "predecessor": predecessor_id})))
    conn.commit()
    return current(conn, cohort)


def _diff(old: dict, new: dict, path="") -> list[str]:
    out = []
    for k in sorted(set(old) | set(new)):
        p = f"{path}.{k}" if path else k
        a, b = old.get(k), new.get(k)
        if isinstance(a, dict) and isinstance(b, dict):
            out.extend(_diff(a, b, p))
        elif a != b:
            out.append(f"{p}: {a!r} -> {b!r}")
    return out


def check(conn, cohort: str, event_date: str = None) -> dict:
    """Verify the frozen configuration still holds; roll the window if not.

    Returns {'window': .., 'action': 'unchanged'|'opened'|'rolled',
             'changes': [...]}. Never raises on a config change -- a change is a
    legitimate act; pooling results across it is not.
    """
    ensure_tables(conn)
    w = current(conn, cohort)
    ed = event_date or date.today().isoformat()
    if w is None or w["status"] != STATUS_OPEN:
        return {"window": open_window(conn, cohort, ed,
                                      predecessor_id=w["window_id"] if w else None),
                "action": "opened", "changes": []}

    cfg = frozen_config(conn, cohort)
    h = config_hash(cfg)
    if h == w["config_hash"]:
        return {"window": w, "action": "unchanged", "changes": []}

    changes = _diff(w["frozen_config"], cfg)
    conn.execute(
        "INSERT INTO ft_window_event (window_id, event, occurred_at, event_date, detail) "
        "VALUES (?,?,?,?,?)",
        (w["window_id"], EVENT_CLOSE_CONTAMINATED,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ed,
         json.dumps({"from_hash": w["config_hash"], "to_hash": h,
                     "changes": changes[:40]})))
    conn.commit()
    new = open_window(conn, cohort, ed, predecessor_id=w["window_id"])
    return {"window": new, "action": "rolled", "changes": changes}


def check_all(conn, cohorts=COHORTS, event_date: str = None) -> dict:
    return {c: check(conn, c, event_date) for c in cohorts}


def progress(conn, cohort: str) -> dict:
    """How far the open window is against its own pre-registered stopping rule."""
    w = current(conn, cohort)
    if not w:
        return {"cohort": cohort, "window": None}
    ft_strategy = {COHORT_SCANNER: None}.get(cohort, cohort)
    try:
        if ft_strategy:
            n_sig, n_days = conn.execute(
                "SELECT COUNT(*), COUNT(DISTINCT signal_date) FROM ft_signal "
                "WHERE strategy=? AND signal_date>=?", (ft_strategy, w["start_date"])
            ).fetchone()
        else:
            n_sig, n_days = conn.execute(
                "SELECT COUNT(*), COUNT(DISTINCT signal_date) FROM ft_signal "
                "WHERE strategy NOT IN ('eod','premarket') AND signal_date>=?",
                (w["start_date"],)).fetchone()
    except sqlite3.Error:
        n_sig = n_days = 0
    return {
        "cohort": cohort, "window_id": w["window_id"], "status": w["status"],
        "start_date": w["start_date"], "signals": n_sig, "sessions": n_days,
        "first_read_at": MIN_SESSIONS_FIRST_READ,
        "decision_at": (MIN_SESSIONS_DECISION, MIN_SIGNALS_DECISION),
        "readable": n_days >= MIN_SESSIONS_FIRST_READ,
        "decidable": (n_days >= MIN_SESSIONS_DECISION
                      and n_sig >= MIN_SIGNALS_DECISION),
    }
