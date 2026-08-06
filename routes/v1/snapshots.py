"""Snapshot APIs (Production Engine Phase 2, Workstream 2C Task 2C-2). See
docs/superpowers/specs/2026-08-06-2c2-snapshot-api-design.md.

A metadata/inventory layer across every snapshot-producing table --
watchlist_snapshot (engine.trade_plan) and candidate_watchlist_snapshot
(engine.watchlist_report) -- not a second way to fetch content (that's
2C-1's job for watchlists, 2C-4's for the candidate universe). Thin
controllers over list_snapshot_inventory() in each module; type/strategy
filtering happens in Python over the already-computed combined list, not
via new SQL.
"""
import config
from flask import request

from data.db import connect as db_connect
from engine import trade_plan, watchlist_report
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok


def _combined_inventory(conn) -> list[dict]:
    rows = [
        {"type": "watchlist", "strategy": r["strategy"], "date": r["date"],
         "ticker_count": r["ticker_count"]}
        for r in trade_plan.list_snapshot_inventory(conn)
    ]
    rows += [
        {"type": "candidate_universe", "strategy": None, "date": r["date"],
         "ticker_count": r["ticker_count"]}
        for r in watchlist_report.list_snapshot_inventory(conn)
    ]
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def _apply_filters(rows: list[dict]) -> list[dict]:
    type_ = request.args.get("type")
    strategy = request.args.get("strategy")
    if type_:
        rows = [r for r in rows if r["type"] == type_]
    if strategy:
        rows = [r for r in rows if r["strategy"] == strategy]
    return rows


@api_v1_bp.route("/snapshots", methods=["GET"])
def snapshots_index():
    conn = db_connect(config.DB_PATH)
    try:
        rows = _combined_inventory(conn)
    finally:
        conn.close()
    rows = _apply_filters(rows)
    return ok({"snapshots": rows, "count": len(rows)})


@api_v1_bp.route("/snapshots/<date_str>", methods=["GET"])
def snapshots_by_date(date_str):
    conn = db_connect(config.DB_PATH)
    try:
        rows = _combined_inventory(conn)
    finally:
        conn.close()
    rows = _apply_filters([r for r in rows if r["date"] == date_str])
    if not rows:
        raise ApiError("NO_SNAPSHOT_DATA", 404, f"no snapshot for date={date_str!r}")
    return ok({"date": date_str, "snapshots": rows, "count": len(rows)})
