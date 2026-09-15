"""Strict 2-LLM-invocations-per-trading-day contract for the Agent Firm.

Two runs per IDX session, both targeting the SAME up-to-3 selected tickers
(owner decision, 2026-09-15 — was originally spec'd as a single ticker,
widened to top-3 to match the existing deterministic ranking):

  post_close  (16:40 WIB, scheduler.jobs.run_eod_trade_plan)
      -- selects the tickers and creates the plan for the NEXT session.
  premarket   (08:35 WIB, scheduler.jobs.run_premarket_firm_scan)
      -- loads that SAME ticker set and adjusts the plan using overnight
         information (news/flow/corp actions), never re-selects.

Every other Agent Firm call site that used to scan a wider universe or run
more than twice a day (scheduler/scanner.py's per-scan-cycle gate and bear-
watchlist ranking) has been neutered to a pure pass-through — see their own
docstrings in scheduler/scanner.py. monitor.py's per-trade exit-confirmation
review is a distinct, intentionally untouched concern (owner decision,
2026-09-15) — not part of this contract.

This module does not re-implement ticker selection or firm-calling — it only
owns: capping an already-ranked candidate pool at MAX_DAILY_TICKERS (reusing
engine.trade_plan.select_top), finding the next trading session (reusing
engine.calendar_filter.is_trading_day), the retry-safe once-per-
(session_date, run_type) billing guard, and the plan store the premarket run
reads back.
"""
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

RUN_POST_CLOSE = "post_close"
RUN_PREMARKET = "premarket"
MAX_DAILY_TICKERS = 3


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Idempotent migration — safe to call on every job invocation (CLAUDE.md convention)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_firm_daily_run ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_date TEXT NOT NULL, "
        "run_type TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "attempt INTEGER NOT NULL, "
        "tickers TEXT NOT NULL, "
        "provider TEXT, "
        "reason TEXT, "
        "result TEXT, "
        "plan_changed INTEGER, "
        "created_at TEXT NOT NULL, "
        "updated_at TEXT NOT NULL"
        ")"
    )
    # Partial unique index: only one SUCCESS per (session_date, run_type) is ever
    # allowed — this is the actual billing guard. Failed/in_progress attempts are
    # deliberately NOT constrained so a genuine retry can insert a new row.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_firm_daily_run_success "
        "ON agent_firm_daily_run(session_date, run_type) WHERE status = 'success'"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS agent_firm_daily_plan ("
        "session_date TEXT NOT NULL, "
        "ticker TEXT NOT NULL, "
        "rank INTEGER NOT NULL, "
        "decision TEXT, "
        "confidence REAL, "
        "size_tier TEXT, "
        "rationale TEXT, "
        "source TEXT NOT NULL, "
        "created_at TEXT NOT NULL, "
        "updated_at TEXT NOT NULL, "
        "PRIMARY KEY (session_date, ticker)"
        ")"
    )
    conn.commit()


def next_trading_session(from_date: date) -> date:
    """First IDX trading day strictly after from_date.

    Bounded to a 14-day search window — IDX has never had a closure anywhere
    near that long, so exceeding it means the calendar data itself is broken
    and callers should fail loudly rather than silently skip weeks of runs.
    """
    from engine.calendar_filter import is_trading_day
    d = from_date
    for _ in range(14):
        d = d + timedelta(days=1)
        ok, _reason = is_trading_day(d)
        if ok:
            return d
    raise RuntimeError(
        f"no trading day found within 14 days after {from_date} — "
        f"check engine.calendar_filter's holiday data"
    )


