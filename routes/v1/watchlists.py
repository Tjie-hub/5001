"""Watchlist APIs (Production Engine Phase 2, Workstream 2C Task 2C-1). See
docs/superpowers/specs/2026-08-06-2c1-watchlist-api-design.md.

Thin controllers over engine.trade_plan's watchlist_snapshot reads
(get_snapshot, list_snapshot_dates, diff_watchlist -- all pre-existing or
added alongside this task as pure reads) and
engine.persistent_watchlist.list_watchlist. Those functions take an
already-open sqlite3 connection (trade_plan.py's established calling
convention -- scheduler/jobs.py already manages the connection this way,
unlike engine.job_status/engine.metrics's db_path-based convention), so
each controller opens one via the centralized data.db.connect and closes
it; no SQL of its own.
"""
import config
from flask import request

from data.db import connect as db_connect
from engine import persistent_watchlist, trade_plan
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok


def _strategy_param() -> str:
    return request.args.get("strategy", "eod")


@api_v1_bp.route("/watchlists/current", methods=["GET"])
def watchlists_current():
    strategy = _strategy_param()
    conn = db_connect(config.DB_PATH)
    try:
        dates = trade_plan.list_snapshot_dates(conn, strategy)
        if not dates:
            raise ApiError("NO_WATCHLIST_DATA", 404,
                            f"no watchlist snapshot for strategy={strategy!r}")
        latest = dates[0]
        rows = trade_plan.get_snapshot(conn, latest, strategy)
    finally:
        conn.close()
    return ok({"strategy": strategy, "date": latest, "watchlist": rows})


@api_v1_bp.route("/watchlists/history", methods=["GET"])
def watchlists_history():
    strategy = _strategy_param()
    conn = db_connect(config.DB_PATH)
    try:
        dates = trade_plan.list_snapshot_dates(conn, strategy)
    finally:
        conn.close()
    return ok({"strategy": strategy, "dates": dates, "count": len(dates)})


@api_v1_bp.route("/watchlists/diff", methods=["GET"])
def watchlists_diff():
    strategy = _strategy_param()
    date_str = request.args.get("date")
    if not date_str:
        raise ApiError("MISSING_DATE", 400, "date query parameter is required")

    conn = db_connect(config.DB_PATH)
    try:
        rows = trade_plan.get_snapshot(conn, date_str, strategy)
        if not rows:
            raise ApiError("NO_WATCHLIST_DATA", 404,
                            f"no watchlist snapshot for date={date_str!r} strategy={strategy!r}")
        diff = trade_plan.diff_watchlist(conn, date_str, strategy, rows)
    finally:
        conn.close()
    return ok({"strategy": strategy, "date": date_str, "diff": diff})


@api_v1_bp.route("/watchlists/persistent", methods=["GET"])
def watchlists_persistent():
    status = request.args.get("status", "active")
    conn = db_connect(config.DB_PATH)
    try:
        rows = persistent_watchlist.list_watchlist(conn, status=status)
    finally:
        conn.close()
    return ok({"status": status, "watchlist": rows, "count": len(rows)})


@api_v1_bp.route("/watchlists/<date_str>", methods=["GET"])
def watchlists_by_date(date_str):
    strategy = _strategy_param()
    conn = db_connect(config.DB_PATH)
    try:
        rows = trade_plan.get_snapshot(conn, date_str, strategy)
    finally:
        conn.close()
    if not rows:
        raise ApiError("NO_WATCHLIST_DATA", 404,
                        f"no watchlist snapshot for date={date_str!r} strategy={strategy!r}")
    return ok({"strategy": strategy, "date": date_str, "watchlist": rows})
