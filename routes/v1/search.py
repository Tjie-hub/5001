"""Search API (Production OS Slice 5 — Search Workspace).

Thin controller over engine.instrument_search.search_instruments() --
instrument-code search over idx_tickers only. SEARCH_DESIGN_SPEC_v1.0_
FROZEN.md §5 lists five other search scenarios (watchlist candidate,
portfolio position, recommendation, market context) that have no unified
backend search service to back them yet -- this is the smallest complete
slice, not the full spec; see engine/instrument_search.py's docstring.
"""
from flask import request

import config
from engine.instrument_search import search_instruments
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok


@api_v1_bp.route("/search/instruments", methods=["GET"])
def search_instruments_route():
    """Instrument-code search (required ?q=, optional ?limit=, default 20)."""
    query = request.args.get("q", "")
    if not query.strip():
        raise ApiError("MISSING_QUERY", 400, "q query parameter is required")

    limit = request.args.get("limit", 20, type=int)
    results = search_instruments(config.DB_PATH, query, limit=limit)
    return ok({"query": query, "results": results, "count": len(results)})