def select_daily_tickers(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap an already-ranked candidate pool at MAX_DAILY_TICKERS (3, or fewer if
    fewer qualify). Does not invent new ranking — delegates to the existing
    deterministic confluence/conviction ranking in engine.trade_plan."""
    from engine.trade_plan import select_top
    return select_top(cands, n=MAX_DAILY_TICKERS)


class RunGuard:
    """Result of begin_run(): whether the caller may proceed with a billable
    LLM invocation, and the run_id to pass to finish_run() when it does."""

    def __init__(self, should_call: bool, run_id: Optional[int], attempt: Optional[int],
                 reason: Optional[str] = None):
        self.should_call = should_call
        self.run_id = run_id
        self.attempt = attempt
        self.reason = reason


def begin_run(conn: sqlite3.Connection, session_date: str, run_type: str,
              tickers: list[str]) -> RunGuard:
    """Retry-safe idempotency guard for one billable LLM invocation.

    should_call is False iff a SUCCESS row already exists for this
    (session_date, run_type) — a prior FAILURE never blocks a retry, and each
    retry gets its own row with an incremented `attempt` so the invocation
    count is visible in the audit trail (agent_firm_daily_run).
    """
    ensure_tables(conn)
    existing = conn.execute(
        "SELECT id FROM agent_firm_daily_run "
        "WHERE session_date=? AND run_type=? AND status='success'",
        (session_date, run_type),
    ).fetchone()
    if existing:
        return RunGuard(False, existing[0], None, reason="already_succeeded")

    prior_attempts = conn.execute(
        "SELECT COALESCE(MAX(attempt), 0) FROM agent_firm_daily_run "
        "WHERE session_date=? AND run_type=?",
        (session_date, run_type),
    ).fetchone()[0]
    attempt = prior_attempts + 1
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO agent_firm_daily_run "
        "(session_date, run_type, status, attempt, tickers, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (session_date, run_type, "in_progress", attempt, json.dumps(list(tickers)), now, now),
    )
    conn.commit()
    return RunGuard(True, cur.lastrowid, attempt)


def finish_run(conn: sqlite3.Connection, run_id: int, *, status: str,
               provider: Optional[str] = None, reason: Optional[str] = None,
               result: Optional[dict[str, Any]] = None,
               plan_changed: Optional[bool] = None) -> None:
    """Record the outcome of a begin_run()-guarded invocation.

    status='success' is what makes begin_run() refuse a same-day duplicate;
    status='failed' deliberately leaves the door open for a retry.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE agent_firm_daily_run SET status=?, provider=?, reason=?, result=?, "
        "plan_changed=?, updated_at=? WHERE id=?",
        (status, provider, reason,
         json.dumps(result) if result is not None else None,
         None if plan_changed is None else int(plan_changed),
         now, run_id),
    )
    conn.commit()


def persist_plan(conn: sqlite3.Connection, session_date: str, ranked_rows: list[dict[str, Any]],
                 decisions: Optional[list[Any]], *, source: str) -> None:
    """Upsert one agent_firm_daily_plan row per ticker in ranked_rows (rank = position).

    Called by both runs: post_close creates the rows, premarket overwrites the
    same (session_date, ticker) rows in place (source flips to 'premarket') so
    load_plan() always reflects the latest reviewed state.
    """
    ensure_tables(conn)
    by_ticker = {d.ticker: d for d in (decisions or [])}
    now = datetime.now(timezone.utc).isoformat()
    for i, row in enumerate(ranked_rows, start=1):
        ticker = row["ticker"]
        d = by_ticker.get(ticker)
        conn.execute(
            "INSERT INTO agent_firm_daily_plan "
            "(session_date, ticker, rank, decision, confidence, size_tier, rationale, "
            "source, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(session_date, ticker) DO UPDATE SET "
            "rank=excluded.rank, decision=excluded.decision, confidence=excluded.confidence, "
            "size_tier=excluded.size_tier, rationale=excluded.rationale, "
            "source=excluded.source, updated_at=excluded.updated_at",
            (session_date, ticker, i,
             getattr(d, "decision", None), getattr(d, "confidence", None),
             getattr(d, "size_tier", None), getattr(d, "rationale", None),
             source, now, now),
        )
    conn.commit()


def load_plan(conn: sqlite3.Connection, session_date: str) -> list[dict[str, Any]]:
    """The stored plan for session_date, ranked — empty list if none exists yet."""
    ensure_tables(conn)
    rows = conn.execute(
        "SELECT ticker, rank, decision, confidence, size_tier, rationale, source "
        "FROM agent_firm_daily_plan WHERE session_date=? ORDER BY rank",
        (session_date,),
    ).fetchall()
    return [
        {"ticker": r[0], "rank": r[1], "decision": r[2], "confidence": r[3],
         "size_tier": r[4], "rationale": r[5], "source": r[6]}
        for r in rows
    ]
