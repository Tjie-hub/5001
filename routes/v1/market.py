"""Market summary API (Production OS Slice 4 — Market Workspace).

Thin controller over engine.dashboard.get_risk_dashboard() -- the same
aggregator already serving the legacy /api/dashboard/risk route (routes/
flow.py). No new market computation is added here: this endpoint exists to
give the frontend a versioned, enveloped read of data that already exists
and is already computed server-side (breadth, IHSG technicals, foreign
flow, VPIN, accumulation/distribution, and the composite risk score/tier
derived from them) -- consistent with MARKET_DESIGN_SPEC_v1.0_FROZEN.md §12
("API Boundary: Consumes backend market APIs only. No frontend market
calculations.").

get_risk_dashboard() never raises for missing/insufficient data -- every
sub-sensor degrades to a zeroed/'INSUFFICIENT_DATA' (or 'NEUTRAL') summary
(see engine/dashboard.py's _empty_* helpers), so this endpoint has no
NO_DATA 404 case of its own: an honestly-labelled degraded payload is the
correct empty state, not an error.
"""
from datetime import date as _date

from flask import request

import config
from engine.dashboard import get_risk_dashboard
from routes.v1 import api_v1_bp
from routes.v1.envelope import ok


@api_v1_bp.route("/market/summary", methods=["GET"])
def market_summary():
    """Executive market summary: composite risk score/tier plus the
    breadth, IHSG technicals, foreign flow, VPIN and accdist sensors that
    feed it (optional ?date=, default today)."""
    query_date = request.args.get("date", _date.today().isoformat())
    return ok(get_risk_dashboard(config.DB_PATH, query_date))
