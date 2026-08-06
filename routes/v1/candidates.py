"""Candidate Universe APIs (Production Engine Phase 2, Workstream 2C Task
2C-4). See
docs/superpowers/specs/2026-08-06-2c4-candidate-universe-api-design.md.

Four sources, five endpoints, each a thin controller over an existing
service function -- nothing here computes a score, ranks, or scans:
- candidate_watchlist_snapshot (engine.watchlist_report) -- the canonical
  pre-firm candidate universe, current/{date}.
- daily_screen (screener.db.get_screen_results) -- kept alongside the
  still-live legacy /api/screener/results (active consumer:
  templates/workspace.html), not a replacement for it.
- reversal_watchlist / live scan (screener.reversal_filter) -- migrated
  from the removed legacy GET /api/screener/reversal (no active consumer).
- watchlist_premover (engine.premover_detector.get_watchlist) -- migrated
  from the removed legacy GET /api/premover/watchlist (no active
  consumer). POST /api/premover/run (a write/trigger action) is untouched
  and out of this read-only task's scope.
"""
from datetime import date as _date

import config
from flask import request

from data.db import connect as db_connect
from engine import watchlist_report
from engine.premover_detector import get_watchlist as premover_get_watchlist
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok
from screener import db as screener_db
from screener import reversal_filter


@api_v1_bp.route("/candidates", methods=["GET"])
def candidates_current():
    conn = db_connect(config.DB_PATH)
    try:
        inventory = watchlist_report.list_snapshot_inventory(conn)
        if not inventory:
            raise ApiError("NO_CANDIDATE_DATA", 404,
                            "no candidate universe snapshot exists yet")
        latest = inventory[0]["date"]
        rows = watchlist_report.get_snapshot(conn, latest)
    finally:
        conn.close()
    return ok({"date": latest, "candidates": rows})


@api_v1_bp.route("/candidates/<date_str>", methods=["GET"])
def candidates_by_date(date_str):
    conn = db_connect(config.DB_PATH)
    try:
        rows = watchlist_report.get_snapshot(conn, date_str)
    finally:
        conn.close()
    if not rows:
        raise ApiError("NO_CANDIDATE_DATA", 404,
                        f"no candidate universe snapshot for date={date_str!r}")
    return ok({"date": date_str, "candidates": rows})


@api_v1_bp.route("/candidates/screening", methods=["GET"])
def candidates_screening():
    date_str = request.args.get("date", _date.today().isoformat())
    rows = screener_db.get_screen_results(date_str)
    return ok({"date": date_str, "results": rows, "count": len(rows)})


@api_v1_bp.route("/candidates/reversal-watchlist", methods=["GET"])
def candidates_reversal_watchlist():
    date_str = request.args.get("date")
    direction = request.args.get("direction")

    if date_str:
        scan_date = date_str
        results = reversal_filter.run_scan(date_str, config.DB_PATH)
    else:
        scan_date, results = reversal_filter.get_current_watchlist(config.DB_PATH)

    if direction:
        results = [r for r in results if r.get("direction") == direction]

    longs = sum(1 for r in results if r.get("direction") == "long")
    return ok({
        "scan_date": scan_date, "count": len(results),
        "long": longs, "short": len(results) - longs, "results": results,
    })


@api_v1_bp.route("/candidates/premover-watchlist", methods=["GET"])
def candidates_premover_watchlist():
    min_score = int(request.args.get("min_score", 50))
    days = int(request.args.get("days", 5))
    pattern_type = request.args.get("pattern_type", None)
    items = premover_get_watchlist(config.DB_PATH, min_score=min_score,
                                    days=days, pattern_type=pattern_type)
    return ok({"count": len(items), "watchlist": items})
